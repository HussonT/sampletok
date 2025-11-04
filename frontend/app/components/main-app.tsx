'use client';

import React, { useState, useMemo, useTransition, useOptimistic, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@clerk/nextjs';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { SoundsTable } from '@/components/features/sounds-table';
import { SamplesPagination } from '@/components/features/samples-pagination';
import { ProcessingQueue, ProcessingTask } from '@/components/features/processing-queue';
import { BottomPlayer } from '@/components/features/bottom-player';
import { Download, Music, Coins, Search, X } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Sample, SampleFilters, ProcessingStatus, PaginatedResponse } from '@/types/api';
import { processTikTokUrl, deleteSample, getProcessingStatus } from '@/actions/samples';
import { toast } from 'sonner';
import { useProcessing } from '@/contexts/processing-context';
import { TableLoadingSkeleton, LoadingBar } from '@/components/ui/loading-skeletons';
import { createAuthenticatedClient } from '@/lib/api-client';
import Link from 'next/link';

interface MainAppProps {
  initialSamples: Sample[];
  totalSamples: number;
  currentFilters: SampleFilters;
}

export default function MainApp({ initialSamples, totalSamples, currentFilters }: MainAppProps) {
  const router = useRouter();
  const { getToken } = useAuth();
  const queryClient = useQueryClient();
  const { registerProcessingHandler, unregisterProcessingHandler } = useProcessing();
  const [isPending, startTransition] = useTransition();
  const [currentSample, setCurrentSample] = useState<Sample | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [activeSection, setActiveSection] = useState('explore');
  const [downloadedSamples, setDownloadedSamples] = useState<Set<string>>(new Set());
  const [downloadedVideos, setDownloadedVideos] = useState<Set<string>>(new Set());
  const [processingTasks, setProcessingTasks] = useState<Map<string, ProcessingTask>>(new Map());
  const [currentPage, setCurrentPage] = useState(1);
  const [creditBalance, setCreditBalance] = useState<number | null>(null);
  const [hasSubscription, setHasSubscription] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const itemsPerPage = 20;

  // Fetch samples with useQuery
  const { data, isLoading: isLoadingPage } = useQuery({
    queryKey: ['samples', currentPage, searchQuery],
    queryFn: async () => {
      const apiClient = createAuthenticatedClient(getToken);
      const params: any = {
        skip: (currentPage - 1) * itemsPerPage,
        limit: itemsPerPage,
        sort_by: 'created_at_desc'
      };
      if (searchQuery) {
        params.search = searchQuery;
      }
      const data = await apiClient.get<PaginatedResponse<Sample>>('/samples/', params);
      return data;
    },
    initialData: currentPage === 1 ? {
      items: initialSamples,
      total: totalSamples,
      skip: 0,
      limit: itemsPerPage,
      has_more: totalSamples > itemsPerPage,
    } : undefined,
    staleTime: 30 * 1000, // Consider data fresh for 30 seconds
  });

  const samples = data?.items || initialSamples;

  // Prefetch next page for instant navigation
  useEffect(() => {
    const totalPages = Math.ceil((data?.total || totalSamples) / itemsPerPage);
    const nextPage = currentPage + 1;

    // Only prefetch if there's a next page
    if (nextPage <= totalPages) {
      queryClient.prefetchQuery({
        queryKey: ['samples', nextPage],
        queryFn: async () => {
          const apiClient = createAuthenticatedClient(getToken);
          const data = await apiClient.get<PaginatedResponse<Sample>>('/samples/', {
            skip: (nextPage - 1) * itemsPerPage,
            limit: itemsPerPage,
            sort_by: 'recent'
          });
          return data;
        },
        staleTime: 30 * 1000,
      });
    }
  }, [currentPage, queryClient, getToken, itemsPerPage, data?.total, totalSamples]);

  // Fetch credit balance
  useEffect(() => {
    const fetchCredits = async () => {
      try {
        const token = await getToken();
        if (!token) return;

        const api = createAuthenticatedClient(async () => token);
        const data = await api.get<{
          credits: number;
          has_subscription: boolean;
          subscription_tier: string | null;
          monthly_credits: number | null;
        }>('/credits/balance');

        setCreditBalance(data.credits);
        setHasSubscription(data.has_subscription);
      } catch (err) {
        console.error('Failed to fetch credit balance:', err);
      }
    };

    fetchCredits();
    // Refresh credits every 30 seconds
    const interval = setInterval(fetchCredits, 30000);
    return () => clearInterval(interval);
  }, [getToken]);

  // REMOVED: Aggressive prefetching of all samples
  // We now use smart prefetching: only next/previous when a sample is playing
  // This reduces bandwidth from ~24MB to ~2.4MB on page load

  // Compute filtered samples (sorted by most recent)
  const filteredSamples = useMemo(() => {
    return [...samples].sort((a, b) =>
      new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    );
  }, [samples]);

  // Smart preload: High-priority preload of next/previous samples when a sample is selected
  // Changed from 'prefetch' to 'preload' for higher browser priority
  useEffect(() => {
    if (!currentSample) return;

    const currentIndex = filteredSamples.findIndex(s => s.id === currentSample.id);
    if (currentIndex === -1) return;

    // Preload next sample with high priority
    const nextIndex = (currentIndex + 1) % filteredSamples.length;
    const nextSample = filteredSamples[nextIndex];
    if (nextSample) {
      const nextAudioUrl = nextSample.audio_url_mp3 || nextSample.audio_url_wav;
      if (nextAudioUrl) {
        const nextLink = document.createElement('link');
        nextLink.rel = 'preload';  // High priority
        nextLink.as = 'audio';
        nextLink.href = nextAudioUrl;
        nextLink.id = `preload-next-${nextSample.id}`;
        document.head.appendChild(nextLink);
      }
    }

    // Preload previous sample with high priority
    const prevIndex = currentIndex === 0 ? filteredSamples.length - 1 : currentIndex - 1;
    const prevSample = filteredSamples[prevIndex];
    if (prevSample) {
      const prevAudioUrl = prevSample.audio_url_mp3 || prevSample.audio_url_wav;
      if (prevAudioUrl) {
        const prevLink = document.createElement('link');
        prevLink.rel = 'preload';  // High priority
        prevLink.as = 'audio';
        prevLink.href = prevAudioUrl;
        prevLink.id = `preload-prev-${prevSample.id}`;
        document.head.appendChild(prevLink);
      }
    }

    // Cleanup function to remove old preload links when sample changes
    return () => {
      const oldNextLink = document.getElementById(`preload-next-${nextSample?.id}`);
      const oldPrevLink = document.getElementById(`preload-prev-${prevSample?.id}`);
      if (oldNextLink) oldNextLink.remove();
      if (oldPrevLink) oldPrevLink.remove();
    };
  }, [currentSample, filteredSamples]);

  // Handle page change - useQuery will automatically fetch the data
  const handlePageChange = useCallback((page: number) => {
    if (isLoadingPage) return;

    setCurrentPage(page);

    // Scroll to top of content area
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }, [isLoadingPage]);

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

  const handleSamplePreview = (sample: Sample) => {
    if (currentSample?.id === sample.id) {
      setIsPlaying(!isPlaying);
    } else {
      setCurrentSample(sample);
      setIsPlaying(true);
    }
  };

  const handleSampleDownload = (sample: Sample) => {
    // Mark as downloaded locally (actual download handled by SoundsTable)
    setDownloadedSamples(prev => new Set([...prev, sample.id]));

    toast.success('Download started!', {
      description: `Downloading ${sample.creator_username} sample`,
    });
  };

  const handleVideoDownload = (sample: Sample) => {
    // Mark as downloaded locally (actual download handled by SoundsTable)
    setDownloadedVideos(prev => new Set([...prev, sample.id]));

    toast.success('Download started!', {
      description: `Downloading ${sample.creator_username} video`,
    });
  };

  // Hover-to-preload: Start loading audio when user hovers over play button
  const handleSampleHover = useCallback((sample: Sample) => {
    const audioUrl = sample.audio_url_mp3 || sample.audio_url_wav;
    if (!audioUrl) return;

    // Check if already preloaded
    const existingLink = document.getElementById(`hover-preload-${sample.id}`);
    if (existingLink) return;

    // Create high-priority preload link
    const preloadLink = document.createElement('link');
    preloadLink.rel = 'preload';
    preloadLink.as = 'audio';
    preloadLink.href = audioUrl;
    preloadLink.id = `hover-preload-${sample.id}`;
    document.head.appendChild(preloadLink);

    // Clean up after 30 seconds if not played
    setTimeout(() => {
      const link = document.getElementById(`hover-preload-${sample.id}`);
      if (link) link.remove();
    }, 30000);
  }, []);

  const handlePlayerPlayPause = () => {
    setIsPlaying(!isPlaying);
  };

  const handlePlayerNext = () => {
    if (!currentSample) return;
    const currentIndex = filteredSamples.findIndex(s => s.id === currentSample.id);
    const nextIndex = (currentIndex + 1) % filteredSamples.length;
    const nextSample = filteredSamples[nextIndex];
    setCurrentSample(nextSample);
    setIsPlaying(true);
  };

  const handlePlayerPrevious = () => {
    if (!currentSample) return;
    const currentIndex = filteredSamples.findIndex(s => s.id === currentSample.id);
    const prevIndex = currentIndex === 0 ? filteredSamples.length - 1 : currentIndex - 1;
    const prevSample = filteredSamples[prevIndex];
    setCurrentSample(prevSample);
    setIsPlaying(true);
  };

  const handleFavoriteChange = useCallback((sampleId: string, isFavorited: boolean) => {
    // Update the current sample if it's the one being favorited
    if (currentSample?.id === sampleId) {
      setCurrentSample({
        ...currentSample,
        is_favorited: isFavorited
      });
    }
    // Update the query cache to reflect the new favorite state
    queryClient.setQueryData(['samples', currentPage], (oldData: PaginatedResponse<Sample> | undefined) => {
      if (!oldData) return oldData;
      return {
        ...oldData,
        items: oldData.items.map(s =>
          s.id === sampleId ? { ...s, is_favorited: isFavorited } : s
        )
      };
    });
  }, [currentSample, queryClient, currentPage]);

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

        {/* Credit Balance Display */}
        {creditBalance !== null && (
          <Link href={hasSubscription ? '/top-up' : '/pricing'}>
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-md hover:bg-accent/50 transition-colors cursor-pointer">
              <Coins className={`w-4 h-4 ${creditBalance > 0 ? 'text-foreground' : 'text-muted-foreground'}`} />
              <span className={`text-sm ${creditBalance > 0 ? 'text-foreground' : 'text-muted-foreground'}`}>
                {creditBalance}
              </span>
            </div>
          </Link>
        )}
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
              {/* Search Bar */}
              <div className="mb-4 relative max-w-2xl">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  type="text"
                  placeholder="Search samples by description, creator, tags..."
                  value={searchQuery}
                  onChange={(e) => {
                    setSearchQuery(e.target.value);
                    setCurrentPage(1); // Reset to page 1 when searching
                  }}
                  className="pl-10 pr-10"
                />
                {searchQuery && (
                  <button
                    onClick={() => {
                      setSearchQuery('');
                      setCurrentPage(1);
                    }}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                  >
                    <X className="h-4 w-4" />
                  </button>
                )}
              </div>

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
                    userCredits={creditBalance ?? undefined}
                    onSamplePreview={handleSamplePreview}
                    onSampleHover={handleSampleHover}
                    onSampleDownload={handleSampleDownload}
                    onVideoDownload={handleVideoDownload}
                  />
                  <SamplesPagination
                    currentPage={currentPage}
                    totalPages={Math.ceil((data?.total || totalSamples) / itemsPerPage)}
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
                userCredits={creditBalance ?? undefined}
                onSamplePreview={handleSamplePreview}
                onSampleHover={handleSampleHover}
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
        onFavoriteChange={handleFavoriteChange}
      />
    </>
  );
}