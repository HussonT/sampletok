from sqlalchemy import Column, String, Integer, DateTime, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.core.database import Base
from app.utils import utcnow_naive


class InstagramCreator(Base):
    __tablename__ = "instagram_creators"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Instagram identifiers
    instagram_id = Column(String, unique=True, index=True, nullable=False)  # Instagram's user pk
    username = Column(String, unique=True, index=True, nullable=False)  # @username
    full_name = Column(String)  # Display name

    # Profile media - Stored in our infrastructure (R2/S3/GCS)
    profile_pic_url = Column(String)  # Our stored profile picture

    # Profile info
    is_verified = Column(Boolean, default=False)  # Is verified creator
    is_private = Column(Boolean, default=False)  # Is private account

    # Stats (not available in Instagram post API, would need separate API call)
    follower_count = Column(Integer, default=0)
    following_count = Column(Integer, default=0)
    media_count = Column(Integer, default=0)  # Total posts

    # Cache management
    last_fetched_at = Column(DateTime, default=utcnow_naive)  # When data was last updated

    created_at = Column(DateTime, default=utcnow_naive, index=True)
    updated_at = Column(DateTime, default=utcnow_naive, onupdate=utcnow_naive)

    # Relationships
    samples = relationship("Sample", back_populates="instagram_creator")
