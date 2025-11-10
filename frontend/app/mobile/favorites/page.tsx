'use client';

import { useState, useEffect } from 'react';
import { useAuth, SignInButton } from '@clerk/nextjs';
import { Heart } from 'lucide-react';
import { MobileSampleTable } from '@/components/mobile/mobile-sample-table';
import { Sample } from '@/types/api';
import { createAuthenticatedClient } from '@/lib/api-client';
import { useAudioPlayer } from '../layout';

export default function FavoritesPage() {
  const { isSignedIn, getToken, isLoaded } = useAuth();
  const { currentSample, isPlaying, playPreview } = useAudioPlayer();
  const [favorites, setFavorites] = useState<Sample[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch favorites on mount
  useEffect(() => {
    // Wait for Clerk to load
    if (!isLoaded) {
      return;
    }

    if (!isSignedIn) {
      setIsLoading(false);
      return;
    }

    const fetchFavorites = async () => {
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
    };

    fetchFavorites();
  }, [isSignedIn, isLoaded, getToken]);

  // Handle when user removes a favorite
  const handleFavoriteChange = (sampleId: string, isFavorited: boolean) => {
    if (!isFavorited) {
      // Remove from local state immediately for smooth UX
      setFavorites(prev => prev.filter(fav => fav.id !== sampleId));
    }
  };

  if (!isSignedIn) {
    return (
      <div className="flex flex-col items-center justify-center h-screen text-center p-8 bg-black">
        <Heart className="w-16 h-16 text-gray-600 mb-4" />
        <h2 className="text-xl font-bold mb-2 text-white">
          Sign in to see your favorites
        </h2>
        <p className="text-gray-400 mb-6">
          Save samples you love and access them anytime
        </p>
        <SignInButton mode="modal">
          <button className="bg-green-600 hover:bg-green-700 px-6 py-3 rounded-lg text-white font-semibold">
            Sign In
          </button>
        </SignInButton>
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
      <div className="flex flex-col items-center justify-center h-screen text-center p-8 bg-black">
        <Heart className="w-16 h-16 text-gray-600 mb-4" />
        <h2 className="text-xl font-bold mb-2 text-white">
          No favorites yet
        </h2>
        <p className="text-gray-400 mb-2">
          Favorites will appear here when you tap the heart button on samples
        </p>
        <p className="text-sm text-gray-500">
          Go to the Feed tab and start discovering samples!
        </p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-black">
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
