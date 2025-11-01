'use client';

import { useState, useEffect } from 'react';
import { useAuth, useUser } from '@clerk/nextjs';
import { createAuthenticatedClient, publicApi } from '@/lib/api-client';
import {
  TikTokCollectionItem,
  TikTokCollectionListResponse,
  CollectionProcessingTaskResponse,
  CollectionStatusResponse
} from '@/types/api';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Loader2, Search, FolderOpen, Check, Download, AlertCircle, Coins } from 'lucide-react';
import { toast } from 'sonner';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { MAX_VIDEOS_PER_BATCH, getPollingInterval } from '@/lib/constants';
import { CardSkeleton } from '@/components/ui/loading-skeletons';

export default function TikTokConnectPage() {
  const { getToken, isSignedIn } = useAuth();
  const { user } = useUser();
  const [username, setUsername] = useState('');
  const [loading, setLoading] = useState(false);
  const [collections, setCollections] = useState<TikTokCollectionItem[]>([]);
  const [fetchedUsername, setFetchedUsername] = useState<string | null>(null);
  const [processingCollectionId, setProcessingCollectionId] = useState<string | null>(null);
  const [processingStatus, setProcessingStatus] = useState<CollectionStatusResponse | null>(null);
  const [userCredits, setUserCredits] = useState<number | null>(null);

  // Poll for processing status with exponential backoff
  useEffect(() => {
    if (!processingCollectionId) return;

    let intervalId: NodeJS.Timeout;
    let pollCount = 0;

    const pollStatus = async () => {
      try {
        const api = createAuthenticatedClient(getToken);
        const status = await api.get<CollectionStatusResponse>(
          `/collections/${processingCollectionId}/status`
        );
        setProcessingStatus(status);

        // Stop polling if completed or failed
        if (status.status === 'completed' || status.status === 'failed') {
          if (intervalId) clearInterval(intervalId);
          setProcessingCollectionId(null);
          setProcessingStatus(null);  // Clear the status to hide the card
          if (status.status === 'completed') {
            toast.success(`Collection processed! ${status.processed_count} toks ready.`);
          } else {
            toast.error(`Processing failed: ${status.error_message || 'Unknown error'}`);
          }
        } else {
          // Schedule next poll with exponential backoff
          pollCount++;
          const nextDelay = getPollingInterval(pollCount);
          if (intervalId) clearInterval(intervalId);
          intervalId = setTimeout(pollStatus, nextDelay);
        }
      } catch (error) {
        console.error('Error polling status:', error);
        // On error, retry with current backoff schedule
        pollCount++;
        const nextDelay = getPollingInterval(pollCount);
        if (intervalId) clearInterval(intervalId);
        intervalId = setTimeout(pollStatus, nextDelay);
      }
    };

    // Start polling immediately
    pollStatus();

    return () => {
      if (intervalId) clearInterval(intervalId);
    };
  }, [processingCollectionId, getToken]);

  // Exponential backoff: 3s → 5s → 10s → 30s (then stays at 30s)

  // Fetch user credits if signed in
  useEffect(() => {
    if (isSignedIn) {
      const publicCredits = user?.publicMetadata?.credits as number | undefined;
      if (publicCredits !== undefined) {
        setUserCredits(publicCredits);
      }
    }
  }, [isSignedIn, user]);

  const handleFetchCollections = async () => {
    if (!username.trim()) {
      toast.error('Please enter a TikTok username');
      return;
    }

    setLoading(true);
    setCollections([]);
    setFetchedUsername(null);

    try {
      // Use public API since this endpoint doesn't require auth
      const response = await publicApi.get<TikTokCollectionListResponse>(
        `/collections/tiktok/${username.trim()}`
      );

      setCollections(response.collection_list);
      setFetchedUsername(username.trim());

      if (response.collection_list.length === 0) {
        toast.info('No public collections found for this user');
      } else {
        toast.success(`Found ${response.collection_list.length} collection(s)`);
      }
    } catch (error) {
      console.error('Error fetching collections:', error);
      toast.error(error instanceof Error ? error.message : 'Failed to fetch collections');
    } finally {
      setLoading(false);
    }
  };

  const handleProcessCollection = async (collection: TikTokCollectionItem, cursor: number = 0) => {
    if (!isSignedIn) {
      toast.error('Please sign in to process collections');
      return;
    }

    if (!fetchedUsername) {
      toast.error('Username not found');
      return;
    }

    // Calculate how many toks will be in this batch
    const remainingVideos = collection.video_count - cursor;
    const batchSize = Math.min(remainingVideos, MAX_VIDEOS_PER_BATCH);

    // Check credits
    if (userCredits !== null && userCredits < batchSize) {
      toast.error(`Insufficient credits. Need ${batchSize} credits, but have ${userCredits}`);
      return;
    }

    try {
      const api = createAuthenticatedClient(getToken);
      const response = await api.post<CollectionProcessingTaskResponse>(
        '/collections/process',
        {
          collection_id: collection.id,
          tiktok_username: fetchedUsername,
          name: collection.name,
          video_count: collection.video_count,
          cursor: cursor
        }
      );

      toast.success(response.message);

      // Show warning if there are invalid toks
      if (response.invalid_video_count && response.invalid_video_count > 0) {
        toast.warning(
          `Note: ${response.invalid_video_count} tok${response.invalid_video_count > 1 ? 's' : ''} in this collection could not be processed (deleted or private)`
        );
      }

      setProcessingCollectionId(response.collection_id);

      // Update user credits
      if (userCredits !== null) {
        setUserCredits(response.remaining_credits);
      }
    } catch (error) {
      console.error('Error processing collection:', error);
      toast.error(error instanceof Error ? error.message : 'Failed to process collection');
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !loading) {
      handleFetchCollections();
    }
  };

  const getCreditsRequired = (videoCount: number) => Math.min(videoCount, MAX_VIDEOS_PER_BATCH);

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="container mx-auto px-4 py-8 max-w-4xl">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-2">
            <h1 className="text-3xl font-bold">Import TikTok Collection</h1>
            {isSignedIn && userCredits !== null && (
              <Badge variant="secondary" className="flex items-center gap-1">
                <Coins className="w-4 h-4" />
                {userCredits} credits
              </Badge>
            )}
          </div>
          <p className="text-muted-foreground">
            Browse any TikTok user&apos;s public collections and import them to your library
          </p>
        </div>

        {/* Processing Status */}
        {processingStatus && (
          <Card className="mb-6 border-primary">
            <CardContent className="pt-6">
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Loader2 className="w-4 h-4 animate-spin text-primary" />
                    <span className="font-medium">Processing Collection</span>
                  </div>
                  <span className="text-sm text-muted-foreground">
                    {processingStatus.processed_count} / {processingStatus.total_video_count} toks
                  </span>
                </div>
                <Progress value={processingStatus.progress} />
                <p className="text-sm text-muted-foreground">{processingStatus.message}</p>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Username Input Card */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle>Enter TikTok Username</CardTitle>
            <CardDescription>
              Enter a TikTok username to view their public collections
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex gap-2">
              <div className="flex-1 relative">
                <div className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">
                  @
                </div>
                <Input
                  type="text"
                  placeholder="username"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  onKeyPress={handleKeyPress}
                  disabled={loading}
                  className="pl-7"
                />
              </div>
              <Button
                onClick={handleFetchCollections}
                disabled={loading || !username.trim()}
              >
                {loading ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Loading...
                  </>
                ) : (
                  <>
                    <Search className="w-4 h-4 mr-2" />
                    Search
                  </>
                )}
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Collections List */}
        {fetchedUsername && (
          <div className="mb-4">
            <h2 className="text-xl font-semibold mb-4">
              Collections from @{fetchedUsername}
            </h2>
          </div>
        )}

        {loading && fetchedUsername && (
          <CardSkeleton count={2} />
        )}

        {!loading && collections.length > 0 && (
          <div className="grid gap-4">
            {collections.map((collection) => {
              const creditsRequired = getCreditsRequired(collection.video_count);
              const canAfford = userCredits === null || userCredits >= creditsRequired;

              return (
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
                          <h3 className="font-semibold text-lg line-clamp-1">
                            {collection.name}
                          </h3>
                        </div>

                        <div className="flex items-center gap-4 text-sm text-muted-foreground mb-3">
                          <span>{collection.video_count} toks</span>
                          <span>•</span>
                          <span className="flex items-center gap-1">
                            <Coins className="w-3 h-3" />
                            {creditsRequired} credit{creditsRequired !== 1 ? 's' : ''}
                            {collection.video_count > MAX_VIDEOS_PER_BATCH && ` (max ${MAX_VIDEOS_PER_BATCH} toks)`}
                          </span>
                        </div>

                        {!isSignedIn ? (
                          <p className="text-sm text-muted-foreground flex items-center gap-1">
                            <AlertCircle className="w-4 h-4" />
                            Sign in to import this collection
                          </p>
                        ) : !canAfford ? (
                          <p className="text-sm text-destructive flex items-center gap-1">
                            <AlertCircle className="w-4 h-4" />
                            Insufficient credits
                          </p>
                        ) : (
                          <Button
                            size="sm"
                            onClick={() => handleProcessCollection(collection)}
                            disabled={!!processingCollectionId}
                          >
                            <Download className="w-4 h-4 mr-2" />
                            Import Collection
                          </Button>
                        )}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}

        {/* Empty State */}
        {!loading && collections.length === 0 && fetchedUsername && (
          <Card>
            <CardContent className="flex flex-col items-center justify-center py-12">
              <FolderOpen className="w-16 h-16 text-muted-foreground mb-4" />
              <h3 className="text-lg font-semibold mb-2">No Collections Found</h3>
              <p className="text-sm text-muted-foreground text-center max-w-md">
                @{fetchedUsername} doesn&apos;t have any public collections yet.
              </p>
            </CardContent>
          </Card>
        )}

        {/* Info Card */}
        {!fetchedUsername && !loading && (
          <Card className="bg-muted/50">
            <CardContent className="py-8">
              <div className="flex items-start gap-4">
                <div className="p-2 bg-primary/10 rounded-lg">
                  <FolderOpen className="w-6 h-6 text-primary" />
                </div>
                <div>
                  <h3 className="font-semibold mb-2">How it works</h3>
                  <ol className="text-sm text-muted-foreground space-y-2 list-decimal list-inside">
                    <li>Enter a TikTok username to browse their collections</li>
                    <li>Review collections and credit costs (1 credit per tok)</li>
                    <li>Click &quot;Import Collection&quot; to start processing</li>
                    <li>All toks will be available in your collection library</li>
                  </ol>
                </div>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
