from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, update
from sqlalchemy.orm import selectinload
from typing import List, Optional
from uuid import UUID
import logging
import inngest

from app.core.database import get_db
from app.core.config import settings
from app.models import Collection, CollectionSample, CollectionStatus, Sample, User
from app.models.schemas import (
    TikTokCollectionListResponse,
    ProcessCollectionRequest,
    CollectionResponse,
    CollectionWithSamplesResponse,
    CollectionStatusResponse,
    CollectionProcessingTaskResponse,
    SampleResponse
)
from app.api.deps import get_current_user
from app.services.tiktok.collection_service import TikTokCollectionService
from app.inngest_functions import inngest_client

logger = logging.getLogger(__name__)

router = APIRouter()


async def deduct_credits_atomic(
    db: AsyncSession,
    user_id: UUID,
    credits_needed: int
) -> bool:
    """
    Atomically deduct credits from user account using database-level atomic operation.
    This prevents race conditions when multiple requests try to deduct credits simultaneously.

    Args:
        db: Database session
        user_id: UUID of the user
        credits_needed: Number of credits to deduct

    Returns:
        True if credits were successfully deducted, False if insufficient credits
    """
    result = await db.execute(
        update(User)
        .where(and_(
            User.id == user_id,
            User.credits >= credits_needed
        ))
        .values(credits=User.credits - credits_needed)
    )

    # If rowcount is 0, it means either user doesn't exist or insufficient credits
    if result.rowcount == 0:
        # Check if user exists to give better error message
        user_check = await db.execute(select(User).where(User.id == user_id))
        user = user_check.scalars().first()
        if not user:
            logger.error(f"User {user_id} not found during credit deduction")
            return False
        logger.warning(f"Insufficient credits for user {user_id}: has {user.credits}, needs {credits_needed}")
        return False

    await db.commit()
    logger.info(f"Atomically deducted {credits_needed} credits from user {user_id}")
    return True


async def refund_credits_atomic(
    db: AsyncSession,
    user_id: UUID,
    credits_to_refund: int
) -> None:
    """
    Atomically refund credits to user account.

    Args:
        db: Database session
        user_id: UUID of the user
        credits_to_refund: Number of credits to refund
    """
    await db.execute(
        update(User)
        .where(User.id == user_id)
        .values(credits=User.credits + credits_to_refund)
    )
    await db.commit()
    logger.info(f"Refunded {credits_to_refund} credits to user {user_id}")


async def get_valid_video_count(tiktok_collection_id: str) -> tuple[int, int]:
    """
    Get the actual count of valid videos in a TikTok collection.
    Only counts videos that can be processed (have video_id + author username).

    Returns:
        tuple[int, int]: (valid_count, invalid_count)
    """
    try:
        collection_service = TikTokCollectionService()
        result = await collection_service.fetch_collection_posts(
            collection_id=tiktok_collection_id,
            count=settings.TIKTOK_API_MAX_PER_REQUEST,
            cursor=0
        )

        data = result.get('data', {})
        tiktok_videos = data.get('videos', [])

        # Filter out invalid videos (only need video_id + username to build URL)
        valid_videos = [
            v for v in tiktok_videos
            if (v.get('video_id') and
                v.get('author', {}).get('unique_id'))
        ]

        valid_count = len(valid_videos)
        invalid_count = len(tiktok_videos) - valid_count

        logger.info(
            f"Collection {tiktok_collection_id}: {len(tiktok_videos)} total videos, "
            f"{valid_count} valid (can be processed), {invalid_count} invalid"
        )

        return valid_count, invalid_count

    except Exception as e:
        logger.exception(f"Error fetching valid video count for collection {tiktok_collection_id}: {e}")
        return 0, 0


