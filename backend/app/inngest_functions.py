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
from pydantic import BaseModel, Field, validator
from uuid import UUID

from app.core.config import settings
from app.services.tiktok.downloader import TikTokDownloader
from app.services.instagram.downloader import InstagramDownloader
from app.services.audio.processor import AudioProcessor
from app.services.audio.analyzer import AudioAnalyzer
from app.services.audio.lalal_service import LalalAIService
from app.services.storage.s3 import S3Storage
from app.models import Sample, ProcessingStatus, TikTokCreator, Collection, CollectionSample, CollectionStatus, Stem, StemType, StemProcessingStatus, InstagramEngagement
from app.models.instagram_creator import InstagramCreator
from app.models.user import UserDownload
from app.core.database import AsyncSessionLocal
from sqlalchemy import select, or_
from sqlalchemy.exc import IntegrityError
from app.services.tiktok.creator_service import CreatorService
from app.services.instagram.creator_service import CreatorService as InstagramCreatorService
from app.services.instagram.graph_api_service import InstagramGraphAPIService
from app.services.tiktok.collection_service import TikTokCollectionService
from app.services.credit_service import refund_credits_atomic, CreditService
from app.services.email_service import email_service
from app.utils import extract_hashtags, remove_hashtags, utcnow_naive
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

    # Step 7: Generate HLS stream (generates m3u8 + segments, uploads to R2, returns playlist URL)
    hls_url = await ctx.step.run(
        "generate-hls-stream",
        generate_hls_stream,
        audio_files["wav_path"],  # Use WAV path (mp3_path not returned by extract_audio)
        video_metadata["temp_dir"],
        sample_id
    )

    # Step 8: Analyze audio features (BPM, key detection)
    audio_analysis = await ctx.step.run(
        "analyze-audio-features",
        analyze_audio_features,
        audio_files["wav_path"]
    )

    # Step 9: Update database with results (all URLs are from our storage)
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
                "hls": hls_url,
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


@inngest_client.create_function(
    fn_id="process-instagram-video",
    trigger=inngest.TriggerEvent(event="instagram/video.submitted"),
    retries=3
)
async def process_instagram_video(ctx: inngest.Context) -> Dict[str, Any]:
    """
    Process an Instagram video through multiple steps:
    1. Download video from Instagram
    2. Upload video to our storage
    3. Upload thumbnail to our storage
    4. Extract audio (WAV and MP3)
    5. Generate waveform visualization
    6. Generate HLS stream
    7. Analyze audio features (BPM, key detection)
    8. Update database with results
    9. Clean up temp files
    """
    event_data = ctx.event.data
    sample_id = event_data.get("sample_id")
    instagram_url = event_data.get("url")
    shortcode = event_data.get("shortcode")

    logger.info(f"Processing Instagram video: {instagram_url} for sample: {sample_id}")

    # Step 1: Update status to processing
    await ctx.step.run(
        "update-status-processing",
        update_sample_status,
        sample_id,
        ProcessingStatus.PROCESSING
    )

    # Step 2: Download video and get metadata
    video_metadata = await ctx.step.run(
        "download-instagram-video",
        download_instagram_video,
        shortcode,
        sample_id
    )

    # Step 3: Upload video file to our storage
    video_url = await ctx.step.run(
        "upload-video",
        upload_video_to_storage,
        video_metadata["video_path"],
        sample_id
    )

    # Step 4: Upload thumbnail to our storage
    media_urls = await ctx.step.run(
        "upload-media",
        upload_media_to_storage,
        sample_id,
        video_metadata.get("thumbnail_url"),
        None  # Instagram doesn't have a separate cover URL
    )

    # Step 5: Extract audio (creates WAV and MP3, uploads to storage, returns URLs)
    audio_files = await ctx.step.run(
        "extract-audio",
        extract_audio_from_video,
        video_metadata["video_path"],
        video_metadata["temp_dir"],
        sample_id
    )

    # Step 6: Generate waveform (generates PNG, uploads to storage, returns URL)
    waveform_url = await ctx.step.run(
        "generate-waveform",
        generate_waveform,
        audio_files["wav_path"],
        video_metadata["temp_dir"],
        sample_id
    )

    # Step 7: Generate HLS stream (generates m3u8 + segments, uploads to storage, returns playlist URL)
    hls_url = await ctx.step.run(
        "generate-hls-stream",
        generate_hls_stream,
        audio_files["wav_path"],
        video_metadata["temp_dir"],
        sample_id
    )

    # Step 8: Analyze audio features (BPM, key detection)
    audio_analysis = await ctx.step.run(
        "analyze-audio-features",
        analyze_audio_features,
        audio_files["wav_path"]
    )

    # Step 9: Update database with results (all URLs are from our storage)
    await ctx.step.run(
        "update-database",
        update_instagram_sample_complete,
        {
            "sample_id": sample_id,
            "metadata": video_metadata,
            "urls": {
                "video": video_url,
                "thumbnail": media_urls.get("thumbnail"),
                "wav": audio_files["wav_url"],
                "mp3": audio_files["mp3_url"],
                "hls": hls_url,
                "waveform": waveform_url
            },
            "analysis": audio_analysis,
            "audio_metadata": audio_files.get("metadata", {})
        }
    )

    # Step 10: Attempt to send email if available
    email_result = await ctx.step.run(
        "send-sample-email",
        send_instagram_sample_email,
        sample_id,
        event_data.get("engagement_id"),
        {
            "bpm": audio_analysis.get("bpm"),
            "key": audio_analysis.get("key"),
            "creator_username": video_metadata.get("creator", {}).get("username")
        }
    )

    # Step 11: Post Instagram comment with teaser
    await ctx.step.run(
        "post-instagram-comment",
        post_instagram_comment,
        event_data.get("engagement_id"),
        event_data.get("media_id"),
        {
            "bpm": audio_analysis.get("bpm"),
            "key": audio_analysis.get("key"),
            "email_sent": email_result.get("email_sent", False)
        }
    )

    # Step 12: Clean up temp files
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
        "waveform_url": waveform_url,
        "email_sent": email_result.get("email_sent", False)
    }


