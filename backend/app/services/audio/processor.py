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

    async def generate_hls_stream(self, audio_path: str, output_dir: str) -> Dict[str, any]:
        """
        Generate HLS stream from audio file at 320kbps
        Creates .m3u8 playlist and segment files for instant streaming playback

        Args:
            audio_path: Path to source audio file (MP3 or WAV)
            output_dir: Directory to store HLS files

        Returns:
            Dict with 'playlist' path and list of 'segments'
        """
        audio_path = Path(audio_path)
        output_dir = Path(output_dir)

        # Create HLS subdirectory
        hls_dir = output_dir / f"{audio_path.stem}_hls"
        hls_dir.mkdir(parents=True, exist_ok=True)

        # Output files
        playlist_path = hls_dir / "playlist.m3u8"
        segment_pattern = str(hls_dir / "segment_%03d.ts")

        try:
            # Generate HLS stream with 2-second segments at 320kbps
            # Using fMP4 would be better for modern browsers, but TS has better compatibility
            hls_cmd = [
                'ffmpeg', '-i', str(audio_path),
                '-c:a', 'aac',  # AAC codec (better than MP3 for HLS)
                '-b:a', '320k',  # 320kbps bitrate (matching MP3 quality)
                '-ac', '2',  # Stereo
                '-ar', '48000',  # 48kHz sample rate
                '-f', 'hls',  # HLS format
                '-hls_time', '2',  # 2-second segments
                '-hls_list_size', '0',  # Include all segments in playlist
                '-hls_segment_type', 'mpegts',  # Use MPEG-TS segments
                '-hls_segment_filename', segment_pattern,
                '-y',
                str(playlist_path)
            ]

            logger.info(f"Generating HLS stream for {audio_path.name}")
            result = await self._run_command(hls_cmd)

            if result.returncode != 0:
                raise Exception(f"FFmpeg HLS generation failed: {result.stderr}")

            # Get list of generated segment files
            segments = sorted(hls_dir.glob("segment_*.ts"))
            segment_paths = [str(seg) for seg in segments]

            logger.info(f"Generated HLS stream: {len(segment_paths)} segments")

            return {
                'playlist': str(playlist_path),
                'segments': segment_paths,
                'hls_dir': str(hls_dir)
            }

        except Exception as e:
            logger.error(f"Error generating HLS stream: {str(e)}")
            raise

    async def generate_waveform(self, audio_path: str, output_dir: str) -> str:
        """
        Generate normalized waveform visualization with consistent amplitude display
        Returns path to waveform image
        """
        audio_path = Path(audio_path)
        output_dir = Path(output_dir)
        waveform_path = output_dir / f"{audio_path.stem}_waveform.png"

        try:
            # Use ffmpeg to generate normalized waveform with pink to purple gradient
            # scale=sqrt compresses dynamic range so all waveforms appear similar in size
            cmd = [
                'ffmpeg', '-i', str(audio_path),
                '-filter_complex',
                f'[0:a]showwavespic=s={settings.WAVEFORM_WIDTH}x{settings.WAVEFORM_HEIGHT}:colors=#EC4899|#8B5CF6:scale=sqrt',
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