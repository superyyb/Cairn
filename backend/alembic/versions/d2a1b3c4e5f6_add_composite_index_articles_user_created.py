"""add composite index on articles(user_id, created_at DESC)

Revision ID: d2a1b3c4e5f6
Revises: c9d4e8f2a531
Create Date: 2026-06-30 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd2a1b3c4e5f6'
down_revision: Union[str, Sequence[str], None] = 'c9d4e8f2a531'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        'ix_articles_user_id_created_at',
        'articles',
        ['user_id', sa.text('created_at DESC')],
        postgresql_using='btree',
    )


def downgrade() -> None:
    op.drop_index('ix_articles_user_id_created_at', table_name='articles')
