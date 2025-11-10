'use client';

import { Loader2, ArrowDown } from 'lucide-react';

/**
 * Pull-to-Refresh Indicator
 *
 * Visual feedback component for pull-to-refresh gesture.
 * Shows arrow icon during pull, checkmark when threshold reached,
 * and spinner during refresh.
 *
 * Features:
 * - Smooth elastic animation following pull distance
 * - Icon transitions (arrow → checkmark → spinner)
 * - Glassmorphism design matching SampleTok theme
 * - Optimized for mobile touch interactions
 */

interface PullToRefreshIndicatorProps {
  /** Current pull distance in pixels */
  pullDistance: number;
  /** Whether the pull threshold has been reached */
  isThresholdReached: boolean;
  /** Whether a refresh is currently in progress */
  isRefreshing: boolean;
  /** Pull distance threshold in pixels */
  threshold?: number;
}

export function PullToRefreshIndicator({
  pullDistance,
  isThresholdReached,
  isRefreshing,
  threshold = 80,
}: PullToRefreshIndicatorProps) {
  // Don't render if not being pulled or refreshing
  if (pullDistance === 0 && !isRefreshing) return null;

  // Calculate opacity based on pull distance (0 → 1 as you pull)
  const opacity = Math.min(pullDistance / threshold, 1);

  // Calculate scale for elastic feel (1 → 1.2 as you approach threshold)
  const scale = 1 + Math.min(pullDistance / threshold, 0.2);

  // Rotation angle for arrow (0° → 180° when threshold reached)
  const rotation = isThresholdReached ? 180 : Math.min((pullDistance / threshold) * 180, 160);

  return (
    <div
      className="fixed top-0 left-0 right-0 z-50 flex justify-center pt-4 pointer-events-none"
      style={{
        opacity: isRefreshing ? 1 : opacity,
        transform: `translateY(${Math.min(pullDistance * 0.5, 60)}px)`,
        transition: isRefreshing ? 'opacity 0.2s, transform 0.3s' : 'none',
      }}
    >
      <div
        className="flex items-center justify-center w-12 h-12 rounded-full backdrop-blur-sm border shadow-lg"
        style={{
          background: 'rgba(255, 255, 255, 0.1)',
          borderColor: isThresholdReached
            ? 'hsl(338, 82%, 65%)' // SampleTok pink when ready
            : 'rgba(255, 255, 255, 0.2)',
          transform: `scale(${isRefreshing ? 1 : scale})`,
          transition: isRefreshing ? 'all 0.3s' : 'none',
        }}
      >
        {isRefreshing ? (
          // Spinner during refresh
          <Loader2
            className="w-6 h-6 animate-spin"
            style={{ color: 'hsl(338, 82%, 65%)' }}
          />
        ) : isThresholdReached ? (
          // Checkmark when threshold reached (ready to refresh)
          <svg
            className="w-6 h-6"
            viewBox="0 0 24 24"
            fill="none"
            stroke="hsl(338, 82%, 65%)"
            strokeWidth="3"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <polyline points="20 6 9 17 4 12" />
          </svg>
        ) : (
          // Arrow during pull (rotates as you pull)
          <ArrowDown
            className="w-6 h-6 text-white transition-transform"
            style={{
              transform: `rotate(${rotation}deg)`,
            }}
          />
        )}
      </div>
    </div>
  );
}
