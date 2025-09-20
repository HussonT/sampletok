import React from 'react';
import { SampleCard } from './sample-card';

interface Sample {
  id: string;
  tiktokUrl: string;
  creatorUsername: string;
  viewCount: number;
  description: string;
  duration: number;
  audioUrl: string;
  waveformUrl: string;
  createdAt: string;
}

interface SampleGridProps {
  samples: Sample[];
  currentSample: Sample | null;
  isPlaying: boolean;
  onSamplePreview: (sample: Sample) => void;
  onSampleDownload: (sample: Sample) => void;
}

export function SampleGrid({ 
  samples, 
  currentSample, 
  isPlaying, 
  onSamplePreview, 
  onSampleDownload 
}: SampleGridProps) {
  if (samples.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-96 text-center space-y-4">
        <div className="w-24 h-24 rounded-full bg-primary/20 flex items-center justify-center">
          <svg 
            viewBox="0 0 24 24" 
            className="w-12 h-12 text-primary"
            fill="none"
            stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
          </svg>
        </div>
        <div>
          <h3 className="mb-2 text-foreground font-semibold">No samples found</h3>
          <p className="text-muted-foreground max-w-md">
            Try adjusting your filters or add some TikTok videos to get started with your sample library.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 gap-4">
      {samples.map((sample) => (
        <SampleCard
          key={sample.id}
          sample={sample}
          onPreview={onSamplePreview}
          onDownload={onSampleDownload}
          isPlaying={isPlaying && currentSample?.id === sample.id}
        />
      ))}
    </div>
  );
}