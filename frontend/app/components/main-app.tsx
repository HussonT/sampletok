'use client';

import React, { useState, useMemo, useTransition, useOptimistic, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@clerk/nextjs';
import { SoundsTable } from '@/components/features/sounds-table';
import { SamplesPagination } from '@/components/features/samples-pagination';
import { ProcessingQueue, ProcessingTask } from '@/components/features/processing-queue';
import { BottomPlayer } from '@/components/features/bottom-player';
import { Download, Music } from 'lucide-react';
import { Sample, SampleFilters, ProcessingStatus } from '@/types/api';
import { processTikTokUrl, deleteSample, getProcessingStatus } from '@/actions/samples';
import { toast } from 'sonner';
import { useProcessing } from '@/contexts/processing-context';
import { TableLoadingSkeleton, LoadingBar } from '@/components/ui/loading-skeletons';

interface MainAppProps {
  initialSamples: Sample[];
  totalSamples: number;
  currentFilters: SampleFilters;
}

export default function MainApp({ initialSamples, totalSamples, currentFilters }: MainAppProps) {
  const router = useRouter();
  const { getToken } = useAuth();
  const { registerProcessingHandler, unregisterProcessingHandler } = useProcessing();
  const [isPending, startTransition] = useTransition();
  const [samples, setSamples] = useState<Sample[]>(initialSamples);
  const [currentSample, setCurrentSample] = useState<Sample | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [activeSection, setActiveSection] = useState('explore');
  const [downloadedSamples, setDownloadedSamples] = useState<Set<string>>(new Set());
  const [downloadedVideos, setDownloadedVideos] = useState<Set<string>>(new Set());
  const [credits, setCredits] = useState(10);
  const [processingTasks, setProcessingTasks] = useState<Map<string, ProcessingTask>>(new Map());
  const [currentPage, setCurrentPage] = useState(1);
  const [isLoadingPage, setIsLoadingPage] = useState(false);
  const itemsPerPage = 20;

  // Update samples when initialSamples changes (from server refresh)
  useEffect(() => {
    setSamples(initialSamples);
    setCurrentPage(1); // Reset to page 1 when initial data changes
  }, [initialSamples]);

  // Preload videos for current samples
  useEffect(() => {
    samples.forEach((sample) => {
      if (sample.video_url) {
        // Preload video in background
        const link = document.createElement('link');
        link.rel = 'prefetch';
        link.as = 'video';
        link.href = sample.video_url;
        document.head.appendChild(link);
      }
    });
  }, [samples]);

  // Handle page change
  const handlePageChange = useCallback(async (page: number) => {
    if (isLoadingPage) return;

    setIsLoadingPage(true);
    setCurrentPage(page);

    try {
      const params = new URLSearchParams();
      params.append('skip', ((page - 1) * itemsPerPage).toString());
      params.append('limit', itemsPerPage.toString());

      // Get auth token for authenticated requests
      const token = await getToken();
      const headers: HeadersInit = {
        'Content-Type': 'application/json',
      };
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(`${backendUrl}/api/v1/samples?${params.toString()}`, { headers });
      if (!response.ok) throw new Error('Failed to load page');

      const data = await response.json();
      setSamples(data.items);

      // Scroll to top of content area
      window.scrollTo({ top: 0, behavior: 'smooth' });
    } catch (error) {
      console.error('Failed to load page:', error);
      toast.error('Failed to load page');
    } finally {
      setIsLoadingPage(false);
    }
  }, [isLoadingPage, itemsPerPage, getToken]);

  // Add a new processing task
  const addProcessingTask = useCallback((taskId: string, url: string) => {
    const newTask: ProcessingTask = {
      taskId,
      url,
      status: ProcessingStatus.PENDING,
      message: 'Queued for processing...',
      progress: 0
    };
    setProcessingTasks(prev => new Map(prev).set(taskId, newTask));
  }, []);

  // Update processing task status
  const updateProcessingTask = useCallback((taskId: string, updates: Partial<ProcessingTask>) => {
    setProcessingTasks(prev => {
      const newMap = new Map(prev);
      const existing = newMap.get(taskId);
      if (existing) {
        newMap.set(taskId, { ...existing, ...updates });
      }
      return newMap;
    });
  }, []);

  // Remove processing task
  const removeProcessingTask = useCallback((taskId: string) => {
    setProcessingTasks(prev => {
      const newMap = new Map(prev);
      newMap.delete(taskId);
      return newMap;
    });
  }, []);

  // Register processing handler with layout so sidebar can trigger it
  useEffect(() => {
    registerProcessingHandler(addProcessingTask);
    return () => unregisterProcessingHandler();
  }, [addProcessingTask, registerProcessingHandler, unregisterProcessingHandler]);

  // Poll for processing status
  useEffect(() => {
    if (processingTasks.size === 0) return;

    const pollStatus = async () => {
      const currentTasks = Array.from(processingTasks.entries());

      for (const [taskId, task] of currentTasks) {
        // Only poll if still processing
        if (task.status === ProcessingStatus.PENDING || task.status === ProcessingStatus.PROCESSING) {
          try {
            const statusData = await getProcessingStatus(taskId);

            if (statusData) {
              updateProcessingTask(taskId, {
                status: statusData.status,
                message: statusData.message,
                progress: statusData.progress
              });

              // If completed, immediately refresh to show the new sample
              if (statusData.status === ProcessingStatus.COMPLETED) {
                // Aggressive refresh: Call router.refresh multiple times if needed
                router.refresh();

                // Also manually trigger a re-fetch after a short delay
                setTimeout(() => {
                  router.refresh();
                }, 500);

                // Remove task after showing success
                setTimeout(() => {
                  removeProcessingTask(taskId);
                }, 3000); // Show success for 3 seconds
              } else if (statusData.status === ProcessingStatus.FAILED) {
                // Show error for longer
                setTimeout(() => {
                  removeProcessingTask(taskId);
                }, 5000);
              }
            }
          } catch (error) {
            console.error('Failed to poll status for task', taskId, error);
          }
        }
      }
    };

    // Initial poll
    pollStatus();

    // Set up interval
    const interval = setInterval(pollStatus, 2000); // Poll every 2 seconds

    return () => clearInterval(interval);
  }, [processingTasks, updateProcessingTask, removeProcessingTask, router]);

  const filteredSamples = useMemo(() => {
    // Just return samples sorted by most recent
    return [...samples].sort((a, b) =>
      new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    );
  }, [samples]);

  const handleSamplePreview = (sample: Sample) => {
    if (currentSample?.id === sample.id) {
      setIsPlaying(!isPlaying);
    } else {
      setCurrentSample(sample);
      setIsPlaying(true);
    }
  };

  const handleSampleDownload = (sample: Sample) => {
    if (downloadedSamples.has(sample.id)) {
      toast.success('Download started!', {
        description: `Downloading ${sample.creator_username} sample as WAV`,
      });
    } else {
      if (credits <= 0) {
        toast.error('No credits remaining', {
          description: 'Purchase more credits to download samples',
        });
        return;
      }

      setCredits(prev => prev - 1);
      setDownloadedSamples(prev => new Set([...prev, sample.id]));

      toast.success('Sample purchased!', {
        description: `Used 1 credit. ${credits - 1} credits remaining`,
      });
    }
  };

  const handleVideoDownload = (sample: Sample) => {
    if (downloadedVideos.has(sample.id)) {
      toast.success('Download started!', {
        description: `Downloading ${sample.creator_username} video`,
      });
    } else {
      if (credits <= 0) {
        toast.error('No credits remaining', {
          description: 'Purchase more credits to download videos',
        });
        return;
      }

      setCredits(prev => prev - 1);
      setDownloadedVideos(prev => new Set([...prev, sample.id]));

      toast.success('Video purchased!', {
        description: `Used 1 credit. ${credits - 1} credits remaining`,
      });
    }
  };


  const handlePlayerPlayPause = () => {
    setIsPlaying(!isPlaying);
  };

  const handlePlayerNext = () => {
    if (!currentSample) return;
    const currentIndex = filteredSamples.findIndex(s => s.id === currentSample.id);
    const nextIndex = (currentIndex + 1) % filteredSamples.length;
    const nextSample = filteredSamples[nextIndex];
    setCurrentSample(nextSample);
    setIsPlaying(false);
  };

  const handlePlayerPrevious = () => {
    if (!currentSample) return;
    const currentIndex = filteredSamples.findIndex(s => s.id === currentSample.id);
    const prevIndex = currentIndex === 0 ? filteredSamples.length - 1 : currentIndex - 1;
    const prevSample = filteredSamples[prevIndex];
    setCurrentSample(prevSample);
    setIsPlaying(true);
  };

  // Spacebar play/pause
  useEffect(() => {
    const handleKeyPress = (e: KeyboardEvent) => {
      if (e.code === 'Space' && currentSample) {
        // Prevent spacebar from scrolling the page
        e.preventDefault();
        setIsPlaying(prev => !prev);
      }
    };

    window.addEventListener('keydown', handleKeyPress);
    return () => window.removeEventListener('keydown', handleKeyPress);
  }, [currentSample]);

  return (
    <>
      {/* Header */}
      <div className="flex-none border-b px-6 h-16 flex items-center justify-between">
        <div className="flex items-center gap-2">
          {activeSection === 'explore' ? (
            <Music className="w-5 h-5" />
          ) : (
            <Download className="w-5 h-5" />
          )}
          <h1 className="text-xl font-semibold">
            {activeSection === 'explore' ? 'Explore' : 'My Downloads'}
          </h1>
        </div>
        <div className="flex items-center gap-4">
          <div className="text-sm text-muted-foreground">
            {credits} credits
          </div>
        </div>
      </div>

      {/* Loading bar */}
      {isLoadingPage && <LoadingBar />}

      {/* Processing Queue */}
      <ProcessingQueue
        tasks={Array.from(processingTasks.values())}
        onRemoveTask={removeProcessingTask}
      />

      {/* Content */}
      <div className="flex-1 overflow-auto px-6 pb-6" style={{ paddingBottom: currentSample ? '160px' : '24px' }}>
          {activeSection === 'explore' && (
            <>
              {isLoadingPage ? (
                <TableLoadingSkeleton rows={8} />
              ) : (
                <>
                  <SoundsTable
                    samples={filteredSamples}
                    currentSample={currentSample}
                    isPlaying={isPlaying}
                    downloadedSamples={downloadedSamples}
                    downloadedVideos={downloadedVideos}
                    onSamplePreview={handleSamplePreview}
                    onSampleDownload={handleSampleDownload}
                    onVideoDownload={handleVideoDownload}
                  />
                  <SamplesPagination
                    currentPage={currentPage}
                    totalPages={Math.ceil(totalSamples / itemsPerPage)}
                    onPageChange={handlePageChange}
                  />
                </>
              )}
            </>
          )}

          {activeSection === 'library' && (
            downloadedSamples.size === 0 ? (
              <div className="flex items-center justify-center h-96">
                <div className="text-center">
                  <Download className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
                  <h3 className="text-lg font-medium mb-2">No Downloads Yet</h3>
                  <p className="text-muted-foreground">
                    Your downloaded samples will appear here
                  </p>
                </div>
              </div>
            ) : (
              <SoundsTable
                samples={samples.filter(sample => downloadedSamples.has(sample.id))}
                currentSample={currentSample}
                isPlaying={isPlaying}
                downloadedSamples={downloadedSamples}
                downloadedVideos={downloadedVideos}
                onSamplePreview={handleSamplePreview}
                onSampleDownload={handleSampleDownload}
                onVideoDownload={handleVideoDownload}
              />
            )
          )}
        </div>

      {/* Bottom Player */}
      <BottomPlayer
        sample={currentSample}
        isPlaying={isPlaying}
        onPlayPause={handlePlayerPlayPause}
        onNext={handlePlayerNext}
        onPrevious={handlePlayerPrevious}
        onDownload={handleSampleDownload}
      />
    </>
  );
}