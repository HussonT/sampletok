"""
Instagram Business Basic Permission Use Case Demo

This script demonstrates how SampleTok uses instagram_business_basic
as a dependent permission for instagram_manage_comments.

USE CASE:
SampleTok responds to creators who mention @sampletheinternet in their Reels
by providing processed audio information. When mentioned:

1. We detect the mention via webhook
2. We access media metadata to identify the post and creator
3. We post an automated comment with information about the audio (BPM, key)
   and invite them to check our link in bio

The instagram_business_basic permission allows us to:
- Access our Business Account information
- Read usernames and media IDs from posts where we're mentioned
- Properly attribute and respond to creators

PERMISSIONS DEMONSTRATED:
- instagram_business_basic: Access Business Account info, read usernames and media IDs
- instagram_manage_comments: Post automated comments with audio analysis
- pages_read_engagement: Receive mention webhooks

This script simulates the complete flow for Meta App Review demonstration.
"""

import httpx
import asyncio
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

ACCESS_TOKEN = os.getenv('INSTAGRAM_ACCESS_TOKEN')
BUSINESS_ACCOUNT_ID = os.getenv('INSTAGRAM_BUSINESS_ACCOUNT_ID')
BASE_URL = "https://graph.facebook.com/v18.0"


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


def simulate_webhook_payload():
    """
    Simulate the webhook payload we receive when a user mentions @sampletheinternet
    """
    return {
        "object": "instagram",
        "entry": [
            {
                "id": BUSINESS_ACCOUNT_ID,
                "time": int(datetime.now().timestamp()),
                "changes": [
                    {
                        "value": {
                            "media_id": "example_media_id",
                            "comment_id": "example_mention_id"
                        },
                        "field": "mentions"
                    }
                ]
            }
        ]
    }


