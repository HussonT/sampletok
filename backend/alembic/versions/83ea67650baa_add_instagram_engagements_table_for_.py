"""Add instagram_engagements table for mention tracking

This migration updates the instagram_engagements table schema.
It follows 4c48afe435d7 which created the initial table.

Revision ID: 83ea67650baa
Revises: 4c48afe435d7
Create Date: 2025-11-19 06:56:28.281982

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '83ea67650baa'
down_revision = '4c48afe435d7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # This migration modifies the instagram_engagements table created by 4c48afe435d7
    # Drop old indexes
    op.drop_index('idx_instagram_engagements_username_date', table_name='instagram_engagements')
    op.drop_index('idx_instagram_engagements_sample_id', table_name='instagram_engagements')
    op.drop_index('idx_instagram_engagements_status', table_name='instagram_engagements')

    # Add new columns
    op.add_column('instagram_engagements', sa.Column('instagram_shortcode', sa.String(), nullable=True))
    op.add_column('instagram_engagements', sa.Column('instagram_permalink', sa.String(), nullable=True))
    op.add_column('instagram_engagements', sa.Column('instagram_user_id', sa.String(), nullable=True))
    op.add_column('instagram_engagements', sa.Column('email', sa.String(), nullable=True))
    op.add_column('instagram_engagements', sa.Column('email_sent', sa.Boolean(), nullable=True))
    op.add_column('instagram_engagements', sa.Column('email_sent_at', sa.DateTime(), nullable=True))
    op.add_column('instagram_engagements', sa.Column('media_type', sa.String(), nullable=True))
    op.add_column('instagram_engagements', sa.Column('caption', sa.Text(), nullable=True))
    op.add_column('instagram_engagements', sa.Column('error_message', sa.Text(), nullable=True))
    op.add_column('instagram_engagements', sa.Column('retry_count', sa.Integer(), nullable=True))
    op.add_column('instagram_engagements', sa.Column('comment_id', sa.String(), nullable=True))
    op.add_column('instagram_engagements', sa.Column('comment_posted_at', sa.DateTime(), nullable=True))
    op.add_column('instagram_engagements', sa.Column('webhook_payload', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('instagram_engagements', sa.Column('detected_at', sa.DateTime(), nullable=True))
    op.add_column('instagram_engagements', sa.Column('processed_at', sa.DateTime(), nullable=True))

    # Convert VARCHAR columns to ENUM types
    op.execute("CREATE TYPE engagementtype AS ENUM ('MENTION', 'COMMENT', 'STORY_MENTION')")
    op.execute("ALTER TABLE instagram_engagements ALTER COLUMN engagement_type TYPE engagementtype USING engagement_type::engagementtype")

    op.execute("CREATE TYPE engagementstatus AS ENUM ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', 'SKIPPED')")
    op.execute("ALTER TABLE instagram_engagements ALTER COLUMN status TYPE engagementstatus USING status::engagementstatus")

    # Make columns nullable
    op.alter_column('instagram_engagements', 'instagram_username', nullable=True)
    op.alter_column('instagram_engagements', 'comment_text', nullable=True)
    op.alter_column('instagram_engagements', 'created_at', nullable=True)
    op.alter_column('instagram_engagements', 'updated_at', nullable=True)
    op.alter_column('instagram_engagements', 'engagement_type', nullable=True)
    op.alter_column('instagram_engagements', 'status', nullable=True)

    # Drop old columns
    op.drop_column('instagram_engagements', 'instagram_post_url')
    op.drop_column('instagram_engagements', 'was_mentioned')
    op.drop_column('instagram_engagements', 'commented_at')

    # Create new indexes
    op.create_index(op.f('ix_instagram_engagements_created_at'), 'instagram_engagements', ['created_at'], unique=False)
    op.create_index(op.f('ix_instagram_engagements_detected_at'), 'instagram_engagements', ['detected_at'], unique=False)
    op.create_index(op.f('ix_instagram_engagements_engagement_type'), 'instagram_engagements', ['engagement_type'], unique=False)
    op.create_index(op.f('ix_instagram_engagements_instagram_media_id'), 'instagram_engagements', ['instagram_media_id'], unique=True)
    op.create_index(op.f('ix_instagram_engagements_instagram_shortcode'), 'instagram_engagements', ['instagram_shortcode'], unique=False)
    op.create_index(op.f('ix_instagram_engagements_instagram_user_id'), 'instagram_engagements', ['instagram_user_id'], unique=False)
    op.create_index(op.f('ix_instagram_engagements_instagram_username'), 'instagram_engagements', ['instagram_username'], unique=False)
    op.create_index(op.f('ix_instagram_engagements_sample_id'), 'instagram_engagements', ['sample_id'], unique=False)
    op.create_index(op.f('ix_instagram_engagements_status'), 'instagram_engagements', ['status'], unique=False)


def downgrade() -> None:
    # Reverse the changes from upgrade()
    # Drop new indexes
    op.drop_index(op.f('ix_instagram_engagements_status'), table_name='instagram_engagements')
    op.drop_index(op.f('ix_instagram_engagements_sample_id'), table_name='instagram_engagements')
    op.drop_index(op.f('ix_instagram_engagements_instagram_username'), table_name='instagram_engagements')
    op.drop_index(op.f('ix_instagram_engagements_instagram_user_id'), table_name='instagram_engagements')
    op.drop_index(op.f('ix_instagram_engagements_instagram_shortcode'), table_name='instagram_engagements')
    op.drop_index(op.f('ix_instagram_engagements_instagram_media_id'), table_name='instagram_engagements')
    op.drop_index(op.f('ix_instagram_engagements_engagement_type'), table_name='instagram_engagements')
    op.drop_index(op.f('ix_instagram_engagements_detected_at'), table_name='instagram_engagements')
    op.drop_index(op.f('ix_instagram_engagements_created_at'), table_name='instagram_engagements')

    # Add back old columns
    op.add_column('instagram_engagements', sa.Column('commented_at', sa.DateTime(), nullable=False))
    op.add_column('instagram_engagements', sa.Column('was_mentioned', sa.Boolean(), nullable=False))
    op.add_column('instagram_engagements', sa.Column('instagram_post_url', sa.String(), nullable=False))

    # Make columns NOT NULL again
    op.alter_column('instagram_engagements', 'status', nullable=False)
    op.alter_column('instagram_engagements', 'engagement_type', nullable=False)
    op.alter_column('instagram_engagements', 'updated_at', nullable=False)
    op.alter_column('instagram_engagements', 'created_at', nullable=False)
    op.alter_column('instagram_engagements', 'comment_text', nullable=False)
    op.alter_column('instagram_engagements', 'instagram_username', nullable=False)

    # Convert ENUM back to VARCHAR
    op.execute("ALTER TABLE instagram_engagements ALTER COLUMN status TYPE VARCHAR USING status::text")
    op.execute("DROP TYPE engagementstatus")

    op.execute("ALTER TABLE instagram_engagements ALTER COLUMN engagement_type TYPE VARCHAR USING engagement_type::text")
    op.execute("DROP TYPE engagementtype")

    # Drop new columns
    op.drop_column('instagram_engagements', 'processed_at')
    op.drop_column('instagram_engagements', 'detected_at')
    op.drop_column('instagram_engagements', 'webhook_payload')
    op.drop_column('instagram_engagements', 'comment_posted_at')
    op.drop_column('instagram_engagements', 'comment_id')
    op.drop_column('instagram_engagements', 'retry_count')
    op.drop_column('instagram_engagements', 'error_message')
    op.drop_column('instagram_engagements', 'caption')
    op.drop_column('instagram_engagements', 'media_type')
    op.drop_column('instagram_engagements', 'email_sent_at')
    op.drop_column('instagram_engagements', 'email_sent')
    op.drop_column('instagram_engagements', 'email')
    op.drop_column('instagram_engagements', 'instagram_user_id')
    op.drop_column('instagram_engagements', 'instagram_permalink')
    op.drop_column('instagram_engagements', 'instagram_shortcode')

    # Create old indexes
    op.create_index('idx_instagram_engagements_status', 'instagram_engagements', ['status'])
    op.create_index('idx_instagram_engagements_sample_id', 'instagram_engagements', ['sample_id'])
    op.create_index('idx_instagram_engagements_username_date', 'instagram_engagements', ['instagram_username', 'commented_at'])