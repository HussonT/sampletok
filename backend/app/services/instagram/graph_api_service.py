"""
Instagram Graph API Service for mention detection, commenting, and engagement.

This service handles all interactions with the Instagram Graph API including:
- Detecting mentions of @sampletheinternet
- Replying to comments and DMs
- Posting comments on user content
- Managing webhooks for real-time notifications
"""

import logging
from typing import Dict, Any, List, Optional
import httpx
from datetime import datetime

from app.core.config import settings

logger = logging.getLogger(__name__)


class InstagramGraphAPIException(Exception):
    """Base exception for Instagram Graph API errors"""
    pass


class InstagramGraphAPIAuthError(InstagramGraphAPIException):
    """Authentication/authorization errors"""
    pass


class InstagramGraphAPIRateLimitError(InstagramGraphAPIException):
    """Rate limit exceeded"""
    pass


class InstagramGraphAPIService:
    """Service for interacting with Instagram Graph API"""

    def __init__(self):
        """Initialize the Instagram Graph API service"""
        self.app_id = settings.META_APP_ID
        self.app_secret = settings.META_APP_SECRET
        self.access_token = settings.META_ACCESS_TOKEN
        self.business_account_id = settings.INSTAGRAM_BUSINESS_ACCOUNT_ID
        self.graph_api_version = "v21.0"
        self.base_url = f"https://graph.facebook.com/{self.graph_api_version}"

        # Validate required configuration
        if not all([self.app_id, self.app_secret, self.access_token, self.business_account_id]):
            logger.warning(
                "Instagram Graph API not fully configured. "
                "Set META_APP_ID, META_APP_SECRET, META_ACCESS_TOKEN, and INSTAGRAM_BUSINESS_ACCOUNT_ID"
            )

    def is_configured(self) -> bool:
        """Check if the service is properly configured"""
        return all([
            self.app_id,
            self.app_secret,
            self.access_token,
            self.business_account_id
        ])

    async def get_mentions(
        self,
        limit: int = 25,
        fields: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get recent mentions of the Instagram Business Account.

        Args:
            limit: Maximum number of mentions to retrieve (default 25, max 50)
            fields: List of fields to retrieve (default: basic mention info)

        Returns:
            List of mention objects with requested fields

        Raises:
            InstagramGraphAPIAuthError: If authentication fails
            InstagramGraphAPIRateLimitError: If rate limit exceeded
            InstagramGraphAPIException: For other API errors
        """
        if not self.is_configured():
            raise InstagramGraphAPIException("Instagram Graph API is not configured")

        # Default fields for mention data
        if fields is None:
            fields = [
                'id',
                'media_type',
                'media_url',
                'username',
                'text',
                'timestamp',
                'like_count',
                'comments_count'
            ]

        url = f"{self.base_url}/{self.business_account_id}/mentions"
        params = {
            'access_token': self.access_token,
            'fields': ','.join(fields),
            'limit': min(limit, 50)  # API max is 50
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()

                mentions = data.get('data', [])
                logger.info(f"Retrieved {len(mentions)} mentions from Instagram Graph API")
                return mentions

        except httpx.HTTPStatusError as e:
            await self._handle_api_error(e)
        except Exception as e:
            logger.error(f"Error fetching Instagram mentions: {str(e)}")
            raise InstagramGraphAPIException(f"Failed to fetch mentions: {str(e)}")

    async def get_comments(
        self,
        media_id: str,
        limit: int = 25,
        fields: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get comments on a specific media item.

        Args:
            media_id: Instagram media ID
            limit: Maximum number of comments to retrieve
            fields: List of fields to retrieve

        Returns:
            List of comment objects
        """
        if not self.is_configured():
            raise InstagramGraphAPIException("Instagram Graph API is not configured")

        if fields is None:
            fields = ['id', 'text', 'username', 'timestamp', 'like_count', 'replies']

        url = f"{self.base_url}/{media_id}/comments"
        params = {
            'access_token': self.access_token,
            'fields': ','.join(fields),
            'limit': min(limit, 50)
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()

                comments = data.get('data', [])
                logger.info(f"Retrieved {len(comments)} comments for media {media_id}")
                return comments

        except httpx.HTTPStatusError as e:
            await self._handle_api_error(e)
        except Exception as e:
            logger.error(f"Error fetching comments: {str(e)}")
            raise InstagramGraphAPIException(f"Failed to fetch comments: {str(e)}")

    async def reply_to_comment(
        self,
        comment_id: str,
        message: str
    ) -> Dict[str, Any]:
        """
        Reply to a comment on Instagram.

        Args:
            comment_id: ID of the comment to reply to
            message: Reply message text

        Returns:
            Response data from API including new comment ID

        Raises:
            InstagramGraphAPIException: If reply fails
        """
        if not self.is_configured():
            raise InstagramGraphAPIException("Instagram Graph API is not configured")

        url = f"{self.base_url}/{comment_id}/replies"
        data = {
            'access_token': self.access_token,
            'message': message
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, data=data)
                response.raise_for_status()
                result = response.json()

                logger.info(f"Successfully replied to comment {comment_id}")
                return result

        except httpx.HTTPStatusError as e:
            await self._handle_api_error(e)
        except Exception as e:
            logger.error(f"Error replying to comment: {str(e)}")
            raise InstagramGraphAPIException(f"Failed to reply to comment: {str(e)}")

    async def post_comment(
        self,
        media_id: str,
        message: str
    ) -> Dict[str, Any]:
        """
        Post a comment on a media item.

        Args:
            media_id: Instagram media ID
            message: Comment text

        Returns:
            Response data from API including comment ID
        """
        if not self.is_configured():
            raise InstagramGraphAPIException("Instagram Graph API is not configured")

        url = f"{self.base_url}/{media_id}/comments"
        data = {
            'access_token': self.access_token,
            'message': message
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, data=data)
                response.raise_for_status()
                result = response.json()

                logger.info(f"Successfully posted comment on media {media_id}")
                return result

        except httpx.HTTPStatusError as e:
            await self._handle_api_error(e)
        except Exception as e:
            logger.error(f"Error posting comment: {str(e)}")
            raise InstagramGraphAPIException(f"Failed to post comment: {str(e)}")

    async def get_media_details(
        self,
        media_id: str,
        fields: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Get details about a specific media item.

        Args:
            media_id: Instagram media ID
            fields: List of fields to retrieve

        Returns:
            Media object with requested fields
        """
        if not self.is_configured():
            raise InstagramGraphAPIException("Instagram Graph API is not configured")

        if fields is None:
            fields = [
                'id',
                'media_type',
                'media_url',
                'permalink',
                'caption',
                'timestamp',
                'username',
                'like_count',
                'comments_count'
            ]

        url = f"{self.base_url}/{media_id}"
        params = {
            'access_token': self.access_token,
            'fields': ','.join(fields)
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                media = response.json()

                logger.info(f"Retrieved media details for {media_id}")
                return media

        except httpx.HTTPStatusError as e:
            await self._handle_api_error(e)
        except Exception as e:
            logger.error(f"Error fetching media details: {str(e)}")
            raise InstagramGraphAPIException(f"Failed to fetch media details: {str(e)}")

    async def get_business_account_info(self) -> Dict[str, Any]:
        """
        Get information about the Instagram Business Account.

        Returns:
            Business account information
        """
        if not self.is_configured():
            raise InstagramGraphAPIException("Instagram Graph API is not configured")

        url = f"{self.base_url}/{self.business_account_id}"
        params = {
            'access_token': self.access_token,
            'fields': 'id,username,name,profile_picture_url,followers_count,follows_count,media_count'
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                account_info = response.json()

                logger.info(f"Retrieved business account info for @{account_info.get('username')}")
                return account_info

        except httpx.HTTPStatusError as e:
            await self._handle_api_error(e)
        except Exception as e:
            logger.error(f"Error fetching business account info: {str(e)}")
            raise InstagramGraphAPIException(f"Failed to fetch account info: {str(e)}")

    async def verify_webhook(self, verify_token: str, challenge: str) -> Optional[str]:
        """
        Verify webhook subscription request from Meta.

        Args:
            verify_token: Token from webhook GET request
            challenge: Challenge string to return

        Returns:
            Challenge string if verification succeeds, None otherwise
        """
        expected_token = settings.META_WEBHOOK_VERIFY_TOKEN

        if not expected_token:
            logger.error("META_WEBHOOK_VERIFY_TOKEN not configured")
            return None

        if verify_token == expected_token:
            logger.info("Webhook verification successful")
            return challenge
        else:
            logger.warning("Webhook verification failed: token mismatch")
            return None

    async def process_webhook_event(self, event_data: Dict[str, Any]) -> None:
        """
        Process incoming webhook event from Instagram.

        Args:
            event_data: Webhook event payload from Meta

        This method should be extended to handle different event types:
        - mentions: When users mention @sampletheinternet
        - comments: When users comment on posts
        - messages: When users send DMs
        """
        # Extract event details
        entry = event_data.get('entry', [])
        if not entry:
            logger.warning("Received webhook event with no entries")
            return

        for item in entry:
            changes = item.get('changes', [])
            for change in changes:
                field = change.get('field')
                value = change.get('value', {})

                logger.info(f"Processing webhook event: field={field}, value={value}")

                # Route to appropriate handler based on field type
                if field == 'mentions':
                    await self._handle_mention_event(value)
                elif field == 'comments':
                    await self._handle_comment_event(value)
                elif field == 'messages':
                    await self._handle_message_event(value)
                else:
                    logger.info(f"Unhandled webhook field type: {field}")

    @staticmethod
    def extract_shortcode_from_permalink(permalink: str) -> Optional[str]:
        """
        Extract Instagram shortcode from a permalink URL.

        Args:
            permalink: Instagram permalink URL (e.g., "https://www.instagram.com/p/ABC123xyz/")

        Returns:
            Shortcode if found, None otherwise

        Examples:
            - "https://www.instagram.com/p/ABC123xyz/" -> "ABC123xyz"
            - "https://www.instagram.com/reel/XYZ789abc/" -> "XYZ789abc"
        """
        import re

        # Match Instagram post/reel URLs and extract shortcode
        # Matches:
        # - https://www.instagram.com/p/SHORTCODE/
        # - https://www.instagram.com/reel/SHORTCODE/
        # - https://instagram.com/p/SHORTCODE/
        pattern = r'(?:https?://)?(?:www\.)?instagram\.com/(?:p|reel)/([A-Za-z0-9_-]+)/?'

        match = re.search(pattern, permalink)
        if match:
            shortcode = match.group(1)
            logger.info(f"Extracted shortcode '{shortcode}' from permalink")
            return shortcode

        logger.warning(f"Could not extract shortcode from permalink: {permalink}")
        return None

    async def _handle_mention_event(self, mention_data: Dict[str, Any]) -> None:
        """
        Handle a mention event from webhook.

        This triggers the Instagram video processing pipeline when
        users mention @sampletheinternet in their posts.
        """
        media_id = mention_data.get('media_id')
        comment_id = mention_data.get('comment_id')

        logger.info(f"Mention event received: media_id={media_id}, comment_id={comment_id}")

        # Import here to avoid circular imports
        from app.services.instagram.mention_processor import process_instagram_mention

        try:
            # Process the mention asynchronously (this will create sample, trigger Inngest, etc.)
            await process_instagram_mention(media_id)
            logger.info(f"Successfully queued mention processing for media_id={media_id}")
        except Exception as e:
            logger.error(f"Failed to process mention for media_id={media_id}: {str(e)}", exc_info=True)

    async def _handle_comment_event(self, comment_data: Dict[str, Any]) -> None:
        """
        Handle a comment event from webhook.

        Override this method to implement custom comment handling logic.
        """
        comment_id = comment_data.get('id')
        text = comment_data.get('text', '')

        logger.info(f"Comment event received: id={comment_id}, text={text}")

        # TODO: Implement comment handling logic

    async def _handle_message_event(self, message_data: Dict[str, Any]) -> None:
        """
        Handle a message event from webhook.

        Override this method to implement custom message handling logic.
        """
        message_id = message_data.get('id')
        text = message_data.get('text', '')

        logger.info(f"Message event received: id={message_id}, text={text}")

        # TODO: Implement message handling logic

    async def _handle_api_error(self, error: httpx.HTTPStatusError) -> None:
        """
        Handle HTTP errors from Instagram Graph API.

        Raises:
            InstagramGraphAPIAuthError: For 401/403 errors
            InstagramGraphAPIRateLimitError: For 429 errors
            InstagramGraphAPIException: For other errors
        """
        status_code = error.response.status_code
        error_data = {}

        try:
            error_data = error.response.json()
        except Exception:
            pass

        error_message = error_data.get('error', {}).get('message', str(error))

        if status_code in [401, 403]:
            logger.error(f"Instagram Graph API auth error: {error_message}")
            raise InstagramGraphAPIAuthError(f"Authentication failed: {error_message}")
        elif status_code == 429:
            logger.error(f"Instagram Graph API rate limit exceeded: {error_message}")
            raise InstagramGraphAPIRateLimitError(f"Rate limit exceeded: {error_message}")
        else:
            logger.error(f"Instagram Graph API error ({status_code}): {error_message}")
            raise InstagramGraphAPIException(f"API error: {error_message}")
