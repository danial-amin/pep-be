"""Add persona_profile_views for dwell-time tracking.

Revision ID: 013_persona_profile_views
Revises: 012_add_auth_invite
Create Date: 2026-08-06

"""
from alembic import op
import sqlalchemy as sa

revision = "013_persona_profile_views"
down_revision = "012_add_auth_invite"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "persona_profile_views",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("persona_set_id", sa.Integer(), sa.ForeignKey("persona_sets.id"), nullable=False),
        sa.Column("persona_id", sa.Integer(), sa.ForeignKey("personas.id"), nullable=True),
        sa.Column("view_type", sa.String(length=32), nullable=False),
        sa.Column("duration_seconds", sa.Float(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_persona_profile_views_id", "persona_profile_views", ["id"])
    op.create_index("ix_persona_profile_views_user_id", "persona_profile_views", ["user_id"])
    op.create_index(
        "ix_persona_profile_views_persona_set_id", "persona_profile_views", ["persona_set_id"]
    )
    op.create_index("ix_persona_profile_views_persona_id", "persona_profile_views", ["persona_id"])
    op.create_index("ix_persona_profile_views_view_type", "persona_profile_views", ["view_type"])


def downgrade() -> None:
    op.drop_index("ix_persona_profile_views_view_type", table_name="persona_profile_views")
    op.drop_index("ix_persona_profile_views_persona_id", table_name="persona_profile_views")
    op.drop_index("ix_persona_profile_views_persona_set_id", table_name="persona_profile_views")
    op.drop_index("ix_persona_profile_views_user_id", table_name="persona_profile_views")
    op.drop_index("ix_persona_profile_views_id", table_name="persona_profile_views")
    op.drop_table("persona_profile_views")
