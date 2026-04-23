"""安全相关工具:密码哈希、JWT(Day 5 会加)"""
from passlib.context import CryptContext


# bcrypt 上下文,deprecated="auto" 让旧哈希在新算法升级时自动迁移
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """把明文密码哈希成 bcrypt 字符串"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证明文密码是否匹配哈希值"""
    return pwd_context.verify(plain_password, hashed_password)