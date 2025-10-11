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

interface Sample {
  id: string;
  tiktokUrl: string;
  creatorUsername: string;
  creatorAvatarUrl?: string;
  viewCount: number;
  description: string;
  duration: number;
  audioUrl: string;
  waveformUrl: string;
  createdAt: string;
}

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

  useEffect(() => {
    if (audioRef.current) {
      if (isPlaying) {
        audioRef.current.play();
      } else {
        audioRef.current.pause();
      }
    }
  }, [isPlaying, sample]);

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
      {/* Hidden audio element */}
      <audio
        ref={audioRef}
        src={sample.audioUrl}
        onTimeUpdate={handleTimeUpdate}
        onEnded={() => onNext()}
      />

      {/* Floating Player */}
      <Card className="fixed bottom-4 left-4 right-4 z-30 bg-card/95 backdrop-blur-sm border border-border shadow-2xl shadow-primary/20">
        <div className="p-4">
          {/* Sample Info */}
          <div className="flex items-center gap-4 mb-3">
            <Avatar className="w-12 h-12 shrink-0">
              <AvatarImage src={sample.creatorAvatarUrl} alt={sample.creatorUsername} />
              <AvatarFallback>
                {sample.creatorUsername.substring(0, 2).toUpperCase()}
              </AvatarFallback>
            </Avatar>
            <div className="flex-1 min-w-0">
              <p className="truncate font-medium text-foreground">@{sample.creatorUsername}</p>
              <p className="text-xs text-muted-foreground truncate">
                {sample.description}
              </p>
            </div>
            <div className="flex items-center gap-1">
              <Badge variant="secondary" className="text-xs bg-primary/20 text-primary border-primary/30">
                {formatViewCount(sample.viewCount)} views
              </Badge>
              <Button
                size="sm"
                variant="ghost"
                className="w-8 h-8"
                onClick={() => window.open(sample.tiktokUrl, '_blank')}
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
              max={sample.duration}
              step={0.1}
              onValueChange={handleSeek}
              className="flex-1"
            />
            <span className="text-xs text-muted-foreground min-w-[40px]">
              {formatTime(sample.duration)}
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