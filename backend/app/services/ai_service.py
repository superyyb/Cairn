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
    existing_tags: list[str] | None = None,
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
    tag_hint = ""
    if existing_tags:
        tag_hint = (
            f"\n\nExisting tags in this library — reuse these exact strings whenever they fit, "
            f"instead of inventing new variants:\n{', '.join(existing_tags)}"
        )

    system_prompt = f"""You are a content tagging assistant for a personal knowledge library.
Given an article, you produce:
1. A concise summary (1-2 sentences) capturing the core idea
2. 1-2 tags that best categorize this article

Tag rules:
- Tags must be technologies, concepts, or domain topics — never generic words like "tutorial", "guide", "interesting"
- Use lowercase with hyphens for multi-word tags (e.g. "distributed-systems", not "distributed systems")
- Good tag examples: "kubernetes", "rust", "rag", "react", "security", "database"
- STRONGLY prefer reusing an existing tag over creating a new one — only create a new tag if nothing in the existing list is a good fit{tag_hint}

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

class AnswerGeneration(BaseModel):
    """LLM 生成的结构化回答：正文、实际引用的 source 编号、覆盖度提示都是独立字段，
    不再靠在 markdown 正文里搜 `[N]` 或标题文字来回推——那种字符串匹配对 LLM 的输出格式没有约束力。"""
    answer: str = Field(
        description="The answer to the question, citing sources inline using [1], [2], etc. No heading."
    )
    cited_indices: list[int] = Field(
        description="Every source index that actually appears as [N] in the answer text, and nothing else. Empty list if none were cited."
    )
    coverage_gaps: str | None = Field(
        default=None,
        description="If the question touches areas not well covered by the retrieved articles, describe what's missing "
        "and end with 'Consider saving articles about: ...'. Null if coverage is sufficient to fully answer the question."
    )


def build_source_context(sources: list[dict]) -> str:
    """
    把 sources 拼成真正喂给 GPT 的那段文本 —— generate_answer 用它，
    eval 裁判(app/services/eval_service.py)也要用同一份，检查 faithfulness 时
    对照的必须是模型实际看到的这段（摘要优先，没有摘要才退化用正文前 500 字），
    而不是 sources 里那份没截断的完整 content，不然会误判。
    """
    context_parts = []
    for s in sources:
        text = s.get("ai_summary") or s.get("content", "")[:500]
        context_parts.append(f'[{s["index"]}] {s["title"]}\n{text}')
    return "\n\n".join(context_parts)


def generate_answer(question: str, sources: list[dict]) -> AnswerGeneration | None:
    """
    RAG 的 Generation 步骤：把检索到的文章作为上下文，让 GPT 生成结构化回答。

    sources: 每个元素是 {"index": 1, "title": ..., "ai_summary": ..., "content": ...}
    返回 AnswerGeneration：回答正文 / 实际引用的 source 编号 / 覆盖空白提示，三者都是独立字段。
    """
    if not sources:
        return None

    context = build_source_context(sources)

    system_prompt = """You are a helpful assistant for a personal knowledge base called Cairn.
The user has saved technical articles to their library. Answer their question using ONLY the provided articles.

Cite sources inline using [1], [2], etc. Only state what the articles actually say — never fabricate information.
cited_indices must exactly match every index that appears as [N] anywhere in the answer text, and nothing else —
this applies even when a citation is only used to describe what an off-topic article covers instead of directly
answering the question. If [N] appears in answer, N must be in cited_indices. No exceptions.

Example: if answer is "The articles don't cover AWS storage. They focus on Write-Ahead Logging [1] and
distributed locking [2] instead.", then cited_indices must be [1, 2] — NOT [].

