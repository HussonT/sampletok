"""
Inngest functions for async processing of TikTok videos
"""
import inngest
import tempfile
import logging
from pathlib import Path
import uuid
from typing import Dict, Any

from app.core.config import settings
from app.services.tiktok.downloader import TikTokDownloader
from app.services.audio.processor import AudioProcessor
from app.services.audio.analyzer import AudioAnalyzer
from app.services.storage.s3 import S3Storage
from app.models import Sample, ProcessingStatus, TikTokCreator
from app.core.database import AsyncSessionLocal
from sqlalchemy import select
from app.services.tiktok.creator_service import CreatorService

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
    2. Extract audio (WAV and MP3)
    3. Generate waveform visualization
    4. Analyze audio features (BPM, key detection)
    5. Upload files to storage
    6. Update database with results
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

    # Step 3: Extract audio (creates WAV and MP3, uploads to R2, returns URLs)
    audio_files = await ctx.step.run(
        "extract-audio",
        extract_audio_from_video,
        video_metadata["video_path"],
        video_metadata["temp_dir"],
        sample_id
    )

    # Step 4: Generate waveform (generates PNG, uploads to R2, returns URL)
    waveform_url = await ctx.step.run(
        "generate-waveform",
        generate_waveform,
        audio_files["wav_path"],
        video_metadata["temp_dir"],
        sample_id
    )

    # Step 5: Analyze audio features (BPM, key detection)
    audio_analysis = await ctx.step.run(
        "analyze-audio-features",
        analyze_audio_features,
        audio_files["wav_path"]
    )

    # Step 6: Update database with results (URLs are already from R2)
    await ctx.step.run(
        "update-database",
        update_sample_complete,
        {
            "sample_id": sample_id,
            "metadata": video_metadata,
            "urls": {
                "wav": audio_files["wav_url"],
                "mp3": audio_files["mp3_url"],
                "waveform": waveform_url
            },
            "analysis": audio_analysis,
            "audio_metadata": audio_files.get("metadata", {})
        }
    )

    # Step 7: Clean up temp files
    await ctx.step.run(
        "cleanup-temp-files",
        cleanup_temp_files,
        video_metadata["temp_dir"]
    )

    return {
        "sample_id": sample_id,
        "status": "completed",
        "audio_url": audio_files["mp3_url"],
        "waveform_url": waveform_url
    }


async def update_sample_status(sample_id: str, status: ProcessingStatus) -> None:
    """Update sample processing status in database"""
    try:
        async with AsyncSessionLocal() as db:
            query = select(Sample).where(Sample.id == uuid.UUID(sample_id))
            result = await db.execute(query)
            sample = result.scalar_one()
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

            query = select(Sample).where(Sample.id == uuid.UUID(sample_id))
            result = await db.execute(query)
            sample = result.scalar_one()

            # Update metadata - now with RapidAPI fields
            sample.tiktok_id = metadata.get("tiktok_id")
            sample.aweme_id = metadata.get("aweme_id")
            sample.title = metadata.get("title")
            sample.region = metadata.get("region")
            sample.creator_username = metadata.get("creator_username")
            sample.creator_name = metadata.get("creator_name")
            sample.creator_avatar_url = metadata.get("creator_avatar_url")
            sample.description = metadata.get("description")
            sample.view_count = metadata.get("view_count", 0)
            sample.like_count = metadata.get("like_count", 0)
            sample.comment_count = metadata.get("comment_count", 0)
            sample.share_count = metadata.get("share_count", 0)
            # Use duration from audio metadata (extracted from actual audio file)
            sample.duration_seconds = audio_metadata.get("duration", metadata.get("duration"))
            sample.thumbnail_url = metadata.get("thumbnail_url")
            sample.origin_cover_url = metadata.get("origin_cover_url")
            sample.music_url = metadata.get("music_url")
            sample.video_url = metadata.get("video_url")
            sample.video_url_watermark = metadata.get("video_url_watermark")
            sample.upload_timestamp = metadata.get("upload_timestamp")

            # Update audio analysis results
            if analysis.get("bpm"):
                sample.bpm = analysis["bpm"]
                logger.info(f"Set BPM: {analysis['bpm']}")

            if analysis.get("key") and analysis.get("scale"):
                sample.key = f"{analysis['key']} {analysis['scale']}"
                logger.info(f"Set key: {sample.key}")

            # Update file URLs
            sample.audio_url_wav = urls["wav"]
            sample.audio_url_mp3 = urls["mp3"]
            sample.waveform_url = urls["waveform"]

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
        test_function
    ]