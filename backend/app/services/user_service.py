"""
User service for managing users with Clerk integration.
Includes services for downloads and favorites tracking.
"""

from typing import Optional, List, Dict
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.models.user import User, UserDownload, UserStemDownload, UserFavorite, UserStemFavorite, SampleDismissal
from app.models.sample import Sample
from app.models.stem import Stem
from app.utils import utcnow_naive


async def get_or_create_user_from_clerk(
    db: AsyncSession,
    clerk_user_id: str,
    email: Optional[str] = None,
    username: Optional[str] = None
) -> User:
    """
    Get or create a user from Clerk authentication data.
    Uses Clerk ID as the primary identifier - email and username are optional.

    Args:
        db: Database session
        clerk_user_id: Clerk user ID from the JWT token (required)
        email: Optional user email address
        username: Optional username (will be generated from Clerk ID if not provided)

    Returns:
        User object
    """
    # Try to find existing user by Clerk ID
    result = await db.execute(
        select(User).where(User.clerk_user_id == clerk_user_id)
    )
    user = result.scalar_one_or_none()

    if user:
        # Update email if provided and changed
        if email and user.email != email:
            user.email = email
            await db.commit()
            await db.refresh(user)
        return user

    # User doesn't exist, create new one
    if not username:
        # Generate username from Clerk ID (use last 8 chars for brevity)
        username = f"user_{clerk_user_id[-8:]}"

        # Check if username exists and make it unique if needed
        username_base = username
        counter = 1
        while True:
            result = await db.execute(
                select(User).where(User.username == username)
            )
            if not result.scalar_one_or_none():
                break
            username = f"{username_base}{counter}"
            counter += 1

    user = User(
        clerk_user_id=clerk_user_id,
        email=email,  # Optional - can be None
        username=username,
        hashed_password=None,  # No password for Clerk users
        is_active=True,
        is_superuser=False,
        credits=0  # No free credits - users must subscribe
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    return user


async def get_user_by_clerk_id(
    db: AsyncSession,
    clerk_user_id: str
) -> Optional[User]:
    """
    Get a user by their Clerk user ID.

    Args:
        db: Database session
        clerk_user_id: Clerk user ID

    Returns:
        User object or None if not found
    """
    result = await db.execute(
        select(User).where(User.clerk_user_id == clerk_user_id)
    )
    return result.scalar_one_or_none()


class UserDownloadService:
    """Service for managing user download tracking"""

    @staticmethod
    async def record_download(
        db: AsyncSession,
        user_id: UUID,
        sample_id: UUID,
        download_type: str
    ) -> UserDownload:
        """
        Record a download for a user and increment the sample's download count.

        Args:
            db: Database session
            user_id: User's UUID
            sample_id: Sample's UUID
            download_type: Either 'wav' or 'mp3'

        Returns:
            Created UserDownload record
        """
        # Create download record
        download = UserDownload(
            user_id=user_id,
            sample_id=sample_id,
            download_type=download_type,
            downloaded_at=utcnow_naive()
        )
        db.add(download)

        # Increment sample download count
        stmt = select(Sample).where(Sample.id == sample_id)
        result = await db.execute(stmt)
        sample = result.scalar_one_or_none()

        if sample:
            sample.download_count = (sample.download_count or 0) + 1

        await db.commit()
        await db.refresh(download)

        return download

    @staticmethod
    async def get_user_downloads(
        db: AsyncSession,
        user_id: UUID,
        limit: int = 20,
        offset: int = 0
    ) -> List[UserDownload]:
        """
        Get a user's download history with pagination.

        Args:
            db: Database session
            user_id: User's UUID
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of UserDownload records with sample data eagerly loaded
        """
        from app.models.sample import Sample
        from app.models.tiktok_creator import TikTokCreator

        stmt = (
            select(UserDownload)
            .options(
                selectinload(UserDownload.sample).selectinload(Sample.tiktok_creator)
            )
            .where(UserDownload.user_id == user_id)
            .order_by(UserDownload.downloaded_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await db.execute(stmt)
        downloads = result.scalars().all()

        return list(downloads)

    @staticmethod
    async def check_if_downloaded(
        db: AsyncSession,
        user_id: UUID,
        sample_id: UUID
    ) -> bool:
        """
        Check if a user has downloaded a specific sample.

        Args:
            db: Database session
            user_id: User's UUID
            sample_id: Sample's UUID

        Returns:
            True if user has downloaded this sample, False otherwise
        """
        stmt = select(UserDownload).where(
            and_(
                UserDownload.user_id == user_id,
                UserDownload.sample_id == sample_id
            )
        ).limit(1)
        result = await db.execute(stmt)
        download = result.scalar_one_or_none()

        return download is not None

    @staticmethod
    async def get_download_stats(
        db: AsyncSession,
        user_id: UUID
    ) -> Dict[str, int]:
        """
        Get download statistics for a user.

        Args:
            db: Database session
            user_id: User's UUID

        Returns:
            Dictionary with total, wav_count, and mp3_count
        """
        # Total downloads
        stmt = select(func.count(UserDownload.id)).where(UserDownload.user_id == user_id)
        result = await db.execute(stmt)
        total = result.scalar() or 0

        # WAV downloads
        stmt = select(func.count(UserDownload.id)).where(
            and_(
                UserDownload.user_id == user_id,
                UserDownload.download_type == 'wav'
            )
        )
        result = await db.execute(stmt)
        wav_count = result.scalar() or 0

        # MP3 downloads
        stmt = select(func.count(UserDownload.id)).where(
            and_(
                UserDownload.user_id == user_id,
                UserDownload.download_type == 'mp3'
            )
        )
        result = await db.execute(stmt)
        mp3_count = result.scalar() or 0

        return {
            'total': total,
            'wav_count': wav_count,
            'mp3_count': mp3_count
        }


class UserFavoriteService:
    """Service for managing user favorites"""

    @staticmethod
    async def add_favorite(
        db: AsyncSession,
        user_id: UUID,
        sample_id: UUID
    ) -> UserFavorite:
        """
        Add a sample to user's favorites (idempotent).

        Args:
            db: Database session
            user_id: User's UUID
            sample_id: Sample's UUID

        Returns:
            UserFavorite record (existing or newly created)
        """
        # Check if already favorited
        stmt = select(UserFavorite).where(
            and_(
                UserFavorite.user_id == user_id,
                UserFavorite.sample_id == sample_id
            )
        )
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            return existing

        # Create new favorite
        favorite = UserFavorite(
            user_id=user_id,
            sample_id=sample_id,
            favorited_at=utcnow_naive()
        )
        db.add(favorite)

        try:
            await db.commit()
            await db.refresh(favorite)
            return favorite
        except IntegrityError:
            # Race condition: another request created it
            await db.rollback()
            stmt = select(UserFavorite).where(
                and_(
                    UserFavorite.user_id == user_id,
                    UserFavorite.sample_id == sample_id
                )
            )
            result = await db.execute(stmt)
            return result.scalar_one()

    @staticmethod
    async def remove_favorite(
        db: AsyncSession,
        user_id: UUID,
        sample_id: UUID
    ) -> bool:
        """
        Remove a sample from user's favorites.

        Args:
            db: Database session
            user_id: User's UUID
            sample_id: Sample's UUID

        Returns:
            True if favorite was removed, False if it didn't exist
        """
        stmt = select(UserFavorite).where(
            and_(
                UserFavorite.user_id == user_id,
                UserFavorite.sample_id == sample_id
            )
        )
        result = await db.execute(stmt)
        favorite = result.scalar_one_or_none()

        if favorite:
            await db.delete(favorite)
            await db.commit()
            return True

        return False

    @staticmethod
    async def toggle_favorite(
        db: AsyncSession,
        user_id: UUID,
        sample_id: UUID
    ) -> bool:
        """
        Toggle favorite status for a sample.

        Args:
            db: Database session
            user_id: User's UUID
            sample_id: Sample's UUID

        Returns:
            True if now favorited, False if unfavorited
        """
        stmt = select(UserFavorite).where(
            and_(
                UserFavorite.user_id == user_id,
                UserFavorite.sample_id == sample_id
            )
        )
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            # Remove favorite
            await db.delete(existing)
            await db.commit()
            return False
        else:
            # Add favorite
            await UserFavoriteService.add_favorite(db, user_id, sample_id)
            return True

    @staticmethod
    async def get_user_favorites(
        db: AsyncSession,
        user_id: UUID,
        limit: int = 20,
        offset: int = 0
    ) -> List[UserFavorite]:
        """
        Get a user's favorited samples with pagination.

        Args:
            db: Database session
            user_id: User's UUID
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of UserFavorite records with sample data eagerly loaded
        """
        from app.models.sample import Sample
        from app.models.tiktok_creator import TikTokCreator
        from app.models.instagram_creator import InstagramCreator

        stmt = (
            select(UserFavorite)
            .options(
                selectinload(UserFavorite.sample).selectinload(Sample.tiktok_creator),
                selectinload(UserFavorite.sample).selectinload(Sample.instagram_creator)
            )
            .where(UserFavorite.user_id == user_id)
            .order_by(UserFavorite.favorited_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await db.execute(stmt)
        favorites = result.scalars().all()

        return list(favorites)

    @staticmethod
    async def check_if_favorited(
        db: AsyncSession,
        user_id: UUID,
        sample_id: UUID
    ) -> bool:
        """
        Check if a user has favorited a specific sample.

        Args:
            db: Database session
            user_id: User's UUID
            sample_id: Sample's UUID

        Returns:
            True if user has favorited this sample, False otherwise
        """
        stmt = select(UserFavorite).where(
            and_(
                UserFavorite.user_id == user_id,
                UserFavorite.sample_id == sample_id
            )
        ).limit(1)
        result = await db.execute(stmt)
        favorite = result.scalar_one_or_none()

        return favorite is not None

    @staticmethod
    async def get_favorite_count(
        db: AsyncSession,
        user_id: UUID
    ) -> int:
        """
        Get total number of favorites for a user.

        Args:
            db: Database session
            user_id: User's UUID

        Returns:
            Number of favorited samples
        """
        stmt = select(func.count(UserFavorite.id)).where(UserFavorite.user_id == user_id)
        result = await db.execute(stmt)
        count = result.scalar() or 0

        return count


class UserStemFavoriteService:
    """Service for managing user stem favorites"""

    @staticmethod
    async def add_favorite(
        db: AsyncSession,
        user_id: UUID,
        stem_id: UUID
    ) -> UserStemFavorite:
        """
        Add a stem to user's favorites (idempotent).

        Args:
            db: Database session
            user_id: User's UUID
            stem_id: Stem's UUID

        Returns:
            UserStemFavorite record (existing or newly created)
        """
        # Check if already favorited
        stmt = select(UserStemFavorite).where(
            and_(
                UserStemFavorite.user_id == user_id,
                UserStemFavorite.stem_id == stem_id
            )
        )
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            return existing

        # Create new favorite
        favorite = UserStemFavorite(
            user_id=user_id,
            stem_id=stem_id,
            favorited_at=utcnow_naive()
        )
        db.add(favorite)

        try:
            await db.commit()
            await db.refresh(favorite)
            return favorite
        except IntegrityError:
            # Race condition: another request created it
            await db.rollback()
            stmt = select(UserStemFavorite).where(
                and_(
                    UserStemFavorite.user_id == user_id,
                    UserStemFavorite.stem_id == stem_id
                )
            )
            result = await db.execute(stmt)
            return result.scalar_one()

    @staticmethod
    async def remove_favorite(
        db: AsyncSession,
        user_id: UUID,
        stem_id: UUID
    ) -> bool:
        """
        Remove a stem from user's favorites.

        Args:
            db: Database session
            user_id: User's UUID
            stem_id: Stem's UUID

        Returns:
            True if favorite was removed, False if it didn't exist
        """
        stmt = select(UserStemFavorite).where(
            and_(
                UserStemFavorite.user_id == user_id,
                UserStemFavorite.stem_id == stem_id
            )
        )
        result = await db.execute(stmt)
        favorite = result.scalar_one_or_none()

        if favorite:
            await db.delete(favorite)
            await db.commit()
            return True

        return False

    @staticmethod
    async def check_if_favorited(
        db: AsyncSession,
        user_id: UUID,
        stem_id: UUID
    ) -> bool:
        """
        Check if a user has favorited a specific stem.

        Args:
            db: Database session
            user_id: User's UUID
            stem_id: Stem's UUID

        Returns:
            True if user has favorited this stem, False otherwise
        """
        stmt = select(UserStemFavorite).where(
            and_(
                UserStemFavorite.user_id == user_id,
                UserStemFavorite.stem_id == stem_id
            )
        ).limit(1)
        result = await db.execute(stmt)
        favorite = result.scalar_one_or_none()

        return favorite is not None


class UserStemDownloadService:
    """Service for managing user stem download tracking"""

    @staticmethod
    async def record_download(
        db: AsyncSession,
        user_id: UUID,
        stem_id: UUID,
        download_type: str
    ) -> UserStemDownload:
        """
        Record a download for a user and increment the stem's download count.

        Args:
            db: Database session
            user_id: User's UUID
            stem_id: Stem's UUID
            download_type: Either 'wav' or 'mp3'

        Returns:
            Created UserStemDownload record
        """
        # Create download record
        download = UserStemDownload(
            user_id=user_id,
            stem_id=stem_id,
            download_type=download_type,
            downloaded_at=utcnow_naive()
        )
        db.add(download)

        # Increment stem download count
        stmt = select(Stem).where(Stem.id == stem_id)
        result = await db.execute(stmt)
        stem = result.scalar_one_or_none()

        if stem:
            stem.download_count = (stem.download_count or 0) + 1

        await db.commit()
        await db.refresh(download)

        return download

    @staticmethod
    async def get_user_downloads(
        db: AsyncSession,
        user_id: UUID,
        limit: int = 20,
        offset: int = 0
    ) -> List[UserStemDownload]:
        """
        Get a user's stem download history with pagination.

        Args:
            db: Database session
            user_id: User's UUID
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of UserStemDownload records with stem data eagerly loaded
        """
        stmt = (
            select(UserStemDownload)
            .options(
                selectinload(UserStemDownload.stem).selectinload(Stem.parent_sample)
            )
            .where(UserStemDownload.user_id == user_id)
            .order_by(UserStemDownload.downloaded_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await db.execute(stmt)
        downloads = result.scalars().all()

        return list(downloads)

    @staticmethod
    async def check_if_downloaded(
        db: AsyncSession,
        user_id: UUID,
        stem_id: UUID
    ) -> bool:
        """
        Check if a user has downloaded a specific stem.

        Args:
            db: Database session
            user_id: User's UUID
            stem_id: Stem's UUID

        Returns:
            True if user has downloaded this stem, False otherwise
        """
        stmt = select(UserStemDownload).where(
            and_(
                UserStemDownload.user_id == user_id,
                UserStemDownload.stem_id == stem_id
            )
        ).limit(1)
        result = await db.execute(stmt)
        download = result.scalar_one_or_none()

        return download is not None

    @staticmethod
    async def get_download_stats(
        db: AsyncSession,
        user_id: UUID
    ) -> Dict[str, int]:
        """
        Get stem download statistics for a user.

        Args:
            db: Database session
            user_id: User's UUID

        Returns:
            Dictionary with total, wav_count, and mp3_count
        """
        # Total downloads
        stmt = select(func.count(UserStemDownload.id)).where(UserStemDownload.user_id == user_id)
        result = await db.execute(stmt)
        total = result.scalar() or 0

        # WAV downloads
        stmt = select(func.count(UserStemDownload.id)).where(
            and_(
                UserStemDownload.user_id == user_id,
                UserStemDownload.download_type == 'wav'
            )
        )
        result = await db.execute(stmt)
        wav_count = result.scalar() or 0

        # MP3 downloads
        stmt = select(func.count(UserStemDownload.id)).where(
            and_(
                UserStemDownload.user_id == user_id,
                UserStemDownload.download_type == 'mp3'
            )
        )
        result = await db.execute(stmt)
        mp3_count = result.scalar() or 0

        return {
            'total': total,
            'wav_count': wav_count,
            'mp3_count': mp3_count
        }

class SampleDismissalService:
    """Service for managing sample dismissals for personalized mobile feed"""

    @staticmethod
    async def add_dismissal(
        db: AsyncSession,
        user_id: UUID,
        sample_id: UUID
    ) -> SampleDismissal:
        """
        Add a sample to user's dismissals (idempotent).

        Args:
            db: Database session
            user_id: User's UUID
            sample_id: Sample's UUID

        Returns:
            SampleDismissal record (existing or newly created)
        """
        # Check if already dismissed
        stmt = select(SampleDismissal).where(
            and_(
                SampleDismissal.user_id == user_id,
                SampleDismissal.sample_id == sample_id
            )
        )
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            return existing

        # Create new dismissal
        dismissal = SampleDismissal(
            user_id=user_id,
            sample_id=sample_id,
            dismissed_at=utcnow_naive()
        )
        db.add(dismissal)

        try:
            await db.commit()
            await db.refresh(dismissal)
            return dismissal
        except IntegrityError:
            # Race condition: another request created it
            await db.rollback()
            stmt = select(SampleDismissal).where(
                and_(
                    SampleDismissal.user_id == user_id,
                    SampleDismissal.sample_id == sample_id
                )
            )
            result = await db.execute(stmt)
            return result.scalar_one()

    @staticmethod
    async def remove_dismissal(
        db: AsyncSession,
        user_id: UUID,
        sample_id: UUID
    ) -> bool:
        """
        Remove a sample from user's dismissals.

        Args:
            db: Database session
            user_id: User's UUID
            sample_id: Sample's UUID

        Returns:
            True if dismissal was removed, False if it didn't exist
        """
        stmt = select(SampleDismissal).where(
            and_(
                SampleDismissal.user_id == user_id,
                SampleDismissal.sample_id == sample_id
            )
        )
        result = await db.execute(stmt)
        dismissal = result.scalar_one_or_none()

        if dismissal:
            await db.delete(dismissal)
            await db.commit()
            return True

        return False

    @staticmethod
    async def check_if_dismissed(
        db: AsyncSession,
        user_id: UUID,
        sample_id: UUID
    ) -> bool:
        """
        Check if a user has dismissed a specific sample.

        Args:
            db: Database session
            user_id: User's UUID
            sample_id: Sample's UUID

        Returns:
            True if user has dismissed this sample, False otherwise
        """
        stmt = select(SampleDismissal).where(
            and_(
                SampleDismissal.user_id == user_id,
                SampleDismissal.sample_id == sample_id
            )
        ).limit(1)
        result = await db.execute(stmt)
        dismissal = result.scalar_one_or_none()

        return dismissal is not None

    @staticmethod
    async def batch_add_dismissals(
        db: AsyncSession,
        user_id: UUID,
        sample_ids: List[UUID]
    ) -> int:
        """
        Batch add multiple dismissals for guest data sync.
        Skips duplicates gracefully.

        Args:
            db: Database session
            user_id: User's UUID
            sample_ids: List of sample UUIDs to dismiss

        Returns:
            Number of dismissals actually created (excluding duplicates)
        """
        created_count = 0

        for sample_id in sample_ids:
            # Check if already dismissed
            stmt = select(SampleDismissal).where(
                and_(
                    SampleDismissal.user_id == user_id,
                    SampleDismissal.sample_id == sample_id
                )
            )
            result = await db.execute(stmt)
            existing = result.scalar_one_or_none()

            if not existing:
                dismissal = SampleDismissal(
                    user_id=user_id,
                    sample_id=sample_id,
                    dismissed_at=utcnow_naive()
                )
                db.add(dismissal)
                created_count += 1

        try:
            await db.commit()
        except IntegrityError:
            # Handle race conditions - some may have been created concurrently
            await db.rollback()
            # Don't fail, just return the count we attempted
            pass

        return created_count
