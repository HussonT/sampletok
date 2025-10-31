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
    # Get database connection
    connection = op.get_bind()

    # Fetch all samples with titles
    result = connection.execute(sa.text("SELECT id, title FROM samples WHERE title IS NOT NULL"))
    samples = result.fetchall()

    # Update each sample's title to remove hashtags
    for sample_id, title in samples:
        if title and '#' in title:
            cleaned_title = remove_hashtags(title)
            if cleaned_title != title:
                connection.execute(
                    sa.text("UPDATE samples SET title = :cleaned_title WHERE id = :sample_id"),
                    {"cleaned_title": cleaned_title, "sample_id": sample_id}
                )

    # No need to commit - Alembic manages transactions automatically


def downgrade() -> None:
    # No downgrade needed - we can't restore the original hashtags
    pass