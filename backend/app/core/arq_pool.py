"""FastAPI 依赖注入:获取 arq 的 Redis 连接池。

连接池本身在 main.py 的 lifespan 里创建一次(绑定到 uvicorn 的事件循环),
这里只是读取,不重新创建——ArqRedis 的连接是绑定在创建它时所在的事件循环上的。
"""
from arq.connections import ArqRedis
from fastapi import Request


def get_arq_pool(request: Request) -> ArqRedis:
    return request.app.state.arq_pool
