"""Redis-backed rate limiting for LLM endpoints."""
import redis
from fastapi import Depends, HTTPException, status

from app.core.config import settings
from app.core.security import get_current_user
from app.models.user import User

CHAT_LIMIT = 20      # questions per day
ARTICLE_LIMIT = 50   # saves per day
WINDOW_SEC = 86400   # 24 hours

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
    except redis.RedisError:
        pass


def chat_rate_limit(current_user: User = Depends(get_current_user)) -> User:
    _check_limit(current_user.id, f"rate:chat:{current_user.id}", CHAT_LIMIT, "questions")
    return current_user


def article_rate_limit(current_user: User = Depends(get_current_user)) -> User:
    _check_limit(current_user.id, f"rate:article:{current_user.id}", ARTICLE_LIMIT, "articles")
    return current_user
