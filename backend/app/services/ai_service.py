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
        description="3 to 5 lowercase technical tags (e.g. 'kubernetes', 'distributed systems', 'rust'). No spaces in single-word tags."
    )


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
    existing_tags_line = ""
    if existing_tags:
        existing_tags_line = f"\nExisting tags in the library: {', '.join(existing_tags)}\nReuse an existing tag when it fits. Only create a new tag if the concept is genuinely not covered.\n"

    system_prompt = f"""You are a technical content analyst.
Given a technical article, you produce:
1. A concise summary (1-2 sentences) capturing the core idea
2. 3-5 relevant lowercase tags for categorization
{existing_tags_line}
Tags should be technologies, concepts, or topics — not generic words.
Examples of good tags: "kubernetes", "rust", "distributed-systems", "rag", "react"
Examples of bad tags: "tutorial", "interesting", "important"

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
        ][:5]  # 最多 5 个,防止 LLM 不听话
        
        logger.info(f"AI analyzed: '{title[:50]}' → tags={result.tags}")
        return result
        
    except Exception as e:
        # 失败不抛异常,记日志返回 None,让用户先看到没 AI 的版本
        logger.error(f"OpenAI API error: {e}")
        return None

# 异步处理函数(Day 13)
def process_article_in_background(article_id: int) -> None:
    """
    后台任务:分析文章并把结果写入数据库。
    
    这个函数会在新的数据库 session 里运行(因为请求的 session 在 return 时关闭了)。
    任何异常都不能往外抛,只记日志(后台任务异常没人接)。
    """
    from app.core.database import SessionLocal
    from app.models.article import Article
    from app.models.tag import Tag
    
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
        
        # 查库里已有的所有标签,传给 AI 做归一化参考
        existing_tags = [t.name for t in db.query(Tag).all()]

        # 调 AI
        analysis = analyze_article(article.title, article.content, existing_tags)
        if not analysis:
            logger.warning(f"Background task: AI analysis failed for article {article_id}")
            return
        
        # 写入摘要
        article.ai_summary = analysis.summary
        
        # 处理标签
        for tag_name in analysis.tags:
            tag = db.query(Tag).filter(Tag.name == tag_name).first()
            if not tag:
                tag = Tag(name=tag_name)
                db.add(tag)
                db.flush()
            article.tags.append(tag)
        
        db.commit()
        logger.info(f"✅ Background AI processing done for article {article_id}")
        
    except Exception as e:
        logger.exception(f"Background task error for article {article_id}: {e}")
        db.rollback()
    finally:
        db.close()