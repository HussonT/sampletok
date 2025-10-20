"""add tag model and sample_tags junction table

Revision ID: 2b91c4fd5e8a
Revises: 1d4efa163390
Create Date: 2025-10-20 20:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision = '2b91c4fd5e8a'
down_revision = '1d4efa163390'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create tags table
    op.create_table(
        'tags',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(50), nullable=False, unique=True, index=True),
        sa.Column('display_name', sa.String(50), nullable=False),
        sa.Column('category', sa.Enum('GENRE', 'MOOD', 'INSTRUMENT', 'CONTENT', 'TEMPO', 'EFFECT', 'OTHER', name='tagcategory'), nullable=False, server_default='OTHER', index=True),
        sa.Column('usage_count', sa.Integer(), nullable=False, server_default='0', index=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP'), index=True),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )

    # Create sample_tags junction table
    op.create_table(
        'sample_tags',
        sa.Column('sample_id', UUID(as_uuid=True), nullable=False, primary_key=True),
        sa.Column('tag_id', UUID(as_uuid=True), nullable=False, primary_key=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )

    # Create foreign keys for junction table
    op.create_foreign_key(
        'fk_sample_tags_sample',
        'sample_tags', 'samples',
        ['sample_id'], ['id'],
        ondelete='CASCADE'
    )
    op.create_foreign_key(
        'fk_sample_tags_tag',
        'sample_tags', 'tags',
        ['tag_id'], ['id'],
        ondelete='CASCADE'
    )

    # Create indexes for junction table (for efficient lookups)
    op.create_index('ix_sample_tags_sample_id', 'sample_tags', ['sample_id'])
    op.create_index('ix_sample_tags_tag_id', 'sample_tags', ['tag_id'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_sample_tags_tag_id', 'sample_tags')
    op.drop_index('ix_sample_tags_sample_id', 'sample_tags')

    # Drop foreign keys
    op.drop_constraint('fk_sample_tags_tag', 'sample_tags', type_='foreignkey')
    op.drop_constraint('fk_sample_tags_sample', 'sample_tags', type_='foreignkey')

    # Drop tables
    op.drop_table('sample_tags')
    op.drop_table('tags')

    # Drop enum type
    op.execute("DROP TYPE tagcategory")
