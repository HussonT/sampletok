#!/usr/bin/env python3
"""
Instagram Access Token Refresh Script

Instagram Graph API long-lived tokens expire after 60 days.
This script refreshes the token and displays the new credentials.

Usage:
    # Preview expiration info
    python scripts/refresh_instagram_token.py --check

    # Refresh token
    python scripts/refresh_instagram_token.py

    # Refresh and update .env file (be careful!)
    python scripts/refresh_instagram_token.py --update-env

Setup as cron job (run monthly, before 60-day expiry):
    0 0 1 * * cd /app/backend && python scripts/refresh_instagram_token.py --update-env >> /var/log/instagram-token-refresh.log 2>&1
"""

import asyncio
import sys
import os
import argparse
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.instagram.graph_api import InstagramGraphAPIClient, InstagramGraphAPIError
from app.core.config import settings


async def check_token_expiry():
    """
    Check when the current token will expire.
    Note: This is an estimate - tokens expire 60 days from generation.
    """
    print("=" * 80)
    print("Instagram Access Token Status")
    print("=" * 80)

    if not settings.INSTAGRAM_ACCESS_TOKEN:
        print("❌ ERROR: INSTAGRAM_ACCESS_TOKEN not configured")
        return False

    client = InstagramGraphAPIClient()

    try:
        # Test token by fetching account info
        info = await client.get_account_info()
        print(f"✅ Token is valid")
        print(f"   Account: @{info.get('username')}")
        print(f"   Account ID: {info.get('id')}")
        print(f"   Followers: {info.get('followers_count', 0):,}")
        print()
        print("⚠️  NOTE: Long-lived tokens expire after 60 days from generation.")
        print("   This script cannot determine exact expiry date.")
        print("   Recommendation: Refresh token monthly to ensure it never expires.")
        print()
        return True

    except InstagramGraphAPIError as e:
        print(f"❌ ERROR: Token validation failed")
        print(f"   {str(e)}")
        print()
        print("   Possible reasons:")
        print("   - Token has expired (60 days since generation)")
        print("   - Token was revoked")
        print("   - Invalid token format")
        print()
        return False


async def refresh_token():
    """
    Refresh the Instagram access token.
    Returns new token info or None if refresh failed.
    """
    print("=" * 80)
    print("Refreshing Instagram Access Token")
    print("=" * 80)

    if not settings.INSTAGRAM_ACCESS_TOKEN:
        print("❌ ERROR: INSTAGRAM_ACCESS_TOKEN not configured")
        return None

    if not settings.INSTAGRAM_APP_SECRET:
        print("❌ ERROR: INSTAGRAM_APP_SECRET not configured")
        return None

    client = InstagramGraphAPIClient()

    try:
        print("⏳ Requesting token refresh from Instagram Graph API...")
        result = await client.refresh_access_token()

        new_token = result.get('access_token')
        expires_in = result.get('expires_in')  # Seconds until expiry

        if not new_token:
            print("❌ ERROR: Refresh succeeded but no token returned")
            return None

        # Calculate expiry date
        expiry_date = datetime.now() + timedelta(seconds=expires_in)

        print()
        print("✅ Token refreshed successfully!")
        print()
        print(f"   Expires in: {expires_in:,} seconds (~{expires_in // 86400} days)")
        print(f"   Expiry date: {expiry_date.strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        print("=" * 80)
        print("New Access Token (update your environment variables):")
        print("=" * 80)
        print()
        print(f"INSTAGRAM_ACCESS_TOKEN={new_token}")
        print()
        print("=" * 80)
        print()

        return result

    except InstagramGraphAPIError as e:
        print(f"❌ ERROR: Token refresh failed")
        print(f"   {str(e)}")
        print()
        print("   Possible reasons:")
        print("   - Token has already expired (>60 days old)")
        print("   - Token was revoked or invalidated")
        print("   - App secret is incorrect")
        print()
        print("   Solution: Generate new long-lived token manually")
        print("   See: backend/docs/INSTAGRAM_GRAPH_API_SETUP.md (Step 3)")
        print()
        return None


def update_env_file(new_token: str):
    """
    Update the .env file with the new token.
    Creates backup before updating.
    """
    env_path = Path(__file__).parent.parent / ".env"

    if not env_path.exists():
        print(f"⚠️  WARNING: .env file not found at {env_path}")
        print("   Skipping .env update. Please update manually.")
        return False

    try:
        # Create backup
        backup_path = env_path.with_suffix(f".env.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        print(f"📝 Creating backup: {backup_path.name}")
        backup_path.write_text(env_path.read_text())

        # Read current .env
        env_content = env_path.read_text()

        # Replace token (handle various formats)
        if "INSTAGRAM_ACCESS_TOKEN=" in env_content:
            # Find the line and replace it
            lines = env_content.split('\n')
            for i, line in enumerate(lines):
                if line.startswith('INSTAGRAM_ACCESS_TOKEN='):
                    old_token = line.split('=', 1)[1] if '=' in line else ''
                    lines[i] = f'INSTAGRAM_ACCESS_TOKEN={new_token}'
                    print(f"✅ Updated INSTAGRAM_ACCESS_TOKEN in .env")
                    if old_token:
                        print(f"   Old token: {old_token[:20]}...{old_token[-10:]}")
                    print(f"   New token: {new_token[:20]}...{new_token[-10:]}")
                    break

            # Write updated content
            env_path.write_text('\n'.join(lines))
            print()
            print("✅ .env file updated successfully")
            print(f"   Backup saved: {backup_path.name}")
            print()
            return True
        else:
            print("⚠️  WARNING: INSTAGRAM_ACCESS_TOKEN not found in .env")
            print("   Please add it manually:")
            print(f"   INSTAGRAM_ACCESS_TOKEN={new_token}")
            return False

    except Exception as e:
        print(f"❌ ERROR: Failed to update .env file: {e}")
        print("   Please update manually.")
        return False


async def main():
    parser = argparse.ArgumentParser(
        description="Refresh Instagram Graph API access token",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Check current token status
  python scripts/refresh_instagram_token.py --check

  # Refresh token and display new credentials
  python scripts/refresh_instagram_token.py

  # Refresh token and update .env file
  python scripts/refresh_instagram_token.py --update-env

Setup as monthly cron job:
  0 0 1 * * cd /app/backend && python scripts/refresh_instagram_token.py --update-env
        """
    )

    parser.add_argument(
        '--check',
        action='store_true',
        help='Check current token validity without refreshing'
    )

    parser.add_argument(
        '--update-env',
        action='store_true',
        help='Update .env file with new token (creates backup)'
    )

    args = parser.parse_args()

    if args.check:
        # Just check token validity
        is_valid = await check_token_expiry()
        sys.exit(0 if is_valid else 1)
    else:
        # Refresh token
        result = await refresh_token()

        if not result:
            sys.exit(1)

        new_token = result.get('access_token')

        # Update .env if requested
        if args.update_env and new_token:
            print()
            update_env_file(new_token)

        print()
        print("⏰ REMINDER: Set up monthly cron job to auto-refresh token:")
        print("   0 0 1 * * cd /app/backend && python scripts/refresh_instagram_token.py --update-env")
        print()
        print("📚 For production (GCP/AWS), update secret manager instead of .env")
        print()

        sys.exit(0)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
