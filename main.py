from fastapi import FastAPI

from app.api import users

app = FastAPI(title="ForkMark API", version="0.1.0")

# 注册路由
app.include_router(users.router)

@app.get("/")
def root():
    return {"message": "Hello ForkMark! 🍴"}


@app.get("/health")
def health():
    return {"status": "ok"}