#!/usr/bin/env python3
"""Test the fixed TikTok downloader"""

import asyncio
import tempfile
from pathlib import Path

# Add backend to path
import sys
sys.path.insert(0, '/Users/tomhusson/sideprojects/sampletok/sampletok/backend')

from app.services.tiktok.downloader import TikTokDownloader

async def test_download():
    """Test downloading a TikTok video"""

    # Test URL (use a popular, stable video)
    test_url = "https://www.tiktok.com/@zachking/video/6768504823336815877"

    downloader = TikTokDownloader()

    print(f"Testing download of: {test_url}")
    print("Using Decodo proxy...")

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = await downloader.download_video(test_url, temp_dir)

            print("\n✅ Download successful!")
            print(f"Video ID: {result['tiktok_id']}")
            print(f"Title: {result['title'][:50]}...")
            print(f"Creator: {result['creator_username']}")
            print(f"Duration: {result['duration']}s")
            print(f"Video saved to: {result['video_path']}")

            # Check if file exists
            if Path(result['video_path']).exists():
                file_size = Path(result['video_path']).stat().st_size / (1024*1024)
                print(f"File size: {file_size:.2f} MB")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_download())