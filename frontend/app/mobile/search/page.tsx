'use client';

import { useState, useEffect, useCallback, useMemo } from 'react';
import { useAuth } from '@clerk/nextjs';
import { Search, X, SlidersHorizontal, TrendingUp, Clock } from 'lucide-react';
import { MobileSampleTable } from '@/components/mobile/mobile-sample-table';
import { Sample } from '@/types/api';
import { createAuthenticatedClient, publicApi } from '@/lib/api-client';
import { useAudioPlayer } from '../layout';
import { useHapticFeedback } from '@/hooks/use-haptics';

// Musical keys for filter
const MUSICAL_KEYS = [
  'C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B',
  'Cm', 'C#m', 'Dm', 'D#m', 'Em', 'Fm', 'F#m', 'Gm', 'G#m', 'Am', 'A#m', 'Bm'
];

// BPM ranges
const BPM_RANGES = [
  { label: 'Slow (60-90)', min: 60, max: 90 },
  { label: 'Mid (90-120)', min: 90, max: 120 },
  { label: 'Up (120-140)', min: 120, max: 140 },
  { label: 'Fast (140-180)', min: 140, max: 180 },
];

// Genre tags - Commented out until backend supports genre filtering
// const GENRES = [
//   'Hip-Hop', 'Pop', 'Electronic', 'Rock', 'R&B', 'Dance', 'Trap', 'House'
// ];

interface SearchFilters {
  bpm_min?: number;
  bpm_max?: number;
  key?: string;
  // genre?: string; // Removed until backend supports it
}

interface RecentSearch {
  query: string;
  timestamp: number;
}

