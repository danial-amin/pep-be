"""add human intervention support to simulation messages

Revision ID: 006_human_intervention
Revises: 005_simulations
Create Date: 2026-02-01

"""
from alembic import op
import sqlalchemy as sa

revision = '006_human_intervention'
down_revision = '005_simulations'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'simulation_messages',
        sa.Column('is_human_message', sa.Boolean(), nullable=True, server_default='false')
    )
    op.alter_column(
        'simulation_messages',
        'persona_id',
        existing_type=sa.Integer(),
        nullable=True
    )


def downgrade() -> None:
    op.alter_column(
        'simulation_messages',
        'persona_id',
        existing_type=sa.Integer(),
        nullable=False
    )
    op.drop_column('simulation_messages', 'is_human_message')
