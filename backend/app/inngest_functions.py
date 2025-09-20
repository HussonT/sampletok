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
from app.services.storage.s3 import S3Storage
from app.models import Sample, ProcessingStatus
from app.core.database import AsyncSessionLocal
from sqlalchemy import select

logger = logging.getLogger(__name__)

# Initialize Inngest client
inngest_client = inngest.Inngest(
    app_id="sampletok",
    event_key=settings.INNGEST_EVENT_KEY if hasattr(settings, 'INNGEST_EVENT_KEY') else None,
    is_production=settings.ENVIRONMENT == "production"
)


@inngest_client.create_function(
    fn_id="process-tiktok-video",
    trigger=inngest.TriggerEvent(event="tiktok/video.submitted"),
    retries=3
)
async def process_tiktok_video(
    ctx: inngest.Context,
    step: inngest.Step
) -> Dict[str, Any]:
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
    await step.run(
        "update-status-processing",
        update_sample_status,
        sample_id,
        ProcessingStatus.PROCESSING
    )

    # Step 2: Download video and get metadata
    video_metadata = await step.run(
        "download-video",
        download_tiktok_video,
        tiktok_url
    )

    # Step 3: Extract audio (creates WAV and MP3)
    audio_files = await step.run(
        "extract-audio",
        extract_audio_from_video,
        video_metadata["video_path"]
    )

    # Step 4: Generate waveform
    waveform_path = await step.run(
        "generate-waveform",
        generate_waveform,
        audio_files["wav"]
    )

    # Step 5: Upload all files to storage
    uploaded_urls = await step.run(
        "upload-files",
        upload_to_storage,
        {
            "sample_id": sample_id,
            "wav_path": audio_files["wav"],
            "mp3_path": audio_files["mp3"],
            "waveform_path": waveform_path
        }
    )

    # Step 6: Update database with results
    await step.run(
        "update-database",
        update_sample_complete,
        {
            "sample_id": sample_id,
            "metadata": video_metadata,
            "urls": uploaded_urls
        }
    )

    return {
        "sample_id": sample_id,
        "status": "completed",
        "audio_url": uploaded_urls["mp3"],
        "waveform_url": uploaded_urls["waveform"]
    }


async def update_sample_status(sample_id: str, status: ProcessingStatus) -> None:
    """Update sample processing status in database"""
    async with AsyncSessionLocal() as db:
        query = select(Sample).where(Sample.id == uuid.UUID(sample_id))
        result = await db.execute(query)
        sample = result.scalar_one()
        sample.status = status
        await db.commit()
        logger.info(f"Updated sample {sample_id} status to {status.value}")


async def download_tiktok_video(url: str) -> Dict[str, Any]:
    """Download TikTok video and extract metadata"""
    with tempfile.TemporaryDirectory() as temp_dir:
        downloader = TikTokDownloader()
        metadata = await downloader.download_video(url, temp_dir)
        logger.info(f"Downloaded video: {metadata.get('tiktok_id')}")
        return metadata


async def extract_audio_from_video(video_path: str) -> Dict[str, str]:
    """Extract audio from video file"""
    with tempfile.TemporaryDirectory() as temp_dir:
        processor = AudioProcessor()
        audio_paths = await processor.extract_audio(video_path, temp_dir)
        logger.info(f"Extracted audio: WAV and MP3 created")
        return audio_paths


async def generate_waveform(audio_path: str) -> str:
    """Generate waveform visualization from audio"""
    with tempfile.TemporaryDirectory() as temp_dir:
        processor = AudioProcessor()
        waveform_path = await processor.generate_waveform(audio_path, temp_dir)
        logger.info(f"Generated waveform visualization")
        return waveform_path


async def upload_to_storage(data: Dict[str, str]) -> Dict[str, str]:
    """Upload files to S3/storage"""
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


async def update_sample_complete(data: Dict[str, Any]) -> None:
    """Update sample with processing results"""
    async with AsyncSessionLocal() as db:
        sample_id = data["sample_id"]
        metadata = data["metadata"]
        urls = data["urls"]

        query = select(Sample).where(Sample.id == uuid.UUID(sample_id))
        result = await db.execute(query)
        sample = result.scalar_one()

        # Update metadata
        sample.tiktok_id = metadata.get("tiktok_id")
        sample.creator_username = metadata.get("creator_username")
        sample.creator_name = metadata.get("creator_name")
        sample.description = metadata.get("description")
        sample.view_count = metadata.get("view_count", 0)
        sample.like_count = metadata.get("like_count", 0)
        sample.comment_count = metadata.get("comment_count", 0)
        sample.share_count = metadata.get("share_count", 0)
        sample.duration_seconds = metadata.get("duration")
        sample.thumbnail_url = metadata.get("thumbnail_url")

        # Update file URLs
        sample.audio_url_wav = urls["wav"]
        sample.audio_url_mp3 = urls["mp3"]
        sample.waveform_url = urls["waveform"]

        # Mark as completed
        sample.status = ProcessingStatus.COMPLETED

        await db.commit()
        logger.info(f"Sample {sample_id} processing completed successfully")


# Error handler function
@inngest_client.create_function(
    fn_id="handle-processing-error",
    trigger=inngest.TriggerEvent(event="tiktok/processing.failed")
)
async def handle_processing_error(
    ctx: inngest.Context,
    step: inngest.Step
) -> None:
    """Handle processing failures"""
    event_data = ctx.event.data
    sample_id = event_data.get("sample_id")
    error_message = event_data.get("error", "Unknown error occurred")

    async with AsyncSessionLocal() as db:
        query = select(Sample).where(Sample.id == uuid.UUID(sample_id))
        result = await db.execute(query)
        sample = result.scalar_one()

        sample.status = ProcessingStatus.FAILED
        sample.error_message = error_message

        await db.commit()
        logger.error(f"Sample {sample_id} processing failed: {error_message}")


@inngest_client.create_function(
    fn_id="test-function",
    trigger=inngest.TriggerEvent(event="test/hello")
)
async def test_function(ctx: inngest.Context, step: inngest.Step):
    """Simple test function for testing Inngest integration"""
    data = ctx.event.data

    message = await step.run(
        "log-message",
        lambda: f"Received test message: {data.get('message', 'no message')}"
    )

    return {"status": "success", "message": message}


def get_all_functions():
    """Return all Inngest functions to be served"""
    return [
        process_tiktok_video,
        handle_processing_error,
        test_function
    ]