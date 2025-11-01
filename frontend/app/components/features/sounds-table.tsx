'use client';

import React, { useState, useEffect } from 'react';
import Image from 'next/image';
import { useAuth, useClerk } from '@clerk/nextjs';
import { Button } from '@/components/ui/button';
import { Play, Pause, Users, Video, ImageOff, Loader2, Layers, ChevronDown, ChevronRight, Download } from 'lucide-react';
import { Sample, ProcessingStatus, Stem, StemProcessingStatus } from '@/types/api';
import { CreatorHoverCard } from '@/components/features/creator-hover-card';
import { VideoPreviewHover } from '@/components/features/video-preview-hover';
import { DownloadButton } from '@/components/features/download-button';
import { FavoriteButton } from '@/components/features/favorite-button';
import { StemFavoriteButton } from '@/components/features/stem-favorite-button';
import { StemSeparationModal } from '@/components/features/stem-separation-modal';
import { getAvatarWithFallback } from '@/lib/avatar';
import { toast } from 'sonner';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';

interface SoundsTableProps {
  samples: Sample[];
  currentSample?: Sample | null;
  isPlaying?: boolean;
  downloadedSamples?: Set<string>;
  downloadedVideos?: Set<string>;
  userCredits?: number;
  onSamplePreview?: (sample: Sample) => void;
  onSampleDownload?: (sample: Sample) => void;
  onVideoDownload?: (sample: Sample) => void;
  onFavoriteChange?: (sampleId: string, isFavorited: boolean) => void;
}

