from sqlalchemy import Column, String, DateTime, Boolean, Integer, ForeignKey, Index, UniqueConstraint, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.core.database import Base
from app.utils import utcnow_naive


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    clerk_user_id = Column(String, unique=True, index=True, nullable=False)  # Primary identifier for Clerk users
    email = Column(String, unique=True, index=True, nullable=True)  # Optional - can be fetched from Clerk if needed
    username = Column(String, unique=True, index=True, nullable=True)  # Optional - generated from Clerk ID if not provided
    hashed_password = Column(String, nullable=True)  # Not used for Clerk users
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    credits = Column(Integer, default=0)  # No free credits - subscription required

    # Soft delete for users with active subscriptions
    is_deleted = Column(Boolean, default=False, nullable=False)
    deleted_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=utcnow_naive)
    updated_at = Column(DateTime, default=utcnow_naive, onupdate=utcnow_naive)

    # Relationships
    samples = relationship("Sample", back_populates="creator", cascade="all, delete-orphan")
    downloads = relationship("UserDownload", back_populates="user", cascade="all, delete-orphan")
    stem_downloads = relationship("UserStemDownload", back_populates="user", cascade="all, delete-orphan")
    favorites = relationship("UserFavorite", back_populates="user", cascade="all, delete-orphan")
    stem_favorites = relationship("UserStemFavorite", back_populates="user", cascade="all, delete-orphan")
    collections = relationship("Collection", back_populates="user", cascade="all, delete-orphan")

    # Subscription relationships (1:1)
    subscription = relationship("Subscription", back_populates="user", uselist=False, cascade="all, delete-orphan")
    stripe_customer = relationship("StripeCustomer", back_populates="user", uselist=False, cascade="all, delete-orphan")
    credit_transactions = relationship("CreditTransaction", back_populates="user", cascade="all, delete-orphan")

    # Constraints
    __table_args__ = (
        CheckConstraint('credits >= 0', name='check_credits_non_negative'),
        # Constraint: deleted_at must be set if is_deleted is true
        CheckConstraint(
            '(is_deleted = false) OR (is_deleted = true AND deleted_at IS NOT NULL)',
            name='check_deleted_at'
        ),
        Index('idx_users_is_deleted', 'is_deleted'),
    )


class UserDownload(Base):
    """Track individual user downloads with type (WAV/MP3)"""
    __tablename__ = "user_downloads"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    sample_id = Column(UUID(as_uuid=True), ForeignKey("samples.id", ondelete="CASCADE"), nullable=False)
    download_type = Column(String, nullable=False)  # "wav" or "mp3"
    downloaded_at = Column(DateTime, default=utcnow_naive, nullable=False)

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
    favorited_at = Column(DateTime, default=utcnow_naive, nullable=False)

    # Relationships
    user = relationship("User", back_populates="favorites")
    sample = relationship("Sample", back_populates="user_favorites")

    # Ensure one favorite per user per sample
    __table_args__ = (
        UniqueConstraint('user_id', 'sample_id', name='uix_user_sample_favorite'),
        Index('idx_user_favorites_user_date', 'user_id', 'favorited_at'),
    )


class UserStemDownload(Base):
    """Track individual user stem downloads with type (WAV/MP3)"""
    __tablename__ = "user_stem_downloads"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    stem_id = Column(UUID(as_uuid=True), ForeignKey("stems.id", ondelete="CASCADE"), nullable=False)
    download_type = Column(String, nullable=False)  # "wav" or "mp3"
    downloaded_at = Column(DateTime, default=utcnow_naive, nullable=False)

    # Relationships
    user = relationship("User", back_populates="stem_downloads")
    stem = relationship("Stem", back_populates="user_downloads")

    # Indexes for efficient queries
    __table_args__ = (
        Index('idx_user_stem_downloads_user_stem', 'user_id', 'stem_id'),
        Index('idx_user_stem_downloads_user_date', 'user_id', 'downloaded_at'),
    )


class UserStemFavorite(Base):
    """Track user favorited stems"""
    __tablename__ = "user_stem_favorites"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    stem_id = Column(UUID(as_uuid=True), ForeignKey("stems.id", ondelete="CASCADE"), nullable=False)
    favorited_at = Column(DateTime, default=utcnow_naive, nullable=False)

    # Relationships
    user = relationship("User", back_populates="stem_favorites")
    stem = relationship("Stem", back_populates="user_favorites")

    # Ensure one favorite per user per stem
    __table_args__ = (
        UniqueConstraint('user_id', 'stem_id', name='uix_user_stem_favorite'),
        Index('idx_user_stem_favorites_user_date', 'user_id', 'favorited_at'),
    )