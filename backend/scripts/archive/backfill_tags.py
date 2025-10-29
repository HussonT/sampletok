"""
Script to backfill tags for existing samples by extracting hashtags from descriptions.

Usage:
    python -m scripts.backfill_tags
"""
import asyncio
import logging
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models import Sample
from app.utils import extract_hashtags

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def backfill_tags(force: bool = False):
    """
    Backfill tags for all samples by extracting hashtags from descriptions.

    Args:
        force: If True, re-extract tags even if they already exist (useful for cleaning)
    """
    async with AsyncSessionLocal() as db:
        # Get all samples
        query = select(Sample)
        result = await db.execute(query)
        samples = result.scalars().all()

        logger.info(f"Found {len(samples)} samples to process (force={force})")

        updated_count = 0
        skipped_count = 0
        no_tags_count = 0

        for sample in samples:
            # Skip if tags already exist and we're not forcing re-extraction
            if not force and sample.tags and len(sample.tags) > 0:
                skipped_count += 1
                continue

            # Extract hashtags from description and title
            description_text = sample.description or ""
            title_text = sample.title or ""
            combined_text = f"{title_text} {description_text}"

            hashtags = extract_hashtags(combined_text)

            if hashtags:
                old_tags = sample.tags or []
                sample.tags = hashtags
                updated_count += 1
                if old_tags != hashtags:
                    logger.info(f"Sample {sample.id}: Updated tags from {old_tags} to {hashtags}")
                else:
                    logger.info(f"Sample {sample.id}: Tags unchanged: {hashtags}")
            else:
                sample.tags = []
                no_tags_count += 1
                logger.debug(f"Sample {sample.id}: No hashtags found")

        # Commit all changes
        await db.commit()

        logger.info(f"Backfill complete. Updated: {updated_count}, Skipped: {skipped_count}, No tags: {no_tags_count}")


if __name__ == "__main__":
    import sys
    # Check if --force flag is passed
    force = "--force" in sys.argv
    asyncio.run(backfill_tags(force=force))
