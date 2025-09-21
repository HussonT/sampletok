#!/usr/bin/env python3
"""Debug TikTok download to see what video is actually being downloaded"""

import yt_dlp
import sys
import tempfile
from pathlib import Path

test_url = sys.argv[1] if len(sys.argv) > 1 else "https://www.tiktok.com/@zachking/video/6768504823336815877"

print(f"Testing URL: {test_url}")
print("=" * 50)

# Set up yt-dlp with proxy
proxy_url = "http://spwpwn0jy9:Hb4Lp2z~RfwxX7myk5@gate.decodo.com:10001"

with tempfile.TemporaryDirectory() as temp_dir:
    ydl_opts = {
        'quiet': False,  # Show all output
        'no_warnings': False,
        'verbose': True,  # Extra verbose
        'proxy': proxy_url,
        'outtmpl': str(Path(temp_dir) / '%(id)s.%(ext)s'),
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        print("\n1. Extracting info (no download)...")
        info = ydl.extract_info(test_url, download=False)

        print("\nVideo Info:")
        print(f"  ID: {info.get('id')}")
        print(f"  Title: {info.get('title')}")
        print(f"  Uploader: {info.get('uploader')}")
        print(f"  Duration: {info.get('duration')}s")
        print(f"  Webpage URL: {info.get('webpage_url')}")
        print(f"  Direct URL: {info.get('url', 'N/A')[:100]}...")
        print(f"  Extension: {info.get('ext')}")

        print("\n2. Downloading video...")
        ydl.download([test_url])

        # Find the downloaded file
        video_id = info.get('id')
        ext = info.get('ext', 'mp4')
        expected_path = Path(temp_dir) / f"{video_id}.{ext}"

        print(f"\n3. Looking for file: {expected_path}")

        if expected_path.exists():
            print(f"✅ File found: {expected_path}")
            print(f"   Size: {expected_path.stat().st_size / (1024*1024):.2f} MB")
        else:
            print("❌ File not found at expected path!")
            print("\nFiles in temp directory:")
            for file in Path(temp_dir).iterdir():
                print(f"  - {file.name} ({file.stat().st_size / (1024*1024):.2f} MB)")

        print("\n4. Checking if correct video:")
        print(f"   Expected ID from URL: {test_url.split('/')[-1]}")
        print(f"   Downloaded ID: {video_id}")
        print(f"   Match: {'✅' if test_url.split('/')[-1] == str(video_id) else '❌'}")