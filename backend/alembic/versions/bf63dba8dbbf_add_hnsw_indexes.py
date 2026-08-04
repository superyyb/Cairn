"""add_hnsw_indexes

Revision ID: bf63dba8dbbf
Revises: 68df44a9a0ec
Create Date: 2026-07-30 22:26:09.621373

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bf63dba8dbbf'
down_revision: Union[str, Sequence[str], None] = '68df44a9a0ec'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # CREATE INDEX CONCURRENTLY 不能跑在事务里，Alembic 默认会把整个 migration
    # 包进一个事务，所以这里要用 autocommit_block() 跳出事务边界。
    # articles.embedding 曾经有过这个索引，被后来一次迁移的 autogenerate 误删了，
    # tags.embedding 是新加的——_resolve_tag 的语义去重查询同样在做余弦相似度检索。
    with op.get_context().autocommit_block():
        op.create_index(
            "articles_embedding_idx",
            "articles",
            ["embedding"],
            unique=False,
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
            postgresql_concurrently=True,
        )
        op.create_index(
            "tags_embedding_idx",
            "tags",
            ["embedding"],
            unique=False,
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
            postgresql_concurrently=True,
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.get_context().autocommit_block():
        op.drop_index("tags_embedding_idx", table_name="tags", postgresql_concurrently=True)
        op.drop_index("articles_embedding_idx", table_name="articles", postgresql_concurrently=True)
