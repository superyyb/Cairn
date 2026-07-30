"""add_eval_tables

Revision ID: 0f2e6f86d3d9
Revises: c2fc019f0285
Create Date: 2026-07-30 13:43:28.974354

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0f2e6f86d3d9'
down_revision: Union[str, Sequence[str], None] = 'c2fc019f0285'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "eval_questions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("category", sa.String(20), nullable=False),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("expected_article_ids_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column(
            "source_article_id",
            sa.Integer(),
            sa.ForeignKey("articles.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("external_id", sa.String(50), nullable=True, unique=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "eval_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "eval_user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("config_snapshot_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_eval_runs_eval_user_id", "eval_runs", ["eval_user_id"])

    op.create_table(
        "eval_results",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "eval_run_id",
            sa.Integer(),
            sa.ForeignKey("eval_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "eval_question_id",
            sa.Integer(),
            sa.ForeignKey("eval_questions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("retrieved_article_ids_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("similarities_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("precision_at_k", sa.Float(), nullable=True),
        sa.Column("recall_at_k", sa.Float(), nullable=True),
        sa.Column("reciprocal_rank", sa.Float(), nullable=True),
        sa.Column("passed_threshold_check", sa.Boolean(), nullable=True),
        sa.Column("top_k_used", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("eval_run_id", "eval_question_id", name="uk_eval_results_run_question"),
    )
    op.create_index("ix_eval_results_eval_run_id", "eval_results", ["eval_run_id"])
    op.create_index("ix_eval_results_eval_question_id", "eval_results", ["eval_question_id"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_eval_results_eval_question_id", table_name="eval_results")
    op.drop_index("ix_eval_results_eval_run_id", table_name="eval_results")
    op.drop_table("eval_results")
    op.drop_index("ix_eval_runs_eval_user_id", table_name="eval_runs")
    op.drop_table("eval_runs")
    op.drop_table("eval_questions")
