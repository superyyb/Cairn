"""arq worker 入口:定义后台任务和 WorkerSettings。

运行方式:uv run arq app.worker.WorkerSettings
"""
import asyncio
import logging
from datetime import timedelta

from arq import Retry, cron
from arq.connections import RedisSettings

import app.models  # noqa: F401 — registers all ORM models before mapper resolves relationships
from app.core.config import settings
from app.core.utils import utc_now
from app.services.ai_service import mark_article_failed, process_article_in_background

logger = logging.getLogger(__name__)

MAX_TRIES = 3            # 保持和 WorkerSettings.max_tries 一致
JOB_TIMEOUT_SECONDS = 60  # OpenAI 调用正常几秒内完成,给足余量


async def process_article_task(ctx, article_id: int) -> None:
    """
    arq 任务入口。process_article_in_background 本身是同步函数(同步 SQLAlchemy
    + 同步 OpenAI 客户端),用 asyncio.to_thread 包一层,避免为了接入 arq
    去重写 ai_service.py 里那套同步逻辑。
    """
    job_try = ctx.get("job_try", 1)
    try:
        await asyncio.to_thread(process_article_in_background, article_id)
    except Exception as exc:
        logger.warning(
            f"process_article_task failed for article {article_id} "
            f"(try {job_try}/{MAX_TRIES}): {exc}"
        )
        if job_try >= MAX_TRIES:
            # 最后一次允许的尝试也失败了:arq 不会再调用这个函数,
            # 所以由我们自己把终态记下来。
            await asyncio.to_thread(mark_article_failed, article_id)
            raise
        raise Retry(defer=min(2 ** job_try, 30))


def _reconcile_stuck_articles_sync() -> list[int]:
    from app.core.database import SessionLocal
    from app.models.article import Article

    threshold = utc_now() - timedelta(seconds=JOB_TIMEOUT_SECONDS * 3)
    db = SessionLocal()
    try:
        stuck_ids = [
            row.id
            for row in db.query(Article.id)
            .filter(Article.status == "processing", Article.updated_at < threshold)
            .all()
        ]
    finally:
        db.close()

    for article_id in stuck_ids:
        mark_article_failed(article_id)

    return stuck_ids


async def reconcile_stuck_articles(ctx) -> None:
    """
    兜底巡检:处理"worker 恰好在最后一次重试执行到一半被杀掉"这种边界情况。
    那种情况下 arq 自己的重试次数预检查会在我们的代码跑起来之前就短路掉,
    process_article_task 永远不会再被调用,status 会卡在 processing 出不来。
    这里定期扫一遍卡太久的文章,直接标 failed。

    查询 + mark_article_failed 都是同步 SQLAlchemy 调用,和 process_article_task
    一样丢进 asyncio.to_thread,避免这个 cron job 挡住 arq 的事件循环。
    """
    stuck_ids = await asyncio.to_thread(_reconcile_stuck_articles_sync)

    if stuck_ids:
        logger.warning(f"Reconciled {len(stuck_ids)} stuck article(s): {stuck_ids}")


class WorkerSettings:
    functions = [process_article_task]
    cron_jobs = [
        cron(reconcile_stuck_articles, minute=set(range(0, 60, 5))),  # 每 5 分钟跑一次
    ]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    max_tries = MAX_TRIES
    job_timeout = JOB_TIMEOUT_SECONDS
