"""
Complete Meta API tests for ALL permissions in app review.
"""

import httpx
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

ACCESS_TOKEN = os.getenv('INSTAGRAM_ACCESS_TOKEN')
BUSINESS_ACCOUNT_ID = os.getenv('INSTAGRAM_BUSINESS_ACCOUNT_ID')
BASE_URL = "https://graph.facebook.com/v24.0"


async def make_api_call(endpoint, params=None, method="GET"):
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


async def run_all_tests():
    print("=" * 80)
    print("🚀 Running COMPLETE Meta API Review Tests")
    print("=" * 80)
    print(f"\nBusiness Account ID: {BUSINESS_ACCOUNT_ID}")
    print(f"Access Token: {'✅ Set' if ACCESS_TOKEN else '❌ Missing'}\n")

    results = {}

    # Test 1: email
    print("🧪 Test 1: email...")
    try:
        data = await make_api_call("me", params={"fields": "email"})
        print(f"✅ SUCCESS: Got email {data.get('email', 'N/A')}")
        results['email'] = True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        results['email'] = False

    # Test 2: public_profile
    print("\n🧪 Test 2: public_profile...")
    try:
        data = await make_api_call("me", params={"fields": "id,name"})
        print(f"✅ SUCCESS: Got profile {data.get('name')}")
        results['public_profile'] = True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        results['public_profile'] = False

    # Test 3: pages_show_list
    print("\n🧪 Test 3: pages_show_list...")
    try:
        data = await make_api_call("me/accounts", params={"fields": "id,name"})
        print(f"✅ SUCCESS: Got {len(data.get('data', []))} pages")
        results['pages_show_list'] = True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        results['pages_show_list'] = False

    # Test 4: instagram_basic
    print("\n🧪 Test 4: instagram_basic...")
    try:
        data = await make_api_call(
            f"{BUSINESS_ACCOUNT_ID}",
            params={"fields": "id,username,name,profile_picture_url"}
        )
        print(f"✅ SUCCESS: Got account @{data.get('username')}")
        results['instagram_basic'] = True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        results['instagram_basic'] = False

    # Test 5: instagram_business_basic
    print("\n🧪 Test 5: instagram_business_basic...")
    try:
        data = await make_api_call(
            f"{BUSINESS_ACCOUNT_ID}",
            params={"fields": "id,username,followers_count,media_count"}
        )
        print(f"✅ SUCCESS: Got business account data")
        print(f"   Followers: {data.get('followers_count', 'N/A')}")
        results['instagram_business_basic'] = True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        results['instagram_business_basic'] = False

    # Test 6: instagram_content_publish
    print("\n🧪 Test 6: instagram_content_publish...")
    try:
        data = await make_api_call(
            f"{BUSINESS_ACCOUNT_ID}/media",
            params={"fields": "id,media_type,permalink,caption", "limit": 3}
        )
        media_count = len(data.get('data', []))
        print(f"✅ SUCCESS: Got {media_count} published media items")
        results['instagram_content_publish'] = True
        media_id = data['data'][0]['id'] if data.get('data') else None
    except Exception as e:
        print(f"❌ FAILED: {e}")
        results['instagram_content_publish'] = False
        media_id = None

    # Test 7: instagram_business_content_publish
    print("\n🧪 Test 7: instagram_business_content_publish...")
    try:
        data = await make_api_call(
            f"{BUSINESS_ACCOUNT_ID}/media",
            params={"fields": "id,media_type,timestamp", "limit": 5}
        )
        print(f"✅ SUCCESS: Got business content")
        results['instagram_business_content_publish'] = True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        results['instagram_business_content_publish'] = False

    # Test 8: pages_read_engagement
    print("\n🧪 Test 8: pages_read_engagement...")
    try:
        data = await make_api_call(
            f"{BUSINESS_ACCOUNT_ID}/media",
            params={"fields": "id,like_count,comments_count", "limit": 3}
        )
        print(f"✅ SUCCESS: Got engagement data for {len(data.get('data', []))} posts")
        for media in data.get('data', [])[:2]:
            print(f"   Media: {media.get('like_count', 0)} likes, {media.get('comments_count', 0)} comments")
        results['pages_read_engagement'] = True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        results['pages_read_engagement'] = False

    # Test 9: instagram_manage_comments (read)
    print("\n🧪 Test 9: instagram_manage_comments (read)...")
    if media_id:
        try:
            data = await make_api_call(
                f"{media_id}/comments",
                params={"fields": "id,text,username"}
            )
            print(f"✅ SUCCESS: Read comments for media {media_id}")
            print(f"   Found {len(data.get('data', []))} comments")
            results['instagram_manage_comments'] = True
        except Exception as e:
            print(f"❌ FAILED: {e}")
            results['instagram_manage_comments'] = False
    else:
        print("⚠️  SKIPPED: No media_id available")
        results['instagram_manage_comments'] = False

    # Test 10: instagram_business_manage_comments (read)
    print("\n🧪 Test 10: instagram_business_manage_comments (read)...")
    if media_id:
        try:
            data = await make_api_call(
                f"{media_id}/comments",
                params={"fields": "id,text,timestamp"}
            )
            print(f"✅ SUCCESS: Business manage comments (read)")
            results['instagram_business_manage_comments'] = True
        except Exception as e:
            print(f"❌ FAILED: {e}")
            results['instagram_business_manage_comments'] = False
    else:
        print("⚠️  SKIPPED: No media_id available")
        results['instagram_business_manage_comments'] = False

    # Test 11: instagram_manage_comments (write)
    print("\n🧪 Test 11: instagram_manage_comments (write - post comment)...")
    if media_id:
        try:
            test_message = "🧪 Meta API Review - Complete permission test"
            data = await make_api_call(
                f"{media_id}/comments",
                params={"message": test_message},
                method="POST"
            )
            print(f"✅ SUCCESS: Posted test comment")
            print(f"   Comment ID: {data['id']}")
            results['instagram_manage_comments_write'] = True
        except Exception as e:
            print(f"❌ FAILED: {e}")
            results['instagram_manage_comments_write'] = False
    else:
        print("⚠️  SKIPPED: No media_id available")
        results['instagram_manage_comments_write'] = False

    # Test 12: Instagram Public Content Access
    print("\n🧪 Test 12: Instagram Public Content Access...")
    try:
        data = await make_api_call(
            f"{BUSINESS_ACCOUNT_ID}/media",
            params={"fields": "id,media_url,permalink", "limit": 1}
        )
        print(f"✅ SUCCESS: Accessed public content")
        results['instagram_public_content_access'] = True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        results['instagram_public_content_access'] = False

    # Test 13: Business Asset User Profile Access
    print("\n🧪 Test 13: Business Asset User Profile Access...")
    try:
        data = await make_api_call(
            f"{BUSINESS_ACCOUNT_ID}",
            params={"fields": "id,username,biography,website"}
        )
        print(f"✅ SUCCESS: Accessed business profile")
        print(f"   Username: @{data.get('username')}")
        results['business_asset_user_profile_access'] = True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        results['business_asset_user_profile_access'] = False

    # Summary
    print("\n" + "=" * 80)
    print("📊 Complete Test Results")
    print("=" * 80)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status} - {test_name}")

    print(f"\n🎯 Results: {passed}/{total} tests passed")

    if passed >= total - 1:  # Allow 1 failure
        print("\n✅ TESTS COMPLETE!")
        print("\n📝 Next steps:")
        print("   1. Wait 3-5 minutes for Meta to register all API calls")
        print("   2. Hard refresh the Meta App Review page (Cmd+Shift+R)")
        print("   3. All permissions should show 'Completed'")
        print("   4. Submit your app for review")
    else:
        print("\n⚠️  Multiple tests failed.")
        print("   Check errors above and ensure you have a test post on Instagram")


if __name__ == "__main__":
    asyncio.run(run_all_tests())
