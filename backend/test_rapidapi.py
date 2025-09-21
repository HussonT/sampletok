#!/usr/bin/env python3
"""
Test script for RapidAPI TikTok downloader integration
"""
import asyncio
import tempfile
import json
from pathlib import Path
import sys

# Add the app directory to the path
sys.path.insert(0, '/Users/tomhusson/sideprojects/sampletok/sampletok/backend')

from app.services.tiktok.downloader import TikTokDownloader


async def test_video_info():
    """Test fetching video info without downloading"""
    print("\n=== Testing Video Info Fetch ===")

    # Test URL - you can replace with any valid TikTok URL
    test_url = "https://www.tiktok.com/@taylorswift/video/7288965373704064286"

    downloader = TikTokDownloader()

    try:
        info = await downloader.get_video_info(test_url)
        print(f"✓ Successfully fetched video info")
        print(f"  Title: {info.get('title', 'N/A')}")
        print(f"  Creator: {info.get('creator_username', 'N/A')} ({info.get('creator_name', 'N/A')})")
        print(f"  Views: {info.get('view_count', 0):,}")
        print(f"  Likes: {info.get('like_count', 0):,}")
        print(f"  Comments: {info.get('comment_count', 0):,}")
        return True
    except Exception as e:
        print(f"✗ Failed to fetch video info: {str(e)}")
        return False


async def test_video_download():
    """Test downloading a video with full metadata"""
    print("\n=== Testing Video Download ===")

    # Test URL - you can replace with any valid TikTok URL
    test_url = "https://www.tiktok.com/@tiktok/video/7231338487075638570"

    downloader = TikTokDownloader()

    with tempfile.TemporaryDirectory(prefix='tiktok_test_') as temp_dir:
        try:
            metadata = await downloader.download_video(test_url, temp_dir)
            print(f"✓ Successfully downloaded video")

            # Check that the video file exists
            video_path = Path(metadata['video_path'])
            if video_path.exists():
                file_size_mb = video_path.stat().st_size / (1024 * 1024)
                print(f"  Video saved to: {video_path}")
                print(f"  File size: {file_size_mb:.2f} MB")
            else:
                print(f"✗ Video file not found at {video_path}")
                return False

            # Print metadata
            print("\n  Metadata:")
            print(f"    Aweme ID: {metadata.get('aweme_id', 'N/A')}")
            print(f"    Title: {metadata.get('title', 'N/A')[:50]}...")
            print(f"    Region: {metadata.get('region', 'N/A')}")
            print(f"    Creator: @{metadata.get('creator_username', 'N/A')} ({metadata.get('creator_name', 'N/A')})")
            print(f"    Views: {metadata.get('view_count', 0):,}")
            print(f"    Likes: {metadata.get('like_count', 0):,}")
            print(f"    Comments: {metadata.get('comment_count', 0):,}")
            print(f"    Upload timestamp: {metadata.get('upload_timestamp', 'N/A')}")

            # Check URLs
            print("\n  URLs available:")
            if metadata.get('thumbnail_url'):
                print(f"    ✓ Thumbnail URL")
            if metadata.get('origin_cover_url'):
                print(f"    ✓ Original cover URL")
            if metadata.get('music_url'):
                print(f"    ✓ Music URL")
            if metadata.get('video_url'):
                print(f"    ✓ No-watermark video URL")
            if metadata.get('video_url_watermark'):
                print(f"    ✓ Watermarked video URL")
            if metadata.get('creator_avatar_url'):
                print(f"    ✓ Creator avatar URL")

            return True

        except Exception as e:
            print(f"✗ Failed to download video: {str(e)}")
            import traceback
            traceback.print_exc()
            return False


async def test_invalid_url():
    """Test handling of invalid URLs"""
    print("\n=== Testing Invalid URL Handling ===")

    invalid_url = "https://www.example.com/not-a-tiktok-video"

    downloader = TikTokDownloader()

    try:
        await downloader.get_video_info(invalid_url)
        print("✗ Should have raised an error for invalid URL")
        return False
    except Exception as e:
        print(f"✓ Correctly handled invalid URL: {str(e)}")
        return True


async def main():
    """Run all tests"""
    print("Starting RapidAPI TikTok Downloader Tests")
    print("=" * 50)

    results = []

    # Run tests
    results.append(await test_video_info())
    results.append(await test_video_download())
    results.append(await test_invalid_url())

    # Summary
    print("\n" + "=" * 50)
    print("Test Summary:")
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")

    if passed == total:
        print("✓ All tests passed!")
        return 0
    else:
        print(f"✗ {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)