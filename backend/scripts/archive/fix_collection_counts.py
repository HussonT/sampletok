#!/usr/bin/env python3
"""
Migration script to fix collection video counts.
Updates total_video_count to reflect only valid videos (not including invalid/deleted ones).
"""
import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import AsyncSessionLocal
from app.models import Collection
from app.services.tiktok.collection_service import TikTokCollectionService
from sqlalchemy import select
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def get_valid_video_count(tiktok_collection_id: str) -> int:
    """Get actual count of valid videos that can be processed"""
    try:
        service = TikTokCollectionService()
        result = await service.fetch_collection_posts(
            collection_id=tiktok_collection_id,
            count=30,
            cursor=0
        )

        data = result.get('data', {})
        videos = data.get('videos', [])

        # Same filter as in endpoints
        valid_videos = [
            v for v in videos
            if (v.get('video_id') and
                v.get('author', {}).get('unique_id'))
        ]

        return len(valid_videos)

    except Exception as e:
        logger.error(f"Error fetching collection {tiktok_collection_id}: {e}")
        return -1


async def fix_all_collections():
    """Fix video counts for all collections"""
    print("\n" + "="*80)
    print("FIXING COLLECTION VIDEO COUNTS")
    print("="*80 + "\n")

    async with AsyncSessionLocal() as db:
        # Get all collections
        query = select(Collection).order_by(Collection.created_at.desc())
        result = await db.execute(query)
        collections = result.scalars().all()

        if not collections:
            print("No collections found.")
            return

        print(f"Found {len(collections)} collections to check\n")

        fixed_count = 0
        skipped_count = 0
        error_count = 0

        for collection in collections:
            print(f"📦 Collection: {collection.name}")
            print(f"   User: @{collection.tiktok_username}")
            print(f"   Current count: {collection.total_video_count}")

            # Fetch actual valid count
            valid_count = await get_valid_video_count(collection.tiktok_collection_id)

            if valid_count == -1:
                print(f"   ❌ Error fetching from TikTok API")
                error_count += 1
                print()
                continue

            print(f"   Actual valid: {valid_count}")

            if collection.total_video_count == valid_count:
                print(f"   ✓ Already correct")
                skipped_count += 1
            else:
                old_count = collection.total_video_count
                collection.total_video_count = valid_count
                print(f"   ✅ Fixed: {old_count} → {valid_count}")
                fixed_count += 1

            print()

        # Commit all changes
        await db.commit()

        print("="*80)
        print("SUMMARY")
        print("="*80)
        print(f"Total collections: {len(collections)}")
        print(f"Fixed:             {fixed_count}")
        print(f"Already correct:   {skipped_count}")
        print(f"Errors:            {error_count}")
        print("="*80 + "\n")


if __name__ == "__main__":
    asyncio.run(fix_all_collections())