async def get_new_videos_count(
    collection_id: UUID,
    tiktok_collection_id: str,
    db: AsyncSession
) -> tuple[int, int]:
    """
    Check how many new videos are in a TikTok collection compared to what we have.

    Returns:
        tuple[int, int]: (total_valid_videos_in_tiktok, new_videos_count)
    """
    try:
        # Fetch current videos from TikTok
        collection_service = TikTokCollectionService()
        result = await collection_service.fetch_collection_posts(
            collection_id=tiktok_collection_id,
            count=settings.TIKTOK_API_MAX_PER_REQUEST,
            cursor=0
        )

        data = result.get('data', {})
        tiktok_videos = data.get('videos', [])

        # Filter out invalid videos (only need video_id + username to build URL)
        valid_videos = [
            v for v in tiktok_videos
            if (v.get('video_id') and
                v.get('author', {}).get('unique_id'))
        ]
        tiktok_video_ids = {v['video_id'] for v in valid_videos}

        # Get existing video_ids from our database
        query = (
            select(CollectionSample)
            .join(Sample, CollectionSample.sample_id == Sample.id)
            .where(CollectionSample.collection_id == collection_id)
        )
        result = await db.execute(query)
        collection_samples = result.scalars().all()

        # Get the tiktok_ids from existing samples
        existing_query = select(Sample.tiktok_id).where(
            Sample.id.in_([cs.sample_id for cs in collection_samples])
        )
        result = await db.execute(existing_query)
        existing_video_ids = {row[0] for row in result.all() if row[0]}

        # Calculate new videos
        new_video_ids = tiktok_video_ids - existing_video_ids

        logger.info(
            f"Collection {collection_id}: {len(tiktok_video_ids)} videos in TikTok, "
            f"{len(existing_video_ids)} already imported, {len(new_video_ids)} new"
        )

        return len(tiktok_video_ids), len(new_video_ids)

    except Exception as e:
        logger.exception(f"Error checking new videos for collection {collection_id}: {e}")
        # On error, assume all videos are new (conservative approach)
        return 0, 0


@router.get("/tiktok/{username}", response_model=TikTokCollectionListResponse)
async def get_tiktok_user_collections(
    username: str,
    count: int = Query(default=settings.MAX_COLLECTIONS_PER_REQUEST, ge=1, le=settings.MAX_COLLECTIONS_PER_REQUEST, description="Number of collections to fetch"),
    cursor: int = Query(default=0, ge=0, description="Pagination cursor")
):
    """
    Fetch a TikTok user's public collections (no authentication required)

    Args:
        username: TikTok username (unique_id)
        count: Number of collections to fetch (max 35)
        cursor: Pagination cursor for next page

    Returns:
        List of public collections with metadata
    """
    try:
        collection_service = TikTokCollectionService()
        result = await collection_service.fetch_collection_list(
            username=username,
            count=count,
            cursor=cursor
        )

        # Extract data from API response
        data = result.get('data', {})

        # Convert collection IDs to strings to prevent JavaScript number precision issues
        # TikTok collection IDs are very large integers that exceed JavaScript's Number.MAX_SAFE_INTEGER
        collection_list = data.get('collection_list', [])
        for collection in collection_list:
            if 'id' in collection:
                collection['id'] = str(collection['id'])

        return TikTokCollectionListResponse(
            collection_list=collection_list,
            cursor=data.get('cursor', 0),
            hasMore=data.get('hasMore', False)
        )

    except ValueError as e:
        logger.error(f"Validation error fetching collections: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error fetching TikTok collections: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch collections: {str(e)}"
        )


