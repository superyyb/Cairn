"""定期清理过期和已吊销的 refresh token"""
import asyncio
import logging
from datetime import timedelta

from app.core.database import SessionLocal
from app.core.utils import utc_now
from app.models.refresh_token import RefreshToken

logger = logging.getLogger(__name__)

REVOKED_RETAIN_DAYS = 7  # 已吊销的 token 保留 7 天后删除


async def cleanup_refresh_tokens() -> None:
    while True:
        await asyncio.sleep(3600)  # 每小时执行一次
        try:
            db = SessionLocal()
            try:
                revoked_cutoff = utc_now() - timedelta(days=REVOKED_RETAIN_DAYS)
                deleted = (
                    db.query(RefreshToken)
                    .filter(
                        (RefreshToken.expires_at < utc_now())
                        | (RefreshToken.revoked_at < revoked_cutoff)
                    )
                    .delete(synchronize_session=False)
                )
                db.commit()
                if deleted:
                    logger.info(f"Cleaned up {deleted} expired/revoked refresh tokens")
            finally:
                db.close()
        except Exception:
            logger.exception("Refresh token cleanup failed")
