"""Add RapidAPI fields to samples table

Revision ID: add_rapidapi_fields
Revises:
Create Date: 2024-09-21

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_rapidapi_fields'
down_revision = '7ab896202ecc'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new columns for RapidAPI metadata
    op.add_column('samples', sa.Column('aweme_id', sa.String(), nullable=True))
    op.add_column('samples', sa.Column('title', sa.String(), nullable=True))
    op.add_column('samples', sa.Column('region', sa.String(), nullable=True))
    op.add_column('samples', sa.Column('creator_avatar_url', sa.String(), nullable=True))
    op.add_column('samples', sa.Column('upload_timestamp', sa.Integer(), nullable=True))
    op.add_column('samples', sa.Column('origin_cover_url', sa.String(), nullable=True))
    op.add_column('samples', sa.Column('music_url', sa.String(), nullable=True))
    op.add_column('samples', sa.Column('video_url', sa.String(), nullable=True))
    op.add_column('samples', sa.Column('video_url_watermark', sa.String(), nullable=True))

    # Create unique index on aweme_id
    op.create_index('ix_samples_aweme_id', 'samples', ['aweme_id'], unique=True)


def downgrade() -> None:
    # Remove the index
    op.drop_index('ix_samples_aweme_id', table_name='samples')

    # Remove the columns
    op.drop_column('samples', 'video_url_watermark')
    op.drop_column('samples', 'video_url')
    op.drop_column('samples', 'music_url')
    op.drop_column('samples', 'origin_cover_url')
    op.drop_column('samples', 'upload_timestamp')
    op.drop_column('samples', 'creator_avatar_url')
    op.drop_column('samples', 'region')
    op.drop_column('samples', 'title')
    op.drop_column('samples', 'aweme_id')