#!/usr/bin/env python3
"""Test TikTok download with browser cookies"""

import yt_dlp
import tempfile
from pathlib import Path

test_url = "https://www.tiktok.com/@juice.a.cuice/video/7340397177325374766"

print("Testing TikTok download with browser cookies...")
print(f"URL: {test_url}")
print("=" * 50)

# Try different browsers
browsers = ['chrome', 'firefox', 'safari', 'edge']

for browser in browsers:
    print(f"\nTrying {browser} browser cookies...")

    with tempfile.TemporaryDirectory() as temp_dir:
        ydl_opts = {
            'quiet': False,
            'outtmpl': str(Path(temp_dir) / '%(id)s.%(ext)s'),
            'cookiesfrombrowser': (browser, None, None, None),
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(test_url, download=True)

                print(f"✅ SUCCESS with {browser}!")
                print(f"  Downloaded: {info.get('title', 'N/A')[:50]}...")
                print(f"  Creator: {info.get('uploader', 'N/A')}")

                # Check file
                for file in Path(temp_dir).iterdir():
                    print(f"  File: {file.name} ({file.stat().st_size/(1024*1024):.1f} MB)")
                break

        except Exception as e:
            error_msg = str(e)
            if "browser is not installed" in error_msg:
                print(f"  ❌ {browser} not found")
            elif "Could not extract cookies" in error_msg:
                print(f"  ❌ No cookies found in {browser}")
            elif "login" in error_msg.lower():
                print(f"  ❌ {browser} cookies exist but not logged into TikTok")
            else:
                print(f"  ❌ Failed: {error_msg[:100]}...")
            continue
else:
    print("\n⚠️  All browsers failed.")
    print("\nTo fix this:")
    print("1. Open TikTok.com in Chrome/Firefox/Safari")
    print("2. Log in to your TikTok account")
    print("3. Browse a few videos to establish session")
    print("4. Keep the browser open and try again")