"""
Inngest functions for async processing of TikTok videos
"""
import asyncio
import inngest
import tempfile
import logging
from pathlib import Path
import uuid
from typing import Dict, Any, Optional

from app.core.config import settings
from app.services.tiktok.downloader import TikTokDownloader
from app.services.audio.processor import AudioProcessor
from app.services.audio.analyzer import AudioAnalyzer
from app.services.storage.s3 import S3Storage
from app.models import Sample, ProcessingStatus, TikTokCreator, Collection, CollectionSample, CollectionStatus
from app.models.user import UserDownload
from app.core.database import AsyncSessionLocal
from sqlalchemy import select, or_
from sqlalchemy.exc import IntegrityError
from app.services.tiktok.creator_service import CreatorService
from app.services.tiktok.collection_service import TikTokCollectionService
from app.services.credit_service import refund_credits_atomic
from app.utils import extract_hashtags, remove_hashtags
from datetime import datetime
from typing import List, Tuple

logger = logging.getLogger(__name__)

# Initialize Inngest client
# For production: set INNGEST_EVENT_KEY and INNGEST_SIGNING_KEY environment variables
# When using branch keys, set INNGEST_ENV to specify the branch environment name
inngest_kwargs = {
    "app_id": "sampletok",
    "event_key": settings.INNGEST_EVENT_KEY,
    "signing_key": settings.INNGEST_SIGNING_KEY,
    "is_production": settings.ENVIRONMENT == "production"
}

# Add env parameter if INNGEST_ENV is set (required for branch environments)
if settings.INNGEST_ENV:
    inngest_kwargs["env"] = settings.INNGEST_ENV
    logger.info(f"Inngest client initialized with branch env: {settings.INNGEST_ENV}")
else:
    logger.info(f"Inngest client initialized for environment: {settings.ENVIRONMENT}")

# Log configuration (without sensitive keys)
logger.info(f"Inngest config - app_id: sampletok, is_production: {settings.ENVIRONMENT == 'production'}, has_event_key: {bool(settings.INNGEST_EVENT_KEY)}, has_signing_key: {bool(settings.INNGEST_SIGNING_KEY)}")

inngest_client = inngest.Inngest(**inngest_kwargs)

@inngest_client.create_function(
    fn_id="process-tiktok-video",
    trigger=inngest.TriggerEvent(event="tiktok/video.submitted"),
    retries=3
)
async def process_tiktok_video(ctx: inngest.Context) -> Dict[str, Any]:
    """
    Process a TikTok video through multiple steps:
    1. Download video from TikTok
    2. Upload video to our storage
    3. Upload thumbnails/covers to our storage
    4. Extract audio (WAV and MP3)
    5. Generate waveform visualization
    6. Analyze audio features (BPM, key detection)
    7. Update database with results
    8. Clean up temp files
    """
    event_data = ctx.event.data
    sample_id = event_data.get("sample_id")
    tiktok_url = event_data.get("url")

    logger.info(f"Processing TikTok video: {tiktok_url} for sample: {sample_id}")

    # Step 1: Update status to processing
    await ctx.step.run(
        "update-status-processing",
        update_sample_status,
        sample_id,
        ProcessingStatus.PROCESSING
    )

    # Step 2: Download video and get metadata
    video_metadata = await ctx.step.run(
        "download-video",
        download_tiktok_video,
        tiktok_url,
        sample_id
    )

    # Step 3: Upload video file to our storage
    video_url = await ctx.step.run(
        "upload-video",
        upload_video_to_storage,
        video_metadata["video_path"],
        sample_id
    )

    # Step 4: Upload thumbnails/covers to our storage
    # Use origin_cover_url if available (higher quality), otherwise fall back to thumbnail_url
    cover_url_to_use = video_metadata.get("origin_cover_url") or video_metadata.get("thumbnail_url")
    media_urls = await ctx.step.run(
        "upload-media",
        upload_media_to_storage,
        sample_id,
        video_metadata.get("thumbnail_url"),
        cover_url_to_use
    )

    # Step 5: Extract audio (creates WAV and MP3, uploads to R2, returns URLs)
    audio_files = await ctx.step.run(
        "extract-audio",
        extract_audio_from_video,
        video_metadata["video_path"],
        video_metadata["temp_dir"],
        sample_id
    )

    # Step 6: Generate waveform (generates PNG, uploads to R2, returns URL)
    waveform_url = await ctx.step.run(
        "generate-waveform",
        generate_waveform,
        audio_files["wav_path"],
        video_metadata["temp_dir"],
        sample_id
    )

    # Step 7: Analyze audio features (BPM, key detection)
    audio_analysis = await ctx.step.run(
        "analyze-audio-features",
        analyze_audio_features,
        audio_files["wav_path"]
    )

    # Step 8: Update database with results (all URLs are from our storage)
    await ctx.step.run(
        "update-database",
        update_sample_complete,
        {
            "sample_id": sample_id,
            "metadata": video_metadata,
            "urls": {
                "video": video_url,
                "thumbnail": media_urls.get("thumbnail"),
                "cover": media_urls.get("cover"),
                "wav": audio_files["wav_url"],
                "mp3": audio_files["mp3_url"],
                "waveform": waveform_url
            },
            "analysis": audio_analysis,
            "audio_metadata": audio_files.get("metadata", {})
        }
    )

    # Step 9: Clean up temp files
    await ctx.step.run(
        "cleanup-temp-files",
        cleanup_temp_files,
        video_metadata["temp_dir"]
    )

    return {
        "sample_id": sample_id,
        "status": "completed",
        "video_url": video_url,
        "audio_url": audio_files["mp3_url"],
        "waveform_url": waveform_url
    }


