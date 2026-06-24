"""标签模型"""
from typing import Optional
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector

from app.core.database import Base
from app.models.article import article_tags  # 导入中间表


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    embedding: Mapped[Optional[list[float]]] = mapped_column(Vector(1536), nullable=True)
    
    # ORM 关系:关联文章(多对多)
    articles: Mapped[list["Article"]] = relationship(
        secondary=article_tags,
        back_populates="tags",
    )
    
    def __repr__(self):
        return f"<Tag {self.name}>"