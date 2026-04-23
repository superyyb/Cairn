import logging

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.api import users, auth

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


app = FastAPI(title="ForkMark API", version="0.1.0")

# 注册路由
app.include_router(users.router)
app.include_router(auth.router)


# 全局异常处理:任何未捕获的异常都走这里
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled exception on {request.method} {request.url.path}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error. Please try again later."},
    )


@app.get("/")
def root():
    return {"message": "Hello ForkMark! 🍴"}


@app.get("/health")
def health():
    return {"status": "ok"}