#!/usr/bin/env python3
"""
Interactive script to help you get Instagram Graph API credentials.

This script guides you through the process of getting your credentials
from the Graph API Explorer and saves them to your .env file.

Usage:
    python scripts/get_instagram_credentials.py
"""

import os
import sys
from pathlib import Path


def print_header(text: str):
    """Print a formatted header"""
    print("\n" + "=" * 80)
    print(text)
    print("=" * 80 + "\n")


def print_step(number: int, text: str):
    """Print a step number with text"""
    print(f"\n📋 Step {number}: {text}")
    print("-" * 80)


def main():
    print_header("Instagram Graph API Credentials Setup")

    print("This script will help you get the credentials needed for Instagram integration.")
    print("\nPrerequisites:")
    print("  ✓ You have a Facebook account")
    print("  ✓ You have an Instagram Business or Creator account")
    print("  ✓ Your Instagram account is connected to a Facebook Page")
    print("  ✓ You have created a Facebook App at https://developers.facebook.com/apps/")

    response = input("\n✅ Do you meet all prerequisites? (y/n): ")
    if response.lower() != 'y':
        print("\n❌ Please complete the prerequisites first.")
        print("   See INSTAGRAM_QUICK_TEST.md for detailed setup instructions.")
        sys.exit(1)

    # Step 1: Get App ID and Secret
    print_step(1, "Get your App ID and App Secret")
    print("1. Go to https://developers.facebook.com/apps/")
    print("2. Select your app")
    print("3. Go to Settings → Basic")
    print("4. Copy your App ID and App Secret")

    app_id = input("\nEnter your App ID: ").strip()
    app_secret = input("Enter your App Secret: ").strip()

    # Step 2: Get Access Token
    print_step(2, "Get your Access Token with required permissions")
    print("1. Go to https://developers.facebook.com/tools/explorer/")
    print("2. Select your app from the dropdown")
    print("3. Click 'Generate Access Token'")
    print("4. Select these permissions:")
    print("   - instagram_manage_contents")
    print("   - instagram_business_content_publish")
    print("   - instagram_business_manage_comments")
    print("   - pages_read_engagement")
    print("   - instagram_business_basic")
    print("   - instagram_business_manage_messages")
    print("5. Click 'Generate Access Token'")
    print("6. Copy the access token")

    access_token = input("\nEnter your Access Token: ").strip()

    # Step 3: Get Business Account ID
    print_step(3, "Get your Instagram Business Account ID")
    print("1. Stay in Graph API Explorer")
    print("2. With your access token active, run this query:")
    print("   me/accounts?fields=instagram_business_account")
    print("3. Find your Facebook Page in the results")
    print("4. Look for 'instagram_business_account' → 'id'")
    print("5. Copy that ID")
    print("\nAlternatively, run:")
    print(f"   me/accounts → select your page → run:")
    print(f"   {{page-id}}?fields=instagram_business_account")

    business_account_id = input("\nEnter your Instagram Business Account ID: ").strip()

    # Step 4: Generate webhook verify token
    print_step(4, "Generate Webhook Verify Token")
    print("This is a random token you create for webhook security.")

    import secrets
    webhook_token = secrets.token_hex(32)
    print(f"\n✅ Generated random token: {webhook_token}")

    # Step 5: Save to .env
    print_step(5, "Save credentials to .env file")

    env_path = Path(__file__).parent.parent / ".env"

    if not env_path.exists():
        print(f"\n❌ .env file not found at {env_path}")
        print("   Please copy .env.example to .env first:")
        print("   cp .env.example .env")
        sys.exit(1)

    # Read current .env
    with open(env_path, 'r') as f:
        env_content = f.read()

    # Replace placeholder values
    replacements = {
        'INSTAGRAM_APP_ID=your-facebook-app-id': f'INSTAGRAM_APP_ID={app_id}',
        'INSTAGRAM_APP_ID=your-facebook-app-id-here': f'INSTAGRAM_APP_ID={app_id}',
        'INSTAGRAM_APP_SECRET=your-facebook-app-secret': f'INSTAGRAM_APP_SECRET={app_secret}',
        'INSTAGRAM_APP_SECRET=your-facebook-app-secret-here': f'INSTAGRAM_APP_SECRET={app_secret}',
        'INSTAGRAM_ACCESS_TOKEN=your-long-lived-instagram-access-token': f'INSTAGRAM_ACCESS_TOKEN={access_token}',
        'INSTAGRAM_ACCESS_TOKEN=your-long-lived-instagram-access-token-here': f'INSTAGRAM_ACCESS_TOKEN={access_token}',
        'INSTAGRAM_BUSINESS_ACCOUNT_ID=your-instagram-business-account-id': f'INSTAGRAM_BUSINESS_ACCOUNT_ID={business_account_id}',
        'INSTAGRAM_BUSINESS_ACCOUNT_ID=your-instagram-business-account-id-here': f'INSTAGRAM_BUSINESS_ACCOUNT_ID={business_account_id}',
        'INSTAGRAM_WEBHOOK_VERIFY_TOKEN=your-random-webhook-verify-token-here': f'INSTAGRAM_WEBHOOK_VERIFY_TOKEN={webhook_token}',
    }

    for old, new in replacements.items():
        env_content = env_content.replace(old, new)

    # Write back to .env
    with open(env_path, 'w') as f:
        f.write(env_content)

    print(f"\n✅ Credentials saved to {env_path}")

    # Step 6: Run tests
    print_step(6, "Test your credentials")
    print("Run the test script to verify everything is working:")
    print("\n   python test_instagram_graph_api.py")

    run_now = input("\n🚀 Run tests now? (y/n): ")
    if run_now.lower() == 'y':
        print("\nRunning tests...\n")
        os.system("python test_instagram_graph_api.py")

    print("\n" + "=" * 80)
    print("✅ Setup complete!")
    print("=" * 80)
    print("\nNext steps:")
    print("1. If tests pass, you're ready to use the integration in development mode")
    print("2. Test the end-to-end flow by tagging your Instagram account in a post")
    print("3. When ready for production, submit your app for App Review")
    print("\nImportant: Access tokens expire after 60 days. Set up a refresh mechanism.")
    print("See backend/docs/INSTAGRAM_GRAPH_API_SETUP.md for token refresh instructions.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Setup cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error: {str(e)}")
        sys.exit(1)
