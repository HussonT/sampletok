#!/usr/bin/env python3
"""Test the full processing pipeline directly"""

import asyncio
import tempfile
from pathlib import Path
import sys
sys.path.insert(0, '/Users/tomhusson/sideprojects/sampletok/sampletok/backend')

from app.services.tiktok.downloader import TikTokDownloader
from app.services.audio.processor import AudioProcessor
from app.services.storage.s3 import S3Storage

async def test_pipeline():
    """Test full pipeline: download -> audio -> waveform -> upload"""

    test_url = "https://www.tiktok.com/@zachking/video/6768504823336815877"
    sample_id = "test-sample-123"

    print("🚀 Testing full pipeline...")

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            # Step 1: Download video
            print("\n1️⃣ Downloading video...")
            downloader = TikTokDownloader()
            metadata = await downloader.download_video(test_url, temp_dir)
            print(f"   ✅ Downloaded: {metadata['video_path']}")

            # Step 2: Extract audio
            print("\n2️⃣ Extracting audio...")
            processor = AudioProcessor()
            audio_files = await processor.extract_audio(metadata['video_path'], temp_dir)
            print(f"   ✅ WAV: {audio_files['wav']}")
            print(f"   ✅ MP3: {audio_files['mp3']}")

            # Step 3: Generate waveform
            print("\n3️⃣ Generating waveform...")
            waveform_path = await processor.generate_waveform(audio_files['wav'], temp_dir)
            print(f"   ✅ Waveform: {waveform_path}")

            # Step 4: Upload to storage
            print("\n4️⃣ Uploading to MinIO...")
            storage = S3Storage()

            wav_url = await storage.upload_file(
                audio_files['wav'],
                f"samples/{sample_id}/audio.wav"
            )
            print(f"   ✅ WAV uploaded: {wav_url}")

            mp3_url = await storage.upload_file(
                audio_files['mp3'],
                f"samples/{sample_id}/audio.mp3"
            )
            print(f"   ✅ MP3 uploaded: {mp3_url}")

            waveform_url = await storage.upload_file(
                waveform_path,
                f"samples/{sample_id}/waveform.png"
            )
            print(f"   ✅ Waveform uploaded: {waveform_url}")

            print("\n✨ Pipeline completed successfully!")
            print(f"\nFinal URLs:")
            print(f"  MP3: {mp3_url}")
            print(f"  Waveform: {waveform_url}")

    except Exception as e:
        print(f"\n❌ Pipeline failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_pipeline())