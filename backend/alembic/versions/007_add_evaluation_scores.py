"""add evaluation_scores to persona_sets

Revision ID: 007_evaluation_scores
Revises: 006_human_intervention
Create Date: 2026-02-21

"""
from alembic import op
import sqlalchemy as sa

revision = '007_evaluation_scores'
down_revision = '006_human_intervention'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'persona_sets',
        sa.Column('evaluation_scores', sa.JSON(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('persona_sets', 'evaluation_scores')
