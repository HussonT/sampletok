"""
Debug Instagram access token to check validity and permissions.
"""
import asyncio
import sys
from pathlib import Path
import httpx

sys.path.insert(0, str(Path(__file__).parent))

from app.core.config import settings


async def debug_token():
    """Debug the current access token"""

    print("=" * 80)
    print("INSTAGRAM ACCESS TOKEN DEBUGGER")
    print("=" * 80)

    token = settings.INSTAGRAM_ACCESS_TOKEN
    app_id = settings.INSTAGRAM_APP_ID
    app_secret = settings.INSTAGRAM_APP_SECRET

    if not token or token == "your-long-lived-instagram-access-token-here":
        print("\n❌ No access token configured in .env")
        return

    print(f"\nToken (first 30 chars): {token[:30]}...")
    print(f"App ID: {app_id}")

    # Method 1: Debug token using Meta's debug endpoint
    print("\n" + "-" * 80)
    print("Checking token validity with Meta Debug API...")
    print("-" * 80)

    try:
        # Use app access token to debug user token
        debug_url = "https://graph.facebook.com/debug_token"
        params = {
            'input_token': token,
            'access_token': f"{app_id}|{app_secret}"
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(debug_url, params=params)
            response.raise_for_status()
            data = response.json()

        token_data = data.get('data', {})

        print(f"\n✅ Token is valid!")
        print(f"   App ID: {token_data.get('app_id')}")
        print(f"   User ID: {token_data.get('user_id')}")
        print(f"   Valid: {token_data.get('is_valid')}")
        print(f"   Issued at: {token_data.get('issued_at')}")
        print(f"   Expires at: {token_data.get('expires_at', 'Never')}")

        if 'data_access_expires_at' in token_data:
            print(f"   Data access expires at: {token_data.get('data_access_expires_at')}")

        # Show scopes/permissions
        scopes = token_data.get('scopes', [])
        print(f"\n   Permissions ({len(scopes)}):")
        for scope in scopes:
            print(f"      - {scope}")

        # Check for required permissions
        required_scopes = [
            'instagram_manage_contents',
            'instagram_business_content_publish',
            'instagram_business_manage_comments',
            'pages_read_engagement',
            'instagram_business_basic',
        ]

        missing = [s for s in required_scopes if s not in scopes]
        if missing:
            print(f"\n   ⚠️  Missing permissions:")
            for scope in missing:
                print(f"      - {scope}")
        else:
            print(f"\n   ✅ All required permissions present!")

    except httpx.HTTPStatusError as e:
        print(f"\n❌ Failed to debug token: {e}")
        try:
            error_data = e.response.json()
            print(f"   Error: {error_data.get('error', {}).get('message')}")
        except:
            pass
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")

    # Method 2: Try a simple API call
    print("\n" + "-" * 80)
    print("Testing with a simple API call...")
    print("-" * 80)

    try:
        business_id = settings.INSTAGRAM_BUSINESS_ACCOUNT_ID
        url = f"https://graph.facebook.com/v21.0/{business_id}"
        params = {
            'access_token': token,
            'fields': 'id,username'
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

        print(f"\n✅ API call successful!")
        print(f"   Account ID: {data.get('id')}")
        print(f"   Username: @{data.get('username')}")

    except httpx.HTTPStatusError as e:
        print(f"\n❌ API call failed: {e.response.status_code}")
        try:
            error_data = e.response.json()
            error_msg = error_data.get('error', {}).get('message', str(e))
            print(f"   Error: {error_msg}")

            # Common error messages
            if "Invalid OAuth access token" in error_msg:
                print("\n   💡 The token is invalid or expired.")
                print("      Generate a new token at: https://developers.facebook.com/tools/explorer/")
            elif "permissions" in error_msg.lower():
                print("\n   💡 The token doesn't have required permissions.")
                print("      Re-generate with all required permissions selected.")
            elif "Cannot parse access token" in error_msg:
                print("\n   💡 The token format is incorrect.")
                print("      Make sure you copied the entire token without spaces/newlines.")

        except:
            print(f"   Raw error: {e}")
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")

    # Summary and next steps
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print("\nIf the token is invalid:")
    print("1. Go to https://developers.facebook.com/tools/explorer/")
    print("2. Select your app from the dropdown")
    print("3. Click 'Generate Access Token'")
    print("4. Select these permissions:")
    print("   ✅ instagram_manage_contents")
    print("   ✅ instagram_business_content_publish")
    print("   ✅ instagram_business_manage_comments")
    print("   ✅ pages_read_engagement")
    print("   ✅ instagram_business_basic")
    print("   ✅ instagram_business_manage_messages")
    print("5. Copy the new token and update INSTAGRAM_ACCESS_TOKEN in .env")
    print("6. Re-run: python test_meta_use_cases.py")


if __name__ == "__main__":
    asyncio.run(debug_token())
