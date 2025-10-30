'use client';

import { useState, useEffect } from 'react';
import { Download } from 'lucide-react';
import { SoundsTable } from '@/components/features/sounds-table';
import { TableLoadingSkeleton } from '@/components/ui/loading-skeletons';
import { Sample } from '@/types/api';
import { useAuth } from '@clerk/nextjs';
import { useAudioPlayer } from '../layout';
import { createAuthenticatedClient } from '@/lib/api-client';

export default function MyDownloadsPage() {
  const { getToken } = useAuth();
  const { currentSample, isPlaying, playPreview } = useAudioPlayer();
  const [downloads, setDownloads] = useState<Sample[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Fetch downloads
  useEffect(() => {
    async function fetchDownloads() {
      try {
        const token = await getToken();
        if (!token) {
          setIsLoading(false);
          return;
        }

        // Use ApiClient for proper URL handling
        const apiClient = createAuthenticatedClient(getToken);
        const data = await apiClient.get<Sample[]>('/users/me/downloads', { limit: 50 });
        setDownloads(data);
      } catch (error) {
        console.error('Error fetching downloads:', error);
      } finally {
        setIsLoading(false);
      }
    }

    fetchDownloads();
  }, [getToken]);

  // Deduplicate samples (same sample can be downloaded multiple times)
  const uniqueSamples = Array.from(
    downloads.reduce((map, sample) => {
      const existing = map.get(sample.id);
      if (!existing || (sample.downloaded_at && (!existing.downloaded_at || sample.downloaded_at > existing.downloaded_at))) {
        map.set(sample.id, sample);
      }
      return map;
    }, new Map<string, Sample>()).values()
  );

  return (
    <>
      {/* Header */}
      <div className="flex-none border-b px-6 h-16 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Download className="w-5 h-5" />
          <h1 className="text-xl font-semibold">My Downloads</h1>
        </div>
        <div className="text-sm text-muted-foreground">
          {isLoading ? '...' : `${uniqueSamples.length} unique ${uniqueSamples.length === 1 ? 'sample' : 'samples'}`}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto px-6 py-6">
        {isLoading ? (
          <TableLoadingSkeleton rows={6} />
        ) : uniqueSamples.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 text-center">
            <Download className="w-16 h-16 text-muted-foreground mb-4" />
            <h2 className="text-2xl font-semibold mb-2">No downloads yet</h2>
            <p className="text-muted-foreground mb-6 max-w-md">
              Start browsing and downloading samples to build your collection.
            </p>
          </div>
        ) : (
          <SoundsTable
            samples={uniqueSamples}
            currentSample={currentSample}
            isPlaying={isPlaying}
            onSamplePreview={playPreview}
            downloadedSamples={new Set(uniqueSamples.map(s => s.id))}
          />
        )}
      </div>
    </>
  );
}
