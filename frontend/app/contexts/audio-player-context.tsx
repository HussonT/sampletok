'use client';

import { createContext, useContext } from 'react';
import { Sample } from '@/types/api';

// Audio player context
export interface AudioPlayerContextType {
  currentSample: Sample | null;
  isPlaying: boolean;
  playbackQueue: Sample[];
  autoPlayNext: boolean;
  setCurrentSample: (sample: Sample | null) => void;
  setIsPlaying: (playing: boolean) => void;
  setPlaybackQueue: (queue: Sample[]) => void;
  setAutoPlayNext: (enabled: boolean) => void;
  playPreview: (sample: Sample) => void;
  playNext: () => void;
  playPrevious: () => void;
}

export const AudioPlayerContext = createContext<AudioPlayerContextType | undefined>(undefined);

export function useMobileAudioPlayer() {
  const context = useContext(AudioPlayerContext);
  if (!context) {
    throw new Error('useMobileAudioPlayer must be used within MobileLayout');
  }
  return context;
}
