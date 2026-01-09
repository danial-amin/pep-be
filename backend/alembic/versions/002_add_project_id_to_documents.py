"""add project_id to documents for session isolation

Revision ID: 002_project_id
Revises: 001_analytics
Create Date: 2024-12-30 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '002_project_id'
down_revision = '001_analytics'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add project_id column to documents table for session/project isolation
    op.add_column('documents', sa.Column('project_id', sa.String(length=255), nullable=True))
    # Create index for faster filtering by project_id
    op.create_index(op.f('ix_documents_project_id'), 'documents', ['project_id'], unique=False)


def downgrade() -> None:
    # Remove index and column
    op.drop_index(op.f('ix_documents_project_id'), table_name='documents')
    op.drop_column('documents', 'project_id')
