"""Add judge_runs and judge_scores tables for simulation LLM-as-judge evaluation.

Revision ID: 009_judge_scores
Revises: 008_agreement_evaluator
Create Date: 2026-06-10

"""
from alembic import op
import sqlalchemy as sa

revision = "009_judge_scores"
down_revision = "008_agreement_evaluator"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "judge_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("judge_model", sa.String(length=128), nullable=False),
        sa.Column("model_version", sa.String(length=128), nullable=False),
        sa.Column("pass_number", sa.Integer(), nullable=False),
        sa.Column("temperature", sa.Float(), nullable=False),
        sa.Column("level", sa.String(length=32), nullable=False),
        sa.Column("simulation_id", sa.Integer(), nullable=False),
        sa.Column("target_id", sa.Integer(), nullable=False),
        sa.Column("prompt_template_hash", sa.String(length=64), nullable=False),
        sa.Column("system_prompt", sa.Text(), nullable=False),
        sa.Column("user_prompt", sa.Text(), nullable=False),
        sa.Column("run_timestamp", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["simulation_id"], ["simulations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_judge_runs_simulation_id", "judge_runs", ["simulation_id"])
    op.create_index(
        "ix_judge_runs_unique",
        "judge_runs",
        ["judge_model", "level", "simulation_id", "target_id", "pass_number"],
        unique=True,
    )

    op.create_table(
        "judge_scores",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("judge_run_id", sa.Integer(), nullable=False),
        sa.Column("judge_model", sa.String(length=128), nullable=False),
        sa.Column("model_version", sa.String(length=128), nullable=False),
        sa.Column("pass_number", sa.Integer(), nullable=False),
        sa.Column("temperature", sa.Float(), nullable=False),
        sa.Column("level", sa.String(length=32), nullable=False),
        sa.Column("simulation_id", sa.Integer(), nullable=False),
        sa.Column("target_id", sa.Integer(), nullable=False),
        sa.Column("item", sa.String(length=64), nullable=False),
        sa.Column("item_type", sa.String(length=32), nullable=False),
        sa.Column("response_code", sa.Integer(), nullable=True),
        sa.Column("response_label", sa.Text(), nullable=False),
        sa.Column("justification", sa.Text(), nullable=False),
        sa.Column("run_timestamp", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["judge_run_id"], ["judge_runs.id"]),
        sa.ForeignKeyConstraint(["simulation_id"], ["simulations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_judge_scores_judge_run_id", "judge_scores", ["judge_run_id"])
    op.create_index("ix_judge_scores_simulation_id", "judge_scores", ["simulation_id"])
    op.create_index(
        "ix_judge_scores_unique",
        "judge_scores",
        ["judge_model", "pass_number", "level", "simulation_id", "target_id", "item"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_judge_scores_unique", table_name="judge_scores")
    op.drop_index("ix_judge_scores_simulation_id", table_name="judge_scores")
    op.drop_index("ix_judge_scores_judge_run_id", table_name="judge_scores")
    op.drop_table("judge_scores")
    op.drop_index("ix_judge_runs_unique", table_name="judge_runs")
    op.drop_index("ix_judge_runs_simulation_id", table_name="judge_runs")
    op.drop_table("judge_runs")
