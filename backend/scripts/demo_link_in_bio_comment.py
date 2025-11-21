"""
Instagram "Link in Bio" Flow Demo

Simple, professional flow:
1. User mentions @sampletheinternet
2. We comment with BPM/Key info + "Link in bio"
3. User clicks our profile link to find their sample

This is the cleanest approach - no DMs, no public links.
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


def generate_link_in_bio_comment(username: str, bpm: int = 128, key: str = "A minor") -> str:
    """
    Generate a comment with sample info + link in bio.

    This is what actually gets posted in production after audio analysis.
    Shows the value (BPM/Key) and directs to profile link.
    """
    comment = (
        f"🎵 @{username} Your audio sample is ready!\n\n"
        f"🎹 Key: {key}\n"
        f"⏱️ BPM: {bpm}\n\n"
        f"🔗 Find your sample via our link in bio!\n\n"
        f"💡 Don't forget to tag the original creator if you end up remixing it."
    )
    return comment


def generate_link_in_bio_comment_v2(username: str, bpm: int = 128, key: str = "A minor") -> str:
    """
    Alternative version - shorter and punchier.
    """
    comment = (
        f"🎵 @{username} Sample extracted!\n\n"
        f"{key} • {bpm} BPM\n\n"
        f"Download link in bio 🔥\n\n"
        f"💡 Tag the original creator if you remix this!"
    )
    return comment


def generate_link_in_bio_comment_v3(username: str, bpm: int = 128, key: str = "A minor") -> str:
    """
    Alternative version - professional and informative.
    """
    comment = (
        f"✅ @{username} Audio extracted and analyzed!\n\n"
        f"📊 BPM: {bpm}\n"
        f"🎹 Key: {key}\n\n"
        f"🎧 Listen & download → Link in our bio\n\n"
        f"💡 Tag the original creator if you remix this!"
    )
    return comment


async def demo_link_in_bio_flow():
    """
    Demonstrate the "Link in Bio" flow for App Review.
    Finds comments that tagged @sampletheinternet and replies to them.
    """
    print("=" * 80)
    print("🎬 Instagram 'Link in Bio' Flow Demo")
    print("=" * 80)
    print("\nClean, professional flow:")
    print("  1. Find comments that mention @sampletheinternet")
    print("  2. Reply with audio analysis (BPM, Key)")
    print("  3. User clicks link in our bio to find sample")
    print("  4. No DMs, no public sample links needed")
    print()

    # Step 1: Get recent media to search for mentions
    print("📸 Step 1: Searching for comments mentioning @sampletheinternet...")
    try:
        media_response = await make_api_call(
            f"{BUSINESS_ACCOUNT_ID}/media",
            params={"fields": "id,caption,media_type,permalink,username", "limit": 10}
        )

        media_list = media_response.get('data', [])
        if not media_list:
            print("❌ ERROR: No media found")
            return

        # Search through media for comments mentioning @sampletheinternet
        mention_found = False
        target_media_id = None
        target_comment_id = None
        target_username = None
        target_permalink = None

        for media in media_list:
            media_id = media['id']
            permalink = media.get('permalink')

            # Get comments on this media
            try:
                comments_response = await make_api_call(
                    f"{media_id}/comments",
                    params={"fields": "id,text,username"}
                )

                comments = comments_response.get('data', [])

                for comment in comments:
                    comment_text = comment.get('text', '').lower()
                    if '@sampletheinternet' in comment_text or 'sampletheinternet' in comment_text:
                        mention_found = True
                        target_media_id = media_id
                        target_comment_id = comment['id']
                        target_username = comment.get('username', 'user')
                        target_permalink = permalink
                        print(f"✅ Found mention in comment by @{target_username}")
                        print(f"   Comment: {comment.get('text', '')[:80]}...")
                        print(f"   Post URL: {permalink}")
                        break

                if mention_found:
                    break

            except Exception as e:
                # Skip if we can't read comments on this media
                continue

        if not mention_found:
            print("⚠️  No comments mentioning @sampletheinternet found")
            print("   Falling back to replying to latest media...")
            # Fallback to first media
            media = media_list[0]
            target_media_id = media['id']
            target_permalink = media.get('permalink')
            target_username = 'hussontomm'
            target_comment_id = None  # Will post as top-level comment

    except Exception as e:
        print(f"❌ ERROR: {e}")
        return

    # Step 2: Show comment variations
    print("\n💬 Step 2: Comment Options (choose your favorite)...")

    # Use realistic BPM and key from actual audio analysis
    bpm = 140  # Example from beat analysis
    key = "G minor"  # Example from key detection

    print("\n📝 Version 1: Detailed")
    print("-" * 80)
    comment_v1 = generate_link_in_bio_comment(target_username, bpm, key)
    print(comment_v1)
    print("-" * 80)

    print("\n📝 Version 2: Short & Punchy")
    print("-" * 80)
    comment_v2 = generate_link_in_bio_comment_v2(target_username, bpm, key)
    print(comment_v2)
    print("-" * 80)

    print("\n📝 Version 3: Professional")
    print("-" * 80)
    comment_v3 = generate_link_in_bio_comment_v3(target_username, bpm, key)
    print(comment_v3)
    print("-" * 80)

    # Ask which version to post
    print("\n🎯 Which version should we post?")
    print("1. Detailed (shows all info)")
    print("2. Short & Punchy (minimal, cool)")
    print("3. Professional (balanced)")

    choice = "2"  # Default to short & punchy (change to input() for interactive)

    if choice == "1":
        selected_comment = comment_v1
        version_name = "Detailed"
    elif choice == "2":
        selected_comment = comment_v2
        version_name = "Short & Punchy"
    elif choice == "3":
        selected_comment = comment_v3
        version_name = "Professional"
    else:
        selected_comment = comment_v2
        version_name = "Short & Punchy (default)"

    # Step 3: Post the comment (reply if we found a mention, otherwise top-level)
    if target_comment_id:
        print(f"\n🚀 Step 3: Replying to @{target_username}'s comment...")
        endpoint = f"{target_comment_id}/replies"
    else:
        print(f"\n🚀 Step 3: Posting '{version_name}' comment...")
        endpoint = f"{target_media_id}/comments"

    try:
        result = await make_api_call(
            endpoint,
            params={"message": selected_comment},
            method="POST"
        )

        comment_id = result['id']
        print(f"\n✅ Comment posted!")
        print(f"   Comment ID: {comment_id}")
        print(f"   Version: {version_name}")
        if target_comment_id:
            print(f"   Type: Reply to @{target_username}'s mention")
        print(f"   View at: {target_permalink}")

    except Exception as e:
        print(f"❌ ERROR: {e}")
        return

    # Instructions
    print("\n" + "=" * 80)
    print("🎥 App Review Demo Instructions")
    print("=" * 80)
    print("\n📹 For screen recording, show this flow:\n")
    print("1. 📱 Open Instagram, show post mentioning @sampletheinternet")
    print("2. 💬 Show the comment with BPM/Key analysis")
    print("3. 👆 Click @sampletheinternet profile")
    print("4. 🔗 Click the link in bio")
    print("5. 🌐 Show the SampleTok website with their sample")
    print("6. 🎧 Play the audio sample")
    print("7. 📊 Show the BPM/Key matches the comment")

    print("\n💡 Script for recording:")
    print("-" * 80)
    print('"When a user mentions @sampletheinternet in their Instagram post,')
    print('our system automatically:')
    print('')
    print('  1. Detects the mention via webhooks')
    print('  2. Downloads and analyzes the audio')
    print('  3. Extracts BPM and musical key')
    print('  4. Posts these results as a comment')
    print('  5. User finds their sample via our profile link')
    print('')
    print('This provides valuable music production data while keeping')
    print('sample links organized in one place - our link in bio."')
    print("-" * 80)

    print(f"\n✅ Check the comment: {target_permalink}")

    print("\n📋 What to put in Instagram bio:")
    print("   🎵 Turn any video into a sample")
    print("   👉 https://app.sampletheinternet.com")
    print("\n   (Instagram will auto-convert this to a clickable link)")


if __name__ == "__main__":
    asyncio.run(demo_link_in_bio_flow())
