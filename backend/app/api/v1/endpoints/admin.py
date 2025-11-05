"""
Admin endpoints for emergency operations
"""
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from typing import Optional
from pydantic import BaseModel
from uuid import UUID
import logging

from app.core.database import get_db
from app.core.config import settings
from app.models import Collection, CollectionStatus, User, Stem, StemProcessingStatus, Sample, CollectionSample
from app.services.credit_service import CreditService
from app.inngest_functions import inngest_client
import inngest
from collections import defaultdict
from app.services.audio.processor import AudioProcessor
from app.services.storage.s3 import S3Storage
import tempfile
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)

router = APIRouter()


class AddCreditsRequest(BaseModel):
    clerk_id: str
    credits: int

    class Config:
        json_schema_extra = {
            "example": {
                "clerk_id": "user_2abc123def456",
                "credits": 100
            }
        }


class RefundCreditsRequest(BaseModel):
    clerk_id: str
    credits: int
    reason: str
    collection_id: Optional[str] = None
    sample_id: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "clerk_id": "user_2abc123def456",
                "credits": 50,
                "reason": "Refund for failed collection processing",
                "collection_id": "2a3960d1-f762-4947-8f50-f2a736dd1bf6"
            }
        }


class BackfillHLSRequest(BaseModel):
    limit: Optional[int] = None
    dry_run: bool = False

    class Config:
        json_schema_extra = {
            "example": {
                "limit": 10,
                "dry_run": False
            }
        }


@router.post("/reset-user-collections")
async def reset_user_collections(
    clerk_id: str,
    x_admin_key: str = Header(..., description="Admin API key"),
    db: AsyncSession = Depends(get_db)
):
    """
    Emergency endpoint to reset all stuck collections for a user and refund credits.

    Requires X-Admin-Key header matching ADMIN_API_KEY for security.

    Example:
        POST /api/v1/admin/reset-user-collections?clerk_id=user_2abc123def456
        X-Admin-Key: your-admin-api-key
    """
    # Verify admin key
    if not settings.ADMIN_API_KEY:
        raise HTTPException(status_code=503, detail="Admin API not configured")
    if x_admin_key != settings.ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid admin key")

    logger.info(f"Admin: Resetting collections for Clerk ID {clerk_id}")

    # Get user
    user_query = select(User).where(User.clerk_user_id == clerk_id)
    user_result = await db.execute(user_query)
    user = user_result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail=f"User with Clerk ID {clerk_id} not found")

    # Get stuck collections
    collections_query = select(Collection).where(
        Collection.user_id == user.id,
        Collection.status.in_([CollectionStatus.pending, CollectionStatus.processing, CollectionStatus.failed])
    )
    collections_result = await db.execute(collections_query)
    stuck_collections = collections_result.scalars().all()

    if not stuck_collections:
        return {
            "message": "No stuck collections found",
            "clerk_id": clerk_id,
            "user_email": user.email,
            "collections_reset": 0,
            "credits_refunded": 0,
            "current_credits": user.credits
        }

    # Calculate total refund
    total_refund = sum(
        (c.total_video_count - (c.processed_count or 0))
        for c in stuck_collections
    )

    # Refund credits
    user.credits += total_refund

    # Reset collections
    reset_details = []
    for collection in stuck_collections:
        videos_to_refund = collection.total_video_count - (collection.processed_count or 0)
        reset_details.append({
            "id": str(collection.id),
            "name": collection.name,
            "status": collection.status.value,
            "videos_processed": collection.processed_count or 0,
            "total_videos": collection.total_video_count,
            "credits_refunded": videos_to_refund
        })

        collection.status = CollectionStatus.pending
        collection.processed_count = 0
        collection.error_message = None
        collection.current_cursor = 0
        collection.started_at = None
        collection.completed_at = None

    await db.commit()

    logger.info(
        f"Admin: Reset {len(stuck_collections)} collections for Clerk ID {clerk_id}, "
        f"refunded {total_refund} credits, new balance: {user.credits}"
    )

    return {
        "message": f"Successfully reset {len(stuck_collections)} collections",
        "clerk_id": clerk_id,
        "user_email": user.email,
        "collections_reset": len(stuck_collections),
        "credits_refunded": total_refund,
        "current_credits": user.credits,
        "collections": reset_details
    }


