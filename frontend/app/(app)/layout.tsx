'use client';

import { usePathname } from 'next/navigation';
import { AppSidebar } from '@/components/features/app-sidebar';
import { useEffect, useState, useRef, useCallback, createContext, useContext } from 'react';
import { ProcessingContext } from '@/contexts/processing-context';
import { BottomPlayer } from '@/components/features/bottom-player';
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
    throw new Error('useAudioPlayer must be used within AppLayout');
  }
  return context;
}

export default function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const [activeSection, setActiveSection] = useState('explore');
  const processingHandlerRef = useRef<((taskId: string, url: string) => void) | null>(null);

  // Audio player state
  const [currentSample, setCurrentSample] = useState<Sample | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);

  // Update active section based on pathname
  useEffect(() => {
    if (pathname === '/') {
      setActiveSection('explore');
    } else if (pathname?.includes('/my-downloads')) {
      setActiveSection('downloads');
    } else if (pathname?.includes('/my-favorites')) {
      setActiveSection('favorites');
    } else if (pathname?.includes('/tiktok-connect')) {
      setActiveSection('tiktok-connect');
    }
  }, [pathname]);

  const registerProcessingHandler = useCallback((handler: (taskId: string, url: string) => void) => {
    processingHandlerRef.current = handler;
  }, []);

  const unregisterProcessingHandler = useCallback(() => {
    processingHandlerRef.current = null;
  }, []);

  const handleProcessingStarted = useCallback((taskId: string, url: string) => {
    if (processingHandlerRef.current) {
      processingHandlerRef.current(taskId, url);
    }
  }, []);

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

  const handleNext = useCallback(() => {
    // TODO: Implement next sample logic if needed
  }, []);

  const handlePrevious = useCallback(() => {
    // TODO: Implement previous sample logic if needed
  }, []);

  const handleDownload = useCallback((sample: Sample) => {
    // TODO: Implement download logic if needed
  }, []);

  const audioPlayerValue: AudioPlayerContextType = {
    currentSample,
    isPlaying,
    setCurrentSample,
    setIsPlaying,
    playPreview,
  };

  return (
    <ProcessingContext.Provider value={{ registerProcessingHandler, unregisterProcessingHandler }}>
      <AudioPlayerContext.Provider value={audioPlayerValue}>
        <div className="flex h-screen w-screen overflow-hidden">
          {/* Sidebar - Fixed width */}
          <div className="w-64 flex-shrink-0 border-r border-border bg-sidebar">
            <AppSidebar
              activeSection={activeSection}
              onSectionChange={setActiveSection}
              onProcessingStarted={handleProcessingStarted}
            />
          </div>

          {/* Main Content - Takes remaining space */}
          <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
            {children}
          </div>

          {/* Bottom Player - Persists across all pages */}
          <BottomPlayer
            sample={currentSample}
            isPlaying={isPlaying}
            onPlayPause={handlePlayPause}
            onNext={handleNext}
            onPrevious={handlePrevious}
            onDownload={handleDownload}
          />
        </div>
      </AudioPlayerContext.Provider>
    </ProcessingContext.Provider>
  );
}
