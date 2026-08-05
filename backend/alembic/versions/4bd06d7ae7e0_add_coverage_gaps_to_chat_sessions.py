"""add coverage_gaps to chat_sessions

Revision ID: 4bd06d7ae7e0
Revises: 7dfd75dcb949
Create Date: 2026-08-05 13:42:14.126102

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4bd06d7ae7e0'
down_revision: Union[str, Sequence[str], None] = '7dfd75dcb949'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('chat_sessions', sa.Column('coverage_gaps', sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('chat_sessions', 'coverage_gaps')
