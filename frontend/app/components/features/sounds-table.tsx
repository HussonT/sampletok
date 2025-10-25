import React from 'react';
import Image from 'next/image';
import { Button } from '@/components/ui/button';
import { Play, Pause, Users, Download, Video } from 'lucide-react';
import { Sample } from '@/types/api';
import { CreatorHoverCard } from '@/components/features/creator-hover-card';
import { VideoPreviewHover } from '@/components/features/video-preview-hover';
import { getAvatarWithFallback } from '@/lib/avatar';

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

  const handleDownload = (sample: Sample) => {
    // Use the backend download endpoint to avoid CORS issues
    // Backend always serves WAV files
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    const downloadUrl = `${apiUrl}/api/v1/samples/${sample.id}/download`;

    const link = document.createElement('a');
    link.href = downloadUrl;
    link.download = `${sample.creator_username || 'unknown'}_${sample.id}.wav`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    onSampleDownload?.(sample);
  };

  const handleVideoDownload = (sample: Sample) => {
    // Use the backend video download endpoint
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    const downloadUrl = `${apiUrl}/api/v1/samples/${sample.id}/download-video`;

    const link = document.createElement('a');
    link.href = downloadUrl;
    link.download = `${sample.creator_username || 'unknown'}_${sample.id}.mp4`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    onVideoDownload?.(sample);
  };

  return (
    <div className="w-full bg-background">
      <table className="w-full">
        <thead>
          <tr className="border-b border-border text-muted-foreground text-sm">
            <th className="text-left py-3 px-4 font-normal"></th>
            <th className="text-left py-3 px-4 font-normal">Sample</th>
            <th className="text-left py-3 px-4 font-normal">Creator</th>
            <th className="text-left py-3 px-4 font-normal">Waveform</th>
            <th className="text-left py-3 px-4 font-normal">Duration</th>
            <th className="text-left py-3 px-4 font-normal">Key</th>
            <th className="text-left py-3 px-4 font-normal">BPM</th>
            <th className="text-left py-3 px-4 font-normal">TikTok</th>
            <th className="text-left py-3 px-4 font-normal">Audio</th>
            <th className="text-left py-3 px-4 font-normal">Video</th>
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
                </td>
                <td className="py-3 px-4">
                  <div className="space-y-1">
                    <div className="text-sm font-medium text-foreground">
                      {sample.description ? `${sample.description.slice(0, 30)}...` : 'No description'}
                    </div>
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
                      <div className="flex items-center gap-3 cursor-pointer">
                        <Image
                          src={getAvatarWithFallback(
                            sample.tiktok_creator.avatar_thumb,
                            sample.tiktok_creator.username
                          )}
                          alt={`@${sample.tiktok_creator.username}`}
                          width={32}
                          height={32}
                          className="w-8 h-8 rounded object-cover"
                          unoptimized
                        />
                        <div className="space-y-1">
                          <div className="text-sm font-medium hover:text-primary transition-colors">
                            @{sample.tiktok_creator.username}
                          </div>
                          <div className="flex items-center gap-1 text-xs text-muted-foreground">
                            <Users className="w-3 h-3" />
                            <span>{formatFollowers(sample.tiktok_creator.follower_count)}</span>
                          </div>
                        </div>
                      </div>
                    </CreatorHoverCard>
                  ) : (
                    <div className="flex items-center gap-3">
                      <Image
                        src={getAvatarWithFallback(null, sample.creator_username || sample.id)}
                        alt={`@${sample.creator_username || 'unknown'}`}
                        width={32}
                        height={32}
                        className="w-8 h-8 rounded object-cover"
                        unoptimized
                      />
                      <div className="space-y-1">
                        <div className="text-sm font-medium">@{sample.creator_username || 'unknown'}</div>
                        <div className="flex items-center gap-1 text-xs text-muted-foreground">
                          <Users className="w-3 h-3" />
                          <span>{sample.creator_follower_count ? formatFollowers(sample.creator_follower_count) : '0 followers'}</span>
                        </div>
                      </div>
                    </div>
                  )}
                </td>
                <td className="py-1 px-4">
                  <div className="w-48 h-20 relative">
                    {sample.waveform_url ? (
                      <Image
                        src={sample.waveform_url}
                        alt="Waveform"
                        width={192}
                        height={80}
                        className="w-full h-full object-cover rounded-md"
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
                  <Button
                    variant="ghost"
                    size="sm"
                    className="p-0 w-8 h-8"
                    onClick={() => handleDownload(sample)}
                    title="Download audio sample (WAV)"
                  >
                    <Download className="w-4 h-4" />
                  </Button>
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