async def update_sample_status(sample_id: str, status: ProcessingStatus) -> None:
    """Update sample processing status in database"""
    try:
        async with AsyncSessionLocal() as db:
            # Convert sample_id to UUID if it's a string
            if isinstance(sample_id, str):
                sample_uuid = uuid.UUID(sample_id)
            else:
                sample_uuid = sample_id

            query = select(Sample).where(Sample.id == sample_uuid)
            result = await db.execute(query)
            sample = result.scalars().first()

            if not sample:
                logger.error(f"Sample {sample_uuid} not found in database during update_sample_status!")
                raise ValueError(f"Sample {sample_uuid} not found - may have been deleted or never created")

            sample.status = status
            await db.commit()
            logger.info(f"Updated sample {sample_id} status to {status.value}")
    except Exception as e:
        logger.exception(f"Error updating sample {sample_id} status: {e}")
        raise


async def download_tiktok_video(url: str, sample_id: str) -> Dict[str, Any]:
    """Download TikTok video and extract metadata"""
    # Use a persistent temp directory for this sample
    temp_dir = Path(tempfile.gettempdir()) / f"sampletok_{sample_id}"
    temp_dir.mkdir(parents=True, exist_ok=True)

    try:
        downloader = TikTokDownloader()
        metadata = await downloader.download_video(url, str(temp_dir))

        # Fetch/update creator using creator service (with smart caching)
        creator_username = metadata.get('creator_username')
        if creator_username:
            try:
                logger.info(f"Getting or fetching creator for @{creator_username}")
                async with AsyncSessionLocal() as db:
                    creator_service = CreatorService(db)
                    creator = await creator_service.get_or_fetch_creator(creator_username)

                    if creator:
                        # Store creator ID in metadata to link the sample
                        metadata['tiktok_creator_id'] = str(creator.id)
                        logger.info(f"Linked creator @{creator.username} ({creator.follower_count} followers)")
                    else:
                        logger.warning(f"Could not fetch creator info for @{creator_username}")
            except Exception as e:
                logger.exception(f"Failed to get/fetch creator @{creator_username}: {e}")
                # Continue without creator link

        logger.info(f"Downloaded video: {metadata.get('aweme_id')} to {temp_dir}")
        metadata['temp_dir'] = str(temp_dir)  # Pass temp_dir to next steps
        return metadata
    except Exception as e:
        # Clean up on error
        import shutil
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        raise


async def extract_audio_from_video(video_path: str, temp_dir: str, sample_id: str) -> Dict[str, Any]:
    """Extract audio from video file, upload to storage, and return URLs"""
    # Use the same temp directory from download step
    processor = AudioProcessor()
    audio_paths = await processor.extract_audio(video_path, temp_dir)

    # Get audio metadata (duration, sample rate, etc.)
    audio_metadata = await processor.get_audio_metadata(audio_paths["wav"])

    logger.info(f"Extracted audio: WAV and MP3 created in {temp_dir}, duration={audio_metadata.get('duration'):.1f}s")

    # Upload files to R2 immediately to make this step idempotent
    storage = S3Storage()

    logger.info(f"Uploading audio files to R2 for sample {sample_id}")
    wav_url = await storage.upload_file(
        audio_paths["wav"],
        f"samples/{sample_id}/audio.wav"
    )
    mp3_url = await storage.upload_file(
        audio_paths["mp3"],
        f"samples/{sample_id}/audio.mp3"
    )
    logger.info(f"Successfully uploaded audio files to R2: WAV and MP3")

    return {
        "wav_url": wav_url,
        "mp3_url": mp3_url,
        "wav_path": audio_paths["wav"],  # Keep for waveform/analysis in same step
        "metadata": audio_metadata
    }


async def upload_video_to_storage(video_path: str, sample_id: str) -> str:
    """Upload video file to our storage and return URL"""
    storage = S3Storage()
    logger.info(f"Uploading video to storage for sample {sample_id}")

    video_url = await storage.upload_file(
        video_path,
        f"samples/{sample_id}/video.mp4"
    )
    logger.info(f"Successfully uploaded video to storage")

    return video_url


async def upload_media_to_storage(
    sample_id: str,
    thumbnail_url: Optional[str],
    cover_url: Optional[str]
) -> Dict[str, Optional[str]]:
    """Download and upload thumbnail and cover images to our storage"""
    storage = S3Storage()
    media_urls = {}

    # Upload thumbnail
    if thumbnail_url:
        logger.info(f"Downloading and uploading thumbnail for sample {sample_id}")
        stored_url = await storage.download_and_upload_url(
            thumbnail_url,
            f"samples/{sample_id}/thumbnail.jpg",
            "image/jpeg"
        )
        media_urls["thumbnail"] = stored_url
        if stored_url:
            logger.info(f"Successfully uploaded thumbnail")

    # Upload cover image
    if cover_url:
        logger.info(f"Downloading and uploading cover image for sample {sample_id}")
        stored_url = await storage.download_and_upload_url(
            cover_url,
            f"samples/{sample_id}/cover.jpg",
            "image/jpeg"
        )
        media_urls["cover"] = stored_url
        if stored_url:
            logger.info(f"Successfully uploaded cover image")

    return media_urls


