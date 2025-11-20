"""
Test script for Instagram Graph API integration.

This script tests all the required API calls needed for the Instagram use cases:
- instagram_manage_contents
- instagram_business_content_publish
- instagram_business_manage_comments
- pages_read_engagement

Run this script to verify your Instagram Graph API setup is working correctly.

Usage:
    python test_instagram_graph_api.py
"""

import asyncio
import sys
from pathlib import Path

# Add backend directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.instagram.graph_api_service import (
    InstagramGraphAPIService,
    InstagramGraphAPIException,
    InstagramGraphAPIAuthError,
    InstagramGraphAPIRateLimitError
)
from app.core.config import settings


async def test_configuration():
    """Test 1: Verify configuration is set up correctly"""
    print("\n" + "="*80)
    print("TEST 1: Configuration Check")
    print("="*80)

    service = InstagramGraphAPIService()

    print(f"✓ App ID: {'Set' if service.app_id and service.app_id != 'your-facebook-app-id-here' else 'NOT SET ❌'}")
    print(f"✓ App Secret: {'Set' if service.app_secret and service.app_secret != 'your-facebook-app-secret-here' else 'NOT SET ❌'}")
    print(f"✓ Access Token: {'Set' if service.access_token and service.access_token != 'your-long-lived-instagram-access-token-here' else 'NOT SET ❌'}")
    print(f"✓ Business Account ID: {'Set' if service.business_account_id and service.business_account_id != 'your-instagram-business-account-id-here' else 'NOT SET ❌'}")
    print(f"✓ Webhook Verify Token: {'Set' if settings.META_WEBHOOK_VERIFY_TOKEN and settings.META_WEBHOOK_VERIFY_TOKEN != 'your-random-webhook-verify-token-here' else 'NOT SET ❌'}")

    if not service.is_configured():
        print("\n❌ FAILED: Instagram Graph API is not properly configured")
        print("\nPlease update your .env file with the following:")
        print("1. INSTAGRAM_APP_ID - Your Facebook App ID")
        print("2. INSTAGRAM_APP_SECRET - Your Facebook App Secret")
        print("3. INSTAGRAM_ACCESS_TOKEN - Long-lived access token")
        print("4. INSTAGRAM_BUSINESS_ACCOUNT_ID - Your Instagram Business Account ID")
        print("5. INSTAGRAM_WEBHOOK_VERIFY_TOKEN - Random verification token")
        print("\nSee backend/docs/INSTAGRAM_GRAPH_API_SETUP.md for setup instructions")
        return False

    print("\n✅ PASSED: All configuration values are set")
    return True


async def test_business_account_info():
    """Test 2: Get business account info (tests instagram_business_basic & pages_read_engagement)"""
    print("\n" + "="*80)
    print("TEST 2: Business Account Info")
    print("="*80)
    print("API Permissions Required: instagram_business_basic, pages_read_engagement")

    service = InstagramGraphAPIService()

    try:
        account_info = await service.get_business_account_info()

        print(f"\n✅ PASSED: Retrieved business account info")
        print(f"   Username: @{account_info.get('username')}")
        print(f"   Name: {account_info.get('name')}")
        print(f"   Followers: {account_info.get('followers_count'):,}")
        print(f"   Following: {account_info.get('follows_count'):,}")
        print(f"   Posts: {account_info.get('media_count'):,}")
        print(f"   Profile Picture: {account_info.get('profile_picture_url')}")

        return True

    except InstagramGraphAPIAuthError as e:
        print(f"\n❌ FAILED: Authentication error - {str(e)}")
        print("\nPossible issues:")
        print("- Access token is invalid or expired")
        print("- App doesn't have required permissions")
        print("- Business Account ID is incorrect")
        return False

    except InstagramGraphAPIException as e:
        print(f"\n❌ FAILED: API error - {str(e)}")
        return False


async def test_get_mentions():
    """Test 3: Get mentions (tests instagram_manage_contents)"""
    print("\n" + "="*80)
    print("TEST 3: Get Mentions")
    print("="*80)
    print("API Permission Required: instagram_manage_contents")

    service = InstagramGraphAPIService()

    try:
        mentions = await service.get_mentions(limit=5)

        print(f"\n✅ PASSED: Retrieved {len(mentions)} mention(s)")

        if mentions:
            print("\nRecent mentions:")
            for i, mention in enumerate(mentions[:3], 1):
                print(f"\n  {i}. Media ID: {mention.get('id')}")
                print(f"     Username: @{mention.get('username')}")
                print(f"     Type: {mention.get('media_type')}")
                print(f"     Timestamp: {mention.get('timestamp')}")
                print(f"     Caption: {mention.get('text', 'N/A')[:100]}...")
        else:
            print("\nNo mentions found (this is OK - try tagging your account in a test post)")

        return True

    except InstagramGraphAPIAuthError as e:
        print(f"\n❌ FAILED: Authentication error - {str(e)}")
        print("\nPossible issues:")
        print("- Missing 'instagram_manage_contents' permission")
        print("- Access token expired")
        return False

    except InstagramGraphAPIException as e:
        print(f"\n❌ FAILED: API error - {str(e)}")
        return False


