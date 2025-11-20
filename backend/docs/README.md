# Backend Documentation

This directory contains comprehensive documentation for the SampleTok backend services and integrations.

## Available Documentation

### Integration Guides

#### [Instagram Graph API Setup](INSTAGRAM_GRAPH_API_SETUP.md)

Complete guide for setting up Facebook App integration with Instagram Graph API. Covers:

- Creating a Facebook App in Meta Developer Console
- Adding Instagram Graph API product
- Linking the @sampletheinternet Business Account
- Requesting required permissions
- Obtaining App ID, Secret, and Access Tokens
- Configuring webhooks for real-time mention detection
- Testing and troubleshooting

**Status**: Phase 2 - Instagram Engagement Integration (TPERS-472)

Required for features:
- Real-time mention detection
- Automated comment responses
- Direct Message handling
- User engagement automation

## Quick Reference

### Instagram Graph API Environment Variables

```bash
# Meta/Facebook App Configuration
META_APP_ID=your_meta_app_id_here
META_APP_SECRET=your_meta_app_secret_here
META_ACCESS_TOKEN=your_long_lived_page_access_token_here

# Instagram Business Account
INSTAGRAM_BUSINESS_ACCOUNT_ID=your_instagram_business_account_id
INSTAGRAM_USERNAME=sampletheinternet

# Webhook Configuration
META_WEBHOOK_VERIFY_TOKEN=your_random_secure_webhook_token_here
```

### Useful Commands

```bash
# Test Instagram Graph API connection
curl -X GET "https://graph.facebook.com/v21.0/{IG_BUSINESS_ACCOUNT_ID}?fields=username,followers_count&access_token={ACCESS_TOKEN}"

# Get recent mentions
curl -X GET "https://graph.facebook.com/v21.0/{IG_BUSINESS_ACCOUNT_ID}/mentions?fields=id,username,text,timestamp&access_token={ACCESS_TOKEN}"

# Test webhook verification
curl -X GET "https://your-backend.com/api/v1/webhooks/instagram?hub.mode=subscribe&hub.verify_token={VERIFY_TOKEN}&hub.challenge=test_challenge"
```

## Related Services

### Instagram Services (`app/services/instagram/`)

- **downloader.py**: Instagram video downloading via RapidAPI
- **creator_service.py**: Creator profile caching and management
- **validator.py**: URL validation for Instagram posts
- **graph_api_service.py**: Instagram Graph API integration (mention detection, commenting)

### Service Initialization

```python
from app.services.instagram import (
    InstagramDownloader,
    InstagramGraphAPIService,
    CreatorService
)

# For video downloading
downloader = InstagramDownloader()
metadata = await downloader.download_video(shortcode="ABC123")

# For Graph API integration
graph_api = InstagramGraphAPIService()
mentions = await graph_api.get_mentions(limit=10)
await graph_api.reply_to_comment(comment_id="123", message="Thanks!")
```

## Contributing

When adding new integrations or features, please:

1. Create comprehensive setup documentation in this directory
2. Update `.env.example` with required environment variables
3. Add configuration to `app/core/config.py`
4. Update `CLAUDE.md` with integration details
5. Include testing instructions and troubleshooting guides

## Support

For questions or issues with integrations:

- Instagram Graph API: See [Meta Developer Support](https://developers.facebook.com/support/)
- Internal questions: Check `CLAUDE.md` and existing service implementations
