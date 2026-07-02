"""鉴权相关的 Pydantic schemas"""
from pydantic import BaseModel


class Token(BaseModel):
    """Web 登录/刷新响应 — refresh token 在 httpOnly cookie 里，不在 body"""
    access_token: str
    token_type: str = "bearer"


class TokenWithRefresh(BaseModel):
    """Extension 登录/刷新响应 — refresh token 在 body 里（extension 无法使用 httpOnly cookie）"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    """Extension 发送 refresh token 时的请求体"""
    refresh_token: str
