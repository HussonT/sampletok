from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel
import logging
import inngest

from app.core.database import get_db, AsyncSessionLocal
from app.core.config import settings
from app.core.rate_limit import limiter
from app.models import Sample, ProcessingStatus, Stem, StemType, StemProcessingStatus, UserStemFavorite
from app.models.user import UserStemDownload
from app.models.user import User
from app.api.deps import get_current_user, get_current_user_optional
from app.services.credit_service import CreditService
from app.services.storage.s3 import S3Storage
from app.services.user_service import UserStemFavoriteService, UserStemDownloadService
from app.inngest_functions import inngest_client

logger = logging.getLogger(__name__)

router = APIRouter()


# Request/Response models
class StemSeparationRequest(BaseModel):
    stems: List[str]  # List of stem types (e.g., ["vocal", "drums", "bass"])


class StemSeparationResponse(BaseModel):
    success: bool
    credits_deducted: int
    remaining_credits: int
    stem_ids: List[str]
    estimated_time_seconds: int
    message: str


class StemResponse(BaseModel):
    id: str
    stem_type: str
    file_name: str
    bpm: Optional[int]
    key: Optional[str]
    duration_seconds: Optional[float]
    status: str
    download_url_mp3: Optional[str]
    download_url_wav: Optional[str]
    download_count: int = 0
    error_message: Optional[str]
    created_at: str
    completed_at: Optional[str]
    is_favorited: Optional[bool] = None
    favorited_at: Optional[str] = None
    is_downloaded: Optional[bool] = None

    class Config:
        from_attributes = True


class FavoriteResponse(BaseModel):
    is_favorited: bool
    favorited_at: Optional[str] = None


