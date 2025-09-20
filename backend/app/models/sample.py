from sqlalchemy import Column, String, Integer, Float, DateTime, Text, ForeignKey, Table, Enum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from app.core.database import Base


class ProcessingStatus(enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


# Association table for many-to-many relationship
user_samples = Table(
    'user_samples',
    Base.metadata,
    Column('user_id', UUID(as_uuid=True), ForeignKey('users.id'), primary_key=True),
    Column('sample_id', UUID(as_uuid=True), ForeignKey('samples.id'), primary_key=True),
    Column('downloaded_at', DateTime, default=datetime.utcnow)
)


class Sample(Base):
    __tablename__ = "samples"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # TikTok metadata
    tiktok_url = Column(String, nullable=False, index=True)
    tiktok_id = Column(String, unique=True, index=True)
    creator_username = Column(String, index=True)
    creator_name = Column(String)
    description = Column(Text)
    view_count = Column(Integer, default=0)
    like_count = Column(Integer, default=0)
    share_count = Column(Integer, default=0)
    comment_count = Column(Integer, default=0)

    # Audio metadata
    duration_seconds = Column(Float)
    bpm = Column(Integer)
    key = Column(String)
    genre = Column(String)
    tags = Column(JSONB, default=list)

    # File information
    audio_url_wav = Column(String)
    audio_url_mp3 = Column(String)
    waveform_url = Column(String)
    thumbnail_url = Column(String)
    file_size_wav = Column(Integer)
    file_size_mp3 = Column(Integer)

    # Processing information
    status = Column(Enum(ProcessingStatus), default=ProcessingStatus.PENDING)
    error_message = Column(Text)
    processed_at = Column(DateTime)

    # User who added the sample
    creator_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    creator = relationship("User", back_populates="samples", foreign_keys=[creator_id])
    downloaded_by = relationship(
        "User",
        secondary=user_samples,
        back_populates="downloaded_samples"
    )