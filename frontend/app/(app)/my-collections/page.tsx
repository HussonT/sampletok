'use client';

import { useState, useEffect } from 'react';
import { useAuth, useUser } from '@clerk/nextjs';
import { createAuthenticatedClient } from '@/lib/api-client';
import { Collection, CollectionProcessingTaskResponse } from '@/types/api';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Loader2, FolderOpen, CheckCircle, XCircle, Clock, ChevronRight, Download, Coins } from 'lucide-react';
import { toast } from 'sonner';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import Link from 'next/link';
import { formatDistanceToNow } from 'date-fns';

export default function MyCollectionsPage() {
  const { getToken } = useAuth();
  const { user } = useUser();
  const [collections, setCollections] = useState<Collection[]>([]);
  const [loading, setLoading] = useState(true);
  const [processingId, setProcessingId] = useState<string | null>(null);
  const [userCredits, setUserCredits] = useState<number | null>(null);

  useEffect(() => {
    fetchCollections();
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
    const batchSize = Math.min(remainingVideos, 30);

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

      // Show warning if there are invalid videos
      if (response.invalid_video_count && response.invalid_video_count > 0) {
        toast.warning(
          `Note: ${response.invalid_video_count} video${response.invalid_video_count > 1 ? 's' : ''} in this collection could not be processed (deleted or private)`
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

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="w-5 h-5 text-green-500" />;
      case 'failed':
        return <XCircle className="w-5 h-5 text-destructive" />;
      case 'processing':
        return <Loader2 className="w-5 h-5 text-primary animate-spin" />;
      default:
        return <Clock className="w-5 h-5 text-muted-foreground" />;
    }
  };

  const getStatusBadge = (status: string) => {
    const variants: Record<string, 'default' | 'secondary' | 'destructive' | 'outline'> = {
      completed: 'default',
      processing: 'secondary',
      failed: 'destructive',
      pending: 'outline'
    };

    return (
      <Badge variant={variants[status] || 'outline'}>
        {status.charAt(0).toUpperCase() + status.slice(1)}
      </Badge>
    );
  };

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

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
        {collections.length > 0 ? (
          <div className="grid gap-4">
            {collections.map((collection) => (
              <Card key={collection.id} className="hover:border-primary/50 transition-colors">
                <CardContent className="p-6">
                  <div className="flex items-start gap-4">
                    {/* Collection Icon */}
                    <div className="w-16 h-16 rounded-lg flex items-center justify-center bg-primary/10 flex-shrink-0">
                      <FolderOpen className="w-8 h-8 text-primary" />
                    </div>

                    {/* Collection Info */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-start justify-between gap-2 mb-2">
                        <div>
                          <h3 className="font-semibold text-lg line-clamp-1 mb-1">
                            {collection.name}
                          </h3>
                          <p className="text-sm text-muted-foreground">
                            @{collection.tiktok_username}
                          </p>
                        </div>
                        {getStatusBadge(collection.status)}
                      </div>

                      <div className="flex items-center gap-4 text-sm text-muted-foreground mb-3">
                        <span className="flex items-center gap-1">
                          {getStatusIcon(collection.status)}
                          {collection.processed_count} / {collection.total_video_count} videos
                        </span>
                        <span>•</span>
                        <span>
                          {formatDistanceToNow(new Date(collection.created_at), { addSuffix: true })}
                        </span>
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
                            disabled={processingId === collection.id}
                          >
                            {processingId === collection.id ? (
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
                </CardContent>
              </Card>
            ))}
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
