#!/usr/bin/env python3
"""
Backfill HLS streams for existing samples

This script:
1. Finds all samples that have MP3 files but no HLS playlist
2. Downloads the MP3 from storage
3. Generates HLS segments (m3u8 + .ts files)
4. Uploads segments to storage
5. Updates database with HLS URL

Usage:
    python scripts/backfill_hls_streams.py --dry-run  # Preview what will be processed
    python scripts/backfill_hls_streams.py            # Actually process samples
    python scripts/backfill_hls_streams.py --limit 10 # Process only 10 samples
    python scripts/backfill_hls_streams.py --sample-id <uuid>  # Process specific sample
"""

import asyncio
import argparse
import logging
import sys
import tempfile
from pathlib import Path
from typing import List, Optional
from uuid import UUID

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models.sample import Sample, ProcessingStatus
from app.services.audio.processor import AudioProcessor
from app.services.storage.s3 import S3Storage

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def get_samples_without_hls(
    limit: Optional[int] = None,
    sample_id: Optional[str] = None
) -> List[Sample]:
    """
    Get all completed samples that have MP3 but no HLS playlist

    Args:
        limit: Maximum number of samples to return
        sample_id: If provided, only get this specific sample

    Returns:
        List of Sample objects
    """
    async with AsyncSessionLocal() as db:
        query = select(Sample).where(
            Sample.status == ProcessingStatus.COMPLETED,
            Sample.audio_url_mp3.isnot(None),
            Sample.audio_url_hls.is_(None)
        )

        if sample_id:
            query = query.where(Sample.id == UUID(sample_id))

        if limit:
            query = query.limit(limit)

        result = await db.execute(query)
        samples = result.scalars().all()

        return list(samples)


async def get_total_samples_without_hls() -> int:
    """Get count of samples that need HLS processing"""
    async with AsyncSessionLocal() as db:
        query = select(func.count()).select_from(Sample).where(
            Sample.status == ProcessingStatus.COMPLETED,
            Sample.audio_url_mp3.isnot(None),
            Sample.audio_url_hls.is_(None)
        )
        result = await db.execute(query)
        count = result.scalar()
        return count or 0


async def process_sample_hls(sample: Sample, dry_run: bool = False) -> bool:
    """
    Generate and upload HLS stream for a single sample

    Args:
        sample: Sample object to process
        dry_run: If True, don't actually process, just log what would happen

    Returns:
        True if successful, False otherwise
    """
    logger.info(f"Processing sample {sample.id} - {sample.creator_username}")

    if dry_run:
        logger.info(f"  [DRY RUN] Would generate HLS for MP3: {sample.audio_url_mp3}")
        return True

    temp_dir = None
    try:
        # Create temporary directory for processing
        temp_dir = tempfile.mkdtemp(prefix=f"hls_{sample.id}_")
        temp_path = Path(temp_dir)

        logger.info(f"  Downloading MP3 from storage...")

        # Download MP3 from storage
        storage = S3Storage()
        mp3_filename = f"{sample.id}.mp3"
        mp3_path = temp_path / mp3_filename

        # Extract the object key from the URL
        # URL format: https://domain/samples/{sample_id}/audio.mp3
        mp3_url = sample.audio_url_mp3
        if '/samples/' in mp3_url:
            # Extract object key: samples/{sample_id}/audio.mp3
            object_key = mp3_url.split('/samples/')[-1]
            object_key = f"samples/{object_key}"
        else:
            logger.error(f"  Could not parse MP3 URL: {mp3_url}")
            return False

        # Download the file
        try:
            await storage.download_file(object_key, str(mp3_path))
        except Exception as e:
            logger.error(f"  Failed to download MP3: {e}")
            logger.info(f"  Trying alternative download method via URL...")

            # Fallback: download via HTTP
            import httpx
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(mp3_url)
                response.raise_for_status()
                mp3_path.write_bytes(response.content)

        if not mp3_path.exists():
            logger.error(f"  MP3 file does not exist after download: {mp3_path}")
            return False

        logger.info(f"  MP3 downloaded: {mp3_path.stat().st_size / 1024 / 1024:.2f} MB")

        # Generate HLS stream
        logger.info(f"  Generating HLS stream...")
        processor = AudioProcessor()
        hls_data = await processor.generate_hls_stream(str(mp3_path), temp_dir)

        num_segments = len(hls_data['segments'])
        logger.info(f"  Generated {num_segments} HLS segments")

        # Upload playlist
        logger.info(f"  Uploading HLS playlist...")
        playlist_url = await storage.upload_file(
            hls_data['playlist'],
            f"samples/{sample.id}/hls/playlist.m3u8"
        )
        logger.info(f"  Playlist uploaded: {playlist_url}")

        # Upload all segments
        logger.info(f"  Uploading {num_segments} HLS segments...")
        for i, segment_path in enumerate(hls_data['segments'], 1):
            segment_filename = Path(segment_path).name
            await storage.upload_file(
                segment_path,
                f"samples/{sample.id}/hls/{segment_filename}"
            )
            if i % 5 == 0:  # Log every 5 segments
                logger.info(f"    Uploaded {i}/{num_segments} segments")

        logger.info(f"  All segments uploaded")

        # Update database
        logger.info(f"  Updating database...")
        async with AsyncSessionLocal() as db:
            # Re-fetch sample in this session
            result = await db.execute(
                select(Sample).where(Sample.id == sample.id)
            )
            db_sample = result.scalar_one()
            db_sample.audio_url_hls = playlist_url
            await db.commit()

        logger.info(f"  ✅ Successfully processed sample {sample.id}")
        return True

    except Exception as e:
        logger.error(f"  ❌ Error processing sample {sample.id}: {e}", exc_info=True)
        return False

    finally:
        # Cleanup temp directory
        if temp_dir and Path(temp_dir).exists():
            import shutil
            try:
                shutil.rmtree(temp_dir)
                logger.info(f"  Cleaned up temp directory")
            except Exception as e:
                logger.warning(f"  Failed to cleanup temp directory: {e}")


