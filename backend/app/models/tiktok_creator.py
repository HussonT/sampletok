from sqlalchemy import Column, String, Integer, DateTime, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.core.database import Base
from app.utils import utcnow_naive


class TikTokCreator(Base):
    __tablename__ = "tiktok_creators"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # TikTok identifiers
    tiktok_id = Column(String, unique=True, index=True, nullable=False)  # TikTok's user ID
    username = Column(String, unique=True, index=True, nullable=False)  # @username
    nickname = Column(String)  # Display name

    # Profile media - All stored in our infrastructure (R2/S3/GCS)
    avatar_thumb = Column(String)  # Our stored small avatar
    avatar_medium = Column(String)  # Our stored medium avatar
    avatar_large = Column(String)  # Our stored large avatar

    # Profile info
    signature = Column(Text)  # Bio/signature
    verified = Column(Boolean, default=False)  # Is verified creator

    # Stats (cached from TikTok API)
    follower_count = Column(Integer, default=0)
    following_count = Column(Integer, default=0)
    heart_count = Column(Integer, default=0)  # Total likes received
    video_count = Column(Integer, default=0)  # Total videos posted

    # Cache management
    last_fetched_at = Column(DateTime, default=utcnow_naive)  # When stats were last updated

    created_at = Column(DateTime, default=utcnow_naive, index=True)
    updated_at = Column(DateTime, default=utcnow_naive, onupdate=utcnow_naive)

    # Relationships
    samples = relationship("Sample", back_populates="tiktok_creator")
