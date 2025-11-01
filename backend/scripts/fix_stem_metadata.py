"""
Fix stem BPM and key values by copying from parent samples.

Stems should always have the same BPM and key as their parent sample
since they're extracted from the same audio.
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import AsyncSessionLocal
from app.models import Stem, Sample, StemProcessingStatus
from sqlalchemy import select, update
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def fix_stem_metadata():
    """Update all stems to have the same BPM and key as their parent samples"""

    async with AsyncSessionLocal() as db:
        # Get all stems with their parent samples
        query = select(Stem).where(Stem.status == StemProcessingStatus.COMPLETED)
        result = await db.execute(query)
        stems = result.scalars().all()

        logger.info(f"Found {len(stems)} completed stems to check")

        updated_count = 0
        for stem in stems:
            # Get parent sample
            sample_query = select(Sample).where(Sample.id == stem.parent_sample_id)
            sample_result = await db.execute(sample_query)
            parent_sample = sample_result.scalars().first()

            if not parent_sample:
                logger.warning(f"Parent sample not found for stem {stem.id}")
                continue

            # Check if metadata needs updating
            needs_update = False
            if stem.bpm != parent_sample.bpm:
                logger.info(f"Stem {stem.id} ({stem.stem_type}): Updating BPM from {stem.bpm} to {parent_sample.bpm}")
                stem.bpm = parent_sample.bpm
                needs_update = True

            if stem.key != parent_sample.key:
                logger.info(f"Stem {stem.id} ({stem.stem_type}): Updating key from '{stem.key}' to '{parent_sample.key}'")
                stem.key = parent_sample.key
                needs_update = True

            # Also fix duration if it's significantly different (should be the same)
            if stem.duration_seconds and parent_sample.duration_seconds:
                # Allow 0.1s tolerance for rounding
                duration_diff = abs(stem.duration_seconds - parent_sample.duration_seconds)
                if duration_diff > 0.1:
                    logger.info(f"Stem {stem.id} ({stem.stem_type}): Updating duration from {stem.duration_seconds}s to {parent_sample.duration_seconds}s")
                    stem.duration_seconds = parent_sample.duration_seconds
                    needs_update = True

            if needs_update:
                updated_count += 1

        if updated_count > 0:
            await db.commit()
            logger.info(f"✅ Updated metadata for {updated_count} stems")
        else:
            logger.info("✅ No stems needed updating - all metadata is correct!")


if __name__ == "__main__":
    asyncio.run(fix_stem_metadata())
