from sqlalchemy import Column, String, Integer, DateTime, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.core.database import Base


class TikTokCreator(Base):
    __tablename__ = "tiktok_creators"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # TikTok identifiers
    tiktok_id = Column(String, unique=True, index=True, nullable=False)  # TikTok's user ID
    username = Column(String, unique=True, index=True, nullable=False)  # @username
    nickname = Column(String)  # Display name

    # Profile media
    avatar_thumb = Column(String)  # Small avatar URL
    avatar_medium = Column(String)  # Medium avatar URL
    avatar_large = Column(String)  # Large avatar URL

    # Profile info
    signature = Column(Text)  # Bio/signature
    verified = Column(Boolean, default=False)  # Is verified creator

    # Stats (cached from TikTok API)
    follower_count = Column(Integer, default=0)
    following_count = Column(Integer, default=0)
    heart_count = Column(Integer, default=0)  # Total likes received
    video_count = Column(Integer, default=0)  # Total videos posted

    # Cache management
    last_fetched_at = Column(DateTime, default=datetime.utcnow)  # When stats were last updated

    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    samples = relationship("Sample", back_populates="tiktok_creator")