async def update_sample_status(sample_id: str, status: ProcessingStatus) -> None:
    """Update sample processing status in database with retry logic for race conditions"""
    max_retries = 3
    retry_delay = 0.5  # Start with 500ms delay

    for attempt in range(max_retries):
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
                    if attempt < max_retries - 1:
                        # Sample not found, but we have retries left - likely a visibility race condition
                        logger.warning(
                            f"Sample {sample_uuid} not found (attempt {attempt + 1}/{max_retries}). "
                            f"Retrying in {retry_delay}s... This can happen when processing starts "
                            f"before the database transaction is fully visible."
                        )
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                        continue
                    else:
                        # Final attempt failed
                        logger.error(
                            f"Sample {sample_uuid} not found after {max_retries} attempts! "
                            f"Sample may have been deleted or database has a serious consistency issue."
                        )
                        raise ValueError(
                            f"Sample {sample_uuid} not found after {max_retries} retries - "
                            f"may have been deleted or database transaction not visible"
                        )

                # Sample found - update status
                sample.status = status
                await db.commit()
                logger.info(f"Updated sample {sample_id} status to {status.value}")
                return  # Success - exit retry loop

        except ValueError:
            # ValueError is raised when sample not found after all retries
            raise
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


async def download_instagram_video(shortcode: str, sample_id: str) -> Dict[str, Any]:
    """Download Instagram video and extract metadata"""
    # Use a persistent temp directory for this sample
    temp_dir = Path(tempfile.gettempdir()) / f"sampletok_{sample_id}"
    temp_dir.mkdir(parents=True, exist_ok=True)

    try:
        downloader = InstagramDownloader()
        metadata = await downloader.download_video(shortcode, str(temp_dir))

        # Get or create Instagram creator using creator service (with smart caching)
        # Instagram API returns creator data with the post, so we just need to cache it
        if metadata.get('creator_instagram_id') and metadata.get('creator_username'):
            try:
                logger.info(f"Getting or creating Instagram creator @{metadata['creator_username']}")
                async with AsyncSessionLocal() as db:
                    instagram_creator_service = InstagramCreatorService(db)
                    creator = await instagram_creator_service.get_or_create_creator(metadata)

                    if creator:
                        # Store creator ID in metadata to link the sample
                        metadata['instagram_creator_id'] = str(creator.id)
                        logger.info(f"Linked Instagram creator @{creator.username}")
                    else:
                        logger.warning(f"Could not create Instagram creator @{metadata['creator_username']}")
            except Exception as e:
                logger.exception(f"Failed to get/create Instagram creator: {e}")
                # Continue without creator link

        logger.info(f"Downloaded Instagram video: {shortcode} to {temp_dir}")
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


async def generate_hls_stream(audio_path: str, temp_dir: str, sample_id: str) -> str:
    """Generate HLS stream, upload playlist and segments to storage, and return playlist URL"""
    # Use the same temp directory
    processor = AudioProcessor()
    hls_data = await processor.generate_hls_stream(audio_path, temp_dir)
    logger.info(f"Generated HLS stream: {len(hls_data['segments'])} segments")

    # Upload to R2 immediately
    storage = S3Storage()

    # Upload playlist file
    logger.info(f"Uploading HLS playlist to R2 for sample {sample_id}")
    playlist_url = await storage.upload_file(
        hls_data['playlist'],
        f"samples/{sample_id}/hls/playlist.m3u8"
    )
    logger.info(f"Successfully uploaded HLS playlist to R2")

    # Upload all segment files
    logger.info(f"Uploading {len(hls_data['segments'])} HLS segments to R2")
    for i, segment_path in enumerate(hls_data['segments']):
        segment_filename = Path(segment_path).name
        await storage.upload_file(
            segment_path,
            f"samples/{sample_id}/hls/{segment_filename}"
        )
        logger.info(f"Uploaded HLS segment {i+1}/{len(hls_data['segments'])}")

    logger.info(f"Successfully uploaded all HLS segments to R2")

    # Clean up HLS directory
    import shutil
    try:
        shutil.rmtree(hls_data['hls_dir'])
        logger.info(f"Cleaned up local HLS directory")
    except Exception as e:
        logger.warning(f"Failed to clean up HLS directory: {e}")

    return playlist_url


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


