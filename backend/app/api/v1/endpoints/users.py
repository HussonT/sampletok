"""
User endpoints for managing user-specific data (downloads, favorites, profile).
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.core.database import get_db
from app.models.user import User
from app.api.deps import get_current_user
from app.services.user_service import UserDownloadService, UserFavoriteService
from app.models.schemas import SampleResponse, UserStatsResponse


router = APIRouter()


@router.get("/me/downloads", response_model=List[SampleResponse])
async def get_my_downloads(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get the authenticated user's download history with full sample metadata.
    Returns empty list for users with no downloads.
    """
    # Get user's downloads with eager-loaded sample data
    downloads = await UserDownloadService.get_user_downloads(
        db=db,
        user_id=current_user.id,
        limit=limit,
        offset=offset
    )

    # Get all favorited sample IDs for this user to efficiently check favorites
    # (avoids N+1 queries)
    from sqlalchemy import select
    from app.models.user import UserFavorite
    favorited_sample_ids_result = await db.execute(
        select(UserFavorite.sample_id).where(UserFavorite.user_id == current_user.id)
    )
    favorited_sample_ids = set(favorited_sample_ids_result.scalars().all())

    # Convert to sample responses
    samples = []
    for download in downloads:
        sample = download.sample
        if sample:
            # Convert sample to response model
            sample_dict = SampleResponse.model_validate(sample).model_dump()
            # Add download-specific metadata
            sample_dict['downloaded_at'] = download.downloaded_at.isoformat()
            sample_dict['download_type'] = download.download_type
            sample_dict['is_downloaded'] = True  # Mark as downloaded for UI
            # Check if this sample is also favorited
            sample_dict['is_favorited'] = sample.id in favorited_sample_ids
            samples.append(SampleResponse(**sample_dict))

    return samples


@router.get("/me/favorites", response_model=List[SampleResponse])
async def get_my_favorites(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get the authenticated user's favorited samples with full sample metadata.
    Returns empty list for users with no favorites.
    """
    # Get user's favorites with eager-loaded sample data
    favorites = await UserFavoriteService.get_user_favorites(
        db=db,
        user_id=current_user.id,
        limit=limit,
        offset=offset
    )

    # Convert to sample responses
    samples = []
    for favorite in favorites:
        sample = favorite.sample
        if sample:
            # Convert sample to response model
            sample_dict = SampleResponse.model_validate(sample).model_dump()
            # Add favorite-specific metadata
            sample_dict['favorited_at'] = favorite.favorited_at.isoformat()
            sample_dict['is_favorited'] = True  # Mark as favorited for UI
            samples.append(SampleResponse(**sample_dict))

    return samples


@router.get("/me/stats", response_model=UserStatsResponse)
async def get_my_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get the authenticated user's statistics for mobile profile page.

    Returns:
    - total_favorites: Number of favorited samples
    - total_downloads: Number of sample downloads (unique samples, not individual file downloads)
    - total_swipes: Number of total interactions (favorites + dismissals)
    - total_sessions: Number of unique days with activity (approximated by unique dates from favorites/downloads/dismissals)
    """
    from sqlalchemy import select, func
    from app.models.user import UserFavorite, UserDownload, SampleDismissal

    # Count total favorites
    favorites_count_result = await db.execute(
        select(func.count(UserFavorite.id)).where(UserFavorite.user_id == current_user.id)
    )
    total_favorites = favorites_count_result.scalar() or 0

    # Count unique downloaded samples (not individual file downloads)
    downloads_count_result = await db.execute(
        select(func.count(func.distinct(UserDownload.sample_id))).where(UserDownload.user_id == current_user.id)
    )
    total_downloads = downloads_count_result.scalar() or 0

    # Count total dismissals
    dismissals_count_result = await db.execute(
        select(func.count(SampleDismissal.id)).where(SampleDismissal.user_id == current_user.id)
    )
    total_dismissals = dismissals_count_result.scalar() or 0

    # Total swipes = favorites + dismissals
    total_swipes = total_favorites + total_dismissals

    # Count unique session days by getting distinct dates from all activity tables
    # We'll use the most recent activity to approximate sessions
    # Get unique dates from favorites
    favorites_dates = await db.execute(
        select(func.date(UserFavorite.favorited_at))
        .where(UserFavorite.user_id == current_user.id)
        .distinct()
    )

    # Get unique dates from downloads
    downloads_dates = await db.execute(
        select(func.date(UserDownload.downloaded_at))
        .where(UserDownload.user_id == current_user.id)
        .distinct()
    )

    # Get unique dates from dismissals
    dismissals_dates = await db.execute(
        select(func.date(SampleDismissal.dismissed_at))
        .where(SampleDismissal.user_id == current_user.id)
        .distinct()
    )

    # Combine all unique dates
    all_dates = set()
    all_dates.update(favorites_dates.scalars().all())
    all_dates.update(downloads_dates.scalars().all())
    all_dates.update(dismissals_dates.scalars().all())
    total_sessions = len(all_dates)

    return UserStatsResponse(
        total_favorites=total_favorites,
        total_downloads=total_downloads,
        total_swipes=total_swipes,
        total_sessions=total_sessions,
        credits=current_user.credits
    )