async def demo_business_basic_use_case():
    """
    Demonstrate the complete flow of how we use instagram_business_basic
    """
    print("=" * 80)
    print("🎬 SampleTok: instagram_business_basic Use Case Demo")
    print("=" * 80)
    print("\n📋 Use Case: Automated Audio Analysis Comments for Creators\n")

    # Step 1: Verify Business Account Access (instagram_business_basic)
    print("=" * 80)
    print("STEP 1: Access Business Account Information")
    print("=" * 80)
    print("Permission: instagram_business_basic")
    print("Purpose: Verify our Business Account identity and access\n")

    try:
        business_info = await make_api_call(
            f"{BUSINESS_ACCOUNT_ID}",
            params={
                "fields": "id,username,name,biography,followers_count,follows_count,media_count"
            }
        )

        print("✅ Successfully accessed Business Account:")
        print(f"   Account ID: {business_info.get('id')}")
        print(f"   Username: @{business_info.get('username')}")
        print(f"   Display Name: {business_info.get('name')}")
        print(f"   Followers: {business_info.get('followers_count', 'N/A')}")
        print(f"   Media Count: {business_info.get('media_count', 'N/A')}")

    except Exception as e:
        print(f"❌ ERROR: {e}")
        return

    # Step 2: Simulate Webhook Reception
    print("\n" + "=" * 80)
    print("STEP 2: Receive Mention Webhook")
    print("=" * 80)
    print("Permission: pages_read_engagement")
    print("Purpose: Detect when creators mention @sampletheinternet\n")

    webhook_payload = simulate_webhook_payload()
    print("📨 Webhook Payload Received:")
    print(f"   Object: {webhook_payload['object']}")
    print(f"   Business Account: {webhook_payload['entry'][0]['id']}")
    print(f"   Field: {webhook_payload['entry'][0]['changes'][0]['field']}")
    print(f"   Media ID: {webhook_payload['entry'][0]['changes'][0]['value']['media_id']}")

    # Step 3: Get Latest Media (for demo, use actual latest post)
    print("\n" + "=" * 80)
    print("STEP 3: Access Media Metadata")
    print("=" * 80)
    print("Permission: instagram_business_basic + instagram_content_publish")
    print("Purpose: Identify the post and creator who mentioned us\n")

    try:
        media_response = await make_api_call(
            f"{BUSINESS_ACCOUNT_ID}/media",
            params={
                "fields": "id,caption,media_type,permalink,username,timestamp",
                "limit": 1
            }
        )

        media_list = media_response.get('data', [])
        if not media_list:
            print("❌ ERROR: No media found")
            return

        media = media_list[0]
        media_id = media['id']
        permalink = media.get('permalink')
        username = media.get('username', 'unknown')
        media_type = media.get('media_type', 'UNKNOWN')
        timestamp = media.get('timestamp', 'N/A')
        caption = media.get('caption', 'No caption')[:100]

        print("✅ Media Information Retrieved:")
        print(f"   Media ID: {media_id}")
        print(f"   Media Type: {media_type}")
        print(f"   Creator: @{username}")
        print(f"   Posted: {timestamp}")
        print(f"   URL: {permalink}")
        print(f"   Caption: {caption}...")

    except Exception as e:
        print(f"❌ ERROR: {e}")
        return

    # Step 4: Simulate Audio Analysis
    print("\n" + "=" * 80)
    print("STEP 4: Audio Analysis (Backend Processing)")
    print("=" * 80)
    print("Purpose: Extract and analyze audio from the video\n")

    # Simulate audio analysis results
    bpm = 140
    key = "G minor"

    print("🎵 Audio Analysis Complete:")
    print(f"   BPM: {bpm}")
    print(f"   Key: {key}")

    # Step 5: Generate Automated Comment
    print("\n" + "=" * 80)
    print("STEP 5: Generate Automated Response")
    print("=" * 80)
    print("Purpose: Create helpful comment with audio information\n")

    comment_message = (
        f"✅ @{username} Audio extracted and analyzed!\n\n"
        f"📊 BPM: {bpm}\n"
        f"🎹 Key: {key}\n\n"
        f"🎧 Listen & download → Link in our bio\n\n"
        f"💡 Tag the original creator if you remix this!"
    )

    print("📝 Comment to Post:")
    print("-" * 80)
    print(comment_message)
    print("-" * 80)

    # Step 6: Post Comment (instagram_manage_comments)
    print("\n" + "=" * 80)
    print("STEP 6: Post Automated Comment")
    print("=" * 80)
    print("Permission: instagram_manage_comments")
    print("Purpose: Respond to creator with audio analysis results\n")

    try:
        result = await make_api_call(
            f"{media_id}/comments",
            params={"message": comment_message},
            method="POST"
        )

        comment_id = result['id']
        print("✅ Comment Posted Successfully!")
        print(f"   Comment ID: {comment_id}")
        print(f"   Posted to: {permalink}")

    except Exception as e:
        print(f"❌ ERROR: {e}")
        return

    # Step 7: Verify Comment
    print("\n" + "=" * 80)
    print("STEP 7: Verify Comment Visibility")
    print("=" * 80)
    print("Permission: instagram_business_basic + instagram_manage_comments")
    print("Purpose: Confirm comment is visible to creator\n")

    try:
        comments = await make_api_call(
            f"{media_id}/comments",
            params={"fields": "id,text,username,timestamp"}
        )

        our_comment = None
        for comment in comments.get('data', []):
            if comment['id'] == comment_id:
                our_comment = comment
                break

        if our_comment:
            print("✅ Comment Verified on Instagram:")
            print(f"   Username: {our_comment.get('username')}")
            print(f"   Timestamp: {our_comment.get('timestamp')}")
        else:
            print("⚠️  Comment posted but not found in verification")

    except Exception as e:
        print(f"⚠️  Could not verify comment: {e}")

    # Summary
    print("\n" + "=" * 80)
    print("📊 PERMISSION USAGE SUMMARY")
    print("=" * 80)
    print("\n✅ instagram_business_basic Usage:")
    print("   • Access Business Account ID and username")
    print("   • Read account metadata (followers, media count)")
    print("   • Identify our account for proper attribution")
    print("   • Required dependency for instagram_manage_comments")

    print("\n✅ instagram_manage_comments Usage:")
    print("   • Post automated comment with audio analysis")
    print("   • Verify comment visibility")
    print("   • Provide value to creators (BPM, key information)")

    print("\n✅ pages_read_engagement Usage:")
    print("   • Receive webhooks when mentioned")
    print("   • Access engagement data from media")

    print("\n" + "=" * 80)
    print("💡 VALUE PROPOSITION FOR CREATORS")
    print("=" * 80)
    print("\nSampleTok provides instant value to content creators by:")
    print("  1. Automatically analyzing audio from their videos")
    print("  2. Providing BPM and musical key information")
    print("  3. Offering easy access to processed samples")
    print("  4. Encouraging proper creator attribution")

    print("\n" + "=" * 80)
    print("🎥 APP REVIEW DEMONSTRATION")
    print("=" * 80)
    print("\nFor screen recording, show this complete flow:")
    print("\n1. 📱 Open Instagram and show a Reel")
    print("2. 💬 Show the automated comment with BPM/Key analysis")
    print("3. 👤 Click on @sampletheinternet to show our Business Account")
    print("4. 🔗 Click the link in our bio to access samples")
    print("5. 🎧 Play the processed audio sample")
    print("6. 📊 Verify BPM/Key matches the Instagram comment")

    print("\n" + "=" * 80)
    print("✅ DEMO COMPLETE")
    print("=" * 80)
    print(f"\nCheck the posted comment: {permalink}")
    print("\nThis demonstrates how instagram_business_basic enables")
    print("SampleTok to provide automated, valuable responses to creators.")


if __name__ == "__main__":
    asyncio.run(demo_business_basic_use_case())
