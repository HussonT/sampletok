from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from typing import List, Optional
from uuid import UUID
import logging
import inngest

from app.core.database import get_db
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


@router.get("/tiktok/{username}", response_model=TikTokCollectionListResponse)
async def get_tiktok_user_collections(
    username: str,
    count: int = Query(default=35, ge=1, le=35, description="Number of collections to fetch"),
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
    # Enforce max 30 videos per batch
    max_videos = 30
    videos_to_process = min(request.video_count - request.cursor, max_videos)

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

            # Deduct credits for the new batch
            current_user.credits -= videos_to_process

            # Update collection to pending for new batch
            existing_collection.status = CollectionStatus.pending
            existing_collection.current_cursor = request.cursor
            await db.commit()

            collection = existing_collection
        else:
            # cursor=0 means starting from beginning
            if existing_collection.status == CollectionStatus.completed and not existing_collection.has_more:
                return CollectionProcessingTaskResponse(
                    collection_id=existing_collection.id,
                    status="completed",
                    message="Collection fully imported",
                    credits_deducted=0,
                    remaining_credits=current_user.credits
                )
            elif existing_collection.status == CollectionStatus.processing:
                return CollectionProcessingTaskResponse(
                    collection_id=existing_collection.id,
                    status="processing",
                    message="Collection is currently being processed",
                    credits_deducted=0,
                    remaining_credits=current_user.credits
                )

            # Restart from beginning
            current_user.credits -= videos_to_process
            existing_collection.status = CollectionStatus.pending
            existing_collection.current_cursor = 0
            existing_collection.processed_count = 0
            await db.commit()
            collection = existing_collection
    else:
        # Deduct credits
        current_user.credits -= videos_to_process

        # Create new collection record
        collection = Collection(
            user_id=current_user.id,
            tiktok_collection_id=request.collection_id,
            tiktok_username=request.tiktok_username,
            name=request.name,
            total_video_count=request.video_count,
            current_cursor=request.cursor,
            status=CollectionStatus.pending
        )
        db.add(collection)
        await db.commit()
        await db.refresh(collection)

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
        # Mark collection as failed and refund credits
        collection.status = CollectionStatus.failed
        collection.error_message = f"Failed to queue processing: {str(e)}"
        current_user.credits += videos_to_process  # Refund credits
        await db.commit()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to queue collection for processing: {str(e)}"
        )

    # Calculate batch info for message
    start_video = request.cursor + 1
    end_video = min(request.cursor + videos_to_process, request.video_count)

    return CollectionProcessingTaskResponse(
        collection_id=collection.id,
        status="pending",
        message=f"Batch queued: videos {start_video}-{end_video} of {request.video_count}",
        credits_deducted=videos_to_process,
        remaining_credits=current_user.credits
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
