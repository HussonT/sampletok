'use client';

import { useState, useEffect } from 'react';
import { useAuth, useUser } from '@clerk/nextjs';
import { createAuthenticatedClient } from '@/lib/api-client';
import { Collection, CollectionProcessingTaskResponse, CollectionStatusResponse } from '@/types/api';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Loader2, FolderOpen, CheckCircle, XCircle, ChevronRight, Download, RefreshCw } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import Link from 'next/link';
import Image from 'next/image';
import { MAX_VIDEOS_PER_BATCH } from '@/lib/constants';
import { PageLoader, CardSkeleton } from '@/components/ui/loading-skeletons';
import CardSwap from '@/components/CardSwap';

export default function MyCollectionsPage() {
  const { getToken } = useAuth();
  const { user } = useUser();
  const [collections, setCollections] = useState<Collection[]>([]);
  const [loading, setLoading] = useState(true);
  const [processingId, setProcessingId] = useState<string | null>(null);
  const [syncingId, setSyncingId] = useState<string | null>(null);
  const [userCredits, setUserCredits] = useState<number | null>(null);

  useEffect(() => {
    fetchCollections();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Fetch user credits
  useEffect(() => {
    const publicCredits = user?.publicMetadata?.credits as number | undefined;
    if (publicCredits !== undefined) {
      setUserCredits(publicCredits);
    }
  }, [user]);

  const fetchCollections = async () => {
    setLoading(true);
    try {
      const api = createAuthenticatedClient(getToken);
      const data = await api.get<Collection[]>('/collections');
      setCollections(data);
    } catch (error) {
      console.error('Error fetching collections:', error);
      toast.error('Failed to load collections');
    } finally {
      setLoading(false);
    }
  };

  const handleImportNextBatch = async (collection: Collection) => {
    if (!collection.next_cursor) return;

    const remainingVideos = collection.total_video_count - collection.next_cursor;
    const batchSize = Math.min(remainingVideos, MAX_VIDEOS_PER_BATCH);

    if (userCredits !== null && userCredits < batchSize) {
      toast.error(`Insufficient credits. Need ${batchSize} credits, but have ${userCredits}`);
      return;
    }

    try {
      setProcessingId(collection.id);
      const api = createAuthenticatedClient(getToken);
      const response = await api.post<CollectionProcessingTaskResponse>(
        '/collections/process',
        {
          collection_id: collection.tiktok_collection_id,
          tiktok_username: collection.tiktok_username,
          name: collection.name,
          video_count: collection.total_video_count,
          cursor: collection.next_cursor
        }
      );

      toast.success(response.message);

      // Show warning if there are invalid toks
      if (response.invalid_video_count && response.invalid_video_count > 0) {
        toast.warning(
          `Note: ${response.invalid_video_count} tok${response.invalid_video_count > 1 ? 's' : ''} in this collection could not be processed (deleted or private)`
        );
      }

      if (userCredits !== null) {
        setUserCredits(response.remaining_credits);
      }

      // Refresh collections after a delay
      setTimeout(() => {
        fetchCollections();
        setProcessingId(null);
      }, 2000);
    } catch (error) {
      console.error('Error importing next batch:', error);
      toast.error(error instanceof Error ? error.message : 'Failed to import batch');
      setProcessingId(null);
    }
  };

  const handleSync = async (collection: Collection) => {
    try {
      setSyncingId(collection.id);
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

      if (userCredits !== null) {
        setUserCredits(response.remaining_credits);
      }

      // If no new toks or already completed, refresh immediately
      if (response.status === 'completed' || response.credits_deducted === 0) {
        fetchCollections();
        setSyncingId(null);
      } else {
        // New toks are being processed - poll for updates
        pollSyncStatus(collection.id);
      }
    } catch (error) {
      console.error('Error syncing collection:', error);
      toast.error(error instanceof Error ? error.message : 'Failed to sync collection');
      setSyncingId(null);
    }
  };

  const pollSyncStatus = async (collectionId: string) => {
    const maxPolls = 60; // Poll for up to 60 seconds
    let pollCount = 0;

    const poll = async () => {
      if (pollCount >= maxPolls) {
        setSyncingId(null);
        fetchCollections();
        return;
      }

      try {
        const api = createAuthenticatedClient(getToken);
        const status = await api.get<CollectionStatusResponse>(`/collections/${collectionId}/status`);

        if (status.status === 'completed' || status.status === 'failed') {
          setSyncingId(null);
          fetchCollections();
          return;
        }

        // Continue polling
        pollCount++;
        setTimeout(poll, 1000);
      } catch (error) {
        console.error('Error polling sync status:', error);
        setSyncingId(null);
        fetchCollections();
      }
    };

    poll();
  };

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="container mx-auto px-4 py-8 max-w-4xl">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold mb-2">My Collections</h1>
          <p className="text-muted-foreground">
            View and manage your imported TikTok collections
          </p>
        </div>

        {/* Collections List */}
        {loading ? (
          <CardSkeleton count={3} />
        ) : collections.length > 0 ? (
          <div className="grid gap-4">
            {collections.map((collection) => {
              const isSyncing = syncingId === collection.id;
              const isImporting = processingId === collection.id;
              const isProcessing = collection.status === 'processing' && !isSyncing;

              return (
                <div key={collection.id} className="py-6">
                  <div className="flex items-start gap-4">
                    {/* Collection Cover - Vertical Card (2x3 aspect ratio) with floating Sync button */}
                    <div className="w-32 h-44 flex items-center justify-center flex-shrink-0 relative" style={{ paddingBottom: '16px', paddingRight: '16px' }}>
                      <div className="absolute inset-0" style={{ width: '96px', height: '144px' }}>
                        {collection.cover_images && collection.cover_images.length > 0 ? (
                          <CardSwap
                            images={collection.cover_images}
                            alt={collection.name}
                            className="w-full h-full"
                            cycleInterval={1000}
                          />
                        ) : collection.cover_image_url ? (
                          <Image
                            src={collection.cover_image_url}
                            alt={collection.name}
                            fill
                            className="object-cover"
                            sizes="(max-width: 768px) 96px, 96px"
                          />
                        ) : (
                          <div className="flex items-center justify-center w-24 h-36 rounded-lg bg-primary/10 border border-border shadow-md">
                            <FolderOpen className="w-10 h-10 text-primary" />
                          </div>
                        )}
                      </div>

                      {/* Floating Sync button on top left of cover */}
                      {collection.status === 'completed' && (
                        <button
                          onClick={() => handleSync(collection)}
                          disabled={isSyncing || isImporting}
                          className="absolute -top-2 -left-2 z-10 p-2 rounded-full bg-background/90 backdrop-blur-sm border border-border shadow-lg hover:shadow-xl hover:bg-background transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                          style={{
                            boxShadow: '0 4px 20px rgba(0,0,0,0.3)'
                          }}
                        >
                          {isSyncing ? (
                            <Loader2 className="w-5 h-5 animate-spin text-primary" />
                          ) : (
                            <div className="relative w-5 h-5">
                              {/* Circular sync arrows - full size to match button edge */}
                              <svg className="absolute -inset-2 w-9 h-9 z-0" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                                <path d="M21 10C21 10 18.995 7.26822 17.3662 5.63824C15.7373 4.00827 13.4864 3 11 3C6.02944 3 2 7.02944 2 12C2 16.9706 6.02944 21 11 21C15.1031 21 18.5649 18.2543 19.6482 14.5M21 10V4M21 10H15" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                              </svg>
                              {/* TikTok logo in center - pink and on top */}
                              <div className="absolute inset-0 flex items-center justify-center z-10">
                                <svg className="w-[17px] h-[17px] text-pink-500" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                                  <path d="M19.59 6.69a4.83 4.83 0 01-3.77-4.25V2h-3.45v13.67a2.89 2.89 0 01-5.2 1.74 2.89 2.89 0 012.31-4.64 2.93 2.93 0 01.88.13V9.4a6.84 6.84 0 00-1-.05A6.33 6.33 0 005 20.1a6.34 6.34 0 0010.86-4.43v-7a8.16 8.16 0 004.77 1.52v-3.4a4.85 4.85 0 01-1-.1z" fill="currentColor"/>
                                </svg>
                              </div>
                            </div>
                          )}
                        </button>
                      )}
                    </div>

                    {/* Collection Info */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-start justify-between gap-2 mb-2">
                        <div className="flex-1">
                          <h3 className="font-semibold text-lg line-clamp-1 mb-1">
                            {collection.name}
                          </h3>
                          <p className="text-sm text-muted-foreground">
                            @{collection.tiktok_username}
                          </p>
                        </div>
                      </div>

                      <div className="flex items-center gap-4 text-sm text-muted-foreground mb-3">
                        {isSyncing ? (
                          <span className="flex items-center gap-1 text-primary">
                            <Loader2 className="w-4 h-4 animate-spin" />
                            Checking for new toks...
                          </span>
                        ) : isProcessing && collection.processed_count === 0 ? (
                          <span className="flex items-center gap-1 text-primary">
                            <Loader2 className="w-4 h-4 animate-spin" />
                            Preparing to process toks...
                          </span>
                        ) : isProcessing ? (
                          <span className="flex items-center gap-1 text-primary">
                            <Loader2 className="w-4 h-4 animate-spin" />
                            Processing {collection.processed_count} / {collection.total_video_count} toks
                          </span>
                        ) : collection.status === 'failed' ? (
                          <span className="flex items-center gap-1 text-destructive">
                            <XCircle className="w-4 h-4" />
                            Failed
                          </span>
                        ) : (
                          <span className="flex items-center gap-1">
                            <CheckCircle className="w-4 h-4 text-green-500" />
                            {collection.sample_count} {collection.sample_count === 1 ? 'tok' : 'toks'} imported
                          </span>
                        )}
                      </div>

                      {collection.error_message && (
                        <div className="mb-3 p-3 bg-destructive/10 border border-destructive/20 rounded-md">
                          <p className="text-sm text-destructive">{collection.error_message}</p>
                        </div>
                      )}

                      <div className="flex gap-2">
                        {collection.status === 'completed' && (
                          <Link href={`/my-collections/${collection.id}`}>
                            <Button size="sm" variant="outline">
                              View Samples
                              <ChevronRight className="w-4 h-4 ml-1" />
                            </Button>
                          </Link>
                        )}

                        {collection.has_more && collection.status === 'completed' && collection.next_cursor && (
                          <Button
                            size="sm"
                            onClick={() => handleImportNextBatch(collection)}
                            disabled={isImporting || isSyncing}
                          >
                            {isImporting ? (
                              <>
                                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                                Processing...
                              </>
                            ) : (
                              <>
                                <Download className="w-4 h-4 mr-2" />
                                Import Next 30
                              </>
                            )}
                          </Button>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          /* Empty State */
          <Card>
            <CardContent className="flex flex-col items-center justify-center py-16">
              <FolderOpen className="w-16 h-16 text-muted-foreground mb-4" />
              <h3 className="text-lg font-semibold mb-2">No Collections Yet</h3>
              <p className="text-sm text-muted-foreground text-center max-w-md mb-4">
                You haven&apos;t imported any TikTok collections yet. Start by searching for a creator&apos;s collections.
              </p>
              <Link href="/tiktok-connect">
                <Button>
                  Import Collection
                </Button>
              </Link>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
