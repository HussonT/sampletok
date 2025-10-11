"""
Inngest functions for async processing of TikTok videos
"""
import inngest
import tempfile
import logging
from pathlib import Path
import uuid
from typing import Dict, Any
import asyncio

from app.core.config import settings
from app.services.tiktok.downloader import TikTokDownloader
from app.services.audio.processor import AudioProcessor
from app.services.storage.s3 import S3Storage
from app.models import Sample, ProcessingStatus, TikTokCreator
from app.core.database import AsyncSessionLocal
from sqlalchemy import select
from app.services.tiktok.creator_service import CreatorService

logger = logging.getLogger(__name__)

# Initialize Inngest client
inngest_client = inngest.Inngest(
    app_id="sampletok",
    event_key=settings.INNGEST_EVENT_KEY if hasattr(settings, 'INNGEST_EVENT_KEY') else None,
    is_production=False  # Always use development mode for now
)


@inngest_client.create_function(
    fn_id="process-tiktok-video",
    trigger=inngest.TriggerEvent(event="tiktok/video.submitted"),
    retries=3
)
def process_tiktok_video(ctx: inngest.Context) -> Dict[str, Any]:
    """
    Process a TikTok video through multiple steps:
    1. Download video from TikTok
    2. Extract audio (WAV and MP3)
    3. Generate waveform visualization
    4. Upload files to storage
    5. Update database with results
    """
    event_data = ctx.event.data
    sample_id = event_data.get("sample_id")
    tiktok_url = event_data.get("url")

    logger.info(f"Processing TikTok video: {tiktok_url} for sample: {sample_id}")

    # Step 1: Update status to processing
    ctx.step.run(
        "update-status-processing",
        update_sample_status_sync,
        sample_id,
        ProcessingStatus.PROCESSING
    )

    # Step 2: Download video and get metadata
    video_metadata = ctx.step.run(
        "download-video",
        download_tiktok_video_sync,
        tiktok_url,
        sample_id
    )

    # Step 3: Extract audio (creates WAV and MP3)
    audio_files = ctx.step.run(
        "extract-audio",
        extract_audio_from_video_sync,
        video_metadata["video_path"],
        video_metadata["temp_dir"]
    )

    # Step 4: Generate waveform
    waveform_path = ctx.step.run(
        "generate-waveform",
        generate_waveform_sync,
        audio_files["wav"],
        video_metadata["temp_dir"]
    )

    # Step 5: Upload all files to storage
    uploaded_urls = ctx.step.run(
        "upload-files",
        upload_to_storage_sync,
        {
            "sample_id": sample_id,
            "wav_path": audio_files["wav"],
            "mp3_path": audio_files["mp3"],
            "waveform_path": waveform_path
        }
    )

    # Step 6: Update database with results
    ctx.step.run(
        "update-database",
        update_sample_complete_sync,
        {
            "sample_id": sample_id,
            "metadata": video_metadata,
            "urls": uploaded_urls
        }
    )

    # Step 7: Clean up temp files
    ctx.step.run(
        "cleanup-temp-files",
        cleanup_temp_files_sync,
        video_metadata["temp_dir"]
    )

    return {
        "sample_id": sample_id,
        "status": "completed",
        "audio_url": uploaded_urls["mp3"],
        "waveform_url": uploaded_urls["waveform"]
    }


def update_sample_status_sync(sample_id: str, status: ProcessingStatus) -> None:
    """Update sample processing status in database (sync wrapper)"""
    try:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        # Use sync database connection - replace asyncpg with psycopg2
        sync_db_url = settings.DATABASE_URL.replace("postgresql+asyncpg", "postgresql")
        engine = create_engine(sync_db_url)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

        with SessionLocal() as db:
            query = select(Sample).where(Sample.id == uuid.UUID(sample_id))
            result = db.execute(query)
            sample = result.scalar_one()
            sample.status = status
            db.commit()
            logger.info(f"Updated sample {sample_id} status to {status.value}")
    except Exception as e:
        logger.error(f"Error updating sample status: {e}")
        raise


