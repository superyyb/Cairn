"""用户模型"""
from datetime import datetime

from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    username: Mapped[str] = mapped_column(String(100), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    chat_sessions = relationship("ChatSession", back_populates="user")
    refresh_tokens = relationship("RefreshToken", back_populates="user")

    def __repr__(self):
        return f"<User {self.email}>"