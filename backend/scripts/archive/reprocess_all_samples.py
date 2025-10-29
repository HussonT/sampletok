"""
Reprocess all existing samples through the complete pipeline

This script will:
1. Find all existing samples
2. Delete old files from storage (optional)
3. Trigger the full Inngest pipeline for each sample
   - Download video from TikTok
   - Extract audio (WAV + MP3)
   - Generate waveform
   - Analyze BPM/key
   - Download and store video, thumbnails, covers
   - Download and store creator avatars
   - Upload everything to our storage

Run from backend directory:
    python -m scripts.reprocess_all_samples
"""

import asyncio
import logging
from pathlib import Path
import sys
from typing import List, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import AsyncSessionLocal
from app.models import Sample, ProcessingStatus
from app.core.config import settings
import inngest

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def trigger_reprocessing(sample: Sample) -> bool:
    """
    Trigger the Inngest pipeline for a sample

    Returns True if successfully triggered, False otherwise
    """
    if not sample.tiktok_url:
        logger.warning(f"  Sample {sample.id} has no TikTok URL, skipping")
        return False

    try:
        # Get Inngest client
        from app.inngest_functions import inngest_client

        # Send event to Inngest to trigger processing
        await inngest_client.send(
            inngest.Event(
                name="tiktok/video.submitted",
                data={
                    "sample_id": str(sample.id),
                    "url": sample.tiktok_url
                }
            )
        )

        logger.info(f"  ✓ Pipeline triggered for sample {sample.id}")
        return True

    except Exception as e:
        logger.error(f"  ✗ Error triggering pipeline for sample {sample.id}: {e}")
        return False


async def reset_sample_status(sample: Sample, db: AsyncSession) -> None:
    """Reset sample to pending status for reprocessing"""
    try:
        sample.status = ProcessingStatus.PENDING
        sample.error_message = None
        await db.commit()
        logger.info(f"  Reset sample {sample.id} to pending")
    except Exception as e:
        logger.error(f"  Error resetting sample status: {e}")
        await db.rollback()


async def main(
    filter_status: Optional[str] = None,
    limit: Optional[int] = None,
    skip_reset: bool = False,
    dry_run: bool = False,
    auto_confirm: bool = False
):
    """
    Main reprocessing function

    Args:
        filter_status: Only reprocess samples with this status (e.g., "completed", "failed")
        limit: Maximum number of samples to reprocess
        skip_reset: Don't reset status to pending (useful for testing)
        dry_run: Just show what would be processed without actually triggering
        auto_confirm: Skip confirmation prompt and proceed automatically
    """
    logger.info("="*60)
    logger.info("Starting sample reprocessing")
    logger.info("="*60)

    if dry_run:
        logger.info("🔍 DRY RUN MODE - No actual processing will occur")

    stats = {
        'total': 0,
        'triggered': 0,
        'failed': 0,
        'skipped': 0,
    }

    async with AsyncSessionLocal() as db:
        # Build query
        query = select(Sample).order_by(Sample.created_at.desc())

        if filter_status:
            status_enum = ProcessingStatus(filter_status)
            query = query.where(Sample.status == status_enum)
            logger.info(f"Filtering by status: {filter_status}")

        result = await db.execute(query)
        samples = result.scalars().all()

        if limit:
            samples = samples[:limit]
            logger.info(f"Limited to first {limit} samples")

        stats['total'] = len(samples)
        logger.info(f"Found {len(samples)} samples to reprocess\n")

        if stats['total'] == 0:
            logger.info("No samples to process. Exiting.")
            return

        # Ask for confirmation
        if not dry_run and not auto_confirm:
            print("\n" + "⚠️  WARNING " + "="*50)
            print(f"This will reprocess {len(samples)} samples through the FULL pipeline:")
            print("  - Download video from TikTok")
            print("  - Extract audio (WAV + MP3)")
            print("  - Generate waveforms")
            print("  - Analyze BPM/key")
            print("  - Download and store all media")
            print("  - This may take a while and consume TikTok API credits")
            print("="*60)

            confirm = input("\nType 'yes' to continue: ")
            if confirm.lower() != 'yes':
                logger.info("Cancelled by user")
                return
            print()
        elif not dry_run and auto_confirm:
            logger.info(f"Auto-confirmed: Processing {len(samples)} samples")

        # Process each sample
        for i, sample in enumerate(samples, 1):
            logger.info(f"[{i}/{len(samples)}] Processing sample {sample.id}")
            logger.info(f"  URL: {sample.tiktok_url}")
            logger.info(f"  Creator: @{sample.creator_username}")
            logger.info(f"  Current status: {sample.status.value}")

            if dry_run:
                logger.info(f"  [DRY RUN] Would trigger reprocessing")
                stats['triggered'] += 1
            else:
                # Reset status if requested
                if not skip_reset:
                    await reset_sample_status(sample, db)

                # Trigger reprocessing
                success = await trigger_reprocessing(sample)

                if success:
                    stats['triggered'] += 1
                else:
                    stats['failed'] += 1

                # Small delay to avoid overwhelming the system
                await asyncio.sleep(2)

            logger.info("")

    # Print summary
    logger.info("="*60)
    logger.info("REPROCESSING COMPLETE" if not dry_run else "DRY RUN COMPLETE")
    logger.info("="*60)
    logger.info(f"\nTotal samples: {stats['total']}")
    logger.info(f"Successfully triggered: {stats['triggered']}")
    logger.info(f"Failed: {stats['failed']}")
    logger.info(f"Skipped: {stats['skipped']}")

    if not dry_run:
        logger.info("\n💡 Monitor processing progress:")
        logger.info("   - Check Inngest dashboard: http://localhost:8288")
        logger.info("   - Watch backend logs for processing updates")

    logger.info("\n" + "="*60)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Reprocess samples through the full pipeline')
    parser.add_argument(
        '--status',
        choices=['pending', 'processing', 'completed', 'failed'],
        help='Only reprocess samples with this status'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Maximum number of samples to reprocess'
    )
    parser.add_argument(
        '--skip-reset',
        action='store_true',
        help='Don\'t reset sample status to pending'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be processed without actually doing it'
    )
    parser.add_argument(
        '--yes',
        action='store_true',
        help='Skip confirmation prompt and proceed automatically'
    )

    args = parser.parse_args()

    asyncio.run(main(
        filter_status=args.status,
        limit=args.limit,
        skip_reset=args.skip_reset,
        dry_run=args.dry_run,
        auto_confirm=args.yes
    ))
