'use client';

import { VideoFeed } from '@/components/mobile/video-feed';
import { useSampleQueue } from '@/hooks/use-sample-queue';
import { useAuth } from '@clerk/nextjs';
import { useState, useEffect, useCallback } from 'react';
import { createAuthenticatedClient, publicApi } from '@/lib/api-client';
import { Loader2 } from 'lucide-react';

export default function MobileFeedPage() {
  const { isSignedIn, getToken } = useAuth();
  const [apiClient, setApiClient] = useState(publicApi);

  // Create authenticated API client when user is signed in
  useEffect(() => {
    if (isSignedIn && getToken) {
      setApiClient(createAuthenticatedClient(getToken));
    } else {
      setApiClient(publicApi);
    }
  }, [isSignedIn, getToken]);

  const {
    samples,
    loadMore,
    hasMore,
    isLoading,
    reset,
  } = useSampleQueue({ apiClient });

  // Handle favorite change (optimistic update in feed component)
  const handleFavoriteChange = useCallback((sampleId: string, isFavorited: boolean) => {
    // The VideoFeedItem component handles the API call and optimistic update
    // This callback can be used for additional tracking if needed
    console.log(`Sample ${sampleId} favorited: ${isFavorited}`);
  }, []);

  // Loading state (initial load)
  if (isLoading && samples.length === 0) {
    return (
      <div className="flex items-center justify-center h-screen bg-[hsl(0,0%,17%)]">
        <div className="text-center">
          <Loader2 className="w-12 h-12 animate-spin text-[hsl(338,82%,65%)] mx-auto mb-4" />
          <p className="text-gray-400">Loading samples...</p>
        </div>
      </div>
    );
  }

  // No samples state
  if (!isLoading && samples.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-screen bg-[hsl(0,0%,17%)] p-6 text-center">
        <div className="max-w-md space-y-6">
          <span className="text-6xl mb-4">🎵</span>
          <h2 className="text-2xl font-bold text-white mb-2">
            No samples yet
          </h2>
          <p className="text-gray-400 mb-6">
            Check back later for new samples!
          </p>
        </div>
      </div>
    );
  }

  return (
    <VideoFeed
      samples={samples}
      onLoadMore={loadMore}
      hasMore={hasMore}
      isLoading={isLoading}
      onFavoriteChange={handleFavoriteChange}
    />
  );
}
