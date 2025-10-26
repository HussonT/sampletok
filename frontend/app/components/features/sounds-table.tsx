'use client';

import React, { useState } from 'react';
import Image from 'next/image';
import { useAuth } from '@clerk/nextjs';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Play, Pause, Users, Video } from 'lucide-react';
import { Sample } from '@/types/api';
import { CreatorHoverCard } from '@/components/features/creator-hover-card';
import { VideoPreviewHover } from '@/components/features/video-preview-hover';
import { DownloadButton } from '@/components/features/download-button';
import { FavoriteButton } from '@/components/features/favorite-button';
import { getAvatarWithFallback } from '@/lib/avatar';
import { removeHashtags } from '@/lib/text-utils';
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
  onSamplePreview?: (sample: Sample) => void;
  onSampleDownload?: (sample: Sample) => void;
  onVideoDownload?: (sample: Sample) => void;
  onLoadMore?: () => void;
  hasMore?: boolean;
  isLoadingMore?: boolean;
}

export function SoundsTable({
  samples,
  currentSample,
  isPlaying = false,
  downloadedSamples,
  downloadedVideos,
  onSamplePreview,
  onSampleDownload,
  onVideoDownload,
  onLoadMore,
  hasMore = false,
  isLoadingMore = false
}: SoundsTableProps) {
  const { isSignedIn, getToken } = useAuth();
  const router = useRouter();
  const [downloadingVideo, setDownloadingVideo] = useState<string | null>(null);

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

  const handleDragStart = (e: React.DragEvent, sample: Sample) => {
    e.dataTransfer.setData('application/json', JSON.stringify(sample));
    e.dataTransfer.effectAllowed = 'copy';
  };

  const handleVideoDownload = async (sample: Sample) => {
    // Redirect to sign-in if not authenticated
    if (!isSignedIn) {
      toast.info('Please sign in to download videos', {
        description: 'You need to be signed in to download videos',
      });
      const returnUrl = encodeURIComponent(window.location.pathname + window.location.search);
      router.push(`/sign-in?redirect_url=${returnUrl}`);
      return;
    }

    try {
      setDownloadingVideo(sample.id);
      toast.loading('Starting video download...', { id: 'video-download' });

      // Call the download endpoint (uses Clerk ID from JWT for authentication)
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/samples/${sample.id}/download-video`,
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
        description: 'MP4 file saved to your downloads',
      });

      onVideoDownload?.(sample);
    } catch (error) {
      console.error('Video download error:', error);
      toast.error('Video download failed', {
        id: 'video-download',
        description: 'Please try again or contact support if the issue persists',
      });
    } finally {
      setDownloadingVideo(null);
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
            <th className="text-left py-3 px-4 font-normal whitespace-nowrap" style={{ width: '70px' }}>Audio</th>
            <th className="text-left py-3 px-4 font-normal whitespace-nowrap" style={{ width: '70px' }}>Video</th>
          </tr>
        </thead>
        <tbody>
          {samples.map((sample, index) => {
            const isCurrentPlaying = currentSample?.id === sample.id && isPlaying;

            return (
              <tr
                key={sample.id}
                className="border-b border-border hover:bg-secondary/20 transition-colors"
                draggable
                onDragStart={(e) => handleDragStart(e, sample)}
                style={{ cursor: 'grab' }}
              >
                <td className="py-3 px-4">
                  <div className="flex items-center gap-2">
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
                    <FavoriteButton
                      sample={sample}
                      variant="ghost"
                      size="sm"
                      className="p-0 w-8 h-8"
                    />
                  </div>
                </td>
                <td className="py-3 px-4">
                  <div className="space-y-1">
                    <TooltipProvider>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <div className="text-sm font-medium text-foreground cursor-help">
                            {sample.description
                              ? `${removeHashtags(sample.description).slice(0, 30)}...`
                              : 'No description'}
                          </div>
                        </TooltipTrigger>
                        <TooltipContent side="top" className="max-w-md">
                          <p>{removeHashtags(sample.description || '')|| 'No description'}</p>
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
                    {sample.waveform_url ? (
                      <Image
                        src={sample.waveform_url}
                        alt="Waveform"
                        width={192}
                        height={64}
                        className="w-full h-full object-contain rounded-md"
                        unoptimized
                      />
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
                  {formatDuration(sample.duration_seconds || 0)}
                </td>
                <td className="py-3 px-4 text-sm">
                  {getKey(sample)}
                </td>
                <td className="py-3 px-4 text-sm">
                  {formatBPM(sample)}
                </td>
                <td className="py-3 px-4">
                  <VideoPreviewHover
                    videoUrl={sample.video_url}
                    tiktokUrl={sample.tiktok_url || '#'}
                  />
                </td>
                <td className="py-3 px-4">
                  <DownloadButton
                    sample={sample}
                    format="wav"
                    variant="ghost"
                    size="sm"
                    className="p-0 w-8 h-8"
                  />
                </td>
                <td className="py-3 px-4">
                  <Button
                    variant="ghost"
                    size="sm"
                    className={`p-0 w-8 h-8 ${downloadedVideos?.has(sample.id) ? 'text-primary' : ''}`}
                    onClick={() => handleVideoDownload(sample)}
                    title={downloadedVideos?.has(sample.id) ? "Download video (already purchased)" : "Download video (1 credit)"}
                    disabled={!sample.video_url}
                  >
                    <Video className="w-4 h-4" />
                  </Button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>

      {/* Load More Button */}
      {hasMore && onLoadMore && (
        <div className="flex justify-center py-8">
          <Button
            onClick={onLoadMore}
            disabled={isLoadingMore}
            variant="outline"
            size="lg"
          >
            {isLoadingMore ? 'Loading...' : 'Load More Samples'}
          </Button>
        </div>
      )}

      {/* End of results message */}
      {!hasMore && samples.length > 0 && (
        <div className="flex justify-center py-8 text-sm text-muted-foreground">
          No more samples to load
        </div>
      )}
    </div>
  );
}