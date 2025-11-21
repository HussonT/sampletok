"""
Simplified Meta API tests using direct HTTP calls.
"""

import httpx
import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

ACCESS_TOKEN = os.getenv('INSTAGRAM_ACCESS_TOKEN')
BUSINESS_ACCOUNT_ID = os.getenv('INSTAGRAM_BUSINESS_ACCOUNT_ID')
BASE_URL = "https://graph.facebook.com/v24.0"


async def make_api_call(endpoint, params=None, method="GET"):
    """Make a Graph API call"""
    if params is None:
        params = {}
    params['access_token'] = ACCESS_TOKEN

    url = f"{BASE_URL}/{endpoint}"

    async with httpx.AsyncClient(timeout=30.0) as client:
        if method == "GET":
            response = await client.get(url, params=params)
        elif method == "POST":
            response = await client.post(url, params=params)

        response.raise_for_status()
        return response.json()


async def run_tests():
    print("=" * 80)
    print("🚀 Running Meta API Review Tests")
    print("=" * 80)
    print(f"\nBusiness Account ID: {BUSINESS_ACCOUNT_ID}")
    print(f"Access Token: {'✅ Set' if ACCESS_TOKEN else '❌ Missing'}\n")

    results = {}

    # Test 1: instagram_basic
    print("🧪 Test 1: instagram_basic...")
    try:
        data = await make_api_call(
            f"{BUSINESS_ACCOUNT_ID}",
            params={"fields": "id,username,name"}
        )
        print(f"✅ SUCCESS: Got account @{data.get('username')}")
        results['instagram_basic'] = True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        results['instagram_basic'] = False

    # Test 2: instagram_content_publish (read media)
    print("\n🧪 Test 2: instagram_content_publish...")
    try:
        data = await make_api_call(
            f"{BUSINESS_ACCOUNT_ID}/media",
            params={"fields": "id,media_type,permalink", "limit": 3}
        )
        media_count = len(data.get('data', []))
        print(f"✅ SUCCESS: Got {media_count} media items")
        results['instagram_content_publish'] = True

        # Save first media_id for later tests
        media_id = data['data'][0]['id'] if data.get('data') else None

    except Exception as e:
        print(f"❌ FAILED: {e}")
        results['instagram_content_publish'] = False
        media_id = None

    # Test 3: pages_read_engagement
    print("\n🧪 Test 3: pages_read_engagement...")
    try:
        data = await make_api_call(
            f"{BUSINESS_ACCOUNT_ID}/media",
            params={"fields": "id,like_count,comments_count", "limit": 3}
        )
        print(f"✅ SUCCESS: Got engagement data for {len(data.get('data', []))} posts")
        for media in data.get('data', [])[:2]:
            print(f"   Media {media['id']}: {media.get('like_count', 0)} likes")
        results['pages_read_engagement'] = True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        results['pages_read_engagement'] = False

    # Test 4: instagram_manage_comments (read)
    print("\n🧪 Test 4: instagram_manage_comments (read)...")
    if media_id:
        try:
            data = await make_api_call(
                f"{media_id}/comments",
                params={"fields": "id,text"}
            )
            print(f"✅ SUCCESS: Got comments for media {media_id}")
            print(f"   Found {len(data.get('data', []))} comments")
            results['instagram_manage_comments_read'] = True
        except Exception as e:
            print(f"❌ FAILED: {e}")
            results['instagram_manage_comments_read'] = False
    else:
        print("⚠️  SKIPPED: No media_id available")
        results['instagram_manage_comments_read'] = False

    # Test 5: instagram_manage_comments (write)
    print("\n🧪 Test 5: instagram_manage_comments (write - post comment)...")
    if media_id:
        try:
            test_message = "🧪 Meta API Review Test - Testing instagram_manage_comments permission"
            data = await make_api_call(
                f"{media_id}/comments",
                params={"message": test_message},
                method="POST"
            )
            print(f"✅ SUCCESS: Posted comment")
            print(f"   Comment ID: {data['id']}")
            print(f"   Message: {test_message}")
            results['instagram_manage_comments_write'] = True
        except Exception as e:
            print(f"❌ FAILED: {e}")
            results['instagram_manage_comments_write'] = False
    else:
        print("⚠️  SKIPPED: No media_id available")
        results['instagram_manage_comments_write'] = False

    # Summary
    print("\n" + "=" * 80)
    print("📊 Test Results Summary")
    print("=" * 80)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status} - {test_name}")

    print(f"\n🎯 Results: {passed}/{total} tests passed")

    if passed == total:
        print("\n✅ ALL TESTS PASSED!")
        print("\n📝 Next steps:")
        print("   1. Wait 2-3 minutes for Meta to register the API calls")
        print("   2. Refresh the Meta App Review page")
        print("   3. The '0 API test call(s)' should update to 'Completed'")
        print("   4. Submit your app for review once all tests show 'Completed'")
    else:
        print("\n⚠️  Some tests failed. Common issues:")
        print("   - No media found: Create a test post on @sampletheinternet")
        print("   - Comments disabled: Enable comments on your test post")


if __name__ == "__main__":
    asyncio.run(run_tests())
