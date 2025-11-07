"""add filtering indexes

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2025-11-04 20:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b2c3d4e5f6a7'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add indexes for filtering
    op.create_index('ix_samples_bpm', 'samples', ['bpm'])
    op.create_index('ix_samples_key', 'samples', ['key'])

    # GIN index for JSONB tag queries (array overlap operations)
    op.execute('CREATE INDEX ix_samples_tags_gin ON samples USING GIN (tags)')


def downgrade() -> None:
    op.execute('DROP INDEX IF EXISTS ix_samples_tags_gin')
    op.drop_index('ix_samples_key', table_name='samples')
    op.drop_index('ix_samples_bpm', table_name='samples')
