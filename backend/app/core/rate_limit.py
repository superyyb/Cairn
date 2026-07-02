"""Redis-backed rate limiting for API endpoints."""
import logging
import redis
from fastapi import Depends, HTTPException, Request, status

from app.core.config import settings
from app.core.security import get_current_user
from app.models.user import User

logger = logging.getLogger(__name__)

CHAT_LIMIT = 20         # questions per day
ARTICLE_LIMIT = 50      # saves per day
WINDOW_24H = 86400

LOGIN_LIMIT = 10        # attempts per 15 min
REFRESH_LIMIT = 20      # attempts per 15 min
WINDOW_15M = 900

_redis_client: redis.Redis | None = None


def get_redis() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    return _redis_client


def _check_limit(identifier: str | int, key: str, limit: int, label: str, window_sec: int = WINDOW_24H) -> None:
    r = get_redis()
    try:
        count = r.incr(key)
        if count == 1:
            r.expire(key, window_sec)
        if count > limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit reached: {limit} {label}.",
                headers={"Retry-After": str(window_sec)},
            )
    except redis.RedisError as e:
        logger.warning(f"Redis unavailable, rate limiting skipped for {identifier}: {e}")


def login_rate_limit(request: Request) -> None:
    ip = request.client.host if request.client else "unknown"
    _check_limit(ip, f"rate:login:{ip}", LOGIN_LIMIT, "login attempts per 15 minutes", WINDOW_15M)


def refresh_rate_limit(request: Request) -> None:
    ip = request.client.host if request.client else "unknown"
    _check_limit(ip, f"rate:refresh:{ip}", REFRESH_LIMIT, "refresh attempts per 15 minutes", WINDOW_15M)


def chat_rate_limit(current_user: User = Depends(get_current_user)) -> None:
    _check_limit(current_user.id, f"rate:chat:{current_user.id}", CHAT_LIMIT, "questions per day")


def article_rate_limit(current_user: User = Depends(get_current_user)) -> None:
    _check_limit(current_user.id, f"rate:article:{current_user.id}", ARTICLE_LIMIT, "article saves per day")
