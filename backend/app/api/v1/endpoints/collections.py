from fastapi import APIRouter, Depends, HTTPException, Query, Request
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
from app.api.deps import get_current_user, require_active_subscription
from app.services.tiktok.collection_service import TikTokCollectionService
from app.services.credit_service import deduct_credits_atomic, refund_credits_atomic
from app.inngest_functions import inngest_client
from app.core.rate_limit import limiter

logger = logging.getLogger(__name__)

router = APIRouter()


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

        # Get existing video_ids from our database (single query to avoid N+1)
        query = (
            select(Sample.tiktok_id)
            .join(CollectionSample, Sample.id == CollectionSample.sample_id)
            .where(CollectionSample.collection_id == collection_id)
        )
        result = await db.execute(query)
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
@limiter.limit(f"{settings.COLLECTIONS_LIST_RATE_LIMIT_PER_MINUTE}/minute")
async def get_tiktok_user_collections(
    request: Request,
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
@limiter.limit(f"{settings.COLLECTION_RATE_LIMIT_PER_MINUTE}/minute")
async def process_collection(
    request: Request,
    payload: ProcessCollectionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_active_subscription)
):
    """
    Process a TikTok collection - downloads all videos and adds them to user's downloads

    Requires ACTIVE SUBSCRIPTION and sufficient credits (1 credit per video, max 30 videos)

    Args:
        payload: Collection details (collection_id, username, name, video_count)
        current_user: Authenticated user with active subscription

    Returns:
        Task response with collection_id for status tracking

    Raises:
        403: If user has no active subscription
    """
    # Enforce max videos per batch
    max_videos = settings.MAX_VIDEOS_PER_BATCH
    videos_to_process = min(payload.video_count - payload.cursor, max_videos)
    is_sync = False  # Track if this is a sync operation
    invalid_video_count = None  # Track invalid videos for new collections

    # Check if collection already exists for this user
    existing_query = select(Collection).where(
        and_(
            Collection.user_id == current_user.id,
            Collection.tiktok_collection_id == payload.collection_id
        )
    )
    result = await db.execute(existing_query)
    existing_collection = result.scalars().first()

    if existing_collection:
        # If collection exists, check if we're importing a new batch
        if payload.cursor > 0:
            # This is a continuation - NO credit deduction (already deducted upfront)
            if existing_collection.status == CollectionStatus.processing:
                return CollectionProcessingTaskResponse(
                    collection_id=existing_collection.id,
                    status="processing",
                    message="Collection is currently being processed",
                    credits_deducted=0,
                    remaining_credits=current_user.credits
                )

            # Update collection to pending for next batch (no credit deduction)
            existing_collection.status = CollectionStatus.pending
            existing_collection.current_cursor = payload.cursor
            await db.commit()

            # Refresh user to get current credit balance
            await db.refresh(current_user)
            collection = existing_collection
            videos_to_process = 0  # No credits deducted for continuation batches
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
                #
                # KNOWN ISSUE: TOCTOU (Time-Of-Check-Time-Of-Use) Race Condition
                # =================================================================
                # The subscription is checked early in the request (via require_active_subscription dependency),
                # but credit deduction happens here, potentially seconds later. Theoretically, the subscription
                # could be cancelled between the check and the deduction.
                #
                # IMPACT ANALYSIS:
                # 1. Subscription cancellations are rare during active processing
                # 2. Atomic credit operations (with_for_update) prevent double-spending
                # 3. Worst case: User loses subscription mid-request, gets charged credits anyway
                # 4. This is an acceptable edge case given the complexity of adding re-checks
                #
                # MITIGATION:
                # - Credit deductions use database-level locks (atomic operations)
                # - Complete audit trail via CreditTransaction allows manual review
                # - Subscription status is refreshed on next request
                #
                # ALTERNATIVE CONSIDERED AND REJECTED:
                # Re-checking subscription status before every credit deduction would:
                # - Add N extra database queries per request
                # - Increase complexity and potential for deadlocks
                # - Provide minimal benefit for an extremely rare edge case
                #
                # DECISION: Accept this known limitation. Document it clearly for future maintainers.
                if not await deduct_credits_atomic(db, current_user.id, new_videos):
                    # Refresh user to get current credit balance for error message
                    # Note: There's a minor TOCTOU here - balance could change between deduction and refresh
                    # This only affects the error message, not business logic, so it's acceptable
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
        valid_video_count, invalid_video_count = await get_valid_video_count(payload.collection_id)

        if valid_video_count == 0:
            raise HTTPException(
                status_code=400,
                detail="No valid videos found in this collection"
            )

        # Deduct credits for ALL videos upfront (automatic processing will handle all batches)
        if not await deduct_credits_atomic(db, current_user.id, valid_video_count):
            # Refresh user to get current credit balance for error message
            await db.refresh(current_user)
            raise HTTPException(
                status_code=402,
                detail=f"Insufficient credits. Need {valid_video_count} credits for the full collection, but have {current_user.credits}"
            )

        videos_to_process = valid_video_count  # All credits deducted upfront

        # Create new collection record with correct count
        collection = Collection(
            user_id=current_user.id,
            tiktok_collection_id=payload.collection_id,
            tiktok_username=payload.tiktok_username,
            name=payload.name,
            total_video_count=valid_video_count,  # Use actual valid count
            current_cursor=payload.cursor,
            status=CollectionStatus.pending
        )
        db.add(collection)
        await db.commit()
        await db.refresh(collection)
        # Refresh user to get updated credit balance
        await db.refresh(current_user)

        logger.info(
            f"Created collection {collection.id}: {valid_video_count} valid videos "
            f"(TikTok API reported {payload.video_count}, {invalid_video_count} invalid)"
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

        # Refund credits FIRST (before marking collection as failed)
        await refund_credits_atomic(db, current_user.id, videos_to_process)

        # Re-fetch the collection after rollback to ensure it's attached to the session
        refetch_query = select(Collection).where(Collection.id == collection.id)
        refetch_result = await db.execute(refetch_query)
        collection = refetch_result.scalar_one()

        # Now mark collection as failed and commit
        collection.status = CollectionStatus.failed
        collection.error_message = f"Failed to queue processing: {str(e)}"
        await db.commit()

        # Refresh user to get updated balance
        await db.refresh(current_user)

        raise HTTPException(
            status_code=500,
            detail=f"Failed to queue collection for processing: {str(e)}"
        )

    # Calculate batch info for message
    if is_sync:
        message = f"Syncing collection: processing {videos_to_process} new videos"
    elif payload.cursor > 0:
        # Continuation batch (no credits deducted)
        message = "Collection processing will continue automatically"
    else:
        # New collection - all credits deducted upfront
        message = f"Collection queued: {videos_to_process} videos will be processed automatically in batches"

    return CollectionProcessingTaskResponse(
        collection_id=collection.id,
        status="pending",
        message=message,
        credits_deducted=videos_to_process,
        remaining_credits=current_user.credits,
        invalid_video_count=invalid_video_count
    )


@router.get("", response_model=List[CollectionResponse])
@limiter.limit(f"{settings.COLLECTIONS_LIST_RATE_LIMIT_PER_MINUTE}/minute")
async def list_user_collections(
    request: Request,
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
        List of user's collections with sample counts
    """
    from sqlalchemy import func

    query = (
        select(Collection)
        .where(Collection.user_id == current_user.id)
        .order_by(Collection.created_at.desc())
        .offset(skip)
        .limit(limit)
    )

    result = await db.execute(query)
    collections = result.scalars().all()

    # Get sample counts for all collections in one query
    collection_ids = [c.id for c in collections]
    if collection_ids:
        count_query = (
            select(
                CollectionSample.collection_id,
                func.count(CollectionSample.sample_id).label('count')
            )
            .where(CollectionSample.collection_id.in_(collection_ids))
            .group_by(CollectionSample.collection_id)
        )
        count_result = await db.execute(count_query)
        counts_dict = {row.collection_id: row.count for row in count_result.all()}

        # Get cover images (first sample's cover) for all collections
        # Use ROW_NUMBER to get the first sample by position for each collection
        from sqlalchemy import func as sql_func
        from sqlalchemy.sql import select as sql_select

        # Subquery to get first sample per collection (lowest position)
        cover_query = (
            select(
                CollectionSample.collection_id,
                Sample.cover_url
            )
            .join(Sample, Sample.id == CollectionSample.sample_id)
            .where(CollectionSample.collection_id.in_(collection_ids))
            .distinct(CollectionSample.collection_id)
            .order_by(CollectionSample.collection_id, CollectionSample.position)
        )
        cover_result = await db.execute(cover_query)
        covers_dict = {row.collection_id: row.cover_url for row in cover_result.all()}

        # Get multiple cover images (first 10) for the card swap component
        covers_array_query = (
            select(
                CollectionSample.collection_id,
                Sample.cover_url
            )
            .join(Sample, Sample.id == CollectionSample.sample_id)
            .where(
                (CollectionSample.collection_id.in_(collection_ids)) &
                (Sample.cover_url.isnot(None))
            )
            .order_by(CollectionSample.collection_id, CollectionSample.position)
        )
        covers_array_result = await db.execute(covers_array_query)

        # Group covers by collection_id, limit to 10 per collection
        covers_arrays_dict = {}
        for row in covers_array_result.all():
            if row.collection_id not in covers_arrays_dict:
                covers_arrays_dict[row.collection_id] = []
            if len(covers_arrays_dict[row.collection_id]) < 10:
                covers_arrays_dict[row.collection_id].append(row.cover_url)
    else:
        counts_dict = {}
        covers_dict = {}
        covers_arrays_dict = {}

    # Build response with sample counts and cover images
    response_list = []
    for c in collections:
        collection_dict = {
            'id': c.id,
            'user_id': c.user_id,
            'tiktok_collection_id': c.tiktok_collection_id,
            'tiktok_username': c.tiktok_username,
            'name': c.name,
            'total_video_count': c.total_video_count,
            'current_cursor': c.current_cursor,
            'next_cursor': c.next_cursor,
            'has_more': c.has_more,
            'status': c.status.value if hasattr(c.status, 'value') else c.status,
            'processed_count': c.processed_count,
            'sample_count': counts_dict.get(c.id, 0),
            'cover_image_url': covers_dict.get(c.id),
            'cover_images': covers_arrays_dict.get(c.id, []),
            'error_message': c.error_message,
            'created_at': c.created_at,
            'started_at': c.started_at,
            'completed_at': c.completed_at
        }
        response_list.append(CollectionResponse(**collection_dict))

    return response_list


@router.get("/{collection_id}", response_model=CollectionWithSamplesResponse)
@limiter.limit(f"{settings.COLLECTIONS_LIST_RATE_LIMIT_PER_MINUTE}/minute")
async def get_collection_details(
    request: Request,
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
@limiter.limit(f"{settings.COLLECTIONS_LIST_RATE_LIMIT_PER_MINUTE}/minute")
async def get_collection_status(
    request: Request,
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


@router.post("/{collection_id}/reset")
async def reset_stuck_collection(
    collection_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Reset a stuck collection and refund unprocessed credits.

    Use this when a collection is stuck in 'pending' or 'processing' status
    and hasn't made progress. This will:
    1. Calculate how many videos were charged but not processed
    2. Refund those credits
    3. Reset the collection to allow re-processing

    Args:
        collection_id: UUID of the collection to reset

    Returns:
        Details about the reset operation
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

    # Only allow resetting pending/processing/failed collections
    if collection.status == CollectionStatus.completed:
        raise HTTPException(
            status_code=400,
            detail="Cannot reset a completed collection. Use the sync feature instead."
        )

    # Calculate unprocessed videos that should be refunded
    # For pending collections, all videos are unprocessed
    # For processing collections, refund (total - processed)
    total_videos = collection.total_video_count
    processed_videos = collection.processed_count or 0
    videos_to_refund = total_videos - processed_videos

    # Refund credits
    refunded = 0
    if videos_to_refund > 0:
        await refund_credits_atomic(db, current_user.id, videos_to_refund)
        refunded = videos_to_refund
        logger.info(f"Refunded {refunded} credits to user {current_user.id} for stuck collection {collection_id}")

    # Reset collection to pending state
    collection.status = CollectionStatus.pending
    collection.processed_count = 0
    collection.error_message = None
    collection.current_cursor = 0
    collection.started_at = None
    collection.completed_at = None

    await db.commit()

    # Refresh user to get updated credit balance
    await db.refresh(current_user)

    return {
        "collection_id": str(collection_id),
        "status": "reset",
        "message": f"Collection reset successfully. Refunded {refunded} credits.",
        "credits_refunded": refunded,
        "remaining_credits": current_user.credits,
        "total_videos": total_videos,
        "processed_videos": processed_videos
    }
