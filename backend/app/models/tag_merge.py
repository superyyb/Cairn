"""Tag 合并记录"""
from datetime import datetime, timezone
from sqlalchemy import String, Float, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class TagMerge(Base):
    __tablename__ = "tag_merges"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    from_name: Mapped[str] = mapped_column(String(100), nullable=False)
    to_id: Mapped[int] = mapped_column(ForeignKey("tags.id", ondelete="CASCADE"), nullable=False)
    distance: Mapped[float] = mapped_column(Float, nullable=False)
    merged_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        nullable=False,
    )

    to_tag: Mapped["Tag"] = relationship("Tag")

    def __repr__(self):
        return f"<TagMerge '{self.from_name}' → tag_id={self.to_id} dist={self.distance:.3f}>"
