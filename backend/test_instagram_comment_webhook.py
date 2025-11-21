#!/usr/bin/env python3
"""
Test script for Instagram comment webhook event.

This tests the payload structure from Instagram when users mention @sampletheinternet in comments.
"""
import asyncio
import json
import httpx


async def test_comment_webhook():
    """Test POST request for comment webhook event"""
    print("\n" + "="*60)
    print("TEST: Instagram Comment Webhook Event")
    print("="*60)

    # The exact payload structure you provided
    event_data = {
        "object": "instagram",
        "entry": [
            {
                "id": "instagram_business_account_id",
                "time": 1234567890,
                "changes": [
                    {
                        "field": "comments",
                        "value": {
                            "from": {
                                "id": "232323232",
                                "username": "test"
                            },
                            "media": {
                                "id": "123123123",
                                "media_product_type": "FEED"
                            },
                            "id": "17865799348089039",
                            "parent_id": "1231231234",
                            "text": "This is an example."
                        }
                    }
                ]
            }
        ]
    }

    print(f"\nTest Payload:")
    print(json.dumps(event_data, indent=2))

    # Send POST request to the webhook endpoint
    url = "http://localhost:8000/api/v1/webhooks/instagram"

    print(f"\nSending POST to {url}...")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                json=event_data,
                timeout=30.0
            )

            print(f"\nResponse Status: {response.status_code}")
            print(f"Response Body: {response.json()}")

            if response.status_code == 200:
                print("\n✓ Webhook accepted successfully!")
            else:
                print(f"\n✗ Unexpected status code: {response.status_code}")

    except httpx.ConnectError:
        print("\n✗ Connection failed! Is the backend running on localhost:8000?")
        print("   Start it with: cd backend && uvicorn app.main:app --reload")
    except Exception as e:
        print(f"\n✗ Error: {e}")


async def test_comment_with_mention():
    """Test comment that mentions @sampletheinternet"""
    print("\n" + "="*60)
    print("TEST: Comment with @sampletheinternet mention")
    print("="*60)

    # Comment that mentions our account
    event_data = {
        "object": "instagram",
        "entry": [
            {
                "id": "instagram_business_account_id",
                "time": 1234567890,
                "changes": [
                    {
                        "field": "comments",
                        "value": {
                            "from": {
                                "id": "232323232",
                                "username": "testuser"
                            },
                            "media": {
                                "id": "123123123_MENTION_TEST",
                                "media_product_type": "FEED"
                            },
                            "id": "17865799348089039",
                            "parent_id": "1231231234",
                            "text": "Check this out @sampletheinternet!"
                        }
                    }
                ]
            }
        ]
    }

    print(f"\nTest Payload:")
    print(json.dumps(event_data, indent=2))

    url = "http://localhost:8000/api/v1/webhooks/instagram"

    print(f"\nSending POST to {url}...")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                json=event_data,
                timeout=30.0
            )

            print(f"\nResponse Status: {response.status_code}")
            print(f"Response Body: {response.json()}")

            if response.status_code == 200:
                print("\n✓ Comment webhook with mention processed!")
                print("   This should have created an InstagramEngagement record")
                print("   and triggered the mention processor")
            else:
                print(f"\n✗ Unexpected status code: {response.status_code}")

    except httpx.ConnectError:
        print("\n✗ Connection failed! Is the backend running on localhost:8000?")
        print("   Start it with: cd backend && uvicorn app.main:app --reload")
    except Exception as e:
        print(f"\n✗ Error: {e}")


async def test_comment_without_mention():
    """Test comment that doesn't mention our account (should be ignored)"""
    print("\n" + "="*60)
    print("TEST: Comment without @sampletheinternet (should be ignored)")
    print("="*60)

    event_data = {
        "object": "instagram",
        "entry": [
            {
                "id": "instagram_business_account_id",
                "time": 1234567890,
                "changes": [
                    {
                        "field": "comments",
                        "value": {
                            "from": {
                                "id": "232323232",
                                "username": "testuser"
                            },
                            "media": {
                                "id": "999999999_NO_MENTION",
                                "media_product_type": "FEED"
                            },
                            "id": "17865799348089040",
                            "parent_id": "1231231234",
                            "text": "Just a regular comment without any mention"
                        }
                    }
                ]
            }
        ]
    }

    print(f"\nTest Payload:")
    print(json.dumps(event_data, indent=2))

    url = "http://localhost:8000/api/v1/webhooks/instagram"

    print(f"\nSending POST to {url}...")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                json=event_data,
                timeout=30.0
            )

            print(f"\nResponse Status: {response.status_code}")
            print(f"Response Body: {response.json()}")

            if response.status_code == 200:
                print("\n✓ Comment webhook accepted (but should be ignored)")
                print("   No InstagramEngagement record should be created")
            else:
                print(f"\n✗ Unexpected status code: {response.status_code}")

    except httpx.ConnectError:
        print("\n✗ Connection failed! Is the backend running on localhost:8000?")
        print("   Start it with: cd backend && uvicorn app.main:app --reload")
    except Exception as e:
        print(f"\n✗ Error: {e}")


async def main():
    """Run all comment webhook tests"""
    print("\n" + "="*60)
    print("Instagram Comment Webhook Test Suite")
    print("="*60)

    # Test 1: Basic comment webhook structure
    await test_comment_webhook()

    await asyncio.sleep(1)  # Brief pause between tests

    # Test 2: Comment with @sampletheinternet mention
    await test_comment_with_mention()

    await asyncio.sleep(1)

    # Test 3: Comment without mention (should be ignored)
    await test_comment_without_mention()

    print("\n" + "="*60)
    print("All tests completed!")
    print("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
