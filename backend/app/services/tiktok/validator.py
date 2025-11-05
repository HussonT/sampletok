import re
from typing import Optional, Tuple
from urllib.parse import urlparse, parse_qs


class TikTokURLValidator:
    """Validates and normalizes TikTok URLs"""

    VALID_DOMAINS = ['tiktok.com', 'www.tiktok.com', 'vm.tiktok.com', 'vt.tiktok.com', 'm.tiktok.com']

    @classmethod
    def validate_url(cls, url: str) -> Tuple[bool, Optional[str]]:
        """
        Validate a TikTok URL
        Returns: (is_valid, error_message)
        """
        try:
            # Ensure URL has a scheme
            if not url.startswith(('http://', 'https://')):
                url = f"https://{url}"

            parsed = urlparse(url)

            # Check if domain is valid
            if parsed.netloc not in cls.VALID_DOMAINS:
                return False, f"Invalid domain: {parsed.netloc}. Must be from tiktok.com"

            # Short URL domains (vm.tiktok.com, vt.tiktok.com) are valid but can't extract video ID until redirect
            # These are valid TikTok URLs even if we can't extract the ID yet
            if parsed.netloc in ['vm.tiktok.com', 'vt.tiktok.com']:
                return True, None

            # Check for video ID in path for regular URLs
            if not cls._extract_video_id(url):
                return False, "Could not extract video ID from URL"

            return True, None

        except Exception as e:
            return False, f"Invalid URL format: {str(e)}"

    @classmethod
    def _extract_video_id(cls, url: str) -> Optional[str]:
        """Extract video ID from TikTok URL"""
        patterns = [
            r'/video/(\d+)',  # Standard format: /video/1234567890
            r'/@[\w._]+/video/(\d+)',  # User video format: /@username/video/1234567890
            r'/v/(\d+)',  # Short format: /v/1234567890
            r'/(\d{19})\.html',  # Mobile format with 19-digit ID: /1234567890123456789.html
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)

        # Check for video parameter in query string
        parsed = urlparse(url)
        query_params = parse_qs(parsed.query)
        if 'video_id' in query_params:
            return query_params['video_id'][0]

        return None

    @classmethod
    def normalize_url(cls, url: str) -> str:
        """Normalize TikTok URL to a standard format"""
        # Ensure URL has a scheme
        if not url.startswith(('http://', 'https://')):
            url = f"https://{url}"

        # Don't normalize short URLs - let the downloader handle the redirect
        parsed = urlparse(url)
        if parsed.netloc in ['vm.tiktok.com', 'vt.tiktok.com']:
            return url

        video_id = cls._extract_video_id(url)
        if video_id and video_id.isdigit():
            # Extract username if present, otherwise use a placeholder
            username_match = re.search(r'/@([\w._]+)/', url)
            username = username_match.group(1) if username_match else 'video'
            return f"https://www.tiktok.com/@{username}/video/{video_id}"
        return url