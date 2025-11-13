'use client';

import { useState, useEffect, useCallback } from 'react';
import { useAuth, SignInButton } from '@clerk/nextjs';
import { Heart } from 'lucide-react';
import { MobileSampleTable } from '@/components/mobile/mobile-sample-table';
import { PullToRefreshIndicator } from '@/components/mobile/pull-to-refresh-indicator';
import { Sample } from '@/types/api';
import { createAuthenticatedClient } from '@/lib/api-client';
import { useMobileAudioPlayer } from '@/contexts/audio-player-context';
import { usePullToRefresh } from '@/hooks/use-pull-to-refresh';

export default function FavoritesPage() {
  const { isSignedIn, getToken, isLoaded } = useAuth();
  const { currentSample, isPlaying, playPreview } = useMobileAudioPlayer();
  const [favorites, setFavorites] = useState<Sample[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch favorites function (extracted for reuse in refresh)
  const fetchFavorites = useCallback(async () => {
    if (!isSignedIn) {
      setIsLoading(false);
      return;
    }

    try {
      setError(null);
      const token = await getToken();
      if (!token) {
        setError('Unable to get authentication token');
        setIsLoading(false);
        return;
      }

      console.log('[FavoritesPage] API URL:', process.env.NEXT_PUBLIC_API_URL);
      const apiClient = createAuthenticatedClient(getToken);
      console.log('[FavoritesPage] Fetching favorites...');
      const data = await apiClient.get<Sample[]>('/users/me/favorites', { limit: 50 });
      console.log('[FavoritesPage] Favorites fetched:', data.length);
      setFavorites(data);
    } catch (error) {
      console.error('[FavoritesPage] Error fetching favorites:', error);
      const errorMessage = error instanceof Error ? error.message : 'Failed to load favorites';
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  }, [isSignedIn, getToken]);

  // Fetch favorites on mount
  useEffect(() => {
    // Wait for Clerk to load
    if (!isLoaded) {
      return;
    }

    fetchFavorites();
  }, [isLoaded, fetchFavorites]);

  // Pull-to-refresh functionality
  const { isRefreshing, pullDistance, isThresholdReached } = usePullToRefresh({
    onRefresh: fetchFavorites,
    enabled: isSignedIn && !isLoading && favorites.length > 0,
    threshold: 80,
  });

  // Handle when user removes a favorite
  const handleFavoriteChange = (sampleId: string, isFavorited: boolean) => {
    if (!isFavorited) {
      // Remove from local state immediately for smooth UX
      setFavorites(prev => prev.filter(fav => fav.id !== sampleId));
    }
  };

  if (!isSignedIn) {
    return (
      <div className="flex flex-col items-center justify-center h-screen text-center p-8 bg-black relative overflow-hidden">
        {/* Gradient background effect */}
        <div className="absolute inset-0 bg-gradient-to-br from-[hsl(338,82%,65%)]/5 via-transparent to-transparent" />

        <div className="relative z-10 space-y-6">
          {/* Icon with gradient background */}
          <div className="mx-auto w-24 h-24 rounded-full bg-gradient-to-br from-[hsl(338,82%,65%)]/20 to-[hsl(338,82%,65%)]/5 flex items-center justify-center backdrop-blur-sm border border-[hsl(338,82%,65%)]/20">
            <Heart className="w-12 h-12 text-[hsl(338,82%,65%)]" />
          </div>

          <div className="space-y-3">
            <h2 className="text-2xl font-bold text-white">
              Sign in to see your favorites
            </h2>
            <p className="text-gray-400 text-base max-w-sm mx-auto">
              Save samples you love and access them anytime, anywhere
            </p>
          </div>

          <SignInButton mode="modal">
            <button className="bg-gradient-to-br from-[hsl(338,82%,65%)] to-[hsl(338,82%,55%)] hover:from-[hsl(338,82%,60%)] hover:to-[hsl(338,82%,50%)] px-8 py-4 rounded-full text-white font-semibold shadow-lg shadow-[hsl(338,82%,65%)]/25 transition-all duration-200 active:scale-95">
              Sign In
            </button>
          </SignInButton>
        </div>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center h-screen bg-black">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-[hsl(338,82%,65%)]"></div>
        <p className="text-gray-400 mt-4">Loading your favorites...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-screen text-center p-8 bg-black">
        <Heart className="w-16 h-16 text-red-500 mb-4" />
        <h2 className="text-xl font-bold mb-2 text-white">
          Error loading favorites
        </h2>
        <p className="text-gray-400 mb-4">
          {error}
        </p>
        <button
          onClick={() => window.location.reload()}
          className="bg-[hsl(338,82%,65%)] hover:bg-[hsl(338,82%,55%)] px-6 py-3 rounded-lg text-white font-semibold"
        >
          Retry
        </button>
      </div>
    );
  }

  if (favorites.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-screen text-center p-8 bg-black relative overflow-hidden">
        {/* Gradient background effect */}
        <div className="absolute inset-0 bg-gradient-to-br from-[hsl(338,82%,65%)]/5 via-transparent to-transparent" />

        <div className="relative z-10 space-y-6 max-w-md">
          {/* Animated heart icon */}
          <div className="mx-auto w-24 h-24 rounded-full bg-gradient-to-br from-[hsl(338,82%,65%)]/20 to-[hsl(338,82%,65%)]/5 flex items-center justify-center backdrop-blur-sm border border-[hsl(338,82%,65%)]/20">
            <Heart className="w-12 h-12 text-gray-500" />
          </div>

          <div className="space-y-3">
            <h2 className="text-2xl font-bold text-white">
              No favorites yet
            </h2>
            <p className="text-gray-400 text-base leading-relaxed">
              Tap the <Heart className="inline w-4 h-4 mx-1 text-[hsl(338,82%,65%)]" /> button on samples to save them here
            </p>
            <p className="text-sm text-gray-500">
              Go to the Feed tab and start discovering samples!
            </p>
          </div>

          {/* Visual hint */}
          <div className="flex items-center justify-center gap-2 text-xs text-gray-500">
            <div className="w-8 h-0.5 bg-gradient-to-r from-transparent to-gray-700" />
            <span>Swipe between tabs below</span>
            <div className="w-8 h-0.5 bg-gradient-to-l from-transparent to-gray-700" />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-black">
      {/* Pull-to-refresh indicator */}
      <PullToRefreshIndicator
        pullDistance={pullDistance}
        isThresholdReached={isThresholdReached}
        isRefreshing={isRefreshing}
        threshold={80}
      />

      {/* Header */}
      <div className="sticky top-0 z-10 bg-black/95 backdrop-blur-sm border-b border-white/10 px-4 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Heart className="w-5 h-5 text-[hsl(338,82%,65%)] fill-current" />
            <h1 className="text-lg font-semibold text-white">Your Favorites</h1>
          </div>
          <div className="text-sm text-gray-400">
            {favorites.length} {favorites.length === 1 ? 'sample' : 'samples'}
          </div>
        </div>
      </div>

      {/* Content */}
      <MobileSampleTable
        samples={favorites}
        currentSample={currentSample}
        isPlaying={isPlaying}
        onSamplePreview={playPreview}
        onFavoriteChange={handleFavoriteChange}
      />
    </div>
  );
}
