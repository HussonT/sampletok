import os
import tempfile
import asyncio
from typing import Dict, Any, Optional
from pathlib import Path
import logging
import httpx
from urllib.parse import quote, unquote, urlparse
from datetime import datetime
import re

from app.core.config import settings

logger = logging.getLogger(__name__)


class InstagramDownloader:
    """Downloads Instagram videos using RapidAPI"""

    def __init__(self):
        self.api_key = settings.RAPIDAPI_INSTAGRAM_KEY
        self.api_host = settings.RAPIDAPI_INSTAGRAM_HOST
        self.headers = {
            'x-rapidapi-key': self.api_key,
            'x-rapidapi-host': self.api_host
        }

    async def download_video(self, shortcode: str, output_dir: Optional[str] = None) -> Dict[str, Any]:
        """
        Download an Instagram video and extract metadata using RapidAPI
        Args:
            shortcode: Instagram post shortcode (e.g., "DQxmWDwAfUf")
            output_dir: Optional directory to save the video
        Returns: dict with video_path and comprehensive metadata
        """
        if not output_dir:
            output_dir = tempfile.mkdtemp(prefix='instagram_')

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        try:
            # Step 1: Get video metadata from RapidAPI
            logger.info(f"Fetching metadata for Instagram shortcode: {shortcode}")
            video_data = await self._fetch_video_data(shortcode)

            if not video_data:
                raise ValueError("Failed to fetch video data from API")

            # Step 2: Extract video URL (use first video version - usually highest quality)
            video_versions = video_data.get('video_versions', [])
            if not video_versions:
                raise ValueError("No video versions found in API response")

            video_url = video_versions[0]['url']

            # Extract video ID for filename
            post_id = video_data.get('id', shortcode)
            video_filename = f"{shortcode}.mp4"
            video_path = output_path / video_filename

            logger.info(f"Downloading video to: {video_path}")
            await self._download_file(video_url, str(video_path))

            if not video_path.exists():
                raise FileNotFoundError(f"Downloaded video not found: {video_path}")

            # Step 3: Extract and format metadata
            metadata = self._format_metadata(video_data, str(video_path))

            logger.info(f"Successfully downloaded Instagram video: {shortcode}")
            return metadata

        except Exception as e:
            logger.error(f"Error downloading Instagram video: {str(e)}")
            raise

    async def _fetch_video_data(self, shortcode: str) -> Dict[str, Any]:
        """Fetch video metadata from RapidAPI"""
        api_url = f"https://{self.api_host}/post?shortcode={shortcode}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(api_url, headers=self.headers)
                response.raise_for_status()

                data = response.json()

                # The API returns the post data directly
                return data

            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error fetching video data: {e.response.status_code}")
                if e.response.status_code == 404:
                    raise ValueError("Instagram post not found")
                raise ValueError(f"Failed to fetch video data: HTTP {e.response.status_code}")
            except Exception as e:
                logger.error(f"Error fetching video data: {str(e)}")
                raise

    async def _download_file(self, url: str, output_path: str) -> None:
        """Download a file from URL to the specified path"""
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            try:
                response = await client.get(url)
                response.raise_for_status()

                # Write the content to file
                with open(output_path, 'wb') as f:
                    f.write(response.content)

            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error downloading file: {e.response.status_code}")
                raise ValueError(f"Failed to download file: HTTP {e.response.status_code}")
            except Exception as e:
                logger.error(f"Error downloading file: {str(e)}")
                raise

    def _format_metadata(self, api_data: Dict[str, Any], video_path: str) -> Dict[str, Any]:
        """Format API response into our metadata structure"""
        user = api_data.get('user', {})
        caption = api_data.get('caption', {})
        clips_metadata = api_data.get('clips_metadata', {})
        music_info = clips_metadata.get('music_info', {}) if clips_metadata else {}
        music_asset = music_info.get('music_asset_info', {}) if music_info else {}

        # Get image/thumbnail URLs
        image_versions = api_data.get('image_versions2', {})
        candidates = image_versions.get('candidates', [])
        thumbnail_url = candidates[0]['url'] if candidates else ''

        # Get file size
        file_size = 0
        if os.path.exists(video_path):
            file_size = os.path.getsize(video_path)

        # Extract video URL from first video version
        video_versions = api_data.get('video_versions', [])
        video_url = video_versions[0]['url'] if video_versions else ''

        # Get caption text
        caption_text = caption.get('text', '') if caption else ''

        # Instagram doesn't have titles like TikTok - use caption as title
        # If caption is too long, use first line or truncate
        title = api_data.get('title', '')
        if not title and caption_text:
            # Use first line of caption as title (up to 100 chars)
            first_line = caption_text.split('\n')[0].strip()
            title = first_line[:100] if len(first_line) > 100 else first_line
        if not title:
            # Fallback to generic title with creator name
            username = user.get('username', 'Unknown')
            title = f"Instagram Reel by @{username}"

        metadata = {
            # Primary identifiers
            'instagram_id': api_data.get('id', ''),
            'instagram_pk': str(api_data.get('pk', '')),
            'instagram_shortcode': api_data.get('code', ''),

            # Video information
            'title': title,
            'caption': caption_text,
            'description': caption_text,
            'product_type': api_data.get('product_type', ''),  # 'clips', 'igtv', etc.
            'media_type': api_data.get('media_type', 0),  # 1=image, 2=video, 8=carousel

            # Creator information
            'creator_username': user.get('username', ''),
            'creator_full_name': user.get('full_name', ''),
            'creator_instagram_id': str(user.get('pk', '')),
            'creator_profile_pic_url': user.get('profile_pic_url', ''),
            'creator_is_verified': user.get('is_verified', False),
            'creator_is_private': user.get('is_private', False),

            # Engagement metrics
            'like_count': api_data.get('like_count', 0),
            'comment_count': api_data.get('comment_count', 0),
            'view_count': api_data.get('play_count', 0) or api_data.get('view_count', 0),  # Instagram uses play_count for Reels
            'share_count': api_data.get('reshare_count', 0),

            # Media URLs
            'thumbnail_url': thumbnail_url,
            'video_url': video_url,

            # Video details
            'duration': api_data.get('video_duration', 0),
            'has_audio': api_data.get('has_audio', False),
            'original_width': api_data.get('original_width', 0),
            'original_height': api_data.get('original_height', 0),

            # Music information (if available)
            'music_title': music_asset.get('title', ''),
            'music_artist': music_asset.get('display_artist', ''),

            # Timestamps
            'taken_at': api_data.get('taken_at', 0),
            'taken_at_datetime': datetime.fromtimestamp(
                api_data.get('taken_at', 0)
            ).isoformat() if api_data.get('taken_at') else None,

            # File information
            'video_path': video_path,
            'file_size': file_size,
        }

        return metadata

    async def get_user_profile(self, username: str) -> Dict[str, Any]:
        """
        Fetch Instagram user profile data from RapidAPI
        Returns profile info including follower count, following count, etc.
        """
        api_url = f"https://{self.api_host}/profile?username={username}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(api_url, headers=self.headers)
                response.raise_for_status()

                data = response.json()
                logger.info(f"Successfully fetched Instagram profile for @{username}")
                return data

            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error fetching Instagram profile: {e.response.status_code}")
                if e.response.status_code == 404:
                    raise ValueError("Instagram user not found")
                raise ValueError(f"Failed to fetch profile data: HTTP {e.response.status_code}")
            except Exception as e:
                logger.error(f"Error fetching Instagram profile: {str(e)}")
                raise

    async def get_post_info(self, shortcode: str) -> Dict[str, Any]:
        """Get post metadata without downloading"""
        try:
            video_data = await self._fetch_video_data(shortcode)

            if not video_data:
                raise ValueError("Failed to fetch video data from API")

            user = video_data.get('user', {})
            caption = video_data.get('caption', {})

            return {
                'instagram_id': video_data.get('id', ''),
                'shortcode': video_data.get('code', ''),
                'title': video_data.get('title', ''),
                'caption': caption.get('text', '') if caption else '',
                'creator_username': user.get('username', ''),
                'creator_full_name': user.get('full_name', ''),
                'like_count': video_data.get('like_count', 0),
                'comment_count': video_data.get('comment_count', 0),
                'view_count': video_data.get('view_count', 0),
                'duration': video_data.get('video_duration', 0),
            }

        except Exception as e:
            logger.error(f"Error getting Instagram post info: {str(e)}")
            raise
