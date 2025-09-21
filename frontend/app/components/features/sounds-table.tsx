import React from 'react';
import { Button } from '@/components/ui/button';
import { Play, Pause, ExternalLink, Users, Download } from 'lucide-react';
import { Sample } from '@/types/api';

interface SoundsTableProps {
  samples: Sample[];
  currentSample?: Sample | null;
  isPlaying?: boolean;
  downloadedSamples?: Set<string>;
  onSamplePreview?: (sample: Sample) => void;
  onSampleDownload?: (sample: Sample) => void;
}

export function SoundsTable({
  samples,
  currentSample,
  isPlaying = false,
  onSamplePreview,
  onSampleDownload
}: SoundsTableProps) {

  const formatDuration = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toFixed(1)}`;
  };

  const formatBPM = (sample: Sample): number => {
    const idCode = sample.id.charCodeAt(0) || 65;
    return 100 + (idCode % 50);
  };

  const getKey = (sample: Sample): string => {
    const keys = ['C#', 'D', 'D#', 'F', 'F#', 'G', 'G#', 'A'];
    const modes = ['maj', 'min'];
    const keyIndex = sample.id.charCodeAt(0) % keys.length;
    const modeIndex = (sample.creator_username || 'A').charCodeAt(0) % modes.length;
    return `${keys[keyIndex]} ${modes[modeIndex]}`;
  };

  const formatFollowers = (count: number): string => {
    if (count >= 1000000) {
      return `${(count / 1000000).toFixed(1)}M followers`;
    } else if (count >= 1000) {
      return `${(count / 1000).toFixed(1)}K followers`;
    }
    return `${count} followers`;
  };

  const getCategories = (_sample: Sample): string[] => {
    const allCategories = ['drums', 'trance'];
    return allCategories;
  };

  const handleDragStart = (e: React.DragEvent, sample: Sample) => {
    e.dataTransfer.setData('application/json', JSON.stringify(sample));
    e.dataTransfer.effectAllowed = 'copy';
  };

  const handleDownload = (sample: Sample) => {
    const link = document.createElement('a');
    link.href = sample.audio_url_mp3 || sample.audio_url_wav || '#';
    link.download = `${sample.creator_username || 'unknown'}_${sample.id}.mp3`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    onSampleDownload?.(sample);
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
            <th className="text-left py-3 px-4 font-normal">Download</th>
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
                    <div className="flex gap-2">
                      {getCategories(sample).map((cat) => (
                        <span key={cat} className="bg-secondary text-secondary-foreground px-2 py-0.5 rounded text-xs">
                          {cat}
                        </span>
                      ))}
                    </div>
                  </div>
                </td>
                <td className="py-3 px-4">
                  <div className="space-y-1">
                    <div className="text-sm font-medium">@{sample.creator_username || 'unknown'}</div>
                    <div className="flex items-center gap-1 text-xs text-muted-foreground">
                      <Users className="w-3 h-3" />
                      <span>{sample.view_count ? `${(sample.view_count / 1000).toFixed(0)}k views` : 'No views'}</span>
                    </div>
                  </div>
                </td>
                <td className="py-3 px-4">
                  <div className="w-24 h-8">
                    <svg className="w-full h-full" viewBox="0 0 100 32">
                      {Array.from({ length: 50 }).map((_, i) => {
                        // Generate deterministic height based on sample ID and position
                        const seed = sample.id.charCodeAt(0) + sample.id.charCodeAt(sample.id.length - 1) + i;
                        const height = ((seed * 9.7) % 28) + 4;
                        const y = (32 - height) / 2;
                        return (
                          <rect
                            key={i}
                            x={i * 2}
                            y={y}
                            width="1.5"
                            height={height}
                            fill="currentColor"
                            className="text-muted-foreground"
                          />
                        );
                      })}
                    </svg>
                  </div>
                </td>
                <td className="py-3 px-4 text-sm text-muted-foreground">
                  {formatDuration(sample.duration)}
                </td>
                <td className="py-3 px-4 text-sm">
                  {getKey(sample)}
                </td>
                <td className="py-3 px-4 text-sm">
                  {formatBPM(sample)}
                </td>
                <td className="py-3 px-4">
                  <a
                    href={sample.tiktok_url || '#'}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-primary hover:text-primary/80 underline text-sm flex items-center gap-1"
                  >
                    View on TikTok
                    <ExternalLink className="w-3 h-3" />
                  </a>
                </td>
                <td className="py-3 px-4">
                  <Button
                    variant="ghost"
                    size="sm"
                    className="p-0 w-8 h-8"
                    onClick={() => handleDownload(sample)}
                    title="Download sample"
                  >
                    <Download className="w-4 h-4" />
                  </Button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}