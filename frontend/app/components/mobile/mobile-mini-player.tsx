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
