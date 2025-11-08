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


class TikTokDownloader:
    """Downloads TikTok videos using RapidAPI"""

    def __init__(self):
        self.api_key = settings.RAPIDAPI_KEY
        self.api_host = settings.RAPIDAPI_HOST

        # Validate API keys are configured
        if not self.api_key or not self.api_host:
            raise ValueError(
                "TikTok API keys not configured. "
                "Please set RAPIDAPI_KEY and RAPIDAPI_HOST environment variables."
            )

        self.headers = {
            'x-rapidapi-key': self.api_key,
            'x-rapidapi-host': self.api_host
        }

    async def download_video(self, url: str, output_dir: Optional[str] = None) -> Dict[str, Any]:
        """
        Download a TikTok video and extract metadata using RapidAPI
        Returns dict with video_path and comprehensive metadata
        """
        if not output_dir:
            output_dir = tempfile.mkdtemp(prefix='tiktok_')

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        try:
            # Step 1: Get video metadata and download URLs from RapidAPI
            logger.info(f"Fetching metadata for TikTok URL: {url}")
            video_data = await self._fetch_video_data(url)

            if not video_data:
                raise ValueError("Failed to fetch video data from API")

            # Step 2: Download the video file
            video_url = video_data.get('play')
            if not video_url:
                raise ValueError("No video download URL found in API response")

            # Extract video ID for filename
            aweme_id = video_data.get('aweme_id', 'unknown')
            video_filename = f"{aweme_id}.mp4"
            video_path = output_path / video_filename

            logger.info(f"Downloading video to: {video_path}")
            await self._download_file(video_url, str(video_path))

            if not video_path.exists():
                raise FileNotFoundError(f"Downloaded video not found: {video_path}")

            # Step 3: Extract and format metadata
            metadata = self._format_metadata(video_data, str(video_path))

            logger.info(f"Successfully downloaded video: {aweme_id}")
            return metadata

        except Exception as e:
            logger.error(f"Error downloading TikTok video: {str(e)}")
            raise

    async def _fetch_video_data(self, url: str) -> Dict[str, Any]:
        """Fetch video metadata from RapidAPI"""
        # Encode the URL for the API
        encoded_url = quote(url, safe='')
        api_url = f"https://{self.api_host}/?url={encoded_url}&hd=1"

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(api_url, headers=self.headers)
                response.raise_for_status()

                data = response.json()

                # Check if the API returned success
                if data.get('code') != 0:
                    error_msg = data.get('msg', 'Unknown error')
                    raise ValueError(f"API error: {error_msg}")

                return data.get('data', {})

            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error fetching video data: {e.response.status_code}")
                raise ValueError(f"Failed to fetch video data: HTTP {e.response.status_code}")
            except Exception as e:
                logger.error(f"Error fetching video data: {str(e)}")
                raise

    async def _download_file(self, url: str, output_path: str) -> None:
        """Download a file from URL to the specified path using streaming to reduce memory usage"""
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            try:
                # Use streaming to avoid loading entire file into memory
                async with client.stream('GET', url) as response:
                    response.raise_for_status()

                    # Write the content to file in chunks
                    with open(output_path, 'wb') as f:
                        async for chunk in response.aiter_bytes(chunk_size=8192):
                            f.write(chunk)

            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error downloading file: {e.response.status_code}")
                raise ValueError(f"Failed to download file: HTTP {e.response.status_code}")
            except Exception as e:
                logger.error(f"Error downloading file: {str(e)}")
                raise

    def _format_metadata(self, api_data: Dict[str, Any], video_path: str) -> Dict[str, Any]:
        """Format API response into our metadata structure"""
        author = api_data.get('author', {})

        # Extract video ID from the URL or use aweme_id
        video_id = api_data.get('aweme_id', '')

        # Get file size
        file_size = 0
        if os.path.exists(video_path):
            file_size = os.path.getsize(video_path)

        metadata = {
            # Primary identifiers
            'tiktok_id': video_id,
            'aweme_id': api_data.get('aweme_id'),

            # Video information
            'title': api_data.get('title', ''),
            'description': api_data.get('title', ''),  # Use title as description for compatibility
            'region': api_data.get('region', ''),

            # Creator information
            'creator_username': author.get('unique_id', ''),
            'creator_name': author.get('nickname', ''),
            'creator_avatar_url': author.get('avatar', ''),
            'creator_follower_count': author.get('follower_count', 0),

            # Engagement metrics
            'view_count': api_data.get('play_count', 0),
            'like_count': api_data.get('digg_count', 0),
            'comment_count': api_data.get('comment_count', 0),
            'share_count': 0,  # Not provided by this API

            # Media URLs
            'thumbnail_url': api_data.get('cover', ''),
            'origin_cover_url': api_data.get('origin_cover', ''),
            'music_url': api_data.get('music', ''),
            'video_url': api_data.get('play', ''),
            'video_url_watermark': api_data.get('wmplay', ''),

            # Timestamps
            'upload_timestamp': api_data.get('create_time', 0),
            'upload_date': datetime.fromtimestamp(
                api_data.get('create_time', 0)
            ).strftime('%Y%m%d') if api_data.get('create_time') else '',

            # File information
            'video_path': video_path,
            'file_size': file_size,

            # Duration will be calculated from the video file later
            'duration': 0
        }

        return metadata

    async def get_user_info(self, unique_id: str) -> Dict[str, Any]:
        """Fetch user/creator information and stats from TikTok"""
        api_url = f"https://{self.api_host}/user/info?unique_id={unique_id}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(api_url, headers=self.headers)
                response.raise_for_status()

                data = response.json()

                # Check if the API returned success
                if data.get('code') != 0:
                    error_msg = data.get('msg', 'Unknown error')
                    logger.warning(f"User info API error: {error_msg}")
                    return {}

                user_data = data.get('data', {})
                user = user_data.get('user', {})
                stats = user_data.get('stats', {})

                return {
                    'creator_id': user.get('id', ''),
                    'creator_username': user.get('uniqueId', ''),
                    'creator_name': user.get('nickname', ''),
                    'creator_avatar_thumb': user.get('avatarThumb', ''),
                    'creator_avatar_medium': user.get('avatarMedium', ''),
                    'creator_avatar_large': user.get('avatarLarger', ''),
                    'creator_signature': user.get('signature', ''),
                    'creator_verified': user.get('verified', False),
                    'creator_follower_count': stats.get('followerCount', 0),
                    'creator_following_count': stats.get('followingCount', 0),
                    'creator_heart_count': stats.get('heartCount', 0),
                    'creator_video_count': stats.get('videoCount', 0),
                }

            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error fetching user info: {e.response.status_code}")
                return {}
            except Exception as e:
                logger.error(f"Error fetching user info: {str(e)}")
                return {}

    async def get_video_info(self, url: str) -> Dict[str, Any]:
        """Get video metadata without downloading"""
        try:
            video_data = await self._fetch_video_data(url)

            if not video_data:
                raise ValueError("Failed to fetch video data from API")

            author = video_data.get('author', {})

            return {
                'tiktok_id': video_data.get('aweme_id'),
                'title': video_data.get('title', ''),
                'description': video_data.get('title', ''),
                'creator_username': author.get('unique_id', ''),
                'creator_name': author.get('nickname', ''),
                'view_count': video_data.get('play_count', 0),
                'like_count': video_data.get('digg_count', 0),
                'comment_count': video_data.get('comment_count', 0),
                'duration': 0,  # Would need to download to get actual duration
            }

        except Exception as e:
            logger.error(f"Error getting TikTok video info: {str(e)}")
            raise