export function SoundsTable({
  samples,
  currentSample,
  isPlaying = false,
  downloadedSamples,
  downloadedVideos,
  userCredits = 0,
  onSamplePreview,
  onSampleDownload,
  onVideoDownload,
  onFavoriteChange
}: SoundsTableProps) {
  const { isSignedIn, getToken } = useAuth();
  const { openSignUp } = useClerk();
  const [downloadingVideo, setDownloadingVideo] = useState<string | null>(null);
  const [downloadingStem, setDownloadingStem] = useState<string | null>(null);
  const [waveformErrors, setWaveformErrors] = useState<Set<string>>(new Set());
  const [stemModalOpen, setStemModalOpen] = useState(false);
  const [selectedSampleForStems, setSelectedSampleForStems] = useState<Sample | null>(null);

  // Stem expansion state
  const [expandedSamples, setExpandedSamples] = useState<Set<string>>(new Set());
  const [stemsData, setStemsData] = useState<Map<string, Stem[]>>(new Map());
  const [loadingStems, setLoadingStems] = useState<Map<string, boolean>>(new Map());

  const formatDuration = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const formatBPM = (sample: Sample): string => {
    return sample.bpm ? sample.bpm.toString() : '--';
  };

  const getKey = (sample: Sample): string => {
    return sample.key || '--';
  };

  const formatFollowers = (count: number): string => {
    if (count >= 1000000) {
      return `${(count / 1000000).toFixed(1)}M followers`;
    } else if (count >= 1000) {
      return `${(count / 1000).toFixed(0)}k followers`;
    }
    return `${count} followers`;
  };

  const getCategories = (_sample: Sample): string[] => {
    // TODO: Implement proper category detection
    return [];
  };

  const isProcessing = (sample: Sample): boolean => {
    return sample.status === ProcessingStatus.PENDING || sample.status === ProcessingStatus.PROCESSING;
  };

  const handleDragStart = (e: React.DragEvent, sample: Sample) => {
    e.dataTransfer.setData('application/json', JSON.stringify(sample));
    e.dataTransfer.effectAllowed = 'copy';
  };

  const fetchStems = async (sampleId: string, forceRefresh = false) => {
    // If we're already loading or have data (and not forcing refresh), don't refetch
    if (!forceRefresh && (loadingStems.get(sampleId) || stemsData.has(sampleId))) {
      return;
    }

    setLoadingStems(new Map(loadingStems.set(sampleId, true)));

    try {
      const token = await getToken();
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/stems/${sampleId}/stems`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error('Failed to fetch stems');
      }

      const stems: Stem[] = await response.json();
      setStemsData(new Map(stemsData.set(sampleId, stems)));
    } catch (error) {
      console.error('Error fetching stems:', error);
      // Don't show error toast for background fetches
      if (forceRefresh) {
        toast.error('Failed to load stems');
      }
    } finally {
      setLoadingStems(new Map(loadingStems.set(sampleId, false)));
    }
  };

  // Fetch stems for all samples on mount to show chevrons
  useEffect(() => {
    const fetchAllStems = async () => {
      if (!isSignedIn) return;

      // Fetch stems for all completed samples
      for (const sample of samples) {
        if (!isProcessing(sample)) {
          await fetchStems(sample.id);
        }
      }
    };

    fetchAllStems();
  }, [samples.length, isSignedIn]); // Only re-run when sample count changes or auth status changes

  const toggleStemExpansion = async (sampleId: string) => {
    const newExpanded = new Set(expandedSamples);

    if (expandedSamples.has(sampleId)) {
      // Collapse
      newExpanded.delete(sampleId);
    } else {
      // Expand - fetch stems if we don't have them
      newExpanded.add(sampleId);
      if (!stemsData.has(sampleId)) {
        await fetchStems(sampleId);
      }
    }

    setExpandedSamples(newExpanded);
  };

  const getStemTypeLabel = (stemType: string): string => {
    const labels: Record<string, string> = {
      'vocal': 'Vocals',
      'drum': 'Drums',
      'bass': 'Bass',
      'piano': 'Piano',
      'electric_guitar': 'Electric Guitar',
      'acoustic_guitar': 'Acoustic Guitar',
      'synthesizer': 'Synthesizer',
      'strings': 'Strings',
      'wind': 'Wind Instruments',
    };
    return labels[stemType] || stemType;
  };

  const getStemStatusBadge = (status: StemProcessingStatus) => {
    const statusStyles: Record<StemProcessingStatus, { bg: string; text: string; label: string }> = {
      [StemProcessingStatus.PENDING]: { bg: 'bg-yellow-500/10', text: 'text-yellow-600', label: 'Getting ready...' },
      [StemProcessingStatus.UPLOADING]: { bg: 'bg-blue-500/10', text: 'text-blue-600', label: 'Fetching from the tok-verse...' },
      [StemProcessingStatus.PROCESSING]: { bg: 'bg-blue-500/10', text: 'text-blue-600', label: 'Extracting the vibes...' },
      [StemProcessingStatus.DOWNLOADING]: { bg: 'bg-blue-500/10', text: 'text-blue-600', label: 'Packaging your magic...' },
      [StemProcessingStatus.ANALYZING]: { bg: 'bg-purple-500/10', text: 'text-purple-600', label: 'Decoding the frequencies...' },
      [StemProcessingStatus.COMPLETED]: { bg: 'bg-green-500/10', text: 'text-green-600', label: '' },
      [StemProcessingStatus.FAILED]: { bg: 'bg-red-500/10', text: 'text-red-600', label: 'Oops, something broke :(' },
    };

    const style = statusStyles[status];

    // Determine if this is a loading state that should show an animated spinner
    const isLoading = [
      StemProcessingStatus.PENDING,
      StemProcessingStatus.UPLOADING,
      StemProcessingStatus.PROCESSING,
      StemProcessingStatus.DOWNLOADING,
      StemProcessingStatus.ANALYZING,
    ].includes(status);

    // Don't render badge for completed status (no label)
    if (status === StemProcessingStatus.COMPLETED) {
      return null;
    }

    return (
      <span className={`px-2 py-1 rounded text-xs flex items-center gap-1.5 ${style.bg} ${style.text}`}>
        {isLoading && <Loader2 className="w-3 h-3 animate-spin" />}
        {style.label}
      </span>
    );
  };

  const handleVideoDownload = async (sample: Sample) => {
    // Open Clerk sign-up modal if not authenticated
    if (!isSignedIn) {
      const currentUrl = window.location.pathname + window.location.search;
      openSignUp({
        redirectUrl: currentUrl,
        afterSignUpUrl: currentUrl,
      });
      return;
    }

    try {
      setDownloadingVideo(sample.id);
      toast.loading('Starting video download...', { id: 'video-download' });

      // Ensure API URL is configured
      const apiUrl = process.env.NEXT_PUBLIC_API_URL;
      if (!apiUrl) {
        throw new Error('API URL not configured. Please set NEXT_PUBLIC_API_URL environment variable.');
      }

      // Call the download endpoint (uses Clerk ID from JWT for authentication)
      const response = await fetch(
        `${apiUrl}/api/v1/samples/${sample.id}/download-video`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${await getToken()}`,
          },
        }
      );

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));

        // Handle 403 (no subscription or no credits) with helpful messages
        if (response.status === 403) {
          const detail = errorData.detail || '';

          if (detail.includes('subscription required') || detail.includes('Active subscription')) {
            toast.error('Subscription Required', {
              id: 'video-download',
              description: 'You need an active subscription to download videos.',
              action: {
                label: 'Subscribe Now',
                onClick: () => window.location.href = '/pricing'
              },
              duration: 5000,
            });
            return;
          }

          if (detail.includes('Insufficient credits') || detail.includes('credits')) {
            toast.error('No Credits Available', {
              id: 'video-download',
              description: 'You need at least 1 credit to download. Top up your credits to continue.',
              action: {
                label: 'Buy Credits',
                onClick: () => window.location.href = '/top-up'
              },
              duration: 5000,
            });
            return;
          }
        }

        // Only log unexpected errors (not 403s which are handled above)
        console.error('Video download failed:', response.status, errorData);
        throw new Error(errorData.detail || 'Download failed');
      }

      // Get the blob and trigger download
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${sample.creator_username || 'unknown'}_${sample.id}.mp4`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);

      toast.success('Video download complete!', {
        id: 'video-download',
        description: sample.is_downloaded
          ? 'MP4 file saved to your downloads (Free re-download)'
          : 'MP4 file saved to your downloads (1 credit used)',
      });

      onVideoDownload?.(sample);
    } catch (error) {
      console.error('Video download error:', error);

      // Show helpful error message
      const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';

      // If error mentions credits or subscription, show helpful toast
      if (errorMessage.toLowerCase().includes('credit') || errorMessage.toLowerCase().includes('subscription')) {
        toast.error('Cannot Download Video', {
          id: 'video-download',
          description: errorMessage,
          action: {
            label: errorMessage.toLowerCase().includes('subscription') ? 'Subscribe' : 'Buy Credits',
            onClick: () => window.location.href = errorMessage.toLowerCase().includes('subscription') ? '/pricing' : '/top-up'
          },
          duration: 5000,
        });
      } else {
        toast.error('Video download failed', {
          id: 'video-download',
          description: errorMessage || 'Please try again or contact support if the issue persists',
        });
      }
    } finally {
      setDownloadingVideo(null);
    }
  };

  const handleStemDownload = async (stem: Stem, format: 'wav' | 'mp3' = 'mp3') => {
    // Open Clerk sign-up modal if not authenticated
    if (!isSignedIn) {
      const currentUrl = window.location.pathname + window.location.search;
      openSignUp({
        redirectUrl: currentUrl,
        afterSignUpUrl: currentUrl,
      });
      return;
    }

    try {
      setDownloadingStem(stem.id);
      toast.loading(`Starting ${format.toUpperCase()} download...`, { id: 'stem-download' });

      // Ensure API URL is configured
      const apiUrl = process.env.NEXT_PUBLIC_API_URL;
      if (!apiUrl) {
        throw new Error('API URL not configured. Please set NEXT_PUBLIC_API_URL environment variable.');
      }

      // Call the download endpoint
      const response = await fetch(
        `${apiUrl}/api/v1/stems/${stem.id}/download?download_type=${format}`,
        {
          method: 'GET',
          headers: {
            'Authorization': `Bearer ${await getToken()}`,
          },
        }
      );

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));

        // Handle 403 (no subscription or no credits) with helpful messages
        if (response.status === 403) {
          const detail = errorData.detail || '';

          if (detail.includes('subscription required') || detail.includes('Active subscription')) {
            toast.error('Subscription Required', {
              id: 'stem-download',
              description: 'You need an active subscription to download stems.',
              action: {
                label: 'Subscribe Now',
                onClick: () => window.location.href = '/pricing'
              },
              duration: 5000,
            });
            return;
          }

          if (detail.includes('Insufficient credits') || detail.includes('credits')) {
            toast.error('No Credits Available', {
              id: 'stem-download',
              description: 'You need at least 1 credit to download. Top up your credits to continue.',
              action: {
                label: 'Buy Credits',
                onClick: () => window.location.href = '/top-up'
              },
              duration: 5000,
            });
            return;
          }
        }

        console.error('Stem download failed:', response.status, errorData);
        throw new Error(errorData.detail || 'Download failed');
      }

      // Get the blob and trigger download
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${stem.stem_type}_${stem.id}.${format}`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);

      toast.success('Download complete!', {
        id: 'stem-download',
        description: stem.is_downloaded
          ? `${format.toUpperCase()} file saved to your downloads (Free re-download)`
          : `${format.toUpperCase()} file saved to your downloads (1 credit used)`,
      });

      // Refresh stems to update download status
      // Find which sample this stem belongs to
      for (const [sampleId, stems] of stemsData.entries()) {
        if (stems.some(s => s.id === stem.id)) {
          await fetchStems(sampleId);
          break;
        }
      }
    } catch (error) {
      console.error('Stem download error:', error);

      const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';

      if (errorMessage.toLowerCase().includes('credit') || errorMessage.toLowerCase().includes('subscription')) {
        toast.error('Cannot Download Stem', {
          id: 'stem-download',
          description: errorMessage,
          action: {
            label: errorMessage.toLowerCase().includes('subscription') ? 'Subscribe' : 'Buy Credits',
            onClick: () => window.location.href = errorMessage.toLowerCase().includes('subscription') ? '/pricing' : '/top-up'
          },
          duration: 5000,
        });
      } else {
        toast.error('Download failed', {
          id: 'stem-download',
          description: errorMessage || 'Please try again or contact support if the issue persists',
        });
      }
    } finally {
      setDownloadingStem(null);
    }
  };

  return (
    <div className="w-full bg-background">
      <table className="w-full min-w-[1400px]">
        <thead>
          <tr className="border-b border-border text-muted-foreground text-sm">
            <th className="text-left py-3 px-4 font-normal whitespace-nowrap" style={{ width: '96px' }}></th>
            <th className="text-left py-3 px-4 font-normal whitespace-nowrap" style={{ width: '280px' }}>Sample</th>
            <th className="text-left py-3 px-4 font-normal whitespace-nowrap" style={{ width: '200px' }}>Creator</th>
            <th className="text-left py-3 px-4 font-normal whitespace-nowrap" style={{ width: '220px' }}>Tags</th>
            <th className="text-left py-3 px-4 font-normal whitespace-nowrap" style={{ width: '240px' }}>Waveform</th>
            <th className="text-left py-3 px-4 font-normal whitespace-nowrap" style={{ width: '80px' }}>Duration</th>
            <th className="text-left py-3 px-4 font-normal whitespace-nowrap" style={{ width: '100px' }}>Key</th>
            <th className="text-left py-3 px-4 font-normal whitespace-nowrap" style={{ width: '70px' }}>BPM</th>
            <th className="text-left py-3 px-4 font-normal whitespace-nowrap" style={{ width: '100px' }}>TikTok</th>
            <th className="text-left py-3 px-4 font-normal whitespace-nowrap" style={{ width: '70px' }}>Stems</th>
            <th className="text-left py-3 px-4 font-normal whitespace-nowrap" style={{ width: '70px' }}>Audio</th>
            <th className="text-left py-3 px-4 font-normal whitespace-nowrap" style={{ width: '70px' }}>Video</th>
          </tr>
        </thead>
        <tbody>
          {samples.map((sample, index) => {
            const isCurrentPlaying = currentSample?.id === sample.id && isPlaying;
            const processing = isProcessing(sample);

            return (
              <React.Fragment key={sample.id}>
                <tr
                  className={`border-b border-border transition-colors ${processing ? 'bg-secondary/10' : 'hover:bg-secondary/20'}`}
                  draggable={!processing}
                  onDragStart={(e) => !processing && handleDragStart(e, sample)}
                  style={{ cursor: processing ? 'default' : 'grab' }}
                >
                <td className="py-3 px-4">
                  <div className="flex items-center gap-2">
                    {processing ? (
                      <TooltipProvider>
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <div className="p-0 w-8 h-8 flex items-center justify-center">
                              <Loader2 className="w-4 h-4 animate-spin text-primary" />
                            </div>
                          </TooltipTrigger>
                          <TooltipContent>
                            <p className="text-xs">Processing sample...</p>
                          </TooltipContent>
                        </Tooltip>
                      </TooltipProvider>
                    ) : (
                      <Button
                        variant="ghost"
                        size="sm"
                        className="p-0 w-8 h-8 hover:bg-secondary/50"
                        onClick={() => onSamplePreview?.(sample)}
                      >
                        {isCurrentPlaying ? (
                          <Pause className="w-4 h-4" />
                        ) : (
                          <Play className="w-4 h-4" />
                        )}
                      </Button>
                    )}
                    {!processing && (
                      <FavoriteButton
                        sample={sample}
                        variant="ghost"
                        size="sm"
                        className="p-0 w-8 h-8"
                        onFavoriteChange={(isFavorited) => onFavoriteChange?.(sample.id, isFavorited)}
                      />
                    )}
                  </div>
                </td>
                <td className="py-3 px-4">
                  <div className="space-y-1">
                    {processing ? (
                      <div className="flex items-center gap-2">
                        <div className="text-sm font-medium text-muted-foreground italic">
                          Processing sample...
                        </div>
                      </div>
                    ) : (
                      <>
                        <TooltipProvider>
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <div className="text-sm font-medium text-foreground cursor-help">
                                {sample.title
                                  ? `${sample.title.slice(0, 30)}...`
                                  : sample.description
                                  ? `${sample.description.slice(0, 30)}...`
                                  : 'No title'}
                              </div>
                            </TooltipTrigger>
                            <TooltipContent side="top" className="max-w-md">
                              <p>{sample.title || sample.description || 'No title'}</p>
                            </TooltipContent>
                          </Tooltip>
                        </TooltipProvider>
                        <div className="flex items-center gap-3">
                          <div className="flex gap-2">
                            {getCategories(sample).map((cat) => (
                              <span key={cat} className="bg-secondary text-secondary-foreground px-2 py-0.5 rounded text-xs">
                                {cat}
                              </span>
                            ))}
                          </div>
                          <div className="flex items-center gap-1 text-xs text-muted-foreground">
                            <Users className="w-3 h-3" />
                            <span>{sample.view_count ? `${(sample.view_count / 1000).toFixed(0)}k views` : '0 views'}</span>
                          </div>
                        </div>
                      </>
                    )}
                  </div>
                </td>
                <td className="py-3 px-4">
                  {sample.tiktok_creator ? (
                    <CreatorHoverCard creator={sample.tiktok_creator}>
                      <div className="flex items-center gap-2.5 cursor-pointer">
                        <Image
                          src={getAvatarWithFallback(
                            sample.tiktok_creator.avatar_thumb,
                            sample.tiktok_creator.username
                          )}
                          alt={`@${sample.tiktok_creator.username}`}
                          width={40}
                          height={40}
                          className="w-10 h-10 rounded object-cover flex-shrink-0"
                          unoptimized
                          onError={(e) => {
                            // Fallback to generated avatar on error
                            const target = e.target as HTMLImageElement;
                            target.src = getAvatarWithFallback(null, sample.tiktok_creator!.username);
                          }}
                        />
                        <div className="min-w-0 flex-1">
                          <div className="text-sm font-medium hover:text-primary transition-colors truncate">
                            @{sample.tiktok_creator.username}
                          </div>
                          <div className="flex items-center gap-1 text-xs text-muted-foreground">
                            <Users className="w-3 h-3 flex-shrink-0" />
                            <span>{formatFollowers(sample.tiktok_creator.follower_count)}</span>
                          </div>
                        </div>
                      </div>
                    </CreatorHoverCard>
                  ) : (
                    <div className="flex items-center gap-2.5">
                      <Image
                        src={getAvatarWithFallback(null, sample.creator_username || sample.id)}
                        alt={`@${sample.creator_username || 'unknown'}`}
                        width={40}
                        height={40}
                        className="w-10 h-10 rounded object-cover flex-shrink-0"
                        unoptimized
                        onError={(e) => {
                          // Fallback to generated avatar on error
                          const target = e.target as HTMLImageElement;
                          target.src = getAvatarWithFallback(null, sample.creator_username || sample.id);
                        }}
                      />
                      <div className="min-w-0 flex-1">
                        <div className="text-sm font-medium truncate">@{sample.creator_username || 'unknown'}</div>
                        <div className="flex items-center gap-1 text-xs text-muted-foreground">
                          <Users className="w-3 h-3 flex-shrink-0" />
                          <span>{sample.creator_follower_count ? formatFollowers(sample.creator_follower_count) : '0 followers'}</span>
                        </div>
                      </div>
                    </div>
                  )}
                </td>
                <td className="py-3 px-4">
                  {sample.tags && sample.tags.length > 0 ? (
                    <TooltipProvider>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <div className="flex flex-wrap gap-1 max-w-[200px] cursor-help">
                            {sample.tags.slice(0, 3).map((tag) => (
                              <span
                                key={tag}
                                className="bg-primary/10 text-primary px-2 py-0.5 rounded-md text-xs font-medium"
                              >
                                #{tag}
                              </span>
                            ))}
                            {sample.tags.length > 3 && (
                              <span className="text-xs text-muted-foreground self-center">
                                +{sample.tags.length - 3}
                              </span>
                            )}
                          </div>
                        </TooltipTrigger>
                        <TooltipContent
                          side="top"
                          className="w-64 p-3 bg-[hsl(0,0%,17%)] border border-[hsl(0,0%,25%)] [&>svg]:hidden"
                          sideOffset={5}
                        >
                          <div className="flex flex-wrap gap-1.5 w-full">
                            {sample.tags.map((tag) => (
                              <span
                                key={tag}
                                className="bg-primary/20 text-primary px-2 py-0.5 rounded-md text-xs font-medium whitespace-nowrap inline-block"
                              >
                                #{tag}
                              </span>
                            ))}
                          </div>
                        </TooltipContent>
                      </Tooltip>
                    </TooltipProvider>
                  ) : (
                    <span className="text-xs text-muted-foreground">No tags</span>
                  )}
                </td>
                <td className="py-3 px-4">
                  <div className="w-full h-16 relative">
                    {processing ? (
                      <div className="w-full h-full flex items-center justify-center bg-secondary/20 rounded-md border border-border/50">
                        <div className="flex items-center gap-2 text-muted-foreground">
                          <Loader2 className="w-3 h-3 animate-spin" />
                          <span className="text-[10px]">Generating...</span>
                        </div>
                      </div>
                    ) : sample.waveform_url && !waveformErrors.has(sample.id) ? (
                      <Image
                        src={sample.waveform_url}
                        alt="Waveform"
                        width={192}
                        height={64}
                        className="w-full h-full object-contain rounded-md"
                        unoptimized
                        onError={() => {
                          setWaveformErrors(prev => new Set(prev).add(sample.id));
                        }}
                      />
                    ) : waveformErrors.has(sample.id) ? (
                      <div className="w-full h-full flex items-center justify-center bg-secondary/20 rounded-md border border-border">
                        <div className="flex flex-col items-center gap-1 text-muted-foreground">
                          <ImageOff className="w-4 h-4" />
                          <span className="text-[10px]">Image unavailable</span>
                        </div>
                      </div>
                    ) : (
                      <svg className="w-full h-full" viewBox="0 0 100 60">
                        <defs>
                          <linearGradient id={`gradient-${sample.id}`} x1="0%" y1="0%" x2="0%" y2="100%">
                            <stop offset="0%" stopColor="#EC4899" stopOpacity="0.8" />
                            <stop offset="100%" stopColor="#8B5CF6" stopOpacity="0.6" />
                          </linearGradient>
                        </defs>
                        {Array.from({ length: 50 }).map((_, i) => {
                          // Generate deterministic height based on sample ID and position
                          const seed = sample.id.charCodeAt(0) + sample.id.charCodeAt(sample.id.length - 1) + i;
                          const height = ((seed * 9.7) % 52) + 8;
                          const y = (60 - height) / 2;
                          return (
                            <rect
                              key={i}
                              x={i * 2}
                              y={y}
                              width="1.5"
                              height={height}
                              fill={`url(#gradient-${sample.id})`}
                              className="transition-all"
                            />
                          );
                        })}
                      </svg>
                    )}
                  </div>
                </td>
                <td className="py-3 px-4 text-sm text-muted-foreground">
                  {processing ? '--' : formatDuration(sample.duration_seconds || 0)}
                </td>
                <td className="py-3 px-4 text-sm text-muted-foreground">
                  {processing ? '--' : getKey(sample)}
                </td>
                <td className="py-3 px-4 text-sm text-muted-foreground">
                  {processing ? '--' : formatBPM(sample)}
                </td>
                <td className="py-3 px-4">
                  {processing ? (
                    <div className="flex items-center justify-center w-8 h-8">
                      <span className="text-xs text-muted-foreground">--</span>
                    </div>
                  ) : (
                    <VideoPreviewHover
                      videoUrl={sample.video_url}
                      tiktokUrl={sample.tiktok_url || '#'}
                    />
                  )}
                </td>
                <td className="py-3 px-4">
                  {processing ? (
                    <div className="flex items-center justify-center w-8 h-8">
                      <span className="text-xs text-muted-foreground">--</span>
                    </div>
                  ) : (
                    <div className="flex items-center gap-1">
                      {/* Chevron button - only show if stems exist */}
                      {stemsData.get(sample.id) && stemsData.get(sample.id)!.length > 0 ? (
                        <TooltipProvider>
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <Button
                                variant="ghost"
                                size="sm"
                                className="p-0 w-8 h-8"
                                onClick={() => toggleStemExpansion(sample.id)}
                              >
                                {expandedSamples.has(sample.id) ? (
                                  <ChevronDown className="w-4 h-4" />
                                ) : (
                                  <ChevronRight className="w-4 h-4" />
                                )}
                              </Button>
                            </TooltipTrigger>
                            <TooltipContent>
                              <p className="text-xs">
                                {expandedSamples.has(sample.id) ? 'Hide' : 'Show'} stems ({stemsData.get(sample.id)?.length || 0})
                              </p>
                            </TooltipContent>
                          </Tooltip>
                        </TooltipProvider>
                      ) : loadingStems.get(sample.id) ? (
                        <div className="w-8 h-8 flex items-center justify-center">
                          <Loader2 className="w-4 h-4 animate-spin" />
                        </div>
                      ) : null}

                      {/* Layers button - always show for creating new stems */}
                      <TooltipProvider>
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <Button
                              variant="ghost"
                              size="sm"
                              className="p-0 w-8 h-8"
                              onClick={() => {
                                if (!isSignedIn) {
                                  const currentUrl = window.location.pathname + window.location.search;
                                  openSignUp({
                                    redirectUrl: currentUrl,
                                    afterSignUpUrl: currentUrl,
                                  });
                                  return;
                                }
                                setSelectedSampleForStems(sample);
                                setStemModalOpen(true);
                              }}
                            >
                              <Layers className="w-4 h-4" />
                            </Button>
                          </TooltipTrigger>
                          <TooltipContent>
                            <p className="text-xs">Separate stems (2 credits per stem)</p>
                          </TooltipContent>
                        </Tooltip>
                      </TooltipProvider>
                    </div>
                  )}
                </td>
                <td className="py-3 px-4">
                  {processing ? (
                    <div className="flex items-center justify-center w-8 h-8">
                      <span className="text-xs text-muted-foreground">--</span>
                    </div>
                  ) : (
                    <DownloadButton
                      sample={sample}
                      format="wav"
                      variant="ghost"
                      size="sm"
                      className="p-0 w-8 h-8"
                    />
                  )}
                </td>
                <td className="py-3 px-4">
                  {processing ? (
                    <div className="flex items-center justify-center w-8 h-8">
                      <span className="text-xs text-muted-foreground">--</span>
                    </div>
                  ) : (
                    <Button
                      variant="ghost"
                      size="sm"
                      className={`p-0 w-8 h-8 ${downloadedVideos?.has(sample.id) ? 'text-primary' : ''}`}
                      onClick={() => handleVideoDownload(sample)}
                      title={sample.is_downloaded ? "Download video (Free - Already purchased)" : "Download video (1 credit)"}
                      disabled={!sample.video_url}
                    >
                      <Video className="w-4 h-4" />
                    </Button>
                  )}
                </td>
              </tr>

              {/* Expandable Stem Rows */}
              {expandedSamples.has(sample.id) && stemsData.get(sample.id) && (
                <>
                  {stemsData.get(sample.id)!.map((stem) => (
                    <tr
                      key={stem.id}
                      className="border-b border-border bg-secondary/5 hover:bg-secondary/10 transition-colors"
                    >
                      {/* Play and Favorite buttons */}
                      <td className="py-2 px-4">
                        <div className="flex items-center gap-2 pl-8">
                          {stem.status === StemProcessingStatus.COMPLETED && stem.download_url_mp3 ? (
                            <>
                              <Button
                                variant="ghost"
                                size="sm"
                                className="p-0 w-8 h-8 hover:bg-secondary/50"
                                onClick={() => {
                                  // Convert stem to Sample-like object for the player
                                  const stemAsSample: Sample = {
                                    id: stem.id,
                                    audio_url_mp3: stem.download_url_mp3,
                                    audio_url_wav: stem.download_url_wav,
                                    title: `${getStemTypeLabel(stem.stem_type)} - ${sample.title || sample.description || 'Untitled'}`,
                                    description: `${getStemTypeLabel(stem.stem_type)} from ${sample.title || sample.description || 'sample'}`,
                                    duration_seconds: stem.duration_seconds,
                                    bpm: stem.bpm,
                                    key: stem.key,
                                    status: ProcessingStatus.COMPLETED,
                                    // Pass through parent sample's creator info
                                    creator_username: sample.creator_username,
                                    creator_follower_count: sample.creator_follower_count,
                                    tiktok_creator: sample.tiktok_creator,
                                    tiktok_url: sample.tiktok_url,
                                    view_count: sample.view_count,
                                    like_count: sample.like_count,
                                    share_count: sample.share_count,
                                    comment_count: sample.comment_count,
                                    tags: sample.tags || [],
                                    created_at: stem.created_at,
                                  };
                                  onSamplePreview?.(stemAsSample);
                                }}
                              >
                                {currentSample?.id === stem.id && isPlaying ? (
                                  <Pause className="w-4 h-4" />
                                ) : (
                                  <Play className="w-4 h-4" />
                                )}
                              </Button>
                              <StemFavoriteButton
                                stem={stem}
                                variant="ghost"
                                size="sm"
                                className="p-0 w-8 h-8"
                                onFavoriteChange={(isFavorited) => {
                                  // Update stem in local state
                                  const updatedStems = stemsData.get(sample.id)?.map(s =>
                                    s.id === stem.id ? { ...s, is_favorited: isFavorited } : s
                                  );
                                  if (updatedStems) {
                                    setStemsData(new Map(stemsData.set(sample.id, updatedStems)));
                                  }
                                }}
                              />
                            </>
                          ) : (
                            <div className="w-8 h-8"></div>
                          )}
                        </div>
                      </td>

                      {/* Stem Type and Status */}
                      <td className="py-2 px-4" colSpan={2}>
                        <div className="flex items-center gap-3 pl-8">
                          <div className="flex items-center gap-2">
                            <div className="w-1 h-8 bg-primary/30 rounded-full"></div>
                            <div className="text-sm font-medium">{getStemTypeLabel(stem.stem_type)}</div>
                          </div>
                          {getStemStatusBadge(stem.status as StemProcessingStatus)}
                        </div>
                      </td>

                      {/* Tags column - empty */}
                      <td className="py-2 px-4"></td>

                      {/* Waveform column - empty for now */}
                      <td className="py-2 px-4">
                        {stem.status === StemProcessingStatus.PROCESSING && (
                          <div className="flex items-center gap-2 text-xs text-muted-foreground">
                            <Loader2 className="w-3 h-3 animate-spin" />
                            <span>Processing...</span>
                          </div>
                        )}
                      </td>

                      {/* Duration */}
                      <td className="py-2 px-4 text-sm text-muted-foreground">
                        {stem.duration_seconds ? formatDuration(stem.duration_seconds) : '--'}
                      </td>

                      {/* Key */}
                      <td className="py-2 px-4 text-sm text-muted-foreground">
                        {stem.key || '--'}
                      </td>

                      {/* BPM */}
                      <td className="py-2 px-4 text-sm text-muted-foreground">
                        {stem.bpm || '--'}
                      </td>

                      {/* TikTok column - empty */}
                      <td className="py-2 px-4"></td>

                      {/* Stems column - empty */}
                      <td className="py-2 px-4"></td>

                      {/* Audio Download */}
                      <td className="py-2 px-4">
                        {stem.status === StemProcessingStatus.COMPLETED && stem.download_url_mp3 ? (
                          <TooltipProvider>
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  className={`p-0 w-8 h-8 ${stem.is_downloaded ? 'text-pink-500 hover:text-pink-600' : ''}`}
                                  onClick={() => handleStemDownload(stem, 'mp3')}
                                  disabled={downloadingStem === stem.id}
                                >
                                  {downloadingStem === stem.id ? (
                                    <Loader2 className="w-4 h-4 animate-spin" />
                                  ) : (
                                    <Download className={`w-4 h-4 ${stem.is_downloaded ? 'fill-current' : ''}`} />
                                  )}
                                </Button>
                              </TooltipTrigger>
                              <TooltipContent>
                                <p className="text-xs">
                                  {stem.is_downloaded
                                    ? 'Download MP3 again (Free - Already purchased)'
                                    : 'Download MP3 (1 credit)'}
                                </p>
                              </TooltipContent>
                            </Tooltip>
                          </TooltipProvider>
                        ) : (
                          <div className="flex items-center justify-center w-8 h-8">
                            <span className="text-xs text-muted-foreground">--</span>
                          </div>
                        )}
                      </td>

                      {/* Video column - empty for stems */}
                      <td className="py-2 px-4"></td>
                    </tr>
                  ))}
                </>
              )}
              </React.Fragment>
            );
          })}
        </tbody>
      </table>

      {/* Stem Separation Modal */}
      {selectedSampleForStems && (
        <StemSeparationModal
          open={stemModalOpen}
          onOpenChange={setStemModalOpen}
          sample={selectedSampleForStems}
          userCredits={userCredits}
          onSuccess={() => {
            // Refresh stems data for this sample
            if (selectedSampleForStems) {
              fetchStems(selectedSampleForStems.id, true);
              // Expand the stems view to show the new stems
              setExpandedSamples(new Set(expandedSamples).add(selectedSampleForStems.id));
            }
            toast.success('Stem separation has started! Check back in a few minutes.');
          }}
        />
      )}
    </div>
  );
}