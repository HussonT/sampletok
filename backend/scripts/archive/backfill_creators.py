"""
Backfill creator information for existing sampless
"""
import asyncio
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models import Sample
from app.services.tiktok.creator_service import CreatorService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def backfill_creators():
    """Fetch and link creator info for samples that don't have it"""

    async with AsyncSessionLocal() as db:
        # Get samples without creator link but with username
        stmt = select(Sample).where(
            Sample.tiktok_creator_id.is_(None),
            Sample.creator_username.isnot(None),
            Sample.creator_username != ''
        )

        result = await db.execute(stmt)
        samples = result.scalars().all()

        logger.info(f"Found {len(samples)} samples to backfill")

        creator_service = CreatorService(db)

        for i, sample in enumerate(samples, 1):
            try:
                logger.info(f"[{i}/{len(samples)}] Processing @{sample.creator_username}")

                # Get or fetch creator
                creator = await creator_service.get_or_fetch_creator(sample.creator_username)

                if creator:
                    # Link sample to creator
                    sample.tiktok_creator_id = creator.id
                    await db.commit()
                    logger.info(f"✓ Linked to creator with {creator.follower_count} followers")
                else:
                    logger.warning(f"✗ Could not fetch creator info")

                # Small delay to avoid rate limiting
                await asyncio.sleep(0.5)

            except Exception as e:
                logger.error(f"Error processing sample {sample.id}: {e}")
                await db.rollback()
                continue

        logger.info("Backfill complete!")


if __name__ == "__main__":
    asyncio.run(backfill_creators())
