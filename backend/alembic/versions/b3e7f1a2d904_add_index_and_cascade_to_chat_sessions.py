"""add index and cascade to chat_sessions

Revision ID: b3e7f1a2d904
Revises: 9e285665e775
Create Date: 2026-06-30 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b3e7f1a2d904'
down_revision: Union[str, Sequence[str], None] = '9e285665e775'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add composite index for the common history query:
    # SELECT * FROM chat_sessions WHERE user_id = ? ORDER BY created_at DESC
    op.create_index(
        'ix_chat_sessions_user_id_created_at',
        'chat_sessions',
        ['user_id', sa.text('created_at DESC')],
        postgresql_using='btree',
    )

    # Fix FK to cascade on user deletion so no orphaned chat records
    op.drop_constraint('chat_sessions_user_id_fkey', 'chat_sessions', type_='foreignkey')
    op.create_foreign_key(
        'chat_sessions_user_id_fkey',
        'chat_sessions', 'users',
        ['user_id'], ['id'],
        ondelete='CASCADE',
    )


def downgrade() -> None:
    op.drop_constraint('chat_sessions_user_id_fkey', 'chat_sessions', type_='foreignkey')
    op.create_foreign_key(
        'chat_sessions_user_id_fkey',
        'chat_sessions', 'users',
        ['user_id'], ['id'],
    )

    op.drop_index('ix_chat_sessions_user_id_created_at', table_name='chat_sessions')