async def generate_waveform(audio_path: str, temp_dir: str, sample_id: str) -> str:
    """Generate waveform visualization, upload to storage, and return URL"""
    # Use the same temp directory
    processor = AudioProcessor()
    waveform_path = await processor.generate_waveform(audio_path, temp_dir)
    logger.info(f"Generated waveform visualization in {temp_dir}")

    # Upload to R2 immediately
    storage = S3Storage()
    logger.info(f"Uploading waveform to R2 for sample {sample_id}")
    waveform_url = await storage.upload_file(
        waveform_path,
        f"samples/{sample_id}/waveform.png"
    )
    logger.info(f"Successfully uploaded waveform to R2")

    # Clean up waveform file
    import os
    try:
        os.remove(waveform_path)
        logger.info(f"Cleaned up local waveform file")
    except Exception as e:
        logger.warning(f"Failed to clean up waveform file: {e}")

    return waveform_url


async def analyze_audio_features(audio_path: str) -> Dict[str, Any]:
    """
    Analyze audio file to extract musical features
    Returns dict with BPM, key, scale, and confidence scores
    """
    try:
        analyzer = AudioAnalyzer()
        analysis = await analyzer.analyze_audio(audio_path)
        logger.info(f"Audio analysis complete: BPM={analysis.get('bpm')}, Key={analysis.get('key')} {analysis.get('scale')}")
        return analysis
    except Exception as e:
        logger.error(f"Error during audio analysis: {str(e)}")
        # Return empty analysis on failure - don't fail the entire pipeline
        return {
            'bpm': None,
            'key': None,
            'scale': None,
            'key_confidence': None
        }


# upload_to_storage function removed - files are now uploaded immediately after creation
# This makes the pipeline idempotent and resilient to step retries


def cleanup_temp_files(temp_dir: str) -> None:
    """Clean up temporary files after processing"""
    import shutil
    try:
        temp_path = Path(temp_dir)
        if temp_path.exists():
            shutil.rmtree(temp_path)
            logger.info(f"Cleaned up temp files at {temp_dir}")
    except Exception as e:
        logger.warning(f"Failed to clean up temp files: {e}")
        # Don't fail the whole process if cleanup fails


async def update_sample_complete(data: Dict[str, Any]) -> None:
    """Update sample with processing results"""
    try:
        async with AsyncSessionLocal() as db:
            sample_id = data["sample_id"]
            metadata = data["metadata"]
            urls = data["urls"]
            analysis = data.get("analysis", {})
            audio_metadata = data.get("audio_metadata", {})

            # Convert sample_id to UUID if it's a string
            if isinstance(sample_id, str):
                sample_uuid = uuid.UUID(sample_id)
            else:
                sample_uuid = sample_id

            logger.info(f"Looking for sample with ID: {sample_uuid}")
            query = select(Sample).where(Sample.id == sample_uuid)
            result = await db.execute(query)
            sample = result.scalars().first()

            if not sample:
                logger.error(f"Sample {sample_uuid} not found in database during update_sample_complete!")
                logger.error(f"Sample metadata: aweme_id={metadata.get('aweme_id')}, tiktok_id={metadata.get('tiktok_id')}")

                # Try to find by aweme_id as fallback
                aweme_id = metadata.get('aweme_id')
                if aweme_id:
                    logger.info(f"Attempting to find sample by aweme_id: {aweme_id}")
                    query = select(Sample).where(Sample.aweme_id == aweme_id)
                    result = await db.execute(query)
                    sample = result.scalars().first()
                    if sample:
                        logger.info(f"Found sample by aweme_id: {sample.id}")
                    else:
                        logger.error(f"Sample not found by aweme_id either. Sample may have been deleted.")
                        raise ValueError(f"Sample {sample_uuid} not found - may have been deleted or never created")
                else:
                    raise ValueError(f"Sample {sample_uuid} not found and no aweme_id available for fallback lookup")

            # Update metadata from TikTok API
            # Only set tiktok_id if it's not already set (avoid unique constraint errors during reprocessing)
            if not sample.tiktok_id and metadata.get("tiktok_id"):
                sample.tiktok_id = metadata.get("tiktok_id")
            sample.aweme_id = metadata.get("aweme_id")
            # Clean title by removing hashtags
            raw_title = metadata.get("title") or ""
            sample.title = remove_hashtags(raw_title)
            sample.region = metadata.get("region")
            sample.creator_username = metadata.get("creator_username")
            sample.creator_name = metadata.get("creator_name")
            sample.description = metadata.get("description")
            sample.view_count = metadata.get("view_count", 0)
            sample.like_count = metadata.get("like_count", 0)
            sample.comment_count = metadata.get("comment_count", 0)
            sample.share_count = metadata.get("share_count", 0)
            sample.upload_timestamp = metadata.get("upload_timestamp")

            # Extract hashtags from description and title
            description_text = metadata.get("description", "")
            title_text = metadata.get("title", "")
            combined_text = f"{title_text} {description_text}"
            hashtags = extract_hashtags(combined_text)
            if hashtags:
                sample.tags = hashtags
                logger.info(f"Extracted {len(hashtags)} hashtags: {hashtags}")

            # Use duration from audio metadata (extracted from actual audio file)
            sample.duration_seconds = audio_metadata.get("duration", metadata.get("duration"))

            # Update audio analysis results
            if analysis.get("bpm"):
                sample.bpm = analysis["bpm"]
                logger.info(f"Set BPM: {analysis['bpm']}")

            if analysis.get("key") and analysis.get("scale"):
                sample.key = f"{analysis['key']} {analysis['scale']}"
                logger.info(f"Set key: {sample.key}")

            # Update file URLs - All from our storage (R2/S3/GCS)
            sample.video_url = urls.get("video")
            sample.thumbnail_url = urls.get("thumbnail")
            sample.cover_url = urls.get("cover")
            sample.audio_url_wav = urls["wav"]
            sample.audio_url_mp3 = urls["mp3"]
            sample.waveform_url = urls["waveform"]

            # Calculate video file size if available
            if metadata.get("file_size"):
                sample.file_size_video = metadata["file_size"]

            # Link to TikTok creator if available
            tiktok_creator_id = metadata.get("tiktok_creator_id")
            if tiktok_creator_id:
                sample.tiktok_creator_id = uuid.UUID(tiktok_creator_id)
                logger.info(f"Linked sample to creator {tiktok_creator_id}")

            # Mark as completed
            sample.status = ProcessingStatus.COMPLETED

            await db.commit()
            logger.info(f"Sample {sample_id} processing completed successfully")
    except Exception as e:
        logger.exception(f"Error updating sample {sample_id} complete: {e}")
        raise


