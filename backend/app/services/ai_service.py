"""AI Service - 调用 OpenAI 处理文章内容"""
import logging
from typing import TypedDict

from openai import OpenAI
from pydantic import BaseModel, Field

from app.core.config import settings


logger = logging.getLogger(__name__)

# 全局 OpenAI 客户端(整个 app 共享一个,自动管理连接池)
client = OpenAI(api_key=settings.openai_api_key)


# ===== 用 Pydantic 定义 LLM 输出的 schema =====

class ArticleAnalysis(BaseModel):
    """LLM 分析文章后返回的结构化数据"""
    summary: str = Field(
        description="A concise 1-2 sentence summary of the article's core idea, in the same language as the article."
    )
    tags: list[str] = Field(
        description="1 to 2 lowercase tags that best categorize this article (e.g. 'kubernetes', 'rust'). No spaces in single-word tags."
    )


# ===== Embedding 函数 =====

def embed_text(text: str) -> list[float] | None:
    """把文本转成向量，失败返回 None。"""
    try:
        response = client.embeddings.create(
            model=settings.embedding_model,
            input=text[:8000],
        )
        return response.data[0].embedding
    except Exception as e:
        logger.error(f"Embedding API error: {e}")
        return None


def embed_article(article) -> list[float] | None:
    """
    给文章生成向量。
    优先用 标题 + AI摘要，没有摘要时降级用 标题 + excerpt。
    """
    if article.ai_summary:
        text = f"{article.title}. {article.ai_summary}"
    elif article.excerpt:
        text = f"{article.title}. {article.excerpt}"
    else:
        text = article.title
    return embed_text(text)


# ===== 主要 service 函数 =====

def analyze_article(
    title: str,
    content: str | None,
) -> ArticleAnalysis | None:
    """
    用 LLM 分析文章,返回摘要和标签。
    existing_tags: 库里已有的标签,让 LLM 优先复用而不是造新词。
    如果失败,返回 None(不抛异常,让上层决定是否重试)。
    """
    # 1. 防御性检查:内容太短就别浪费 API 调用
    if not content or len(content.strip()) < 100:
        logger.info(f"Skipping AI analysis: content too short ({len(content or '')} chars)")
        return None

    # 2. 截断超长内容(GPT-4o-mini 上下文够大但没必要塞全文,省 token)
    truncated_content = content[:8000]  # 约 2000-3000 token

    # 3. 构造 prompt
    system_prompt = """You are a content tagging assistant for a personal knowledge library.
Given an article, you produce:
1. A concise summary (1-2 sentences) capturing the core idea
2. 1-2 tags that best categorize this article

Tag rules:
- Tags must be technologies, concepts, or domain topics — never generic words like "tutorial", "guide", "interesting"
- Use lowercase with hyphens for multi-word tags (e.g. "distributed-systems", not "distributed systems")
- Good tag examples: "kubernetes", "rust", "rag", "react", "security", "database"

Respond with the same language as the article (English in / English out, 中文 in / 中文 out).
"""

    user_prompt = f"""Title: {title}

Content:
{truncated_content}

Analyze this article."""
    
    # 4. 调用 OpenAI(用 Structured Output,强制返回符合 schema 的 JSON)
    try:
        response = client.beta.chat.completions.parse(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format=ArticleAnalysis,  # 关键!强制 schema
            temperature=0.3,                   # 低温度 = 更稳定、可预测
        )
        
        result = response.choices[0].message.parsed
        if result is None:
            logger.warning("OpenAI returned no parsed result")
            return None
        
        # 5. 后处理:tag 标准化(全部小写、去空格)
        result.tags = [
            tag.strip().lower() 
            for tag in result.tags 
            if tag.strip()
        ][:2]  # 最多 2 个,防止 LLM 不听话
        
        logger.info(f"AI analyzed: '{title[:50]}' → tags={result.tags}")
        return result
        
    except Exception as e:
        # 失败不抛异常,记日志返回 None,让用户先看到没 AI 的版本
        logger.error(f"OpenAI API error: {e}")
        return None

# ===== RAG 回答生成 =====

