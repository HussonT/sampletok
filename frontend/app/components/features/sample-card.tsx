import React, { useState, useRef } from 'react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Play, Pause, Download, Heart } from 'lucide-react';
import { Sample } from '@/types/api';

interface SampleCardProps {
  sample: Sample;
  onPreview: (sample: Sample) => void;
  onDownload: (sample: Sample) => void;
  isPlaying: boolean;
}

export function SampleCard({ sample, onPreview, onDownload, isPlaying }: SampleCardProps) {
  const [isHovered, setIsHovered] = useState(false);
  const [isFavorited, setIsFavorited] = useState(false);

  const formatViewCount = (count: number) => {
    if (count >= 1000000) return `${(count / 1000000).toFixed(1)}M`;
    if (count >= 1000) return `${(count / 1000).toFixed(1)}K`;
    return count.toString();
  };

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <Card 
      className="group relative overflow-hidden border border-border/30 hover:border-primary/50 hover:shadow-lg hover:shadow-primary/20 transition-all duration-200 cursor-pointer bg-card"
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      onClick={() => onPreview(sample)}
    >
      {/* Waveform Background */}
      <div className="aspect-[4/3] bg-muted/50 relative overflow-hidden">
        {/* Mock waveform visualization */}
        <div className="absolute inset-0 flex items-center justify-center p-4">
          <svg
            viewBox="0 0 200 60"
            className="w-full h-full opacity-60"
          >
            {Array.from({ length: 50 }, (_, i) => {
              // Use deterministic pattern instead of Math.random() to avoid hydration mismatch
              const height = (Math.sin(i * 0.5) * 15 + 25);
              const y = (60 - height) / 2;
              return (
                <rect
                  key={i}
                  x={i * 4}
                  y={y}
                  width="2"
                  height={height}
                  fill="currentColor"
                  className="text-primary/60"
                />
              );
            })}
          </svg>
        </div>

        {/* Play/Pause Overlay */}
        <div 
          className={`absolute inset-0 flex items-center justify-center bg-black/40 transition-opacity duration-200 ${
            isHovered || isPlaying ? 'opacity-100' : 'opacity-0'
          }`}
        >
          <Button
            size="sm"
            variant="default"
            className="rounded-full w-12 h-12 bg-primary hover:bg-primary/90 shadow-lg"
          >
            {isPlaying ? (
              <Pause className="w-5 h-5" />
            ) : (
              <Play className="w-5 h-5" />
            )}
          </Button>
        </div>

        {/* Favorite Button */}
        <Button
          size="sm"
          variant="ghost"
          className={`absolute top-2 right-2 w-8 h-8 rounded-full transition-opacity duration-200 ${
            isHovered ? 'opacity-100' : 'opacity-0'
          }`}
          onClick={(e) => {
            e.stopPropagation();
            setIsFavorited(!isFavorited);
          }}
        >
          <Heart 
            className={`w-4 h-4 ${isFavorited ? 'fill-red-500 text-red-500' : 'text-white'}`} 
          />
        </Button>
      </div>

      {/* Sample Info */}
      <div className="p-3 space-y-2">
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1 min-w-0">
            <p className="truncate font-medium text-foreground">@{sample.creator_username}</p>
            <p className="text-xs text-muted-foreground truncate">
              {sample.title || sample.description || 'Untitled'}
            </p>
          </div>
          <Badge variant="secondary" className="shrink-0 bg-primary/20 text-primary border-primary/30">
            {formatDuration(sample.duration_seconds || 0)}
          </Badge>
        </div>

        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <span>{formatViewCount(sample.view_count)} views</span>
            <span>•</span>
            <span>{new Date(sample.created_at).toLocaleDateString()}</span>
          </div>
          <Button
            size="sm"
            variant="ghost"
            className="w-8 h-8"
            onClick={(e) => {
              e.stopPropagation();
              onDownload(sample);
            }}
          >
            <Download className="w-4 h-4" />
          </Button>
        </div>
      </div>
    </Card>
  );
}