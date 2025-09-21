#!/usr/bin/env python
"""Test the TikTok processing API endpoint"""

import httpx
import sys
import json
import asyncio

async def process_video(tiktok_url: str):
    """Process a TikTok video using the API endpoint"""

    # Send request to API
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/v1/process/tiktok",
            json={"url": tiktok_url}
        )

        if response.status_code == 200:
            result = response.json()
            print(f"✅ Video queued for processing!")
            print(f"Task ID: {result['task_id']}")
            print(f"Status: {result['status']}")
            print(f"Message: {result['message']}")

            # Check status endpoint
            print(f"\nTo check status:")
            print(f"curl http://localhost:8000/api/v1/process/status/{result['task_id']}")

            return result['task_id']
        else:
            print(f"❌ Error: {response.status_code}")
            print(response.text)
            return None

async def check_status(task_id: str):
    """Check the status of a processing task"""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"http://localhost:8000/api/v1/process/status/{task_id}"
        )

        if response.status_code == 200:
            result = response.json()
            print(f"\n📊 Status Update:")
            print(f"Task ID: {result['task_id']}")
            print(f"Status: {result['status']}")
            print(f"Progress: {result['progress']}%")
            print(f"Message: {result['message']}")

            if result.get('result'):
                print(f"\n🎵 Results:")
                print(f"Audio URL: {result['result']['audio_url']}")
                print(f"Waveform URL: {result['result']['waveform_url']}")
        else:
            print(f"Error checking status: {response.status_code}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  Process new video: python test_api.py <tiktok_url>")
        print("  Check status:      python test_api.py --status <task_id>")
        sys.exit(1)

    if sys.argv[1] == "--status" and len(sys.argv) > 2:
        # Check status of existing task
        task_id = sys.argv[2]
        asyncio.run(check_status(task_id))
    else:
        # Process new video
        tiktok_url = sys.argv[1]
        task_id = asyncio.run(process_video(tiktok_url))

        if task_id:
            print("\n⏳ Checking initial status...")
            asyncio.run(check_status(task_id))