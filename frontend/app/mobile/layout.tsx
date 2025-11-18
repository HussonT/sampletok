'use client';

import { useState, useCallback } from 'react';
import { MobileBottomNav } from '@/components/mobile/mobile-bottom-nav';
import { MobileMiniPlayer } from '@/components/mobile/mobile-mini-player';
import { QueryProvider } from '@/providers/query-provider';
import { Sample } from '@/types/api';
import { AudioPlayerContext } from '@/contexts/audio-player-context';
import { Toaster } from '@/components/ui/sonner';
import { OpenInBrowserBanner } from '@/components/mobile/open-in-browser-banner';

export default function MobileLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  // Audio player state
  const [currentSample, setCurrentSample] = useState<Sample | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [playbackQueue, setPlaybackQueue] = useState<Sample[]>([]);
  const [autoPlayNext, setAutoPlayNext] = useState(true); // Default to auto-play next

  // Audio player functions
  const playPreview = useCallback((sample: Sample) => {
    if (currentSample?.id === sample.id) {
      setIsPlaying(!isPlaying);
    } else {
      setCurrentSample(sample);
      setIsPlaying(true);
    }
  }, [currentSample, isPlaying]);

  const playNext = useCallback(() => {
    if (!currentSample || playbackQueue.length === 0) return;

    const currentIndex = playbackQueue.findIndex(s => s.id === currentSample.id);
    if (currentIndex >= 0 && currentIndex < playbackQueue.length - 1) {
      const nextSample = playbackQueue[currentIndex + 1];
      setCurrentSample(nextSample);
      setIsPlaying(true);
    }
  }, [currentSample, playbackQueue]);

  const playPrevious = useCallback(() => {
    if (!currentSample || playbackQueue.length === 0) return;

    const currentIndex = playbackQueue.findIndex(s => s.id === currentSample.id);
    if (currentIndex > 0) {
      const previousSample = playbackQueue[currentIndex - 1];
      setCurrentSample(previousSample);
      setIsPlaying(true);
    }
  }, [currentSample, playbackQueue]);

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
          playbackQueue,
          autoPlayNext,
          setCurrentSample,
          setIsPlaying,
          setPlaybackQueue,
          setAutoPlayNext,
          playPreview,
          playNext,
          playPrevious,
        }}
      >
        <div className="min-h-screen bg-background">
          {/* TikTok browser banner - shows at top when in TikTok app */}
          <OpenInBrowserBanner />

          {/* Full-screen mobile content */}
          <main className={currentSample ? 'pb-32' : 'pb-20'}>{children}</main>

          {/* Mini player (shown when playing) */}
          {currentSample && (
            <MobileMiniPlayer
              sample={currentSample}
              isPlaying={isPlaying}
              onPlayPause={handlePlayPause}
              onClose={handleClosePlayer}
              onNext={playbackQueue.length > 0 ? playNext : undefined}
              onPrevious={playbackQueue.length > 0 ? playPrevious : undefined}
              autoPlayNext={autoPlayNext}
            />
          )}

          {/* Fixed bottom navigation */}
          <MobileBottomNav />

          {/* Mobile toast notifications - positioned at top */}
          <Toaster position="top-center" />
        </div>
      </AudioPlayerContext.Provider>
    </QueryProvider>
  );
}
