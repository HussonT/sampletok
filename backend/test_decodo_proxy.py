#!/usr/bin/env python3
"""Test Decodo proxy with TikTok"""

import yt_dlp
import requests

# First test basic proxy connectivity
print("Testing Decodo proxy connectivity...")
proxy_url = "http://spwpwn0jy9:Hb4Lp2z~RfwxX7myk5@gate.decodo.com:10001"

try:
    # Test basic connectivity
    result = requests.get('https://ip.decodo.com/json', proxies={
        'http': proxy_url,
        'https': proxy_url
    }, timeout=10)
    print(f"✅ Proxy is working! IP: {result.json().get('ip', 'unknown')}")
except Exception as e:
    print(f"❌ Proxy test failed: {e}")
    exit(1)

# Now test with TikTok
print("\nTesting with TikTok...")
test_url = "https://www.tiktok.com/@zachking/video/6768504823336815877"

ydl_opts = {
    'quiet': False,
    'no_warnings': False,
    'skip_download': True,  # Just get info
    'proxy': proxy_url,
    'http_headers': {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
}

try:
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        print("Extracting video info through Decodo proxy...")
        info = ydl.extract_info(test_url, download=False)

        print("\n✅ SUCCESS! Decodo proxy works with TikTok")
        print(f"\nVideo Details:")
        print(f"  Title: {info.get('title', 'N/A')}")
        print(f"  Creator: {info.get('uploader', 'N/A')}")
        print(f"  Duration: {info.get('duration', 0)}s")
        print(f"  Views: {info.get('view_count', 0):,}")

except Exception as e:
    print(f"\n❌ TikTok test failed: {e}")
    print("\nThe proxy works but TikTok might still be blocking it.")
    print("You may need to use cookies or a different approach.")