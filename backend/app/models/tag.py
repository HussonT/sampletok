from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Table, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from app.core.database import Base


class TagCategory(enum.Enum):
    """Categories for organizing tags"""
    GENRE = "genre"  # e.g., hip-hop, edm, pop, rock
    MOOD = "mood"  # e.g., energetic, chill, dark, happy
    INSTRUMENT = "instrument"  # e.g., piano, guitar, drums, synth
    CONTENT = "content"  # e.g., dance, comedy, tutorial, viral
    TEMPO = "tempo"  # e.g., slow, medium, fast, upbeat
    EFFECT = "effect"  # e.g., reverb, distorted, lofi, clean
    OTHER = "other"  # catch-all for uncategorized tags


# Association table for many-to-many relationship between samples and tags
sample_tags = Table(
    'sample_tags',
    Base.metadata,
    Column('sample_id', UUID(as_uuid=True), ForeignKey('samples.id', ondelete='CASCADE'), primary_key=True),
    Column('tag_id', UUID(as_uuid=True), ForeignKey('tags.id', ondelete='CASCADE'), primary_key=True),
    Column('created_at', DateTime, default=datetime.utcnow)
)


class Tag(Base):
    """Tag model for categorizing and searching samples"""
    __tablename__ = "tags"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Tag name (normalized, lowercase, unique)
    name = Column(String(50), unique=True, nullable=False, index=True)

    # Display name (preserves original casing)
    display_name = Column(String(50), nullable=False)

    # Category for organization
    category = Column(Enum(TagCategory), default=TagCategory.OTHER, nullable=False, index=True)

    # Usage tracking
    usage_count = Column(Integer, default=0, nullable=False, index=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    samples = relationship(
        "Sample",
        secondary=sample_tags,
        back_populates="tag_objects"
    )

    def __repr__(self):
        return f"<Tag {self.display_name} ({self.category.value})>"
