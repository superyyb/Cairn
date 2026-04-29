"""安全相关工具:密码哈希 + JWT"""
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User

# 密码哈希
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """把明文密码哈希成 bcrypt 字符串"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证明文密码是否匹配哈希值"""
    return pwd_context.verify(plain_password, hashed_password)


# JWT
def create_access_token(subject: str | int, expires_delta: timedelta | None = None) -> str:
    """
    生成 JWT access token。
    
    subject: 通常是 user_id,会写入 token 的 'sub' 字段。
    expires_delta: 自定义过期时间,默认用配置里的 ACCESS_TOKEN_EXPIRE_MINUTES。
    """
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.access_token_expire_minutes)
    
    expire = datetime.now(timezone.utc) + expires_delta
    
    payload = {
        "sub": str(subject),  # JWT 标准要求 sub 是字符串
        "exp": expire,        # 过期时间
    }
    
    encoded_jwt = jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt


def decode_access_token(token: str) -> dict | None:
    """
    解析 JWT token,返回 payload。
    如果 token 无效或过期,返回 None。
    """
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return payload
    except JWTError:
        return None


# 告诉 FastAPI:这个 API 用 OAuth2 鉴权，从 Authorization Header 拿 Bearer token
# tokenUrl 指向登录接口,这样 Swagger UI 能自动跳转登录
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    """
    解析 token 拿到当前用户。
    所有需要登录才能访问的接口,都用 Depends(get_current_user)。
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # 1. 解码 token
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception
    
    # 2. 从 payload 拿 user_id
    user_id_str = payload.get("sub")
    if user_id_str is None:
        raise credentials_exception
    
    try:
        user_id = int(user_id_str)
    except ValueError:
        raise credentials_exception
    
    # 3. 查数据库
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
    
    return user
