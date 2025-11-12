'use client';

import { createContext, useContext } from 'react';
import { Sample } from '@/types/api';

// Audio player context for desktop app
export interface DesktopAudioPlayerContextType {
  currentSample: Sample | null;
  isPlaying: boolean;
  setCurrentSample: (sample: Sample | null) => void;
  setIsPlaying: (playing: boolean) => void;
  playPreview: (sample: Sample) => void;
}

export const DesktopAudioPlayerContext = createContext<DesktopAudioPlayerContextType | undefined>(undefined);

export function useDesktopAudioPlayer() {
  const context = useContext(DesktopAudioPlayerContext);
  if (!context) {
    throw new Error('useDesktopAudioPlayer must be used within AppLayout');
  }
  return context;
}
