"""文章相关 API"""
import asyncio
import logging

from arq.connections import ArqRedis
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.arq_pool import get_arq_pool
from app.core.database import get_db
from app.core.rate_limit import article_rate_limit
from app.core.security import get_current_user
from app.core.utils import hash_url
from app.models.article import Article
from app.models.tag import Tag
from app.models.user import User
from app.schemas.article import ArticleCreate, ArticleResponse, ArticleSaveResult, StarPayload

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/articles", tags=["articles"])


@router.post(
    "",
    response_model=ArticleSaveResult,
    status_code=status.HTTP_200_OK,
    summary="Save an article (AI analysis runs asynchronously in background)",
)
async def save_article(
    payload: ArticleCreate,
    current_user: User = Depends(get_current_user),
    _: None = Depends(article_rate_limit),
    db: Session = Depends(get_db),
    arq_pool: ArqRedis = Depends(get_arq_pool),
):
    """
    接收 Chrome 插件的抓取结果,立刻保存并返回。
    AI 摘要和标签会通过 arq 任务队列异步生成,稍后刷新即可看到。
    """
    url_str = str(payload.url)
    url_hash = hash_url(url_str)

    def _save_sync() -> tuple[Article, bool]:
        """
        同步的 DB 读写逻辑(查重 + insert + commit + refresh)。
        这个端点是 async def(要 await arq enqueue),但 SQLAlchemy 的
        Session 是同步的——放进 asyncio.to_thread 里跑,不让它挡住事件循环。
        """
        # 1. 检查是否已保存
        existing = (
            db.query(Article)
            .filter(
                Article.user_id == current_user.id,
                Article.url_hash == url_hash,
            )
            .first()
        )
        if existing:
            return existing, False

        # 2. 立刻保存(不等 AI)
        new_article = Article(
            user_id=current_user.id,
            url=url_str,
            url_hash=url_hash,
            title=payload.title,
            content=payload.content,
            excerpt=payload.excerpt,
            byline=payload.byline,
            site_name=payload.site_name,
            lang=payload.lang,
            length=payload.length,
            # ai_summary 留空,后台任务负责填写
        )
        try:
            db.add(new_article)
            db.commit()
            db.refresh(new_article)
        except IntegrityError:
            db.rollback()
            existing = (
                db.query(Article)
                .filter(Article.user_id == current_user.id, Article.url_hash == url_hash)
                .first()
            )
            return existing, False

        return new_article, True

    article, is_new = await asyncio.to_thread(_save_sync)

    if not is_new:
        return ArticleSaveResult(
            article=ArticleResponse.model_validate(article),
            is_new=False,
            message="You've already saved this article.",
        )

    # 3. 提交到 arq 队列(HTTP 响应返回之后由 worker 处理)
    #    只传 article_id(纯数据),worker 自己开新的 db session
    try:
        await asyncio.wait_for(
            arq_pool.enqueue_job(
                "process_article_task",
                article.id,
                _job_id=f"article-{article.id}",
            ),
            timeout=2.0,
        )
        logger.info(f"Article {article.id} saved, AI processing enqueued")
    except (Exception, asyncio.TimeoutError) as e:
        # Redis 不可用时不能让整个请求失败——文章已经存好了,
        # 停在 status="pending",以后可以手动/巡检重新入队。
        logger.error(f"Failed to enqueue AI processing for article {article.id}: {e}")

    return ArticleSaveResult(
        article=ArticleResponse.model_validate(article),
        is_new=True,
        message="Article saved! AI analysis is running in the background.",
    )


@router.get(
    "",
    response_model=list[ArticleResponse],
    summary="Get my article list",
)
def list_my_articles(
    skip: int = 0,
    limit: int = 500,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if limit > 500:
        limit = 500

    articles = (
        db.query(Article)
        .options(selectinload(Article.tags))
        .filter(Article.user_id == current_user.id)
        .order_by(Article.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return articles


@router.get(
    "/{article_id}",
    response_model=ArticleResponse,
    summary="Get article detail by ID",
)
def get_article(
    article_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    获取一篇文章的完整内容(包括最新的 AI 摘要和标签)。

    只能获取当前登录用户自己保存的文章,
    访问别人的文章会返回 404(避免暴露文章是否存在)。
    """
    article = (
        db.query(Article)
        .options(selectinload(Article.tags))
        .filter(
            Article.id == article_id,
            Article.user_id == current_user.id,
        )
        .first()
    )

    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Article not found",
        )

    return article


@router.patch(
    "/{article_id}/star",
    response_model=ArticleResponse,
    summary="Set star state on an article",
)
def set_star(
    article_id: int,
    payload: StarPayload,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    article = db.query(Article).filter(
        Article.id == article_id,
        Article.user_id == current_user.id,
    ).first()
    if not article:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")
    article.is_starred = payload.is_starred
    db.commit()
    db.refresh(article)
    return article


@router.delete(
    "/{article_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an article",
)
def delete_article(
    article_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    article = (
        db.query(Article)
        .filter(
            Article.id == article_id,
            Article.user_id == current_user.id,
        )
        .first()
    )

    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Article not found",
        )

    db.delete(article)
    db.commit()
    logger.info(f"Article {article_id} deleted by user {current_user.id}")