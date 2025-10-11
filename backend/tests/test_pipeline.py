"""
Tests for the full TikTok processing pipeline
"""
import pytest
import tempfile
from pathlib import Path

from app.services.tiktok.downloader import TikTokDownloader
from app.services.audio.processor import AudioProcessor
from app.services.storage.s3 import S3Storage


class TestFullPipeline:
    """Integration tests for the complete processing pipeline"""

    @pytest.mark.asyncio
    async def test_complete_pipeline(self, sample_tiktok_url: str):
        """Test full pipeline: download -> audio extraction -> waveform -> upload"""
        sample_id = "test-pipeline-sample"

        with tempfile.TemporaryDirectory() as temp_dir:
            # Step 1: Download video
            downloader = TikTokDownloader()
            metadata = await downloader.download_video(sample_tiktok_url, temp_dir)

            video_path = Path(metadata['video_path'])
            assert video_path.exists()
            assert video_path.stat().st_size > 0

            # Step 2: Extract audio
            processor = AudioProcessor()
            audio_files = await processor.extract_audio(str(video_path), temp_dir)

            assert 'wav' in audio_files
            assert 'mp3' in audio_files
            assert Path(audio_files['wav']).exists()
            assert Path(audio_files['mp3']).exists()

            # Step 3: Generate waveform
            waveform_path = await processor.generate_waveform(audio_files['wav'], temp_dir)

            assert Path(waveform_path).exists()
            assert Path(waveform_path).suffix == '.png'

            # Step 4: Upload to storage
            storage = S3Storage()

            try:
                wav_url = await storage.upload_file(
                    audio_files['wav'],
                    f"samples/{sample_id}/audio.wav"
                )
                assert wav_url is not None
                assert isinstance(wav_url, str)

                mp3_url = await storage.upload_file(
                    audio_files['mp3'],
                    f"samples/{sample_id}/audio.mp3"
                )
                assert mp3_url is not None
                assert isinstance(mp3_url, str)

                waveform_url = await storage.upload_file(
                    waveform_path,
                    f"samples/{sample_id}/waveform.png"
                )
                assert waveform_url is not None
                assert isinstance(waveform_url, str)

            finally:
                # Cleanup: delete uploaded files
                await storage.delete_file(f"samples/{sample_id}/audio.wav")
                await storage.delete_file(f"samples/{sample_id}/audio.mp3")
                await storage.delete_file(f"samples/{sample_id}/waveform.png")

    @pytest.mark.asyncio
    async def test_audio_extraction(self, sample_tiktok_url: str):
        """Test just the audio extraction step"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Download video first
            downloader = TikTokDownloader()
            metadata = await downloader.download_video(sample_tiktok_url, temp_dir)

            # Extract audio
            processor = AudioProcessor()
            audio_files = await processor.extract_audio(metadata['video_path'], temp_dir)

            # Verify both formats exist
            wav_path = Path(audio_files['wav'])
            mp3_path = Path(audio_files['mp3'])

            assert wav_path.exists()
            assert mp3_path.exists()
            assert wav_path.suffix == '.wav'
            assert mp3_path.suffix == '.mp3'
            assert wav_path.stat().st_size > 0
            assert mp3_path.stat().st_size > 0

    @pytest.mark.asyncio
    async def test_waveform_generation(self, sample_tiktok_url: str):
        """Test just the waveform generation step"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Download and extract audio first
            downloader = TikTokDownloader()
            metadata = await downloader.download_video(sample_tiktok_url, temp_dir)

            processor = AudioProcessor()
            audio_files = await processor.extract_audio(metadata['video_path'], temp_dir)

            # Generate waveform
            waveform_path = await processor.generate_waveform(audio_files['wav'], temp_dir)

            # Verify waveform
            waveform = Path(waveform_path)
            assert waveform.exists()
            assert waveform.suffix == '.png'
            assert waveform.stat().st_size > 0