# Error handler function
@inngest_client.create_function(
    fn_id="handle-processing-error",
    trigger=inngest.TriggerEvent(event="tiktok/processing.failed")
)
async def handle_processing_error(ctx: inngest.Context) -> None:
    """Handle processing failures"""
    event_data = ctx.event.data
    sample_id = event_data.get("sample_id")
    error_message = event_data.get("error", "Unknown error occurred")

    async def update_failed_status():
        async with AsyncSessionLocal() as db:
            query = select(Sample).where(Sample.id == uuid.UUID(sample_id))
            result = await db.execute(query)
            sample = result.scalar_one()

            sample.status = ProcessingStatus.FAILED
            sample.error_message = error_message

            await db.commit()
            logger.exception(f"Sample {sample_id} processing failed: {error_message}")

    await ctx.step.run("mark-as-failed", update_failed_status)


# Collection processing function
@inngest_client.create_function(
    fn_id="process-collection",
    trigger=inngest.TriggerEvent(event="collection/import.submitted"),
    retries=3
)
async def process_collection(ctx: inngest.Context) -> Dict[str, Any]:
    """
    Process a TikTok collection:
    1. Fetch all videos from the collection
    2. For each video:
       - Check if sample exists
       - If not, create sample and trigger processing
       - Link to collection via CollectionSample
    3. Mark collection as completed
    """
    event_data = ctx.event.data
    collection_id = event_data.get("collection_id")
    user_id = None
    video_list = []
    processed_count = 0

    try:
        # Fetch collection details from database (single source of truth)
        collection_data = await ctx.step.run(
            f"fetch-collection-from-db-{collection_id}",
            fetch_collection_from_db,
            collection_id
        )

        tiktok_collection_id = collection_data["tiktok_collection_id"]
        user_id = collection_data["user_id"]
        cursor = collection_data["current_cursor"]
        max_videos = settings.MAX_VIDEOS_PER_BATCH

        logger.info(f"Processing collection {collection_id} (TikTok ID: {tiktok_collection_id}) for user {user_id} from cursor {cursor}")

        # Step 1: Update collection status to processing
        await ctx.step.run(
            f"update-collection-status-processing-{collection_id}",
            update_collection_status,
            collection_id,
            CollectionStatus.processing
        )

        # Step 2: Fetch videos from TikTok collection (with cursor for pagination)
        fetch_result = await ctx.step.run(
            f"fetch-collection-videos-{collection_id}-cursor{cursor}",
            fetch_collection_videos_with_cursor,
            tiktok_collection_id,
            cursor,
            max_videos
        )

        video_list = fetch_result["videos"]
        next_cursor = fetch_result.get("next_cursor")
        has_more = fetch_result.get("has_more", False)

        logger.info(f"Fetched {len(video_list)} videos from collection {tiktok_collection_id}, has_more: {has_more}")

        # Step 3: Update total video count if this is the first batch and count differs
        # (This happens when invalid/deleted videos are filtered out)
        if cursor == 0 and len(video_list) != collection_data["total_video_count"]:
            await ctx.step.run(
                f"update-total-video-count-{collection_id}",
                update_collection_total_count,
                collection_id,
                len(video_list)
            )

        # Step 4: Get current processed count from DB to accumulate correctly
        collection_data_updated = await ctx.step.run(
            f"get-current-processed-count-{collection_id}",
            fetch_collection_from_db,
            collection_id
        )
        existing_processed_count = collection_data_updated.get("processed_count", 0)
        processed_count = existing_processed_count

        # Step 4.5: Filter out videos that are already in this collection (OPTIMIZATION)
        filtered_result = await ctx.step.run(
            f"filter-new-videos-{collection_id}-cursor{cursor}",
            filter_new_videos_for_collection,
            collection_id,
            video_list,
            cursor
        )
        new_videos, new_positions = filtered_result

        logger.info(f"After filtering: {len(new_videos)} new videos to process (out of {len(video_list)} fetched)")

        # If no new videos, mark as completed and return early
        if len(new_videos) == 0:
            logger.info(f"No new videos found for collection {collection_id}, completing batch")
            await ctx.step.run(
                f"mark-collection-completed-early-{collection_id}",
                complete_collection,
                collection_id,
                next_cursor,
                has_more
            )
            return {
                "collection_id": collection_id,
                "status": "completed",
                "processed_count": 0,
                "total_videos": len(video_list),
                "new_videos": 0,
                "has_more": has_more,
                "next_cursor": next_cursor,
                "message": "No new videos found - all videos already in collection"
            }

        # Process each NEW video (optimized loop)
        for idx, (video_data, absolute_position) in enumerate(zip(new_videos, new_positions)):
            try:
                aweme_id = video_data.get('aweme_id', f'unknown-{absolute_position}')
                logger.info(f"Processing NEW video {idx + 1}/{len(new_videos)} (absolute position {absolute_position}): {aweme_id}")

                # CRITICAL: Include collection_id in step ID to prevent Inngest from reusing cached results
                # when the same collection is imported multiple times
                unique_step_id = f"process-video-{collection_id}-{aweme_id}" if aweme_id and aweme_id != f'unknown-{absolute_position}' else f"process-video-{collection_id}-pos{absolute_position}"

                sample_id = await ctx.step.run(
                    unique_step_id,
                    process_collection_video,
                    collection_id,
                    user_id,
                    video_data,
                    absolute_position
                )

                if sample_id:
                    processed_count += 1
                    logger.info(f"Successfully processed NEW video {idx + 1}, sample_id: {sample_id}, total processed: {processed_count}")
                    # Update processed count after each video
                    await ctx.step.run(
                        f"update-processed-count-{collection_id}-pos{absolute_position}",
                        update_collection_processed_count,
                        collection_id,
                        processed_count
                    )
                else:
                    logger.warning(f"NEW video {idx + 1} returned None - check for errors")
                    # Refund 1 credit for failed video
                    await ctx.step.run(
                        f"refund-credit-{collection_id}-pos{absolute_position}",
                        refund_credit_for_failed_video,
                        user_id
                    )

            except Exception as e:
                logger.exception(f"Exception processing NEW video at position {absolute_position} (index {idx}): {str(e)}")
                # Refund 1 credit for failed video
                await ctx.step.run(
                    f"refund-credit-exception-{collection_id}-pos{absolute_position}",
                    refund_credit_for_failed_video,
                    user_id
                )
                # Continue with next video instead of failing entire collection

        # Step 5: Mark collection batch as completed and update pagination
        await ctx.step.run(
            f"mark-collection-completed-{collection_id}",
            complete_collection,
            collection_id,
            next_cursor,
            has_more
        )

        new_videos_count = len(new_videos)
        return {
            "collection_id": collection_id,
            "status": "completed",
            "processed_count": processed_count,
            "total_videos": len(video_list),
            "new_videos": new_videos_count,
            "has_more": has_more,
            "next_cursor": next_cursor,
            "message": f"Processed {new_videos_count} new video{'s' if new_videos_count != 1 else ''}"
        }

    except Exception as e:
        # Critical failure - handle cleanup and refunds
        error_message = f"Collection processing failed: {str(e)}"
        logger.exception(f"CRITICAL: {error_message}")

        # Calculate how many videos were charged but not processed
        # If we fetched the video list, we know how many credits were charged
        videos_charged = len(video_list)
        videos_not_processed = videos_charged - processed_count

        # Refund credits for unprocessed videos
        if videos_not_processed > 0 and user_id:
            try:
                await ctx.step.run(
                    f"refund-unprocessed-videos-{collection_id}",
                    refund_credits_for_failed_collection,
                    user_id,
                    videos_not_processed
                )
                logger.info(f"Refunded {videos_not_processed} credits for collection {collection_id} after critical failure")
            except Exception as refund_error:
                logger.exception(f"Failed to refund credits after collection failure: {refund_error}")

        # Mark collection as failed
        try:
            await ctx.step.run(
                f"mark-collection-failed-{collection_id}",
                mark_collection_failed,
                collection_id,
                error_message
            )
        except Exception as status_error:
            logger.exception(f"Failed to mark collection as failed: {status_error}")

        # Re-raise the exception so Inngest knows the function failed
        raise


