"""Add studies.order_rotations for per-participant counterbalancing.

Revision ID: 015_study_order_rotations
Revises: 014_study_mode
Create Date: 2026-08-06

"""
from alembic import op
import sqlalchemy as sa

revision = "015_study_order_rotations"
down_revision = "014_study_mode"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("studies", sa.Column("order_rotations", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("studies", "order_rotations")