@router.post("/reset-collection/{collection_id}")
async def reset_collection_by_id(
    collection_id: str,
    x_admin_key: str = Header(..., description="Admin API key"),
    trigger: bool = False,
    hard_reset: bool = False,
    db: AsyncSession = Depends(get_db)
):
    """
    Emergency endpoint to reset a specific collection and refund credits.

    Options:
    - trigger: Automatically trigger Inngest processing after reset
    - hard_reset: Delete all CollectionSample links to force re-fetch of all videos

    Requires X-Admin-Key header matching ADMIN_API_KEY for security.

    Example:
        POST /api/v1/admin/reset-collection/2a3960d1-f762-4947-8f50-f2a736dd1bf6?trigger=true&hard_reset=true
        X-Admin-Key: your-admin-api-key
    """
    # Verify admin key
    if not settings.ADMIN_API_KEY:
        raise HTTPException(status_code=503, detail="Admin API not configured")
    if x_admin_key != settings.ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid admin key")

    logger.info(f"Admin: Resetting collection {collection_id} (trigger={trigger})")

    # Get collection
    collection_query = select(Collection).where(Collection.id == text(f"'{collection_id}'::uuid"))
    collection_result = await db.execute(collection_query)
    collection = collection_result.scalar_one_or_none()

    if not collection:
        raise HTTPException(status_code=404, detail=f"Collection {collection_id} not found")

    # Get user
    user_query = select(User).where(User.id == collection.user_id)
    user_result = await db.execute(user_query)
    user = user_result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found for collection")

    # Calculate refund
    videos_to_refund = collection.total_video_count - (collection.processed_count or 0)

    # Store old state
    old_status = collection.status.value
    old_credits = user.credits

    # Refund credits
    if videos_to_refund > 0:
        user.credits += videos_to_refund

    # Reset collection
    collection.status = CollectionStatus.pending
    collection.processed_count = 0
    collection.error_message = None
    collection.current_cursor = 0
    collection.started_at = None
    collection.completed_at = None

    await db.commit()

    logger.info(
        f"Admin: Reset collection {collection_id} (status: {old_status} → pending), "
        f"refunded {videos_to_refund} credits to user {user.clerk_user_id}, "
        f"balance: {old_credits} → {user.credits}"
    )

    # Hard reset: Delete all CollectionSample links to force re-fetch
    links_deleted = 0
    if hard_reset:
        try:
            logger.info(f"Admin: Hard reset - deleting all CollectionSample links for collection {collection_id}")
            delete_result = await db.execute(
                text("DELETE FROM collection_samples WHERE collection_id = :collection_id"),
                {"collection_id": collection_id}
            )
            links_deleted = delete_result.rowcount
            await db.commit()
            logger.info(f"Admin: Deleted {links_deleted} CollectionSample links for collection {collection_id}")
        except Exception as e:
            logger.error(f"Admin: Failed to delete CollectionSample links: {e}")

    # Optionally trigger Inngest processing immediately
    triggered = False
    trigger_error = None
    if trigger:
        try:
            logger.info(f"Admin: Triggering Inngest processing for collection {collection_id}")
            await inngest_client.send(
                inngest.Event(
                    name="collection/import.submitted",
                    data={
                        "collection_id": collection_id
                    }
                )
            )
            triggered = True
            logger.info(f"Admin: Successfully triggered processing for collection {collection_id}")
        except Exception as e:
            trigger_error = str(e)
            logger.error(f"Admin: Failed to trigger Inngest for collection {collection_id}: {e}")

    response = {
        "message": "Successfully reset collection",
        "collection_id": collection_id,
        "collection_name": collection.name,
        "old_status": old_status,
        "new_status": "pending",
        "user_clerk_id": user.clerk_user_id,
        "user_email": user.email,
        "credits_refunded": videos_to_refund,
        "previous_balance": old_credits,
        "new_balance": user.credits,
        "total_videos": collection.total_video_count,
        "videos_processed": 0
    }

    if hard_reset:
        response["hard_reset"] = True
        response["links_deleted"] = links_deleted

    if trigger:
        response["triggered"] = triggered
        if trigger_error:
            response["trigger_error"] = trigger_error

    return response


