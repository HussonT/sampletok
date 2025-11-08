"""
Service for managing Instagram creators with smart caching
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.instagram_creator import InstagramCreator
from app.utils import utcnow_naive
from app.services.storage.s3 import S3Storage
from app.services.instagram.downloader import InstagramDownloader
from app.core.config import settings

logger = logging.getLogger(__name__)

# Cache TTL from config (default 24 hours)
CREATOR_CACHE_TTL = timedelta(hours=getattr(settings, 'CREATOR_CACHE_TTL_HOURS', 24))


class CreatorService:
    """Manages Instagram creator info with smart caching"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.downloader = InstagramDownloader()

    async def get_or_create_creator(self, creator_data: Dict[str, Any]) -> Optional[InstagramCreator]:
        """
        Get creator from DB or create if not exists/stale
        Fetches full profile data from Instagram API to get follower counts

        Args:
            creator_data: Creator data from Instagram post API response

        Returns:
            InstagramCreator object
        """
        instagram_id = creator_data.get('creator_instagram_id', '')
        username = creator_data.get('creator_username', '')

        if not instagram_id or not username:
            logger.warning("Missing required creator fields")
            return None

        # Check if creator exists in DB
        stmt = select(InstagramCreator).where(InstagramCreator.instagram_id == instagram_id)
        result = await self.db.execute(stmt)
        creator = result.scalar_one_or_none()

        # If exists and fresh, return cached
        if creator and self._is_fresh(creator):
            logger.info(f"Using cached Instagram creator info for @{username}")
            return creator

        # Fetch full profile data from API to get follower counts
        profile_data = None
        try:
            logger.info(f"Fetching Instagram profile data for @{username}")
            profile_data = await self.downloader.get_user_profile(username)
        except Exception as e:
            logger.warning(f"Failed to fetch Instagram profile for @{username}: {e}")
            # Continue without profile data - we'll use what we have from post data

        # Merge profile data with creator data
        if profile_data:
            creator_data = {**creator_data, 'profile_data': profile_data}

        # Update or create creator
        if creator:
            logger.info(f"Updating Instagram creator info for @{username}")
            creator = await self._update_creator(creator, creator_data)
        else:
            try:
                logger.info(f"Creating new Instagram creator @{username}")
                creator = await self._create_creator(creator_data)
            except IntegrityError:
                # Race condition: another process created this creator
                # Roll back and fetch the existing creator
                await self.db.rollback()
                logger.info(f"Creator @{username} already exists (race condition), fetching...")
                stmt = select(InstagramCreator).where(InstagramCreator.instagram_id == instagram_id)
                result = await self.db.execute(stmt)
                creator = result.scalar_one_or_none()

                if not creator:
                    raise Exception(f"Failed to get/create creator @{username}")

        return creator

    def _is_fresh(self, creator: InstagramCreator) -> bool:
        """Check if creator data is fresh (< 24 hours old)"""
        if not creator.last_fetched_at:
            return False

        age = utcnow_naive() - creator.last_fetched_at
        return age < CREATOR_CACHE_TTL

    async def _create_creator(self, data: Dict[str, Any]) -> InstagramCreator:
        """Create new creator in DB"""
        # Extract profile stats if available
        profile_data = data.get('profile_data', {})

        # Create creator first to get ID
        creator = InstagramCreator(
            instagram_id=data.get('creator_instagram_id', ''),
            username=data.get('creator_username', ''),
            full_name=data.get('creator_full_name', ''),
            is_verified=data.get('creator_is_verified', False),
            is_private=data.get('creator_is_private', False),
            follower_count=profile_data.get('follower_count', 0),
            following_count=profile_data.get('following_count', 0),
            media_count=profile_data.get('media_count', 0),
            last_fetched_at=utcnow_naive()
        )

        self.db.add(creator)
        await self.db.commit()
        await self.db.refresh(creator)

        # Download and upload profile picture to our storage
        profile_pic_url = data.get('creator_profile_pic_url')
        if profile_pic_url:
            storage = S3Storage()
            creator_id = str(creator.id)

            stored_url = await storage.download_and_upload_url(
                profile_pic_url,
                f"instagram_creators/{creator_id}/profile_pic.jpg",
                "image/jpeg"
            )

            creator.profile_pic_url = stored_url
            await self.db.commit()
            await self.db.refresh(creator)

        logger.info(f"Created new Instagram creator @{creator.username}")
        return creator

    async def _update_creator(self, creator: InstagramCreator, data: Dict[str, Any]) -> InstagramCreator:
        """Update existing creator with fresh data"""
        # Extract profile stats if available
        profile_data = data.get('profile_data', {})

        creator.full_name = data.get('creator_full_name', creator.full_name)
        creator.is_verified = data.get('creator_is_verified', creator.is_verified)
        creator.is_private = data.get('creator_is_private', creator.is_private)

        # Update stats if we fetched profile data
        if profile_data:
            creator.follower_count = profile_data.get('follower_count', creator.follower_count)
            creator.following_count = profile_data.get('following_count', creator.following_count)
            creator.media_count = profile_data.get('media_count', creator.media_count)

        creator.last_fetched_at = utcnow_naive()

        # Download and upload new profile picture to our storage
        profile_pic_url = data.get('creator_profile_pic_url')
        if profile_pic_url:
            storage = S3Storage()
            creator_id = str(creator.id)

            try:
                stored_url = await storage.download_and_upload_url(
                    profile_pic_url,
                    f"instagram_creators/{creator_id}/profile_pic.jpg",
                    "image/jpeg"
                )
                creator.profile_pic_url = stored_url
            except Exception as e:
                logger.warning(f"Failed to update profile picture for @{creator.username}: {e}")

        await self.db.commit()
        await self.db.refresh(creator)

        logger.info(f"Updated Instagram creator @{creator.username}")
        return creator
