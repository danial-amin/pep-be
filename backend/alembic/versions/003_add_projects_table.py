"""add projects table and link persona_sets to projects

Revision ID: 003_projects
Revises: 002_project_id
Create Date: 2024-12-30 11:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '003_projects'
down_revision = '002_project_id'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create projects table
    op.create_table(
        'projects',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('field_of_study', sa.String(length=255), nullable=True),
        sa.Column('core_objective', sa.Text(), nullable=True),
        sa.Column('includes_context', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('includes_interviews', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_projects_id'), 'projects', ['id'], unique=False)
    
    # Add project_id to persona_sets table
    op.add_column('persona_sets', sa.Column('project_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_persona_sets_project_id'), 'persona_sets', ['project_id'], unique=False)
    op.create_foreign_key(
        'fk_persona_sets_project_id',
        'persona_sets', 'projects',
        ['project_id'], ['id'],
        ondelete='SET NULL'
    )


def downgrade() -> None:
    # Remove foreign key and column from persona_sets
    op.drop_constraint('fk_persona_sets_project_id', 'persona_sets', type_='foreignkey')
    op.drop_index(op.f('ix_persona_sets_project_id'), table_name='persona_sets')
    op.drop_column('persona_sets', 'project_id')
    
    # Drop projects table
    op.drop_index(op.f('ix_projects_id'), table_name='projects')
    op.drop_table('projects')