@router.post("/add-credits")
async def add_credits(
    request: AddCreditsRequest,
    x_admin_key: str = Header(..., description="Admin API key"),
    db: AsyncSession = Depends(get_db)
):
    """
    Add credits to a user's account by their Clerk ID.

    Requires X-Admin-Key header matching ADMIN_API_KEY for security.

    Example:
        POST /api/v1/admin/add-credits
        X-Admin-Key: your-admin-api-key
        {
            "clerk_id": "user_2abc123def456",
            "credits": 100
        }
    """
    # Verify admin key
    if not settings.ADMIN_API_KEY:
        raise HTTPException(status_code=503, detail="Admin API not configured")
    if x_admin_key != settings.ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid admin key")

    if request.credits <= 0:
        raise HTTPException(status_code=400, detail="Credits must be positive")

    logger.info(f"Admin: Adding {request.credits} credits to Clerk ID {request.clerk_id}")

    # Find user by Clerk ID
    user_query = select(User).where(User.clerk_user_id == request.clerk_id)
    user_result = await db.execute(user_query)
    user = user_result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=404,
            detail=f"User with Clerk ID {request.clerk_id} not found"
        )

    # Store old balance
    old_credits = user.credits

    # Add credits
    user.credits += request.credits
    await db.commit()

    logger.info(
        f"Admin: Added {request.credits} credits to user {user.clerk_user_id}. "
        f"Balance: {old_credits} → {user.credits}"
    )

    return {
        "message": f"Successfully added {request.credits} credits",
        "user_email": user.email,
        "clerk_id": user.clerk_user_id,
        "credits_added": request.credits,
        "previous_balance": old_credits,
        "new_balance": user.credits
    }


@router.post("/refund-credits")
async def refund_credits(
    request: RefundCreditsRequest,
    x_admin_key: str = Header(..., description="Admin API key"),
    db: AsyncSession = Depends(get_db)
):
    """
    Manual credit refund endpoint with full audit trail.

    Creates a proper CreditTransaction record for tracking and reconciliation.
    Use this for manual refunds when automated systems fail.

    Requires X-Admin-Key header matching ADMIN_API_KEY for security.

    Args:
        clerk_id: User's Clerk ID
        credits: Number of credits to refund (positive integer)
        reason: Human-readable reason for the refund
        collection_id: Optional collection reference for audit trail
        sample_id: Optional sample reference for audit trail

    Example:
        POST /api/v1/admin/refund-credits
        X-Admin-Key: your-admin-api-key
        {
            "clerk_id": "user_2abc123def456",
            "credits": 50,
            "reason": "Refund for failed collection processing",
            "collection_id": "2a3960d1-f762-4947-8f50-f2a736dd1bf6"
        }
    """
    # Verify admin key
    if not settings.ADMIN_API_KEY:
        raise HTTPException(status_code=503, detail="Admin API not configured")
    if x_admin_key != settings.ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid admin key")

    if request.credits <= 0:
        raise HTTPException(status_code=400, detail="Credits must be positive")

    logger.info(
        f"Admin: Manual refund of {request.credits} credits to Clerk ID {request.clerk_id}. "
        f"Reason: {request.reason}"
    )

    # Find user by Clerk ID
    user_query = select(User).where(User.clerk_user_id == request.clerk_id)
    user_result = await db.execute(user_query)
    user = user_result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=404,
            detail=f"User with Clerk ID {request.clerk_id} not found"
        )

    # Convert collection_id and sample_id to UUID if provided
    collection_uuid = UUID(request.collection_id) if request.collection_id else None
    sample_uuid = UUID(request.sample_id) if request.sample_id else None

    # Use CreditService for atomic refund with audit trail
    credit_service = CreditService(db)

    try:
        await credit_service.refund_credits_atomic(
            user_id=user.id,
            credits_to_refund=request.credits,
            description=f"Admin manual refund: {request.reason}",
            collection_id=collection_uuid,
            sample_id=sample_uuid
        )

        # Commit the transaction
        await db.commit()

        # Refresh user to get updated balance
        await db.refresh(user)

        logger.info(
            f"Admin: Successfully refunded {request.credits} credits to user {user.clerk_user_id}. "
            f"New balance: {user.credits}"
        )

        return {
            "message": f"Successfully refunded {request.credits} credits",
            "user_email": user.email,
            "clerk_id": user.clerk_user_id,
            "credits_refunded": request.credits,
            "new_balance": user.credits,
            "reason": request.reason,
            "audit_trail": "CreditTransaction created with type='refund'"
        }

    except Exception as e:
        logger.error(f"Admin: Error refunding credits: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to refund credits: {str(e)}"
        )


