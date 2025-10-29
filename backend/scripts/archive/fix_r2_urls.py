"""
Fix R2 URLs in the database by reconstructing them with correct domain

This script updates malformed/broken R2 URLs in the database without reprocessing samples.
It extracts the object key from broken URLs and reconstructs them with the correct R2 domain.
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Optional
import re

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import AsyncSessionLocal
from app.models import Sample
from app.core.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def extract_object_key(broken_url: Optional[str]) -> Optional[str]:
    """Extract object key from a broken URL"""
    if not broken_url:
        return None

    # Try to extract the object key from various broken URL formats
    # Example broken: https://B17fde0__r2.cloudllarestorage.com/sampletok-samples/sample-...
    # Should be: pub-xxx.r2.dev/sample-...

    # Try to find the actual object key (after bucket name or domain)
    patterns = [
        r'sampletok-samples/(.+)$',  # After bucket name
        r'/([^/]+/[^/]+\.(mp3|wav|png|mp4|jpg|jpeg|webp))$',  # File path pattern
        r'sample-[a-f0-9-]+/[^/]+\.(mp3|wav|png|mp4|jpg|jpeg|webp)$',  # Sample ID pattern
    ]

    for pattern in patterns:
        match = re.search(pattern, broken_url)
        if match:
            return match.group(1) if match.lastindex >= 1 else match.group(0)

    logger.warning(f"Could not extract object key from: {broken_url}")
    return None


def construct_r2_url(object_key: str) -> str:
    """Construct proper R2 URL from object key"""
    r2_domain = settings.R2_PUBLIC_DOMAIN
    if not r2_domain:
        raise ValueError("R2_PUBLIC_DOMAIN not configured")

    return f"https://{r2_domain}/{object_key}"


async def fix_sample_urls(sample: Sample, db: AsyncSession, dry_run: bool = False) -> dict:
    """Fix URLs for a single sample"""
    fixed = {
        'wav_url': False,
        'mp3_url': False,
        'waveform_url': False,
        'video_url': False,
        'thumbnail_url': False,
        'cover_image_url': False
    }

    url_fields = [
        ('wav_url', sample.wav_url),
        ('mp3_url', sample.mp3_url),
        ('waveform_url', sample.waveform_url),
        ('video_url', sample.video_url),
        ('thumbnail_url', sample.thumbnail_url),
        ('cover_image_url', sample.cover_image_url),
    ]

    for field_name, current_url in url_fields:
        if not current_url:
            continue

        # Check if URL is broken (doesn't contain proper R2 domain)
        if settings.R2_PUBLIC_DOMAIN not in current_url:
            object_key = extract_object_key(current_url)
            if object_key:
                new_url = construct_r2_url(object_key)
                logger.info(f"  {field_name}: {current_url[:80]}... -> {new_url[:80]}...")

                if not dry_run:
                    setattr(sample, field_name, new_url)
                    fixed[field_name] = True
            else:
                logger.warning(f"  {field_name}: Could not extract key from {current_url}")

    if not dry_run and any(fixed.values()):
        await db.commit()

    return fixed


async def main(dry_run: bool = True, limit: Optional[int] = None):
    """Fix R2 URLs in database"""
    logger.info("="*60)
    logger.info("Starting R2 URL fix")
    logger.info(f"R2 Domain: {settings.R2_PUBLIC_DOMAIN}")
    logger.info(f"Storage Type: {settings.STORAGE_TYPE}")
    logger.info("="*60)

    if dry_run:
        logger.info("🔍 DRY RUN MODE - No changes will be made")

    stats = {
        'total': 0,
        'fixed': 0,
        'skipped': 0,
        'errors': 0,
    }

    async with AsyncSessionLocal() as db:
        # Find all completed samples
        query = select(Sample).order_by(Sample.created_at.desc())

        if limit:
            query = query.limit(limit)

        result = await db.execute(query)
        samples = result.scalars().all()

        stats['total'] = len(samples)
        logger.info(f"Found {len(samples)} samples to check\n")

        for i, sample in enumerate(samples, 1):
            # Check if any URLs are broken
            urls_to_check = [
                sample.wav_url,
                sample.mp3_url,
                sample.waveform_url,
                sample.video_url,
                sample.thumbnail_url,
                sample.cover_image_url
            ]

            has_broken_urls = any(
                url and settings.R2_PUBLIC_DOMAIN not in url
                for url in urls_to_check if url
            )

            if not has_broken_urls:
                stats['skipped'] += 1
                continue

            logger.info(f"[{i}/{len(samples)}] Fixing sample {sample.id}")
            logger.info(f"  Creator: @{sample.creator_username}")

            try:
                fixed = await fix_sample_urls(sample, db, dry_run)
                if any(fixed.values()):
                    stats['fixed'] += 1
                    fixed_fields = [k for k, v in fixed.items() if v]
                    logger.info(f"  ✓ Fixed fields: {', '.join(fixed_fields)}")
                else:
                    stats['skipped'] += 1
                    logger.info(f"  - No URLs fixed")

            except Exception as e:
                stats['errors'] += 1
                logger.error(f"  ✗ Error: {e}")

            logger.info("")

    # Print summary
    logger.info("="*60)
    logger.info("FIX COMPLETE" if not dry_run else "DRY RUN COMPLETE")
    logger.info("="*60)
    logger.info(f"Total samples checked: {stats['total']}")
    logger.info(f"Samples fixed: {stats['fixed']}")
    logger.info(f"Samples skipped: {stats['skipped']}")
    logger.info(f"Errors: {stats['errors']}")
    logger.info("="*60)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Fix broken R2 URLs in database')
    parser.add_argument(
        '--apply',
        action='store_true',
        help='Apply changes (default is dry run)'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Maximum number of samples to process'
    )

    args = parser.parse_args()

    asyncio.run(main(
        dry_run=not args.apply,
        limit=args.limit
    ))
