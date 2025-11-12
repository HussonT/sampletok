'use client';

import { useState, useEffect } from 'react';
import { useAuth, useUser } from '@clerk/nextjs';
import { useParams, useRouter } from 'next/navigation';
import { createAuthenticatedClient } from '@/lib/api-client';
import { CollectionWithSamples, CollectionProcessingTaskResponse, CollectionStatusResponse } from '@/types/api';
import { FolderOpen, ChevronLeft, Music, RefreshCw, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { SoundsTable } from '@/components/features/sounds-table';
import { useDesktopAudioPlayer } from '@/contexts/desktop-audio-player-context';
import Link from 'next/link';
import { TableLoadingSkeleton } from '@/components/ui/loading-skeletons';

export default function CollectionDetailPage() {
  const { getToken } = useAuth();
  const { user } = useUser();
  const params = useParams();
  const router = useRouter();
  const collectionId = params.id as string;
  const { currentSample, isPlaying, playPreview } = useDesktopAudioPlayer();

  const [collection, setCollection] = useState<CollectionWithSamples | null>(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);

  useEffect(() => {
    fetchCollection();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [collectionId]);

  const fetchCollection = async () => {
    setLoading(true);
    try {
      const api = createAuthenticatedClient(getToken);
      const data = await api.get<CollectionWithSamples>(`/collections/${collectionId}`);
      setCollection(data);
    } catch (error) {
      console.error('Error fetching collection:', error);
      toast.error('Failed to load collection');
      router.push('/my-collections');
    } finally {
      setLoading(false);
    }
  };

  const handleSync = async () => {
    if (!collection) return;

    try {
      setSyncing(true);
      toast.info('Checking for new toks...');

      const api = createAuthenticatedClient(getToken);

      // Request to sync from the beginning (cursor=0) to check for new toks
      const response = await api.post<CollectionProcessingTaskResponse>(
        '/collections/process',
        {
          collection_id: collection.tiktok_collection_id,
          tiktok_username: collection.tiktok_username,
          name: collection.name,
          video_count: collection.total_video_count,
          cursor: 0  // Start from beginning to detect new toks
        }
      );

      toast.success(response.message);

      // Show warning if there are invalid toks
      if (response.invalid_video_count && response.invalid_video_count > 0) {
        toast.warning(
          `Note: ${response.invalid_video_count} tok${response.invalid_video_count > 1 ? 's' : ''} could not be processed (deleted or private)`
        );
      }

      // If no new toks or already completed, refresh immediately
      if (response.status === 'completed' || response.credits_deducted === 0) {
        fetchCollection();
        setSyncing(false);
      } else {
        // New toks are being processed - poll for updates
        pollSyncStatus();
      }
    } catch (error) {
      console.error('Error syncing collection:', error);
      toast.error(error instanceof Error ? error.message : 'Failed to sync collection');
      setSyncing(false);
    }
  };

  const pollSyncStatus = async () => {
    const maxPolls = 60; // Poll for up to 60 seconds
    let pollCount = 0;

    const poll = async () => {
      if (pollCount >= maxPolls) {
        setSyncing(false);
        fetchCollection();
        return;
      }

      try {
        const api = createAuthenticatedClient(getToken);
        const status = await api.get<CollectionStatusResponse>(`/collections/${collectionId}/status`);

        if (status.status === 'completed' || status.status === 'failed') {
          setSyncing(false);
          fetchCollection();
          return;
        }

        // Continue polling
        pollCount++;
        setTimeout(poll, 1000);
      } catch (error) {
        console.error('Error polling sync status:', error);
        setSyncing(false);
        fetchCollection();
      }
    };

    poll();
  };

  return (
    <>
      {/* Header */}
      <div className="flex-none border-b border-border px-6 py-4">
        <Link href="/my-collections">
          <Button variant="ghost" size="sm" className="mb-3">
            <ChevronLeft className="w-4 h-4 mr-1" />
            Back to Collections
          </Button>
        </Link>

        <div className="flex items-start justify-between gap-4">
          <div className="flex items-start gap-4">
            <div className="w-12 h-12 rounded-lg flex items-center justify-center bg-primary/10 flex-shrink-0">
              <FolderOpen className="w-6 h-6 text-primary" />
            </div>
            <div className="flex-1">
              <h1 className="text-2xl font-bold mb-1">{loading ? '...' : collection?.name}</h1>
              <div className="flex items-center gap-3 text-sm text-muted-foreground">
                <span>@{loading ? '...' : collection?.tiktok_username}</span>
                {!loading && collection && (
                  <>
                    <span>•</span>
                    <Badge variant="secondary">
                      {collection.samples.length} {collection.samples.length === 1 ? 'sample' : 'samples'}
                    </Badge>
                  </>
                )}
              </div>
            </div>
          </div>
          {!loading && collection && (
            <Button
              size="sm"
              variant="outline"
              onClick={handleSync}
              disabled={syncing}
            >
              {syncing ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Syncing...
                </>
              ) : (
                <>
                  <RefreshCw className="w-4 h-4 mr-2" />
                  Sync
                </>
              )}
            </Button>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto px-6 py-6">
        {loading ? (
          <TableLoadingSkeleton rows={6} />
        ) : !collection ? null : collection.samples.length > 0 ? (
          <SoundsTable
            samples={collection.samples}
            currentSample={currentSample}
            isPlaying={isPlaying}
            onSamplePreview={playPreview}
          />
        ) : (
          <div className="flex flex-col items-center justify-center py-20 text-center">
            <Music className="w-16 h-16 text-muted-foreground mb-4" />
            <h2 className="text-2xl font-semibold mb-2">No Samples Yet</h2>
            <p className="text-muted-foreground mb-6 max-w-md">
              This collection is still being processed or no samples were found.
            </p>
          </div>
        )}
      </div>
    </>
  );
}