@router.post("/{sample_id}/separate-stems", response_model=StemSeparationResponse)
@limiter.limit(f"{settings.STEM_SEPARATION_RATE_LIMIT_PER_MINUTE}/minute")
async def submit_stem_separation(
    sample_id: UUID,
    request: StemSeparationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Submit a stem separation request for a sample.
    Deducts 2 credits per stem upfront and creates stem records.
    """
    # Validate sample exists and is completed
    sample = await db.execute(select(Sample).where(Sample.id == sample_id))
    sample = sample.scalars().first()

    if not sample:
        raise HTTPException(status_code=404, detail="Sample not found")

    if sample.status != ProcessingStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail="Sample must be fully processed before separating stems"
        )

    # Validate stem types
    valid_stem_types = [e.value for e in StemType]
    for stem_type in request.stems:
        if stem_type not in valid_stem_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid stem type: {stem_type}. Valid types: {valid_stem_types}"
            )

    # Check for duplicate stems already processed or processing
    existing_stems = await db.execute(
        select(Stem).where(
            Stem.parent_sample_id == sample_id,
            Stem.stem_type.in_([StemType(s) for s in request.stems])
        )
    )
    existing_stems = existing_stems.scalars().all()

    if existing_stems:
        existing_types = [s.stem_type.value for s in existing_stems]
        raise HTTPException(
            status_code=400,
            detail=f"Stems already exist or are being processed for: {existing_types}"
        )

    # Calculate credits needed
    num_stems = len(request.stems)
    credits_needed = num_stems * settings.CREDITS_PER_STEM

    # Check and deduct credits atomically
    try:
        # Use CreditService to deduct credits
        credit_service = CreditService(db)
        success = await credit_service.deduct_credits_atomic(
            current_user.id,
            credits_needed,
            transaction_type="stem_separation",
            description=f"Stem separation for sample {sample_id} ({num_stems} stems)",
            sample_id=sample_id
        )

        if not success:
            # Get current credits for error message
            await db.refresh(current_user)
            raise HTTPException(
                status_code=402,
                detail=f"Insufficient credits. Need {credits_needed}, have {current_user.credits}"
            )

        # Get remaining credits after deduction
        await db.refresh(current_user)
        remaining_credits = current_user.credits

        # Create stem records
        stem_records = []
        for stem_type in request.stems:
            stem = Stem(
                parent_sample_id=sample_id,
                stem_type=StemType(stem_type),
                status=StemProcessingStatus.PENDING
            )
            db.add(stem)
            stem_records.append(stem)

        await db.commit()

        # Refresh to get IDs
        for stem in stem_records:
            await db.refresh(stem)

        stem_ids = [str(stem.id) for stem in stem_records]

        # Trigger Inngest background job
        try:
            await inngest_client.send(
                inngest.Event(
                    name="stem/separation.submitted",
                    data={
                        "sample_id": str(sample_id),
                        "stem_ids": stem_ids
                    }
                )
            )
            logger.info(f"Triggered stem separation job for sample {sample_id}")
        except Exception as e:
            logger.exception(f"Failed to trigger Inngest job: {e}")
            # Note: Credits already deducted, stems created. Job can be retried manually.
            raise HTTPException(
                status_code=500,
                detail="Failed to start stem separation job. Please contact support."
            )

        # Estimate time: ~30 seconds per stem
        estimated_time = num_stems * 30

        return StemSeparationResponse(
            success=True,
            credits_deducted=credits_needed,
            remaining_credits=remaining_credits,
            stem_ids=stem_ids,
            estimated_time_seconds=estimated_time,
            message=f"Stem separation started for {num_stems} stems"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error submitting stem separation: {e}")
        raise HTTPException(status_code=500, detail="Failed to submit stem separation request")


@router.get("/{sample_id}/stems", response_model=List[StemResponse])
async def get_sample_stems(
    sample_id: UUID,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all stems for a sample with their status and download URLs.
    Includes user-specific fields (is_favorited) when authenticated.
    """
    # Verify sample exists
    sample = await db.execute(select(Sample).where(Sample.id == sample_id))
    sample = sample.scalars().first()

    if not sample:
        raise HTTPException(status_code=404, detail="Sample not found")

    # Get all stems for this sample
    stems = await db.execute(
        select(Stem).where(Stem.parent_sample_id == sample_id).order_by(Stem.created_at)
    )
    stems = stems.scalars().all()

    # Get favorite and download status for all stems if user is authenticated
    favorites_map = {}
    downloads_map = {}
    if current_user:
        stem_ids = [stem.id for stem in stems]

        # Get favorites
        favorites_stmt = select(UserStemFavorite.stem_id, UserStemFavorite.favorited_at).where(
            and_(
                UserStemFavorite.user_id == current_user.id,
                UserStemFavorite.stem_id.in_(stem_ids)
            )
        )
        favorites_result = await db.execute(favorites_stmt)
        favorites_map = {row[0]: row[1] for row in favorites_result}

        # Get downloads
        downloads_stmt = select(UserStemDownload.stem_id).where(
            and_(
                UserStemDownload.user_id == current_user.id,
                UserStemDownload.stem_id.in_(stem_ids)
            )
        ).distinct()
        downloads_result = await db.execute(downloads_stmt)
        downloads_map = {row[0] for row in downloads_result}

    # Convert to response model
    responses = []
    for stem in stems:
        # Get parent sample name for file naming
        file_name = f"{stem.stem_type.value}_{sample.tiktok_id or sample.id}"

        response_dict = {
            "id": str(stem.id),
            "stem_type": stem.stem_type.value,
            "file_name": file_name,
            "bpm": stem.bpm,
            "key": stem.key,
            "duration_seconds": stem.duration_seconds,
            "status": stem.status.value,
            "download_url_mp3": stem.audio_url_mp3,
            "download_url_wav": stem.audio_url_wav,
            "download_count": stem.download_count,
            "error_message": stem.error_message,
            "created_at": stem.created_at.isoformat(),
            "completed_at": stem.completed_at.isoformat() if stem.completed_at else None,
        }

        # Add favorite and download data if user is authenticated
        if current_user:
            if stem.id in favorites_map:
                response_dict['is_favorited'] = True
                response_dict['favorited_at'] = favorites_map[stem.id].isoformat()
            else:
                response_dict['is_favorited'] = False

            response_dict['is_downloaded'] = stem.id in downloads_map

        responses.append(StemResponse(**response_dict))

    return responses


@router.get("/{stem_id}/download")
async def download_stem(
    stem_id: UUID,
    download_type: str = Query("mp3", regex="^(wav|mp3)$"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Download a separated stem - requires authentication, active subscription, and 1 credit for first download.
    Records the download in user history and increments download count.
    Re-downloads are free after the first download.
    """
    # Validate download_type
    if download_type not in ["wav", "mp3"]:
        raise HTTPException(
            status_code=400,
            detail="download_type must be 'wav' or 'mp3'"
        )

    # Get stem with parent sample and TikTok creator relationships
    from sqlalchemy.orm import selectinload
    stem_query = (
        select(Stem)
        .where(Stem.id == stem_id)
        .options(
            selectinload(Stem.parent_sample).selectinload(Sample.tiktok_creator)
        )
    )
    stem = await db.execute(stem_query)
    stem = stem.scalars().first()

    if not stem:
        raise HTTPException(status_code=404, detail="Stem not found")

    if stem.status != StemProcessingStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail=f"Stem is not ready for download (status: {stem.status.value})"
        )

    # Check if user has already downloaded this stem (any format)
    has_downloaded = await UserStemDownloadService.check_if_downloaded(
        db=db,
        user_id=current_user.id,
        stem_id=stem_id
    )

    # Only deduct credits for first-time downloads
    if not has_downloaded:
        # Check if user has active subscription
        await db.refresh(current_user, ["subscription"])
        if not current_user.subscription or not current_user.subscription.is_active:
            raise HTTPException(
                status_code=403,
                detail="Active subscription required to download stems. Please subscribe at /pricing"
            )

        # Check if user has sufficient credits (need 1 credit for download)
        if current_user.credits < 1:
            raise HTTPException(
                status_code=403,
                detail=f"Insufficient credits. You need 1 credit to download but have {current_user.credits}. Purchase a top-up at /top-up"
            )

        # Deduct 1 credit atomically
        credit_service = CreditService(db)
        success = await credit_service.deduct_credits_atomic(
            user_id=current_user.id,
            credits_needed=1,
            transaction_type="stem_download",
            description=f"Downloaded {download_type.upper()} stem: {stem.stem_type.value}",
            stem_id=stem_id
        )

        if not success:
            raise HTTPException(
                status_code=403,
                detail="Failed to deduct credits. Please try again or contact support."
            )

    # Get file path
    file_key = stem.file_path_mp3 if download_type == "mp3" else stem.file_path_wav

    if not file_key:
        raise HTTPException(status_code=404, detail=f"No {download_type.upper()} file available")

    try:
        # Record the download (after credit check but before streaming)
        await UserStemDownloadService.record_download(
            db=db,
            user_id=current_user.id,
            stem_id=stem_id,
            download_type=download_type
        )

        storage = S3Storage()

        # Stream file from storage
        async def stream_file():
            # Download file to memory and stream
            import tempfile
            from pathlib import Path

            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                tmp_path = tmp.name

            try:
                await storage.download_file(file_key, tmp_path)

                # Stream file in chunks
                with open(tmp_path, 'rb') as f:
                    while chunk := f.read(8192):
                        yield chunk
            finally:
                # Clean up temp file
                Path(tmp_path).unlink(missing_ok=True)

        # Determine content type and filename
        content_type = "audio/mpeg" if download_type == "mp3" else "audio/wav"

        # Format filename: {bpm}bpm_{key}_{artist_username}_{stem_type}.{extension}
        parent_sample = stem.parent_sample
        bpm = parent_sample.bpm or "unknown"
        key = parent_sample.key or "unknown"

        # Get artist username from TikTok creator or fall back to creator_username field
        if parent_sample.tiktok_creator:
            artist_username = parent_sample.tiktok_creator.username
        elif parent_sample.creator_username:
            artist_username = parent_sample.creator_username
        else:
            artist_username = "unknown"

        # Sanitize username for filename (remove special characters)
        import re
        artist_username = re.sub(r'[^\w\-_]', '_', artist_username)

        filename = f"{bpm}bpm_{key}_{artist_username}_{stem.stem_type.value}.{download_type}"

        return StreamingResponse(
            stream_file(),
            media_type=content_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )

    except Exception as e:
        logger.exception(f"Error downloading stem: {e}")
        raise HTTPException(status_code=500, detail="Failed to download stem")


@router.post("/{stem_id}/favorite", response_model=FavoriteResponse)
async def add_stem_favorite(
    stem_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Add a stem to user's favorites - requires authentication.
    Idempotent: returns success even if already favorited.
    """
    # Verify stem exists
    query = select(Stem).where(Stem.id == stem_id)
    result = await db.execute(query)
    stem = result.scalar_one_or_none()

    if not stem:
        raise HTTPException(status_code=404, detail="Stem not found")

    # Add to favorites (idempotent)
    favorite = await UserStemFavoriteService.add_favorite(
        db=db,
        user_id=current_user.id,
        stem_id=stem_id
    )

    return FavoriteResponse(
        is_favorited=True,
        favorited_at=favorite.favorited_at.isoformat()
    )


@router.delete("/{stem_id}/favorite", status_code=204)
async def remove_stem_favorite(
    stem_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Remove a stem from user's favorites - requires authentication.
    Idempotent: returns success even if not favorited.
    """
    # Remove from favorites (idempotent)
    await UserStemFavoriteService.remove_favorite(
        db=db,
        user_id=current_user.id,
        stem_id=stem_id
    )

    return None  # 204 No Content