async def filter_new_videos_for_collection(
    collection_id: str,
    video_list: List[Dict[str, Any]],
    cursor: int
) -> Tuple[List[Dict[str, Any]], List[int]]:
    """
    Filter out videos that are already linked to this collection.
    Returns: (new_videos, new_positions) - lists of videos and their positions that need processing

    This is a critical optimization that prevents re-processing existing videos during sync.
    """
    try:
        async with AsyncSessionLocal() as db:
            # Extract all video_ids from the batch
            video_ids = []
            aweme_ids = []
            for video_data in video_list:
                video_id = video_data.get('video_id')
                aweme_id = video_data.get('aweme_id')
                if video_id:
                    video_ids.append(video_id)
                if aweme_id:
                    aweme_ids.append(aweme_id)

            if not video_ids and not aweme_ids:
                logger.warning("No valid video IDs found in batch")
                return [], []

            # Step 1: Bulk query to find all samples that exist for these video_ids/aweme_ids
            existing_samples_query = select(Sample.id, Sample.tiktok_id, Sample.aweme_id).where(
                or_(
                    Sample.tiktok_id.in_(video_ids) if video_ids else False,
                    Sample.aweme_id.in_(aweme_ids) if aweme_ids else False
                )
            )
            result = await db.execute(existing_samples_query)
            existing_samples = result.all()

            # Create lookup sets for fast checking
            existing_video_ids = {s.tiktok_id for s in existing_samples if s.tiktok_id}
            existing_aweme_ids = {s.aweme_id for s in existing_samples if s.aweme_id}
            existing_sample_ids = {s.id for s in existing_samples}

            logger.info(f"Found {len(existing_samples)} existing samples for {len(video_ids)} videos")

            # Step 2: Bulk query to find which of these samples are already linked to this collection
            if existing_sample_ids:
                linked_samples_query = select(CollectionSample.sample_id).where(
                    (CollectionSample.collection_id == uuid.UUID(collection_id)) &
                    (CollectionSample.sample_id.in_(existing_sample_ids))
                )
                linked_result = await db.execute(linked_samples_query)
                linked_samples = linked_result.scalars().all()
                linked_sample_ids = set(linked_samples)

                # Map video_ids/aweme_ids to sample_ids for quick lookup
                video_id_to_sample_id = {s.tiktok_id: s.id for s in existing_samples if s.tiktok_id}
                aweme_id_to_sample_id = {s.aweme_id: s.id for s in existing_samples if s.aweme_id}
            else:
                linked_sample_ids = set()
                video_id_to_sample_id = {}
                aweme_id_to_sample_id = {}

            logger.info(f"Found {len(linked_sample_ids)} samples already linked to collection")

            # Step 3: Filter videos to only include new ones
            new_videos = []
            new_positions = []

            for batch_position, video_data in enumerate(video_list):
                absolute_position = cursor + batch_position
                video_id = video_data.get('video_id')
                aweme_id = video_data.get('aweme_id')

                # Check if this video is already linked to the collection
                is_linked = False

                if video_id and video_id in video_id_to_sample_id:
                    sample_id = video_id_to_sample_id[video_id]
                    if sample_id in linked_sample_ids:
                        is_linked = True

                if aweme_id and aweme_id in aweme_id_to_sample_id:
                    sample_id = aweme_id_to_sample_id[aweme_id]
                    if sample_id in linked_sample_ids:
                        is_linked = True

                if not is_linked:
                    new_videos.append(video_data)
                    new_positions.append(absolute_position)
                else:
                    logger.info(f"Skipping video at position {absolute_position} (already in collection)")

            logger.info(f"Filtered to {len(new_videos)} new videos out of {len(video_list)} total")
            return new_videos, new_positions

    except Exception as e:
        logger.exception(f"Error filtering videos for collection: {e}")
        # On error, return all videos to be safe (fallback to old behavior)
        return video_list, list(range(cursor, cursor + len(video_list)))


