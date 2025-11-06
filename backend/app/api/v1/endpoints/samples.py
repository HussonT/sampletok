from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, Body
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, text, cast, String
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import selectinload
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel
import httpx
import inngest
import asyncio
import logging
import time

from app.core.database import get_db, AsyncSessionLocal
from app.models import Sample, ProcessingStatus
from app.models.user import User, UserDownload, UserFavorite
from app.models.schemas import (
    SampleResponse,
    SampleUpdate,
    PaginatedResponse,
    PaginationParams,
    ReprocessRequest,
    ReprocessResponse,
    SampleSearchParams,
    SampleSearchResponse
)
from app.api.deps import get_current_user, get_current_user_optional
from app.services.user_service import UserDownloadService, UserFavoriteService

# TODO: Add rate limiting to download endpoints to prevent abuse (e.g., max 100 downloads per hour per user)

logger = logging.getLogger(__name__)

router = APIRouter()


def escape_like_pattern(pattern: str) -> str:
    """
    Escape special LIKE/ILIKE pattern characters to prevent SQL injection.

    PostgreSQL LIKE patterns use:
    - % to match any sequence of characters
    - _ to match any single character
    - \ as escape character

    This function escapes these characters so they're treated as literals.

    Example:
        escape_like_pattern("test%") -> "test\\%"
        escape_like_pattern("a_b") -> "a\\_b"
    """
    return pattern.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')


# Request/Response models
class DownloadRequest(BaseModel):
    download_type: str  # "wav" or "mp3"


class FavoriteResponse(BaseModel):
    is_favorited: bool
    favorited_at: Optional[str] = None


async def enrich_samples_with_user_data(
    samples: List[Sample],
    user: Optional[User],
    db: AsyncSession
) -> List[SampleResponse]:
    """
    Convert samples to SampleResponse with user-specific fields (is_favorited, is_downloaded).
    If user is None, these fields remain null.
    """
    if not user:
        # No user, return samples as-is without user-specific data
        return [SampleResponse.model_validate(sample) for sample in samples]

    # Get all sample IDs
    sample_ids = [sample.id for sample in samples]

    # Batch query for favorites
    favorites_stmt = select(UserFavorite.sample_id, UserFavorite.favorited_at).where(
        and_(
            UserFavorite.user_id == user.id,
            UserFavorite.sample_id.in_(sample_ids)
        )
    )
    favorites_result = await db.execute(favorites_stmt)
    favorites_map = {row[0]: row[1] for row in favorites_result}

    # Batch query for downloads (get most recent download for each sample)
    from sqlalchemy import distinct
    downloads_stmt = select(
        UserDownload.sample_id,
        UserDownload.downloaded_at,
        UserDownload.download_type
    ).where(
        and_(
            UserDownload.user_id == user.id,
            UserDownload.sample_id.in_(sample_ids)
        )
    ).order_by(UserDownload.downloaded_at.desc())
    downloads_result = await db.execute(downloads_stmt)
    downloads_map = {}
    for row in downloads_result:
        sample_id = row[0]
        if sample_id not in downloads_map:  # Only keep most recent
            downloads_map[sample_id] = (row[1], row[2])

    # Build responses with user-specific data
    responses = []
    for sample in samples:
        sample_dict = SampleResponse.model_validate(sample).model_dump()

        # Add favorite data
        if sample.id in favorites_map:
            sample_dict['is_favorited'] = True
            sample_dict['favorited_at'] = favorites_map[sample.id].isoformat()
        else:
            sample_dict['is_favorited'] = False

        # Add download data
        if sample.id in downloads_map:
            sample_dict['is_downloaded'] = True
            sample_dict['downloaded_at'] = downloads_map[sample.id][0].isoformat()
            sample_dict['download_type'] = downloads_map[sample.id][1]
        else:
            sample_dict['is_downloaded'] = False

        responses.append(SampleResponse(**sample_dict))

    return responses


