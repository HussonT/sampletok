#!/usr/bin/env python3
"""
Debug script to analyze TikTok collection video data and filtering logic
"""
import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.tiktok.collection_service import TikTokCollectionService


async def debug_collection(collection_id: str, collection_name: str):
    """Fetch and analyze collection data"""
    print(f"\n{'='*80}")
    print(f"Analyzing Collection: {collection_name}")
    print(f"Collection ID: {collection_id}")
    print(f"{'='*80}\n")

    service = TikTokCollectionService()

    try:
        # Fetch data
        result = await service.fetch_collection_posts(
            collection_id=collection_id,
            count=30,
            cursor=0
        )

        data = result.get('data', {})
        videos = data.get('videos', [])

        print(f"📊 Total videos returned by API: {len(videos)}\n")

        # Analyze each video
        valid_count = 0
        invalid_count = 0

        for i, video in enumerate(videos, 1):
            video_id = video.get('video_id')
            aweme_id = video.get('aweme_id')
            author = video.get('author', {})
            author_id = author.get('id')
            author_unique_id = author.get('unique_id')

            # Check our filter
            is_valid = bool(video_id and author_unique_id)

            status = "✅ VALID" if is_valid else "❌ INVALID"

            print(f"Video #{i}: {status}")
            print(f"  video_id: {video_id or 'MISSING'}")
            print(f"  aweme_id: {aweme_id or 'MISSING'}")
            print(f"  author.id: {author_id or 'MISSING'}")
            print(f"  author.unique_id: {author_unique_id or 'MISSING'}")

            if not is_valid:
                print(f"  🔍 WHY INVALID:")
                if not video_id:
                    print(f"     - Missing video_id")
                if not author_unique_id:
                    print(f"     - Missing author.unique_id")

            print()

            if is_valid:
                valid_count += 1
            else:
                invalid_count += 1

        print(f"\n{'='*80}")
        print(f"📈 SUMMARY")
        print(f"{'='*80}")
        print(f"Total returned: {len(videos)}")
        print(f"Valid videos:   {valid_count}")
        print(f"Invalid videos: {invalid_count}")
        print(f"{'='*80}\n")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """Debug both collections"""

    # Inspiration - shows 5/6 in UI (database says 6 videos)
    await debug_collection(
        collection_id="7565939439155890976",
        collection_name="Inspiration (@musicbycope)"
    )

    # To sample - shows 21/22 in UI (database says 22 videos)
    await debug_collection(
        collection_id="7565254233776196385",
        collection_name="To sample (@musicbycope)"
    )


if __name__ == "__main__":
    asyncio.run(main())
