"""安全相关工具:密码哈希 + JWT"""
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings


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