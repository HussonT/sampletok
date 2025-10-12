#!/usr/bin/env python3
"""
Cleanup script for orphaned/incomplete samples in the database!

This script identifies and optionally removes sample records that:
1. Have status != COMPLETED
2. Are missing essential fields (creator_username, title, audio_url_mp3, waveform_url)
3. Have been stuck in PENDING/PROCESSING for too long

Usage (run from backend/ directory):
    # Dry run (show what would be deleted, don't actually delete)
    python scripts/cleanup_orphaned_samples.py --dry-run

    # Delete incomplete samples
    python scripts/cleanup_orphaned_samples.py --delete

    # Delete samples older than N days
    python scripts/cleanup_orphaned_samples.py --delete --days 7

    # Show statistics only
    python scripts/cleanup_orphaned_samples.py --stats
"""

import asyncio
import argparse
import sys
from pathlib import Path
from datetime import datetime, timedelta
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Add parent directory to path so we can import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.models import Sample, ProcessingStatus
from app.core.config import settings


async def get_orphaned_samples(session: AsyncSession, days_old: int = None):
    """Find samples that are incomplete or orphaned."""

    # Build query for orphaned samples
    query = select(Sample).where(
        or_(
            # Incomplete processing status
            Sample.status != ProcessingStatus.COMPLETED,
            # Missing essential metadata
            Sample.creator_username.is_(None),
            Sample.creator_username == '',
            Sample.title.is_(None),
            Sample.title == '',
            # Missing essential files
            Sample.audio_url_mp3.is_(None),
            Sample.audio_url_mp3 == '',
            Sample.waveform_url.is_(None),
            Sample.waveform_url == ''
        )
    )

    # Optional: only clean up old records
    if days_old:
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        query = query.where(Sample.created_at < cutoff_date)

    result = await session.execute(query)
    return result.scalars().all()


async def get_statistics(session: AsyncSession):
    """Get statistics about sample states."""

    # Total samples
    total_result = await session.execute(select(func.count(Sample.id)))
    total = total_result.scalar()

    # By status
    status_counts = {}
    for status in ProcessingStatus:
        result = await session.execute(
            select(func.count(Sample.id)).where(Sample.status == status)
        )
        status_counts[status.value] = result.scalar()

    # Missing essential fields
    missing_username = await session.execute(
        select(func.count(Sample.id)).where(
            or_(Sample.creator_username.is_(None), Sample.creator_username == '')
        )
    )

    missing_title = await session.execute(
        select(func.count(Sample.id)).where(
            or_(Sample.title.is_(None), Sample.title == '')
        )
    )

    missing_audio = await session.execute(
        select(func.count(Sample.id)).where(
            or_(Sample.audio_url_mp3.is_(None), Sample.audio_url_mp3 == '')
        )
    )

    missing_waveform = await session.execute(
        select(func.count(Sample.id)).where(
            or_(Sample.waveform_url.is_(None), Sample.waveform_url == '')
        )
    )

    return {
        'total': total,
        'by_status': status_counts,
        'missing_fields': {
            'creator_username': missing_username.scalar(),
            'title': missing_title.scalar(),
            'audio_url_mp3': missing_audio.scalar(),
            'waveform_url': missing_waveform.scalar()
        }
    }


async def delete_samples(session: AsyncSession, samples: list):
    """Delete the given samples from database."""
    for sample in samples:
        await session.delete(sample)
    await session.commit()


def print_sample_info(sample: Sample):
    """Print information about a sample."""
    print(f"  ID: {sample.id}")
    print(f"  Status: {sample.status.value}")
    print(f"  Created: {sample.created_at}")
    print(f"  TikTok URL: {sample.tiktok_url}")
    print(f"  Creator: {sample.creator_username or '(missing)'}")
    print(f"  Title: {sample.title or '(missing)'}")
    print(f"  Audio URL: {sample.audio_url_mp3 or '(missing)'}")
    print(f"  Waveform URL: {sample.waveform_url or '(missing)'}")
    if sample.error_message:
        print(f"  Error: {sample.error_message}")
    print()


async def main():
    parser = argparse.ArgumentParser(
        description='Clean up orphaned/incomplete samples from database'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be deleted without actually deleting'
    )
    parser.add_argument(
        '--delete',
        action='store_true',
        help='Actually delete orphaned samples'
    )
    parser.add_argument(
        '--stats',
        action='store_true',
        help='Show statistics about samples'
    )
    parser.add_argument(
        '--days',
        type=int,
        default=None,
        help='Only clean up samples older than N days'
    )

    args = parser.parse_args()

    # Create database connection
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False
    )

    async_session = sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    async with async_session() as session:
        # Show statistics
        if args.stats:
            print("\n=== Sample Statistics ===\n")
            stats = await get_statistics(session)

            print(f"Total samples: {stats['total']}")
            print("\nBy status:")
            for status, count in stats['by_status'].items():
                print(f"  {status}: {count}")

            print("\nSamples missing essential fields:")
            for field, count in stats['missing_fields'].items():
                print(f"  {field}: {count}")
            print()

            return

        # Find orphaned samples
        print("\n=== Finding orphaned samples ===\n")
        if args.days:
            print(f"Looking for samples older than {args.days} days...")

        orphaned = await get_orphaned_samples(session, args.days)

        if not orphaned:
            print("✓ No orphaned samples found!")
            return

        print(f"Found {len(orphaned)} orphaned/incomplete samples:\n")

        # Show details
        for sample in orphaned:
            print_sample_info(sample)

        # Delete if requested
        if args.delete:
            confirm = input(f"\nAre you sure you want to DELETE {len(orphaned)} samples? (yes/no): ")
            if confirm.lower() == 'yes':
                print("\nDeleting samples...")
                await delete_samples(session, orphaned)
                print(f"✓ Deleted {len(orphaned)} samples")
            else:
                print("Cancelled.")
        elif not args.dry_run:
            print("\nℹ Run with --delete to actually remove these samples")
            print("  or --dry-run to preview without changes")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())