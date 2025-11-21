# Instagram Graph API Setup - Quick Reference

**Time to Complete**: ~30-45 minutes

This is a condensed checklist for setting up Instagram Graph API integration. For detailed explanations, see `INSTAGRAM_GRAPH_API_SETUP.md`.

## Prerequisites Checklist

- [ ] Instagram Business Account (not personal)
- [ ] Facebook Page linked to Instagram account
- [ ] Facebook account with admin access to the Page
- [ ] Backend deployed and publicly accessible (for webhooks)

## Step-by-Step Setup

### 1. Create Facebook App (10 min)

1. Go to https://developers.facebook.com/
2. Click "My Apps" → "Create App"
3. Select "Business" app type
4. Fill in:
   - App Name: `SampleTok Instagram Integration`
   - Contact Email: Your email
   - Business Account: Select or create
5. Click "Create App"
6. **Record credentials** from Settings → Basic:
   - App ID: `____________`
   - App Secret: `____________` (click "Show")

### 2. Add Instagram Product (5 min)

1. In app dashboard, scroll to "Add Products"
2. Find "Instagram Graph API" → Click "Set Up"
3. Go to Instagram Graph API → Settings
4. Add Instagram Tester:
   - Click "Add Instagram Testers"
   - Search `@sampletheinternet`
   - Click "Submit"
5. Accept invitation on Instagram:
   - Settings → Apps and Websites → Tester Invites → Accept

### 3. Generate Access Token (10 min)

1. Go to https://developers.facebook.com/tools/explorer/
2. Select your app from dropdown
3. Click "Generate Access Token"
4. Select permissions:
   - [x] `instagram_basic`
   - [x] `instagram_manage_comments`
   - [x] `instagram_manage_messages`
   - [x] `pages_read_engagement`
   - [x] `pages_manage_metadata`
5. Authorize and copy short-lived token

6. **Exchange for long-lived token**:
```bash
curl -X GET "https://graph.facebook.com/v18.0/oauth/access_token" \
  -d "grant_type=fb_exchange_token" \
  -d "client_id=YOUR_APP_ID" \
  -d "client_secret=YOUR_APP_SECRET" \
  -d "fb_exchange_token=SHORT_LIVED_TOKEN"
```

7. **Record**: `access_token` from response: `____________`

### 4. Get Instagram Business Account ID (5 min)

```bash
# Get Facebook Page ID
curl -X GET "https://graph.facebook.com/v18.0/me/accounts" \
  -d "access_token=YOUR_LONG_LIVED_TOKEN"

# Get Instagram Business Account ID (replace PAGE_ID)
curl -X GET "https://graph.facebook.com/v18.0/PAGE_ID" \
  -d "fields=instagram_business_account" \
  -d "access_token=YOUR_LONG_LIVED_TOKEN"
```

**Record**: `instagram_business_account.id`: `____________`

### 5. Configure Webhooks (10 min)

1. Generate verify token:
```bash
openssl rand -hex 32
```
**Record**: `____________`

2. In app dashboard, go to Instagram Graph API → Configuration
3. Under "Webhooks":
   - Callback URL: `https://your-backend.com/api/v1/webhooks/instagram`
   - Verify Token: Paste generated token
   - Click "Verify and Save"

4. Click "Add Subscriptions":
   - [x] mentions
   - [x] comments (optional)
   - Click "Subscribe"

### 6. Update Environment Variables

Add to `.env` or production secrets:

```bash
INSTAGRAM_APP_ID=____________
INSTAGRAM_APP_SECRET=____________
INSTAGRAM_ACCESS_TOKEN=____________
INSTAGRAM_BUSINESS_ACCOUNT_ID=____________
INSTAGRAM_WEBHOOK_VERIFY_TOKEN=____________
```

For GCP Cloud Run:
```bash
gcloud secrets create instagram-app-id --data-file=- <<< "YOUR_APP_ID"
gcloud secrets create instagram-app-secret --data-file=- <<< "YOUR_APP_SECRET"
gcloud secrets create instagram-access-token --data-file=- <<< "YOUR_TOKEN"
gcloud secrets create instagram-business-account-id --data-file=- <<< "YOUR_ACCOUNT_ID"
gcloud secrets create instagram-webhook-verify-token --data-file=- <<< "YOUR_VERIFY_TOKEN"
```

### 7. Verify Setup (5 min)

```bash
# 1. Health check
curl https://your-backend.com/api/v1/webhooks/instagram/health

# Expected: {"status":"healthy","instagram_configured":true,...}

# 2. Test webhook verification
curl "https://your-backend.com/api/v1/webhooks/instagram?hub.mode=subscribe&hub.challenge=12345&hub.verify_token=YOUR_VERIFY_TOKEN"

# Expected: 12345

# 3. Test account info (Python)
cd backend
source venv/bin/activate
python -c "
from app.services.instagram.graph_api import InstagramGraphAPIClient
import asyncio
async def test():
    client = InstagramGraphAPIClient()
    info = await client.get_account_info()
    print(f'Account: @{info[\"username\"]} | Followers: {info[\"followers_count\"]}')
asyncio.run(test())
"

# 4. Test live mention (final verification)
# - Post Instagram content and tag @sampletheinternet
# - Check backend logs for webhook delivery
# - Verify database record created
```

## Success Criteria Checklist

- [ ] Facebook App created with correct credentials
- [ ] Instagram Graph API product added
- [ ] `@sampletheinternet` added as tester and invitation accepted
- [ ] Long-lived access token generated (60-day expiry)
- [ ] Instagram Business Account ID retrieved
- [ ] Webhook configured and verified
- [ ] All 5 environment variables set
- [ ] Health check returns `"instagram_configured": true`
- [ ] Account info retrieved successfully
- [ ] Test mention delivered via webhook

## Common Issues

**"instagram_configured": false**
→ Check all 5 environment variables are set and valid

**"Invalid OAuth access token"**
→ Regenerate long-lived token (Step 3)

**Webhook verification failed (403)**
→ Ensure `INSTAGRAM_WEBHOOK_VERIFY_TOKEN` matches Meta dashboard

**No webhook delivery**
→ Check webhook subscription is "Active" in Meta dashboard

**"Comments are disabled on this post"**
→ Expected - our code handles this gracefully

## Next Steps

1. **Monitor token expiry**: Set reminder to refresh token before 60-day expiry
2. **Set up cron job** for auto token refresh:
   ```bash
   # Monthly refresh
   0 0 1 * * cd /app/backend && python scripts/refresh_instagram_token.py
   ```
3. **Implement processing job** (TPERS-473): Create Inngest function to process mentions
4. **Test end-to-end**: Tag `@sampletheinternet` → Video processed → Comment posted
5. **Production readiness**: Submit for App Review when ready for public launch

## Production Deployment Notes

**GCP Cloud Run**:
- Use Secret Manager for all credentials
- Set secrets as environment variables in Cloud Run config
- Ensure webhook URL uses HTTPS (Cloud Run provides this)
- Set token refresh cron job via Cloud Scheduler

**Rate Limiting**:
- Development Mode: 200 calls/hour, 25 test users
- Production Mode: 4,800 calls/hour (after business verification)

**Token Management**:
- Long-lived tokens expire after 60 days
- Set up monthly refresh cron job
- Store refresh logs for debugging

## Support Resources

- Full setup guide: `INSTAGRAM_GRAPH_API_SETUP.md`
- API docs: https://developers.facebook.com/docs/instagram-api
- Webhook guide: https://developers.facebook.com/docs/graph-api/webhooks
- Token debugging: https://developers.facebook.com/tools/debug/accesstoken/
