import re
from typing import Optional, Tuple
from urllib.parse import urlparse, parse_qs


class TikTokURLValidator:
    """Validates and normalizes TikTok URLs"""

    VALID_DOMAINS = ['tiktok.com', 'www.tiktok.com', 'vm.tiktok.com', 'm.tiktok.com']

    @classmethod
    def validate_url(cls, url: str) -> Tuple[bool, Optional[str]]:
        """
        Validate a TikTok URL
        Returns: (is_valid, error_message)
        """
        try:
            parsed = urlparse(url)

            # Check if domain is valid
            if parsed.netloc not in cls.VALID_DOMAINS:
                return False, f"Invalid domain: {parsed.netloc}. Must be from tiktok.com"

            # Check for video ID in path
            if not cls._extract_video_id(url):
                return False, "Could not extract video ID from URL"

            return True, None

        except Exception as e:
            return False, f"Invalid URL format: {str(e)}"

    @classmethod
    def _extract_video_id(cls, url: str) -> Optional[str]:
        """Extract video ID from TikTok URL"""
        patterns = [
            r'/video/(\d+)',  # Standard format
            r'/@[\w.-]+/video/(\d+)',  # User video format
            r'/v/(\d+)',  # Short format
            r'/([\w]+)\.html',  # Mobile format
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
        video_id = cls._extract_video_id(url)
        if video_id and video_id.isdigit():
            # Extract username if present, otherwise use a placeholder
            username_match = re.search(r'/@([\w.-]+)/', url)
            username = username_match.group(1) if username_match else 'video'
            return f"https://www.tiktok.com/@{username}/video/{video_id}"
        return url