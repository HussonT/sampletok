import os
import tempfile
import asyncio
from typing import Dict, Any, Optional
import yt_dlp
from pathlib import Path
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class TikTokDownloader:
    """Downloads TikTok videos using yt-dlp"""

    def __init__(self):
        self.ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'format': 'best',
            'outtmpl': '%(id)s.%(ext)s',
            'cookiefile': None,  # Can add cookie file if needed
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
        }

    async def download_video(self, url: str, output_dir: Optional[str] = None) -> Dict[str, Any]:
        """
        Download a TikTok video and extract metadata
        Returns dict with video_path and metadata
        """
        if not output_dir:
            output_dir = tempfile.mkdtemp(prefix='tiktok_')

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Update output template with directory
        opts = self.ydl_opts.copy()
        opts['outtmpl'] = str(output_path / '%(id)s.%(ext)s')

        try:
            # Run yt-dlp in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._download_with_ytdlp,
                url,
                opts
            )

            return result

        except Exception as e:
            logger.error(f"Error downloading TikTok video: {str(e)}")
            raise

    def _download_with_ytdlp(self, url: str, opts: dict) -> Dict[str, Any]:
        """Synchronous download using yt-dlp"""
        with yt_dlp.YoutubeDL(opts) as ydl:
            # Extract info first
            info = ydl.extract_info(url, download=False)

            # Check video duration
            duration = info.get('duration', 0)
            if duration > settings.MAX_VIDEO_DURATION_SECONDS:
                raise ValueError(f"Video too long: {duration}s (max: {settings.MAX_VIDEO_DURATION_SECONDS}s)")

            # Download the video
            ydl.download([url])

            # Get the downloaded file path
            video_id = info.get('id')
            ext = info.get('ext', 'mp4')
            video_path = Path(opts['outtmpl'].replace('%(id)s', video_id).replace('%(ext)s', ext))

            if not video_path.exists():
                # Try to find the file with different extensions
                for possible_ext in ['mp4', 'webm', 'mov']:
                    possible_path = video_path.with_suffix(f'.{possible_ext}')
                    if possible_path.exists():
                        video_path = possible_path
                        break
                else:
                    raise FileNotFoundError(f"Downloaded video not found: {video_path}")

            # Extract relevant metadata
            metadata = {
                'tiktok_id': info.get('id'),
                'title': info.get('title', ''),
                'description': info.get('description', ''),
                'creator_username': info.get('uploader', ''),
                'creator_name': info.get('uploader_id', ''),
                'view_count': info.get('view_count', 0),
                'like_count': info.get('like_count', 0),
                'comment_count': info.get('comment_count', 0),
                'share_count': info.get('repost_count', 0),
                'duration': duration,
                'thumbnail_url': info.get('thumbnail', ''),
                'upload_date': info.get('upload_date', ''),
                'video_path': str(video_path)
            }

            return metadata

    async def get_video_info(self, url: str) -> Dict[str, Any]:
        """Get video metadata without downloading"""
        opts = self.ydl_opts.copy()
        opts['skip_download'] = True

        try:
            loop = asyncio.get_event_loop()
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = await loop.run_in_executor(None, ydl.extract_info, url, False)

            return {
                'tiktok_id': info.get('id'),
                'title': info.get('title', ''),
                'description': info.get('description', ''),
                'creator_username': info.get('uploader', ''),
                'duration': info.get('duration', 0),
                'view_count': info.get('view_count', 0),
            }

        except Exception as e:
            logger.error(f"Error getting TikTok video info: {str(e)}")
            raise