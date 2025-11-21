"""
Comprehensive test of ALL Instagram Graph API endpoints for Meta App Review.

This script makes direct API calls to satisfy Meta's testing requirements.
It mimics what you would do manually in Graph API Explorer.
"""

import asyncio
import sys
from pathlib import Path
import httpx

sys.path.insert(0, str(Path(__file__).parent))

from app.core.config import settings


async def test_all_endpoints():
    """Run all API endpoint tests"""

    token = settings.INSTAGRAM_ACCESS_TOKEN
    business_id = settings.INSTAGRAM_BUSINESS_ACCOUNT_ID
    base_url = "https://graph.facebook.com/v21.0"

    print("=" * 80)
    print("COMPREHENSIVE INSTAGRAM GRAPH API ENDPOINT TESTS")
    print("=" * 80)
    print(f"\nBusiness Account: {business_id}")
    print(f"Token: {token[:30]}...")

    results = {}

    async with httpx.AsyncClient(timeout=30.0) as client:

        # TEST 1: pages_read_engagement
        print("\n" + "=" * 80)
        print("TEST 1: pages_read_engagement")
        print("=" * 80)
        print("API Call: GET /{ig-user-id}?fields=username,followers_count,...")

        try:
            url = f"{base_url}/{business_id}"
            params = {
                'access_token': token,
                'fields': 'username,followers_count,follows_count,media_count,profile_picture_url'
            }
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            print(f"\n✅ SUCCESS")
            print(f"   Username: @{data.get('username')}")
            print(f"   Followers: {data.get('followers_count')}")
            print(f"   Media: {data.get('media_count')}")
            results['pages_read_engagement'] = True

        except Exception as e:
            print(f"\n❌ FAILED: {str(e)}")
            results['pages_read_engagement'] = False

        # TEST 2: instagram_business_basic
        print("\n" + "=" * 80)
        print("TEST 2: instagram_business_basic")
        print("=" * 80)
        print("API Call: GET /{ig-user-id}?fields=id,username,name")

        try:
            url = f"{base_url}/{business_id}"
            params = {
                'access_token': token,
                'fields': 'id,username,name'
            }
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            print(f"\n✅ SUCCESS")
            print(f"   Account ID: {data.get('id')}")
            print(f"   Username: @{data.get('username')}")
            results['instagram_business_basic'] = True

        except Exception as e:
            print(f"\n❌ FAILED: {str(e)}")
            results['instagram_business_basic'] = False

        # Get media for next tests
        print("\n" + "=" * 80)
        print("Getting media list...")
        print("=" * 80)

        media_id = None
        try:
            url = f"{base_url}/{business_id}/media"
            params = {
                'access_token': token,
                'fields': 'id,media_type,permalink',
                'limit': 1
            }
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            media_items = data.get('data', [])

            if media_items:
                media_id = media_items[0]['id']
                print(f"\n✅ Found media: {media_items[0].get('permalink')}")
                print(f"   Media ID: {media_id}")
            else:
                print(f"\n⚠️  No media found on account")

        except Exception as e:
            print(f"\n❌ Failed to get media: {str(e)}")

        # TEST 3: instagram_business_manage_comments (GET comments)
        print("\n" + "=" * 80)
        print("TEST 3: instagram_business_manage_comments (GET)")
        print("=" * 80)
        print("API Call: GET /{media-id}/comments")

        if media_id:
            try:
                url = f"{base_url}/{media_id}/comments"
                params = {
                    'access_token': token,
                    'fields': 'id,text,username,timestamp'
                }
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                comments = data.get('data', [])

                print(f"\n✅ SUCCESS")
                print(f"   Retrieved {len(comments)} comment(s)")
                results['instagram_business_manage_comments_get'] = True

            except Exception as e:
                print(f"\n❌ FAILED: {str(e)}")
                results['instagram_business_manage_comments_get'] = False
        else:
            print(f"\n⚠️  SKIPPED: No media to test on")
            results['instagram_business_manage_comments_get'] = None

        # TEST 4: instagram_business_content_publish (POST comment)
        print("\n" + "=" * 80)
        print("TEST 4: instagram_business_content_publish (POST)")
        print("=" * 80)
        print("API Call: POST /{media-id}/comments")

        comment_id = None
        if media_id:
            try:
                url = f"{base_url}/{media_id}/comments"
                data_payload = {
                    'access_token': token,
                    'message': '🤖 API Test - Meta App Review Validation'
                }
                response = await client.post(url, data=data_payload)
                response.raise_for_status()
                data = response.json()
                comment_id = data.get('id')

                print(f"\n✅ SUCCESS")
                print(f"   Posted comment ID: {comment_id}")
                results['instagram_business_content_publish'] = True

            except Exception as e:
                print(f"\n❌ FAILED: {str(e)}")
                results['instagram_business_content_publish'] = False
        else:
            print(f"\n⚠️  SKIPPED: No media to test on")
            results['instagram_business_content_publish'] = None

        # TEST 5: instagram_content_publish (alias test)
        print("\n" + "=" * 80)
        print("TEST 5: instagram_content_publish")
        print("=" * 80)
        print("API Call: Same as instagram_business_content_publish")

        if results.get('instagram_business_content_publish'):
            print(f"\n✅ SUCCESS (tested via instagram_business_content_publish)")
            results['instagram_content_publish'] = True
        else:
            results['instagram_content_publish'] = results.get('instagram_business_content_publish')

        # TEST 6: instagram_manage_comments (POST reply)
        print("\n" + "=" * 80)
        print("TEST 6: instagram_manage_comments (POST reply)")
        print("=" * 80)
        print("API Call: POST /{comment-id}/replies")

        reply_id = None
        if comment_id:
            try:
                url = f"{base_url}/{comment_id}/replies"
                data_payload = {
                    'access_token': token,
                    'message': '🤖 Reply test - Meta App Review'
                }
                response = await client.post(url, data=data_payload)
                response.raise_for_status()
                data = response.json()
                reply_id = data.get('id')

                print(f"\n✅ SUCCESS")
                print(f"   Posted reply ID: {reply_id}")
                results['instagram_manage_comments'] = True

            except Exception as e:
                print(f"\n❌ FAILED: {str(e)}")
                results['instagram_manage_comments'] = False
        else:
            print(f"\n⚠️  SKIPPED: No comment to reply to")
            results['instagram_manage_comments'] = None

        # TEST 7: instagram_manage_contents (mentioned_media)
        print("\n" + "=" * 80)
        print("TEST 7: instagram_manage_contents")
        print("=" * 80)
        print("API Call: GET /{ig-user-id}/mentioned_media")

        try:
            url = f"{base_url}/{business_id}/mentioned_media"
            params = {
                'access_token': token,
                'fields': 'id,media_type,media_url'
            }
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            mentioned = data.get('data', [])

            print(f"\n✅ SUCCESS")
            print(f"   Retrieved {len(mentioned)} mentioned media")
            results['instagram_manage_contents'] = True

        except Exception as e:
            print(f"\n❌ FAILED: {str(e)}")
            print(f"   Trying alternative endpoint...")

            # Try alternative: tags endpoint
            try:
                url = f"{base_url}/{business_id}/tags"
                params = {
                    'access_token': token,
                    'fields': 'id'
                }
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()

                print(f"\n✅ SUCCESS (via /tags endpoint)")
                results['instagram_manage_contents'] = True

            except Exception as e2:
                print(f"\n❌ FAILED: {str(e2)}")
                results['instagram_manage_contents'] = False

        # TEST 8: instagram_basic
        print("\n" + "=" * 80)
        print("TEST 8: instagram_basic")
        print("=" * 80)
        print("API Call: GET /{ig-user-id}?fields=id,username")

        try:
            url = f"{base_url}/{business_id}"
            params = {
                'access_token': token,
                'fields': 'id,username'
            }
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            print(f"\n✅ SUCCESS")
            print(f"   ID: {data.get('id')}")
            print(f"   Username: @{data.get('username')}")
            results['instagram_basic'] = True

        except Exception as e:
            print(f"\n❌ FAILED: {str(e)}")
            results['instagram_basic'] = False

        # CLEANUP: Delete test comment and reply
        print("\n" + "=" * 80)
        print("CLEANUP: Deleting test comment and reply")
        print("=" * 80)

        if reply_id:
            try:
                url = f"{base_url}/{reply_id}"
                params = {'access_token': token}
                response = await client.delete(url, params=params)
                print(f"✅ Deleted reply {reply_id}")
            except Exception as e:
                print(f"⚠️  Could not delete reply: {str(e)}")

        if comment_id:
            try:
                url = f"{base_url}/{comment_id}"
                params = {'access_token': token}
                response = await client.delete(url, params=params)
                print(f"✅ Deleted comment {comment_id}")
            except Exception as e:
                print(f"⚠️  Could not delete comment: {str(e)}")

    # SUMMARY
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)

    passed = sum(1 for r in results.values() if r is True)
    skipped = sum(1 for r in results.values() if r is None)
    failed = sum(1 for r in results.values() if r is False)

    print(f"\nResults: {passed} passed, {skipped} skipped, {failed} failed")
    print("\nDetailed Results:")

    for test_name, result in results.items():
        if result is True:
            status = "✅ PASSED"
        elif result is None:
            status = "⚠️  SKIPPED"
        else:
            status = "❌ FAILED"
        print(f"{status}: {test_name}")

    print("\n" + "=" * 80)
    print("NEXT STEPS")
    print("=" * 80)

    if failed == 0:
        print("\n🎉 All tests passed!")
        print("\nCheck your Meta Developer Console:")
        print("https://developers.facebook.com/apps/1264936368726488/use-cases/")
        print("\nThe API call counters should update within a few minutes to 24 hours.")
        print("If they don't update, try running the same queries in Graph API Explorer directly.")
    else:
        print("\n⚠️  Some tests failed.")
        print("\nFor failed tests, try running them manually in Graph API Explorer:")
        print("https://developers.facebook.com/tools/explorer/")

    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(test_all_endpoints())
    sys.exit(0 if success else 1)
