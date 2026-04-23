"""用户相关的 Pydantic schemas —— 用于 API 输入输出验证"""
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


# ===== 输入 schemas(客户端 → 服务端)=====
class UserCreate(BaseModel):
    """注册接口的请求体"""
    email: EmailStr  # 自动验证邮箱格式
    password: str = Field(min_length=8, max_length=100, description="At least 8 digits")
    username: str = Field(min_length=1, max_length=100)


# ===== 输出 schemas(服务端 → 客户端)=====
class UserResponse(BaseModel):
    """返回用户信息时用的 schema —— 注意不包含 password_hash!"""
    id: int
    email: str
    username: str
    created_at: datetime

    model_config = {"from_attributes": True}
    # ↑ 这一行让 Pydantic 能从 SQLAlchemy 对象自动转换