def generate_answer(question: str, sources: list[dict]) -> str | None:
    """
    RAG 的 Generation 步骤：把检索到的文章作为上下文，让 GPT 生成回答。

    sources: 每个元素是 {"index": 1, "title": ..., "ai_summary": ..., "content": ...}
    返回结构化 markdown：库里有什么 → 回答 → 覆盖空白提示。
    """
    if not sources:
        return None

    context_parts = []
    for s in sources:
        text = s.get("ai_summary") or s.get("content", "")[:500]
        context_parts.append(f'[{s["index"]}] {s["title"]}\n{text}')
    context = "\n\n".join(context_parts)

    system_prompt = """You are a helpful assistant for a personal knowledge base called Cairn.
The user has saved technical articles to their library. Answer their question using ONLY the provided articles.

Structure your response using exactly these markdown sections:

## Answer
Answer the question based on the articles. Cite sources inline using [1], [2], etc.
Only state what the articles actually say — never fabricate information.

## ⚠️ Coverage gaps
If the question touches areas NOT well covered by the retrieved articles, list what's missing specifically.
End with: "Consider saving articles about: [list the missing topics]"
If coverage is sufficient to fully answer the question, omit this section entirely.

Rules:
- IMPORTANT: Always respond in the same language as the user's question. English question → English answer. Chinese question → Chinese answer.
- Never make up information not present in the articles
- If the library has almost nothing relevant, say so clearly in the Answer section"""

    user_prompt = f"""Here are the retrieved articles from the user's library:

{context}

Question: {question}

Respond following the structure above:"""

    try:
        response = client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"generate_answer error: {e}")
        return None


# ===== Tag 语义去重 =====

SIMILARITY_THRESHOLD = 0.15  # cosine distance（越小越相似）; 0.15 ≈ similarity > 0.85

def _resolve_tag(db, tag_name: str):
    """
    给定 LLM 生成的 tag 名称，返回最终应使用的 Tag 对象：
    1. 完全匹配 → 直接复用
    2. Embedding 语义相似（距离 < threshold）→ 复用最近的已有 tag
    3. 都不满足 → 创建新 tag 并存 embedding
    """
    from app.models.tag import Tag
    from sqlalchemy import text

    # 1. 完全匹配
    existing = db.query(Tag).filter(Tag.name == tag_name).first()
    if existing:
        from app.models.tag_merge import TagMerge
        db.add(TagMerge(from_name=tag_name, to_id=existing.id, distance=0.0))
        return existing

    # 2. 语义相似匹配
    tag_embedding = embed_text(tag_name)
    if tag_embedding:
        result = db.execute(
            text("""
                SELECT id, name, embedding <=> CAST(:emb AS vector) AS distance
                FROM tags
                WHERE embedding IS NOT NULL
                ORDER BY distance
                LIMIT 1
            """),
            {"emb": str(tag_embedding)},
        ).first()

        if result and result.distance < SIMILARITY_THRESHOLD:
            logger.info(
                f"Tag '{tag_name}' → reusing '{result.name}' (distance={result.distance:.3f})"
            )
            from app.models.tag_merge import TagMerge
            db.add(TagMerge(from_name=tag_name, to_id=result.id, distance=result.distance))
            return db.query(Tag).filter(Tag.id == result.id).first()

    # 3. 创建新 tag
    new_tag = Tag(name=tag_name, embedding=tag_embedding)
    db.add(new_tag)
    db.flush()
    logger.info(f"Tag '{tag_name}' → created new tag")
    return new_tag


# 异步处理函数(Day 13)
def process_article_in_background(article_id: int) -> None:
    """
    后台任务:分析文章并把结果写入数据库。
    
    这个函数会在新的数据库 session 里运行(因为请求的 session 在 return 时关闭了)。
    任何异常都不能往外抛,只记日志(后台任务异常没人接)。
    """
    from app.core.database import SessionLocal
    from app.models.article import Article

    db = SessionLocal()
    try:
        article = db.query(Article).filter(Article.id == article_id).first()
        if not article:
            logger.warning(f"Background task: article {article_id} not found")
            return
        
        # 跳过已处理过的(防止重复执行)
        if article.ai_summary:
            logger.info(f"Background task: article {article_id} already processed, skipping")
            return
        
        # 调 AI
        analysis = analyze_article(article.title, article.content)
        if not analysis:
            logger.warning(f"Background task: AI analysis failed for article {article_id}")
            return
        
        # 写入摘要
        article.ai_summary = analysis.summary
        
        # 处理标签（带 embedding 语义去重）
        for tag_name in analysis.tags:
            tag = _resolve_tag(db, tag_name)
            if tag not in article.tags:
                article.tags.append(tag)
        
        # 生成向量（摘要已写入，向量质量更高）
        embedding = embed_article(article)
        if embedding:
            article.embedding = embedding

        db.commit()
        logger.info(f"✅ Background AI processing done for article {article_id}")
        
    except Exception as e:
        logger.exception(f"Background task error for article {article_id}: {e}")
        db.rollback()
    finally:
        db.close()