@router.post("/retrigger-failed-stems")
async def retrigger_failed_stems(
    x_admin_key: str = Header(..., description="Admin API key"),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrigger all failed or stuck stem separation jobs.

    This will resend the Inngest event for all stems that are:
    - PENDING (never started)
    - UPLOADING (stuck during upload)
    - PROCESSING (stuck during processing)
    - FAILED (explicitly failed)

    Requires X-Admin-Key header matching ADMIN_API_KEY for security.

    Example:
        POST /api/v1/admin/retrigger-failed-stems
        X-Admin-Key: your-admin-api-key
    """
    # Verify admin key
    if not settings.ADMIN_API_KEY:
        raise HTTPException(status_code=503, detail="Admin API not configured")
    if x_admin_key != settings.ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid admin key")

    logger.info("Admin: Retriggering failed stem separation jobs")

    # Get stems that are stuck or failed
    stems_query = select(Stem).where(
        Stem.status.in_([
            StemProcessingStatus.PENDING,
            StemProcessingStatus.UPLOADING,
            StemProcessingStatus.PROCESSING,
            StemProcessingStatus.FAILED
        ])
    )
    stems_result = await db.execute(stems_query)
    stems = stems_result.scalars().all()

    if not stems:
        return {
            "message": "No stems need retriggering",
            "stems_retriggered": 0,
            "samples_affected": 0
        }

    # Group stems by sample_id
    stems_by_sample = defaultdict(list)
    for stem in stems:
        stems_by_sample[str(stem.parent_sample_id)].append(stem)

    # Retrigger each sample's stems
    retriggered_count = 0
    failed_count = 0
    sample_details = []

    for sample_id, sample_stems in stems_by_sample.items():
        stem_ids = [str(stem.id) for stem in sample_stems]
        stem_types = [stem.stem_type.value for stem in sample_stems]

        try:
            # Send Inngest event
            await inngest_client.send(
                inngest.Event(
                    name="stem/separation.submitted",
                    data={
                        "sample_id": sample_id,
                        "stem_ids": stem_ids
                    }
                )
            )

            retriggered_count += len(sample_stems)
            sample_details.append({
                "sample_id": sample_id,
                "stem_count": len(sample_stems),
                "stem_types": stem_types,
                "status": "retriggered"
            })

            logger.info(f"Admin: Retriggered {len(sample_stems)} stems for sample {sample_id}")

        except Exception as e:
            failed_count += len(sample_stems)
            sample_details.append({
                "sample_id": sample_id,
                "stem_count": len(sample_stems),
                "stem_types": stem_types,
                "status": "failed",
                "error": str(e)
            })

            logger.error(f"Admin: Failed to retrigger stems for sample {sample_id}: {e}")

    logger.info(
        f"Admin: Retriggered {retriggered_count} stems across {len(stems_by_sample)} samples. "
        f"Failed: {failed_count}"
    )

    return {
        "message": f"Retriggered {retriggered_count} stems across {len(stems_by_sample)} samples",
        "stems_retriggered": retriggered_count,
        "stems_failed": failed_count,
        "samples_affected": len(stems_by_sample),
        "details": sample_details
    }


@router.post("/backfill-hls")
async def backfill_hls_streams(
    request: BackfillHLSRequest,
    x_admin_key: str = Header(..., description="Admin API key"),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate HLS streaming playlists for existing samples that only have MP3 files.

    This adds instant playback capability to older samples without re-downloading from TikTok.
    For each sample, it:
    1. Downloads the existing MP3 from storage
    2. Generates HLS segments (2-second chunks at 320kbps AAC)
    3. Uploads playlist.m3u8 + all segment files
    4. Updates database with HLS URL

    Much faster than full reprocessing (no TikTok API calls needed).

    Requires X-Admin-Key header matching ADMIN_API_KEY for security.

    Args:
        limit: Maximum number of samples to process (optional, processes all if not specified)
        dry_run: If true, preview what would be processed without actually doing it

    Example:
        POST /api/v1/admin/backfill-hls
        X-Admin-Key: your-admin-api-key
        {
            "limit": 10,
            "dry_run": false
        }
    """
    # Verify admin key
    if not settings.ADMIN_API_KEY:
        raise HTTPException(status_code=503, detail="Admin API not configured")
    if x_admin_key != settings.ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid admin key")

    logger.info(f"Admin: Starting HLS backfill (limit={request.limit}, dry_run={request.dry_run})")

    # Get samples without HLS
    from app.models.sample import ProcessingStatus
    query = select(Sample).where(
        Sample.status == ProcessingStatus.COMPLETED,
        Sample.audio_url_mp3.isnot(None),
        Sample.audio_url_hls.is_(None)
    )

    if request.limit:
        query = query.limit(request.limit)

    result = await db.execute(query)
    samples = result.scalars().all()

    if not samples:
        return {
            "message": "No samples need HLS processing",
            "samples_processed": 0,
            "samples_failed": 0,
            "dry_run": request.dry_run
        }

    if request.dry_run:
        sample_list = [
            {
                "id": str(s.id),
                "creator": s.creator_username,
                "duration": s.duration_seconds,
                "mp3_url": s.audio_url_mp3
            }
            for s in samples
        ]
        return {
            "message": f"Would process {len(samples)} samples",
            "samples_found": len(samples),
            "dry_run": True,
            "samples": sample_list
        }

    # Process samples
    success_count = 0
    failed_count = 0
    sample_details = []

    storage = S3Storage()
    processor = AudioProcessor()

    for sample in samples:
        temp_dir = None
        try:
            logger.info(f"Processing sample {sample.id} - {sample.creator_username}")

            # Create temporary directory
            temp_dir = tempfile.mkdtemp(prefix=f"hls_{sample.id}_")
            temp_path = Path(temp_dir)

            # Download MP3 from storage
            mp3_path = temp_path / f"{sample.id}.mp3"
            mp3_url = sample.audio_url_mp3

            if '/samples/' in mp3_url:
                object_key = mp3_url.split('/samples/')[-1]
                object_key = f"samples/{object_key}"
            else:
                raise ValueError(f"Could not parse MP3 URL: {mp3_url}")

            await storage.download_file(object_key, str(mp3_path))

            # Generate HLS stream
            hls_data = await processor.generate_hls_stream(str(mp3_path), temp_dir)
            num_segments = len(hls_data['segments'])

            # Upload playlist
            playlist_url = await storage.upload_file(
                hls_data['playlist'],
                f"samples/{sample.id}/hls/playlist.m3u8"
            )

            # Upload all segments
            for segment_path in hls_data['segments']:
                segment_filename = Path(segment_path).name
                await storage.upload_file(
                    segment_path,
                    f"samples/{sample.id}/hls/{segment_filename}"
                )

            # Update database
            sample.audio_url_hls = playlist_url
            await db.commit()
            await db.refresh(sample)

            success_count += 1
            sample_details.append({
                "id": str(sample.id),
                "creator": sample.creator_username,
                "segments": num_segments,
                "status": "success",
                "hls_url": playlist_url
            })

            logger.info(f"Successfully processed sample {sample.id}")

        except Exception as e:
            failed_count += 1
            sample_details.append({
                "id": str(sample.id),
                "creator": sample.creator_username,
                "status": "failed",
                "error": str(e)
            })
            logger.error(f"Failed to process sample {sample.id}: {e}", exc_info=True)

        finally:
            # Cleanup temp directory
            if temp_dir and Path(temp_dir).exists():
                try:
                    shutil.rmtree(temp_dir)
                except Exception as e:
                    logger.warning(f"Failed to cleanup temp directory: {e}")

    logger.info(
        f"Admin: HLS backfill complete. Processed: {success_count}, Failed: {failed_count}"
    )

    return {
        "message": f"Processed {success_count} samples successfully",
        "samples_processed": success_count,
        "samples_failed": failed_count,
        "total_samples": len(samples),
        "dry_run": False,
        "details": sample_details
    }
