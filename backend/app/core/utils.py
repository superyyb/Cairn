"""通用工具函数"""
import hashlib
from datetime import datetime, timezone
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


def utc_now() -> datetime:
    """
    当前 UTC 时间,返回 naive datetime(不带 tzinfo)。

    数据库里所有时间列都是不带时区的 timestamp,全仓库也统一用 naive 时间比较/存储。
    `datetime.utcnow()` 在 Python 3.12 起被弃用,但直接换成 `datetime.now(timezone.utc)`
    会返回 aware datetime——存进 naive 列时,psycopg 可能按会话时区悄悄转换、
    和其他 naive 时间比较时也会直接报 TypeError。这里用 `.replace(tzinfo=None)`
    去掉 tzinfo,保持和原来 `utcnow()` 完全一样的行为,只是换个不会被弃用的写法。
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)

# 常见追踪参数,参考 AdGuard / uBlock Origin 的 tracking-param 规则摘取,
# 不是我们自己发明的清单——新的追踪参数出现时,加一行就行。
TRACKING_PARAMS = frozenset({
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "utm_id",
    "gclid", "gclsrc", "dclid",
    "fbclid", "fb_action_ids", "fb_action_types", "fb_ref",
    "mc_cid", "mc_eid",
    "igshid",
    "ref", "ref_src", "ref_url",
    "si",  # YouTube 分享链接
    "spm", "scm",  # 淘宝系
    "vero_id",
    "yclid",
    "msclkid",
})

_DEFAULT_PORTS = {"http": 80, "https": 443}


def normalize_url(url: str) -> str:
    """
    归一化 URL,用于去重哈希:
    - scheme / host 转小写
    - 去掉默认端口(:80 / :443)
    - path 末尾多余的斜杠去掉(根路径保留 "/")
    - 剔除已知追踪参数,剩余 query 参数按 key 排序(避免参数顺序不同判成两个 URL)

    注意:fragment(# 后面的部分)原样保留,不做任何处理。
    GitHub 评论(#issuecomment-xxx)、Stack Overflow 答案(#answer-xxx)这类场景里,
    fragment 是具体资源的身份标识,不是纯页内锚点——剔除会把不同的评论/答案误判成同一篇文章。
    """
    parts = urlsplit(url)

    scheme = parts.scheme.lower()
    hostname = (parts.hostname or "").lower()
    port = parts.port
    if port == _DEFAULT_PORTS.get(scheme):
        port = None
    netloc = hostname + (f":{port}" if port else "")

    path = parts.path
    if len(path) > 1 and path.endswith("/"):
        path = path.rstrip("/")

    query_pairs = sorted(
        (k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
        if k not in TRACKING_PARAMS
    )
    query = urlencode(query_pairs)

    return urlunsplit((scheme, netloc, path, query, parts.fragment))


def hash_url(url: str) -> str:
    """
    把归一化后的 URL 哈希成 64 位十六进制字符串(SHA-256)。
    用于数据库 unique 索引去重。
    """
    return hashlib.sha256(normalize_url(url).encode("utf-8")).hexdigest()