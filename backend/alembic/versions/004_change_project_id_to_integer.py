"""change project_id from string to integer in documents

Revision ID: 004_project_id_int
Revises: 003_projects
Create Date: 2024-12-30 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '004_project_id_int'
down_revision = '003_projects'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop the old index
    op.drop_index(op.f('ix_documents_project_id'), table_name='documents')
    
    # Change project_id from String to Integer
    # First, we need to handle existing data - convert string IDs to integers if possible
    # For safety, we'll set NULL for any non-numeric values
    op.execute("""
        UPDATE documents 
        SET project_id = NULL 
        WHERE project_id IS NOT NULL 
        AND project_id !~ '^[0-9]+$'
    """)
    
    # Now convert the column type
    op.execute("""
        ALTER TABLE documents 
        ALTER COLUMN project_id TYPE INTEGER 
        USING CASE 
            WHEN project_id IS NULL THEN NULL 
            ELSE project_id::INTEGER 
        END
    """)
    
    # Recreate the index
    op.create_index(op.f('ix_documents_project_id'), 'documents', ['project_id'], unique=False)
    
    # Add foreign key constraint
    op.create_foreign_key(
        'fk_documents_project_id',
        'documents', 'projects',
        ['project_id'], ['id'],
        ondelete='SET NULL'
    )


def downgrade() -> None:
    # Drop foreign key
    op.drop_constraint('fk_documents_project_id', 'documents', type_='foreignkey')
    
    # Drop index
    op.drop_index(op.f('ix_documents_project_id'), table_name='documents')
    
    # Change back to String
    op.alter_column('documents', 'project_id',
                    type_=sa.String(length=255),
                    existing_type=sa.Integer(),
                    postgresql_using=project_id::text)
    
    # Recreate index
    op.create_index(op.f('ix_documents_project_id'), 'documents', ['project_id'], unique=False)
