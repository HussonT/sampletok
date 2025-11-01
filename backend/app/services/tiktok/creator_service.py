"""
Service for managing TikTok creators with smart caching
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.tiktok_creator import TikTokCreator
from app.utils import utcnow_naive
from app.services.tiktok.downloader import TikTokDownloader
from app.utils import utcnow_naive
from app.services.storage.s3 import S3Storage
from app.utils import utcnow_naive
from app.core.config import settings
from app.utils import utcnow_naive

logger = logging.getLogger(__name__)

# Cache TTL from config
CREATOR_CACHE_TTL = timedelta(hours=settings.CREATOR_CACHE_TTL_HOURS)


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
            try:
                creator = await self._create_creator(creator_data)
            except IntegrityError:
                # Race condition: another process created this creator
                # Roll back and fetch the existing creator
                await self.db.rollback()
                logger.info(f"Creator @{username} already exists (race condition), fetching...")
                stmt = select(TikTokCreator).where(TikTokCreator.username == username)
                result = await self.db.execute(stmt)
                creator = result.scalar_one_or_none()

                if not creator:
                    raise Exception(f"Failed to get/fetch creator @{username}")

        return creator

    def _is_fresh(self, creator: TikTokCreator) -> bool:
        """Check if creator data is fresh (< 24 hours old)"""
        if not creator.last_fetched_at:
            return False

        age = utcnow_naive() - creator.last_fetched_at
        return age < CREATOR_CACHE_TTL

    async def _create_creator(self, data: Dict[str, Any]) -> TikTokCreator:
        """Create new creator in DB"""
        # Create creator first to get ID
        creator = TikTokCreator(
            tiktok_id=data.get('creator_id', ''),
            username=data.get('creator_username', ''),
            nickname=data.get('creator_name', ''),
            signature=data.get('creator_signature'),
            verified=data.get('creator_verified', False),
            follower_count=data.get('creator_follower_count', 0),
            following_count=data.get('creator_following_count', 0),
            heart_count=data.get('creator_heart_count', 0),
            video_count=data.get('creator_video_count', 0),
            last_fetched_at=utcnow_naive()
        )

        self.db.add(creator)
        await self.db.commit()
        await self.db.refresh(creator)

        # Download and upload avatars to our storage
        storage = S3Storage()
        creator_id = str(creator.id)

        avatar_urls = await self._download_avatars(
            storage,
            creator_id,
            data.get('creator_avatar_thumb'),
            data.get('creator_avatar_medium'),
            data.get('creator_avatar_large')
        )

        # Update creator with stored avatar URLs
        creator.avatar_thumb = avatar_urls.get('thumb')
        creator.avatar_medium = avatar_urls.get('medium')
        creator.avatar_large = avatar_urls.get('large')
        await self.db.commit()
        await self.db.refresh(creator)

        logger.info(f"Created new creator @{creator.username} with {creator.follower_count} followers")
        return creator

    async def _update_creator(self, creator: TikTokCreator, data: Dict[str, Any]) -> TikTokCreator:
        """Update existing creator with fresh data"""
        creator.nickname = data.get('creator_name', creator.nickname)
        creator.signature = data.get('creator_signature', creator.signature)
        creator.verified = data.get('creator_verified', creator.verified)
        creator.follower_count = data.get('creator_follower_count', creator.follower_count)
        creator.following_count = data.get('creator_following_count', creator.following_count)
        creator.heart_count = data.get('creator_heart_count', creator.heart_count)
        creator.video_count = data.get('creator_video_count', creator.video_count)
        creator.last_fetched_at = utcnow_naive()

        # Download and upload new avatars to our storage
        storage = S3Storage()
        creator_id = str(creator.id)

        avatar_urls = await self._download_avatars(
            storage,
            creator_id,
            data.get('creator_avatar_thumb'),
            data.get('creator_avatar_medium'),
            data.get('creator_avatar_large')
        )

        # Update with new stored URLs if available
        if avatar_urls.get('thumb'):
            creator.avatar_thumb = avatar_urls['thumb']
        if avatar_urls.get('medium'):
            creator.avatar_medium = avatar_urls['medium']
        if avatar_urls.get('large'):
            creator.avatar_large = avatar_urls['large']

        await self.db.commit()
        await self.db.refresh(creator)

        logger.info(f"Updated creator @{creator.username} - {creator.follower_count} followers")
        return creator

    async def _download_avatars(
        self,
        storage: S3Storage,
        creator_id: str,
        thumb_url: Optional[str],
        medium_url: Optional[str],
        large_url: Optional[str]
    ) -> Dict[str, Optional[str]]:
        """Download and upload creator avatars to our storage"""
        avatar_urls = {}

        # Download and upload thumb avatar
        if thumb_url:
            stored_url = await storage.download_and_upload_url(
                thumb_url,
                f"creators/{creator_id}/avatar_thumb.jpg",
                "image/jpeg"
            )
            avatar_urls['thumb'] = stored_url

        # Download and upload medium avatar
        if medium_url:
            stored_url = await storage.download_and_upload_url(
                medium_url,
                f"creators/{creator_id}/avatar_medium.jpg",
                "image/jpeg"
            )
            avatar_urls['medium'] = stored_url

        # Download and upload large avatar
        if large_url:
            stored_url = await storage.download_and_upload_url(
                large_url,
                f"creators/{creator_id}/avatar_large.jpg",
                "image/jpeg"
            )
            avatar_urls['large'] = stored_url

        return avatar_urls
