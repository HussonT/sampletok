from sqlalchemy import Column, String, DateTime, Boolean, Integer, ForeignKey, Index, UniqueConstraint, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    clerk_user_id = Column(String, unique=True, index=True, nullable=False)  # Primary identifier for Clerk users
    email = Column(String, unique=True, index=True, nullable=True)  # Optional - can be fetched from Clerk if needed
    username = Column(String, unique=True, index=True, nullable=True)  # Optional - generated from Clerk ID if not provided
    hashed_password = Column(String, nullable=True)  # Not used for Clerk users
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    credits = Column(Integer, default=10)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    samples = relationship("Sample", back_populates="creator", cascade="all, delete-orphan")
    downloads = relationship("UserDownload", back_populates="user", cascade="all, delete-orphan")
    favorites = relationship("UserFavorite", back_populates="user", cascade="all, delete-orphan")
    collections = relationship("Collection", back_populates="user", cascade="all, delete-orphan")

    # Constraints
    __table_args__ = (
        CheckConstraint('credits >= 0', name='check_credits_non_negative'),
    )


class UserDownload(Base):
    """Track individual user downloads with type (WAV/MP3)"""
    __tablename__ = "user_downloads"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    sample_id = Column(UUID(as_uuid=True), ForeignKey("samples.id", ondelete="CASCADE"), nullable=False)
    download_type = Column(String, nullable=False)  # "wav" or "mp3"
    downloaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="downloads")
    sample = relationship("Sample", back_populates="user_downloads")

    # Indexes for efficient queries
    __table_args__ = (
        Index('idx_user_downloads_user_sample', 'user_id', 'sample_id'),
        Index('idx_user_downloads_user_date', 'user_id', 'downloaded_at'),
    )


class UserFavorite(Base):
    """Track user favorited samples"""
    __tablename__ = "user_favorites"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    sample_id = Column(UUID(as_uuid=True), ForeignKey("samples.id", ondelete="CASCADE"), nullable=False)
    favorited_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="favorites")
    sample = relationship("Sample", back_populates="user_favorites")

    # Ensure one favorite per user per sample
    __table_args__ = (
        UniqueConstraint('user_id', 'sample_id', name='uix_user_sample_favorite'),
        Index('idx_user_favorites_user_date', 'user_id', 'favorited_at'),
    )