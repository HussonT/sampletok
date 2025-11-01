'use client';

import { useEffect, useRef } from 'react';
import Hls from 'hls.js';

interface HlsAudioPlayerProps {
  hlsUrl?: string;
  mp3Url?: string;
  audioRef: React.RefObject<HTMLAudioElement | null>;
  preload?: "none" | "metadata" | "auto";
  crossOrigin?: "anonymous" | "use-credentials";
  onTimeUpdate?: () => void;
  onEnded?: () => void;
}

/**
 * HLS Audio Player Component
 *
 * Wraps HTML5 audio element with HLS.js for adaptive streaming support.
 * Falls back to direct MP3 playback if:
 * - HLS URL is not available
 * - Browser natively supports HLS (Safari)
 * - HLS.js is not supported
 *
 * Benefits of HLS:
 * - Instant playback: Loads first 2-second segment (~80KB) instead of full file (1.2MB)
 * - Professional streaming: Same technology used by Spotify, YouTube, Netflix
 * - Better buffering: Adaptive segment loading based on network conditions
 * - Seek performance: Jump to any point without downloading entire file
 */
export function HlsAudioPlayer({
  hlsUrl,
  mp3Url,
  audioRef,
  preload = "metadata",
  crossOrigin = "anonymous",
  onTimeUpdate,
  onEnded
}: HlsAudioPlayerProps) {
  const hlsRef = useRef<Hls | null>(null);

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    // Check if we have any valid source
    if (!hlsUrl && !mp3Url) {
      console.warn('No audio source available (neither HLS nor MP3)');
      return;
    }

    // Priority 1: Use HLS if available and supported
    if (hlsUrl && Hls.isSupported()) {
      // Initialize HLS.js
      const hls = new Hls({
        enableWorker: true,
        lowLatencyMode: false,
        backBufferLength: 10,  // Keep 10 seconds in buffer
        maxBufferLength: 30,    // Buffer ahead 30 seconds
        maxMaxBufferLength: 60, // Max buffer 60 seconds
        maxBufferSize: 60 * 1000 * 1000, // 60MB buffer
      });

      hlsRef.current = hls;

      hls.on(Hls.Events.ERROR, (event, data) => {
        if (data.fatal) {
          switch (data.type) {
            case Hls.ErrorTypes.NETWORK_ERROR:
              console.error('HLS network error, trying to recover');
              hls.startLoad();
              break;
            case Hls.ErrorTypes.MEDIA_ERROR:
              console.error('HLS media error, trying to recover');
              hls.recoverMediaError();
              break;
            default:
              console.error('HLS fatal error, falling back to MP3', data);
              // Fallback to MP3 if available
              if (mp3Url) {
                hls.destroy();
                hlsRef.current = null;
                audio.src = mp3Url;
              }
              break;
          }
        }
      });

      hls.loadSource(hlsUrl);
      hls.attachMedia(audio);

      return () => {
        if (hlsRef.current) {
          hlsRef.current.destroy();
          hlsRef.current = null;
        }
      };
    }
    // Priority 2: Native HLS support (Safari)
    else if (hlsUrl && audio.canPlayType('application/vnd.apple.mpegurl')) {
      // Safari supports HLS natively
      audio.src = hlsUrl;
    }
    // Priority 3: Fallback to MP3
    else if (mp3Url) {
      audio.src = mp3Url;
    }

    return () => {
      // Cleanup - only clear if we set it
      if (audio.src) {
        audio.src = '';
      }
    };
  }, [hlsUrl, mp3Url, audioRef]);

  return (
    <audio
      ref={audioRef}
      preload={preload}
      crossOrigin={crossOrigin}
      onTimeUpdate={onTimeUpdate}
      onEnded={onEnded}
    />
  );
}