async def fetch_collection_from_db(collection_id: str) -> Dict[str, Any]:
    """Fetch collection details from database"""
    try:
        async with AsyncSessionLocal() as db:
            query = select(Collection).where(Collection.id == uuid.UUID(collection_id))
            result = await db.execute(query)
            collection = result.scalar_one()

            return {
                "tiktok_collection_id": collection.tiktok_collection_id,
                "user_id": str(collection.user_id),
                "current_cursor": collection.current_cursor,
                "total_video_count": collection.total_video_count,
                "name": collection.name,
                "tiktok_username": collection.tiktok_username,
                "processed_count": collection.processed_count
            }
    except Exception as e:
        logger.exception(f"Error fetching collection {collection_id} from database: {e}")
        raise


async def refund_credit_for_failed_video(user_id: str) -> None:
    """Refund 1 credit to user when a video fails to process"""
    try:
        async with AsyncSessionLocal() as db:
            await refund_credits_atomic(db, uuid.UUID(user_id), 1)
            logger.info(f"Refunded 1 credit to user {user_id} for failed video")
    except Exception as e:
        logger.exception(f"Error refunding credit to user {user_id}: {e}")
        # Don't raise - we don't want refund failure to stop collection processing


async def refund_credits_for_failed_collection(user_id: str, credits_to_refund: int) -> None:
    """Refund multiple credits to user when collection processing fails"""
    try:
        async with AsyncSessionLocal() as db:
            await refund_credits_atomic(db, uuid.UUID(user_id), credits_to_refund)
            logger.info(f"Refunded {credits_to_refund} credits to user {user_id} for failed collection")
    except Exception as e:
        logger.exception(f"Error refunding {credits_to_refund} credits to user {user_id}: {e}")
        # Don't raise - we don't want refund failure to stop collection processing


async def mark_collection_failed(collection_id: str, error_message: str) -> None:
    """Mark collection as failed with error message"""
    try:
        async with AsyncSessionLocal() as db:
            query = select(Collection).where(Collection.id == uuid.UUID(collection_id))
            result = await db.execute(query)
            collection = result.scalar_one()
            collection.status = CollectionStatus.failed
            collection.error_message = error_message
            await db.commit()
            logger.info(f"Marked collection {collection_id} as failed: {error_message}")
    except Exception as e:
        logger.exception(f"Error marking collection {collection_id} as failed: {e}")
        # Don't raise - we've already logged the error