async def test_post_comment():
    """Test 4: Post a comment (tests instagram_business_manage_comments & instagram_business_content_publish)"""
    print("\n" + "="*80)
    print("TEST 4: Post Comment")
    print("="*80)
    print("API Permissions Required: instagram_business_manage_comments, instagram_business_content_publish")

    service = InstagramGraphAPIService()

    # First, get business account's own media to test commenting on
    print("\nFetching your recent posts to test commenting...")

    try:
        # Get recent media from your business account
        import httpx
        url = f"{service.base_url}/{service.business_account_id}/media"
        params = {
            'access_token': service.access_token,
            'fields': 'id,caption,timestamp,media_type,permalink',
            'limit': 5
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            media_items = data.get('data', [])

        if not media_items:
            print("\n⚠️  SKIPPED: No media found on your account to test commenting")
            print("   Please post something on your Instagram Business account first")
            return True  # Not a failure, just can't test

        # Use the most recent media item
        test_media = media_items[0]
        media_id = test_media['id']

        print(f"\nFound test media:")
        print(f"  Media ID: {media_id}")
        print(f"  Type: {test_media.get('media_type')}")
        print(f"  Caption: {test_media.get('caption', 'N/A')[:100]}...")
        print(f"  Link: {test_media.get('permalink')}")

        # Ask for confirmation before posting
        print("\n⚠️  This will post a test comment on your most recent Instagram post.")
        response = input("Continue? (y/n): ")

        if response.lower() != 'y':
            print("\n⚠️  SKIPPED: User cancelled test")
            return True

        # Post test comment
        test_message = "🤖 Test comment from SampleTheInternet API integration"

        print(f"\nPosting comment: '{test_message}'")
        result = await service.post_comment(media_id, test_message)

        comment_id = result.get('id')
        print(f"\n✅ PASSED: Successfully posted comment")
        print(f"   Comment ID: {comment_id}")

        # Optional: Delete the test comment
        print("\n🧹 Cleaning up test comment...")
        delete_url = f"{service.base_url}/{comment_id}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            delete_response = await client.delete(
                delete_url,
                params={'access_token': service.access_token}
            )
            if delete_response.status_code == 200:
                print("   Test comment deleted successfully")
            else:
                print(f"   Warning: Could not delete test comment (you may need to delete it manually)")

        return True

    except InstagramGraphAPIAuthError as e:
        print(f"\n❌ FAILED: Authentication error - {str(e)}")
        print("\nPossible issues:")
        print("- Missing 'instagram_business_manage_comments' permission")
        print("- Comments are disabled on the post")
        return False

    except InstagramGraphAPIException as e:
        print(f"\n❌ FAILED: API error - {str(e)}")
        return False


async def test_webhook_verification():
    """Test 5: Verify webhook configuration"""
    print("\n" + "="*80)
    print("TEST 5: Webhook Verification")
    print("="*80)

    service = InstagramGraphAPIService()

    test_token = settings.META_WEBHOOK_VERIFY_TOKEN
    test_challenge = "test_challenge_12345"

    result = await service.verify_webhook(test_token, test_challenge)

    if result == test_challenge:
        print("\n✅ PASSED: Webhook verification working correctly")
        print(f"   Verify Token: {test_token[:20]}...")
        return True
    else:
        print("\n❌ FAILED: Webhook verification failed")
        print("   Check INSTAGRAM_WEBHOOK_VERIFY_TOKEN in .env")
        return False


async def run_all_tests():
    """Run all tests in sequence"""
    print("\n" + "="*80)
    print("INSTAGRAM GRAPH API INTEGRATION TESTS")
    print("="*80)
    print(f"Environment: {settings.ENVIRONMENT}")
    print(f"API Version: v21.0")

    tests = [
        ("Configuration Check", test_configuration),
        ("Business Account Info", test_business_account_info),
        ("Get Mentions", test_get_mentions),
        ("Post Comment", test_post_comment),
        ("Webhook Verification", test_webhook_verification),
    ]

    results = {}

    for test_name, test_func in tests:
        try:
            passed = await test_func()
            results[test_name] = passed

            # If configuration check fails, stop immediately
            if test_name == "Configuration Check" and not passed:
                break

        except Exception as e:
            print(f"\n❌ FAILED: Unexpected error - {str(e)}")
            results[test_name] = False

    # Print summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)

    passed_count = sum(1 for passed in results.values() if passed)
    total_count = len(results)

    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{status}: {test_name}")

    print(f"\nTotal: {passed_count}/{total_count} tests passed")

    if passed_count == total_count:
        print("\n🎉 All tests passed! Your Instagram Graph API integration is working correctly.")
        print("\nNext steps:")
        print("1. Submit your app for App Review in Facebook Developer Console")
        print("2. Request the following permissions:")
        print("   - instagram_manage_contents")
        print("   - instagram_business_content_publish")
        print("   - instagram_business_manage_comments")
        print("   - pages_read_engagement")
        print("3. Once approved, you can go live with the integration!")
    else:
        print("\n⚠️  Some tests failed. Please review the errors above and fix any issues.")
        print("   See backend/docs/INSTAGRAM_GRAPH_API_SETUP.md for help")

    return passed_count == total_count


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