@router.get("/", response_model=PaginatedResponse)
async def get_samples(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=20),
    genre: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    bpm_min: Optional[int] = Query(None, ge=0, le=300),
    bpm_max: Optional[int] = Query(None, ge=0, le=300),
    key: Optional[str] = Query(None, max_length=20),
    tags: Optional[str] = Query(None, max_length=500),
    sort_by: Optional[str] = Query("created_at_desc", description="Sort order: created_at_desc, created_at_asc, views_desc, bpm_asc, bpm_desc"),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """
    V3 Search endpoint - Text search with BPM, Key, and Tag filtering

    - Full-text search using PostgreSQL tsvector
    - BPM range filtering
    - Musical key filtering
    - Tag filtering (OR logic - any tag matches)
    - Sorted by relevance (if search) or created_at/views/bpm
    - Includes user-specific fields (is_favorited, is_downloaded) when authenticated
    """
    start_time = time.time()

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
        Sample.waveform_url != ''
    )

    # Apply status filter - default to COMPLETED only
    if status:
        try:
            status_enum = ProcessingStatus[status.upper()]
            query = query.where(Sample.status == status_enum)
        except KeyError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    else:
        # By default, only show completed samples
        query = query.where(Sample.status == ProcessingStatus.COMPLETED)

    if genre:
        query = query.where(Sample.genre == genre)

    # BPM range filter
    if bpm_min is not None:
        query = query.where(Sample.bpm >= bpm_min)
    if bpm_max is not None:
        query = query.where(Sample.bpm <= bpm_max)

    # Key filter
    if key:
        query = query.where(Sample.key == key)

    # Tag filter (OR logic - any tag matches)
    # Note: Validation is handled by SampleSearchParams Pydantic schema
    if tags:
        # Parse tags (already validated and normalized by Pydantic schema)
        tag_list = [t.strip().lower() for t in tags.split(",") if t.strip()]

        # Use JSONB ?| operator: checks if any of the array elements exist
        query = query.where(
            Sample.tags.op('?|')(cast(tag_list, ARRAY(String)))
        )

    # Full-text search with PostgreSQL tsvector
    if search:
        # Convert search query to tsquery
        ts_query = func.plainto_tsquery('english', search)

        # Escape LIKE pattern special characters to prevent SQL injection
        escaped_search = escape_like_pattern(search)

        # Filter by tsvector match OR partial username match
        # This allows searching for creator names like "lucy" matching "lucyparkmusic"
        query = query.where(
            or_(
                Sample.search_vector.op('@@')(ts_query),
                Sample.creator_username.ilike(f'%{escaped_search}%')
            )
        )

        # Sort by relevance when searching (prioritize exact username matches)
        escaped_search_lower = escape_like_pattern(search.lower())
        query = query.order_by(
            # First: exact username matches
            func.lower(Sample.creator_username).like(f'%{escaped_search_lower}%').desc(),
            # Then: full-text search relevance
            func.ts_rank(Sample.search_vector, ts_query).desc()
        )
    else:
        # Apply sorting when not searching
        if sort_by == "created_at_desc":
            query = query.order_by(Sample.created_at.desc())
        elif sort_by == "created_at_asc":
            query = query.order_by(Sample.created_at.asc())
        elif sort_by == "views_desc":
            query = query.order_by(Sample.view_count.desc())
        elif sort_by == "bpm_asc":
            query = query.order_by(Sample.bpm.asc())
        elif sort_by == "bpm_desc":
            query = query.order_by(Sample.bpm.desc())
        else:
            query = query.order_by(Sample.created_at.desc())

    # Get total count with timeout
    count_query = select(func.count()).select_from(query.subquery())
    try:
        result = await asyncio.wait_for(
            db.execute(count_query),
            timeout=5.0
        )
        total = result.scalar_one()
    except asyncio.TimeoutError:
        logger.error("Count query timeout", extra={"search": search, "tags": tags})
        raise HTTPException(
            status_code=504,
            detail="Database query took too long while counting results. Try using more specific filters or a shorter search term."
        )

    # Apply pagination and eager load creator
    query = query.options(selectinload(Sample.tiktok_creator)).offset(skip).limit(limit)

    # Execute main query with timeout
    try:
        result = await asyncio.wait_for(
            db.execute(query),
            timeout=5.0
        )
        samples = result.scalars().all()
    except asyncio.TimeoutError:
        logger.error("Search query timeout", extra={"search": search, "tags": tags, "limit": limit})
        raise HTTPException(
            status_code=504,
            detail="Database query took too long while fetching results. Try using more specific filters or a shorter search term."
        )

    # Enrich with user-specific data (favorites, downloads)
    items = await enrich_samples_with_user_data(samples, current_user, db)

    # Log slow queries
    query_time = time.time() - start_time
    if query_time > 1.0:
        logger.warning(
            f"Slow search query: {query_time:.2f}s",
            extra={"search": search, "duration": query_time}
        )

    return PaginatedResponse(
        items=items,
        total=total,
        skip=skip,
        limit=limit,
        has_more=(skip + limit) < total,
        next_cursor=None
    )


