from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum as SQLEnum, BigInteger, Index, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum
import uuid


class CollectionStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class Collection(Base):
    __tablename__ = "collections"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # TikTok collection metadata
    tiktok_collection_id = Column(String, nullable=False, index=True)  # e.g., "7565254233776196385"
    tiktok_username = Column(String, nullable=False, index=True)  # The TikTok user who owns the collection
    name = Column(String, nullable=False)  # Collection name from TikTok
    total_video_count = Column(Integer, nullable=False)  # Total videos in the TikTok collection
    current_cursor = Column(Integer, default=0, nullable=False)  # Current pagination cursor
    next_cursor = Column(Integer, nullable=True)  # Next cursor for pagination (from API response)
    has_more = Column(Boolean, default=False, nullable=False)  # Whether there are more videos to import

    # Processing status
    status = Column(SQLEnum(CollectionStatus), default=CollectionStatus.pending, nullable=False, index=True)
    processed_count = Column(Integer, default=0, nullable=False)  # How many videos we've processed so far
    error_message = Column(String, nullable=True)  # Error details if failed

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    started_at = Column(DateTime, nullable=True)  # When processing started
    completed_at = Column(DateTime, nullable=True)  # When processing completed

    # Relationships
    user = relationship("User", back_populates="collections")
    collection_samples = relationship("CollectionSample", back_populates="collection", cascade="all, delete-orphan")

    # Index for finding collections by TikTok ID and username
    __table_args__ = (
        Index('ix_collections_tiktok_username_collection_id', 'tiktok_username', 'tiktok_collection_id'),
        Index('ix_collections_user_created', 'user_id', 'created_at'),
    )


class CollectionSample(Base):
    __tablename__ = "collection_samples"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    collection_id = Column(UUID(as_uuid=True), ForeignKey("collections.id", ondelete="CASCADE"), nullable=False, index=True)
    sample_id = Column(UUID(as_uuid=True), ForeignKey("samples.id", ondelete="CASCADE"), nullable=False, index=True)
    position = Column(Integer, nullable=False)  # Order in the collection (0-based)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    collection = relationship("Collection", back_populates="collection_samples")
    sample = relationship("Sample", back_populates="collection_samples")

    # Unique constraint: each sample can only appear once per collection
    # Index for efficient lookups
    __table_args__ = (
        Index('ix_collection_samples_unique', 'collection_id', 'sample_id', unique=True),
        Index('ix_collection_samples_position', 'collection_id', 'position'),
    )