Field boundaries — keep these strictly separate, never duplicate content across them:
- answer: only the substantive response built from the articles. If the articles don't cover the question, state
  that briefly, then briefly mention what the retrieved articles actually discuss instead — grounded only in their
  real content, with inline citations (e.g. "The articles don't cover AWS storage. They focus on Write-Ahead
  Logging [1] and distributed locking [2] instead."). Do not go further than that: the phrase "Consider saving
  articles about" and any list of missing/suggested topics must NEVER appear in answer — that content belongs
  exclusively in coverage_gaps.
- coverage_gaps: the ONLY field for describing what's missing and what to save. If the question touches areas NOT
  well covered by the retrieved articles, put the full explanation here — what's missing specifically, ending with
  "Consider saving articles about: [list the missing topics]". If coverage is sufficient to fully answer the
  question, leave coverage_gaps null.

Rules:
- IMPORTANT: Always respond in the same language as the user's question. English question → English answer. Chinese question → Chinese answer.
- Never make up information not present in the articles"""

    user_prompt = f"""Here are the retrieved articles from the user's library:

{context}

Question: {question}

Respond with your answer."""

    try:
        response = client.beta.chat.completions.parse(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format=AnswerGeneration,
            temperature=0.3,
        )
        return response.choices[0].message.parsed
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


# 异步处理函数,由 arq worker 调用(见 app/worker.py)
def process_article_in_background(article_id: int) -> None:
    """
    后台任务:分析文章并把结果写入数据库。

    这个函数会在新的数据库 session 里运行(因为请求的 session 在 return 时关闭了)。
    失败会往外抛异常——arq 的 worker 负责捕获并决定是否重试,这里不再吞掉异常。
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

        # 复用已有结果：同一 URL 若被其他用户完整处理过，直接拷贝，跳过 OpenAI 调用。
        # 注意：同时检查 ai_summary 和 embedding 都不为 None，避免复用一个半成品 donor。
        # 竞态说明：两个任务并发处理同一全新 URL 时，都会查不到 donor 并各自调一次
        # OpenAI——这不是数据错误，只是偶尔多花一次 API 调用，可接受。
        from app.models.tag import Tag
        donor = (
            db.query(Article)
            .filter(
                Article.url_hash == article.url_hash,
                Article.id != article.id,
                Article.ai_summary.isnot(None),
                Article.embedding.isnot(None),
            )
            .order_by(Article.created_at)  # 选最早处理完的，结果确定可预期
            .first()
        )

        if donor:
            article.ai_summary = donor.ai_summary
            article.embedding = donor.embedding
            article.tags = donor.tags
            article.status = "done"
            db.commit()
            logger.info(f"✅ Article {article_id} reused AI results from donor {donor.id}")
            return

        # 内容太短/缺失：本来就分析不出东西，不是失败，不需要重试
        if not article.content or len(article.content.strip()) < 100:
            article.status = "skipped"
            db.commit()
            logger.info(f"Article {article_id}: content too short, marking skipped")
            return

        # 标记为处理中：worker 若在这之后崩溃,能看到它死在了哪一步
        article.status = "processing"
        db.commit()

        # donor 不存在，走完整 AI 流程
        existing_tag_names = [t.name for t in db.query(Tag).all()]
        analysis = analyze_article(article.title, article.content, existing_tag_names)
        if not analysis:
            # OpenAI 调用失败是暂时性问题，往外抛让 arq 重试
            raise RuntimeError(f"AI analysis returned no result for article {article_id}")

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

        article.status = "done"
        db.commit()
        logger.info(f"✅ Background AI processing done for article {article_id}")

    except Exception as e:
        logger.exception(f"Background task error for article {article_id}: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def mark_article_failed(article_id: int) -> None:
    """
    把文章标记为永久失败。只在 status 还是 processing 时才改,
    避免和一个刚好并发完成的 done 状态互相覆盖。

    调用方:arq worker 在重试次数耗尽时(app/worker.py),
    以及定期巡检卡死任务的 reconcile_stuck_articles cron job。
    """
    from app.core.database import SessionLocal
    from app.models.article import Article

    db = SessionLocal()
    try:
        article = db.query(Article).filter(Article.id == article_id).first()
        if article and article.status == "processing":
            article.status = "failed"
            db.commit()
            logger.warning(f"Article {article_id} marked as failed")
    finally:
        db.close()