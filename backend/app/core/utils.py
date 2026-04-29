"""通用工具函数"""
import hashlib


def hash_url(url: str) -> str:
    """
    把 URL 哈希成 64 位十六进制字符串(SHA-256)。
    用于数据库 unique 索引去重。
    """
    return hashlib.sha256(url.encode("utf-8")).hexdigest()