@router.get("/tags/popular", response_model=List[dict])
async def get_popular_tags(
    limit: int = Query(50, ge=1, le=100, description="Maximum number of tags to return"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get most popular tags across all samples
    Returns list of {tag: str, count: int}

    Performance note: This query uses jsonb_array_elements_text() which expands
    all tag arrays. At scale (>10K samples), consider:
    - Denormalized sample_tags table with indexes
    - Materialized view refreshed hourly
    - Redis caching with 5-minute TTL
    """
    start_time = time.time()

    try:
        query = select(
            func.jsonb_array_elements_text(Sample.tags).label('tag'),
            func.count().label('count')
        ).where(
            Sample.status == ProcessingStatus.COMPLETED
        ).group_by('tag').order_by(text('count DESC')).limit(limit)

        result = await asyncio.wait_for(
            db.execute(query),
            timeout=3.0
        )

        query_time = time.time() - start_time

        # Log performance metrics
        if query_time > 1.0:
            logger.warning(
                f"Slow popular tags query: {query_time:.2f}s - Consider implementing caching or denormalization",
                extra={"duration": query_time, "limit": limit}
            )
        else:
            logger.debug(f"Popular tags query completed in {query_time:.2f}s")

        return [{"tag": row.tag, "count": row.count} for row in result]
    except asyncio.TimeoutError:
        query_time = time.time() - start_time
        logger.error(
            f"Popular tags query timeout after {query_time:.2f}s - Consider implementing caching or denormalization",
            extra={"duration": query_time, "limit": limit}
        )
        return []  # Return empty on timeout


@router.get("/{sample_id}", response_model=SampleResponse)
async def get_sample(
    sample_id: UUID,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific sample by ID.
    Includes user-specific fields (is_favorited, is_downloaded) when authenticated.
    """
    query = select(Sample).options(selectinload(Sample.tiktok_creator)).where(Sample.id == sample_id)
    result = await db.execute(query)
    sample = result.scalar_one_or_none()

    if not sample:
        raise HTTPException(status_code=404, detail="Sample not found")

    # Enrich with user-specific data
    enriched_samples = await enrich_samples_with_user_data([sample], current_user, db)

    return enriched_samples[0]


@router.patch("/{sample_id}", response_model=SampleResponse)
async def update_sample(
    sample_id: UUID,
    sample_update: SampleUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update a sample's metadata"""
    query = select(Sample).where(Sample.id == sample_id)
    result = await db.execute(query)
    sample = result.scalar_one_or_none()

    if not sample:
        raise HTTPException(status_code=404, detail="Sample not found")

    # Update fields
    update_data = sample_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(sample, field, value)

    await db.commit()
    await db.refresh(sample)

    return SampleResponse.model_validate(sample)


@router.delete("/{sample_id}")
async def delete_sample(
    sample_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Delete a sample"""
    query = select(Sample).where(Sample.id == sample_id)
    result = await db.execute(query)
    sample = result.scalar_one_or_none()

    if not sample:
        raise HTTPException(status_code=404, detail="Sample not found")

    await db.delete(sample)
    await db.commit()

    return {"message": "Sample deleted successfully"}


@router.post("/{sample_id}/download")
async def download_sample(
    sample_id: UUID,
    request: DownloadRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Download a sample audio file (WAV or MP3) - requires authentication, active subscription, and 1 credit.
    Records the download in user history and increments download count.
    Deducts 1 credit from user account.
    """
    # Validate download_type
    if request.download_type not in ["wav", "mp3"]:
        raise HTTPException(
            status_code=400,
            detail="download_type must be 'wav' or 'mp3'"
        )

    # Get sample with TikTok creator relationship
    from sqlalchemy.orm import selectinload
    query = (
        select(Sample)
        .where(Sample.id == sample_id)
        .options(selectinload(Sample.tiktok_creator))
    )
    result = await db.execute(query)
    sample = result.scalar_one_or_none()

    if not sample:
        raise HTTPException(status_code=404, detail="Sample not found")

    # Check if user has already downloaded this sample (any format)
    has_downloaded = await UserDownloadService.check_if_downloaded(
        db=db,
        user_id=current_user.id,
        sample_id=sample_id
    )

    # Only deduct credits for first-time downloads
    if not has_downloaded:
        # Check if user has active subscription
        await db.refresh(current_user, ["subscription"])
        if not current_user.subscription or not current_user.subscription.is_active:
            raise HTTPException(
                status_code=403,
                detail="Active subscription required to download samples. Please subscribe at /pricing"
            )

        # Check if user has sufficient credits (need 1 credit for download)
        if current_user.credits < 1:
            raise HTTPException(
                status_code=403,
                detail=f"Insufficient credits. You need 1 credit to download but have {current_user.credits}. Purchase a top-up at /top-up"
            )

        # Deduct 1 credit atomically
        from app.services.credit_service import CreditService
        credit_service = CreditService(db)
        success = await credit_service.deduct_credits_atomic(
            user_id=current_user.id,
            credits_needed=1,
            transaction_type="sample_download",
            description=f"Downloaded {request.download_type.upper()} sample: {sample.creator_username or 'unknown'}",
            sample_id=sample_id
        )

        if not success:
            raise HTTPException(
                status_code=403,
                detail="Failed to deduct credits. Please try again or contact support."
            )

    # Get appropriate audio URL
    if request.download_type == "wav":
        audio_url = sample.audio_url_wav
        media_type = "audio/wav"
        extension = "wav"
    else:  # mp3
        audio_url = sample.audio_url_mp3
        media_type = "audio/mpeg"
        extension = "mp3"

    if not audio_url:
        raise HTTPException(
            status_code=404,
            detail=f"No {request.download_type.upper()} audio file available for this sample"
        )

    # Record download in database (also increments sample.download_count)
    try:
        await UserDownloadService.record_download(
            db=db,
            user_id=current_user.id,
            sample_id=sample_id,
            download_type=request.download_type
        )
    except Exception as e:
        logger.error(f"Failed to record download: {e}")
        # Continue with download even if recording fails

    # Fetch the file from the remote URL
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(audio_url, follow_redirects=True)
            response.raise_for_status()
        except httpx.HTTPError as e:
            raise HTTPException(status_code=500, detail=f"Failed to fetch audio file: {str(e)}")

    # Generate filename: {bpm}bpm_{key}_{artist_username}_sample.{extension}
    bpm = sample.bpm or "unknown"
    key = sample.key or "unknown"

    # Get artist username from TikTok creator or fall back to creator_username field
    if sample.tiktok_creator:
        artist_username = sample.tiktok_creator.username
    elif sample.creator_username:
        artist_username = sample.creator_username
    else:
        artist_username = "unknown"

    # Sanitize username for filename (remove special characters)
    import re
    artist_username = re.sub(r'[^\w\-_]', '_', artist_username)

    filename = f"{bpm}bpm_{key}_{artist_username}_sample.{extension}"

    # Return as streaming response with download headers
    return StreamingResponse(
        iter([response.content]),
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


@router.post("/{sample_id}/download-video")
async def download_video(
    sample_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Download the TikTok video file - requires authentication, active subscription, and 1 credit.
    Records the download in user history and increments download count.
    Deducts 1 credit from user account.
    """
    # Get sample with TikTok creator relationship
    from sqlalchemy.orm import selectinload
    query = (
        select(Sample)
        .where(Sample.id == sample_id)
        .options(selectinload(Sample.tiktok_creator))
    )
    result = await db.execute(query)
    sample = result.scalar_one_or_none()

    if not sample:
        raise HTTPException(status_code=404, detail="Sample not found")

    # Check if user has already downloaded this sample (any format)
    has_downloaded = await UserDownloadService.check_if_downloaded(
        db=db,
        user_id=current_user.id,
        sample_id=sample_id
    )

    # Only deduct credits for first-time downloads
    if not has_downloaded:
        # Check if user has active subscription
        await db.refresh(current_user, ["subscription"])
        if not current_user.subscription or not current_user.subscription.is_active:
            raise HTTPException(
                status_code=403,
                detail="Active subscription required to download videos. Please subscribe at /pricing"
            )

        # Check if user has sufficient credits (need 1 credit for download)
        if current_user.credits < 1:
            raise HTTPException(
                status_code=403,
                detail=f"Insufficient credits. You need 1 credit to download but have {current_user.credits}. Purchase a top-up at /top-up"
            )

        # Deduct 1 credit atomically
        from app.services.credit_service import CreditService
        credit_service = CreditService(db)
        success = await credit_service.deduct_credits_atomic(
            user_id=current_user.id,
            credits_needed=1,
            transaction_type="video_download",
            description=f"Downloaded video: {sample.creator_username or 'unknown'}",
            sample_id=sample_id
        )

        if not success:
            raise HTTPException(
                status_code=403,
                detail="Failed to deduct credits. Please try again or contact support."
            )

    # Get video URL from our storage
    video_url = sample.video_url
    if not video_url:
        raise HTTPException(status_code=404, detail="No video file available for this sample")

    # Record download in database (also increments sample.download_count)
    try:
        await UserDownloadService.record_download(
            db=db,
            user_id=current_user.id,
            sample_id=sample_id,
            download_type="video"
        )
    except Exception as e:
        logger.error(f"Failed to record video download: {e}")
        # Continue with download even if recording fails

    # Fetch the file from our storage
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(video_url, follow_redirects=True)
            response.raise_for_status()
        except httpx.HTTPError as e:
            raise HTTPException(status_code=500, detail=f"Failed to fetch video file: {str(e)}")

    # Generate filename: {bpm}bpm_{key}_{artist_username}_video.mp4
    bpm = sample.bpm or "unknown"
    key = sample.key or "unknown"

    # Get artist username from TikTok creator or fall back to creator_username field
    if sample.tiktok_creator:
        artist_username = sample.tiktok_creator.username
    elif sample.creator_username:
        artist_username = sample.creator_username
    else:
        artist_username = "unknown"

    # Sanitize username for filename (remove special characters)
    import re
    artist_username = re.sub(r'[^\w\-_]', '_', artist_username)

    filename = f"{bpm}bpm_{key}_{artist_username}_video.mp4"

    # Return as streaming response with download headers
    return StreamingResponse(
        iter([response.content]),
        media_type="video/mp4",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


@router.post("/{sample_id}/favorite", response_model=FavoriteResponse)
async def add_favorite(
    sample_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Add a sample to user's favorites - requires authentication.
    Idempotent: returns success even if already favorited.
    """
    # Verify sample exists
    query = select(Sample).where(Sample.id == sample_id)
    result = await db.execute(query)
    sample = result.scalar_one_or_none()

    if not sample:
        raise HTTPException(status_code=404, detail="Sample not found")

    # Add to favorites (idempotent)
    favorite = await UserFavoriteService.add_favorite(
        db=db,
        user_id=current_user.id,
        sample_id=sample_id
    )

    return FavoriteResponse(
        is_favorited=True,
        favorited_at=favorite.favorited_at.isoformat()
    )


@router.delete("/{sample_id}/favorite", status_code=204)
async def remove_favorite(
    sample_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Remove a sample from user's favorites - requires authentication.
    Idempotent: returns success even if not favorited.
    """
    # Remove from favorites (idempotent)
    await UserFavoriteService.remove_favorite(
        db=db,
        user_id=current_user.id,
        sample_id=sample_id
    )

    return None  # 204 No Content


async def check_url_has_content(url: Optional[str], timeout: int = 10) -> bool:
    """
    Check if a URL exists and has actual content behind it.
    Returns True if URL has valid content, False otherwise.
    """
    if not url:
        return False

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            # Use HEAD request first for efficiency
            response = await client.head(url, follow_redirects=True)

            # Check if response is successful
            if response.status_code != 200:
                return False

            # Check Content-Length header if available
            content_length = response.headers.get('content-length')
            if content_length:
                # If content length is 0 or very small, likely broken
                if int(content_length) < 100:  # Less than 100 bytes is suspicious
                    return False
            else:
                # If no Content-Length header, do a GET to check actual content
                response = await client.get(url, follow_redirects=True)
                if response.status_code != 200 or len(response.content) < 100:
                    return False

            return True

    except Exception as e:
        logger.debug(f"URL check failed for {url}: {e}")
        return False


async def sample_has_broken_links(sample: Sample) -> bool:
    """
    Check if a sample has any broken or missing media links.
    Returns True if sample needs reprocessing due to broken links.
    """
    # Check essential media URLs
    urls_to_check = []

    # Video URL (critical)
    if sample.video_url:
        urls_to_check.append(("video", sample.video_url))
    else:
        return True  # Missing video URL

    # Audio URLs (critical)
    if sample.audio_url_wav:
        urls_to_check.append(("audio_wav", sample.audio_url_wav))
    else:
        return True  # Missing WAV

    if sample.audio_url_mp3:
        urls_to_check.append(("audio_mp3", sample.audio_url_mp3))
    else:
        return True  # Missing MP3

    # Waveform (critical for UI)
    if sample.waveform_url:
        urls_to_check.append(("waveform", sample.waveform_url))
    else:
        return True  # Missing waveform

    # Check each URL
    for media_type, url in urls_to_check:
        has_content = await check_url_has_content(url)
        if not has_content:
            logger.info(f"  Sample {sample.id}: Broken {media_type} URL")
            return True

    return False


async def reprocess_samples_background(
    filter_status: Optional[str] = None,
    limit: Optional[int] = None,
    skip_reset: bool = False,
    broken_links_only: bool = False
):
    """Background task to reprocess samples"""
    logger.info("="*60)
    logger.info("Starting background sample reprocessing")
    if broken_links_only:
        logger.info("Mode: Broken links only")
    logger.info("="*60)

    stats = {
        'total': 0,
        'triggered': 0,
        'failed': 0,
        'skipped': 0,
    }

    async with AsyncSessionLocal() as db:
        # Build query
        query = select(Sample).order_by(Sample.created_at.desc())

        if filter_status:
            status_enum = ProcessingStatus(filter_status)
            query = query.where(Sample.status == status_enum)
            logger.info(f"Filtering by status: {filter_status}")

        result = await db.execute(query)
        samples = result.scalars().all()

        if limit:
            samples = samples[:limit]
            logger.info(f"Limited to first {limit} samples")

        stats['total'] = len(samples)
        logger.info(f"Found {len(samples)} samples to reprocess")

        if stats['total'] == 0:
            logger.info("No samples to process. Exiting.")
            return

        # Get Inngest client
        from app.inngest_functions import inngest_client

        # Process each sample
        for i, sample in enumerate(samples, 1):
            logger.info(f"[{i}/{len(samples)}] Processing sample {sample.id}")
            logger.info(f"  URL: {sample.tiktok_url}")
            logger.info(f"  Creator: @{sample.creator_username}")
            logger.info(f"  Current status: {sample.status.value}")

            # Check for broken links if requested
            if broken_links_only:
                logger.info(f"  Checking URLs for sample {sample.id}...")
                has_broken = await sample_has_broken_links(sample)
                if not has_broken:
                    logger.info(f"  ✓ All URLs valid, skipping sample {sample.id}")
                    stats['skipped'] += 1
                    continue
                else:
                    logger.info(f"  ✗ Found broken/missing URLs, will reprocess")

            # Reset status if requested
            if not skip_reset:
                try:
                    sample.status = ProcessingStatus.PENDING
                    sample.error_message = None
                    await db.commit()
                    logger.info(f"  Reset sample {sample.id} to pending")
                except Exception as e:
                    logger.error(f"  Error resetting sample status: {e}")
                    await db.rollback()

            # Trigger reprocessing
            if not sample.tiktok_url:
                logger.warning(f"  Sample {sample.id} has no TikTok URL, skipping")
                continue

            try:
                await inngest_client.send(
                    inngest.Event(
                        name="tiktok/video.submitted",
                        data={
                            "sample_id": str(sample.id),
                            "url": sample.tiktok_url
                        }
                    )
                )
                logger.info(f"  ✓ Pipeline triggered for sample {sample.id}")
                stats['triggered'] += 1
            except Exception as e:
                logger.error(f"  ✗ Error triggering pipeline for sample {sample.id}: {e}")
                stats['failed'] += 1

            # Small delay to avoid overwhelming the system
            await asyncio.sleep(2)

    # Log summary
    logger.info("="*60)
    logger.info("BACKGROUND REPROCESSING COMPLETE")
    logger.info("="*60)
    logger.info(f"Total samples: {stats['total']}")
    logger.info(f"Successfully triggered: {stats['triggered']}")
    logger.info(f"Failed: {stats['failed']}")
    logger.info(f"Skipped: {stats['skipped']}")
    logger.info("="*60)


@router.post("/reprocess", response_model=ReprocessResponse)
async def reprocess_samples(
    request: ReprocessRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Trigger reprocessing of samples through the full Inngest pipeline.

    This endpoint triggers background reprocessing of samples, downloading fresh media
    from TikTok and storing everything in your infrastructure.

    - **filter_status**: Only reprocess samples with specific status (pending/processing/completed/failed)
    - **limit**: Maximum number of samples to reprocess
    - **skip_reset**: Don't reset sample status to pending
    - **dry_run**: Show what would be processed without actually triggering
    """
    # Build query to count samples
    query = select(func.count(Sample.id))

    if request.filter_status:
        try:
            status_enum = ProcessingStatus(request.filter_status)
            query = query.where(Sample.status == status_enum)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status: {request.filter_status}. Must be one of: pending, processing, completed, failed"
            )

    result = await db.execute(query)
    total_count = result.scalar()

    # Apply limit if specified
    samples_to_process = min(total_count, request.limit) if request.limit else total_count

    if samples_to_process == 0:
        return ReprocessResponse(
            message="No samples found matching the criteria",
            total_samples=0,
            status="completed"
        )

    if request.dry_run:
        return ReprocessResponse(
            message=f"Dry run: Would reprocess {samples_to_process} samples",
            total_samples=samples_to_process,
            status="dry_run"
        )

    # Add background task
    background_tasks.add_task(
        reprocess_samples_background,
        filter_status=request.filter_status,
        limit=request.limit,
        skip_reset=request.skip_reset,
        broken_links_only=request.broken_links_only
    )

    message = f"Started reprocessing {samples_to_process} samples in the background."
    if request.broken_links_only:
        message += " Only samples with broken/missing URLs will be processed."
    message += " Check logs for progress."

    return ReprocessResponse(
        message=message,
        total_samples=samples_to_process,
        status="started"
    )


@router.post("/fix-creator-avatars")
async def fix_creator_avatars(
    dry_run: bool = False,
    db: AsyncSession = Depends(get_db)
):
    """
    Fix creator avatar URLs by updating from internal R2 endpoint to public R2 domain
    """
    from app.models.tiktok_creator import TikTokCreator
    from app.core.config import settings

    def fix_url(old_url: str) -> str:
        """Convert broken R2 URL to public R2 domain URL"""
        if not old_url:
            return old_url

        # If already using public domain, no change needed
        if settings.R2_PUBLIC_DOMAIN in old_url:
            return old_url

        # Extract the path after bucket name
        if '/sampletok-samples/' in old_url:
            path = old_url.split('/sampletok-samples/')[-1]
            return f"https://{settings.R2_PUBLIC_DOMAIN}/{path}"

        return old_url

    # Get all creators
    query = select(TikTokCreator)
    result = await db.execute(query)
    creators = result.scalars().all()

    stats = {
        'total': len(creators),
        'fixed': 0,
        'skipped': 0,
    }

    for creator in creators:
        # Check if any avatar URLs need fixing
        needs_fix = False

        if creator.avatar_thumb and settings.R2_PUBLIC_DOMAIN not in creator.avatar_thumb:
            needs_fix = True
        if creator.avatar_medium and settings.R2_PUBLIC_DOMAIN not in creator.avatar_medium:
            needs_fix = True
        if creator.avatar_large and settings.R2_PUBLIC_DOMAIN not in creator.avatar_large:
            needs_fix = True

        if not needs_fix:
            stats['skipped'] += 1
            continue

        # Fix URLs
        if not dry_run:
            if creator.avatar_thumb:
                creator.avatar_thumb = fix_url(creator.avatar_thumb)
            if creator.avatar_medium:
                creator.avatar_medium = fix_url(creator.avatar_medium)
            if creator.avatar_large:
                creator.avatar_large = fix_url(creator.avatar_large)

        stats['fixed'] += 1

    if not dry_run:
        await db.commit()

    return {
        "message": f"{'Dry run: Would fix' if dry_run else 'Fixed'} {stats['fixed']} creator avatar URLs",
        "total_creators": stats['total'],
        "fixed": stats['fixed'],
        "skipped": stats['skipped'],
        "dry_run": dry_run
    }