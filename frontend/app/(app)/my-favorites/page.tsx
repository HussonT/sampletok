'use client';

import { useState, useEffect } from 'react';
import { Heart } from 'lucide-react';
import { SoundsTable } from '@/components/features/sounds-table';
import { TableLoadingSkeleton } from '@/components/ui/loading-skeletons';
import { Sample } from '@/types/api';
import { useAuth } from '@clerk/nextjs';
import { useAudioPlayer } from '../layout';

export default function MyFavoritesPage() {
  const { getToken } = useAuth();
  const { currentSample, isPlaying, playPreview } = useAudioPlayer();
  const [favorites, setFavorites] = useState<Sample[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Fetch favorites function
  const fetchFavorites = async () => {
    try {
      const token = await getToken();
      if (!token) {
        setIsLoading(false);
        return;
      }

      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/api/v1/users/me/favorites?limit=50`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        console.error('Failed to fetch favorites:', response.status, response.statusText);
        setIsLoading(false);
        return;
      }

      const data = await response.json();
      setFavorites(data);
    } catch (error) {
      console.error('Error fetching favorites:', error);
    } finally {
      setIsLoading(false);
    }
  };

  // Fetch favorites on mount
  useEffect(() => {
    fetchFavorites();
  }, [getToken]);

  // Handle favorite removal
  const handleFavoriteToggle = (sampleId: string, isFavorited: boolean) => {
    if (!isFavorited) {
      // Remove from local state immediately for smooth UX
      setFavorites(prev => prev.filter(fav => fav.id !== sampleId));
    }
  };

  // Deduplicate samples (should be unique by design, but add safety check)
  const uniqueFavorites = Array.from(
    favorites.reduce((map, sample) => {
      const existing = map.get(sample.id);
      if (!existing || (sample.favorited_at && (!existing.favorited_at || sample.favorited_at > existing.favorited_at))) {
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
          <Heart className="w-5 h-5 text-red-500 fill-current" />
          <h1 className="text-xl font-semibold">My Favorites</h1>
        </div>
        <div className="text-sm text-muted-foreground">
          {isLoading ? '...' : `${uniqueFavorites.length} ${uniqueFavorites.length === 1 ? 'sample' : 'samples'}`}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto px-6 py-6">
        {isLoading ? (
          <TableLoadingSkeleton rows={6} />
        ) : uniqueFavorites.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 text-center">
            <Heart className="w-16 h-16 text-muted-foreground mb-4" />
            <h2 className="text-2xl font-semibold mb-2">No favorites yet</h2>
            <p className="text-muted-foreground mb-6 max-w-md">
              Discover samples you love and save them to your favorites for easy access.
            </p>
          </div>
        ) : (
          <SoundsTable
            samples={uniqueFavorites}
            currentSample={currentSample}
            isPlaying={isPlaying}
            onSamplePreview={playPreview}
            onFavoriteChange={handleFavoriteToggle}
          />
        )}
      </div>
    </>
  );
}
