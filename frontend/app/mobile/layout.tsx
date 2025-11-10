'use client';

import { useState, useCallback, createContext, useContext } from 'react';
import { MobileBottomNav } from '@/components/mobile/mobile-bottom-nav';
import { MobileMiniPlayer } from '@/components/mobile/mobile-mini-player';
import { QueryProvider } from '@/providers/query-provider';
import { Sample } from '@/types/api';

// Audio player context
interface AudioPlayerContextType {
  currentSample: Sample | null;
  isPlaying: boolean;
  setCurrentSample: (sample: Sample | null) => void;
  setIsPlaying: (playing: boolean) => void;
  playPreview: (sample: Sample) => void;
}

const AudioPlayerContext = createContext<AudioPlayerContextType | undefined>(undefined);

export function useAudioPlayer() {
  const context = useContext(AudioPlayerContext);
  if (!context) {
    throw new Error('useAudioPlayer must be used within MobileLayout');
  }
  return context;
}

export default function MobileLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  // Audio player state
  const [currentSample, setCurrentSample] = useState<Sample | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);

  // Audio player functions
  const playPreview = useCallback((sample: Sample) => {
    if (currentSample?.id === sample.id) {
      setIsPlaying(!isPlaying);
    } else {
      setCurrentSample(sample);
      setIsPlaying(true);
    }
  }, [currentSample, isPlaying]);

  const handlePlayPause = useCallback(() => {
    setIsPlaying(!isPlaying);
  }, [isPlaying]);

  const handleClosePlayer = useCallback(() => {
    setIsPlaying(false);
    setCurrentSample(null);
  }, []);

  return (
    <QueryProvider>
      <AudioPlayerContext.Provider
        value={{
          currentSample,
          isPlaying,
          setCurrentSample,
          setIsPlaying,
          playPreview,
        }}
      >
        <div className="min-h-screen bg-background">
          {/* Full-screen mobile content */}
          <main className={currentSample ? 'pb-32' : 'pb-20'}>{children}</main>

          {/* Mini player (shown when playing) */}
          {currentSample && (
            <MobileMiniPlayer
              sample={currentSample}
              isPlaying={isPlaying}
              onPlayPause={handlePlayPause}
              onClose={handleClosePlayer}
            />
          )}

          {/* Fixed bottom navigation */}
          <MobileBottomNav />
        </div>
      </AudioPlayerContext.Provider>
    </QueryProvider>
  );
}
