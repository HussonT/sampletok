'use client';

import { useCallback, useEffect, useState } from 'react';

/**
 * Haptic Feedback Hook
 *
 * Provides cross-platform haptic/vibration feedback for mobile interactions.
 * Falls back gracefully on unsupported devices.
 *
 * Supported Platforms:
 * - iOS: Haptic Engine (via navigator.vibrate)
 * - Android: Vibration API
 * - Desktop: No-op (silent fallback)
 *
 * Haptic Patterns:
 * - light: Quick tap (10ms) - for subtle feedback
 * - medium: Standard tap (20ms) - for button presses
 * - heavy: Strong tap (40ms) - for important actions
 * - success: Double tap (20ms, pause, 10ms) - for confirmations
 * - error: Triple tap (30ms, pause, 20ms, pause, 30ms) - for errors
 *
 * Usage:
 * ```tsx
 * const { triggerHaptic, isSupported } = useHaptics();
 *
 * <button onClick={() => triggerHaptic('medium')}>
 *   Click me
 * </button>
 * ```
 */

export type HapticPattern = 'light' | 'medium' | 'heavy' | 'success' | 'error';

interface UseHapticsOptions {
  /** Enable/disable haptics globally (default: true) */
  enabled?: boolean;
}

interface UseHapticsReturn {
  /** Trigger a haptic feedback pattern */
  triggerHaptic: (pattern: HapticPattern) => void;
  /** Whether haptics are supported on this device */
  isSupported: boolean;
  /** Enable/disable haptics */
  setEnabled: (enabled: boolean) => void;
  /** Current enabled state */
  enabled: boolean;
}

/**
 * Haptic pattern definitions (in milliseconds)
 * Format: [vibrate, pause, vibrate, pause, ...]
 */
const HAPTIC_PATTERNS: Record<HapticPattern, number | number[]> = {
  light: 10,
  medium: 20,
  heavy: 40,
  success: [20, 50, 10], // Double tap
  error: [30, 50, 20, 50, 30], // Triple tap
};

export function useHaptics(options: UseHapticsOptions = {}): UseHapticsReturn {
  // If options.enabled is provided, use it; otherwise default to true
  // This allows the hook to be used both with and without mobile settings
  const [enabled, setEnabled] = useState(options.enabled ?? true);
  const [isSupported, setIsSupported] = useState(false);

  /**
   * Check if Vibration API is supported
   */
  useEffect(() => {
    if (typeof window !== 'undefined' && 'vibrate' in navigator) {
      setIsSupported(true);
    }
  }, []);

  /**
   * Trigger haptic feedback with specified pattern
   */
  const triggerHaptic = useCallback(
    (pattern: HapticPattern) => {
      // Bail out if haptics are disabled, not supported, or not in browser
      if (!enabled || !isSupported || typeof window === 'undefined') {
        return;
      }

      try {
        const vibrationPattern = HAPTIC_PATTERNS[pattern];
        navigator.vibrate(vibrationPattern);
      } catch (error) {
        // Silent fail - haptics are enhancement, not critical
        console.debug('Haptic feedback error:', error);
      }
    },
    [enabled, isSupported]
  );

  return {
    triggerHaptic,
    isSupported,
    setEnabled,
    enabled,
  };
}

/**
 * Convenience hooks for specific haptic patterns
 */
export function useHapticFeedback() {
  const { triggerHaptic, isSupported } = useHaptics();

  return {
    onLight: useCallback(() => triggerHaptic('light'), [triggerHaptic]),
    onMedium: useCallback(() => triggerHaptic('medium'), [triggerHaptic]),
    onHeavy: useCallback(() => triggerHaptic('heavy'), [triggerHaptic]),
    onSuccess: useCallback(() => triggerHaptic('success'), [triggerHaptic]),
    onError: useCallback(() => triggerHaptic('error'), [triggerHaptic]),
    isSupported,
  };
}
