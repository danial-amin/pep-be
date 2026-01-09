"""add analytics columns to persona models

Revision ID: 001_analytics
Revises: 
Create Date: 2024-12-29 21:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_analytics'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add columns to persona_sets table
    op.add_column('persona_sets', sa.Column('rqe_scores', postgresql.JSON(astext_type=sa.Text()), nullable=True))
    op.add_column('persona_sets', sa.Column('diversity_score', postgresql.JSON(astext_type=sa.Text()), nullable=True))
    op.add_column('persona_sets', sa.Column('validation_scores', postgresql.JSON(astext_type=sa.Text()), nullable=True))
    op.add_column('persona_sets', sa.Column('generation_cycle', sa.Integer(), nullable=True, server_default='1'))
    op.add_column('persona_sets', sa.Column('status', sa.String(length=50), nullable=True, server_default='generated'))
    
    # Add columns to personas table
    op.add_column('personas', sa.Column('similarity_score', postgresql.JSON(astext_type=sa.Text()), nullable=True))
    op.add_column('personas', sa.Column('validation_status', sa.String(length=50), nullable=True))


def downgrade() -> None:
    # Remove columns from personas table
    op.drop_column('personas', 'validation_status')
    op.drop_column('personas', 'similarity_score')
    
    # Remove columns from persona_sets table
    op.drop_column('persona_sets', 'status')
    op.drop_column('persona_sets', 'generation_cycle')
    op.drop_column('persona_sets', 'validation_scores')
    op.drop_column('persona_sets', 'diversity_score')
    op.drop_column('persona_sets', 'rqe_scores')

