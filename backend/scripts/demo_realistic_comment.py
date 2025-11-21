"""
Realistic Instagram Auto-Comment Demo for App Review

This script demonstrates the actual comment that will be posted when users
mention @sampletheinternet in their Instagram posts.

Use this for your App Review screen recording to show Meta reviewers
exactly what the feature does.
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


def generate_realistic_comment(username: str, sample_id: int = 123) -> str:
    """
    Generate the actual comment that will be posted in production.

    This matches the format used in app/services/instagram/mention_processor.py
    """
    comment = (
        f"🎵 Hey @{username}! We've extracted the audio from your video and turned it into a sample!\n\n"
        f"🎧 Listen and download: https://app.sampletheinternet.com/samples/{sample_id}\n\n"
        f"Made with SampleTok - Turn any video into a sample! 🔥"
    )
    return comment


async def demo_realistic_comment():
    """
    Post a realistic auto-comment to demonstrate the feature for App Review.
    """
    print("=" * 80)
    print("🎬 Instagram Auto-Comment Demo for App Review")
    print("=" * 80)
    print("\nThis demo shows the ACTUAL comment that users will receive")
    print("when they mention @sampletheinternet in their Instagram posts.\n")

    # Step 1: Get the latest media
    print("📸 Step 1: Finding your latest Instagram post...")
    try:
        media_response = await make_api_call(
            f"{BUSINESS_ACCOUNT_ID}/media",
            params={"fields": "id,caption,media_type,permalink,username", "limit": 1}
        )

        media_list = media_response.get('data', [])
        if not media_list:
            print("❌ ERROR: No media found on @sampletheinternet")
            print("   Please create a test post on Instagram first.")
            return

        media = media_list[0]
        media_id = media['id']
        media_type = media.get('media_type', 'UNKNOWN')
        permalink = media.get('permalink', 'N/A')
        username = media.get('username', 'sampletheinternet')
        caption = media.get('caption', 'No caption')[:80]

        print(f"✅ Found media:")
        print(f"   Media ID: {media_id}")
        print(f"   Type: {media_type}")
        print(f"   URL: {permalink}")
        print(f"   Caption: {caption}...")

    except Exception as e:
        print(f"❌ ERROR getting media: {e}")
        return

    # Step 2: Generate realistic comment
    print("\n💬 Step 2: Generating production-ready auto-comment...")

    # Use a realistic sample ID (e.g., 456 for demo purposes)
    sample_id = 456
    comment_message = generate_realistic_comment(username, sample_id)

    print("\n📝 Comment that will be posted:")
    print("-" * 80)
    print(comment_message)
    print("-" * 80)

    # Step 3: Ask for confirmation
    print("\n⚠️  CONFIRMATION REQUIRED")
    print(f"This will post the above comment to: {permalink}")
    print("\nThis demonstrates the feature for App Review. The comment shows:")
    print("  ✅ Friendly greeting with @mention")
    print("  ✅ Explanation of what happened")
    print("  ✅ Direct link to the sample page")
    print("  ✅ Brand mention (SampleTok)")
    print("\nContinue? (y/n): ", end='')

    # Auto-confirm for script (remove this for interactive use)
    confirmation = "y"  # Change to input() for interactive mode

    if confirmation.lower() != 'y':
        print("\n❌ Cancelled. No comment posted.")
        return

    # Step 4: Post the comment
    print("\n🚀 Step 3: Posting realistic auto-comment...")
    try:
        result = await make_api_call(
            f"{media_id}/comments",
            params={"message": comment_message},
            method="POST"
        )

        comment_id = result['id']
        print(f"✅ SUCCESS! Comment posted")
        print(f"   Comment ID: {comment_id}")
        print(f"   Posted to: {permalink}")

    except Exception as e:
        print(f"❌ ERROR posting comment: {e}")
        if "Comments are disabled" in str(e):
            print("\n💡 TIP: Enable comments on this Instagram post and try again")
        return

    # Step 5: Verify the comment
    print("\n🔍 Step 4: Verifying comment was posted...")
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
            print(f"✅ Comment verified on Instagram!")
            print(f"   Username: {our_comment.get('username')}")
            print(f"   Timestamp: {our_comment.get('timestamp')}")
        else:
            print("⚠️  Comment posted but not found in verification")

    except Exception as e:
        print(f"⚠️  Could not verify comment: {e}")

    # Final instructions
    print("\n" + "=" * 80)
    print("🎥 App Review Recording Instructions")
    print("=" * 80)
    print("\nFor your screen recording, show this flow:\n")
    print("1. 📱 Open Instagram app (mobile or desktop)")
    print("2. 🖼️  Create/show a test post")
    print("3. ✏️  Add caption mentioning @sampletheinternet")
    print("4. 📤 Post the content")
    print("5. ⏱️  Wait 30-60 seconds (mention our automated processing)")
    print("6. 💬 Show the auto-comment that appears")
    print("7. 🔗 Click the link in the comment to show the sample page")
    print("8. 🎧 Play the audio sample to demonstrate the feature")
    print("\n💡 Script to say during recording:")
    print("-" * 80)
    print('"When a user mentions @sampletheinternet in their Instagram post,')
    print('our app automatically:')
    print('  1. Detects the mention via Instagram webhooks')
    print('  2. Downloads the video from their post')
    print('  3. Extracts and processes the audio')
    print('  4. Creates a shareable sample on our platform')
    print('  5. Posts this helpful comment with a direct link')
    print('')
    print('This allows content creators to easily extract audio from their')
    print('Instagram videos and share samples with their audience."')
    print("-" * 80)

    print(f"\n✅ Check the comment on Instagram: {permalink}")
    print("\n🎬 Ready to record your App Review demo!")


async def show_comment_variations():
    """
    Show different comment variations for different scenarios.
    """
    print("\n" + "=" * 80)
    print("📝 Comment Variations for Different Scenarios")
    print("=" * 80)

    scenarios = [
        {
            "name": "Standard Video Post",
            "username": "musicproducer",
            "sample_id": 789,
            "description": "When user posts a video and mentions us"
        },
        {
            "name": "Reel Post",
            "username": "djcoolname",
            "sample_id": 101,
            "description": "When user posts a Reel and mentions us"
        },
        {
            "name": "Carousel Post",
            "username": "beatmaker",
            "sample_id": 202,
            "description": "When user posts carousel with video and mentions us"
        }
    ]

    for i, scenario in enumerate(scenarios, 1):
        print(f"\n{i}. {scenario['name']}")
        print(f"   Scenario: {scenario['description']}")
        print(f"\n   Comment:")
        print("   " + "-" * 76)
        comment = generate_realistic_comment(scenario['username'], scenario['sample_id'])
        for line in comment.split('\n'):
            print(f"   {line}")
        print("   " + "-" * 76)


if __name__ == "__main__":
    print("\n🎯 Choose an option:")
    print("1. Post realistic demo comment (for App Review recording)")
    print("2. Show comment variations (no posting)\n")

    choice = "1"  # Change to input("Enter choice (1 or 2): ") for interactive

    if choice == "1":
        asyncio.run(demo_realistic_comment())
    elif choice == "2":
        asyncio.run(show_comment_variations())
    else:
        print("Invalid choice")
