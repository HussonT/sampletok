"""
Instagram Graph API Client - For auto-engagement features
Handles mentions detection, media retrieval, and comment posting.
"""
import logging
import httpx
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from app.core.config import settings

logger = logging.getLogger(__name__)


class InstagramGraphAPIError(Exception):
    """Base exception for Instagram Graph API errors"""
    pass


class InstagramGraphAPIClient:
    """
    Instagram Graph API client for auto-engagement features.

    Features:
    - Get media details from Graph API
    - Post comments on media
    - Get mentions/tags
    - Verify webhook callbacks

    Docs: https://developers.facebook.com/docs/instagram-api
    """

    def __init__(self):
        """Initialize Instagram Graph API client"""
        self.access_token = settings.INSTAGRAM_ACCESS_TOKEN
        self.business_account_id = settings.INSTAGRAM_BUSINESS_ACCOUNT_ID
        self.app_secret = settings.INSTAGRAM_APP_SECRET
        self.verify_token = settings.INSTAGRAM_WEBHOOK_VERIFY_TOKEN

        # Validate required credentials
        if not self.access_token:
            logger.warning("INSTAGRAM_ACCESS_TOKEN not configured - auto-engagement disabled")

        self.base_url = "https://graph.facebook.com/v18.0"
        self.timeout = 30.0

    def is_configured(self) -> bool:
        """Check if Instagram Graph API is properly configured"""
        return bool(
            self.access_token
            and self.business_account_id
            and self.app_secret
            and self.verify_token
        )

    async def get_media_info(self, media_id: str) -> Dict[str, Any]:
        """
        Get media information from Instagram Graph API.

        Args:
            media_id: Instagram media ID (from webhook or API)

        Returns:
            Media information including caption, media_type, permalink, etc.

        Docs: https://developers.facebook.com/docs/instagram-api/reference/ig-media
        """
        if not self.access_token:
            raise InstagramGraphAPIError("Instagram access token not configured")

        url = f"{self.base_url}/{media_id}"
        params = {
            "fields": "id,media_type,media_url,permalink,caption,timestamp,username,like_count,comments_count,is_comment_enabled",
            "access_token": self.access_token
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(url, params=params)
                response.raise_for_status()

                data = response.json()
                logger.info(f"Retrieved media info for {media_id}")
                return data

            except httpx.HTTPStatusError as e:
                error_data = e.response.json() if e.response.text else {}
                error_msg = error_data.get('error', {}).get('message', str(e))
                logger.error(f"Failed to get media info: {error_msg}")
                raise InstagramGraphAPIError(f"Failed to get media info: {error_msg}")
            except Exception as e:
                logger.error(f"Unexpected error getting media info: {e}")
                raise InstagramGraphAPIError(f"Unexpected error: {e}")

    async def post_comment(self, media_id: str, message: str) -> Dict[str, Any]:
        """
        Post a comment on an Instagram media.

        Args:
            media_id: Instagram media ID
            message: Comment text (max 2200 characters)

        Returns:
            Comment data including comment ID

        Docs: https://developers.facebook.com/docs/instagram-api/reference/ig-media/comments
        """
        if not self.access_token:
            raise InstagramGraphAPIError("Instagram access token not configured")

        # Validate message length (Instagram limit is 2200 characters)
        if len(message) > 2200:
            logger.warning(f"Comment too long ({len(message)} chars), truncating to 2200")
            message = message[:2197] + "..."

        url = f"{self.base_url}/{media_id}/comments"
        data = {
            "message": message,
            "access_token": self.access_token
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(url, data=data)
                response.raise_for_status()

                result = response.json()
                logger.info(f"Posted comment on media {media_id}: {result.get('id')}")
                return result

            except httpx.HTTPStatusError as e:
                error_data = e.response.json() if e.response.text else {}
                error_msg = error_data.get('error', {}).get('message', str(e))
                error_code = error_data.get('error', {}).get('code')

                # Handle common errors
                if error_code == 190:  # Invalid token
                    logger.error("Instagram access token is invalid or expired")
                    raise InstagramGraphAPIError("Access token invalid or expired")
                elif error_code == 100:  # Invalid parameter
                    logger.error(f"Invalid parameter: {error_msg}")
                    raise InstagramGraphAPIError(f"Invalid parameter: {error_msg}")
                elif "comments are disabled" in error_msg.lower():
                    logger.warning(f"Comments disabled on media {media_id}")
                    raise InstagramGraphAPIError("Comments are disabled on this post")
                else:
                    logger.error(f"Failed to post comment: {error_msg}")
                    raise InstagramGraphAPIError(f"Failed to post comment: {error_msg}")

            except Exception as e:
                logger.error(f"Unexpected error posting comment: {e}")
                raise InstagramGraphAPIError(f"Unexpected error: {e}")

    async def get_mentions(
        self,
        limit: int = 25,
        after: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get recent mentions of the business account.

        Args:
            limit: Number of mentions to retrieve (max 25)
            after: Pagination cursor

        Returns:
            List of mentions with pagination info

        Docs: https://developers.facebook.com/docs/instagram-api/reference/ig-user/tags
        """
        if not self.access_token or not self.business_account_id:
            raise InstagramGraphAPIError("Instagram credentials not configured")

        url = f"{self.base_url}/{self.business_account_id}/tags"
        params = {
            "fields": "id,media_type,media_url,permalink,caption,timestamp,username",
            "limit": min(limit, 25),  # Instagram API max is 25
            "access_token": self.access_token
        }

        if after:
            params["after"] = after

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(url, params=params)
                response.raise_for_status()

                data = response.json()
                logger.info(f"Retrieved {len(data.get('data', []))} mentions")
                return data

            except httpx.HTTPStatusError as e:
                error_data = e.response.json() if e.response.text else {}
                error_msg = error_data.get('error', {}).get('message', str(e))
                logger.error(f"Failed to get mentions: {error_msg}")
                raise InstagramGraphAPIError(f"Failed to get mentions: {error_msg}")
            except Exception as e:
                logger.error(f"Unexpected error getting mentions: {e}")
                raise InstagramGraphAPIError(f"Unexpected error: {e}")

    async def get_media_children(self, media_id: str) -> List[Dict[str, Any]]:
        """
        Get children media for carousel posts.

        Args:
            media_id: Parent media ID

        Returns:
            List of child media items

        Docs: https://developers.facebook.com/docs/instagram-api/reference/ig-media/children
        """
        if not self.access_token:
            raise InstagramGraphAPIError("Instagram access token not configured")

        url = f"{self.base_url}/{media_id}/children"
        params = {
            "fields": "id,media_type,media_url,permalink,timestamp",
            "access_token": self.access_token
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(url, params=params)
                response.raise_for_status()

                data = response.json()
                return data.get('data', [])

            except httpx.HTTPStatusError as e:
                error_data = e.response.json() if e.response.text else {}
                error_msg = error_data.get('error', {}).get('message', str(e))
                logger.error(f"Failed to get media children: {error_msg}")
                raise InstagramGraphAPIError(f"Failed to get media children: {error_msg}")
            except Exception as e:
                logger.error(f"Unexpected error getting media children: {e}")
                raise InstagramGraphAPIError(f"Unexpected error: {e}")

    def verify_webhook(self, mode: str, token: str, challenge: str) -> Optional[str]:
        """
        Verify webhook subscription challenge from Instagram.

        Args:
            mode: Should be "subscribe"
            token: Verify token from webhook request
            challenge: Challenge string to echo back

        Returns:
            Challenge string if verification succeeds, None otherwise

        Docs: https://developers.facebook.com/docs/graph-api/webhooks/getting-started
        """
        if not self.verify_token:
            logger.error("INSTAGRAM_WEBHOOK_VERIFY_TOKEN not configured")
            return None

        if mode == "subscribe" and token == self.verify_token:
            logger.info("Webhook verification successful")
            return challenge
        else:
            logger.warning(f"Webhook verification failed: mode={mode}, token_match={token == self.verify_token}")
            return None

    async def refresh_access_token(self) -> Dict[str, Any]:
        """
        Refresh a long-lived access token.
        Long-lived tokens expire after 60 days.

        Returns:
            New access token info with expiration

        Docs: https://developers.facebook.com/docs/instagram-basic-display-api/guides/long-lived-access-tokens
        """
        if not self.access_token or not settings.INSTAGRAM_APP_SECRET:
            raise InstagramGraphAPIError("Instagram credentials not configured")

        url = f"{self.base_url}/oauth/access_token"
        params = {
            "grant_type": "ig_refresh_token",
            "access_token": self.access_token
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(url, params=params)
                response.raise_for_status()

                data = response.json()
                logger.info(f"Access token refreshed, expires in {data.get('expires_in')} seconds")
                return data

            except httpx.HTTPStatusError as e:
                error_data = e.response.json() if e.response.text else {}
                error_msg = error_data.get('error', {}).get('message', str(e))
                logger.error(f"Failed to refresh access token: {error_msg}")
                raise InstagramGraphAPIError(f"Failed to refresh token: {error_msg}")
            except Exception as e:
                logger.error(f"Unexpected error refreshing token: {e}")
                raise InstagramGraphAPIError(f"Unexpected error: {e}")

    async def get_account_info(self) -> Dict[str, Any]:
        """
        Get Instagram Business Account information.

        Returns:
            Account info including username, profile picture, followers count

        Docs: https://developers.facebook.com/docs/instagram-api/reference/ig-user
        """
        if not self.access_token or not self.business_account_id:
            raise InstagramGraphAPIError("Instagram credentials not configured")

        url = f"{self.base_url}/{self.business_account_id}"
        params = {
            "fields": "id,username,name,biography,profile_picture_url,followers_count,follows_count,media_count",
            "access_token": self.access_token
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(url, params=params)
                response.raise_for_status()

                data = response.json()
                logger.info(f"Retrieved account info for @{data.get('username')}")
                return data

            except httpx.HTTPStatusError as e:
                error_data = e.response.json() if e.response.text else {}
                error_msg = error_data.get('error', {}).get('message', str(e))
                logger.error(f"Failed to get account info: {error_msg}")
                raise InstagramGraphAPIError(f"Failed to get account info: {error_msg}")
            except Exception as e:
                logger.error(f"Unexpected error getting account info: {e}")
                raise InstagramGraphAPIError(f"Unexpected error: {e}")
