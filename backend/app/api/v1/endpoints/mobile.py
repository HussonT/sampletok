"""
Mobile API endpoints for swipe-based sample discovery.

Provides:
- Personalized feed excluding favorited/dismissed samples
- Batch sync endpoint for guest data migration
"""

from fastapi import APIRouter, Depends, Query, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel

from app.core.database import get_db
from app.core.rate_limit import limiter
from app.core.config import settings
from app.models import Sample, ProcessingStatus
from app.models.user import User, UserFavorite, SampleDismissal
from app.models.schemas import SampleResponse, PaginatedResponse
from app.api.deps import get_current_user, get_current_user_optional
from app.services.user_service import UserFavoriteService, SampleDismissalService
from app.api.v1.endpoints.samples import enrich_samples_with_user_data
from app.utils.datetime import utcnow_naive

router = APIRouter()


class BatchSyncRequest(BaseModel):
    """Request model for batch syncing guest data"""
    favorited_sample_ids: List[UUID] = []
    dismissed_sample_ids: List[UUID] = []


class BatchSyncResponse(BaseModel):
    """Response model for batch sync"""
    favorites_synced: int
    dismissals_synced: int
    message: str


@router.get("/feed", response_model=PaginatedResponse)
@limiter.limit(f"{settings.MOBILE_FEED_RATE_LIMIT_PER_MINUTE}/minute")
async def get_mobile_feed(
    request: Request,
    limit: int = Query(10, ge=1, le=20, description="Number of samples to return"),
    skip: int = Query(0, ge=0, description="Number of samples to skip"),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """
    Get personalized mobile feed for swipe-based discovery.

    - Excludes samples user has favorited
    - Excludes samples user has dismissed
    - Returns randomized order for discovery
    - Works for both authenticated and guest users

    For authenticated users: excludes their favorites and dismissals
    For guest users: returns random samples (guests track locally)
    """
    # Base query - only completed, playable samples
    query = select(Sample).where(
        # Must have essential metadata
        Sample.creator_username.isnot(None),
        Sample.creator_username != '',
        Sample.title.isnot(None),
        Sample.title != '',
        # Must have playable audio file
        Sample.audio_url_mp3.isnot(None),
        Sample.audio_url_mp3 != '',
        # Must have waveform for UI display
        Sample.waveform_url.isnot(None),
        Sample.waveform_url != '',
        # Must have video for mobile feed
        Sample.video_url.isnot(None),
        Sample.video_url != '',
        # Only completed samples
        Sample.status == ProcessingStatus.COMPLETED
    )

    # Exclude favorited and dismissed samples for authenticated users
    if current_user:
        # Get user's favorited sample IDs
        favorites_stmt = select(UserFavorite.sample_id).where(
            UserFavorite.user_id == current_user.id
        )
        favorites_result = await db.execute(favorites_stmt)
        favorited_ids = [row[0] for row in favorites_result]

        # Get user's dismissed sample IDs
        dismissals_stmt = select(SampleDismissal.sample_id).where(
            SampleDismissal.user_id == current_user.id
        )
        dismissals_result = await db.execute(dismissals_stmt)
        dismissed_ids = [row[0] for row in dismissals_result]

        # Exclude both favorited and dismissed samples
        excluded_ids = favorited_ids + dismissed_ids
        if excluded_ids:
            query = query.where(Sample.id.not_in(excluded_ids))

    # Randomize order for discovery (using PostgreSQL RANDOM())
    query = query.order_by(func.random())

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    result = await db.execute(count_query)
    total = result.scalar_one()

    # Apply pagination and eager load creators
    query = query.options(
        selectinload(Sample.tiktok_creator),
        selectinload(Sample.instagram_creator)
    ).offset(skip).limit(limit)

    # Execute query
    result = await db.execute(query)
    samples = result.scalars().all()

    # Enrich with user-specific data (favorites, downloads)
    items = await enrich_samples_with_user_data(samples, current_user, db)

    return PaginatedResponse(
        items=items,
        total=total,
        skip=skip,
        limit=limit,
        has_more=(skip + limit) < total,
        next_cursor=None
    )


@router.post("/sync", response_model=BatchSyncResponse)
@limiter.limit(f"{settings.MOBILE_SYNC_RATE_LIMIT_PER_MINUTE}/minute")
async def batch_sync_guest_data(
    request: Request,
    sync_data: BatchSyncRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Batch sync guest favorites and dismissals to user account after login.

    This endpoint allows the frontend to migrate localStorage data
    to the authenticated user's account in a single API call.

    - Accepts arrays of favorited and dismissed sample IDs
    - Bulk inserts into database
    - Ignores duplicates gracefully (idempotent)
    - Returns count of successfully synced items

    Example request:
    ```json
    {
        "favorited_sample_ids": ["uuid1", "uuid2"],
        "dismissed_sample_ids": ["uuid3", "uuid4"]
    }
    ```
    """
    favorites_synced = 0
    dismissals_synced = 0

    # Batch add favorites - optimized to avoid N+1 queries
    if sync_data.favorited_sample_ids:
        # Single query: Verify all samples exist
        valid_samples_query = select(Sample.id).where(
            Sample.id.in_(sync_data.favorited_sample_ids)
        )
        valid_samples_result = await db.execute(valid_samples_query)
        valid_sample_ids = set(valid_samples_result.scalars().all())

        # Single query: Get existing favorites
        existing_favorites_query = select(UserFavorite.sample_id).where(
            and_(
                UserFavorite.user_id == current_user.id,
                UserFavorite.sample_id.in_(valid_sample_ids)
            )
        )
        existing_favorites_result = await db.execute(existing_favorites_query)
        existing_favorite_ids = set(existing_favorites_result.scalars().all())

        # Calculate which samples need new favorites
        new_favorite_ids = valid_sample_ids - existing_favorite_ids

        # Batch insert new favorites
        if new_favorite_ids:
            new_favorites = [
                UserFavorite(
                    user_id=current_user.id,
                    sample_id=sample_id,
                    favorited_at=utcnow_naive()
                )
                for sample_id in new_favorite_ids
            ]
            db.add_all(new_favorites)
            favorites_synced = len(new_favorite_ids)

    # Batch add dismissals
    if sync_data.dismissed_sample_ids:
        dismissals_synced = await SampleDismissalService.batch_add_dismissals(
            db=db,
            user_id=current_user.id,
            sample_ids=sync_data.dismissed_sample_ids
        )

    return BatchSyncResponse(
        favorites_synced=favorites_synced,
        dismissals_synced=dismissals_synced,
        message=f"Successfully synced {favorites_synced} favorites and {dismissals_synced} dismissals"
    )
