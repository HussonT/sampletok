"""
ShareService - URL generation and social media text templates for sample sharing
"""
from typing import Optional
from uuid import UUID
from urllib.parse import urlencode
import logging

from app.core.config import settings
from app.models import Sample

logger = logging.getLogger(__name__)


class ShareService:
    """Service for generating shareable URLs and social media text"""

    @staticmethod
    def get_sample_share_url(
        sample_id: UUID,
        platform: Optional[str] = None,
        utm_source: Optional[str] = None,
        utm_medium: Optional[str] = None,
        utm_campaign: Optional[str] = None
    ) -> str:
        """
        Generate shareable URL for a sample with UTM tracking parameters.

        Args:
            sample_id: UUID of the sample
            platform: Platform where link will be shared (instagram, twitter, facebook, etc.)
            utm_source: Override default UTM source
            utm_medium: Override default UTM medium
            utm_campaign: Override default UTM campaign

        Returns:
            Full URL with UTM parameters

        Example:
            https://app.sampletheinternet.com/s/123?utm_source=instagram&utm_medium=comment&utm_campaign=auto_engagement
        """
        # Base URL configuration
        base_url = getattr(settings, 'PUBLIC_APP_URL', 'https://app.sampletheinternet.com')

        # Remove trailing slash if present
        base_url = base_url.rstrip('/')

        # Construct sample URL
        sample_url = f"{base_url}/s/{sample_id}"

        # Build UTM parameters
        utm_params = {}

        if platform:
            # Platform-specific defaults
            utm_params['utm_source'] = utm_source or platform.lower()

            # Set medium based on platform if not specified
            if not utm_medium:
                if platform.lower() == 'instagram':
                    utm_params['utm_medium'] = 'comment'
                elif platform.lower() in ['twitter', 'facebook']:
                    utm_params['utm_medium'] = 'social'
                else:
                    utm_params['utm_medium'] = 'share'
            else:
                utm_params['utm_medium'] = utm_medium

            utm_params['utm_campaign'] = utm_campaign or 'sample_share'

        # Add UTM parameters to URL if any exist
        if utm_params:
            query_string = urlencode(utm_params)
            sample_url = f"{sample_url}?{query_string}"

        return sample_url

    @staticmethod
    def generate_share_text(sample: Sample, platform: str) -> str:
        """
        Generate platform-specific share text for social media.

        Args:
            sample: Sample model instance
            platform: Target platform (instagram, twitter, facebook)

        Returns:
            Formatted share text appropriate for the platform
        """
        # Get share URL
        share_url = ShareService.get_sample_share_url(
            sample.id,
            platform=platform,
            utm_campaign='auto_engagement'
        )

        # Extract metadata
        bpm = sample.bpm or "Unknown"
        key = sample.key or "Unknown"
        username = sample.creator_username or "Unknown"

        # Platform-specific templates
        if platform.lower() == 'instagram':
            # Instagram: Short, engaging, with emojis and hashtags
            text = (
                f"✅ Your sample is ready, @{username}!\n"
                f"🎵 BPM: {bpm} | Key: {key}\n\n"
                f"Make music with it here: {share_url}\n\n"
                f"Tag us when you use it! 🔥\n"
                f"#SampleTheInternet #ProducerTools #MusicProduction"
            )
        elif platform.lower() == 'twitter':
            # Twitter: Concise format (character limit)
            text = (
                f"🎵 Sample ready for @{username}!\n"
                f"BPM: {bpm} | Key: {key}\n\n"
                f"{share_url}\n\n"
                f"#SampleTheInternet #Producers"
            )
        elif platform.lower() == 'facebook':
            # Facebook: Descriptive format
            text = (
                f"Sample transformed and ready! 🎵\n\n"
                f"Creator: @{username}\n"
                f"BPM: {bpm}\n"
                f"Musical Key: {key}\n\n"
                f"Check it out and start creating: {share_url}\n\n"
                f"#SampleTheInternet #MusicProduction #ProducerTools"
            )
        else:
            # Generic template for other platforms
            text = (
                f"Your sample is ready!\n"
                f"BPM: {bpm} | Key: {key}\n"
                f"{share_url}"
            )

        return text

    @staticmethod
    def generate_instagram_comment(sample: Sample) -> str:
        """
        Generate Instagram comment text for auto-engagement.
        Optimized for Instagram's character limits and style.

        Args:
            sample: Sample model instance

        Returns:
            Instagram comment text with sample metadata and link
        """
        return ShareService.generate_share_text(sample, 'instagram')
