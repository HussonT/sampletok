"""
Fix creator avatar URLs in database

Updates creator avatar URLs from broken internal R2 endpoint to public R2 domain
"""

import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import AsyncSessionLocal
from app.models.tiktok_creator import TikTokCreator
from app.core.config import settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def fix_url(old_url: str) -> str:
    """Convert broken R2 URL to public R2 domain URL"""
    if not old_url:
        return old_url

    # If already using public domain, no change needed
    if settings.R2_PUBLIC_DOMAIN in old_url:
        return old_url

    # Extract the path after bucket name
    # Old: https://817fde014b86ba18d60b1820218aece1.r2.cloudflarestorage.com/sampletok-samples/creators/...
    # New: https://pub-xxx.r2.dev/creators/...

    if '/sampletok-samples/' in old_url:
        # Extract everything after bucket name
        path = old_url.split('/sampletok-samples/')[-1]
        return f"https://{settings.R2_PUBLIC_DOMAIN}/{path}"

    return old_url


async def fix_creator_avatars(dry_run: bool = True):
    """Fix all creator avatar URLs"""
    logger.info("="*60)
    logger.info("Starting creator avatar URL fix")
    logger.info(f"R2 Public Domain: {settings.R2_PUBLIC_DOMAIN}")
    logger.info(f"Storage Type: {settings.STORAGE_TYPE}")
    logger.info("="*60)

    if dry_run:
        logger.info("🔍 DRY RUN MODE - No changes will be made")

    stats = {
        'total': 0,
        'fixed': 0,
        'skipped': 0,
    }

    async with AsyncSessionLocal() as db:
        # Get all creators
        query = select(TikTokCreator)
        result = await db.execute(query)
        creators = result.scalars().all()

        stats['total'] = len(creators)
        logger.info(f"Found {len(creators)} creators to check\n")

        for i, creator in enumerate(creators, 1):
            # Check if any avatar URLs need fixing
            needs_fix = False

            if creator.avatar_thumb and settings.R2_PUBLIC_DOMAIN not in creator.avatar_thumb:
                needs_fix = True
            if creator.avatar_medium and settings.R2_PUBLIC_DOMAIN not in creator.avatar_medium:
                needs_fix = True
            if creator.avatar_large and settings.R2_PUBLIC_DOMAIN not in creator.avatar_large:
                needs_fix = True

            if not needs_fix:
                stats['skipped'] += 1
                continue

            logger.info(f"[{i}/{len(creators)}] Fixing @{creator.username}")

            # Fix URLs
            if creator.avatar_thumb:
                new_thumb = fix_url(creator.avatar_thumb)
                logger.info(f"  thumb: {creator.avatar_thumb[:60]}... -> {new_thumb[:60]}...")
                if not dry_run:
                    creator.avatar_thumb = new_thumb

            if creator.avatar_medium:
                new_medium = fix_url(creator.avatar_medium)
                logger.info(f"  medium: {creator.avatar_medium[:60]}... -> {new_medium[:60]}...")
                if not dry_run:
                    creator.avatar_medium = new_medium

            if creator.avatar_large:
                new_large = fix_url(creator.avatar_large)
                logger.info(f"  large: {creator.avatar_large[:60]}... -> {new_large[:60]}...")
                if not dry_run:
                    creator.avatar_large = new_large

            stats['fixed'] += 1
            logger.info("")

        if not dry_run:
            await db.commit()
            logger.info("✅ Committed changes to database")

    # Print summary
    logger.info("="*60)
    logger.info("FIX COMPLETE" if not dry_run else "DRY RUN COMPLETE")
    logger.info("="*60)
    logger.info(f"Total creators: {stats['total']}")
    logger.info(f"Fixed: {stats['fixed']}")
    logger.info(f"Skipped (already correct): {stats['skipped']}")
    logger.info("="*60)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Fix creator avatar URLs in database')
    parser.add_argument(
        '--apply',
        action='store_true',
        help='Apply changes (default is dry run)'
    )

    args = parser.parse_args()

    asyncio.run(fix_creator_avatars(dry_run=not args.apply))
