'use client';

import React, { useRef, useEffect, useState } from 'react';
import { Play, Pause, X, SkipForward, SkipBack, Volume2, VolumeX } from 'lucide-react';
import { Sample } from '@/types/api';
import { Avatar, AvatarImage, AvatarFallback } from '@/components/ui/avatar';
import { Slider } from '@/components/ui/slider';
import { getAvatarWithFallback } from '@/lib/avatar';
import { HlsAudioPlayer } from '@/components/features/hls-audio-player';
import { useHaptics } from '@/hooks/use-haptics';
import { useMobileSettings } from '@/hooks/use-mobile-settings';

interface MobileMiniPlayerProps {
  sample?: Sample | null;
  isPlaying?: boolean;
  onPlayPause?: () => void;
  onClose?: () => void;
  onNext?: () => void;
  onPrevious?: () => void;
  autoPlayNext?: boolean;
}

export function MobileMiniPlayer({
  sample,
  isPlaying = false,
  onPlayPause,
  onClose,
  onNext,
  onPrevious,
  autoPlayNext = false,
}: MobileMiniPlayerProps) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const playPromiseRef = useRef<Promise<void> | null>(null);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(0.7);
  const [isMuted, setIsMuted] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);

  // Mobile settings for haptic feedback
  const { settings } = useMobileSettings();
  const { triggerHaptic } = useHaptics({ enabled: settings.hapticFeedback });

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

  // Sync volume with audio element
  useEffect(() => {
    if (audioRef.current) {
      audioRef.current.volume = isMuted ? 0 : volume;
    }
  }, [volume, isMuted]);

  // Auto-play next track when current track ends
  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    const handleEnded = () => {
      if (autoPlayNext && onNext) {
        onNext();
      }
    };

    audio.addEventListener('ended', handleEnded);
    return () => audio.removeEventListener('ended', handleEnded);
  }, [autoPlayNext, onNext]);

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

  const handleSeek = (value: number[]) => {
    const newTime = value[0];
    setCurrentTime(newTime);
    if (audioRef.current) {
      audioRef.current.currentTime = newTime;
    }
    triggerHaptic('light');
  };

  const handleVolumeChange = (value: number[]) => {
    const newVolume = value[0];
    setVolume(newVolume);
    if (newVolume > 0 && isMuted) {
      setIsMuted(false);
    }
  };

  const toggleMute = () => {
    setIsMuted(!isMuted);
    triggerHaptic('medium');
  };

  const handlePlayPause = () => {
    onPlayPause?.();
    triggerHaptic('medium');
  };

  const handleNext = () => {
    onNext?.();
    triggerHaptic('medium');
  };

  const handlePrevious = () => {
    onPrevious?.();
    triggerHaptic('medium');
  };

  const handleClose = () => {
    onClose?.();
    triggerHaptic('light');
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

      {/* Enhanced Mini Player UI */}
      <div className="fixed bottom-16 left-0 right-0 bg-background/95 backdrop-blur-lg border-t border-border z-50 transition-all duration-300">
        {/* Compact View */}
        <div className="px-4 py-3">
          {/* Scrubbing Progress Bar - Touch-friendly */}
          <div className="mb-3">
            <Slider
              value={[currentTime]}
              max={duration || 100}
              step={0.1}
              onValueChange={handleSeek}
              className="w-full cursor-pointer"
            />
            <div className="flex justify-between items-center mt-1">
              <span className="text-xs text-muted-foreground tabular-nums">
                {formatDuration(currentTime)}
              </span>
              <span className="text-xs text-muted-foreground tabular-nums">
                {formatDuration(duration)}
              </span>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {/* Creator avatar */}
            <Avatar className="w-10 h-10 flex-shrink-0 ring-2 ring-primary/20">
              <AvatarImage
                src={creator.avatar || getAvatarWithFallback(null, creator.username)}
                alt={creator.name}
              />
              <AvatarFallback className="text-xs bg-gradient-to-br from-primary/80 to-primary/60">
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

            {/* Control buttons */}
            <div className="flex items-center gap-2 flex-shrink-0">
              {/* Previous button */}
              {onPrevious && (
                <button
                  onClick={handlePrevious}
                  className="w-10 h-10 rounded-full flex items-center justify-center hover:bg-secondary/50 active:scale-95 transition-all"
                  aria-label="Previous track"
                >
                  <SkipBack className="w-5 h-5" />
                </button>
              )}

              {/* Play/Pause button */}
              <button
                onClick={handlePlayPause}
                className="w-10 h-10 rounded-full flex items-center justify-center hover:bg-secondary/50 active:scale-95 transition-all"
                aria-label={isPlaying ? 'Pause' : 'Play'}
              >
                {isPlaying ? (
                  <Pause className="w-5 h-5" />
                ) : (
                  <Play className="w-5 h-5 ml-0.5" />
                )}
              </button>

              {/* Next button */}
              {onNext && (
                <button
                  onClick={handleNext}
                  className="w-10 h-10 rounded-full flex items-center justify-center hover:bg-secondary/50 active:scale-95 transition-all"
                  aria-label="Next track"
                >
                  <SkipForward className="w-5 h-5" />
                </button>
              )}

              {/* Volume button - toggles expanded controls */}
              <button
                onClick={() => setIsExpanded(!isExpanded)}
                className="w-9 h-9 rounded-full flex items-center justify-center hover:bg-secondary/50 active:scale-95 transition-all"
                aria-label="Volume"
              >
                {isMuted ? (
                  <VolumeX className="w-4 h-4" />
                ) : (
                  <Volume2 className="w-4 h-4" />
                )}
              </button>

              {/* Close button */}
              <button
                onClick={handleClose}
                className="w-9 h-9 rounded-full flex items-center justify-center hover:bg-secondary/50 active:scale-95 transition-all"
                aria-label="Close player"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>

        {/* Expanded Volume Control */}
        {isExpanded && (
          <div className="px-4 pb-3 border-t border-border/50 animate-in slide-in-from-bottom-2 duration-200">
            <div className="pt-3 flex items-center gap-3">
              <button
                onClick={toggleMute}
                className="w-8 h-8 rounded-full flex items-center justify-center hover:bg-secondary/50 active:scale-95 transition-all"
                aria-label={isMuted ? 'Unmute' : 'Mute'}
              >
                {isMuted ? (
                  <VolumeX className="w-4 h-4" />
                ) : (
                  <Volume2 className="w-4 h-4" />
                )}
              </button>
              <Slider
                value={[isMuted ? 0 : volume]}
                max={1}
                step={0.01}
                onValueChange={handleVolumeChange}
                className="flex-1 cursor-pointer"
              />
              <span className="text-xs text-muted-foreground tabular-nums w-10 text-right">
                {Math.round((isMuted ? 0 : volume) * 100)}%
              </span>
            </div>
          </div>
        )}
      </div>
    </>
  );
}
