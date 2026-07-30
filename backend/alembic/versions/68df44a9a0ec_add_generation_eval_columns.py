"""add_generation_eval_columns

Revision ID: 68df44a9a0ec
Revises: 0f2e6f86d3d9
Create Date: 2026-07-30 14:14:43.925645

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '68df44a9a0ec'
down_revision: Union[str, Sequence[str], None] = '0f2e6f86d3d9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("eval_results", sa.Column("generated_answer", sa.Text(), nullable=True))
    op.add_column("eval_results", sa.Column("faithfulness_score", sa.Float(), nullable=True))
    op.add_column(
        "eval_results",
        sa.Column("unsupported_claims_json", sa.Text(), nullable=False, server_default="[]"),
    )
    op.add_column("eval_results", sa.Column("answer_relevancy_score", sa.Float(), nullable=True))
    op.add_column("eval_results", sa.Column("judge_model", sa.String(50), nullable=True))
    op.add_column("eval_results", sa.Column("judge_reasoning", sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("eval_results", "judge_reasoning")
    op.drop_column("eval_results", "judge_model")
    op.drop_column("eval_results", "answer_relevancy_score")
    op.drop_column("eval_results", "unsupported_claims_json")
    op.drop_column("eval_results", "faithfulness_score")
    op.drop_column("eval_results", "generated_answer")
