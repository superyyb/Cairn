"""_check_limit 是所有 *_rate_limit 依赖共用的核心逻辑:超限要挡、Redis 挂了要放行(fail open)。"""
import redis
import pytest
from fastapi import HTTPException

from app.core import rate_limit


def test_check_limit_blocks_once_over_threshold():
    key = "rate:test:blocks"
    for _ in range(3):
        rate_limit._check_limit("id", key, limit=3, label="test actions", window_sec=60)

    with pytest.raises(HTTPException) as exc_info:
        rate_limit._check_limit("id", key, limit=3, label="test actions", window_sec=60)
    assert exc_info.value.status_code == 429


def test_check_limit_fails_open_when_redis_unavailable(monkeypatch):
    class BrokenRedis:
        def incr(self, key):
            raise redis.RedisError("connection refused")

    monkeypatch.setattr(rate_limit, "get_redis", lambda: BrokenRedis())

    # Redis 挂了不该把用户挡在外面 —— 不抛异常就是通过
    rate_limit._check_limit("id", "rate:test:down", limit=1, label="test actions")
