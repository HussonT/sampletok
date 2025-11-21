# Instagram Graph API Environment Variables Setup

## Required Credentials

You need to fill in these environment variables in `backend/.env`:

### 1. Facebook App Credentials

```bash
INSTAGRAM_APP_ID=your-facebook-app-id-here
INSTAGRAM_APP_SECRET=your-facebook-app-secret-here
```

**Where to find:**
- Go to https://developers.facebook.com/apps/
- Select your "SampleTok" app
- Navigate to: Settings > Basic
- Copy the "App ID" and "App Secret"

### 2. Instagram Access Token

```bash
INSTAGRAM_ACCESS_TOKEN=your-long-lived-instagram-access-token-here
```

**How to generate:**
1. Go to https://developers.facebook.com/tools/explorer/
2. Select your app from dropdown
3. Click "Generate Access Token"
4. Select permissions: instagram_business_basic, instagram_business_manage_comments, pages_read_engagement
5. Click "Get Token"
6. Exchange for long-lived token (60 days) - see documentation

### 3. Instagram Business Account ID

```bash
INSTAGRAM_BUSINESS_ACCOUNT_ID=your-instagram-business-account-id-here
```

**How to find:**
Using Graph API Explorer:
1. Make this API call: `GET /me/accounts`
2. Find your Facebook Page
3. Make this API call: `GET /{page-id}?fields=instagram_business_account`
4. Copy the `instagram_business_account.id` value

### 4. Webhook Verify Token

```bash
INSTAGRAM_WEBHOOK_VERIFY_TOKEN=your-random-webhook-verify-token-here
```

**How to set:**
- Generate any random string (e.g., use password generator)
- This is used to verify webhook requests from Meta
- Example: `MySecureWebhookToken12345`

### 5. Public App URL (Already set)

```bash
PUBLIC_APP_URL=https://app.sampletheinternet.com
```

This is used for:
- Generating shareable sample links
- Webhook callback URLs
- OAuth redirect URLs

## Testing the Setup

Once you've added all credentials to `.env`, run:

```bash
cd backend
python -c "from app.core.config import Settings; s = Settings(); print(f'App ID: {s.INSTAGRAM_APP_ID[:10]}...' if s.INSTAGRAM_APP_ID else 'Missing!')"
```

This will verify the environment variables are loaded correctly.

## Next Steps

After filling in the credentials:
1. Run API tests using Graph API Explorer
2. Configure webhook subscription in Meta Dashboard
3. Test the complete mention → comment workflow
