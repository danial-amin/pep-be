"""Add studies, study_participants, study_events.

Revision ID: 014_study_mode
Revises: 013_persona_profile_views
Create Date: 2026-08-06

"""
from alembic import op
import sqlalchemy as sa

revision = "014_study_mode"
down_revision = "013_persona_profile_views"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "studies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=True),
        sa.Column("persona_set_id", sa.Integer(), sa.ForeignKey("persona_sets.id"), nullable=False),
        sa.Column("persona_order", sa.JSON(), nullable=True),
        sa.Column("allow_open_codes", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("max_participants", sa.Integer(), nullable=False, server_default="40"),
        sa.Column("welcome_text", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_studies_id", "studies", ["id"])
    op.create_index("ix_studies_slug", "studies", ["slug"], unique=True)
    op.create_index("ix_studies_project_id", "studies", ["project_id"])
    op.create_index("ix_studies_persona_set_id", "studies", ["persona_set_id"])

    op.create_table(
        "study_participants",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("study_id", sa.Integer(), sa.ForeignKey("studies.id"), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("study_id", "code", name="uq_study_participant_code"),
    )
    op.create_index("ix_study_participants_id", "study_participants", ["id"])
    op.create_index("ix_study_participants_study_id", "study_participants", ["study_id"])
    op.create_index("ix_study_participants_code", "study_participants", ["code"])
    op.create_index("ix_study_participants_user_id", "study_participants", ["user_id"])

    op.create_table(
        "study_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("study_id", sa.Integer(), sa.ForeignKey("studies.id"), nullable=False),
        sa.Column("participant_id", sa.Integer(), sa.ForeignKey("study_participants.id"), nullable=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("path", sa.String(length=512), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_study_events_id", "study_events", ["id"])
    op.create_index("ix_study_events_study_id", "study_events", ["study_id"])
    op.create_index("ix_study_events_participant_id", "study_events", ["participant_id"])
    op.create_index("ix_study_events_event_type", "study_events", ["event_type"])
    op.create_index("ix_study_events_created_at", "study_events", ["created_at"])


def downgrade() -> None:
    op.drop_table("study_events")
    op.drop_table("study_participants")
    op.drop_table("studies")
