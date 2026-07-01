"""文章模型"""
from datetime import datetime

from sqlalchemy import String, Text, Integer, DateTime, ForeignKey, Table, Column, Boolean, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from pgvector.sqlalchemy import Vector


# 中间表:文章 ↔ 标签 多对多关联
# 注意:这里用 Table 而不是 class,因为中间表不需要 ORM 模型
article_tags = Table(
    "article_tags",
    Base.metadata,
    Column("article_id", Integer, ForeignKey("articles.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class Article(Base):
    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    
    # 所属用户(外键,Week 5 加团队再改)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    
    # 文章内容
    url: Mapped[str] = mapped_column(String(2000), nullable=False)
    url_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)  # URL 去重用
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=True)  # 正文可能很长,用 Text
    excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)  # Readability 自带的短摘要
    
    # 元数据
    byline: Mapped[str | None] = mapped_column(String(200), nullable=True)  # 作者
    site_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    lang: Mapped[str | None] = mapped_column(String(10), nullable=True)
    length: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 字符数
    
    # 用户操作
    is_starred: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # AI 生成
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    embedding: Mapped[list[float] | None] = mapped_column(
    Vector(1536), nullable=True
)
    
    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=datetime.utcnow, 
        onupdate=datetime.utcnow,
        nullable=False,
    )
    
    # ORM 关系:关联标签(多对多)
    tags: Mapped[list["Tag"]] = relationship(
        secondary=article_tags,
        back_populates="articles",
    )
    
    __table_args__ = (
        UniqueConstraint('user_id', 'url_hash', name='uk_articles_user_url'),
    )

    def __repr__(self):
        return f"<Article {self.id} - {self.title[:30]}>"