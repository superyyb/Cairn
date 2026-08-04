"""add_chat_feedback_table

Revision ID: 7dfd75dcb949
Revises: bf63dba8dbbf
Create Date: 2026-08-04 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7dfd75dcb949'
down_revision: Union[str, Sequence[str], None] = 'bf63dba8dbbf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "chat_feedback",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "chat_session_id",
            sa.Integer(),
            sa.ForeignKey("chat_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("rating", sa.Boolean(), nullable=False),
        sa.Column("reason", sa.String(50), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("reviewed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_chat_feedback_chat_session_id", "chat_feedback", ["chat_session_id"], unique=True)
    op.create_index("ix_chat_feedback_user_id", "chat_feedback", ["user_id"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_chat_feedback_user_id", table_name="chat_feedback")
    op.drop_index("ix_chat_feedback_chat_session_id", table_name="chat_feedback")
    op.drop_table("chat_feedback")
