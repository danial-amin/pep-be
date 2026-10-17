"""Add set-mode support to persona chat sessions and messages.

Revision ID: 011_persona_chat_set_mode
Revises: 010_persona_chats
Create Date: 2026-07-17

"""
from alembic import op
import sqlalchemy as sa

revision = "011_persona_chat_set_mode"
down_revision = "010_persona_chats"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Sessions: allow set mode
    op.add_column("persona_chat_sessions", sa.Column("persona_set_id", sa.Integer(), nullable=True))
    op.add_column(
        "persona_chat_sessions",
        sa.Column("mode", sa.String(length=32), nullable=False, server_default="single"),
    )
    op.create_index("ix_persona_chat_sessions_persona_set_id", "persona_chat_sessions", ["persona_set_id"])
    op.create_foreign_key(
        "fk_persona_chat_sessions_persona_set_id",
        "persona_chat_sessions",
        "persona_sets",
        ["persona_set_id"],
        ["id"],
    )
    # persona_id becomes optional (set sessions have no single persona)
    op.alter_column("persona_chat_sessions", "persona_id", existing_type=sa.Integer(), nullable=True)

    # Messages: track which persona spoke
    op.add_column("persona_chat_messages", sa.Column("persona_id", sa.Integer(), nullable=True))
    op.add_column("persona_chat_messages", sa.Column("persona_name", sa.String(length=255), nullable=True))
    op.create_index("ix_persona_chat_messages_persona_id", "persona_chat_messages", ["persona_id"])
    op.create_foreign_key(
        "fk_persona_chat_messages_persona_id",
        "persona_chat_messages",
        "personas",
        ["persona_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_persona_chat_messages_persona_id", "persona_chat_messages", type_="foreignkey")
    op.drop_index("ix_persona_chat_messages_persona_id", table_name="persona_chat_messages")
    op.drop_column("persona_chat_messages", "persona_name")
    op.drop_column("persona_chat_messages", "persona_id")

    op.drop_constraint("fk_persona_chat_sessions_persona_set_id", "persona_chat_sessions", type_="foreignkey")
    op.drop_index("ix_persona_chat_sessions_persona_set_id", table_name="persona_chat_sessions")
    op.drop_column("persona_chat_sessions", "mode")
    op.drop_column("persona_chat_sessions", "persona_set_id")
    op.alter_column("persona_chat_sessions", "persona_id", existing_type=sa.Integer(), nullable=False)
