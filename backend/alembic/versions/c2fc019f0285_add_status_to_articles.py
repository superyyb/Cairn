"""add_status_to_articles

Revision ID: c2fc019f0285
Revises: a1b2c3d4e5f6
Create Date: 2026-07-25 11:24:16.264692

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c2fc019f0285'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "articles",
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
    )
    op.create_index("ix_articles_status", "articles", ["status"])
    # 迁移前已存在的文章：旧的 BackgroundTasks 机制已经不存在了，不会再有任何东西
    # 去补跑它们。有 ai_summary 的算正常处理完成；没有的说明处理已经永久终止，
    # 标成 failed 让它可见，而不是继续悄悄地卡着。
    op.execute("UPDATE articles SET status = 'done' WHERE ai_summary IS NOT NULL")
    op.execute("UPDATE articles SET status = 'failed' WHERE ai_summary IS NULL")


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_articles_status", table_name="articles")
    op.drop_column("articles", "status")