async def update_collection_status(collection_id: str, status: CollectionStatus) -> None:
    """Update collection processing status"""
    try:
        async with AsyncSessionLocal() as db:
            query = select(Collection).where(Collection.id == uuid.UUID(collection_id))
            result = await db.execute(query)
            collection = result.scalar_one()
            collection.status = status
            if status == CollectionStatus.processing:
                collection.started_at = datetime.utcnow()
            await db.commit()
            logger.info(f"Updated collection {collection_id} status to {status.value}")
    except Exception as e:
        logger.exception(f"Error updating collection {collection_id} status: {e}")
        raise


async def fetch_collection_videos_with_cursor(
    tiktok_collection_id: str,
    cursor: int,
    max_videos: int
) -> Dict[str, Any]:
    """
    Fetch videos from a TikTok collection with pagination

    Note: The TikTok API is sometimes inconsistent and may return different numbers
    of videos on subsequent requests. We retry multiple times and return the response
    with the most videos to maximize completeness.
    """
    try:
        logger.info(f"Fetching videos for collection_id={tiktok_collection_id}, cursor={cursor}, max_videos={max_videos}")
        collection_service = TikTokCollectionService()

        # Retry multiple times to handle API inconsistencies
        best_result = None
        max_video_count = 0
        max_attempts = settings.TIKTOK_API_RETRY_ATTEMPTS

        for attempt in range(max_attempts):
            try:
                result = await collection_service.fetch_collection_posts(
                    collection_id=tiktok_collection_id,
                    count=max_videos,
                    cursor=cursor
                )

                data = result.get('data', {})
                videos = data.get('videos', [])
                video_count = len(videos)

                logger.info(f"Attempt {attempt + 1}/{max_attempts}: Got {video_count} videos")

                # Keep the result with the most videos
                if video_count > max_video_count:
                    max_video_count = video_count
                    best_result = result
                    logger.info(f"New best result: {video_count} videos")

                # Small delay between retries
                if attempt < max_attempts - 1:
                    await asyncio.sleep(0.5)

            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed: {e}")
                if attempt == max_attempts - 1:  # Last attempt
                    raise

        if best_result is None:
            raise ValueError("All fetch attempts failed")

        data = best_result.get('data', {})
        videos = data.get('videos', [])

        # Filter out invalid videos (deleted/private/unavailable)
        # Only need video_id and author username to build URL - aweme_id comes from download API
        valid_videos = [
            video for video in videos
            if (video.get('video_id') and
                video.get('author', {}).get('unique_id'))
        ]

        logger.info(f"Using best result with {len(videos)} total videos, {len(valid_videos)} valid videos")

        return {
            "videos": valid_videos,
            "next_cursor": data.get('cursor'),
            "has_more": data.get('hasMore', False)
        }
    except Exception as e:
        logger.exception(f"Error fetching collection videos: {e}")
        raise


async def process_collection_video(
    collection_id: str,
    user_id: str,
    video_data: Dict[str, Any],
    position: int
) -> Optional[str]:
    """
    Process a single video from a collection:
    1. Check if sample exists
    2. If not, create and trigger processing
    3. Link to collection
    """
    try:
        logger.info(f"process_collection_video called with video_data keys: {list(video_data.keys())}")
        async with AsyncSessionLocal() as db:
            # Extract video identifiers
            aweme_id = video_data.get('aweme_id')  # Optional, will be fetched by download API
            video_id = video_data.get('video_id')
            author = video_data.get('author', {})
            author_unique_id = author.get('unique_id', '')

            if not video_id or not author_unique_id:
                logger.warning(f"Missing required fields at position {position}: video_id={video_id}, username={author_unique_id}")
                return None

            # Build TikTok URL (format: https://www.tiktok.com/@username/video/{video_id})
            tiktok_url = f"https://www.tiktok.com/@{author_unique_id}/video/{video_id}"

            logger.info(f"Processing video: {tiktok_url}")

            # Check if sample already exists (by video_id, or aweme_id if available)
            if aweme_id:
                query = select(Sample).where(
                    or_(
                        Sample.tiktok_id == video_id,
                        Sample.aweme_id == aweme_id
                    )
                )
            else:
                query = select(Sample).where(Sample.tiktok_id == video_id)

            result = await db.execute(query)
            existing_sample = result.scalars().first()

            sample_id = None

            if existing_sample:
                logger.info(f"Sample already exists for aweme_id {aweme_id}: {existing_sample.id}")
                sample_id = existing_sample.id
                # Don't auto-create downloads - user must explicitly download
            else:
                # Create new sample and trigger processing
                logger.info(f"Creating new sample for aweme_id {aweme_id}, video_id {video_id}, URL: {tiktok_url}")
                sample = Sample(
                    tiktok_url=tiktok_url,
                    aweme_id=aweme_id,
                    tiktok_id=video_id,
                    status=ProcessingStatus.PENDING
                )
                db.add(sample)
                logger.info(f"Sample added to session, about to commit...")

                try:
                    await db.commit()
                    logger.info(f"Sample committed to database")
                    await db.refresh(sample)
                    logger.info(f"Sample refreshed, ID: {sample.id}, aweme_id: {sample.aweme_id}, status: {sample.status.value}")
                    sample_id = sample.id
                except IntegrityError:
                    # Race condition: another process created this sample
                    # Roll back and fetch the existing sample
                    await db.rollback()
                    logger.info(f"Sample already exists (race condition) for video_id {video_id}, fetching...")

                    # Re-query to get the existing sample
                    if aweme_id:
                        refetch_query = select(Sample).where(
                            or_(
                                Sample.tiktok_id == video_id,
                                Sample.aweme_id == aweme_id
                            )
                        )
                    else:
                        refetch_query = select(Sample).where(Sample.tiktok_id == video_id)

                    refetch_result = await db.execute(refetch_query)
                    existing_sample = refetch_result.scalars().first()

                    if not existing_sample:
                        raise Exception(f"Failed to create or fetch sample for video_id {video_id}")

                    logger.info(f"Found existing sample: {existing_sample.id}")
                    sample_id = existing_sample.id

                # Verify the sample was actually committed by querying it again
                verify_query = select(Sample).where(Sample.id == sample_id)
                verify_result = await db.execute(verify_query)
                verify_sample = verify_result.scalars().first()
                if verify_sample:
                    logger.info(f"✓ Verified sample {sample_id} exists in database after commit")
                else:
                    logger.error(f"✗ WARNING: Sample {sample_id} NOT FOUND in database immediately after commit!")

                # Trigger Inngest processing for this sample
                try:
                    logger.info(f"Sending Inngest event for sample {sample.id}")
                    await inngest_client.send(
                        inngest.Event(
                            name="tiktok/video.submitted",
                            data={
                                "sample_id": str(sample.id),
                                "url": tiktok_url
                            }
                        )
                    )
                    logger.info(f"✓ Successfully triggered processing for sample {sample.id}")

                    # Note: We'll create the UserDownload after processing completes
                    # For now, just create the CollectionSample link
                except Exception as e:
                    logger.error(f"✗ Failed to trigger processing for sample {sample.id}: {e}")

            # Create CollectionSample link
            if sample_id:
                # Check if link already exists
                link_query = select(CollectionSample).where(
                    (CollectionSample.collection_id == uuid.UUID(collection_id)) &
                    (CollectionSample.sample_id == sample_id)
                )
                link_result = await db.execute(link_query)
                existing_link = link_result.scalars().first()

                if not existing_link:
                    collection_sample = CollectionSample(
                        collection_id=uuid.UUID(collection_id),
                        sample_id=sample_id,
                        position=position
                    )
                    db.add(collection_sample)

                await db.commit()
                return str(sample_id)

            return None

    except Exception as e:
        logger.exception(f"Error processing collection video at position {position}: {e}")
        return None


