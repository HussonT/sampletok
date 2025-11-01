"""remove_hashtags_from_titles

Revision ID: c59169fb76ec
Revises: ca613d944f79
Create Date: 2025-10-28 17:53:22.011827

"""
from alembic import op
import sqlalchemy as sa
import re


# revision identifiers, used by Alembic.
revision = 'c59169fb76ec'
down_revision = 'ca613d944f79'
branch_labels = None
depends_on = None


def remove_hashtags(text: str) -> str:
    """Remove hashtags from text."""
    if not text:
        return text
    # Remove hashtags and clean up extra spaces
    text_without_hashtags = re.sub(r'#\w+', '', text)
    # Clean up multiple spaces and strip
    text_cleaned = re.sub(r'\s+', ' ', text_without_hashtags).strip()
    return text_cleaned


def upgrade() -> None:
    # This migration previously contained a data cleanup operation
    # Data operations should be in backend/scripts/sql/ instead
    # If you need to clean hashtags from titles, use the SQL script:
    # backend/scripts/sql/remove_hashtags_from_titles.sql
    pass


def downgrade() -> None:
    # No downgrade needed - we can't restore the original hashtags
    pass