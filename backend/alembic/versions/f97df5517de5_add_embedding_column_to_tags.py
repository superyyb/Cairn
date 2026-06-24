"""add embedding column to tags

Revision ID: f97df5517de5
Revises: fea88ff7f0a2
Create Date: 2026-05-14 11:43:04.304892

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision: str = 'f97df5517de5'
down_revision: Union[str, Sequence[str], None] = 'fea88ff7f0a2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('tags', sa.Column('embedding', Vector(1536), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('tags', 'embedding')
