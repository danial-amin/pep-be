"""add PEP methodology columns for iterative generation

Revision ID: 003_pep_methodology
Revises: 002_project_id
Create Date: 2025-01-18 10:00:00.000000

Adds columns to support the PEP paper methodology:
- PersonaSet: project_id, generation_config, rqe_threshold, max_iterations
- Persona: source_references, attribute_validation
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '003_pep_methodology'
down_revision = '002_project_id'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # PersonaSet columns for PEP methodology
    op.add_column('persona_sets', sa.Column('project_id', sa.String(length=255), nullable=True))
    op.add_column('persona_sets', sa.Column('generation_config', sa.JSON(), nullable=True))
    op.add_column('persona_sets', sa.Column('rqe_threshold', sa.Float(), nullable=True, server_default='0.75'))
    op.add_column('persona_sets', sa.Column('max_iterations', sa.Integer(), nullable=True, server_default='3'))

    # Create index for project_id filtering
    op.create_index(op.f('ix_persona_sets_project_id'), 'persona_sets', ['project_id'], unique=False)

    # Persona columns for source traceability and validation
    op.add_column('personas', sa.Column('source_references', sa.JSON(), nullable=True))
    op.add_column('personas', sa.Column('attribute_validation', sa.JSON(), nullable=True))


def downgrade() -> None:
    # Remove Persona columns
    op.drop_column('personas', 'attribute_validation')
    op.drop_column('personas', 'source_references')

    # Remove PersonaSet columns
    op.drop_index(op.f('ix_persona_sets_project_id'), table_name='persona_sets')
    op.drop_column('persona_sets', 'max_iterations')
    op.drop_column('persona_sets', 'rqe_threshold')
    op.drop_column('persona_sets', 'generation_config')
    op.drop_column('persona_sets', 'project_id')