@router.post("/process", response_model=CollectionProcessingTaskResponse)
async def process_collection(
    request: ProcessCollectionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Process a TikTok collection - downloads all videos and adds them to user's downloads

    Requires authentication and sufficient credits (1 credit per video, max 30 videos)

    Args:
        request: Collection details (collection_id, username, name, video_count)
        current_user: Authenticated user

    Returns:
        Task response with collection_id for status tracking
    """
    # Enforce max videos per batch
    max_videos = settings.MAX_VIDEOS_PER_BATCH
    videos_to_process = min(request.video_count - request.cursor, max_videos)
    is_sync = False  # Track if this is a sync operation
    invalid_video_count = None  # Track invalid videos for new collections

    # Check if user has enough credits (1 credit per video)
    if current_user.credits < videos_to_process:
        raise HTTPException(
            status_code=402,
            detail=f"Insufficient credits. Need {videos_to_process} credits, but have {current_user.credits}"
        )

    # Check if collection already exists for this user
    existing_query = select(Collection).where(
        and_(
            Collection.user_id == current_user.id,
            Collection.tiktok_collection_id == request.collection_id
        )
    )
    result = await db.execute(existing_query)
    existing_collection = result.scalars().first()

    if existing_collection:
        # If collection exists, check if we're importing a new batch
        if request.cursor > 0:
            # This is a continuation - update the collection for next batch
            if existing_collection.status == CollectionStatus.processing:
                return CollectionProcessingTaskResponse(
                    collection_id=existing_collection.id,
                    status="processing",
                    message="Collection is currently being processed",
                    credits_deducted=0,
                    remaining_credits=current_user.credits
                )

            # Deduct credits for the new batch atomically
            if not await deduct_credits_atomic(db, current_user.id, videos_to_process):
                # Refresh user to get current credit balance for error message
                await db.refresh(current_user)
                raise HTTPException(
                    status_code=402,
                    detail=f"Insufficient credits. Need {videos_to_process} credits, but have {current_user.credits}"
                )

            # Update collection to pending for new batch
            existing_collection.status = CollectionStatus.pending
            existing_collection.current_cursor = request.cursor
            await db.commit()

            # Refresh user to get updated credit balance
            await db.refresh(current_user)
            collection = existing_collection
        else:
            # cursor=0 means starting from beginning
            if existing_collection.status == CollectionStatus.completed and not existing_collection.has_more:
                # Check if there are new videos (smart sync)
                total_videos, new_videos = await get_new_videos_count(
                    existing_collection.id,
                    existing_collection.tiktok_collection_id,
                    db
                )

                if new_videos == 0:
                    return CollectionProcessingTaskResponse(
                        collection_id=existing_collection.id,
                        status="completed",
                        message="Collection is up to date - no new videos found",
                        credits_deducted=0,
                        remaining_credits=current_user.credits
                    )

                # New videos found - sync them
                # Deduct credits only for new videos atomically
                if not await deduct_credits_atomic(db, current_user.id, new_videos):
                    # Refresh user to get current credit balance for error message
                    await db.refresh(current_user)
                    raise HTTPException(
                        status_code=402,
                        detail=f"Insufficient credits. Need {new_videos} credits for {new_videos} new videos, but have {current_user.credits}"
                    )

                videos_to_process = new_videos  # Update for message generation

                # Reset collection for sync
                existing_collection.status = CollectionStatus.pending
                existing_collection.current_cursor = 0
                existing_collection.total_video_count = total_videos
                existing_collection.processed_count = 0  # Reset processed count for sync
                existing_collection.has_more = False  # Reset pagination
                existing_collection.next_cursor = None  # Reset pagination
                await db.commit()

                # Refresh user to get updated credit balance
                await db.refresh(current_user)
                collection = existing_collection
                is_sync = True

            elif existing_collection.status == CollectionStatus.processing:
                return CollectionProcessingTaskResponse(
                    collection_id=existing_collection.id,
                    status="processing",
                    message="Collection is currently being processed",
                    credits_deducted=0,
                    remaining_credits=current_user.credits
                )

            # Restart from beginning
            # Deduct credits atomically
            if not await deduct_credits_atomic(db, current_user.id, videos_to_process):
                # Refresh user to get current credit balance for error message
                await db.refresh(current_user)
                raise HTTPException(
                    status_code=402,
                    detail=f"Insufficient credits. Need {videos_to_process} credits, but have {current_user.credits}"
                )

            existing_collection.status = CollectionStatus.pending
            existing_collection.current_cursor = 0
            existing_collection.processed_count = 0
            existing_collection.has_more = False  # Reset pagination
            existing_collection.next_cursor = None  # Reset pagination
            await db.commit()

            # Refresh user to get updated credit balance
            await db.refresh(current_user)
            collection = existing_collection
    else:
        # Get actual valid video count (filters out invalid videos)
        valid_video_count, invalid_video_count = await get_valid_video_count(request.collection_id)

        if valid_video_count == 0:
            raise HTTPException(
                status_code=400,
                detail="No valid videos found in this collection"
            )

        # Recalculate credits based on actual valid videos
        actual_videos_to_process = min(valid_video_count, max_videos)

        # Deduct credits for actual valid videos atomically
        if not await deduct_credits_atomic(db, current_user.id, actual_videos_to_process):
            # Refresh user to get current credit balance for error message
            await db.refresh(current_user)
            raise HTTPException(
                status_code=402,
                detail=f"Insufficient credits. Need {actual_videos_to_process} credits for {actual_videos_to_process} videos, but have {current_user.credits}"
            )

        videos_to_process = actual_videos_to_process

        # Create new collection record with correct count
        collection = Collection(
            user_id=current_user.id,
            tiktok_collection_id=request.collection_id,
            tiktok_username=request.tiktok_username,
            name=request.name,
            total_video_count=valid_video_count,  # Use actual valid count
            current_cursor=request.cursor,
            status=CollectionStatus.pending
        )
        db.add(collection)
        await db.commit()
        await db.refresh(collection)
        # Refresh user to get updated credit balance
        await db.refresh(current_user)

        logger.info(
            f"Created collection {collection.id}: {valid_video_count} valid videos "
            f"(TikTok API reported {request.video_count}, {invalid_video_count} invalid)"
        )

    # Send event to Inngest for async processing
    # Only send our internal collection ID - Inngest will fetch details from database
    try:
        logger.info(f"Sending Inngest event for collection {collection.id}")
        await inngest_client.send(
            inngest.Event(
                name="collection/import.submitted",
                data={
                    "collection_id": str(collection.id)
                }
            )
        )
        logger.info(f"Successfully sent Inngest event for collection {collection.id}")
    except Exception as e:
        logger.exception(f"Failed to send Inngest event for collection {collection.id}: {str(e)}")
        # Rollback any uncommitted changes
        await db.rollback()

        # Mark collection as failed and refund credits
        collection.status = CollectionStatus.failed
        collection.error_message = f"Failed to queue processing: {str(e)}"
        await db.commit()

        # Refund credits atomically
        await refund_credits_atomic(db, current_user.id, videos_to_process)
        # Refresh user to get updated balance
        await db.refresh(current_user)

        raise HTTPException(
            status_code=500,
            detail=f"Failed to queue collection for processing: {str(e)}"
        )

    # Calculate batch info for message
    if is_sync:
        message = f"Syncing collection: processing {videos_to_process} new videos"
    else:
        start_video = request.cursor + 1
        end_video = min(request.cursor + videos_to_process, request.video_count)
        message = f"Batch queued: videos {start_video}-{end_video} of {request.video_count}"

    return CollectionProcessingTaskResponse(
        collection_id=collection.id,
        status="pending",
        message=message,
        credits_deducted=videos_to_process,
        remaining_credits=current_user.credits,
        invalid_video_count=invalid_video_count
    )


@router.get("", response_model=List[CollectionResponse])
async def list_user_collections(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100)
):
    """
    List the current user's imported collections

    Args:
        skip: Number of collections to skip (for pagination)
        limit: Number of collections to return

    Returns:
        List of user's collections
    """
    query = (
        select(Collection)
        .where(Collection.user_id == current_user.id)
        .order_by(Collection.created_at.desc())
        .offset(skip)
        .limit(limit)
    )

    result = await db.execute(query)
    collections = result.scalars().all()

    return [CollectionResponse.model_validate(c) for c in collections]


@router.get("/{collection_id}", response_model=CollectionWithSamplesResponse)
async def get_collection_details(
    collection_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get collection details with all associated samples

    Args:
        collection_id: UUID of the collection

    Returns:
        Collection with samples
    """
    # Get collection with samples (using eager loading)
    query = (
        select(Collection)
        .where(
            and_(
                Collection.id == collection_id,
                Collection.user_id == current_user.id
            )
        )
        .options(
            selectinload(Collection.collection_samples)
            .selectinload(CollectionSample.sample)
            .selectinload(Sample.tiktok_creator)  # Eagerly load creator to avoid lazy-load issues
        )
    )

    result = await db.execute(query)
    collection = result.scalars().first()

    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")

    # Build response with samples in order
    collection_dict = CollectionResponse.model_validate(collection).model_dump()

    # Sort by position and convert to SampleResponse
    sorted_collection_samples = sorted(
        collection.collection_samples,
        key=lambda cs: cs.position
    )

    samples = [
        SampleResponse.model_validate(cs.sample)
        for cs in sorted_collection_samples
        if cs.sample  # Ensure sample exists
    ]

    collection_dict['samples'] = samples

    return CollectionWithSamplesResponse(**collection_dict)


@router.get("/{collection_id}/status", response_model=CollectionStatusResponse)
async def get_collection_status(
    collection_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get the processing status of a collection

    Args:
        collection_id: UUID of the collection

    Returns:
        Collection processing status with progress
    """
    query = select(Collection).where(
        and_(
            Collection.id == collection_id,
            Collection.user_id == current_user.id
        )
    )

    result = await db.execute(query)
    collection = result.scalars().first()

    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")

    # Calculate progress percentage
    progress = 0
    if collection.total_video_count > 0:
        progress = int((collection.processed_count / collection.total_video_count) * 100)

    # Determine message based on status
    status_messages = {
        CollectionStatus.pending: "Collection queued for processing",
        CollectionStatus.processing: f"Processing videos ({collection.processed_count}/{collection.total_video_count})",
        CollectionStatus.completed: f"Completed! Processed {collection.processed_count} videos",
        CollectionStatus.failed: f"Processing failed: {collection.error_message or 'Unknown error'}"
    }

    message = status_messages.get(collection.status, "Unknown status")

    return CollectionStatusResponse(
        collection_id=collection.id,
        status=collection.status.value,
        progress=progress,
        processed_count=collection.processed_count,
        total_video_count=collection.total_video_count,
        message=message,
        error_message=collection.error_message
    )
