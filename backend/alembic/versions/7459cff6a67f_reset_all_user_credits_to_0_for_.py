"""Reset all user credits to 0 for subscription system

Revision ID: 7459cff6a67f
Revises: 9a17a2853027
Create Date: 2025-10-30 18:22:31.343377

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7459cff6a67f'
down_revision = '9a17a2853027'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # This migration previously contained a data operation to reset credits
    # Data operations should be in backend/scripts/sql/ instead
    # Subscription system should handle credit allocation
    pass


def downgrade() -> None:
    # Cannot restore previous credit values - this is a one-way migration
    # Users will need to have credits granted via subscription system
    pass