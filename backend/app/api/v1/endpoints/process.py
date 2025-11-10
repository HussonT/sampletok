from fastapi import APIRouter, Depends, HTTPException
import inngest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
import uuid
import logging

from app.core.database import get_db
from app.models import Sample, ProcessingStatus, User
from app.models.sample import SampleSource
from app.models.schemas import (
    TikTokURLInput,
    InstagramURLInput,
    ProcessingTaskResponse,
    ProcessingStatusResponse,
    SampleResponse
)
from app.services.tiktok.validator import TikTokURLValidator
from app.services.tiktok.downloader import TikTokDownloader
from app.services.instagram.validator import InstagramURLValidator
from app.inngest_functions import inngest_client
from app.api.deps import get_current_user
from app.services.credit_service import CreditService
from pydantic import BaseModel

router = APIRouter()
logger = logging.getLogger(__name__)


class UniversalURLInput(BaseModel):
    """Auto-detect URL input for TikTok or Instagram"""
    url: str


@router.post("/submit", response_model=ProcessingTaskResponse)
async def submit_url(
    input_data: UniversalURLInput,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Universal endpoint that auto-detects TikTok or Instagram URLs
    and routes to the appropriate processor.

    Requires authentication and costs 1 credit per sample.
    """
    url_str = str(input_data.url).strip()

    # Try TikTok first
    is_tiktok, _ = TikTokURLValidator.validate_url(url_str)
    if is_tiktok:
        logger.info(f"Detected TikTok URL: {url_str}")
        tiktok_input = TikTokURLInput(url=url_str)
        return await process_tiktok_url(tiktok_input, db, current_user)

    # Try Instagram
    is_instagram, _ = InstagramURLValidator.validate_url(url_str)
    if is_instagram:
        logger.info(f"Detected Instagram URL: {url_str}")
        instagram_input = InstagramURLInput(url=url_str)
        return await process_instagram_url(instagram_input, db, current_user)

    # Neither TikTok nor Instagram
    raise HTTPException(
        status_code=400,
        detail="URL must be a valid TikTok or Instagram link"
    )


@router.post("/tiktok", response_model=ProcessingTaskResponse)
async def process_tiktok_url(
    input_data: TikTokURLInput,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Process a TikTok URL to extract audio sample.
    This endpoint queues the video for processing and returns immediately.

    Requires authentication and costs 1 credit per sample.
    """
    url_str = str(input_data.url)

    # Validate URL
    is_valid, error_message = TikTokURLValidator.validate_url(url_str)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_message)

    # Normalize URL
    normalized_url = TikTokURLValidator.normalize_url(url_str)

    # Check if URL already exists in database
    # Use first() to handle multiple results and get the most recent one
    query = select(Sample).where(
        Sample.tiktok_url == normalized_url
    ).order_by(Sample.created_at.desc())
    result = await db.execute(query)
    existing_sample = result.scalars().first()

    if existing_sample:
        if existing_sample.status == ProcessingStatus.COMPLETED:
            return ProcessingTaskResponse(
                task_id=str(existing_sample.id),
                status="completed",
                message="Sample already processed (no credits charged)",
                sample_id=existing_sample.id
            )
        elif existing_sample.status == ProcessingStatus.PROCESSING:
            return ProcessingTaskResponse(
                task_id=str(existing_sample.id),
                status="processing",
                message="Sample is currently being processed (no credits charged)",
                sample_id=existing_sample.id
            )

    # Check credits before processing
    credit_service = CreditService(db)
    if current_user.credits < 1:
        raise HTTPException(
            status_code=402,
            detail=f"Insufficient credits. You need 1 credit to process this sample but only have {current_user.credits}."
        )

    # Deduct credits atomically
    credits_deducted = await credit_service.deduct_credits_atomic(
        user_id=current_user.id,
        credits_needed=1,
        transaction_type="sample_processing",
        description=f"Process TikTok sample: {normalized_url}"
    )

    if not credits_deducted:
        raise HTTPException(
            status_code=402,
            detail=f"Insufficient credits. You need 1 credit to process this sample."
        )

    logger.info(f"Deducted 1 credit from user {current_user.id} for sample processing")

    # Create new sample record with creator reference
    sample = Sample(
        source=SampleSource.TIKTOK,
        tiktok_url=normalized_url,
        status=ProcessingStatus.PENDING,
        creator_id=current_user.id  # Associate with user who submitted it
    )
    db.add(sample)
    await db.commit()
    await db.refresh(sample)

    # Send event to Inngest for processing
    try:
        logger.info(f"Sending Inngest event for sample {sample.id}")
        await inngest_client.send(
            inngest.Event(
                name="tiktok/video.submitted",
                data={
                    "sample_id": str(sample.id),
                    "url": normalized_url
                }
            )
        )
        logger.info(f"Successfully sent Inngest event for sample {sample.id}")
    except Exception as e:
        logger.exception(f"Failed to send Inngest event for sample {sample.id}: {str(e)}")
        # Mark sample as failed
        sample.status = ProcessingStatus.FAILED
        sample.error_message = f"Failed to queue processing: {str(e)}"
        await db.commit()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to queue sample for processing: {str(e)}"
        )

    return ProcessingTaskResponse(
        task_id=str(sample.id),
        status="queued",
        message="Sample queued for processing",
        sample_id=sample.id
    )


