"""add creator_follower_count to samples

Revision ID: 1a64b887e7c9
Revises: add_rapidapi_fields
Create Date: 2025-10-11 11:56:00.163511

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1a64b887e7c9'
down_revision = 'add_rapidapi_fields'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('samples', sa.Column('creator_follower_count', sa.Integer(), nullable=True, server_default='0'))


def downgrade() -> None:
    op.drop_column('samples', 'creator_follower_count')