async def update_collection_processed_count(collection_id: str, count: int) -> None:
    """Update the processed count for a collection"""
    try:
        async with AsyncSessionLocal() as db:
            query = select(Collection).where(Collection.id == uuid.UUID(collection_id))
            result = await db.execute(query)
            collection = result.scalar_one()
            collection.processed_count = count
            await db.commit()
    except Exception as e:
        logger.exception(f"Error updating collection processed count: {e}")


async def update_collection_total_count(collection_id: str, total_count: int) -> None:
    """Update the total video count for a collection (after filtering invalid videos)"""
    try:
        async with AsyncSessionLocal() as db:
            query = select(Collection).where(Collection.id == uuid.UUID(collection_id))
            result = await db.execute(query)
            collection = result.scalar_one()
            old_count = collection.total_video_count
            collection.total_video_count = total_count
            await db.commit()
            logger.info(f"Updated collection {collection_id} total_video_count from {old_count} to {total_count}")
    except Exception as e:
        logger.exception(f"Error updating collection total count: {e}")


async def complete_collection(
    collection_id: str,
    next_cursor: Optional[int],
    has_more: bool
) -> None:
    """Mark collection batch as completed and update pagination info"""
    try:
        async with AsyncSessionLocal() as db:
            query = select(Collection).where(Collection.id == uuid.UUID(collection_id))
            result = await db.execute(query)
            collection = result.scalar_one()
            collection.status = CollectionStatus.completed
            collection.completed_at = datetime.utcnow()
            collection.next_cursor = next_cursor
            collection.has_more = has_more
            await db.commit()
            logger.info(f"Marked collection {collection_id} batch as completed (has_more: {has_more})")
    except Exception as e:
        logger.exception(f"Error completing collection: {e}")
        raise


# Collection error handler
@inngest_client.create_function(
    fn_id="handle-collection-error",
    trigger=inngest.TriggerEvent(event="collection/processing.failed")
)
async def handle_collection_error(ctx: inngest.Context) -> None:
    """Handle collection processing failures"""
    event_data = ctx.event.data
    collection_id = event_data.get("collection_id")
    error_message = event_data.get("error", "Unknown error occurred")

    async def update_failed_status():
        async with AsyncSessionLocal() as db:
            query = select(Collection).where(Collection.id == uuid.UUID(collection_id))
            result = await db.execute(query)
            collection = result.scalar_one()

            collection.status = CollectionStatus.failed
            collection.error_message = error_message

            await db.commit()
            logger.exception(f"Collection {collection_id} processing failed: {error_message}")

    await ctx.step.run("mark-collection-as-failed", update_failed_status)


@inngest_client.create_function(
    fn_id="test-function",
    trigger=inngest.TriggerEvent(event="test/hello")
)
def test_function(ctx: inngest.Context):
    """Simple test function for testing Inngest integration"""
    return {"status": "success", "message": "Hello from test function"}


def get_all_functions():
    """Return all Inngest functions to be served"""
    return [
        process_tiktok_video,
        handle_processing_error,
        process_collection,
        handle_collection_error,
        test_function
    ]