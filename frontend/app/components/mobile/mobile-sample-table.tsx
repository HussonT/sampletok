'use client';

import React, { useState } from 'react';
import { useAuth, useClerk } from '@clerk/nextjs';
import { Play, Pause, Download, Heart, Music2, Activity, Clock } from 'lucide-react';
import { Sample, ProcessingStatus } from '@/types/api';
import { Avatar, AvatarImage, AvatarFallback } from '@/components/ui/avatar';
import { getAvatarWithFallback } from '@/lib/avatar';
import { toast } from 'sonner';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';

interface MobileSampleTableProps {
  samples: Sample[];
  currentSample?: Sample | null;
  isPlaying?: boolean;
  onSamplePreview?: (sample: Sample) => void;
  onFavoriteChange?: (sampleId: string, isFavorited: boolean) => void;
}

export function MobileSampleTable({
  samples,
  currentSample,
  isPlaying = false,
  onSamplePreview,
  onFavoriteChange,
}: MobileSampleTableProps) {
  const { isSignedIn, getToken } = useAuth();
  const { openSignUp } = useClerk();
  const [downloadModalOpen, setDownloadModalOpen] = useState(false);
  const [selectedSample, setSelectedSample] = useState<Sample | null>(null);
  const [downloading, setDownloading] = useState(false);
  const [togglingFavorite, setTogglingFavorite] = useState<string | null>(null);

  const formatDuration = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const isProcessing = (sample: Sample): boolean => {
    return sample.status === ProcessingStatus.PENDING || sample.status === ProcessingStatus.PROCESSING;
  };

  const handlePlayPreview = (sample: Sample) => {
    if (!isProcessing(sample)) {
      onSamplePreview?.(sample);
    }
  };

  const handleDownloadClick = (sample: Sample) => {
    if (!isSignedIn) {
      const currentUrl = window.location.pathname + window.location.search;
      openSignUp({
        redirectUrl: currentUrl,
        afterSignUpUrl: currentUrl,
      });
      return;
    }

    setSelectedSample(sample);
    setDownloadModalOpen(true);
  };

  const handleDownload = async (format: 'wav' | 'mp3') => {
    if (!selectedSample || !isSignedIn) return;

    try {
      setDownloading(true);
      toast.loading(`Starting ${format.toUpperCase()} download...`, { id: 'audio-download' });

      const apiUrl = process.env.NEXT_PUBLIC_API_URL;
      if (!apiUrl) {
        throw new Error('API URL not configured');
      }

      const response = await fetch(
        `${apiUrl}/api/v1/samples/${selectedSample.id}/download?download_type=${format}`,
        {
          method: 'GET',
          headers: {
            'Authorization': `Bearer ${await getToken()}`,
          },
        }
      );

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
        throw new Error(errorData.detail || 'Download failed');
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${selectedSample.id}.${format}`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);

      toast.success('Download complete!', {
        id: 'audio-download',
        description: selectedSample.is_downloaded
          ? `${format.toUpperCase()} file saved (Free re-download)`
          : `${format.toUpperCase()} file saved (1 credit used)`,
      });

      setDownloadModalOpen(false);
    } catch (error) {
      console.error('Download error:', error);
      const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';

      toast.error('Download failed', {
        id: 'audio-download',
        description: errorMessage,
      });
    } finally {
      setDownloading(false);
    }
  };

  const handleFavoriteToggle = async (sample: Sample, e: React.MouseEvent) => {
    e.stopPropagation();

    if (!isSignedIn) {
      const currentUrl = window.location.pathname + window.location.search;
      openSignUp({
        redirectUrl: currentUrl,
        afterSignUpUrl: currentUrl,
      });
      return;
    }

    try {
      setTogglingFavorite(sample.id);
      const newFavoritedState = !sample.is_favorited;

      const token = await getToken();
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/samples/${sample.id}/favorite`,
        {
          method: newFavoritedState ? 'POST' : 'DELETE',
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        }
      );

      if (!response.ok) {
        throw new Error('Failed to update favorite');
      }

      onFavoriteChange?.(sample.id, newFavoritedState);

      if (newFavoritedState) {
        toast.success('Added to favorites');
      }
    } catch (error) {
      console.error('Error toggling favorite:', error);
      toast.error('Failed to update favorite');
    } finally {
      setTogglingFavorite(null);
    }
  };

  const getCreatorInfo = (sample: Sample) => {
    if (sample.source === 'instagram' && sample.instagram_creator) {
      return {
        name: sample.instagram_creator.full_name || sample.instagram_creator.username,
        username: `@${sample.instagram_creator.username}`,
        avatar: sample.instagram_creator.profile_pic_url,
      };
    }

    if (sample.tiktok_creator) {
      return {
        name: sample.tiktok_creator.nickname || sample.tiktok_creator.username,
        username: `@${sample.tiktok_creator.username}`,
        avatar: sample.tiktok_creator.avatar_thumb,
      };
    }

    return {
      name: sample.creator_name || 'Unknown Creator',
      username: sample.creator_username ? `@${sample.creator_username}` : '',
      avatar: undefined,
    };
  };

  return (
    <>
      <div className="w-full bg-background">
        {samples.map((sample) => {
          const isCurrentPlaying = currentSample?.id === sample.id && isPlaying;
          const processing = isProcessing(sample);
          const creator = getCreatorInfo(sample);

          return (
            <div
              key={sample.id}
              className={`border-b border-border transition-colors ${
                processing ? 'bg-secondary/10' : 'hover:bg-secondary/20'
              } ${isCurrentPlaying ? 'bg-secondary/30' : ''}`}
            >
              <div className="flex items-center gap-3 py-2 px-3">
                {/* Play button */}
                <button
                  onClick={() => handlePlayPreview(sample)}
                  disabled={processing}
                  className={`flex-shrink-0 w-10 h-10 rounded flex items-center justify-center transition-colors ${
                    processing
                      ? 'bg-secondary/50 cursor-not-allowed'
                      : 'hover:bg-secondary/50 active:scale-95'
                  }`}
                >
                  {isCurrentPlaying ? (
                    <Pause className="w-4 h-4" />
                  ) : (
                    <Play className="w-4 h-4 ml-0.5" />
                  )}
                </button>

                {/* Creator avatar */}
                <Avatar className="w-10 h-10 flex-shrink-0">
                  <AvatarImage
                    src={creator.avatar || getAvatarWithFallback(null, creator.username)}
                    alt={creator.name}
                  />
                  <AvatarFallback className="text-xs">
                    {creator.name[0]?.toUpperCase() || '?'}
                  </AvatarFallback>
                </Avatar>

                {/* Main content */}
                <div className="flex-1 min-w-0">
                  {/* Title/Description */}
                  {(sample.title || sample.description) && (
                    <div className="text-sm font-medium truncate mb-0.5">
                      {sample.title || sample.description}
                    </div>
                  )}

                  {/* Creator name */}
                  <div className="text-xs text-muted-foreground truncate mb-1">
                    {creator.name}
                  </div>

                  {/* Audio metadata */}
                  <div className="flex items-center gap-3 text-xs text-muted-foreground">
                    {sample.duration_seconds && (
                      <div className="flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        <span>{formatDuration(sample.duration_seconds)}</span>
                      </div>
                    )}
                    {sample.key && (
                      <span>{sample.key}</span>
                    )}
                    {sample.bpm && (
                      <span>{Math.round(sample.bpm)} BPM</span>
                    )}
                  </div>
                </div>

                {/* Download button */}
                <button
                  onClick={() => handleDownloadClick(sample)}
                  disabled={processing}
                  className="flex-shrink-0 w-10 h-10 rounded flex items-center justify-center hover:bg-secondary/50 active:scale-95 transition-all disabled:opacity-50"
                >
                  <Download className="w-4 h-4" />
                </button>

                {/* Favorite button */}
                <button
                  onClick={(e) => handleFavoriteToggle(sample, e)}
                  disabled={togglingFavorite === sample.id || processing}
                  className="flex-shrink-0 w-10 h-10 rounded flex items-center justify-center hover:bg-secondary/50 active:scale-95 transition-all disabled:opacity-50"
                >
                  <Heart
                    className={`w-4 h-4 ${
                      sample.is_favorited
                        ? 'fill-primary text-primary'
                        : ''
                    }`}
                  />
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {/* Download format modal */}
      <Dialog open={downloadModalOpen} onOpenChange={setDownloadModalOpen}>
        <DialogContent className="bg-[#1a1a1a] border-white/10 text-white max-w-[90vw] w-full sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="text-white">Choose Download Format</DialogTitle>
          </DialogHeader>
          <div className="space-y-3 pt-4">
            <Button
              onClick={() => handleDownload('mp3')}
              disabled={downloading}
              className="w-full bg-gradient-to-br from-[hsl(338,82%,65%)] to-[hsl(338,82%,55%)] hover:from-[hsl(338,82%,60%)] hover:to-[hsl(338,82%,50%)] text-white border-none h-14"
            >
              <div className="flex flex-col items-center">
                <div className="font-semibold">MP3 (320kbps)</div>
                <div className="text-xs opacity-80">Smaller file size, great for mobile</div>
              </div>
            </Button>
            <Button
              onClick={() => handleDownload('wav')}
              disabled={downloading}
              className="w-full bg-white/10 hover:bg-white/20 text-white border border-white/20 h-14"
            >
              <div className="flex flex-col items-center">
                <div className="font-semibold">WAV (48kHz)</div>
                <div className="text-xs opacity-80">Lossless quality for production</div>
              </div>
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}
