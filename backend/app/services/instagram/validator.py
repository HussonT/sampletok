import re
from typing import Optional, Tuple
from urllib.parse import urlparse, parse_qs


class InstagramURLValidator:
    """Validates and normalizes Instagram URLs"""

    VALID_DOMAINS = ['instagram.com', 'www.instagram.com', 'instagr.am', 'www.instagr.am']

    @classmethod
    def validate_url(cls, url: str) -> Tuple[bool, Optional[str]]:
        """
        Validate an Instagram URL
        Returns: (is_valid, error_message)
        """
        try:
            # Ensure URL has a scheme
            if not url.startswith(('http://', 'https://')):
                url = f"https://{url}"

            parsed = urlparse(url)

            # Check if domain is valid
            if parsed.netloc not in cls.VALID_DOMAINS:
                return False, f"Invalid domain: {parsed.netloc}. Must be from instagram.com"

            # Check for shortcode in path
            shortcode = cls._extract_shortcode(url)
            if not shortcode:
                return False, "Could not extract shortcode from URL. URL must be in format /reel/, /p/, or /tv/"

            return True, None

        except Exception as e:
            return False, f"Invalid URL format: {str(e)}"

    @classmethod
    def _extract_shortcode(cls, url: str) -> Optional[str]:
        """
        Extract shortcode from Instagram URL
        Supports: /reel/{shortcode}/, /p/{shortcode}/, /tv/{shortcode}/
        """
        patterns = [
            r'/reel/([A-Za-z0-9_-]+)',    # Reels: /reel/DQxmWDwAfUf/
            r'/p/([A-Za-z0-9_-]+)',        # Posts: /p/DQxmWDwAfUf/
            r'/tv/([A-Za-z0-9_-]+)',       # IGTV: /tv/DQxmWDwAfUf/
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)

        return None

    @classmethod
    def normalize_url(cls, url: str) -> str:
        """
        Normalize Instagram URL to a standard format
        Returns the original URL as Instagram uses shortcodes
        """
        # Ensure URL has a scheme
        if not url.startswith(('http://', 'https://')):
            url = f"https://{url}"

        # Extract shortcode and post type
        parsed = urlparse(url)
        path = parsed.path

        # Determine post type
        if '/reel/' in path:
            post_type = 'reel'
        elif '/tv/' in path:
            post_type = 'tv'
        elif '/p/' in path:
            post_type = 'p'
        else:
            return url

        shortcode = cls._extract_shortcode(url)
        if shortcode:
            # Return clean URL without query parameters
            return f"https://www.instagram.com/{post_type}/{shortcode}/"

        return url

    @classmethod
    def extract_shortcode(cls, url: str) -> Optional[str]:
        """Public method to extract shortcode from URL"""
        return cls._extract_shortcode(url)
