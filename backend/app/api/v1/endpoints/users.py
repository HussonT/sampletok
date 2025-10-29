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
from app.models.schemas import SampleResponse


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
