"""用户对某次 RAG 回答的评价（👍/👎）"""
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.utils import utc_now


class ChatFeedback(Base):
    """
    一个 chat_session 对应最多一条反馈（unique chat_session_id），改评价是 upsert 更新同一行。

    reason 是纯 String，不建 DB enum，取值只在 Pydantic 里用 Literal 校验，
    跟 EvalQuestion.category 的做法一致，以后加新分类不用迁移。
    reviewed 给 replay_feedback.py 用，标记这条负反馈是否已经跑过裁判回放。
    """
    __tablename__ = "chat_feedback"

    id: Mapped[int] = mapped_column(primary_key=True)
    chat_session_id: Mapped[int] = mapped_column(
        ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    rating: Mapped[bool] = mapped_column(Boolean, nullable=False)  # True=👍 False=👎
    reason: Mapped[str | None] = mapped_column(String(50), nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(default=utc_now, onupdate=utc_now)

    def __repr__(self):
        return f"<ChatFeedback session={self.chat_session_id} rating={self.rating}>"