def download_tiktok_video_sync(url: str, sample_id: str) -> Dict[str, Any]:
    """Download TikTok video and extract metadata (sync wrapper)"""
    async def _download():
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
                    logger.warning(f"Failed to get/fetch creator: {e}")
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

    return asyncio.run(_download())


def extract_audio_from_video_sync(video_path: str, temp_dir: str) -> Dict[str, str]:
    """Extract audio from video file (sync wrapper)"""
    async def _extract():
        # Use the same temp directory from download step
        processor = AudioProcessor()
        audio_paths = await processor.extract_audio(video_path, temp_dir)
        logger.info(f"Extracted audio: WAV and MP3 created in {temp_dir}")
        return audio_paths

    return asyncio.run(_extract())


def generate_waveform_sync(audio_path: str, temp_dir: str) -> str:
    """Generate waveform visualization from audio (sync wrapper)"""
    async def _generate():
        # Use the same temp directory
        processor = AudioProcessor()
        waveform_path = await processor.generate_waveform(audio_path, temp_dir)
        logger.info(f"Generated waveform visualization in {temp_dir}")
        return waveform_path

    return asyncio.run(_generate())


def upload_to_storage_sync(data: Dict[str, str]) -> Dict[str, str]:
    """Upload files to S3/storage (sync wrapper)"""
    async def _upload():
        storage = S3Storage()
        sample_id = data["sample_id"]

        # Upload all files
        wav_url = await storage.upload_file(
            data["wav_path"],
            f"samples/{sample_id}/audio.wav"
        )
        mp3_url = await storage.upload_file(
            data["mp3_path"],
            f"samples/{sample_id}/audio.mp3"
        )
        waveform_url = await storage.upload_file(
            data["waveform_path"],
            f"samples/{sample_id}/waveform.png"
        )

        logger.info(f"Uploaded files to storage for sample {sample_id}")

        return {
            "wav": wav_url,
            "mp3": mp3_url,
            "waveform": waveform_url
        }

    return asyncio.run(_upload())


def cleanup_temp_files_sync(temp_dir: str) -> None:
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


def update_sample_complete_sync(data: Dict[str, Any]) -> None:
    """Update sample with processing results (sync wrapper)"""
    try:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        # Use sync database connection - replace asyncpg with psycopg2
        sync_db_url = settings.DATABASE_URL.replace("postgresql+asyncpg", "postgresql")
        engine = create_engine(sync_db_url)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

        with SessionLocal() as db:
            sample_id = data["sample_id"]
            metadata = data["metadata"]
            urls = data["urls"]

            query = select(Sample).where(Sample.id == uuid.UUID(sample_id))
            result = db.execute(query)
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
            sample.duration_seconds = metadata.get("duration")
            sample.thumbnail_url = metadata.get("thumbnail_url")
            sample.origin_cover_url = metadata.get("origin_cover_url")
            sample.music_url = metadata.get("music_url")
            sample.video_url = metadata.get("video_url")
            sample.video_url_watermark = metadata.get("video_url_watermark")
            sample.upload_timestamp = metadata.get("upload_timestamp")

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

            db.commit()
            logger.info(f"Sample {sample_id} processing completed successfully")
    except Exception as e:
        logger.error(f"Error updating sample complete: {e}")
        raise


# Error handler function
@inngest_client.create_function(
    fn_id="handle-processing-error",
    trigger=inngest.TriggerEvent(event="tiktok/processing.failed")
)
def handle_processing_error(ctx: inngest.Context) -> None:
    """Handle processing failures"""
    event_data = ctx.event.data
    sample_id = event_data.get("sample_id")
    error_message = event_data.get("error", "Unknown error occurred")

    def update_failed_status():
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        # Use sync database connection - replace asyncpg with psycopg2
        sync_db_url = settings.DATABASE_URL.replace("postgresql+asyncpg", "postgresql")
        engine = create_engine(sync_db_url)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

        with SessionLocal() as db:
            query = select(Sample).where(Sample.id == uuid.UUID(sample_id))
            result = db.execute(query)
            sample = result.scalar_one()

            sample.status = ProcessingStatus.FAILED
            sample.error_message = error_message

            db.commit()
            logger.error(f"Sample {sample_id} processing failed: {error_message}")

    ctx.step.run("mark-as-failed", update_failed_status)


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