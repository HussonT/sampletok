'use client';

import { useRef, useEffect, useState, useCallback } from 'react';
import { Sample } from '@/types/api';
import { VideoFeedItem } from './video-feed-item';
import { Loader2 } from 'lucide-react';

/**
 * Video Feed Component
 *
 * Tinder-style vertical scrolling feed for sample discovery.
 * Implements snap scrolling, infinite loading, and autoplay.
 *
 * Key Features:
 * - Snap scroll (one video per viewport)
 * - Infinite scroll with Intersection Observer
 * - Autoplay when video is 70% visible
 * - Global mute state (shared across all videos)
 * - View tracking for auth prompt
 *
 * Architecture:
 * - Container uses snap-y snap-mandatory for Tinder feel
 * - Two IntersectionObservers: one for infinite scroll, one for autoplay
 * - Scroll sentinel at bottom triggers loadMore
 * - Each video item tracks visibility for autoplay
 */
interface VideoFeedProps {
  /** Array of samples to display in feed */
  samples: Sample[];
  /** Callback to load more samples (infinite scroll) */
  onLoadMore: () => void;
  /** Whether more samples are available */
  hasMore: boolean;
  /** Loading state for infinite scroll */
  isLoading: boolean;
  /** Optional callback when favorite state changes */
  onFavoriteChange?: (sampleId: string, isFavorited: boolean) => void;
  /** Optional callback when user scrolls to new video (for auth prompt tracking) */
  onVideoChange?: (videoIndex: number) => void;
  /** Optional callback when user attempts action requiring authentication */
  onAuthRequired?: () => void;
}

export function VideoFeed({
  samples,
  onLoadMore,
  hasMore,
  isLoading,
  onFavoriteChange,
  onVideoChange,
  onAuthRequired
}: VideoFeedProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const observerRef = useRef<IntersectionObserver | null>(null);
  const [currentVideoIndex, setCurrentVideoIndex] = useState(0);
  const [globalMuted, setGlobalMuted] = useState(true); // Global mute state shared across all videos

  /**
   * Infinite Scroll with Intersection Observer
   *
   * Watches the scroll sentinel element at the bottom of the feed.
   * When sentinel comes into view (within 100px), triggers onLoadMore.
   *
   * Optimization: Only observes when hasMore=true and not currently loading
   * to prevent duplicate API calls.
   */
  useEffect(() => {
    if (!hasMore || isLoading) return;

    const options = {
      root: null,
      rootMargin: '100px', // Trigger 100px before reaching sentinel
      threshold: 0.1,
    };

    observerRef.current = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting && hasMore && !isLoading) {
          onLoadMore();
        }
      });
    }, options);

    const sentinel = document.getElementById('scroll-sentinel');
    if (sentinel && observerRef.current) {
      observerRef.current.observe(sentinel);
    }

    return () => {
      if (observerRef.current) {
        observerRef.current.disconnect();
      }
    };
  }, [hasMore, isLoading, onLoadMore]);

  /**
   * Video View Tracking with Intersection Observer
   *
   * Tracks which video is currently "in view" for:
   * 1. Autoplay (VideoFeedItem gets isActive prop)
   * 2. Auth prompt tracking (onVideoChange callback)
   *
   * Threshold: 70% - video must be mostly visible to count as viewed.
   * This prevents "scroll-through" from counting as views.
   *
   * Integration with Auth Prompt:
   * - Each time a new video becomes 70% visible, onVideoChange is called
   * - Parent component (MobileFeedPage) increments auth prompt view count
   * - After 7 unique video views, auth modal is triggered
   */
  useEffect(() => {
    if (!containerRef.current) return;

    const options = {
      root: containerRef.current,
      rootMargin: '0px',
      threshold: 0.7, // Video must be 70% visible to count as "viewed"
    };

    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        const videoIndex = parseInt(entry.target.getAttribute('data-index') || '0');

        if (entry.isIntersecting && entry.intersectionRatio >= 0.7) {
          setCurrentVideoIndex(videoIndex);
          // Notify parent component about video change (for auth prompt tracking)
          onVideoChange?.(videoIndex);
        }
      });
    }, options);

    // Observe all video items (each has data-index attribute)
    const videoElements = containerRef.current.querySelectorAll('[data-index]');
    videoElements.forEach((el) => observer.observe(el));

    return () => observer.disconnect();
  }, [samples.length, onVideoChange]);

  return (
    <div
      ref={containerRef}
      className="h-screen overflow-y-scroll snap-y snap-mandatory bg-[hsl(0,0%,17%)]"
      style={{
        scrollbarWidth: 'none',
        msOverflowStyle: 'none',
        WebkitOverflowScrolling: 'touch'
      }}
    >
      <style jsx>{`
        div::-webkit-scrollbar {
          display: none;
        }
      `}</style>

      {samples.map((sample, index) => (
        <VideoFeedItem
          key={sample.id}
          sample={sample}
          index={index}
          isActive={index === currentVideoIndex}
          onFavoriteChange={onFavoriteChange}
          onAuthRequired={onAuthRequired}
          globalMuted={globalMuted}
          onMuteChange={setGlobalMuted}
        />
      ))}

      {/* Loading sentinel for infinite scroll */}
      {hasMore && (
        <div
          id="scroll-sentinel"
          className="h-screen flex items-center justify-center snap-start bg-[hsl(0,0%,17%)]"
        >
          <div className="text-center">
            <Loader2 className="w-12 h-12 animate-spin text-[hsl(338,82%,65%)] mx-auto mb-4" />
            <p className="text-gray-400">Loading more samples...</p>
          </div>
        </div>
      )}

      {/* No more content */}
      {!hasMore && samples.length > 0 && (
        <div className="h-screen flex items-center justify-center snap-start bg-[hsl(0,0%,17%)]">
          <div className="text-center p-6">
            <span className="text-6xl mb-4 block">🎉</span>
            <h2 className="text-2xl font-bold text-white mb-2">
              You've seen them all!
            </h2>
            <p className="text-gray-400">
              Check back later for more samples
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
