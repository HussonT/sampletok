'use client';

import React, { useRef, useEffect, useState } from 'react';
import { Play, Pause, X } from 'lucide-react';
import { Sample } from '@/types/api';
import { Avatar, AvatarImage, AvatarFallback } from '@/components/ui/avatar';
import { getAvatarWithFallback } from '@/lib/avatar';
import { HlsAudioPlayer } from '@/components/features/hls-audio-player';

interface MobileMiniPlayerProps {
  sample?: Sample | null;
  isPlaying?: boolean;
  onPlayPause?: () => void;
  onClose?: () => void;
}

export function MobileMiniPlayer({
  sample,
  isPlaying = false,
  onPlayPause,
  onClose,
}: MobileMiniPlayerProps) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const playPromiseRef = useRef<Promise<void> | null>(null);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);

  // Reset current time when sample changes
  useEffect(() => {
    setCurrentTime(0);
    setDuration(sample?.duration_seconds || 0);
    if (audioRef.current) {
      audioRef.current.currentTime = 0;
    }
  }, [sample?.id, sample?.duration_seconds]);

  /**
   * Media Session API Integration
   *
   * Enables background playback controls on mobile devices.
   * Shows media notifications with playback controls in:
   * - Lock screen
   * - Notification center
   * - Control center (iOS)
   * - System media controls (Android)
   *
   * Features:
   * - Play/pause controls
   * - Track metadata (title, artist, artwork)
   * - Seek forward/backward (10 seconds)
   * - Previous/next track (if available)
   */
  useEffect(() => {
    if (!sample || typeof window === 'undefined' || !('mediaSession' in navigator)) {
      return;
    }

    const creator = getCreatorInfo();

    try {
      // Set metadata for the current track
      navigator.mediaSession.metadata = new MediaMetadata({
        title: sample.title || sample.description || 'Unknown Track',
        artist: creator.name,
        album: 'SampleTok',
        artwork: [
          // Use thumbnail as artwork
          {
            src: sample.thumbnail_url || sample.cover_url || '/icon-192x192.png',
            sizes: '192x192',
            type: 'image/png'
          },
          {
            src: sample.thumbnail_url || sample.cover_url || '/icon-512x512.png',
            sizes: '512x512',
            type: 'image/png'
          }
        ]
      });

      // Set playback state
      navigator.mediaSession.playbackState = isPlaying ? 'playing' : 'paused';

      // Action handlers
      navigator.mediaSession.setActionHandler('play', () => {
        onPlayPause?.();
      });

      navigator.mediaSession.setActionHandler('pause', () => {
        onPlayPause?.();
      });

      // Seek forward 10 seconds
      navigator.mediaSession.setActionHandler('seekforward', () => {
        if (audioRef.current) {
          audioRef.current.currentTime = Math.min(
            audioRef.current.currentTime + 10,
            duration
          );
        }
      });

      // Seek backward 10 seconds
      navigator.mediaSession.setActionHandler('seekbackward', () => {
        if (audioRef.current) {
          audioRef.current.currentTime = Math.max(
            audioRef.current.currentTime - 10,
            0
          );
        }
      });

      // Update position state (for progress bar in notifications)
      const updatePositionState = () => {
        if ('setPositionState' in navigator.mediaSession && audioRef.current) {
          try {
            navigator.mediaSession.setPositionState({
              duration: duration || audioRef.current.duration || 0,
              playbackRate: audioRef.current.playbackRate,
              position: audioRef.current.currentTime || 0,
            });
          } catch (error) {
            // Some browsers don't support all position state features
            console.debug('Media Session position state error:', error);
          }
        }
      };

      // Update position state periodically
      const positionInterval = setInterval(updatePositionState, 1000);

      // Cleanup on unmount or sample change
      return () => {
        clearInterval(positionInterval);
        if ('mediaSession' in navigator) {
          navigator.mediaSession.metadata = null;
          navigator.mediaSession.setActionHandler('play', null);
          navigator.mediaSession.setActionHandler('pause', null);
          navigator.mediaSession.setActionHandler('seekforward', null);
          navigator.mediaSession.setActionHandler('seekbackward', null);
        }
      };
    } catch (error) {
      // Silent fail - Media Session API is enhancement, not critical
      console.debug('Media Session API error:', error);
    }
  }, [sample, isPlaying, duration, onPlayPause]);

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio || !sample) return;

    const handlePlayback = async () => {
      if (isPlaying) {
        // Wait for any pending play operation to complete before starting a new one
        if (playPromiseRef.current) {
          try {
            await playPromiseRef.current;
          } catch (error) {
            // Ignore errors from previous play attempts
          }
        }

        // Start playing
        playPromiseRef.current = audio.play().catch(error => {
          // Only log non-abort errors
          if (error instanceof Error && error.name !== 'AbortError') {
            console.error('Error playing audio:', error);
          }
        });
      } else {
        // Wait for any pending play to complete before pausing
        if (playPromiseRef.current) {
          try {
            await playPromiseRef.current;
          } catch (error) {
            // Ignore errors
          }
          playPromiseRef.current = null;
        }
        audio.pause();
      }
    };

    handlePlayback();
  }, [isPlaying, sample]);

  const handleTimeUpdate = () => {
    if (audioRef.current) {
      setCurrentTime(audioRef.current.currentTime);
      // If duration wasn't set from metadata, get it from the audio element
      if (!duration && audioRef.current.duration) {
        setDuration(audioRef.current.duration);
      }
    }
  };

  if (!sample) return null;

  const formatDuration = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const getCreatorInfo = () => {
    if (sample.source === 'instagram' && sample.instagram_creator) {
      return {
        name: sample.instagram_creator.full_name || sample.instagram_creator.username,
        username: `@${sample.instagram_creator.username}`,
        avatar: sample.instagram_creator.profile_pic_url,
      };
    }

    if (sample.tiktok_creator) {
      return {
        name: sample.tiktok_creator.nickname || sample.tiktok_creator.username,
        username: `@${sample.tiktok_creator.username}`,
        avatar: sample.tiktok_creator.avatar_thumb,
      };
    }

    return {
      name: sample.creator_name || 'Unknown Creator',
      username: sample.creator_username ? `@${sample.creator_username}` : '',
      avatar: undefined,
    };
  };

  const creator = getCreatorInfo();
  const progressPercentage = duration ? (currentTime / duration) * 100 : 0;

  return (
    <>
      {/* Hidden HLS audio player */}
      {sample && (
        <HlsAudioPlayer
          hlsUrl={sample.audio_url_hls}
          mp3Url={sample.audio_url_mp3 || sample.audio_url_wav}
          audioRef={audioRef}
          preload="metadata"
          crossOrigin="anonymous"
          onTimeUpdate={handleTimeUpdate}
        />
      )}

      {/* Mini Player UI */}
      <div className="fixed bottom-16 left-0 right-0 bg-background/95 backdrop-blur-lg border-t border-border z-50">
        {/* Progress bar */}
        <div className="absolute top-0 left-0 right-0 h-0.5 bg-secondary">
          <div
            className="h-full bg-primary transition-all duration-100"
            style={{ width: `${progressPercentage}%` }}
          />
        </div>

        <div className="flex items-center gap-3 px-4 py-2">
          {/* Play/Pause button */}
          <button
            onClick={onPlayPause}
            className="flex-shrink-0 w-10 h-10 rounded flex items-center justify-center hover:bg-secondary/50 active:scale-95 transition-all"
          >
            {isPlaying ? (
              <Pause className="w-5 h-5" />
            ) : (
              <Play className="w-5 h-5 ml-0.5" />
            )}
          </button>

          {/* Creator avatar */}
          <Avatar className="w-10 h-10 flex-shrink-0">
            <AvatarImage
              src={creator.avatar || getAvatarWithFallback(null, creator.username)}
              alt={creator.name}
            />
            <AvatarFallback className="text-xs">
              {creator.name[0]?.toUpperCase() || '?'}
            </AvatarFallback>
          </Avatar>

          {/* Track info */}
          <div className="flex-1 min-w-0">
            <div className="text-sm font-medium truncate">
              {sample.title || sample.description || 'Unknown Track'}
            </div>
            <div className="text-xs text-muted-foreground truncate">
              {creator.name}
            </div>
          </div>

          {/* Time display */}
          <div className="flex-shrink-0 text-xs text-muted-foreground tabular-nums">
            {formatDuration(currentTime)} / {formatDuration(duration)}
          </div>

          {/* Close button */}
          <button
            onClick={onClose}
            className="flex-shrink-0 w-10 h-10 rounded flex items-center justify-center hover:bg-secondary/50 active:scale-95 transition-all"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>
    </>
  );
}
