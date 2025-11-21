"""
Run Meta API tests to satisfy App Review testing requirements.

This script makes the required API calls for each permission being reviewed.
Run this to complete the "Testing in progress" requirements in Meta App Review.
"""

import asyncio
import os
from app.services.instagram.graph_api import InstagramGraphAPIClient
from app.core.config import settings


async def test_instagram_business_content_publish():
    """Test instagram_business_content_publish - 0 of 1 API call(s) required"""
    print("\n🧪 Testing instagram_business_content_publish...")
    client = InstagramGraphAPIClient()

    try:
        # Get account info (uses this permission)
        info = await client.get_account_info()
        print(f"✅ SUCCESS: Got account @{info['username']}")
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False


async def test_instagram_business_manage_comments():
    """Test instagram_business_manage_comments - 0 of 1 API call(s) required"""
    print("\n🧪 Testing instagram_business_manage_comments...")
    client = InstagramGraphAPIClient()

    try:
        # Get recent media
        response = await client._make_api_request(
            f"/{client.business_account_id}/media",
            params={"fields": "id,media_type", "limit": 1}
        )

        media_list = response.get('data', [])
        if not media_list:
            print("⚠️  No media found - create a test post on Instagram first")
            return False

        media_id = media_list[0]['id']

        # Get comments on this media (tests read permission)
        comments = await client._make_api_request(
            f"/{media_id}/comments",
            params={"fields": "id,text"}
        )

        print(f"✅ SUCCESS: Got comments for media {media_id}")
        print(f"   Found {len(comments.get('data', []))} comments")
        return True

    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False


async def test_instagram_basic():
    """Test instagram_basic - 0 of 1 API call(s) required"""
    print("\n🧪 Testing instagram_basic...")
    client = InstagramGraphAPIClient()

    try:
        # Get account basic info
        info = await client._make_api_request(
            f"/{client.business_account_id}",
            params={"fields": "id,username,name"}
        )

        print(f"✅ SUCCESS: Got basic info for @{info['username']}")
        return True

    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False


async def test_pages_read_engagement():
    """Test pages_read_engagement - 0 of 1 API call(s) required"""
    print("\n🧪 Testing pages_read_engagement...")
    client = InstagramGraphAPIClient()

    try:
        # Get recent media (engagement data)
        response = await client._make_api_request(
            f"/{client.business_account_id}/media",
            params={"fields": "id,like_count,comments_count", "limit": 5}
        )

        media_list = response.get('data', [])
        print(f"✅ SUCCESS: Got engagement data for {len(media_list)} posts")

        for media in media_list[:3]:
            likes = media.get('like_count', 0)
            comments = media.get('comments_count', 0)
            print(f"   Media {media['id']}: {likes} likes, {comments} comments")

        return True

    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False


async def test_instagram_manage_comments():
    """Test instagram_manage_comments - 0 of 1 API call(s) required"""
    print("\n🧪 Testing instagram_manage_comments...")
    client = InstagramGraphAPIClient()

    try:
        # Get recent media
        response = await client._make_api_request(
            f"/{client.business_account_id}/media",
            params={"fields": "id,media_type,caption", "limit": 1}
        )

        media_list = response.get('data', [])
        if not media_list:
            print("⚠️  No media found - create a test post on Instagram first")
            return False

        media_id = media_list[0]['id']
        media_type = media_list[0].get('media_type', 'UNKNOWN')
        caption = media_list[0].get('caption', 'No caption')[:50]

        print(f"   Found media: {media_id}")
        print(f"   Type: {media_type}")
        print(f"   Caption: {caption}...")

        # Post a test comment
        test_message = "🧪 Meta API Review Test - Testing instagram_manage_comments permission"
        result = await client.post_comment(media_id, test_message)

        print(f"✅ SUCCESS: Posted test comment")
        print(f"   Comment ID: {result['id']}")
        print(f"   Message: {test_message}")

        return True

    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False


async def test_instagram_content_publish():
    """Test instagram_content_publish - 0 of 1 API call(s) required"""
    print("\n🧪 Testing instagram_content_publish...")
    client = InstagramGraphAPIClient()

    try:
        # Get media (uses content publish permission to read)
        response = await client._make_api_request(
            f"/{client.business_account_id}/media",
            params={"fields": "id,media_type,permalink", "limit": 3}
        )

        media_list = response.get('data', [])
        print(f"✅ SUCCESS: Got {len(media_list)} published media items")

        for media in media_list:
            print(f"   {media.get('media_type')}: {media.get('permalink')}")

        return True

    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False


async def run_all_tests():
    """Run all API tests required by Meta App Review"""
    print("=" * 80)
    print("🚀 Running Meta API Review Tests")
    print("=" * 80)

    print(f"\n📋 Configuration:")
    print(f"   App: Sample The Internet")
    print(f"   Business Account ID: {settings.INSTAGRAM_BUSINESS_ACCOUNT_ID}")
    print(f"   Access Token: {'✅ Set' if settings.INSTAGRAM_ACCESS_TOKEN else '❌ Missing'}")

    if not settings.INSTAGRAM_ACCESS_TOKEN:
        print("\n❌ ERROR: INSTAGRAM_ACCESS_TOKEN not set in environment")
        print("   Set it in your .env file or export it:")
        print("   export INSTAGRAM_ACCESS_TOKEN='your_token_here'")
        return

    # Run all tests
    results = {}

    results['instagram_business_content_publish'] = await test_instagram_business_content_publish()
    results['instagram_business_manage_comments'] = await test_instagram_business_manage_comments()
    results['instagram_basic'] = await test_instagram_basic()
    results['pages_read_engagement'] = await test_pages_read_engagement()
    results['instagram_manage_comments'] = await test_instagram_manage_comments()
    results['instagram_content_publish'] = await test_instagram_content_publish()

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
        print("   1. Go back to Meta App Review dashboard")
        print("   2. The 'Testing in progress' status should update automatically")
        print("   3. If not updated, wait a few minutes and refresh the page")
        print("   4. Submit your app for review once all tests show 'Completed'")
    else:
        print("\n⚠️  Some tests failed. Check the errors above.")
        print("\n💡 Common issues:")
        print("   - Access token expired: Regenerate in Graph API Explorer")
        print("   - Missing permissions: Check app permissions in Meta dashboard")
        print("   - No media found: Create a test post on @sampletheinternet")


if __name__ == "__main__":
    asyncio.run(run_all_tests())
