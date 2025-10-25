"""
Migration script to download and store all media to our infrastructure

This script will:
1. Download all TikTok videos and store them in our S3/R2
2. Download all thumbnails and cover images
3. Download all creator avatars
4. Update database with new URLs

Run from backend directory:
    python -m scripts.migrate_media_to_storage
"""

import asyncio
import logging
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import AsyncSessionLocal
from app.models import Sample, TikTokCreator
from app.services.storage.s3 import S3Storage
from app.services.tiktok.downloader import TikTokDownloader

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def migrate_sample_media(sample: Sample, storage: S3Storage, db: AsyncSession) -> bool:
    """
    Migrate all media for a single sample

    Returns True if successful, False otherwise
    """
    logger.info(f"Processing sample {sample.id} (@{sample.creator_username})")

    updated = False

    try:
        # 1. Download and store video if we have the external URL
        if sample.video_url and ('tiktok' in sample.video_url.lower() or 'tiktokcdn' in sample.video_url.lower()):
            logger.info(f"  Migrating video for sample {sample.id}")
            video_url = await storage.download_and_upload_url(
                sample.video_url,
                f"samples/{sample.id}/video.mp4",
                "video/mp4"
            )
            if video_url:
                sample.video_url = video_url
                updated = True
                logger.info(f"  ✓ Video migrated")
            else:
                logger.warning(f"  ✗ Failed to migrate video")

        # 2. Download and store thumbnail
        # Check if we have old metadata with thumbnail_url pointing to TikTok CDN
        if hasattr(sample, 'thumbnail_url') and sample.thumbnail_url:
            if 'tiktok' in sample.thumbnail_url.lower() or 'tiktokcdn' in sample.thumbnail_url.lower():
                logger.info(f"  Migrating thumbnail for sample {sample.id}")
                thumbnail_url = await storage.download_and_upload_url(
                    sample.thumbnail_url,
                    f"samples/{sample.id}/thumbnail.jpg",
                    "image/jpeg"
                )
                if thumbnail_url:
                    sample.thumbnail_url = thumbnail_url
                    updated = True
                    logger.info(f"  ✓ Thumbnail migrated")
                else:
                    logger.warning(f"  ✗ Failed to migrate thumbnail")

        # 3. Download and store cover image if available
        if hasattr(sample, 'cover_url') and sample.cover_url:
            if 'tiktok' in sample.cover_url.lower() or 'tiktokcdn' in sample.cover_url.lower():
                logger.info(f"  Migrating cover image for sample {sample.id}")
                cover_url = await storage.download_and_upload_url(
                    sample.cover_url,
                    f"samples/{sample.id}/cover.jpg",
                    "image/jpeg"
                )
                if cover_url:
                    sample.cover_url = cover_url
                    updated = True
                    logger.info(f"  ✓ Cover image migrated")
                else:
                    logger.warning(f"  ✗ Failed to migrate cover image")

        if updated:
            await db.commit()
            logger.info(f"✓ Sample {sample.id} migrated successfully")
        else:
            logger.info(f"  Sample {sample.id} already migrated or no external URLs")

        return True

    except Exception as e:
        logger.error(f"✗ Error migrating sample {sample.id}: {e}")
        await db.rollback()
        return False


