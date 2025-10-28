'use client';

import { useState, useEffect } from 'react';
import { useAuth } from '@clerk/nextjs';
import { useParams, useRouter } from 'next/navigation';
import { createAuthenticatedClient } from '@/lib/api-client';
import { CollectionWithSamples } from '@/types/api';
import { Loader2, FolderOpen, ChevronLeft, Music } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { SoundsTable } from '@/components/features/sounds-table';
import { useAudioPlayer } from '../../layout';
import Link from 'next/link';

export default function CollectionDetailPage() {
  const { getToken } = useAuth();
  const params = useParams();
  const router = useRouter();
  const collectionId = params.id as string;
  const { currentSample, isPlaying, playPreview } = useAudioPlayer();

  const [collection, setCollection] = useState<CollectionWithSamples | null>(null);
  const [loading, setLoading] = useState(true);

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

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!collection) {
    return null;
  }

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

        <div className="flex items-start gap-4">
          <div className="w-12 h-12 rounded-lg flex items-center justify-center bg-primary/10 flex-shrink-0">
            <FolderOpen className="w-6 h-6 text-primary" />
          </div>
          <div className="flex-1">
            <h1 className="text-2xl font-bold mb-1">{collection.name}</h1>
            <div className="flex items-center gap-3 text-sm text-muted-foreground">
              <span>@{collection.tiktok_username}</span>
              <span>•</span>
              <Badge variant="secondary">
                {collection.samples.length} {collection.samples.length === 1 ? 'sample' : 'samples'}
              </Badge>
            </div>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto px-6 py-6">
        {collection.samples.length > 0 ? (
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
