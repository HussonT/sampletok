"""Placeholder migration for production database state

This migration was created to bridge the gap between production and local state.
In production, this migration ID exists in alembic_version table after creating
the instagram_engagements table. This is a no-op migration to satisfy Alembic.

Revision ID: 4c48afe435d7
Revises: 4be5e02bf74e
Create Date: 2025-11-19 20:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '4c48afe435d7'
down_revision = '4be5e02bf74e'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Check if table already exists (it should in production)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    table_exists = 'instagram_engagements' in inspector.get_table_names()

    if not table_exists:
        # Create the table if it doesn't exist (shouldn't happen in production)
        # This handles the case where this runs on a fresh database
        op.create_table('instagram_engagements',
            sa.Column('id', sa.UUID(), nullable=False),
            sa.Column('instagram_media_id', sa.String(), nullable=False),
            sa.Column('instagram_username', sa.String(), nullable=False),
            sa.Column('instagram_post_url', sa.String(), nullable=False),
            sa.Column('engagement_type', sa.String(), nullable=False),
            sa.Column('status', sa.String(), nullable=False),
            sa.Column('sample_id', sa.UUID(), nullable=True),
            sa.Column('comment_text', sa.Text(), nullable=False),
            sa.Column('was_mentioned', sa.Boolean(), nullable=False),
            sa.Column('commented_at', sa.DateTime(), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['sample_id'], ['samples.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('idx_instagram_engagements_status', 'instagram_engagements', ['status'])
        op.create_index('idx_instagram_engagements_sample_id', 'instagram_engagements', ['sample_id'])
        op.create_index('idx_instagram_engagements_username_date', 'instagram_engagements', ['instagram_username', 'commented_at'])


def downgrade() -> None:
    # Only drop if table exists
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    table_exists = 'instagram_engagements' in inspector.get_table_names()

    if table_exists:
        op.drop_index('idx_instagram_engagements_username_date', table_name='instagram_engagements')
        op.drop_index('idx_instagram_engagements_sample_id', table_name='instagram_engagements')
        op.drop_index('idx_instagram_engagements_status', table_name='instagram_engagements')
        op.drop_table('instagram_engagements')
