"""
Email service for sending sample notifications via Postmark.

This service handles:
- Sending sample ready emails to Instagram creators
- Email templates with sample metadata
- Error handling and logging
"""

import logging
from typing import Optional, Dict, Any
from postmarker.core import PostmarkClient
from postmarker.exceptions import PostmarkerException

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending emails via Postmark"""

    def __init__(self):
        """Initialize Postmark client"""
        self.api_key = settings.POSTMARK_API_KEY
        self.from_email = settings.POSTMARK_FROM_EMAIL

        if self.api_key:
            self.client = PostmarkClient(server_token=self.api_key)
        else:
            self.client = None
            logger.warning("Postmark API key not configured - email sending disabled")

    def is_configured(self) -> bool:
        """Check if email service is properly configured"""
        return bool(self.api_key and self.from_email)

    def send_sample_ready_email(
        self,
        to_email: str,
        creator_username: str,
        sample_url: str,
        bpm: Optional[int] = None,
        key: Optional[str] = None,
        original_creator_username: Optional[str] = None
    ) -> bool:
        """
        Send 'Sample Ready' email to Instagram creator.

        Args:
            to_email: Recipient email address
            creator_username: Instagram username who tagged us
            sample_url: URL to the sample page
            bpm: Detected BPM (optional)
            key: Detected musical key (optional)
            original_creator_username: Original video creator (optional)

        Returns:
            True if email sent successfully, False otherwise
        """
        if not self.is_configured():
            logger.error("Email service not configured - cannot send email")
            return False

        try:
            # Build metadata string
            metadata_parts = []
            if bpm:
                metadata_parts.append(f"BPM: {bpm}")
            if key:
                metadata_parts.append(f"Key: {key}")
            metadata_str = " | ".join(metadata_parts) if metadata_parts else "Processing complete"

            # Build email body
            html_body = self._build_html_email(
                creator_username=creator_username,
                sample_url=sample_url,
                metadata=metadata_str,
                original_creator=original_creator_username
            )

            text_body = self._build_text_email(
                creator_username=creator_username,
                sample_url=sample_url,
                metadata=metadata_str,
                original_creator=original_creator_username
            )

            # Send email via Postmark
            self.client.emails.send(
                From=self.from_email,
                To=to_email,
                Subject=f"🎵 Your sample is ready, @{creator_username}!",
                HtmlBody=html_body,
                TextBody=text_body,
                MessageStream="outbound"
            )

            logger.info(f"Successfully sent sample ready email to {to_email} (@{creator_username})")
            return True

        except PostmarkerException as e:
            logger.error(f"Postmark error sending email to {to_email}: {str(e)}")
            return False

        except Exception as e:
            logger.error(f"Unexpected error sending email to {to_email}: {str(e)}", exc_info=True)
            return False

    def _build_html_email(
        self,
        creator_username: str,
        sample_url: str,
        metadata: str,
        original_creator: Optional[str] = None
    ) -> str:
        """Build HTML email body"""

        creator_credit = ""
        if original_creator:
            creator_credit = f"""
            <p style="color: #666; font-size: 14px; margin: 20px 0;">
                <strong>Original creator:</strong> @{original_creator}<br>
                Made something with it? Tag them and let them hear what you created! 🙌
            </p>
            """

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">

            <div style="text-align: center; margin-bottom: 30px;">
                <h1 style="color: #000; font-size: 28px; margin-bottom: 10px;">
                    ✅ Your sample is ready!
                </h1>
                <p style="color: #666; font-size: 18px; margin: 0;">
                    Hey @{creator_username} 👋
                </p>
            </div>

            <div style="background: #f8f9fa; border-radius: 12px; padding: 20px; margin: 20px 0;">
                <h2 style="margin-top: 0; color: #000; font-size: 20px;">🎵 Sample Info</h2>
                <p style="font-size: 16px; color: #333; margin: 10px 0;">
                    <strong>{metadata}</strong>
                </p>
            </div>

            <div style="text-align: center; margin: 30px 0;">
                <a href="{sample_url}" style="display: inline-block; background: #000; color: #fff; padding: 16px 40px; text-decoration: none; border-radius: 8px; font-size: 18px; font-weight: bold;">
                    🎧 Listen & Download
                </a>
            </div>

            {creator_credit}

            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 12px; padding: 20px; margin: 30px 0; color: white;">
                <h3 style="margin-top: 0; font-size: 18px;">🔥 Want to remix this?</h3>
                <p style="margin: 10px 0; font-size: 15px;">
                    Comment <strong>@sampletheinternet</strong> on your post and get this sample in your inbox with <strong>stem splitter and upgraded audio</strong>!
                </p>
            </div>

            <div style="text-align: center; margin-top: 40px; padding-top: 20px; border-top: 1px solid #e0e0e0;">
                <p style="color: #999; font-size: 13px; margin: 5px 0;">
                    Made with 🎵 by <a href="https://sampletheinternet.com" style="color: #667eea; text-decoration: none;">Sample The Internet</a>
                </p>
                <p style="color: #999; font-size: 12px; margin: 5px 0;">
                    Transform any video into music samples instantly
                </p>
            </div>

        </body>
        </html>
        """

    def _build_text_email(
        self,
        creator_username: str,
        sample_url: str,
        metadata: str,
        original_creator: Optional[str] = None
    ) -> str:
        """Build plain text email body"""

        creator_credit = ""
        if original_creator:
            creator_credit = f"""
Original creator: @{original_creator}
Made something with it? Tag them and let them hear what you created!

"""

        return f"""
✅ Your sample is ready!

Hey @{creator_username},

Your sample has been processed and is ready to use!

🎵 Sample Info
{metadata}

Listen & Download:
{sample_url}

{creator_credit}🔥 Want to remix this?
Comment @sampletheinternet on your post and get this sample in your inbox with stem splitter and upgraded audio!

---
Made with 🎵 by Sample The Internet
https://sampletheinternet.com
Transform any video into music samples instantly
"""


# Global instance
email_service = EmailService()
