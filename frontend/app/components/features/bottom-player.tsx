import React from 'react';
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
import { Sample } from '@/data/mock-samples';

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
  if (!sample) return null;

  const formatDuration = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const formatFollowerCount = (count: number): string => {
    if (count >= 1000000) {
      return `${(count / 1000000).toFixed(1)}M`;
    } else if (count >= 1000) {
      return `${(count / 1000).toFixed(1)}K`;
    }
    return count.toString();
  };

  return (
    <div className="fixed bottom-0 left-64 right-0 bg-card/95 backdrop-blur-sm border-t border-border z-50">
      <div className="flex items-center justify-between px-6 py-3">
        {/* Left - Song Info */}
        <div className="flex items-center gap-4 flex-1 min-w-0">
          <div className="w-12 h-12 bg-gradient-to-br from-primary/20 to-primary/40 rounded flex items-center justify-center flex-shrink-0">
            <span className="text-xs font-medium text-primary">
              {sample.id.slice(0, 2).toUpperCase()}
            </span>
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-sm font-medium text-foreground truncate">
              {sample.description}
            </p>
            <div className="flex items-center gap-2">
              <p className="text-xs text-muted-foreground truncate">
                @{sample.creatorUsername}
              </p>
              <div className="flex items-center gap-1 text-xs text-muted-foreground">
                <Users className="w-3 h-3" />
                <span>{formatFollowerCount(sample.followerCount)}</span>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button 
              variant="ghost" 
              size="sm" 
              className="w-8 h-8 p-0"
              onClick={() => window.open(sample.tiktokUrl, '_blank')}
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
            <span className="text-xs text-muted-foreground w-10">0:00</span>
            <Slider
              value={[0]}
              max={100}
              step={1}
              className="flex-1"
            />
            <span className="text-xs text-muted-foreground w-10">
              {formatDuration(sample.duration)}
            </span>
          </div>
        </div>

        {/* Right - Volume */}
        <div className="flex items-center gap-3 flex-1 justify-end">
          <Volume2 className="w-4 h-4 text-muted-foreground" />
          <Slider
            value={[80]}
            max={100}
            step={1}
            className="w-24"
          />
        </div>
      </div>
    </div>
  );
}