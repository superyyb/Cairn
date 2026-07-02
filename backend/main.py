import logging

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
import app.models  # noqa: F401 — registers all ORM models before mapper resolves relationships
from app.api import users, auth, articles, chat
from app.core.config import settings
from fastapi.middleware.cors import CORSMiddleware

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


app = FastAPI(title="Cairn API", version="0.2.0")
# 开发环境允许所有来源(Week 6 部署时再收紧)
_origins = [o.strip() for o in settings.allowed_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(users.router)
app.include_router(auth.router)
app.include_router(articles.router)
app.include_router(chat.router)


# 全局异常处理:任何未捕获的异常都走这里
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # ⚠️ 关键:HTTPException 让 FastAPI 自己处理,我们只兜底真正的未捕获异常
    if isinstance(exc, (HTTPException, StarletteHTTPException)):
        raise exc
    logger.exception(f"Unhandled exception on {request.method} {request.url.path}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error. Please try again later."},
    )


@app.get("/")
def root():
    return {"message": "Hello Cairn! 🍴"}


@app.get("/health")
def health():
    return {"status": "ok"}