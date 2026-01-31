"""add simulation tables for multi-persona conversation playground

Revision ID: 005_simulations
Revises: 004_change_project_id_to_integer
Create Date: 2026-01-31 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '005_simulations'
down_revision = '004_change_project_id_to_integer'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create simulations table
    op.create_table(
        'simulations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('goal', sa.Text(), nullable=False),
        sa.Column('goal_context', sa.Text(), nullable=True),
        sa.Column('max_duration_seconds', sa.Integer(), nullable=True, server_default='300'),
        sa.Column('max_tokens', sa.Integer(), nullable=True, server_default='4000'),
        sa.Column('max_turns', sa.Integer(), nullable=True, server_default='20'),
        sa.Column('status', sa.String(length=50), nullable=True, server_default='pending'),
        sa.Column('current_turn', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('tokens_used', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('key_insights', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('action_items', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('project_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_simulations_id'), 'simulations', ['id'], unique=False)
    op.create_index(op.f('ix_simulations_project_id'), 'simulations', ['project_id'], unique=False)

    # Create simulation_participants table
    op.create_table(
        'simulation_participants',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('simulation_id', sa.Integer(), nullable=False),
        sa.Column('persona_id', sa.Integer(), nullable=False),
        sa.Column('role', sa.String(length=255), nullable=True),
        sa.Column('messages_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('tokens_used', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['persona_id'], ['personas.id'], ),
        sa.ForeignKeyConstraint(['simulation_id'], ['simulations.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_simulation_participants_id'), 'simulation_participants', ['id'], unique=False)

    # Create simulation_messages table
    op.create_table(
        'simulation_messages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('simulation_id', sa.Integer(), nullable=False),
        sa.Column('persona_id', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('turn_number', sa.Integer(), nullable=False),
        sa.Column('tokens', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('is_moderator_message', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('responding_to_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['persona_id'], ['personas.id'], ),
        sa.ForeignKeyConstraint(['responding_to_id'], ['simulation_messages.id'], ),
        sa.ForeignKeyConstraint(['simulation_id'], ['simulations.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_simulation_messages_id'), 'simulation_messages', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_simulation_messages_id'), table_name='simulation_messages')
    op.drop_table('simulation_messages')
    op.drop_index(op.f('ix_simulation_participants_id'), table_name='simulation_participants')
    op.drop_table('simulation_participants')
    op.drop_index(op.f('ix_simulations_project_id'), table_name='simulations')
    op.drop_index(op.f('ix_simulations_id'), table_name='simulations')
    op.drop_table('simulations')
