#!/usr/bin/env python3
"""Test to ensure we're downloading the correct video"""

import yt_dlp
import sys
import tempfile
from pathlib import Path

# Test URL
test_url = sys.argv[1] if len(sys.argv) > 1 else "https://www.tiktok.com/@sample_vault/video/7525528854044183830"
expected_id = test_url.split('/')[-1]

print(f"Testing URL: {test_url}")
print(f"Expected video ID: {expected_id}")
print("=" * 50)

proxy_url = "http://spwpwn0jy9:Hb4Lp2z~RfwxX7myk5@gate.decodo.com:10001"

with tempfile.TemporaryDirectory() as temp_dir:
    ydl_opts = {
        'quiet': False,
        'no_warnings': False,
        'proxy': proxy_url,
        'outtmpl': str(Path(temp_dir) / '%(id)s.%(ext)s'),
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        },
        # Force no cache
        'nocache': True,
        'rm_cachedir': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            print("\nExtracting info...")
            info = ydl.extract_info(test_url, download=True)

            downloaded_id = str(info.get('id'))
            print(f"\n✅ Download completed!")
            print(f"Downloaded video ID: {downloaded_id}")
            print(f"Title: {info.get('title')}")
            print(f"Uploader: {info.get('uploader')}")

            # Verify correct video
            if downloaded_id != expected_id:
                print(f"\n⚠️ WARNING: Downloaded wrong video!")
                print(f"  Expected: {expected_id}")
                print(f"  Got: {downloaded_id}")
            else:
                print(f"\n✅ Correct video downloaded!")

            # List downloaded files
            print("\nDownloaded files:")
            for file in Path(temp_dir).iterdir():
                print(f"  {file.name} - {file.stat().st_size / (1024*1024):.2f} MB")

        except Exception as e:
            print(f"\n❌ Download failed: {e}")
            print("\nThis could mean:")
            print("1. The video is region-restricted")
            print("2. The proxy is having issues")
            print("3. The video was deleted/made private")