'use client';

import { VideoFeed } from '@/components/mobile/video-feed';
import { VideoFeedErrorBoundary } from '@/components/mobile/video-feed-error-boundary';
import { AuthPromptModal } from '@/components/mobile/auth-prompt-modal';
import { PullToRefreshIndicator } from '@/components/mobile/pull-to-refresh-indicator';
import { useSampleQueue } from '@/hooks/use-sample-queue';
import { useAuthPrompt } from '@/hooks/use-auth-prompt';
import { usePullToRefresh } from '@/hooks/use-pull-to-refresh';
import { useAuth } from '@clerk/nextjs';
import { useState, useEffect, useCallback } from 'react';
import { createAuthenticatedClient, publicApi } from '@/lib/api-client';
import { Loader2 } from 'lucide-react';
import { analytics } from '@/lib/analytics';

/**
 * Mobile Feed Page
 *
 * Main entry point for the mobile PWA's Tinder-style video discovery experience.
 * Integrates video feed with strategic authentication prompts to convert guest users.
 *
 * Key Features:
 * - Infinite scroll video feed with sample queue management
 * - Auth prompt triggered after 7 video views (only for guests)
 * - Automatic API client switching on authentication state change
 * - Optimistic UI updates for favorites/downloads
 *
 * Authentication Flow:
 * 1. Guest browses videos using public API
 * 2. Auth prompt shows after 7 videos (strategic timing)
 * 3. User signs up/in via Clerk modal
 * 4. API client switches to authenticated mode
 * 5. User can now favorite/download samples
 * 6. TanStack Query automatically refetches with auth headers
 */
export default function MobileFeedPage() {
  const { isSignedIn, getToken } = useAuth();
  const [apiClient, setApiClient] = useState(publicApi);

  /**
   * Auth Prompt Management - Value First Approach
   *
   * No modals on page load - let users explore and see value first!
   * Auth prompt only shows when:
   * 1. User clicks save/favorite button (needs account to save)
   * 2. User tries to download (needs account)
   * 3. User has viewed exactly 10 distinct samples (seen enough value)
   *
   * Once dismissed, won't show again this session.
   */
  const {
    shouldShowModal,
    triggerAuthPrompt,
    incrementViewCount,
    dismissModal,
    closeModal,
  } = useAuthPrompt({
    triggerCount: 10, // Show auth after 10 distinct samples viewed
    enabled: !isSignedIn, // Only track guest users
  });

  /**
   * API Client Switching
   *
   * Automatically switches between public and authenticated API clients
   * based on authentication state. This ensures:
   * - Guests use public API (limited access)
   * - Authenticated users get their personalized data (favorites, downloads)
   * - TanStack Query automatically refetches when client changes
   */
  useEffect(() => {
    if (isSignedIn && getToken) {
      setApiClient(createAuthenticatedClient(getToken));
    } else {
      setApiClient(publicApi);
    }
  }, [isSignedIn, getToken]);

  // Sample queue management with infinite scroll
  const {
    samples,
    loadMore,
    hasMore,
    isLoading,
    reset,
    refetch,
  } = useSampleQueue({ apiClient });

  /**
   * Pull-to-refresh functionality
   * Refreshes the feed by resetting the queue and fetching new samples
   */
  const { isRefreshing, pullDistance, isThresholdReached } = usePullToRefresh({
    onRefresh: async () => {
      await refetch();
    },
    enabled: !isLoading && samples.length > 0, // Only enable when feed is loaded
    threshold: 80,
  });

  /**
   * Track favorited samples locally to persist across feed navigation.
   * This ensures heart icons remain filled even when scrolling away and back.
   */
  const [favoritedSamples, setFavoritedSamples] = useState<Set<string>>(new Set());

  /**
   * Initialize favorited samples from API data when samples load.
   * This ensures any pre-favorited samples (for authenticated users) are tracked.
   */
  useEffect(() => {
    if (samples.length > 0 && isSignedIn) {
      const newFavorites = samples
        .filter(sample => sample.is_favorited)
        .map(sample => sample.id);

      if (newFavorites.length > 0) {
        setFavoritedSamples(prev => {
          const next = new Set(prev);
          newFavorites.forEach(id => next.add(id));
          return next;
        });
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [samples.length, isSignedIn]); // Only re-run when sample count or auth changes, not on every sample mutation

  /**
   * Handles favorite state changes from video feed.
   * Updates local state to remember which samples are favorited.
   */
  const handleFavoriteChange = useCallback((sampleId: string, isFavorited: boolean) => {
    setFavoritedSamples(prev => {
      const next = new Set(prev);
      if (isFavorited) {
        next.add(sampleId);
      } else {
        next.delete(sampleId);
      }
      return next;
    });
    console.log(`Sample ${sampleId} favorited: ${isFavorited}`);
  }, []);

  /**
   * Tracks when user scrolls to a new video in the feed.
   * Increments view count for auth prompt timing.
   *
   * This is called by VideoFeed component via IntersectionObserver when
   * a video becomes 70% visible (threshold for "in view").
   */
  const handleVideoChange = useCallback((videoIndex: number) => {
    // Increment view count for auth prompt tracking (guests only)
    incrementViewCount();

    // Track mobile feed viewed every 5th video
    if (videoIndex > 0 && videoIndex % 5 === 0) {
      analytics.mobileFeedViewed();
    }
  }, [incrementViewCount, samples.length]);

  // Loading state (initial load) - Show skeleton feed item
  if (isLoading && samples.length === 0) {
    return (
      <VideoFeed
        samples={[]}
        onLoadMore={() => {}}
        hasMore={false}
        isLoading={true}
        onFavoriteChange={handleFavoriteChange}
        onVideoChange={handleVideoChange}
        onAuthRequired={triggerAuthPrompt}
        showLoadingSkeleton={true}
      />
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

  // Merge favorited state with samples
  const enrichedSamples = samples.map(sample => ({
    ...sample,
    is_favorited: favoritedSamples.has(sample.id) || sample.is_favorited || false,
  }));

  return (
    <>
      {/* Pull-to-refresh indicator */}
      <PullToRefreshIndicator
        pullDistance={pullDistance}
        isThresholdReached={isThresholdReached}
        isRefreshing={isRefreshing}
        threshold={80}
      />

      {/* Main video feed with infinite scroll */}
      <VideoFeedErrorBoundary>
        <VideoFeed
          samples={enrichedSamples}
          onLoadMore={loadMore}
          hasMore={hasMore}
          isLoading={isLoading}
          onFavoriteChange={handleFavoriteChange}
          onVideoChange={handleVideoChange} // Tracks views for auth prompt (auto-trigger at 10 views)
          onAuthRequired={triggerAuthPrompt} // Triggers auth prompt on save/download attempts
        />
      </VideoFeedErrorBoundary>

      {/*
        Auth Prompt Modal - Value First Approach

        No modals on page load! Users start browsing immediately.

        Shows strategically when:
        1. User clicks save/favorite (needs account to persist favorites)
        2. User tries to download (needs account for downloads)
        3. User has viewed exactly 10 samples (crossed threshold, seen enough value)

        Once dismissed, won't show again this session - respects user choice.
      */}
      <AuthPromptModal
        isOpen={shouldShowModal}
        onClose={closeModal}
        onDismiss={dismissModal}
      />
    </>
  );
}