@router.post("/instagram", response_model=ProcessingTaskResponse)
async def process_instagram_url(
    input_data: InstagramURLInput,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Process an Instagram URL to extract audio sample.
    This endpoint queues the video for processing and returns immediately.

    Requires authentication and costs 1 credit per sample.
    """
    url_str = str(input_data.url)

    # Validate URL
    is_valid, error_message = InstagramURLValidator.validate_url(url_str)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_message)

    # Normalize URL
    normalized_url = InstagramURLValidator.normalize_url(url_str)

    # Extract shortcode for duplicate checking
    shortcode = InstagramURLValidator.extract_shortcode(url_str)
    if not shortcode:
        raise HTTPException(status_code=400, detail="Could not extract shortcode from URL")

    # Check if shortcode already exists in database
    query = select(Sample).where(
        Sample.instagram_shortcode == shortcode
    ).order_by(Sample.created_at.desc())
    result = await db.execute(query)
    existing_sample = result.scalars().first()

    if existing_sample:
        if existing_sample.status == ProcessingStatus.COMPLETED:
            return ProcessingTaskResponse(
                task_id=str(existing_sample.id),
                status="completed",
                message="Sample already processed (no credits charged)",
                sample_id=existing_sample.id
            )
        elif existing_sample.status == ProcessingStatus.PROCESSING:
            return ProcessingTaskResponse(
                task_id=str(existing_sample.id),
                status="processing",
                message="Sample is currently being processed (no credits charged)",
                sample_id=existing_sample.id
            )
        elif existing_sample.status in (ProcessingStatus.FAILED, ProcessingStatus.PENDING):
            # Retry failed or stuck samples (no additional credits charged)
            logger.info(f"Retrying sample {existing_sample.id} with status {existing_sample.status}")
            existing_sample.status = ProcessingStatus.PENDING
            existing_sample.error_message = None
            await db.commit()
            await db.refresh(existing_sample)

            # Send event to Inngest for processing
            try:
                logger.info(f"Sending Inngest event for Instagram sample {existing_sample.id} (retry)")
                await inngest_client.send(
                    inngest.Event(
                        name="instagram/video.submitted",
                        data={
                            "sample_id": str(existing_sample.id),
                            "url": normalized_url,
                            "shortcode": shortcode
                        }
                    )
                )
                logger.info(f"Successfully sent Inngest event for Instagram sample {existing_sample.id} (retry)")
            except Exception as e:
                logger.exception(f"Failed to send Inngest event for Instagram sample {existing_sample.id}: {str(e)}")
                existing_sample.status = ProcessingStatus.FAILED
                existing_sample.error_message = f"Failed to queue processing: {str(e)}"
                await db.commit()
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to queue sample for processing: {str(e)}"
                )

            return ProcessingTaskResponse(
                task_id=str(existing_sample.id),
                status="queued",
                message="Instagram sample queued for processing (retry - no credits charged)",
                sample_id=existing_sample.id
            )

    # Check credits before processing
    credit_service = CreditService(db)
    if current_user.credits < 1:
        raise HTTPException(
            status_code=402,
            detail=f"Insufficient credits. You need 1 credit to process this sample but only have {current_user.credits}."
        )

    # Deduct credits atomically
    credits_deducted = await credit_service.deduct_credits_atomic(
        user_id=current_user.id,
        credits_needed=1,
        transaction_type="sample_processing",
        description=f"Process Instagram sample: {normalized_url}"
    )

    if not credits_deducted:
        raise HTTPException(
            status_code=402,
            detail=f"Insufficient credits. You need 1 credit to process this sample."
        )

    logger.info(f"Deducted 1 credit from user {current_user.id} for Instagram sample processing")

    # Create new sample record with creator reference
    sample = Sample(
        source=SampleSource.INSTAGRAM,
        instagram_url=normalized_url,
        instagram_shortcode=shortcode,
        status=ProcessingStatus.PENDING,
        creator_id=current_user.id  # Associate with user who submitted it
    )
    db.add(sample)

    # Handle race condition where another request created the same sample concurrently
    try:
        await db.commit()
        await db.refresh(sample)
    except IntegrityError as e:
        await db.rollback()
        # Duplicate shortcode detected - fetch the existing sample
        logger.warning(f"Duplicate Instagram shortcode {shortcode} detected during commit: {str(e)}")
        result = await db.execute(
            select(Sample).where(Sample.instagram_shortcode == shortcode)
        )
        existing_sample = result.scalars().first()
        if existing_sample:
            return ProcessingTaskResponse(
                task_id=str(existing_sample.id),
                status="queued" if existing_sample.status == ProcessingStatus.PENDING else existing_sample.status.value,
                message="Sample already exists (created concurrently)",
                sample_id=existing_sample.id
            )
        # If we can't find it, re-raise the error
        raise HTTPException(status_code=500, detail=f"Database integrity error: {str(e)}")

    # Send event to Inngest for processing
    try:
        logger.info(f"Sending Inngest event for Instagram sample {sample.id}")
        await inngest_client.send(
            inngest.Event(
                name="instagram/video.submitted",
                data={
                    "sample_id": str(sample.id),
                    "url": normalized_url,
                    "shortcode": shortcode
                }
            )
        )
        logger.info(f"Successfully sent Inngest event for Instagram sample {sample.id}")
    except Exception as e:
        logger.exception(f"Failed to send Inngest event for Instagram sample {sample.id}: {str(e)}")
        # Mark sample as failed
        sample.status = ProcessingStatus.FAILED
        sample.error_message = f"Failed to queue processing: {str(e)}"
        await db.commit()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to queue sample for processing: {str(e)}"
        )

    return ProcessingTaskResponse(
        task_id=str(sample.id),
        status="queued",
        message="Instagram sample queued for processing",
        sample_id=sample.id
    )


@router.get("/status/{task_id}", response_model=ProcessingStatusResponse)
async def get_processing_status(
    task_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get the status of a processing task"""
    try:
        sample_id = uuid.UUID(task_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid task ID")

    query = select(Sample).where(Sample.id == sample_id)
    result = await db.execute(query)
    sample = result.scalar_one_or_none()

    if not sample:
        raise HTTPException(status_code=404, detail="Task not found")

    # Calculate progress based on status
    progress = 0
    if sample.status == ProcessingStatus.PENDING:
        progress = 0
    elif sample.status == ProcessingStatus.PROCESSING:
        progress = 50
    elif sample.status == ProcessingStatus.COMPLETED:
        progress = 100
    elif sample.status == ProcessingStatus.FAILED:
        progress = 0

    message = {
        ProcessingStatus.PENDING: "Waiting to process",
        ProcessingStatus.PROCESSING: "Processing video and extracting audio",
        ProcessingStatus.COMPLETED: "Processing completed successfully",
        ProcessingStatus.FAILED: sample.error_message or "Processing failed"
    }.get(sample.status, "Unknown status")

    response = ProcessingStatusResponse(
        task_id=task_id,
        status=sample.status.value,
        progress=progress,
        message=message
    )

    if sample.status == ProcessingStatus.COMPLETED:
        response.result = {
            "sample_id": str(sample.id),
            "audio_url": sample.audio_url_mp3,
            "waveform_url": sample.waveform_url
        }

    return response

