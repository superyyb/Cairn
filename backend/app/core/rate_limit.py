"""Redis-backed rate limiting for LLM endpoints."""
import logging
import redis
from fastapi import Depends, HTTPException, Request, status

from app.core.config import settings
from app.core.security import get_current_user
from app.models.user import User

logger = logging.getLogger(__name__)

CHAT_LIMIT = 20      # questions per day
ARTICLE_LIMIT = 50   # saves per day
WINDOW_SEC = 86400   # 24 hours

LOGIN_LIMIT = 10     # attempts per window
LOGIN_WINDOW_SEC = 900  # 15 minutes

_redis_client: redis.Redis | None = None


def get_redis() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    return _redis_client


def _check_limit(user_id: int, key: str, limit: int, label: str) -> None:
    r = get_redis()
    try:
        count = r.incr(key)
        if count == 1:
            r.expire(key, WINDOW_SEC)
        if count > limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Daily limit reached: {limit} {label} per day.",
                headers={"Retry-After": str(WINDOW_SEC)},
            )
    except redis.RedisError as e:
        # Fail-open: allow request through, but log so we know Redis is down
        logger.warning(f"Redis unavailable, rate limiting skipped for user {user_id}: {e}")


def login_rate_limit(request: Request) -> None:
    ip = request.client.host if request.client else "unknown"
    _check_limit(ip, f"rate:login:{ip}", LOGIN_LIMIT, "login attempts")


def chat_rate_limit(current_user: User = Depends(get_current_user)) -> None:
    _check_limit(current_user.id, f"rate:chat:{current_user.id}", CHAT_LIMIT, "questions")


def article_rate_limit(current_user: User = Depends(get_current_user)) -> None:
    _check_limit(current_user.id, f"rate:article:{current_user.id}", ARTICLE_LIMIT, "articles")
