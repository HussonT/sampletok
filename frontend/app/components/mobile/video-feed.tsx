'use client';

import { useRef, useEffect, useState, useCallback } from 'react';
import { Sample } from '@/types/api';
import { VideoFeedItem } from './video-feed-item';
import { Loader2 } from 'lucide-react';

interface VideoFeedProps {
  samples: Sample[];
  onLoadMore: () => void;
  hasMore: boolean;
  isLoading: boolean;
  onFavoriteChange?: (sampleId: string, isFavorited: boolean) => void;
}

export function VideoFeed({
  samples,
  onLoadMore,
  hasMore,
  isLoading,
  onFavoriteChange
}: VideoFeedProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const observerRef = useRef<IntersectionObserver | null>(null);
  const [currentVideoIndex, setCurrentVideoIndex] = useState(0);
  const [globalMuted, setGlobalMuted] = useState(true); // Global mute state shared across all videos

  // Setup intersection observer for infinite scroll
  useEffect(() => {
    if (!hasMore || isLoading) return;

    const options = {
      root: null,
      rootMargin: '100px',
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

  // Track which video is currently in view for autoplay
  useEffect(() => {
    if (!containerRef.current) return;

    const options = {
      root: containerRef.current,
      rootMargin: '0px',
      threshold: 0.7, // Video must be 70% visible to be considered "in view"
    };

    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        const videoIndex = parseInt(entry.target.getAttribute('data-index') || '0');

        if (entry.isIntersecting && entry.intersectionRatio >= 0.7) {
          setCurrentVideoIndex(videoIndex);
        }
      });
    }, options);

    // Observe all video items
    const videoElements = containerRef.current.querySelectorAll('[data-index]');
    videoElements.forEach((el) => observer.observe(el));

    return () => observer.disconnect();
  }, [samples.length]);

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
