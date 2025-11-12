import React, { useState, useRef, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Slider } from '@/components/ui/slider';
import { Badge } from '@/components/ui/badge';
import {
  Play,
  Pause,
  SkipBack,
  SkipForward,
  Volume2,
  VolumeX,
  Download,
  ExternalLink
} from 'lucide-react';
import { Avatar, AvatarImage, AvatarFallback } from '@/components/ui/avatar';
import { Sample } from '@/types/api';
import { HlsAudioPlayer } from './hls-audio-player';
import { analytics } from '@/lib/analytics';

interface AudioPlayerProps {
  sample: Sample | null;
  isPlaying: boolean;
  onPlayPause: () => void;
  onNext: () => void;
  onPrevious: () => void;
  onDownload: (sample: Sample) => void;
}

export function AudioPlayer({ 
  sample, 
  isPlaying, 
  onPlayPause, 
  onNext, 
  onPrevious, 
  onDownload 
}: AudioPlayerProps) {
  const [currentTime, setCurrentTime] = useState(0);
  const [volume, setVolume] = useState(0.7);
  const [isMuted, setIsMuted] = useState(false);
  const audioRef = useRef<HTMLAudioElement>(null);

  // Handle sample changes - reset audio state
  useEffect(() => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
      setCurrentTime(0);
    }

    // Track audio play when new sample loads and starts playing
    if (sample && isPlaying) {
      analytics.samplePlayed(sample, 'player');
    }
  }, [sample, isPlaying]);

  // Handle play/pause state
  useEffect(() => {
    if (!audioRef.current) return;

    const playAudio = async () => {
      try {
        if (isPlaying) {
          await audioRef.current!.play();
        } else {
          audioRef.current!.pause();
        }
      } catch (error) {
        // Ignore AbortError - happens when play is interrupted (expected behavior)
        if (error instanceof Error && error.name !== 'AbortError') {
          console.error('Error playing audio:', error);
        }
      }
    };

    playAudio();
  }, [isPlaying]);

  useEffect(() => {
    if (audioRef.current) {
      audioRef.current.volume = isMuted ? 0 : volume;
    }
  }, [volume, isMuted]);

  const handleTimeUpdate = () => {
    if (audioRef.current) {
      setCurrentTime(audioRef.current.currentTime);
    }
  };

  const handleSeek = (value: number[]) => {
    const time = value[0];
    setCurrentTime(time);
    if (audioRef.current) {
      audioRef.current.currentTime = time;
    }
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const formatViewCount = (count: number) => {
    if (count >= 1000000) return `${(count / 1000000).toFixed(1)}M`;
    if (count >= 1000) return `${(count / 1000).toFixed(1)}K`;
    return count.toString();
  };

  if (!sample) return null;

  return (
    <>
      {/* Hidden HLS audio player */}
      <HlsAudioPlayer
        hlsUrl={sample.audio_url_hls}
        mp3Url={sample.audio_url_mp3 || sample.audio_url_wav}
        audioRef={audioRef}
        preload="metadata"
        crossOrigin="anonymous"
        onTimeUpdate={handleTimeUpdate}
        onEnded={() => onNext()}
      />

      {/* Floating Player */}
      <Card className="fixed bottom-4 left-4 right-4 z-30 bg-card/95 backdrop-blur-sm border border-border shadow-2xl shadow-primary/20">
        <div className="p-4">
          {/* Sample Info */}
          <div className="flex items-center gap-4 mb-3">
            <Avatar className="w-12 h-12 shrink-0">
              <AvatarImage
                src={sample.tiktok_creator?.avatar_thumb || sample.instagram_creator?.profile_pic_url || sample.thumbnail_url}
                alt={sample.creator_username || 'Creator'}
              />
              <AvatarFallback>
                {(sample.creator_username || 'U').substring(0, 2).toUpperCase()}
              </AvatarFallback>
            </Avatar>
            <div className="flex-1 min-w-0">
              <p className="truncate font-medium text-foreground">@{sample.creator_username}</p>
              <p className="text-xs text-muted-foreground truncate">
                {sample.title || sample.description || 'Untitled'}
              </p>
            </div>
            <div className="flex items-center gap-1">
              <Badge variant="secondary" className="text-xs bg-primary/20 text-primary border-primary/30">
                {formatViewCount(sample.view_count)} views
              </Badge>
              <Button
                size="sm"
                variant="ghost"
                className="w-8 h-8"
                onClick={() => {
                  const platformUrl = sample.source === 'instagram' ? sample.instagram_url : sample.tiktok_url;
                  platformUrl && window.open(platformUrl, '_blank');
                }}
              >
                <ExternalLink className="w-4 h-4" />
              </Button>
              <Button
                size="sm"
                variant="ghost"
                className="w-8 h-8"
                onClick={() => onDownload(sample)}
              >
                <Download className="w-4 h-4" />
              </Button>
            </div>
          </div>

          {/* Progress Bar */}
          <div className="flex items-center gap-2 mb-3">
            <span className="text-xs text-muted-foreground min-w-[40px]">
              {formatTime(currentTime)}
            </span>
            <Slider
              value={[currentTime]}
              max={sample.duration_seconds || 0}
              step={0.1}
              onValueChange={handleSeek}
              className="flex-1"
            />
            <span className="text-xs text-muted-foreground min-w-[40px]">
              {formatTime(sample.duration_seconds || 0)}
            </span>
          </div>

          {/* Controls */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Button size="sm" variant="ghost" onClick={onPrevious}>
                <SkipBack className="w-4 h-4" />
              </Button>
              <Button size="sm" variant="default" onClick={onPlayPause} className="bg-primary hover:bg-primary/90">
                {isPlaying ? (
                  <Pause className="w-4 h-4" />
                ) : (
                  <Play className="w-4 h-4" />
                )}
              </Button>
              <Button size="sm" variant="ghost" onClick={onNext}>
                <SkipForward className="w-4 h-4" />
              </Button>
            </div>

            {/* Volume Control */}
            <div className="flex items-center gap-2 min-w-0 max-w-32">
              <Button
                size="sm"
                variant="ghost"
                onClick={() => setIsMuted(!isMuted)}
              >
                {isMuted ? (
                  <VolumeX className="w-4 h-4" />
                ) : (
                  <Volume2 className="w-4 h-4" />
                )}
              </Button>
              <Slider
                value={[isMuted ? 0 : volume]}
                max={1}
                step={0.1}
                onValueChange={(value) => {
                  setVolume(value[0]);
                  setIsMuted(false);
                }}
                className="flex-1"
              />
            </div>
          </div>
        </div>
      </Card>
    </>
  );
}