export default function SearchPage() {
  const { isSignedIn, getToken, isLoaded } = useAuth();
  const { currentSample, isPlaying, playPreview } = useAudioPlayer();
  const { onMedium, onLight } = useHapticFeedback();

  // Search state
  const [searchQuery, setSearchQuery] = useState('');
  const [debouncedQuery, setDebouncedQuery] = useState('');
  const [filters, setFilters] = useState<SearchFilters>({});
  const [showFilters, setShowFilters] = useState(false);

  // Results state
  const [samples, setSamples] = useState<Sample[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasSearched, setHasSearched] = useState(false);

  // Recent searches
  const [recentSearches, setRecentSearches] = useState<RecentSearch[]>([]);

  // Load recent searches from localStorage
  useEffect(() => {
    try {
      const stored = localStorage.getItem('recentSearches');
      if (stored) {
        const parsed = JSON.parse(stored);
        setRecentSearches(parsed);
      }
    } catch (error) {
      console.error('Error loading recent searches:', error);
    }
  }, []);

  // Debounce search query
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedQuery(searchQuery);
    }, 400);

    return () => clearTimeout(timer);
  }, [searchQuery]);

  // Save recent search
  const saveRecentSearch = useCallback((query: string) => {
    if (!query.trim()) return;

    const newSearch: RecentSearch = {
      query: query.trim(),
      timestamp: Date.now(),
    };

    setRecentSearches((prev) => {
      // Remove duplicates and add to front
      const filtered = prev.filter(s => s.query.toLowerCase() !== query.toLowerCase());
      const updated = [newSearch, ...filtered].slice(0, 10); // Keep max 10

      // Save to localStorage
      try {
        localStorage.setItem('recentSearches', JSON.stringify(updated));
      } catch (error) {
        console.error('Error saving recent searches:', error);
      }

      return updated;
    });
  }, []);

  // Perform search
  const performSearch = useCallback(async () => {
    if (!debouncedQuery.trim() && Object.keys(filters).length === 0) {
      setSamples([]);
      setHasSearched(false);
      return;
    }

    setIsLoading(true);
    setError(null);
    setHasSearched(true);

    try {
      const params: any = {
        limit: 20, // Backend max is 20
        skip: 0,
      };

      if (debouncedQuery.trim()) {
        params.search = debouncedQuery.trim();
        saveRecentSearch(debouncedQuery.trim());
      }

      if (filters.bpm_min) params.bpm_min = filters.bpm_min;
      if (filters.bpm_max) params.bpm_max = filters.bpm_max;
      if (filters.key) params.key = filters.key;
      // Genre filter removed until backend supports it
      // if (filters.genre) params.genre = filters.genre;

      // Use authenticated client if signed in, otherwise public
      let apiClient;
      if (isSignedIn && getToken) {
        apiClient = createAuthenticatedClient(getToken);
      } else {
        apiClient = publicApi;
      }

      const response = await apiClient.get<{ items: Sample[]; total: number; has_more: boolean }>('/samples', params);
      setSamples(response.items || []);
    } catch (error) {
      console.error('Search error:', error);
      setError(error instanceof Error ? error.message : 'Search failed');
    } finally {
      setIsLoading(false);
    }
  }, [debouncedQuery, filters, isSignedIn, getToken, saveRecentSearch]);

  // Trigger search when debounced query or filters change
  useEffect(() => {
    if (isLoaded) {
      performSearch();
    }
  }, [debouncedQuery, filters, isLoaded, performSearch]);

  // Clear search
  const handleClearSearch = () => {
    onLight();
    setSearchQuery('');
    setDebouncedQuery('');
    setFilters({});
    setSamples([]);
    setHasSearched(false);
  };

  // Handle recent search click
  const handleRecentSearchClick = (query: string) => {
    onMedium();
    setSearchQuery(query);
  };

  // Clear recent searches
  const handleClearRecentSearches = () => {
    onLight();
    setRecentSearches([]);
    localStorage.removeItem('recentSearches');
  };

  // Toggle filter
  const toggleFilter = (type: 'bpm' | 'key', value: any) => {
    onMedium();
    setFilters((prev) => {
      const newFilters = { ...prev };

      if (type === 'bpm') {
        if (prev.bpm_min === value.min && prev.bpm_max === value.max) {
          delete newFilters.bpm_min;
          delete newFilters.bpm_max;
        } else {
          newFilters.bpm_min = value.min;
          newFilters.bpm_max = value.max;
        }
      } else if (type === 'key') {
        if (prev.key === value) {
          delete newFilters.key;
        } else {
          newFilters.key = value;
        }
      }
      // Genre handling removed until backend supports it

      return newFilters;
    });
  };

  // Check if filter is active
  const isFilterActive = useMemo(() => {
    return Object.keys(filters).length > 0;
  }, [filters]);

  // Handle favorite change
  const handleFavoriteChange = (sampleId: string, isFavorited: boolean) => {
    setSamples((prev) =>
      prev.map((sample) =>
        sample.id === sampleId ? { ...sample, is_favorited: isFavorited } : sample
      )
    );
  };

  return (
    <div className="min-h-screen bg-black pb-20">
      {/* Header with search bar */}
      <div className="sticky top-0 z-10 bg-black/95 backdrop-blur-sm border-b border-white/10">
        <div className="px-4 py-3 space-y-3">
          {/* Search input */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search samples, creators, sounds..."
              className="w-full h-11 pl-11 pr-20 bg-white/5 border border-white/10 rounded-lg text-white placeholder:text-gray-500 focus:outline-none focus:ring-2 focus:ring-[hsl(338,82%,65%)]/50 focus:border-[hsl(338,82%,65%)]"
            />
            {searchQuery && (
              <button
                onClick={handleClearSearch}
                className="absolute right-12 top-1/2 -translate-y-1/2 w-8 h-8 flex items-center justify-center text-gray-400 hover:text-white active:scale-95 transition-all"
              >
                <X className="w-4 h-4" />
              </button>
            )}
            <button
              onClick={() => {
                onMedium();
                setShowFilters(!showFilters);
              }}
              className={`absolute right-2 top-1/2 -translate-y-1/2 w-8 h-8 flex items-center justify-center rounded transition-all active:scale-95 ${
                isFilterActive
                  ? 'text-[hsl(338,82%,65%)] bg-[hsl(338,82%,65%)]/10'
                  : 'text-gray-400 hover:text-white hover:bg-white/5'
              }`}
            >
              <SlidersHorizontal className="w-4 h-4" />
            </button>
          </div>

          {/* Filter chips */}
          {showFilters && (
            <div className="space-y-3 animate-in slide-in-from-top-2 duration-200">
              {/* BPM ranges */}
              <div>
                <div className="text-xs text-gray-400 mb-2 font-medium">BPM Range</div>
                <div className="flex flex-wrap gap-2">
                  {BPM_RANGES.map((range) => {
                    const isActive =
                      filters.bpm_min === range.min && filters.bpm_max === range.max;
                    return (
                      <button
                        key={range.label}
                        onClick={() => toggleFilter('bpm', range)}
                        className={`px-3 py-1.5 rounded-full text-xs font-medium transition-all active:scale-95 ${
                          isActive
                            ? 'bg-[hsl(338,82%,65%)] text-white'
                            : 'bg-white/5 text-gray-300 border border-white/10 hover:bg-white/10'
                        }`}
                      >
                        {range.label}
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Musical keys */}
              <div>
                <div className="text-xs text-gray-400 mb-2 font-medium">Key</div>
                <div className="flex flex-wrap gap-2">
                  {MUSICAL_KEYS.slice(0, 12).map((key) => {
                    const isActive = filters.key === key;
                    return (
                      <button
                        key={key}
                        onClick={() => toggleFilter('key', key)}
                        className={`px-3 py-1.5 rounded-full text-xs font-medium transition-all active:scale-95 ${
                          isActive
                            ? 'bg-[hsl(338,82%,65%)] text-white'
                            : 'bg-white/5 text-gray-300 border border-white/10 hover:bg-white/10'
                        }`}
                      >
                        {key}
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Genres - Removed until backend supports genre filtering */}
            </div>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="min-h-[calc(100vh-200px)]">
        {/* Loading state */}
        {isLoading && (
          <div className="flex flex-col items-center justify-center h-64">
            <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-[hsl(338,82%,65%)]"></div>
            <p className="text-gray-400 mt-4">Searching...</p>
          </div>
        )}

        {/* Error state */}
        {error && !isLoading && (
          <div className="flex flex-col items-center justify-center h-64 p-8 text-center">
            <Search className="w-16 h-16 text-red-500 mb-4" />
            <h2 className="text-xl font-bold mb-2 text-white">Search Error</h2>
            <p className="text-gray-400">{error}</p>
          </div>
        )}

        {/* Results */}
        {!isLoading && !error && hasSearched && samples.length > 0 && (
          <div>
            <div className="px-4 py-3 text-sm text-gray-400">
              Found {samples.length} {samples.length === 1 ? 'sample' : 'samples'}
            </div>
            <MobileSampleTable
              samples={samples}
              currentSample={currentSample}
              isPlaying={isPlaying}
              onSamplePreview={playPreview}
              onFavoriteChange={handleFavoriteChange}
            />
          </div>
        )}

        {/* No results */}
        {!isLoading && !error && hasSearched && samples.length === 0 && (
          <div className="flex flex-col items-center justify-center h-64 p-8 text-center">
            <Search className="w-16 h-16 text-gray-600 mb-4" />
            <h2 className="text-xl font-bold mb-2 text-white">No Results Found</h2>
            <p className="text-gray-400">
              Try adjusting your search or filters
            </p>
          </div>
        )}

        {/* Recent searches (shown when not searching) */}
        {!hasSearched && !isLoading && recentSearches.length > 0 && (
          <div className="px-4 py-6">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <Clock className="w-4 h-4 text-gray-400" />
                <h2 className="text-sm font-semibold text-gray-300">Recent Searches</h2>
              </div>
              <button
                onClick={handleClearRecentSearches}
                className="text-xs text-gray-500 hover:text-gray-300 transition-colors"
              >
                Clear
              </button>
            </div>
            <div className="space-y-2">
              {recentSearches.map((search, index) => (
                <button
                  key={`${search.query}-${index}`}
                  onClick={() => handleRecentSearchClick(search.query)}
                  className="w-full flex items-center gap-3 px-4 py-3 bg-white/5 hover:bg-white/10 rounded-lg text-left transition-colors active:scale-[0.98]"
                >
                  <Search className="w-4 h-4 text-gray-400 flex-shrink-0" />
                  <span className="text-sm text-white truncate flex-1">
                    {search.query}
                  </span>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Empty state (no search, no recent searches) */}
        {!hasSearched && !isLoading && recentSearches.length === 0 && (
          <div className="flex flex-col items-center justify-center h-64 p-8 text-center">
            <Search className="w-16 h-16 text-gray-600 mb-4" />
            <h2 className="text-xl font-bold mb-2 text-white">Search Samples</h2>
            <p className="text-gray-400 mb-6">
              Find samples by creator, sound, BPM, key, or genre
            </p>
            <div className="flex flex-col gap-2 w-full max-w-xs">
              <div className="flex items-center gap-2 text-sm text-gray-500">
                <TrendingUp className="w-4 h-4" />
                <span>Try: &quot;808&quot;, &quot;guitar loop&quot;, &quot;120 bpm&quot;</span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
