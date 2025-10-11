"""create tiktok_creators table

Revision ID: 1d4efa163390
Revises: e06d0e1bff99
Create Date: 2025-10-11 12:35:19.041098

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision = '1d4efa163390'
down_revision = 'e06d0e1bff99'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create tiktok_creators table
    op.create_table(
        'tiktok_creators',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('tiktok_id', sa.String(), nullable=False, unique=True, index=True),
        sa.Column('username', sa.String(), nullable=False, unique=True, index=True),
        sa.Column('nickname', sa.String(), nullable=True),
        sa.Column('avatar_thumb', sa.String(), nullable=True),
        sa.Column('avatar_medium', sa.String(), nullable=True),
        sa.Column('avatar_large', sa.String(), nullable=True),
        sa.Column('signature', sa.Text(), nullable=True),
        sa.Column('verified', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('follower_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('following_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('heart_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('video_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_fetched_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP'), index=True),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )

    # Add tiktok_creator_id foreign key to samples table
    op.add_column('samples', sa.Column('tiktok_creator_id', UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        'fk_samples_tiktok_creator',
        'samples', 'tiktok_creators',
        ['tiktok_creator_id'], ['id']
    )

    # Note: Not dropping old creator_* columns yet - will do in a follow-up migration after data is migrated


def downgrade() -> None:
    # Drop foreign key and column
    op.drop_constraint('fk_samples_tiktok_creator', 'samples', type_='foreignkey')
    op.drop_column('samples', 'tiktok_creator_id')

    # Drop tiktok_creators table
    op.drop_table('tiktok_creators')