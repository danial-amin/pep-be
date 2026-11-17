"""Add persona_chat_sessions and persona_chat_messages tables.

Revision ID: 010_persona_chats
Revises: 009_judge_scores
Create Date: 2026-07-13

"""
from alembic import op
import sqlalchemy as sa

revision = "010_persona_chats"
down_revision = "009_judge_scores"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "persona_chat_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("persona_id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=True),
        sa.Column("persona_name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["persona_id"], ["personas.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_persona_chat_sessions_id", "persona_chat_sessions", ["id"])
    op.create_index("ix_persona_chat_sessions_persona_id", "persona_chat_sessions", ["persona_id"])
    op.create_index("ix_persona_chat_sessions_project_id", "persona_chat_sessions", ["project_id"])

    op.create_table(
        "persona_chat_messages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("refused", sa.Boolean(), nullable=True),
        sa.Column("retrieval_score", sa.Float(), nullable=True),
        sa.Column("sources_used", sa.JSON(), nullable=True),
        sa.Column("refusal_reason", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["session_id"], ["persona_chat_sessions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_persona_chat_messages_id", "persona_chat_messages", ["id"])
    op.create_index("ix_persona_chat_messages_session_id", "persona_chat_messages", ["session_id"])


def downgrade() -> None:
    op.drop_index("ix_persona_chat_messages_session_id", table_name="persona_chat_messages")
    op.drop_index("ix_persona_chat_messages_id", table_name="persona_chat_messages")
    op.drop_table("persona_chat_messages")
    op.drop_index("ix_persona_chat_sessions_project_id", table_name="persona_chat_sessions")
    op.drop_index("ix_persona_chat_sessions_persona_id", table_name="persona_chat_sessions")
    op.drop_index("ix_persona_chat_sessions_id", table_name="persona_chat_sessions")
    op.drop_table("persona_chat_sessions")
