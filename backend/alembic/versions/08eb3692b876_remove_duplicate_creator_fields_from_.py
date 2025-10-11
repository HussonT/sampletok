"""remove_duplicate_creator_fields_from_sample

Revision ID: 08eb3692b876
Revises: 1d4efa163390
Create Date: 2025-10-11 14:14:48.582720

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '08eb3692b876'
down_revision = '1d4efa163390'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Remove duplicate creator fields that are now in TikTokCreator table
    op.drop_column('samples', 'creator_avatar_thumb')
    op.drop_column('samples', 'creator_avatar_medium')
    op.drop_column('samples', 'creator_avatar_large')
    op.drop_column('samples', 'creator_signature')
    op.drop_column('samples', 'creator_verified')
    op.drop_column('samples', 'creator_follower_count')
    op.drop_column('samples', 'creator_following_count')
    op.drop_column('samples', 'creator_heart_count')
    op.drop_column('samples', 'creator_video_count')


def downgrade() -> None:
    # Re-add the columns if we need to rollback
    op.add_column('samples', sa.Column('creator_avatar_thumb', sa.String(), nullable=True))
    op.add_column('samples', sa.Column('creator_avatar_medium', sa.String(), nullable=True))
    op.add_column('samples', sa.Column('creator_avatar_large', sa.String(), nullable=True))
    op.add_column('samples', sa.Column('creator_signature', sa.Text(), nullable=True))
    op.add_column('samples', sa.Column('creator_verified', sa.Integer(), server_default='0', nullable=True))
    op.add_column('samples', sa.Column('creator_follower_count', sa.Integer(), server_default='0', nullable=True))
    op.add_column('samples', sa.Column('creator_following_count', sa.Integer(), server_default='0', nullable=True))
    op.add_column('samples', sa.Column('creator_heart_count', sa.Integer(), server_default='0', nullable=True))
    op.add_column('samples', sa.Column('creator_video_count', sa.Integer(), server_default='0', nullable=True))