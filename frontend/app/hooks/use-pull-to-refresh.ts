'use client';

import { useEffect, useRef, useState, useCallback } from 'react';

/**
 * Pull-to-Refresh Hook
 *
 * Implements iOS-style pull-to-refresh gesture for mobile web apps.
 * Detects downward pull gesture at the top of the page and triggers a refresh callback.
 *
 * Features:
 * - Elastic animation during pull
 * - Configurable pull distance threshold (default: 80px)
 * - Loading state management
 * - Prevents multiple simultaneous refreshes
 * - Touch-optimized for smooth mobile experience
 *
 * Usage:
 * ```tsx
 * const { isRefreshing, pullDistance } = usePullToRefresh({
 *   onRefresh: async () => {
 *     await refetch();
 *   },
 *   enabled: true,
 * });
 * ```
 */

interface UsePullToRefreshOptions {
  /** Callback function to execute when pull-to-refresh is triggered */
  onRefresh: () => Promise<void> | void;
  /** Minimum pull distance in pixels to trigger refresh (default: 80) */
  threshold?: number;
  /** Enable/disable pull-to-refresh (default: true) */
  enabled?: boolean;
  /** Ref to the scrollable container (default: document.body) */
  containerRef?: React.RefObject<HTMLElement>;
}

interface UsePullToRefreshReturn {
  /** Whether a refresh is currently in progress */
  isRefreshing: boolean;
  /** Current pull distance in pixels (for custom UI) */
  pullDistance: number;
  /** Whether the pull threshold has been reached */
  isThresholdReached: boolean;
}

export function usePullToRefresh({
  onRefresh,
  threshold = 80,
  enabled = true,
  containerRef,
}: UsePullToRefreshOptions): UsePullToRefreshReturn {
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [pullDistance, setPullDistance] = useState(0);
  const [isThresholdReached, setIsThresholdReached] = useState(false);

  const touchStartY = useRef<number>(0);
  const scrollAtStart = useRef<boolean>(false);
  const isDragging = useRef<boolean>(false);

  /**
   * Handle touch start - Record initial touch position and scroll state
   */
  const handleTouchStart = useCallback((e: TouchEvent) => {
    if (!enabled || isRefreshing) return;

    const container = containerRef?.current || document.documentElement;
    const scrollTop = container.scrollTop;

    // Only enable pull-to-refresh when at the top of the page
    scrollAtStart.current = scrollTop <= 0;

    if (scrollAtStart.current) {
      touchStartY.current = e.touches[0].clientY;
      isDragging.current = true;
    }
  }, [enabled, isRefreshing, containerRef]);

  /**
   * Handle touch move - Calculate pull distance and update state
   */
  const handleTouchMove = useCallback((e: TouchEvent) => {
    if (!enabled || isRefreshing || !isDragging.current || !scrollAtStart.current) return;

    const touchY = e.touches[0].clientY;
    const distance = touchY - touchStartY.current;

    // Only track downward pulls (positive distance)
    if (distance > 0) {
      // Apply elastic resistance - diminishing returns as you pull further
      const elasticDistance = Math.pow(distance, 0.85);
      setPullDistance(elasticDistance);
      setIsThresholdReached(elasticDistance >= threshold);

      // Prevent default scroll behavior when pulling
      if (distance > 10) {
        e.preventDefault();
      }
    }
  }, [enabled, isRefreshing, threshold]);

  /**
   * Handle touch end - Trigger refresh if threshold is met
   */
  const handleTouchEnd = useCallback(async () => {
    if (!enabled || isRefreshing || !isDragging.current) {
      setPullDistance(0);
      setIsThresholdReached(false);
      isDragging.current = false;
      return;
    }

    isDragging.current = false;

    // Trigger refresh if pulled beyond threshold
    if (pullDistance >= threshold) {
      setIsRefreshing(true);

      try {
        await onRefresh();
      } catch (error) {
        console.error('Pull-to-refresh error:', error);
      } finally {
        // Keep refresh indicator visible for minimum 500ms (feels more responsive)
        setTimeout(() => {
          setIsRefreshing(false);
          setPullDistance(0);
          setIsThresholdReached(false);
        }, 500);
      }
    } else {
      // Didn't reach threshold - animate back to 0
      setPullDistance(0);
      setIsThresholdReached(false);
    }
  }, [enabled, isRefreshing, pullDistance, threshold, onRefresh]);

  /**
   * Attach touch event listeners
   */
  useEffect(() => {
    if (!enabled) return;

    const container = containerRef?.current || document.documentElement;

    // Use passive: false to allow preventDefault
    const options: AddEventListenerOptions = { passive: false };

    container.addEventListener('touchstart', handleTouchStart, options);
    container.addEventListener('touchmove', handleTouchMove, options);
    container.addEventListener('touchend', handleTouchEnd, options);

    return () => {
      container.removeEventListener('touchstart', handleTouchStart);
      container.removeEventListener('touchmove', handleTouchMove);
      container.removeEventListener('touchend', handleTouchEnd);
    };
  }, [enabled, handleTouchStart, handleTouchMove, handleTouchEnd, containerRef]);

  return {
    isRefreshing,
    pullDistance,
    isThresholdReached,
  };
}
