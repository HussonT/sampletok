"""add_performance_indexes

Revision ID: f4d0aadfe223
Revises: 08eb3692b876
Create Date: 2025-10-11 14:26:49.312812

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f4d0aadfe223'
down_revision = '08eb3692b876'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add composite index for the common query pattern in get_samples endpoint
    # This helps with filtering completed, playable samples
    op.create_index(
        'ix_samples_playable_completed',
        'samples',
        ['status', 'creator_username', 'audio_url_mp3', 'waveform_url'],
        postgresql_where=sa.text("creator_username IS NOT NULL AND creator_username != '' AND audio_url_mp3 IS NOT NULL AND audio_url_mp3 != '' AND waveform_url IS NOT NULL AND waveform_url != ''")
    )

    # Add index for search queries (ILIKE operations)
    op.create_index(
        'ix_samples_creator_username_search',
        'samples',
        [sa.text('creator_username varchar_pattern_ops')],
        postgresql_using='btree'
    )

    op.create_index(
        'ix_samples_description_search',
        'samples',
        [sa.text('description text_pattern_ops')],
        postgresql_using='btree'
    )

    # Add index on tiktok_creator_id for foreign key joins
    op.create_index(
        'ix_samples_tiktok_creator_id',
        'samples',
        ['tiktok_creator_id']
    )

    # Add index on created_at for ORDER BY operations
    op.create_index(
        'ix_samples_created_at_desc',
        'samples',
        [sa.text('created_at DESC')]
    )


def downgrade() -> None:
    # Drop indexes in reverse order
    op.drop_index('ix_samples_created_at_desc', table_name='samples')
    op.drop_index('ix_samples_tiktok_creator_id', table_name='samples')
    op.drop_index('ix_samples_description_search', table_name='samples')
    op.drop_index('ix_samples_creator_username_search', table_name='samples')
    op.drop_index('ix_samples_playable_completed', table_name='samples')