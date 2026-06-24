"""文章相关的 Pydantic schemas"""
from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl


# ===== 输入 schemas(客户端 → 服务端)=====

class ArticleCreate(BaseModel):
    """
    Chrome 插件抓取后发来的数据。
    字段名要和 Day 9 content.js 里 extractArticle() 返回的 keys 对齐。
    """
    url: HttpUrl  # Pydantic 自动验证是合法 URL
    title: str = Field(min_length=1, max_length=500)
    content: str | None = Field(default=None, description="Article body (plain text)")
    excerpt: str | None = Field(default=None, max_length=2000)
    byline: str | None = Field(default=None, max_length=200)
    site_name: str | None = Field(default=None, max_length=200)
    lang: str | None = Field(default=None, max_length=10)
    length: int | None = None
    
    # Pydantic 会忽略 schema 里没定义的字段(默认行为),所以
    # 即使 Chrome 插件多发了 contentHtml / publishedTime 等字段,这里也不会报错。


# ===== 输出 schemas(服务端 → 客户端)=====

class TagOut(BaseModel):
    """标签的简化输出"""
    id: int
    name: str
    
    model_config = {"from_attributes": True}


class ArticleResponse(BaseModel):
    """单篇文章的完整响应"""
    id: int
    url: str  # 注意:输出时是 str,不是 HttpUrl(避免序列化问题)
    title: str
    excerpt: str | None
    byline: str | None
    site_name: str | None
    lang: str | None
    length: int | None
    ai_summary: str | None
    is_starred: bool = False
    tags: list[TagOut] = []
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


class ArticleSaveResult(BaseModel):
    """
    保存接口的响应:除了文章信息,还告诉前端"是新的还是已有的"。
    这是好的 API 设计:让客户端知道发生了什么。
    """
    article: ArticleResponse
    is_new: bool  # True = 第一次保存,False = 数据库里已经有了
    message: str