"""鉴权相关的 Pydantic schemas"""
from pydantic import BaseModel


class Token(BaseModel):
    """登录成功后返回的 token"""
    access_token: str
    token_type: str = "bearer"