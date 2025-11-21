"""
Instagram "Check DMs" Flow Demo

This demonstrates a two-step flow:
1. Comment on post: "Check your DMs!"
2. When user DMs us, auto-reply with sample link

This is better for privacy and keeps links out of public comments.
"""

import httpx
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

ACCESS_TOKEN = os.getenv('INSTAGRAM_ACCESS_TOKEN')
BUSINESS_ACCOUNT_ID = os.getenv('INSTAGRAM_BUSINESS_ACCOUNT_ID')
BASE_URL = "https://graph.facebook.com/v18.0"


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


def generate_check_dms_comment(username: str) -> str:
    """
    Generate a comment that tells user to check DMs.
    No link in public comment = better privacy.
    """
    comment = (
        f"🎵 Hey @{username}! We've extracted the audio from your video!\n\n"
        f"✉️ Check your DMs for the download link 🔥"
    )
    return comment


def generate_dm_response(username: str, sample_id: int) -> str:
    """
    Generate the DM message with the sample link.
    This is sent privately when user DMs us.
    """
    message = (
        f"🎧 Hey {username}!\n\n"
        f"Your audio sample is ready! 🔥\n\n"
        f"Listen and download here:\n"
        f"https://app.sampletheinternet.com/samples/{sample_id}\n\n"
        f"Made with SampleTok - Turn any video into a sample!"
    )
    return message


async def demo_check_dms_flow():
    """
    Demonstrate the "Check DMs" flow for App Review.
    """
    print("=" * 80)
    print("🎬 Instagram 'Check DMs' Flow Demo")
    print("=" * 80)
    print("\nThis is a privacy-friendly two-step flow:")
    print("  1. Public comment: 'Check your DMs!'")
    print("  2. Private DM: Sample link sent privately")
    print()

    # Step 1: Get latest media
    print("📸 Step 1: Finding your latest Instagram post...")
    try:
        media_response = await make_api_call(
            f"{BUSINESS_ACCOUNT_ID}/media",
            params={"fields": "id,caption,media_type,permalink,username", "limit": 1}
        )

        media_list = media_response.get('data', [])
        if not media_list:
            print("❌ ERROR: No media found")
            return

        media = media_list[0]
        media_id = media['id']
        permalink = media.get('permalink')
        username = media.get('username', 'sampletheinternet')
        caption = media.get('caption', 'No caption')[:80]

        print(f"✅ Found media:")
        print(f"   URL: {permalink}")
        print(f"   Caption: {caption}...")

    except Exception as e:
        print(f"❌ ERROR: {e}")
        return

    # Step 2: Post "Check DMs" comment
    print("\n💬 Step 2: Posting 'Check your DMs' comment...")

    check_dms_comment = generate_check_dms_comment(username)

    print("\n📝 Public comment:")
    print("-" * 80)
    print(check_dms_comment)
    print("-" * 80)

    try:
        result = await make_api_call(
            f"{media_id}/comments",
            params={"message": check_dms_comment},
            method="POST"
        )

        comment_id = result['id']
        print(f"\n✅ Comment posted!")
        print(f"   Comment ID: {comment_id}")
        print(f"   View at: {permalink}")

    except Exception as e:
        print(f"❌ ERROR: {e}")
        return

    # Step 3: Show what DM response would look like
    print("\n✉️ Step 3: DM Response (sent when user DMs us)...")

    sample_id = 789  # Example sample ID
    dm_message = generate_dm_response(username, sample_id)

    print("\n📝 Private DM message:")
    print("-" * 80)
    print(dm_message)
    print("-" * 80)

    # Step 4: Test receiving DMs (check if we can access conversations)
    print("\n📬 Step 4: Checking DM capabilities...")

    try:
        # Try to get conversations (requires instagram_manage_messages)
        conversations = await make_api_call(
            f"{BUSINESS_ACCOUNT_ID}/conversations",
            params={"fields": "id,updated_time", "limit": 5}
        )

        conv_count = len(conversations.get('data', []))
        print(f"✅ DM access working! Found {conv_count} conversations")

        if conv_count > 0:
            print("\n   Recent conversations:")
            for conv in conversations.get('data', [])[:3]:
                print(f"   - Conversation ID: {conv['id']}")
                print(f"     Updated: {conv.get('updated_time')}")

    except Exception as e:
        error_msg = str(e)
        if "instagram_manage_messages" in error_msg or "permission" in error_msg.lower():
            print(f"⚠️  DM permission not yet approved")
            print(f"   You have: instagram_business_manage_messages")
            print(f"   You need: instagram_manage_messages with Advanced Access")
            print(f"\n   Current error: {e}")
        else:
            print(f"⚠️  Error checking DMs: {e}")

    # Instructions
    print("\n" + "=" * 80)
    print("🎥 App Review Demo Instructions")
    print("=" * 80)
    print("\n📹 For screen recording, show this flow:\n")
    print("1. 📱 Show Instagram post with @sampletheinternet mention")
    print("2. 💬 Show the 'Check your DMs' comment that was posted")
    print("3. ✉️  Show Instagram DMs")
    print("4. 📨 Demonstrate sending a DM to @sampletheinternet")
    print("5. 🤖 Show the auto-reply with sample link")
    print("6. 🔗 Click the link to show sample page")
    print("7. 🎧 Play the audio sample")

    print("\n💡 Script for recording:")
    print("-" * 80)
    print('"When a user mentions @sampletheinternet in their post,')
    print('we post a comment telling them to check their DMs.')
    print('')
    print('This keeps the sample link private. When they message us,')
    print('we automatically reply with their sample link.')
    print('')
    print('This provides better privacy while still giving users')
    print('instant access to their audio samples."')
    print("-" * 80)

    print("\n📋 Next Steps:")
    print("   1. ✅ Comment posted - check Instagram")
    print("   2. 📱 Manually DM @sampletheinternet from another account")
    print("   3. 🤖 We'll auto-reply with the sample link (once webhooks work)")
    print("   4. 🎬 Record this flow for App Review")


async def test_send_dm_manually():
    """
    Test sending a DM response manually (for demo purposes).

    Note: This requires a conversation_id from an existing DM thread.
    You can't initiate DMs - user must DM you first.
    """
    print("\n" + "=" * 80)
    print("🧪 Manual DM Test")
    print("=" * 80)
    print("\nTo test DM replies:")
    print("1. Use another Instagram account to DM @sampletheinternet")
    print("2. Get the conversation_id from the webhook or API")
    print("3. Use this script to reply")
    print("\nFor App Review, you can:")
    print("  - Show the webhook payload that triggers the DM")
    print("  - Show the DM appearing in Instagram")
    print("  - Explain it's automated via webhooks")


if __name__ == "__main__":
    print("\n🎯 Instagram DM Flow Options:")
    print("1. Demo 'Check DMs' flow (posts comment)")
    print("2. Show manual DM test info\n")

    choice = "1"  # Change to input() for interactive

    if choice == "1":
        asyncio.run(demo_check_dms_flow())
    elif choice == "2":
        asyncio.run(test_send_dm_manually())
