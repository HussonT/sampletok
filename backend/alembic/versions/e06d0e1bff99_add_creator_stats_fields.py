"""add creator stats fields

Revision ID: e06d0e1bff99
Revises: 1a64b887e7c9
Create Date: 2025-10-11 12:15:22.196960

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e06d0e1bff99'
down_revision = '1a64b887e7c9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('samples', sa.Column('creator_avatar_thumb', sa.String(), nullable=True))
    op.add_column('samples', sa.Column('creator_avatar_medium', sa.String(), nullable=True))
    op.add_column('samples', sa.Column('creator_avatar_large', sa.String(), nullable=True))
    op.add_column('samples', sa.Column('creator_signature', sa.Text(), nullable=True))
    op.add_column('samples', sa.Column('creator_verified', sa.Integer(), nullable=True, server_default='0'))
    op.add_column('samples', sa.Column('creator_following_count', sa.Integer(), nullable=True, server_default='0'))
    op.add_column('samples', sa.Column('creator_heart_count', sa.Integer(), nullable=True, server_default='0'))
    op.add_column('samples', sa.Column('creator_video_count', sa.Integer(), nullable=True, server_default='0'))


def downgrade() -> None:
    op.drop_column('samples', 'creator_video_count')
    op.drop_column('samples', 'creator_heart_count')
    op.drop_column('samples', 'creator_following_count')
    op.drop_column('samples', 'creator_verified')
    op.drop_column('samples', 'creator_signature')
    op.drop_column('samples', 'creator_avatar_large')
    op.drop_column('samples', 'creator_avatar_medium')
    op.drop_column('samples', 'creator_avatar_thumb')