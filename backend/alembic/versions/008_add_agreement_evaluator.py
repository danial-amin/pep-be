"""Add agreement evaluator: new columns on simulations, persona_drift_score on messages, new agreement evaluations table.

Revision ID: 008_agreement_evaluator
Revises: 007_evaluation_scores
Create Date: 2026-03-24

"""
from alembic import op
import sqlalchemy as sa

revision = '008_agreement_evaluator'
down_revision = '007_evaluation_scores'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── New columns on simulations ────────────────────────────────────────────
    op.add_column(
        'simulations',
        sa.Column('run_until_agreement', sa.Boolean(), nullable=True, server_default='false')
    )
    op.add_column(
        'simulations',
        sa.Column('agreement_threshold', sa.Float(), nullable=True, server_default='0.75')
    )
    op.add_column(
        'simulations',
        sa.Column('initial_persona_stances', sa.JSON(), nullable=True)
    )

    # ── Personality drift score on messages ───────────────────────────────────
    op.add_column(
        'simulation_messages',
        sa.Column('persona_drift_score', sa.Float(), nullable=True)
    )

    # ── New agreement evaluations table ───────────────────────────────────────
    op.create_table(
        'simulation_agreement_evaluations',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('simulation_id', sa.Integer(), sa.ForeignKey('simulations.id'), nullable=False, index=True),
        sa.Column('turn_number', sa.Integer(), nullable=False),
        sa.Column('overall_agreement_score', sa.Float(), nullable=False),
        sa.Column('agreement_reached', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('persona_stances', sa.JSON(), nullable=True),
        sa.Column('evaluation_reasoning', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table('simulation_agreement_evaluations')
    op.drop_column('simulation_messages', 'persona_drift_score')
    op.drop_column('simulations', 'initial_persona_stances')
    op.drop_column('simulations', 'agreement_threshold')
    op.drop_column('simulations', 'run_until_agreement')
