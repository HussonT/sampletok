"""
Service for managing TikTok creators with smart caching
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.tiktok_creator import TikTokCreator
from app.services.tiktok.downloader import TikTokDownloader

logger = logging.getLogger(__name__)

# Cache TTL: 24 hours
CREATOR_CACHE_TTL = timedelta(hours=24)


class CreatorService:
    """Manages TikTok creator info with smart caching"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.downloader = TikTokDownloader()

    async def get_or_fetch_creator(self, username: str) -> Optional[TikTokCreator]:
        """
        Get creator from DB or fetch from API if not exists/stale

        Args:
            username: TikTok username (without @)

        Returns:
            TikTokCreator object
        """
        # Check if creator exists in DB
        stmt = select(TikTokCreator).where(TikTokCreator.username == username)
        result = await self.db.execute(stmt)
        creator = result.scalar_one_or_none()

        # If exists and fresh, return cached
        if creator and self._is_fresh(creator):
            logger.info(f"Using cached creator info for @{username}")
            return creator

        # Otherwise, fetch from API
        logger.info(f"Fetching fresh creator info for @{username}")
        creator_data = await self.downloader.get_user_info(username)

        if not creator_data:
            logger.warning(f"Failed to fetch creator info for @{username}")
            return creator  # Return stale data if API fails

        # Update or create creator
        if creator:
            creator = await self._update_creator(creator, creator_data)
        else:
            creator = await self._create_creator(creator_data)

        return creator

    def _is_fresh(self, creator: TikTokCreator) -> bool:
        """Check if creator data is fresh (< 24 hours old)"""
        if not creator.last_fetched_at:
            return False

        age = datetime.utcnow() - creator.last_fetched_at
        return age < CREATOR_CACHE_TTL

    async def _create_creator(self, data: Dict[str, Any]) -> TikTokCreator:
        """Create new creator in DB"""
        creator = TikTokCreator(
            tiktok_id=data.get('creator_id', ''),
            username=data.get('creator_username', ''),
            nickname=data.get('creator_name', ''),
            avatar_thumb=data.get('creator_avatar_thumb'),
            avatar_medium=data.get('creator_avatar_medium'),
            avatar_large=data.get('creator_avatar_large'),
            signature=data.get('creator_signature'),
            verified=data.get('creator_verified', False),
            follower_count=data.get('creator_follower_count', 0),
            following_count=data.get('creator_following_count', 0),
            heart_count=data.get('creator_heart_count', 0),
            video_count=data.get('creator_video_count', 0),
            last_fetched_at=datetime.utcnow()
        )

        self.db.add(creator)
        await self.db.commit()
        await self.db.refresh(creator)

        logger.info(f"Created new creator @{creator.username} with {creator.follower_count} followers")
        return creator

    async def _update_creator(self, creator: TikTokCreator, data: Dict[str, Any]) -> TikTokCreator:
        """Update existing creator with fresh data"""
        creator.nickname = data.get('creator_name', creator.nickname)
        creator.avatar_thumb = data.get('creator_avatar_thumb', creator.avatar_thumb)
        creator.avatar_medium = data.get('creator_avatar_medium', creator.avatar_medium)
        creator.avatar_large = data.get('creator_avatar_large', creator.avatar_large)
        creator.signature = data.get('creator_signature', creator.signature)
        creator.verified = data.get('creator_verified', creator.verified)
        creator.follower_count = data.get('creator_follower_count', creator.follower_count)
        creator.following_count = data.get('creator_following_count', creator.following_count)
        creator.heart_count = data.get('creator_heart_count', creator.heart_count)
        creator.video_count = data.get('creator_video_count', creator.video_count)
        creator.last_fetched_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(creator)

        logger.info(f"Updated creator @{creator.username} - {creator.follower_count} followers")
        return creator
