"""
InstagramEngagement model - Tracks mentions, comments, and auto-engagement interactions
"""
from sqlalchemy import Column, String, Integer, DateTime, Boolean, Text, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from app.core.database import Base
from app.utils import utcnow_naive


class EngagementType(enum.Enum):
    """Type of Instagram engagement"""
    MENTION = "mention"  # Creator tagged @sampletheinternet in post
    COMMENT = "comment"  # We posted a comment on their post
    STORY_MENTION = "story_mention"  # Tagged in story (future)


class EngagementStatus(enum.Enum):
    """Processing status of engagement"""
    PENDING = "pending"  # Detected via webhook, not yet processed
    PROCESSING = "processing"  # Currently processing video/audio
    COMPLETED = "completed"  # Successfully processed and commented
    FAILED = "failed"  # Failed to process
    SKIPPED = "skipped"  # Skipped (duplicate, rate limit, etc.)


class InstagramEngagement(Base):
    """
    Tracks Instagram Graph API engagements (mentions, comments).

    Flow:
    1. Webhook receives mention notification
    2. Record created with status=PENDING
    3. Inngest job processes video → status=PROCESSING
    4. Auto-comment posted → status=COMPLETED

    This table enables:
    - Duplicate detection (don't process same post twice)
    - Engagement analytics (mentions per day, success rate)
    - Error tracking (why did it fail?)
    - Rate limiting (prevent spam)
    """
    __tablename__ = "instagram_engagements"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Instagram Graph API identifiers
    instagram_media_id = Column(String, unique=True, index=True, nullable=False)  # IG Media ID from Graph API
    instagram_shortcode = Column(String, index=True)  # Shortcode (e.g., "DQxmWDwAfUf")
    instagram_permalink = Column(String)  # Full Instagram URL

    # Engagement metadata
    engagement_type = Column(Enum(EngagementType), default=EngagementType.MENTION, index=True)
    status = Column(Enum(EngagementStatus), default=EngagementStatus.PENDING, index=True)

    # Creator information
    instagram_user_id = Column(String, index=True)  # Instagram user ID who mentioned us
    instagram_username = Column(String, index=True)  # Username who mentioned us

    # Media information from webhook
    media_type = Column(String)  # "IMAGE", "VIDEO", "CAROUSEL_ALBUM"
    caption = Column(Text)  # Post caption/text

    # Processing information
    error_message = Column(Text)  # Error details if failed
    retry_count = Column(Integer, default=0)  # Number of retry attempts

    # Sample relationship (once processed)
    sample_id = Column(UUID(as_uuid=True), ForeignKey('samples.id'), nullable=True, index=True)

    # Comment we posted (if any)
    comment_id = Column(String)  # Instagram comment ID
    comment_text = Column(Text)  # Text of our comment
    comment_posted_at = Column(DateTime)  # When we commented

    # Webhook payload (for debugging)
    webhook_payload = Column(JSONB)  # Full webhook payload

    # Timestamps
    detected_at = Column(DateTime, default=utcnow_naive, index=True)  # When webhook received
    processed_at = Column(DateTime)  # When processing completed
    created_at = Column(DateTime, default=utcnow_naive, index=True)
    updated_at = Column(DateTime, default=utcnow_naive, onupdate=utcnow_naive)

    # Relationships
    sample = relationship("Sample", backref="instagram_engagements")
