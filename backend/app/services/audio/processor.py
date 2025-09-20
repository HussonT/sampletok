import asyncio
import logging
from pathlib import Path
from typing import Dict, Optional
import subprocess
import json

from app.core.config import settings

logger = logging.getLogger(__name__)


class AudioProcessor:
    """Process audio from video files"""

    async def extract_audio(self, video_path: str, output_dir: str) -> Dict[str, str]:
        """
        Extract audio from video file and create both WAV and MP3 versions
        Returns dict with paths to wav and mp3 files
        """
        video_path = Path(video_path)
        output_dir = Path(output_dir)

        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")

        # Output paths
        wav_path = output_dir / f"{video_path.stem}.wav"
        mp3_path = output_dir / f"{video_path.stem}.mp3"

        try:
            # Extract to WAV (24-bit, 48kHz)
            wav_cmd = [
                'ffmpeg', '-i', str(video_path),
                '-vn',  # No video
                '-acodec', 'pcm_s24le',  # 24-bit PCM
                '-ar', str(settings.AUDIO_SAMPLE_RATE),  # 48kHz
                '-ac', '2',  # Stereo
                '-y',  # Overwrite
                str(wav_path)
            ]

            # Run ffmpeg command
            result = await self._run_command(wav_cmd)
            if result.returncode != 0:
                raise Exception(f"FFmpeg WAV extraction failed: {result.stderr}")

            # Convert to MP3 (320kbps)
            mp3_cmd = [
                'ffmpeg', '-i', str(wav_path),
                '-acodec', 'libmp3lame',
                '-b:a', f'{settings.MP3_BITRATE}k',
                '-y',
                str(mp3_path)
            ]

            result = await self._run_command(mp3_cmd)
            if result.returncode != 0:
                raise Exception(f"FFmpeg MP3 conversion failed: {result.stderr}")

            # Normalize audio levels
            await self.normalize_audio(str(wav_path))
            await self.normalize_audio(str(mp3_path))

            return {
                'wav': str(wav_path),
                'mp3': str(mp3_path)
            }

        except Exception as e:
            logger.error(f"Error extracting audio: {str(e)}")
            raise

    async def normalize_audio(self, audio_path: str) -> None:
        """Normalize audio levels using ffmpeg"""
        temp_path = f"{audio_path}.temp"

        cmd = [
            'ffmpeg', '-i', audio_path,
            '-af', 'loudnorm=I=-16:TP=-1.5:LRA=11',
            '-y',
            temp_path
        ]

        result = await self._run_command(cmd)
        if result.returncode == 0:
            # Replace original with normalized
            Path(temp_path).replace(audio_path)

    async def generate_waveform(self, audio_path: str, output_dir: str) -> str:
        """
        Generate waveform visualization from audio file
        Returns path to waveform image
        """
        audio_path = Path(audio_path)
        output_dir = Path(output_dir)
        waveform_path = output_dir / f"{audio_path.stem}_waveform.png"

        try:
            # Use ffmpeg to generate waveform
            cmd = [
                'ffmpeg', '-i', str(audio_path),
                '-filter_complex',
                f'[0:a]showwavespic=s={settings.WAVEFORM_WIDTH}x{settings.WAVEFORM_HEIGHT}:colors=#4B5EFF',
                '-frames:v', '1',
                '-y',
                str(waveform_path)
            ]

            result = await self._run_command(cmd)
            if result.returncode != 0:
                raise Exception(f"FFmpeg waveform generation failed: {result.stderr}")

            return str(waveform_path)

        except Exception as e:
            logger.error(f"Error generating waveform: {str(e)}")
            raise

    async def get_audio_metadata(self, audio_path: str) -> Dict:
        """Extract metadata from audio file"""
        cmd = [
            'ffprobe',
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            '-show_streams',
            audio_path
        ]

        result = await self._run_command(cmd)
        if result.returncode != 0:
            raise Exception(f"FFprobe failed: {result.stderr}")

        metadata = json.loads(result.stdout)

        # Extract relevant info
        duration = float(metadata.get('format', {}).get('duration', 0))
        sample_rate = None
        channels = None

        for stream in metadata.get('streams', []):
            if stream.get('codec_type') == 'audio':
                sample_rate = int(stream.get('sample_rate', 0))
                channels = int(stream.get('channels', 0))
                break

        return {
            'duration': duration,
            'sample_rate': sample_rate,
            'channels': channels,
            'format': metadata.get('format', {}).get('format_name'),
            'bitrate': int(metadata.get('format', {}).get('bit_rate', 0))
        }

    async def _run_command(self, cmd: list) -> subprocess.CompletedProcess:
        """Run shell command asynchronously"""
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        return subprocess.CompletedProcess(
            args=cmd,
            returncode=process.returncode,
            stdout=stdout.decode() if stdout else '',
            stderr=stderr.decode() if stderr else ''
        )