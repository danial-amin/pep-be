"""Add users, invites, and project ownership.

Revision ID: 012_add_auth_invite
Revises: 011_persona_chat_set_mode
Create Date: 2026-07-17

"""
from alembic import op
import sqlalchemy as sa

revision = "012_add_auth_invite"
down_revision = "011_persona_chat_set_mode"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_users_id", "users", ["id"])
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "invites",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("token", sa.String(length=64), nullable=False),
        sa.Column("invited_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("note", sa.Text(), nullable=True),
    )
    op.create_index("ix_invites_id", "invites", ["id"])
    op.create_index("ix_invites_email", "invites", ["email"])
    op.create_index("ix_invites_token", "invites", ["token"], unique=True)

    op.add_column("projects", sa.Column("user_id", sa.Integer(), nullable=True))
    op.create_index("ix_projects_user_id", "projects", ["user_id"])
    op.create_foreign_key(
        "fk_projects_user_id",
        "projects",
        "users",
        ["user_id"],
        ["id"],
    )

    op.add_column("persona_chat_sessions", sa.Column("user_id", sa.Integer(), nullable=True))
    op.create_index("ix_persona_chat_sessions_user_id", "persona_chat_sessions", ["user_id"])
    op.create_foreign_key(
        "fk_persona_chat_sessions_user_id",
        "persona_chat_sessions",
        "users",
        ["user_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_persona_chat_sessions_user_id", "persona_chat_sessions", type_="foreignkey")
    op.drop_index("ix_persona_chat_sessions_user_id", table_name="persona_chat_sessions")
    op.drop_column("persona_chat_sessions", "user_id")

    op.drop_constraint("fk_projects_user_id", "projects", type_="foreignkey")
    op.drop_index("ix_projects_user_id", table_name="projects")
    op.drop_column("projects", "user_id")

    op.drop_index("ix_invites_token", table_name="invites")
    op.drop_index("ix_invites_email", table_name="invites")
    op.drop_index("ix_invites_id", table_name="invites")
    op.drop_table("invites")

    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_users_id", table_name="users")
    op.drop_table("users")