async def send_instagram_sample_email(
    sample_id: str,
    engagement_id: Optional[str],
    metadata: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Attempt to send sample ready email to Instagram creator.

    Flow:
    1. Get engagement record
    2. Get sample record
    3. Check if email is available
    4. Send email via Postmark
    5. Update engagement record with email_sent status

    Args:
        sample_id: Sample UUID
        engagement_id: InstagramEngagement UUID
        metadata: Dict with bpm, key, creator_username

    Returns:
        Dict with email_sent status and reason
    """
    logger.info(f"Attempting to send email for sample_id={sample_id}, engagement_id={engagement_id}")

    if not engagement_id:
        logger.warning("No engagement_id provided, cannot send email")
        return {"email_sent": False, "reason": "no_engagement_id"}

    try:
        async with AsyncSessionLocal() as db:
            # Get engagement record
            engagement_uuid = uuid.UUID(engagement_id) if isinstance(engagement_id, str) else engagement_id
            query = select(InstagramEngagement).where(InstagramEngagement.id == engagement_uuid)
            result = await db.execute(query)
            engagement = result.scalars().first()

            if not engagement:
                logger.error(f"Engagement {engagement_id} not found")
                return {"email_sent": False, "reason": "engagement_not_found"}

            # Check if email is available
            if not engagement.email:
                logger.info(f"No email available for engagement {engagement_id} (user: @{engagement.instagram_username})")
                return {"email_sent": False, "reason": "no_email"}

            # Get sample to build public URL
            sample_uuid = uuid.UUID(sample_id) if isinstance(sample_id, str) else sample_id
            query = select(Sample).where(Sample.id == sample_uuid)
            result = await db.execute(query)
            sample = result.scalars().first()

            if not sample:
                logger.error(f"Sample {sample_id} not found")
                return {"email_sent": False, "reason": "sample_not_found"}

            # Build public sample URL
            sample_url = f"{settings.PUBLIC_APP_URL}/samples/{sample_id}"

            # Send email
            email_sent = email_service.send_sample_ready_email(
                to_email=engagement.email,
                creator_username=engagement.instagram_username,
                sample_url=sample_url,
                bpm=metadata.get("bpm"),
                key=metadata.get("key"),
                original_creator_username=metadata.get("creator_username")
            )

            # Update engagement record
            if email_sent:
                engagement.email_sent = True
                engagement.email_sent_at = utcnow_naive()
                await db.commit()
                logger.info(f"Successfully sent email to {engagement.email} (@{engagement.instagram_username})")
                return {"email_sent": True, "email": engagement.email}
            else:
                logger.error(f"Failed to send email to {engagement.email}")
                return {"email_sent": False, "reason": "send_failed"}

    except Exception as e:
        logger.error(f"Error sending email for sample {sample_id}: {str(e)}", exc_info=True)
        return {"email_sent": False, "reason": f"error: {str(e)}"}


async def post_instagram_comment(
    engagement_id: Optional[str],
    media_id: str,
    metadata: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Post teaser comment on Instagram media.

    Message format:
    - If email sent: "✅ BPM: X | Key: Y | Check your email! 📧"
    - If no email: "✅ BPM: X | Key: Y | Get this sample with upgraded audio - DM us your email!"

    Plus: "Want to remix? Comment @sampletheinternet and get stem splitter + upgraded audio!"

    Args:
        engagement_id: InstagramEngagement UUID
        media_id: Instagram media ID
        metadata: Dict with bpm, key, email_sent

    Returns:
        Dict with comment_posted status
    """
    logger.info(f"Posting Instagram comment for media_id={media_id}, engagement_id={engagement_id}")

    if not engagement_id:
        logger.warning("No engagement_id provided, cannot post comment")
        return {"comment_posted": False, "reason": "no_engagement_id"}

    try:
        # Build comment message
        bpm = metadata.get("bpm")
        key = metadata.get("key")
        email_sent = metadata.get("email_sent", False)

        # Build metadata line
        metadata_parts = []
        if bpm:
            metadata_parts.append(f"BPM: {bpm}")
        if key:
            metadata_parts.append(f"Key: {key}")

        metadata_line = " | ".join(metadata_parts) if metadata_parts else "Sample ready"

        # Build email line
        if email_sent:
            email_line = "Check your email! 📧"
        else:
            email_line = "Get this sample with upgraded audio - DM us your email!"

        # Build full message
        message = f"✅ {metadata_line} | {email_line}\n\n"
        message += "Want to remix? Comment @sampletheinternet and get stem splitter + upgraded audio!"

        # Post comment via Instagram Graph API
        graph_api = InstagramGraphAPIService()

        if not graph_api.is_configured():
            logger.error("Instagram Graph API not configured")
            return {"comment_posted": False, "reason": "api_not_configured"}

        result = await graph_api.post_comment(media_id, message)
        comment_id = result.get('id')

        if not comment_id:
            logger.error(f"Failed to post comment - no ID returned: {result}")
            return {"comment_posted": False, "reason": "no_comment_id"}

        # Update engagement record with comment details
        async with AsyncSessionLocal() as db:
            engagement_uuid = uuid.UUID(engagement_id) if isinstance(engagement_id, str) else engagement_id
            query = select(InstagramEngagement).where(InstagramEngagement.id == engagement_uuid)
            result_query = await db.execute(query)
            engagement = result_query.scalars().first()

            if engagement:
                engagement.comment_id = comment_id
                engagement.comment_text = message
                engagement.comment_posted_at = utcnow_naive()
                await db.commit()
                logger.info(f"Successfully posted comment {comment_id} on media {media_id}")
            else:
                logger.warning(f"Engagement {engagement_id} not found for comment update")

        return {"comment_posted": True, "comment_id": comment_id}

    except Exception as e:
        logger.error(f"Error posting Instagram comment: {str(e)}", exc_info=True)
        return {"comment_posted": False, "reason": f"error: {str(e)}"}


async def update_sample_complete(data: Dict[str, Any]) -> None:
    """Update sample with processing results (with retry logic for race conditions)"""
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

    max_retries = 3
    retry_delay = 0.5
    sample = None

    # Retry loop to handle race conditions
    for attempt in range(max_retries):
        try:
            async with AsyncSessionLocal() as db:
                logger.info(f"Looking for sample with ID: {sample_uuid} (attempt {attempt + 1}/{max_retries})")
                query = select(Sample).where(Sample.id == sample_uuid)
                result = await db.execute(query)
                sample = result.scalars().first()

                if not sample:
                    # Try to find by aweme_id as fallback
                    aweme_id = metadata.get('aweme_id')
                    if aweme_id:
                        logger.info(f"Sample not found by ID, trying aweme_id: {aweme_id}")
                        query = select(Sample).where(Sample.aweme_id == aweme_id)
                        result = await db.execute(query)
                        sample = result.scalars().first()
                        if sample:
                            logger.info(f"Found sample by aweme_id: {sample.id}")

                if not sample:
                    if attempt < max_retries - 1:
                        # Sample not found, but we have retries left
                        logger.warning(
                            f"Sample {sample_uuid} not found (attempt {attempt + 1}/{max_retries}). "
                            f"Retrying in {retry_delay}s... (aweme_id={metadata.get('aweme_id')})"
                        )
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2
                        continue
                    else:
                        # Final attempt failed
                        logger.error(
                            f"Sample {sample_uuid} not found after {max_retries} attempts! "
                            f"Sample metadata: aweme_id={metadata.get('aweme_id')}, tiktok_id={metadata.get('tiktok_id')}"
                        )
                        raise ValueError(
                            f"Sample {sample_uuid} not found after {max_retries} retries - "
                            f"may have been deleted or database transaction not visible"
                        )

                # Sample found - update metadata from TikTok API
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
                sample.audio_url_hls = urls.get("hls")
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
                return  # Success - exit retry loop

        except ValueError:
            # ValueError is raised when sample not found after all retries
            raise
        except Exception as e:
            logger.exception(f"Error updating sample {sample_id} complete: {e}")
            raise


async def update_instagram_sample_complete(data: Dict[str, Any]) -> None:
    """Update Instagram sample with processing results (with retry logic for race conditions)"""
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

    max_retries = 3
    retry_delay = 0.5
    sample = None

    # Retry loop to handle race conditions
    for attempt in range(max_retries):
        try:
            async with AsyncSessionLocal() as db:
                logger.info(f"Looking for Instagram sample with ID: {sample_uuid} (attempt {attempt + 1}/{max_retries})")
                query = select(Sample).where(Sample.id == sample_uuid)
                result = await db.execute(query)
                sample = result.scalars().first()

                if not sample:
                    # Try to find by instagram_id or shortcode as fallback
                    instagram_id = metadata.get('instagram_id')
                    instagram_shortcode = metadata.get('instagram_shortcode')
                    if instagram_id or instagram_shortcode:
                        logger.info(f"Sample not found by ID, trying instagram_id: {instagram_id} or shortcode: {instagram_shortcode}")
                        query = select(Sample).where(
                            or_(
                                Sample.instagram_id == instagram_id if instagram_id else False,
                                Sample.instagram_shortcode == instagram_shortcode if instagram_shortcode else False
                            )
                        )
                        result = await db.execute(query)
                        sample = result.scalars().first()
                        if sample:
                            logger.info(f"Found sample by instagram metadata: {sample.id}")

                if not sample:
                    if attempt < max_retries - 1:
                        # Sample not found, but we have retries left
                        logger.warning(
                            f"Sample {sample_uuid} not found (attempt {attempt + 1}/{max_retries}). "
                            f"Retrying in {retry_delay}s... (instagram_id={metadata.get('instagram_id')})"
                        )
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2
                        continue
                    else:
                        # Final attempt failed
                        logger.error(
                            f"Sample {sample_uuid} not found after {max_retries} attempts! "
                            f"Sample metadata: instagram_id={metadata.get('instagram_id')}, shortcode={metadata.get('instagram_shortcode')}"
                        )
                        raise ValueError(
                            f"Sample {sample_uuid} not found after {max_retries} retries - "
                            f"may have been deleted or database transaction not visible"
                        )

                # Sample found - update metadata from Instagram API
                # Only set instagram_id if it's not already set (avoid unique constraint errors during reprocessing)
                if not sample.instagram_id and metadata.get("instagram_id"):
                    sample.instagram_id = metadata.get("instagram_id")
                if not sample.instagram_shortcode and metadata.get("instagram_shortcode"):
                    sample.instagram_shortcode = metadata.get("instagram_shortcode")

                # Set Instagram-specific fields
                sample.title = metadata.get("title")
                sample.creator_username = metadata.get("creator_username")
                sample.creator_name = metadata.get("creator_full_name")
                sample.description = metadata.get("caption") or metadata.get("description", "")
                sample.view_count = metadata.get("view_count", 0)
                sample.like_count = metadata.get("like_count", 0)
                sample.comment_count = metadata.get("comment_count", 0)
                sample.share_count = 0  # Instagram doesn't provide share count in this API
                sample.region = None  # Instagram doesn't provide region data

                # Convert Instagram taken_at to upload_timestamp
                taken_at = metadata.get("taken_at")
                if taken_at:
                    sample.upload_timestamp = taken_at

                # Extract hashtags from both title and caption/description
                title_text = metadata.get("title", "")
                description_text = metadata.get("caption") or metadata.get("description", "")
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
                sample.cover_url = urls.get("thumbnail")  # Instagram uses same for both
                sample.audio_url_wav = urls["wav"]
                sample.audio_url_mp3 = urls["mp3"]
                sample.audio_url_hls = urls.get("hls")
                sample.waveform_url = urls["waveform"]

                # Calculate video file size if available
                if metadata.get("file_size"):
                    sample.file_size_video = metadata["file_size"]

                # Link to Instagram creator if available
                instagram_creator_id = metadata.get("instagram_creator_id")
                if instagram_creator_id:
                    sample.instagram_creator_id = uuid.UUID(instagram_creator_id)
                    logger.info(f"Linked sample to Instagram creator {instagram_creator_id}")

                # Mark as completed
                sample.status = ProcessingStatus.COMPLETED

                await db.commit()
                logger.info(f"Instagram sample {sample_id} processing completed successfully")
                return  # Success - exit retry loop

        except ValueError:
            # ValueError is raised when sample not found after all retries
            raise
        except Exception as e:
            logger.exception(f"Error updating Instagram sample {sample_id} complete: {e}")
            raise


# Error handler function
@inngest_client.create_function(
    fn_id="handle-processing-error",
    trigger=inngest.TriggerEvent(event="tiktok/processing.failed")
)
async def handle_processing_error(ctx: inngest.Context) -> None:
    """Handle processing failures (with retry logic for race conditions)"""
    event_data = ctx.event.data
    sample_id = event_data.get("sample_id")
    error_message = event_data.get("error", "Unknown error occurred")

    async def update_failed_status():
        sample_uuid = uuid.UUID(sample_id)
        max_retries = 3
        retry_delay = 0.5

        for attempt in range(max_retries):
            try:
                async with AsyncSessionLocal() as db:
                    logger.info(f"Marking sample {sample_uuid} as failed (attempt {attempt + 1}/{max_retries})")
                    query = select(Sample).where(Sample.id == sample_uuid)
                    result = await db.execute(query)
                    sample = result.scalars().first()

                    if not sample:
                        if attempt < max_retries - 1:
                            logger.warning(
                                f"Sample {sample_uuid} not found in error handler (attempt {attempt + 1}/{max_retries}). "
                                f"Retrying in {retry_delay}s..."
                            )
                            await asyncio.sleep(retry_delay)
                            retry_delay *= 2
                            continue
                        else:
                            logger.error(
                                f"Sample {sample_uuid} not found after {max_retries} attempts in error handler. "
                                f"Cannot mark as failed."
                            )
                            return  # Give up gracefully

                    sample.status = ProcessingStatus.FAILED
                    sample.error_message = error_message

                    await db.commit()
                    logger.error(f"Sample {sample_id} processing failed: {error_message}")
                    return  # Success

            except Exception as e:
                logger.exception(f"Error in error handler for sample {sample_id}: {e}")
                if attempt == max_retries - 1:
                    raise

    await ctx.step.run("mark-as-failed", update_failed_status)


# Instagram error handler function
@inngest_client.create_function(
    fn_id="handle-instagram-processing-error",
    trigger=inngest.TriggerEvent(event="instagram/processing.failed")
)
async def handle_instagram_processing_error(ctx: inngest.Context) -> None:
    """Handle Instagram processing failures (with retry logic for race conditions)"""
    event_data = ctx.event.data
    sample_id = event_data.get("sample_id")
    error_message = event_data.get("error", "Unknown error occurred")

    async def update_failed_status():
        sample_uuid = uuid.UUID(sample_id)
        max_retries = 3
        retry_delay = 0.5

        for attempt in range(max_retries):
            try:
                async with AsyncSessionLocal() as db:
                    logger.info(f"Marking Instagram sample {sample_uuid} as failed (attempt {attempt + 1}/{max_retries})")
                    query = select(Sample).where(Sample.id == sample_uuid)
                    result = await db.execute(query)
                    sample = result.scalars().first()

                    if not sample:
                        if attempt < max_retries - 1:
                            logger.warning(
                                f"Instagram sample {sample_uuid} not found in error handler (attempt {attempt + 1}/{max_retries}). "
                                f"Retrying in {retry_delay}s..."
                            )
                            await asyncio.sleep(retry_delay)
                            retry_delay *= 2
                            continue
                        else:
                            logger.error(
                                f"Instagram sample {sample_uuid} not found after {max_retries} attempts in error handler. "
                                f"Cannot mark as failed."
                            )
                            return  # Give up gracefully

                    sample.status = ProcessingStatus.FAILED
                    sample.error_message = error_message

                    await db.commit()
                    logger.error(f"Instagram sample {sample_id} processing failed: {error_message}")
                    return  # Success

            except Exception as e:
                logger.exception(f"Error in Instagram error handler for sample {sample_id}: {e}")
                if attempt == max_retries - 1:
                    raise

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

        # If there are more videos to process, automatically trigger the next batch
        if has_more and next_cursor is not None:
            logger.info(f"Collection {collection_id} has more videos. Auto-triggering next batch from cursor {next_cursor}")

            # Update current_cursor for the next batch
            await ctx.step.run(
                f"update-cursor-for-next-batch-{collection_id}",
                update_collection_cursor,
                collection_id,
                next_cursor
            )

            # Trigger the next batch processing
            await ctx.step.send_event(
                f"trigger-next-batch-{collection_id}-{next_cursor}",
                inngest.Event(
                    name="collection/import.submitted",
                    data={"collection_id": collection_id}
                )
            )
            logger.info(f"Triggered next batch for collection {collection_id} from cursor {next_cursor}")

        new_videos_count = len(new_videos)
        return {
            "collection_id": collection_id,
            "status": "completed" if not has_more else "processing",
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


async def refund_credits_for_failed_stems(stem_ids: List[str]) -> None:
    """Refund credits to user when stem separation fails"""
    try:
        async with AsyncSessionLocal() as db:
            # Get the first stem to find the user and sample
            if not stem_ids:
                logger.warning("No stem IDs provided for refund")
                return

            # Load first stem with parent sample to get user
            stem_uuid = uuid.UUID(stem_ids[0])
            from sqlalchemy.orm import selectinload
            query = (
                select(Stem)
                .where(Stem.id == stem_uuid)
                .options(selectinload(Stem.parent_sample))
            )
            result = await db.execute(query)
            stem = result.scalars().first()

            if not stem or not stem.parent_sample:
                logger.error(f"Stem {stem_ids[0]} or parent sample not found for refund")
                return

            user_id = stem.parent_sample.creator_id
            if not user_id:
                logger.error(f"No creator_id found for sample {stem.parent_sample_id}")
                return

            # Calculate total credits to refund: 2 credits per stem
            from app.core.config import settings
            credits_to_refund = len(stem_ids) * settings.CREDITS_PER_STEM

            # Refund credits atomically
            credit_service = CreditService(db)
            await credit_service.refund_credits_atomic(
                user_id=user_id,
                credits_to_refund=credits_to_refund,
                description=f"Refund for {len(stem_ids)} failed stem separation(s)",
                stem_id=stem_uuid  # Link to first stem for audit trail
            )

            await db.commit()
            logger.info(f"Refunded {credits_to_refund} credits to user {user_id} for {len(stem_ids)} failed stems")
    except Exception as e:
        logger.exception(f"Error refunding credits for failed stems: {e}")
        # Don't raise - we don't want refund failure to stop error handling


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
                collection.started_at = utcnow_naive()
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
                logger.info(f"Sample already exists for aweme_id {aweme_id}: {existing_sample.id}, status: {existing_sample.status.value}")
                sample_id = existing_sample.id

                # If sample is not completed, retrigger processing
                if existing_sample.status != ProcessingStatus.COMPLETED:
                    logger.info(f"Sample {sample_id} status is {existing_sample.status.value}, retriggering processing")
                    try:
                        await inngest_client.send(
                            inngest.Event(
                                name="tiktok/video.submitted",
                                data={
                                    "sample_id": str(existing_sample.id),
                                    "url": tiktok_url
                                }
                            )
                        )
                        logger.info(f"✓ Successfully retriggered processing for existing sample {sample_id}")
                    except Exception as e:
                        logger.error(f"✗ Failed to retrigger processing for existing sample {sample_id}: {e}")
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
            collection.completed_at = utcnow_naive()
            collection.next_cursor = next_cursor
            collection.has_more = has_more
            await db.commit()
            logger.info(f"Marked collection {collection_id} batch as completed (has_more: {has_more})")
    except Exception as e:
        logger.exception(f"Error completing collection: {e}")
        raise


async def update_collection_cursor(
    collection_id: str,
    cursor: int
) -> None:
    """Update collection's current_cursor for next batch processing"""
    try:
        async with AsyncSessionLocal() as db:
            query = select(Collection).where(Collection.id == uuid.UUID(collection_id))
            result = await db.execute(query)
            collection = result.scalar_one()
            collection.current_cursor = cursor
            collection.status = CollectionStatus.pending  # Reset to pending for next batch
            await db.commit()
            logger.info(f"Updated collection {collection_id} cursor to {cursor} for next batch")
    except Exception as e:
        logger.exception(f"Error updating collection cursor: {e}")
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


# Pydantic models for Inngest event validation
class StemSeparationEventData(BaseModel):
    """Validation model for stem separation Inngest event data"""
    sample_id: UUID = Field(..., description="UUID of the parent sample")
    stem_ids: List[UUID] = Field(..., description="List of stem UUIDs to process", min_items=1)

    @validator('stem_ids')
    def validate_stem_ids_not_empty(cls, v):
        if not v:
            raise ValueError("stem_ids cannot be empty")
        return v


@inngest_client.create_function(
    fn_id="process-stem-separation",
    trigger=inngest.TriggerEvent(event="stem/separation.submitted"),
    retries=2
)
async def process_stem_separation(ctx: inngest.Context) -> Dict[str, Any]:
    """
    Process stem separation request through multiple steps:
    1. Update stem status to uploading
    2. Download original audio from storage
    3. Upload to La La AI
    4. Submit separation job per stem
    5. Poll for completion
    6. Download separated stems
    7. Copy metadata from parent sample (BPM, key, duration)
    8. Upload stems to storage
    9. Update database
    10. Clean up temp files
    """
    # Validate event data
    try:
        event_data = StemSeparationEventData(**ctx.event.data)
    except Exception as e:
        logger.error(f"Invalid event data for stem separation: {e}")
        raise ValueError(f"Invalid event data: {e}")

    stem_ids = [str(stem_id) for stem_id in event_data.stem_ids]
    sample_id = str(event_data.sample_id)

    logger.info(f"Processing stem separation for sample {sample_id}, stems: {stem_ids}")

    # Step 1: Update all stems to uploading status
    await ctx.step.run(
        "update-stems-uploading",
        update_stems_status,
        stem_ids,
        StemProcessingStatus.UPLOADING
    )

    # Step 2: Download original audio from storage
    audio_path = await ctx.step.run(
        "download-original-audio",
        download_sample_audio,
        sample_id
    )

    # Step 3-9: Process each stem type separately
    # Group stems by type to avoid duplicate processing
    stems_by_type = {}
    async with AsyncSessionLocal() as db:
        for stem_id in stem_ids:
            query = select(Stem).where(Stem.id == uuid.UUID(stem_id))
            result = await db.execute(query)
            stem = result.scalars().first()
            if stem:
                stem_type = stem.stem_type.value
                if stem_type not in stems_by_type:
                    stems_by_type[stem_type] = []
                stems_by_type[stem_type].append(str(stem.id))

    # Process each unique stem type
    for stem_type, stem_id_list in stems_by_type.items():
        # Use the first stem ID for this type
        primary_stem_id = stem_id_list[0]

        # Step 3: Upload to La La AI and separate
        separated_file = await ctx.step.run(
            f"separate-{stem_type}",
            separate_stem,
            audio_path,
            stem_type,
            sample_id
        )

        # Step 4: Get stem metadata from parent sample (stems inherit parent's BPM/key)
        stem_analysis = await ctx.step.run(
            f"get-metadata-{stem_type}",
            get_stem_metadata_from_parent,
            separated_file,
            sample_id
        )

        # Step 5: Upload to storage
        stem_urls = await ctx.step.run(
            f"upload-{stem_type}",
            upload_stem_to_storage,
            separated_file,
            sample_id,
            stem_type
        )

        # Step 6: Update database
        await ctx.step.run(
            f"update-{stem_type}",
            update_stem_complete,
            primary_stem_id,
            stem_urls,
            stem_analysis
        )

    # Step 7: Clean up temp files
    await ctx.step.run(
        "cleanup-temp-files",
        cleanup_stem_temp_files,
        audio_path
    )

    return {
        "sample_id": sample_id,
        "stem_ids": stem_ids,
        "status": "completed"
    }


@inngest_client.create_function(
    fn_id="handle-stem-separation-error",
    trigger=inngest.TriggerEvent(event="inngest/function.failed")
)
async def handle_stem_separation_error(ctx: inngest.Context):
    """Handle errors during stem separation processing"""
    # Check if this is a stem separation function failure
    function_id = ctx.event.data.get("function_id")
    if function_id != "process-stem-separation":
        # Not a stem separation error, skip
        return {"skipped": True, "reason": "Not a stem separation error"}

    event_data = ctx.event.data.get("event", {}).get("data", {})
    stem_ids = event_data.get("stem_ids", [])
    error_message = ctx.event.data.get("error", {}).get("message", "Unknown error")

    logger.error(f"Stem separation failed for stems {stem_ids}: {error_message}")

    # Refund credits to user before marking stems as failed
    if stem_ids:
        await ctx.step.run(
            "refund-credits-for-failed-stems",
            refund_credits_for_failed_stems,
            stem_ids
        )

    async def update_failed_status():
        async with AsyncSessionLocal() as db:
            for stem_id in stem_ids:
                try:
                    stem_uuid = uuid.UUID(stem_id)
                    query = select(Stem).where(Stem.id == stem_uuid)
                    result = await db.execute(query)
                    stem = result.scalars().first()

                    if stem:
                        stem.status = StemProcessingStatus.FAILED
                        stem.error_message = error_message

                except Exception as e:
                    logger.exception(f"Error updating failed status for stem {stem_id}: {e}")

            await db.commit()
            logger.info(f"Updated {len(stem_ids)} stems to failed status")

    await ctx.step.run("mark-stems-as-failed", update_failed_status)


async def update_stems_status(stem_ids: List[str], status: StemProcessingStatus) -> None:
    """Update stem processing status in database"""
    try:
        async with AsyncSessionLocal() as db:
            for stem_id in stem_ids:
                stem_uuid = uuid.UUID(stem_id)
                query = select(Stem).where(Stem.id == stem_uuid)
                result = await db.execute(query)
                stem = result.scalars().first()

                if stem:
                    stem.status = status
                    logger.info(f"Updated stem {stem_id} status to {status.value}")

            await db.commit()
    except Exception as e:
        logger.exception(f"Error updating stems status: {e}")
        raise


async def download_sample_audio(sample_id: str) -> str:
    """Download original sample audio from storage to temp directory (with retry logic)"""
    temp_dir = Path(tempfile.gettempdir()) / f"stems_{sample_id}"
    temp_dir.mkdir(parents=True, exist_ok=True)

    sample_uuid = uuid.UUID(sample_id)
    max_retries = 3
    retry_delay = 0.5

    for attempt in range(max_retries):
        try:
            async with AsyncSessionLocal() as db:
                logger.info(f"Looking for sample {sample_uuid} for audio download (attempt {attempt + 1}/{max_retries})")
                query = select(Sample).where(Sample.id == sample_uuid)
                result = await db.execute(query)
                sample = result.scalars().first()

                if not sample or not sample.audio_url_wav:
                    if attempt < max_retries - 1:
                        logger.warning(
                            f"Sample {sample_uuid} not found or has no audio (attempt {attempt + 1}/{max_retries}). "
                            f"Retrying in {retry_delay}s..."
                        )
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2
                        continue
                    else:
                        raise ValueError(
                            f"Sample {sample_id} not found or has no audio after {max_retries} retries"
                        )

                # Sample found - download WAV file from storage
                storage = S3Storage()
                temp_audio_path = temp_dir / f"original.wav"

                # The actual storage key for audio files is samples/{sample_id}/audio.wav
                file_key = f"samples/{sample_id}/audio.wav"

                logger.info(f"Attempting to download audio from key: {file_key}")

                await storage.download_file(file_key, str(temp_audio_path))

                logger.info(f"Downloaded original audio to {temp_audio_path}")
                return str(temp_audio_path)

        except ValueError:
            # ValueError is raised when sample not found after all retries
            raise
        except Exception as e:
            logger.exception(f"Error downloading sample audio: {e}")
            raise


async def separate_stem(audio_path: str, stem_type: str, sample_id: str) -> str:
    """Use La La AI to separate a specific stem"""
    try:
        lalal_service = LalalAIService()
        temp_dir = Path(audio_path).parent / "separated"
        temp_dir.mkdir(parents=True, exist_ok=True)

        # Process single stem type
        result = await lalal_service.process_stem_separation(
            audio_path,
            [stem_type],
            str(temp_dir)
        )

        # La La AI returns different result structures:
        # - Single stem: {'vocals': file_path, 'background': file_path}
        # - The stem_type from our database might be singular ('vocal') but Lalal returns plural ('vocals')

        stem_file = None

        # Map our stem types to what Lalal.ai returns
        # Lalal.ai uses 'vocals' (plural), but our DB uses 'vocal' (singular)
        lalal_key_mapping = {
            'vocal': 'vocals',
            'drum': 'drum',
            'piano': 'piano',
            'bass': 'bass',
            'electric_guitar': 'electric_guitar',
            'acoustic_guitar': 'acoustic_guitar',
            'synthesizer': 'synthesizer',
            'strings': 'strings',
            'wind': 'wind',
            'voice': 'voice'
        }

        # Try to find the stem file with the mapped key
        mapped_key = lalal_key_mapping.get(stem_type, stem_type)
        if mapped_key in result:
            stem_file = result[mapped_key]
            logger.info(f"Found {stem_type} stem using key '{mapped_key}'")
        # Fall back to the original key
        elif stem_type in result:
            stem_file = result[stem_type]
            logger.info(f"Found {stem_type} stem by exact name match")
        # Fall back to generic 'stem' key for single-stem separations
        elif 'stem' in result:
            stem_file = result['stem']
            logger.info(f"Found {stem_type} stem using generic 'stem' key")

        if not stem_file:
            logger.error(f"Available keys in result: {list(result.keys())}")
            raise ValueError(f"No stem file found in La La AI result for {stem_type}. Available: {list(result.keys())}")

        # Ensure file exists
        if not Path(stem_file).exists():
            raise FileNotFoundError(f"Stem file does not exist: {stem_file}")

        # Rename to standardized format if needed
        final_path = temp_dir / f"{stem_type}.wav"
        if Path(stem_file) != final_path:
            Path(stem_file).rename(final_path)

        logger.info(f"Separated {stem_type} stem to {final_path}")
        return str(final_path)

    except Exception as e:
        logger.exception(f"Error separating stem {stem_type}: {e}")
        raise


async def get_stem_metadata_from_parent(stem_file_path: str, sample_id: str) -> Dict[str, Any]:
    """Get stem metadata by copying from parent sample (with retry logic for race conditions)"""
    try:
        # Get just the duration from the separated file to verify it was created
        processor = AudioProcessor()
        metadata = await processor.get_audio_metadata(stem_file_path)

        sample_uuid = uuid.UUID(sample_id)
        max_retries = 3
        retry_delay = 0.5

        # Retry loop to handle race conditions
        for attempt in range(max_retries):
            try:
                async with AsyncSessionLocal() as db:
                    logger.info(f"Looking for parent sample {sample_uuid} for stem metadata (attempt {attempt + 1}/{max_retries})")
                    query = select(Sample).where(Sample.id == sample_uuid)
                    result = await db.execute(query)
                    parent_sample = result.scalars().first()

                    if not parent_sample:
                        if attempt < max_retries - 1:
                            logger.warning(
                                f"Parent sample {sample_uuid} not found (attempt {attempt + 1}/{max_retries}). "
                                f"Retrying in {retry_delay}s..."
                            )
                            await asyncio.sleep(retry_delay)
                            retry_delay *= 2
                            continue
                        else:
                            raise ValueError(
                                f"Parent sample {sample_id} not found after {max_retries} retries"
                            )

                    # Copy BPM, key, and duration from parent sample
                    # Stems are extracted from the same audio, so they have the same musical properties
                    logger.info(f"Copied metadata from parent sample: BPM={parent_sample.bpm}, Key={parent_sample.key}, Duration={metadata.get('duration'):.1f}s")

                    return {
                        "bpm": parent_sample.bpm,
                        "key": parent_sample.key,
                        "duration": metadata.get("duration"),  # Use actual stem duration (should match parent)
                        "sample_rate": metadata.get("sample_rate"),
                        "channels": metadata.get("channels")
                    }

            except ValueError:
                # ValueError is raised when parent sample not found after all retries
                raise
            except Exception as e:
                logger.exception(f"Error getting stem metadata: {e}")
                raise

    except Exception as e:
        logger.exception(f"Error getting stem metadata: {e}")
        # Return partial results if metadata retrieval fails
        return {
            "bpm": None,
            "key": None,
            "duration": None
        }


async def upload_stem_to_storage(stem_file_path: str, sample_id: str, stem_type: str) -> Dict[str, str]:
    """Upload separated stem (WAV and MP3) to storage and return URLs"""
    try:
        storage = S3Storage()
        processor = AudioProcessor()
        stem_path = Path(stem_file_path)

        # Convert WAV to MP3
        mp3_path = stem_path.parent / f"{stem_type}.mp3"
        import subprocess
        cmd = [
            'ffmpeg', '-i', str(stem_path),
            '-acodec', 'libmp3lame',
            '-b:a', '320k',
            '-y',
            str(mp3_path)
        ]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await process.communicate()

        # Upload both files
        wav_key = f"samples/{sample_id}/stems/{stem_type}.wav"
        mp3_key = f"samples/{sample_id}/stems/{stem_type}.mp3"

        await storage.upload_file(str(stem_path), wav_key)
        await storage.upload_file(str(mp3_path), mp3_key)

        wav_url = storage.get_public_url(wav_key)
        mp3_url = storage.get_public_url(mp3_key)

        # Get file sizes
        wav_size = stem_path.stat().st_size
        mp3_size = mp3_path.stat().st_size

        logger.info(f"Uploaded {stem_type} stem: WAV={wav_url}, MP3={mp3_url}")

        return {
            "wav_url": wav_url,
            "mp3_url": mp3_url,
            "wav_key": wav_key,
            "mp3_key": mp3_key,
            "wav_size": wav_size,
            "mp3_size": mp3_size
        }

    except Exception as e:
        logger.exception(f"Error uploading stem to storage: {e}")
        raise


async def update_stem_complete(stem_id: str, urls: Dict[str, str], analysis: Dict[str, Any]) -> None:
    """Update stem record with completed processing results"""
    try:
        async with AsyncSessionLocal() as db:
            stem_uuid = uuid.UUID(stem_id)
            query = select(Stem).where(Stem.id == stem_uuid)
            result = await db.execute(query)
            stem = result.scalars().first()

            if not stem:
                raise ValueError(f"Stem {stem_id} not found")

            # Update with results
            stem.status = StemProcessingStatus.COMPLETED
            stem.audio_url_wav = urls.get("wav_url")
            stem.audio_url_mp3 = urls.get("mp3_url")
            stem.file_path_wav = urls.get("wav_key")
            stem.file_path_mp3 = urls.get("mp3_key")
            stem.file_size_wav = urls.get("wav_size")
            stem.file_size_mp3 = urls.get("mp3_size")
            stem.bpm = analysis.get("bpm")
            # Format key as string (e.g., "Ab major") like we do for samples
            key_data = analysis.get("key")
            if key_data and isinstance(key_data, dict):
                stem.key = f"{key_data.get('key')} {key_data.get('scale')}" if key_data.get('key') and key_data.get('scale') else None
            else:
                stem.key = key_data
            stem.duration_seconds = analysis.get("duration")
            stem.completed_at = utcnow_naive()

            await db.commit()
            logger.info(f"Updated stem {stem_id} with completion data")

    except Exception as e:
        logger.exception(f"Error updating stem complete: {e}")
        raise


async def cleanup_stem_temp_files(audio_path: str) -> None:
    """Clean up temporary files created during stem separation"""
    try:
        temp_dir = Path(audio_path).parent
        if temp_dir.exists():
            import shutil
            shutil.rmtree(temp_dir)
            logger.info(f"Cleaned up temp directory: {temp_dir}")
    except Exception as e:
        logger.warning(f"Failed to cleanup temp files: {e}")


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
        process_instagram_video,
        handle_processing_error,
        handle_instagram_processing_error,
        process_collection,
        handle_collection_error,
        process_stem_separation,
        handle_stem_separation_error,
        test_function
    ]