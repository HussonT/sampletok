import logging
from pathlib import Path
from typing import Dict, Optional
import librosa
import essentia.standard as es

logger = logging.getLogger(__name__)


class AudioAnalyzer:
    """Analyze audio files to extract musical features like BPM and key"""

    async def analyze_audio(self, audio_path: str) -> Dict:
        """
        Analyze audio file and extract musical features
        Returns dict with bpm, key, scale, and confidence scores
        """
        audio_path = Path(audio_path)

        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        try:
            # Detect BPM
            bpm = await self.detect_bpm(str(audio_path))

            # Detect key
            key_data = await self.detect_key(str(audio_path))

            return {
                'bpm': bpm,
                'key': key_data['key'],
                'scale': key_data['scale'],
                'key_confidence': key_data['confidence']
            }

        except Exception as e:
            logger.error(f"Error analyzing audio: {str(e)}")
            # Return partial results or None values on failure
            return {
                'bpm': None,
                'key': None,
                'scale': None,
                'key_confidence': None
            }

    async def detect_bpm(self, audio_path: str) -> Optional[int]:
        """
        Detect BPM (tempo) using Essentia's RhythmExtractor2013
        More accurate than librosa, handles octave errors better
        Returns integer BPM or None on failure

        Note: Automatic BPM detection can have octave errors (detecting 2x or 0.5x the actual tempo).
        This is a fundamental limitation of algorithmic tempo detection.
        """
        try:
            logger.info(f"Detecting BPM for {audio_path}")

            # Load audio file using Essentia (requires 44100 Hz)
            audio = es.MonoLoader(filename=audio_path, sampleRate=44100)()

            # Extract rhythm features using RhythmExtractor2013
            # Use 'multifeature' method for better accuracy (slower but more precise)
            rhythm_extractor = es.RhythmExtractor2013(method="multifeature")
            bpm, beats, beats_confidence, _, beats_intervals = rhythm_extractor(audio)

            bpm_int = int(round(bpm)) if bpm else None

            logger.info(f"Detected BPM: {bpm_int} (confidence: {beats_confidence:.2f})")
            return bpm_int

        except Exception as e:
            logger.error(f"Error detecting BPM: {str(e)}")
            # Fallback to librosa if Essentia fails
            try:
                logger.info("Falling back to librosa for BPM detection...")
                y, sr = librosa.load(audio_path, sr=None)
                tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
                bpm_int = int(tempo) if tempo else None
                logger.info(f"Librosa detected BPM: {bpm_int}")
                return bpm_int
            except Exception as fallback_error:
                logger.error(f"Fallback BPM detection also failed: {fallback_error}")
                return None

    async def detect_key(self, audio_path: str) -> Dict:
        """
        Detect musical key using Essentia's KeyExtractor
        Returns dict with key, scale (major/minor), and confidence
        """
        try:
            logger.info(f"Detecting key for {audio_path}")

            # Load audio file using Essentia
            audio = es.MonoLoader(filename=audio_path)()

            # Extract key using KeyExtractor algorithm
            # Uses 'bgate' profile by default (best for general pop/electronic music)
            key_extractor = es.KeyExtractor()
            key, scale, strength = key_extractor(audio)

            logger.info(f"Detected key: {key} {scale} (confidence: {strength:.2f})")

            return {
                'key': key,
                'scale': scale,
                'confidence': float(strength)
            }

        except Exception as e:
            logger.error(f"Error detecting key: {str(e)}")
            return {
                'key': None,
                'scale': None,
                'confidence': None
            }