async def migrate_creator_avatars(creator: TikTokCreator, storage: S3Storage, db: AsyncSession) -> bool:
    """
    Migrate creator avatars to our storage

    Returns True if successful, False otherwise
    """
    logger.info(f"Processing creator @{creator.username}")

    updated = False

    try:
        # Download and store avatars if they're external URLs
        creator_id = str(creator.id)

        if creator.avatar_thumb and ('tiktok' in creator.avatar_thumb.lower() or 'tiktokcdn' in creator.avatar_thumb.lower()):
            logger.info(f"  Migrating thumb avatar for @{creator.username}")
            thumb_url = await storage.download_and_upload_url(
                creator.avatar_thumb,
                f"creators/{creator_id}/avatar_thumb.jpg",
                "image/jpeg"
            )
            if thumb_url:
                creator.avatar_thumb = thumb_url
                updated = True
                logger.info(f"  ✓ Thumb avatar migrated")

        if creator.avatar_medium and ('tiktok' in creator.avatar_medium.lower() or 'tiktokcdn' in creator.avatar_medium.lower()):
            logger.info(f"  Migrating medium avatar for @{creator.username}")
            medium_url = await storage.download_and_upload_url(
                creator.avatar_medium,
                f"creators/{creator_id}/avatar_medium.jpg",
                "image/jpeg"
            )
            if medium_url:
                creator.avatar_medium = medium_url
                updated = True
                logger.info(f"  ✓ Medium avatar migrated")

        if creator.avatar_large and ('tiktok' in creator.avatar_large.lower() or 'tiktokcdn' in creator.avatar_large.lower()):
            logger.info(f"  Migrating large avatar for @{creator.username}")
            large_url = await storage.download_and_upload_url(
                creator.avatar_large,
                f"creators/{creator_id}/avatar_large.jpg",
                "image/jpeg"
            )
            if large_url:
                creator.avatar_large = large_url
                updated = True
                logger.info(f"  ✓ Large avatar migrated")

        if updated:
            await db.commit()
            logger.info(f"✓ Creator @{creator.username} migrated successfully")
        else:
            logger.info(f"  Creator @{creator.username} already migrated or no external URLs")

        return True

    except Exception as e:
        logger.error(f"✗ Error migrating creator @{creator.username}: {e}")
        await db.rollback()
        return False


async def main():
    """Main migration function"""
    logger.info("="*60)
    logger.info("Starting media migration to our storage")
    logger.info("="*60)

    storage = S3Storage()

    # Statistics
    stats = {
        'samples_total': 0,
        'samples_migrated': 0,
        'samples_failed': 0,
        'creators_total': 0,
        'creators_migrated': 0,
        'creators_failed': 0,
    }

    async with AsyncSessionLocal() as db:
        # 1. Migrate all samples
        logger.info("\n" + "="*60)
        logger.info("MIGRATING SAMPLES")
        logger.info("="*60)

        query = select(Sample).order_by(Sample.created_at.desc())
        result = await db.execute(query)
        samples = result.scalars().all()

        stats['samples_total'] = len(samples)
        logger.info(f"Found {len(samples)} samples to process\n")

        for i, sample in enumerate(samples, 1):
            logger.info(f"[{i}/{len(samples)}] Processing sample...")
            success = await migrate_sample_media(sample, storage, db)

            if success:
                stats['samples_migrated'] += 1
            else:
                stats['samples_failed'] += 1

            # Small delay to avoid rate limiting
            await asyncio.sleep(0.5)

        # 2. Migrate all creators
        logger.info("\n" + "="*60)
        logger.info("MIGRATING CREATORS")
        logger.info("="*60)

        query = select(TikTokCreator)
        result = await db.execute(query)
        creators = result.scalars().all()

        stats['creators_total'] = len(creators)
        logger.info(f"Found {len(creators)} creators to process\n")

        for i, creator in enumerate(creators, 1):
            logger.info(f"[{i}/{len(creators)}] Processing creator...")
            success = await migrate_creator_avatars(creator, storage, db)

            if success:
                stats['creators_migrated'] += 1
            else:
                stats['creators_failed'] += 1

            # Small delay to avoid rate limiting
            await asyncio.sleep(0.5)

    # Print summary
    logger.info("\n" + "="*60)
    logger.info("MIGRATION COMPLETE")
    logger.info("="*60)
    logger.info(f"\nSamples:")
    logger.info(f"  Total: {stats['samples_total']}")
    logger.info(f"  Migrated: {stats['samples_migrated']}")
    logger.info(f"  Failed: {stats['samples_failed']}")
    logger.info(f"\nCreators:")
    logger.info(f"  Total: {stats['creators_total']}")
    logger.info(f"  Migrated: {stats['creators_migrated']}")
    logger.info(f"  Failed: {stats['creators_failed']}")
    logger.info("\n" + "="*60)


if __name__ == "__main__":
    asyncio.run(main())
