"""add unique constraint on articles(user_id, url_hash)

Revision ID: c9d4e8f2a531
Revises: b3e7f1a2d904
Create Date: 2026-06-30 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = 'c9d4e8f2a531'
down_revision: Union[str, Sequence[str], None] = 'b3e7f1a2d904'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint(
        'uk_articles_user_url',
        'articles',
        ['user_id', 'url_hash'],
    )


def downgrade() -> None:
    op.drop_constraint('uk_articles_user_url', 'articles', type_='unique')
