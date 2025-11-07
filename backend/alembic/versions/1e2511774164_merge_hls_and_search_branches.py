"""merge hls and search branches

Revision ID: 1e2511774164
Revises: 8577e3e22893, b2c3d4e5f6a7
Create Date: 2025-11-06 17:39:41.092382

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1e2511774164'
down_revision = ('8577e3e22893', 'b2c3d4e5f6a7')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass