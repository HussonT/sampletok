import React, { useRef, useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Slider } from '@/components/ui/slider';
import {
  SkipBack,
  Play,
  Pause,
  SkipForward,
  Volume2,
  Repeat,
  Shuffle,
  Heart,
  Download,
  ExternalLink,
  Users
} from 'lucide-react';
import { Sample } from '@/types/api';

interface BottomPlayerProps {
  sample?: Sample | null;
  isPlaying?: boolean;
  onPlayPause?: () => void;
  onNext?: () => void;
  onPrevious?: () => void;
  onDownload?: (sample: Sample) => void;
}

export function BottomPlayer({
  sample,
  isPlaying = false,
  onPlayPause,
  onNext,
  onPrevious,
  onDownload
}: BottomPlayerProps) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const [currentTime, setCurrentTime] = useState(0);
  const [volume, setVolume] = useState(80);

  useEffect(() => {
    if (audioRef.current && sample) {
      if (isPlaying) {
        audioRef.current.play().catch(e => {
          console.error('Error playing audio:', e);
        });
      } else {
        audioRef.current.pause();
      }
    }
  }, [isPlaying, sample]);

  useEffect(() => {
    if (audioRef.current) {
      audioRef.current.volume = volume / 100;
    }
  }, [volume]);

  const handleTimeUpdate = () => {
    if (audioRef.current) {
      setCurrentTime(audioRef.current.currentTime);
    }
  };

  const handleSeek = (value: number[]) => {
    const time = (value[0] / 100) * (sample?.duration_seconds || 0);
    if (audioRef.current) {
      audioRef.current.currentTime = time;
      setCurrentTime(time);
    }
  };

  if (!sample) return null;

  const formatDuration = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const formatCount = (count: number): string => {
    if (count >= 1000000) {
      return `${(count / 1000000).toFixed(1)}M`;
    } else if (count >= 1000) {
      return `${(count / 1000).toFixed(1)}K`;
    }
    return count.toString();
  };

  const progressPercentage = sample?.duration_seconds ? (currentTime / sample.duration_seconds) * 100 : 0;

  return (
    <>
      {/* Hidden audio element */}
      {sample && (
        <audio
          ref={audioRef}
          src={sample.music_url || sample.audio_url_mp3 || sample.audio_url_wav}
          onTimeUpdate={handleTimeUpdate}
          onEnded={onNext}
        />
      )}
    <div className="fixed bottom-0 left-64 right-0 bg-card/95 backdrop-blur-sm border-t border-border z-50">
      <div className="flex items-center justify-between px-6 py-3">
        {/* Left - Song Info */}
        <div className="flex items-center gap-4 flex-1 min-w-0">
          <div className="w-12 h-12 bg-gradient-to-br from-primary/20 to-primary/40 rounded flex items-center justify-center flex-shrink-0">
            <span className="text-xs font-medium text-primary">
              {sample.id?.slice(0, 2).toUpperCase() || 'NA'}
            </span>
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-sm font-medium text-foreground truncate">
              {sample.description}
            </p>
            <div className="flex items-center gap-2">
              <p className="text-xs text-muted-foreground truncate">
                @{sample.creator_username || 'unknown'}
              </p>
              <div className="flex items-center gap-1 text-xs text-muted-foreground">
                <Users className="w-3 h-3" />
                <span>{formatCount(sample.view_count || 0)} views</span>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button 
              variant="ghost" 
              size="sm" 
              className="w-8 h-8 p-0"
              onClick={() => sample.tiktok_url && window.open(sample.tiktok_url, '_blank')}
            >
              <ExternalLink className="w-4 h-4" />
            </Button>
            <Button variant="ghost" size="sm" className="w-8 h-8 p-0">
              <Heart className="w-4 h-4" />
            </Button>
            <Button 
              variant="ghost" 
              size="sm" 
              className="w-8 h-8 p-0"
              onClick={() => onDownload?.(sample)}
            >
              <Download className="w-4 h-4" />
            </Button>
          </div>
        </div>

        {/* Center - Player Controls */}
        <div className="flex flex-col items-center gap-2 flex-1 max-w-md">
          <div className="flex items-center gap-4">
            <Button variant="ghost" size="sm" className="w-8 h-8 p-0">
              <Shuffle className="w-4 h-4" />
            </Button>
            <Button 
              variant="ghost" 
              size="sm" 
              className="w-8 h-8 p-0"
              onClick={onPrevious}
            >
              <SkipBack className="w-4 h-4" />
            </Button>
            <Button
              variant="default"
              size="sm"
              className="w-10 h-10 rounded-full bg-primary hover:bg-primary/90"
              onClick={onPlayPause}
            >
              {isPlaying ? (
                <Pause className="w-5 h-5" />
              ) : (
                <Play className="w-5 h-5" />
              )}
            </Button>
            <Button 
              variant="ghost" 
              size="sm" 
              className="w-8 h-8 p-0"
              onClick={onNext}
            >
              <SkipForward className="w-4 h-4" />
            </Button>
            <Button variant="ghost" size="sm" className="w-8 h-8 p-0">
              <Repeat className="w-4 h-4" />
            </Button>
          </div>
          
          {/* Progress Bar */}
          <div className="flex items-center gap-3 w-full">
            <span className="text-xs text-muted-foreground w-10">
              {formatDuration(currentTime)}
            </span>
            <Slider
              value={[progressPercentage]}
              max={100}
              step={1}
              className="flex-1"
              onValueChange={handleSeek}
            />
            <span className="text-xs text-muted-foreground w-10">
              {formatDuration(sample.duration_seconds || 0)}
            </span>
          </div>
        </div>

        {/* Right - Volume */}
        <div className="flex items-center gap-3 flex-1 justify-end">
          <Volume2 className="w-4 h-4 text-muted-foreground" />
          <Slider
            value={[volume]}
            max={100}
            step={1}
            className="w-24"
            onValueChange={(value) => setVolume(value[0])}
          />
        </div>
      </div>
    </div>
    </>
  );
}