async def main():
    parser = argparse.ArgumentParser(
        description='Backfill HLS streams for existing samples'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview what would be processed without actually doing it'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Maximum number of samples to process'
    )
    parser.add_argument(
        '--sample-id',
        type=str,
        help='Process only this specific sample ID'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=1,
        help='Number of samples to process concurrently (default: 1, be careful with higher values)'
    )

    args = parser.parse_args()

    # Get total count
    if args.sample_id:
        logger.info(f"Processing specific sample: {args.sample_id}")
    else:
        total = await get_total_samples_without_hls()
        logger.info(f"Found {total} samples without HLS streams")

        if total == 0:
            logger.info("No samples need HLS processing. Exiting.")
            return

        if args.limit:
            logger.info(f"Will process up to {args.limit} samples")

    if args.dry_run:
        logger.info("DRY RUN MODE - No actual processing will occur")

    # Get samples to process
    samples = await get_samples_without_hls(
        limit=args.limit,
        sample_id=args.sample_id
    )

    if not samples:
        logger.info("No samples found to process")
        return

    logger.info(f"\nProcessing {len(samples)} samples...")
    logger.info("=" * 80)

    # Process samples
    success_count = 0
    failure_count = 0

    for i, sample in enumerate(samples, 1):
        logger.info(f"\n[{i}/{len(samples)}] Sample: {sample.id}")
        logger.info(f"  Creator: {sample.creator_username}")
        logger.info(f"  Duration: {sample.duration_seconds:.1f}s")
        logger.info(f"  MP3 URL: {sample.audio_url_mp3}")

        success = await process_sample_hls(sample, dry_run=args.dry_run)

        if success:
            success_count += 1
        else:
            failure_count += 1

        logger.info(f"  Progress: {success_count} succeeded, {failure_count} failed")

        # Small delay between samples to avoid overwhelming the system
        if i < len(samples):
            await asyncio.sleep(1)

    # Final summary
    logger.info("\n" + "=" * 80)
    logger.info("SUMMARY")
    logger.info("=" * 80)
    logger.info(f"Total processed: {len(samples)}")
    logger.info(f"Successful: {success_count}")
    logger.info(f"Failed: {failure_count}")

    if args.dry_run:
        logger.info("\nThis was a DRY RUN. Run without --dry-run to actually process samples.")


if __name__ == "__main__":
    asyncio.run(main())
