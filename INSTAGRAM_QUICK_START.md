# Instagram Graph API - Quick Start Guide

This is a condensed guide to get you started with the Instagram Graph API integration. For full details, see `backend/docs/INSTAGRAM_GRAPH_API_SETUP.md`.

## What Was Implemented (TPERS-472)

- Complete Instagram Graph API service for mention detection and commenting
- Environment configuration for Meta/Facebook App credentials
- Comprehensive documentation and setup guides
- Webhook infrastructure (ready for Phase 2)

## What You Need To Do

### 1. Create Facebook App (5-10 minutes)

1. Go to https://developers.facebook.com/
2. Click **"My Apps"** → **"Create App"**
3. Select **"Business"** app type
4. App Name: `SampleTok Instagram Integration`
5. Add your business email

### 2. Add Instagram Graph API (2 minutes)

1. In app dashboard, scroll to **"Add Products"**
2. Find **"Instagram Graph API"** → Click **"Set Up"**
3. Go to Instagram Graph API → Settings
4. Add/link the **@sampletheinternet** Business Account

### 3. Request Permissions (Requires App Review - 1-5 business days)

In **App Review → Permissions and Features**, request:

- ✅ `instagram_basic` - Basic account access
- ✅ `instagram_manage_comments` - Comment management
- ✅ `instagram_manage_messages` - DM handling
- ✅ `pages_read_engagement` - Page engagement data

**Note**: You'll need to explain your use case and provide video demonstrations.

### 4. Get Credentials

#### App ID & Secret (Immediate)

1. Go to **Settings → Basic**
2. Copy **App ID**
3. Click **Show** and copy **App Secret**

#### Access Token (After permissions approved)

1. Go to **Instagram Graph API → Tools → User Token Generator**
2. Select your Facebook Page
3. Click **Generate Token** and copy it
4. Exchange for long-lived token using this command:

```bash
curl -X GET "https://graph.facebook.com/v21.0/oauth/access_token?grant_type=fb_exchange_token&client_id={APP_ID}&client_secret={APP_SECRET}&fb_exchange_token={SHORT_LIVED_TOKEN}"
```

5. Get never-expiring page token:

```bash
curl -X GET "https://graph.facebook.com/v21.0/{PAGE_ID}?fields=access_token&access_token={LONG_LIVED_USER_TOKEN}"
```

#### Instagram Business Account ID

```bash
# First get your Page ID
curl -X GET "https://graph.facebook.com/v21.0/me/accounts?access_token={PAGE_TOKEN}"

# Then get Instagram Business Account ID
curl -X GET "https://graph.facebook.com/v21.0/{PAGE_ID}?fields=instagram_business_account&access_token={PAGE_TOKEN}"
```

### 5. Configure Backend (.env file)

Add these to your `backend/.env` file:

```bash
# Meta/Facebook App Configuration
META_APP_ID=your_app_id_here
META_APP_SECRET=your_app_secret_here
META_ACCESS_TOKEN=your_long_lived_page_access_token_here

# Instagram Business Account
INSTAGRAM_BUSINESS_ACCOUNT_ID=17841400008460056  # Replace with your actual ID
INSTAGRAM_USERNAME=sampletheinternet

# Webhook Configuration (generate a random secure token)
META_WEBHOOK_VERIFY_TOKEN=your_random_secure_token_here
```

### 6. Test the Integration

```bash
# Test basic API access
curl -X GET "https://graph.facebook.com/v21.0/{IG_BUSINESS_ACCOUNT_ID}?fields=username,followers_count&access_token={ACCESS_TOKEN}"

# Get recent mentions (once permissions are approved)
curl -X GET "https://graph.facebook.com/v21.0/{IG_BUSINESS_ACCOUNT_ID}/mentions?fields=id,username,text,timestamp&access_token={ACCESS_TOKEN}"
```

Expected response:
```json
{
  "username": "sampletheinternet",
  "followers_count": 12345,
  "id": "17841400008460056"
}
```

## Using the Service in Code

```python
from app.services.instagram import InstagramGraphAPIService

# Initialize service
graph_api = InstagramGraphAPIService()

# Check if configured
if not graph_api.is_configured():
    print("Instagram Graph API not configured")
    return

# Get recent mentions
mentions = await graph_api.get_mentions(limit=10)
for mention in mentions:
    print(f"Mentioned by @{mention['username']}: {mention.get('text', 'N/A')}")

# Reply to a comment
await graph_api.reply_to_comment(
    comment_id="123456",
    message="Thanks for mentioning us! Here's your sample: https://..."
)

# Get business account info
account = await graph_api.get_business_account_info()
print(f"Account: @{account['username']}, Followers: {account['followers_count']}")
```

## Common Issues

### "Invalid OAuth Access Token"
- Token expired → Regenerate long-lived token
- Wrong token → Ensure using PAGE access token, not USER token

### "Permissions Error"
- Permissions not approved yet → Wait for App Review approval
- Wrong permissions scope → Regenerate token with all approved permissions

### "Instagram Account Not Found"
- Not a Business Account → Convert to Business in Instagram settings
- Not linked to Facebook Page → Link in Instagram settings

## What's Next (Phase 2 Tickets)

Now that the foundation is in place:

1. **TPERS-473**: Implement webhook endpoint to receive real-time mention notifications
2. **TPERS-474**: Auto-process videos when @sampletheinternet is mentioned
3. **TPERS-475**: Auto-reply to mentions with sample download links
4. **TPERS-476**: Add monitoring and error handling

## Need Help?

- **Full setup guide**: `backend/docs/INSTAGRAM_GRAPH_API_SETUP.md`
- **Meta Developer Support**: https://developers.facebook.com/support/
- **Graph API Explorer**: https://developers.facebook.com/tools/explorer/
- **API Documentation**: https://developers.facebook.com/docs/instagram-api/

## Security Reminders

- ⚠️ Never commit `.env` file to git
- ⚠️ Use environment variables or secrets manager in production
- ⚠️ Rotate access tokens regularly
- ⚠️ Validate webhook signatures (prevents spoofing)
- ⚠️ Use HTTPS for all webhook endpoints in production
