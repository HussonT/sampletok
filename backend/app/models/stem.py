from sqlalchemy import Column, String, Integer, Float, DateTime, Text, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from app.core.database import Base
from app.utils import utcnow_naive


class StemType(enum.Enum):
    """Supported stem types from La La AI Phoenix model"""
    VOCAL = "vocal"
    VOICE = "voice"
    DRUM = "drum"
    PIANO = "piano"
    BASS = "bass"
    ELECTRIC_GUITAR = "electric_guitar"
    ACOUSTIC_GUITAR = "acoustic_guitar"
    SYNTHESIZER = "synthesizer"
    STRINGS = "strings"
    WIND = "wind"


class StemProcessingStatus(enum.Enum):
    PENDING = "pending"
    UPLOADING = "uploading"
    PROCESSING = "processing"
    DOWNLOADING = "downloading"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    FAILED = "failed"


class Stem(Base):
    __tablename__ = "stems"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Parent sample relationship
    parent_sample_id = Column(UUID(as_uuid=True), ForeignKey('samples.id', ondelete='CASCADE'), nullable=False, index=True)

    # Stem information
    stem_type = Column(Enum(StemType), nullable=False)

    # File storage paths and URLs
    file_path_wav = Column(String)  # R2 path: samples/{sample_id}/stems/{stem_type}.wav
    file_path_mp3 = Column(String)  # R2 path: samples/{sample_id}/stems/{stem_type}.mp3
    audio_url_wav = Column(String)  # Public URL for WAV
    audio_url_mp3 = Column(String)  # Public URL for MP3
    file_size_wav = Column(Integer)
    file_size_mp3 = Column(Integer)

    # Audio metadata (analyzed after separation)
    duration_seconds = Column(Float)
    bpm = Column(Integer)
    key = Column(String)

    # Download tracking
    download_count = Column(Integer, default=0, nullable=False)

    # Processing information
    status = Column(Enum(StemProcessingStatus), default=StemProcessingStatus.PENDING, nullable=False)
    lalal_task_id = Column(String)  # La La AI task ID for polling
    error_message = Column(Text)

    # Timestamps
    created_at = Column(DateTime, default=utcnow_naive, index=True)
    updated_at = Column(DateTime, default=utcnow_naive, onupdate=utcnow_naive)
    completed_at = Column(DateTime)

    # Relationships
    parent_sample = relationship("Sample", back_populates="stems")
    user_downloads = relationship("UserStemDownload", back_populates="stem", cascade="all, delete-orphan")
    user_favorites = relationship("UserStemFavorite", back_populates="stem", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Stem {self.id} - {self.stem_type.value} from Sample {self.parent_sample_id}>"
