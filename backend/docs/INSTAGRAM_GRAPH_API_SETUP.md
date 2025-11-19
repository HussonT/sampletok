# Instagram Graph API Setup Guide

Complete guide for setting up Facebook App and Instagram Graph API integration for auto-engagement features.

## Overview

This guide walks you through creating a Facebook App, adding Instagram Graph API product, linking your Instagram Business Account, and configuring webhooks for mention detection and automated commenting.

## Prerequisites

Before starting, ensure you have:

- **Instagram Business Account** (not personal account)
  - Convert at: Instagram Settings > Account > Switch to Professional Account > Business
- **Facebook Page** linked to your Instagram Business Account
  - Link at: Instagram Settings > Account > Linked Accounts > Facebook
- **Meta Business Verification** (optional but recommended for production)
  - Required for advanced permissions and higher rate limits
  - Apply at: Meta Business Suite > Settings > Business Info > Verification

## Step 1: Create Facebook App

### 1.1 Access Meta Developer Console

1. Go to [Meta for Developers](https://developers.facebook.com/)
2. Log in with your Facebook account (must have admin access to the Facebook Page)
3. Click **"My Apps"** in the top right
4. Click **"Create App"**

### 1.2 Choose App Type

1. Select **"Business"** app type
   - This type is designed for business integrations
   - Supports Instagram Graph API and webhooks
2. Click **"Next"**

### 1.3 Configure App Details

Fill in the app information:

- **App Display Name**: `SampleTok Instagram Integration` (or your preferred name)
- **App Contact Email**: Your business email
- **Business Account**: Select your Meta Business Account (or create one)
- **Purpose**: Select "Yourself or your own business"

Click **"Create App"**

### 1.4 Record App Credentials

After creation, you'll see your app dashboard:

1. Go to **Settings > Basic**
2. Record these credentials (you'll need them for environment variables):
   - **App ID**: e.g., `123456789012345`
   - **App Secret**: Click "Show" and copy (e.g., `abc123def456...`)

**SECURITY WARNING**: Keep App Secret confidential. Never commit to version control or expose in frontend code.

## Step 2: Add Instagram Graph API Product

### 2.1 Add Instagram Product

1. In your app dashboard, scroll to **"Add Products"**
2. Find **"Instagram Graph API"**
3. Click **"Set Up"**

### 2.2 Configure Instagram Settings

1. In left sidebar, go to **Instagram Graph API > Settings**
2. You should see the Instagram Graph API configuration page

## Step 3: Link Instagram Business Account

### 3.1 Add Instagram Tester Accounts (Development)

For development/testing:

1. Go to **Instagram Graph API > Settings**
2. Scroll to **"Instagram Testers"**
3. Click **"Add Instagram Testers"**
4. Search for your Instagram Business Account username: `@sampletheinternet`
5. Click **"Submit"**

### 3.2 Accept Tester Invitation

1. Log into Instagram with the `@sampletheinternet` account
2. Go to Settings > Apps and Websites > Tester Invites
3. Accept the invitation from your Facebook App

### 3.3 Generate Access Token

This is the most critical step - you need a long-lived access token:

#### Option A: Using Graph API Explorer (Recommended)

1. Go to [Graph API Explorer](https://developers.facebook.com/tools/explorer/)
2. Select your app from the dropdown
3. Click **"Generate Access Token"**
4. Select required permissions:
   - `instagram_basic`
   - `instagram_manage_comments`
   - `instagram_manage_messages`
   - `pages_read_engagement`
   - `pages_manage_metadata`
5. Click **"Generate Access Token"** and authorize
6. Copy the **short-lived token** (expires in 1 hour)

#### Option B: Using Meta Business Suite (Alternative)

1. Go to [Meta Business Suite](https://business.facebook.com/)
2. Navigate to Business Settings > Users > System Users
3. Create a system user or select existing
4. Assign assets (Instagram Business Account, Facebook Page)
5. Generate token with required permissions

### 3.4 Exchange for Long-Lived Token

Short-lived tokens expire in 1 hour. Exchange for a 60-day token:

```bash
curl -X GET "https://graph.facebook.com/v18.0/oauth/access_token" \
  -d "grant_type=fb_exchange_token" \
  -d "client_id=YOUR_APP_ID" \
  -d "client_secret=YOUR_APP_SECRET" \
  -d "fb_exchange_token=SHORT_LIVED_TOKEN"
```

Response:
```json
{
  "access_token": "LONG_LIVED_TOKEN",
  "token_type": "bearer",
  "expires_in": 5184000
}
```

**IMPORTANT**: Long-lived tokens expire after 60 days. Set a reminder to refresh them.

### 3.5 Get Instagram Business Account ID

```bash
curl -X GET "https://graph.facebook.com/v18.0/me/accounts" \
  -d "access_token=YOUR_LONG_LIVED_TOKEN"
```

Response includes your Facebook Pages. Find the page linked to your Instagram account:

```json
{
  "data": [
    {
      "id": "FACEBOOK_PAGE_ID",
      "name": "Your Page Name",
      "access_token": "PAGE_ACCESS_TOKEN"
    }
  ]
}
```

Now get the Instagram Business Account ID:

```bash
curl -X GET "https://graph.facebook.com/v18.0/FACEBOOK_PAGE_ID" \
  -d "fields=instagram_business_account" \
  -d "access_token=YOUR_LONG_LIVED_TOKEN"
```

Response:
```json
{
  "instagram_business_account": {
    "id": "17841400000000000"
  },
  "id": "FACEBOOK_PAGE_ID"
}
```

Record the `instagram_business_account.id` - this is your **Instagram Business Account ID**.

## Step 4: Configure App Permissions

### 4.1 Request Required Permissions

For auto-engagement features, you need these permissions:

| Permission | Purpose | Required For |
|------------|---------|--------------|
| `instagram_basic` | Access basic account info | Account info, media details |
| `instagram_manage_comments` | Post and manage comments | Auto-commenting on mentions |
| `instagram_manage_messages` | Manage direct messages | Future: DM responses |
| `pages_read_engagement` | Read page engagement | Mention notifications via webhooks |
| `pages_manage_metadata` | Manage page metadata | Webhook subscriptions |

### 4.2 Development vs Production Permissions

**Development Mode** (Automatic):
- Your app starts in Development Mode
- Permissions work for app admins, developers, and testers
- No App Review needed
- Limited to 25 testers

**Production Mode** (Requires App Review):
- For public launch and unlimited users
- Requires Meta App Review process
- Must demonstrate permission usage
- Can take 1-2 weeks for approval

**For MVP/Testing**: Development Mode is sufficient.

### 4.3 Add Permissions in App Dashboard

1. Go to **Instagram Graph API > Permissions**
2. Click **"Add Permissions"**
3. Search and add each required permission:
   - `instagram_basic`
   - `instagram_manage_comments`
   - `instagram_manage_messages`
   - `pages_read_engagement`
   - `pages_manage_metadata`

Note: Some permissions may require App Review before they're active in Production Mode.

## Step 5: Configure Webhooks

Webhooks allow Instagram to notify your backend when someone mentions `@sampletheinternet`.

### 5.1 Configure Webhook URL

1. Go to **Instagram Graph API > Configuration**
2. Under **"Webhooks"**, click **"Subscribe to this object"**
3. For **"Callback URL"**, enter your backend webhook endpoint:
   - Production: `https://your-backend.com/api/v1/webhooks/instagram`
   - Development (ngrok): `https://abc123.ngrok.io/api/v1/webhooks/instagram`

### 5.2 Set Verify Token

1. Generate a random verification token (or use existing):
   ```bash
   openssl rand -hex 32
   ```
   Example: `a3f8b2c9d4e5f6g7h8i9j0k1l2m3n4o5`

2. Enter this token in the **"Verify Token"** field in Meta dashboard
3. Save this token - you'll add it to your `.env` file as `INSTAGRAM_WEBHOOK_VERIFY_TOKEN`

### 5.3 Subscribe to Webhook Fields

1. After adding the callback URL, click **"Add Subscriptions"**
2. Select the fields you want to receive notifications for:
   - **mentions**: User tagged your account in a post (REQUIRED)
   - **comments**: Comments on your media (optional)
   - **messages**: Direct messages (optional, for future features)

3. Click **"Subscribe"**

### 5.4 Verify Webhook Connection

Meta will send a GET request to your webhook endpoint to verify it:

```
GET /api/v1/webhooks/instagram?hub.mode=subscribe&hub.challenge=123456&hub.verify_token=YOUR_TOKEN
```

Your backend must:
1. Validate `hub.verify_token` matches `INSTAGRAM_WEBHOOK_VERIFY_TOKEN`
2. Return `hub.challenge` as integer

Our implementation at `backend/app/api/v1/endpoints/webhooks.py` handles this automatically.

**Testing Webhook Verification**:

```bash
# Test locally with curl
curl "http://localhost:8000/api/v1/webhooks/instagram?hub.mode=subscribe&hub.challenge=123456&hub.verify_token=YOUR_TOKEN"

# Expected response: 123456 (as integer)
```

## Step 6: Configure Environment Variables

Add these credentials to your `.env` file:

```bash
# Instagram Graph API Settings
INSTAGRAM_APP_ID=123456789012345                              # From Step 1.4
INSTAGRAM_APP_SECRET=abc123def456...                         # From Step 1.4
INSTAGRAM_ACCESS_TOKEN=LONG_LIVED_TOKEN                      # From Step 3.4
INSTAGRAM_BUSINESS_ACCOUNT_ID=17841400000000000              # From Step 3.5
INSTAGRAM_WEBHOOK_VERIFY_TOKEN=a3f8b2c9d4e5f6g7h8i9j0k1...  # From Step 5.2
```

**Production Deployment**:

For Cloud Run or other production environments, add these to your secret manager:
- GCP: Use Secret Manager
- AWS: Use Systems Manager Parameter Store
- Heroku: Use Config Vars

**SECURITY BEST PRACTICES**:
- Never commit `.env` to version control
- Use separate credentials for development and production
- Rotate access tokens regularly (every 60 days)
- Use system users for production tokens (more stable)

## Step 7: Test Integration

### 7.1 Check Configuration

```bash
# Health check endpoint
curl http://localhost:8000/api/v1/webhooks/instagram/health
```

Expected response:
```json
{
  "status": "healthy",
  "instagram_configured": true,
  "has_access_token": true,
  "has_verify_token": true
}
```

### 7.2 Test Getting Account Info

```bash
# Using Python (backend environment)
cd backend
source venv/bin/activate
python -c "
from app.services.instagram.graph_api import InstagramGraphAPIClient
import asyncio

async def test():
    client = InstagramGraphAPIClient()
    info = await client.get_account_info()
    print(f'Account: @{info[\"username\"]}')
    print(f'Followers: {info[\"followers_count\"]}')

asyncio.run(test())
"
```

Expected output:
```
Account: @sampletheinternet
Followers: 12345
```

### 7.3 Test Webhook Reception

1. Make a test Instagram post mentioning `@sampletheinternet`
2. Check backend logs for webhook notification:
   ```
   INFO: Received Instagram webhook: {...}
   INFO: Created Instagram engagement record: ...
   ```

3. Verify database record:
   ```sql
   SELECT * FROM instagram_engagements ORDER BY created_at DESC LIMIT 1;
   ```

### 7.4 Test Comment Posting

```bash
# Using Python (backend environment)
python -c "
from app.services.instagram.graph_api import InstagramGraphAPIClient
import asyncio

async def test():
    client = InstagramGraphAPIClient()
    # Replace with actual media ID from test post
    result = await client.post_comment(
        media_id='123456789',
        message='Test comment from SampleTok!'
    )
    print(f'Comment posted: {result[\"id\"]}')

asyncio.run(test())
"
```

## Step 8: Production Readiness

### 8.1 App Review (When Ready)

To use permissions beyond test users:

1. Go to **App Review > Requests**
2. Click **"Add Items"**
3. Select each permission and provide:
   - **Detailed Description**: Explain why you need this permission
   - **Screenshot/Screencast**: Show the feature in action
   - **Step-by-Step Instructions**: How reviewers can test

4. Submit for review (typical turnaround: 1-2 weeks)

### 8.2 Business Verification

For higher rate limits and advanced features:

1. Go to [Meta Business Suite](https://business.facebook.com/)
2. Navigate to Business Settings > Security Center
3. Click **"Start Verification"**
4. Provide:
   - Business documents (registration, tax ID)
   - Business website
   - Business phone number
5. Submit and wait for approval (3-5 business days)

### 8.3 Rate Limits

**Development Mode**:
- 200 calls/hour per user
- 25 test users maximum

**Production Mode** (Verified Business):
- 200 calls/hour per user (default)
- 4,800 calls/hour per user (with business verification)
- No user limit

### 8.4 Token Refresh Strategy

Long-lived tokens expire after 60 days. Implement auto-refresh:

```python
# backend/scripts/refresh_instagram_token.py
import asyncio
from app.services.instagram.graph_api import InstagramGraphAPIClient

async def refresh_token():
    client = InstagramGraphAPIClient()
    result = await client.refresh_access_token()
    print(f"New token (expires in {result['expires_in']} seconds):")
    print(result['access_token'])

asyncio.run(refresh_token())
```

Run this monthly via cron job:
```bash
# Refresh Instagram token monthly (before 60-day expiry)
0 0 1 * * cd /app/backend && python scripts/refresh_instagram_token.py
```

## Troubleshooting

### Issue: "Invalid OAuth access token"

**Cause**: Token expired or invalid.

**Solution**:
1. Check token expiration:
   ```bash
   curl "https://graph.facebook.com/v18.0/debug_token?input_token=YOUR_TOKEN&access_token=YOUR_APP_ID|YOUR_APP_SECRET"
   ```
2. If expired, generate new token (Step 3.3-3.4)
3. Update `INSTAGRAM_ACCESS_TOKEN` in environment

### Issue: "Permissions error" when posting comment

**Cause**: Missing `instagram_manage_comments` permission or not granted for test account.

**Solution**:
1. Verify permission is added in App Dashboard
2. Regenerate access token with correct permissions
3. Ensure Instagram account is added as tester

### Issue: Webhook not receiving events

**Cause**: Webhook not properly configured or subscription inactive.

**Solution**:
1. Check webhook subscription in App Dashboard (should show "Active")
2. Verify `INSTAGRAM_WEBHOOK_VERIFY_TOKEN` matches Meta dashboard
3. Test webhook manually:
   ```bash
   curl "YOUR_BACKEND_URL/api/v1/webhooks/instagram?hub.mode=subscribe&hub.challenge=test&hub.verify_token=YOUR_TOKEN"
   ```
4. Check backend logs for errors

### Issue: "Comments are disabled on this post"

**Cause**: Creator disabled comments on their post.

**Solution**: This is expected behavior. Our error handling skips these posts gracefully. No action needed.

### Issue: App stuck in Development Mode

**Cause**: App not submitted for App Review or review pending.

**Solution**:
- Development Mode is fine for testing with up to 25 users
- Submit for App Review when ready for public launch
- Can take 1-2 weeks for approval

## Next Steps

After completing this setup:

1. **Test the full flow**: Have someone mention `@sampletheinternet` in a test post
2. **Verify webhook delivery**: Check backend logs and database records
3. **Implement next ticket**: TPERS-473 - Create Inngest job for processing Instagram mentions
4. **Monitor rate limits**: Track API usage in Meta Developer Console
5. **Set up token refresh**: Add monthly cron job to refresh access token

## Resources

- [Instagram Graph API Documentation](https://developers.facebook.com/docs/instagram-api)
- [Instagram Graph API Permissions](https://developers.facebook.com/docs/instagram-api/overview#permissions)
- [Webhooks Getting Started](https://developers.facebook.com/docs/graph-api/webhooks/getting-started)
- [Long-Lived Access Tokens](https://developers.facebook.com/docs/instagram-basic-display-api/guides/long-lived-access-tokens)
- [App Review Process](https://developers.facebook.com/docs/app-review)

## Security Checklist

- [ ] App Secret stored securely (not in version control)
- [ ] Access token stored securely (environment variables or secret manager)
- [ ] Webhook verify token is random and secure (32+ characters)
- [ ] HTTPS enabled for webhook endpoints
- [ ] Token refresh strategy implemented
- [ ] Rate limit monitoring in place
- [ ] Error handling for expired tokens
- [ ] Separate credentials for dev/staging/production

## Compliance Notes

- **Data Privacy**: Instagram Graph API access requires compliance with Meta's Platform Policies
- **User Data**: Only use data for the purpose the user consented to (e.g., processing their mention)
- **Data Retention**: Don't store user data longer than necessary
- **GDPR**: If operating in EU, ensure GDPR compliance for user data
- **Terms of Service**: Review Meta's Platform Terms regularly for policy updates
