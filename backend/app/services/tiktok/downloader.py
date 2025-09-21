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
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
        }

        # Don't set cookies here - we'll try them one by one during download
        # Add Decodo proxy if configured
        if settings.PROXY_URL:
            self.ydl_opts['proxy'] = settings.PROXY_URL
            logger.info(f"Using Decodo proxy for TikTok downloads")

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

        # Try different browsers for cookies
        # First try Dia by using Chrome's cookie extraction with Dia's path
        browsers_to_try = []

        # Check if Dia exists and add it first (using chrome extraction method)
        import os
        dia_cookies = "/Users/tomhusson/Library/Application Support/Dia/User Data/Default/Cookies"
        if os.path.exists(dia_cookies):
            # Use chrome extraction but with Dia's profile path
            browsers_to_try.append(('chrome', 'Default', None, '/Users/tomhusson/Library/Application Support/Dia/User Data'))
            logger.info("Found Dia browser, will try it first")

        # Then add other browsers
        browsers_to_try.extend([
            ('firefox', None, None, None),
            ('chrome', None, None, None),
            ('safari', None, None, None),
            ('edge', None, None, None),
            ('brave', None, None, None),
        ])

        last_error = None

        for browser_config in browsers_to_try:
            # Create a copy of opts for this attempt
            current_opts = opts.copy()
            current_opts['cookiesfrombrowser'] = browser_config

            # Get browser name for logging
            browser_name = "Dia" if browser_config[3] and "Dia" in browser_config[3] else browser_config[0]

            try:
                with yt_dlp.YoutubeDL(current_opts) as ydl:
                    logger.info(f"Trying to extract cookies from {browser_name}...")
                    # Extract info first
                    info = ydl.extract_info(url, download=False)

                    # If we got here, it worked!
                    logger.info(f"Successfully using {browser_name} cookies")
                    opts['cookiesfrombrowser'] = browser_config
                    break
            except Exception as e:
                error_msg = str(e)
                if "could not find" in error_msg and "cookies database" in error_msg:
                    logger.debug(f"{browser_name} not installed or no cookies found")
                elif "requiring login" in error_msg:
                    logger.debug(f"{browser_name} cookies found but not logged into TikTok")
                else:
                    logger.debug(f"{browser_name} failed: {error_msg[:100]}")
                last_error = e
                continue
        else:
            # If no browser worked, try without cookies (will use proxy if configured)
            logger.warning("No browser cookies worked, trying without cookies...")
            try:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(url, download=False)
            except Exception as e:
                if last_error:
                    raise last_error
                raise

        # Now we have info, validate it
        if not info:
            raise ValueError("Unable to extract video information. Video may be private, deleted, or region-restricted.")

        # Check video duration
        duration = info.get('duration', 0)
        if duration > settings.MAX_VIDEO_DURATION_SECONDS:
            raise ValueError(f"Video too long: {duration}s (max: {settings.MAX_VIDEO_DURATION_SECONDS}s)")

        # Now download the video with the working configuration
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])

            # Get the downloaded file path
            video_id = info.get('id')
            ext = info.get('ext', 'mp4')

            # Ensure video_id is a string
            if not isinstance(video_id, str):
                video_id = str(video_id) if video_id else 'unknown'
            if not isinstance(ext, str):
                ext = str(ext) if ext else 'mp4'

            # Handle outtmpl being either string or dict
            outtmpl = opts['outtmpl']
            if isinstance(outtmpl, dict):
                # If it's a dict, get the default template
                outtmpl = outtmpl.get('default', '%(id)s.%(ext)s')

            # Get the output directory from the template
            output_dir = Path(outtmpl).parent
            video_filename = f"{video_id}.{ext}"
            video_path = output_dir / video_filename

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