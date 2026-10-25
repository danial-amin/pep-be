"""Add simulation message lineage for branching playgrounds.

Revision ID: 016_simulation_branch_lineage
Revises: 015_study_order_rotations
Create Date: 2026-10-25

"""
from alembic import op
import sqlalchemy as sa


revision = "016_simulation_branch_lineage"
down_revision = "015_study_order_rotations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "simulation_messages",
        sa.Column("parent_message_id", sa.Integer(), nullable=True),
    )
    op.create_index(
        "ix_simulation_messages_parent_message_id",
        "simulation_messages",
        ["parent_message_id"],
    )
    op.create_foreign_key(
        "fk_simulation_messages_parent_message_id",
        "simulation_messages",
        "simulation_messages",
        ["parent_message_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.add_column(
        "simulations",
        sa.Column("active_head_message_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_simulations_active_head_message_id",
        "simulations",
        "simulation_messages",
        ["active_head_message_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.add_column(
        "simulation_agreement_evaluations",
        sa.Column("head_message_id", sa.Integer(), nullable=True),
    )
    op.create_index(
        "ix_simulation_agreement_evaluations_head_message_id",
        "simulation_agreement_evaluations",
        ["head_message_id"],
    )
    op.create_foreign_key(
        "fk_simulation_agreement_evaluations_head_message_id",
        "simulation_agreement_evaluations",
        "simulation_messages",
        ["head_message_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Existing sessions are a single chain in speak order.
    op.execute(
        """
        WITH ordered AS (
            SELECT id,
                   lag(id) OVER (
                       PARTITION BY simulation_id
                       ORDER BY turn_number, id
                   ) AS prev_id
            FROM simulation_messages
        )
        UPDATE simulation_messages AS m
        SET parent_message_id = ordered.prev_id
        FROM ordered
        WHERE m.id = ordered.id
          AND ordered.prev_id IS NOT NULL
        """
    )
    op.execute(
        """
        UPDATE simulations AS s
        SET active_head_message_id = sub.id
        FROM (
            SELECT DISTINCT ON (simulation_id) id, simulation_id
            FROM simulation_messages
            ORDER BY simulation_id, turn_number DESC, id DESC
        ) AS sub
        WHERE s.id = sub.simulation_id
        """
    )
    op.execute(
        """
        UPDATE simulation_agreement_evaluations AS e
        SET head_message_id = sub.id
        FROM (
            SELECT DISTINCT ON (simulation_id, turn_number)
                   id, simulation_id, turn_number
            FROM simulation_messages
            ORDER BY simulation_id, turn_number, id DESC
        ) AS sub
        WHERE e.simulation_id = sub.simulation_id
          AND e.turn_number = sub.turn_number
          AND e.head_message_id IS NULL
        """
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_simulation_agreement_evaluations_head_message_id",
        "simulation_agreement_evaluations",
        type_="foreignkey",
    )
    op.drop_index(
        "ix_simulation_agreement_evaluations_head_message_id",
        table_name="simulation_agreement_evaluations",
    )
    op.drop_column("simulation_agreement_evaluations", "head_message_id")

    op.drop_constraint(
        "fk_simulations_active_head_message_id",
        "simulations",
        type_="foreignkey",
    )
    op.drop_column("simulations", "active_head_message_id")

    op.drop_constraint(
        "fk_simulation_messages_parent_message_id",
        "simulation_messages",
        type_="foreignkey",
    )
    op.drop_index(
        "ix_simulation_messages_parent_message_id",
        table_name="simulation_messages",
    )
    op.drop_column("simulation_messages", "parent_message_id")
