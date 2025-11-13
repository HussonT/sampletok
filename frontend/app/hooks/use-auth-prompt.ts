'use client';

import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@clerk/nextjs';

// localStorage key for persisting auth prompt state across sessions
const STORAGE_KEY = 'sampletok_auth_prompt';

// Default number of video views before showing auth prompt
// Why 10? Based on conversion optimization: users need several interactions to understand
// product value before being asked to commit. Shows once after 10 distinct samples viewed.
const DEFAULT_TRIGGER_COUNT = 10;

/**
 * Authentication Prompt State
 *
 * Stored in localStorage to persist across page refreshes and track user behavior.
 * Resets daily to give returning guests fresh opportunities to convert.
 */
interface AuthPromptState {
  /** Total number of distinct samples viewed by guest user */
  totalViewCount: number;
  /** Date string for daily reset tracking (format: "Mon Jan 01 2024") */
  lastReset: string;
}

/**
 * Hook Configuration Options
 */
interface UseAuthPromptOptions {
  /** Number of video views before showing modal (default: 7) */
  triggerCount?: number;
  /** Enable/disable the auth prompt system (default: true) */
  enabled?: boolean;
}

/**
 * useAuthPrompt Hook
 *
 * Manages authentication prompt timing for guest users based on video view count.
 * Implements strategic recurring prompts to maximize conversion opportunities.
 *
 * Key Features:
 * - Tracks video view count in localStorage (persists across page refreshes)
 * - Shows modal EVERY N views (default: 7 videos) - recurring throughout session
 * - Resets counter after each modal show to trigger again after N more views
 * - Daily reset for returning guests (fresh conversion opportunity each day)
 * - Automatically disabled for authenticated users
 *
 * Why Recurring Prompts?
 * - Multiple touchpoints increase conversion likelihood
 * - User mindset changes throughout browsing session
 * - Non-intrusive frequency (every 7 videos = ~2-3 minutes of browsing)
 * - Users who dismissed early might be ready after seeing more value
 *
 * Why Daily Reset?
 * - Balances re-engagement with respect for user choice
 * - Users who dismissed yesterday might be ready today
 * - Gives returning guests fresh opportunities over time
 *
 * @example
 * ```tsx
 * const { shouldShowModal, incrementViewCount, dismissModal, closeModal } = useAuthPrompt({
 *   triggerCount: 7,  // Show every 7 videos
 *   enabled: !isSignedIn  // Only for guests
 * });
 *
 * // In video feed component:
 * const handleVideoChange = (index) => {
 *   incrementViewCount();  // Track each video view
 * };
 *
 * // In render:
 * <AuthPromptModal
 *   isOpen={shouldShowModal}
 *   onClose={closeModal}
 *   onDismiss={dismissModal}
 * />
 * ```
 */
export function useAuthPrompt({
  triggerCount = DEFAULT_TRIGGER_COUNT,
  enabled = true
}: UseAuthPromptOptions = {}) {
  const { isSignedIn } = useAuth();
  const [shouldShowModal, setShouldShowModal] = useState(false);
  const [dismissedThisSession, setDismissedThisSession] = useState(false);
  const [state, setState] = useState<AuthPromptState>({
    totalViewCount: 0,
    lastReset: new Date().toDateString(),
  });

  /**
   * Load auth prompt state from localStorage on component mount.
   * NO auto-showing modals - value first approach!
   */
  useEffect(() => {
    // Skip if disabled or user is already signed in
    if (!enabled || isSignedIn) return;

    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        const parsedState = JSON.parse(stored) as AuthPromptState;
        const today = new Date().toDateString();

        // Daily reset for view count
        if (parsedState.lastReset !== today) {
          const freshState: AuthPromptState = {
            totalViewCount: 0,
            lastReset: today,
          };
          setState(freshState);
          localStorage.setItem(STORAGE_KEY, JSON.stringify(freshState));
        } else {
          // Same day - restore previous state
          setState(parsedState);
        }
      }
    } catch (error) {
      console.error('Error loading auth prompt state:', error);
    }
  }, [enabled, isSignedIn]);

  /**
   * Saves auth prompt state to localStorage.
   * Handles errors gracefully (e.g., localStorage quota exceeded, privacy mode).
   */
  const saveState = useCallback((newState: AuthPromptState) => {
    setState(newState);
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(newState));
    } catch (error) {
      console.error('Error saving auth prompt state:', error);
    }
  }, []);

  /**
   * Increments video view count and auto-triggers modal when threshold is reached.
   * Called by parent component each time user scrolls to a new distinct sample.
   *
   * Auto-trigger Logic:
   * - Triggers modal when view count CROSSES the threshold (not if already past it)
   * - Only triggers if user hasn't dismissed modal this session
   * - Respects user choice to browse as guest
   *
   * Conditions checked:
   * - Hook must be enabled
   * - User must be a guest (not signed in)
   * - Modal not dismissed this session
   */
  const incrementViewCount = useCallback(() => {
    // Don't track if disabled, user is signed in, or auth modal was dismissed this session
    if (!enabled || isSignedIn || dismissedThisSession) return;

    const newTotalViewCount = state.totalViewCount + 1;
    const newState = {
      ...state,
      totalViewCount: newTotalViewCount,
    };

    // Auto-trigger modal when CROSSING the threshold (not if already past it)
    // This prevents auto-showing on page load if user already has 10+ views from previous session
    if (newTotalViewCount === triggerCount && !dismissedThisSession) {
      setShouldShowModal(true);
    }

    saveState(newState);
  }, [enabled, isSignedIn, dismissedThisSession, state, triggerCount, saveState]);

  /**
   * Manually triggers auth prompt modal.
   * Used when user attempts actions requiring authentication:
   * - Clicking save/favorite button
   * - Attempting to download a sample
   *
   * Respects user choice - won't show if already dismissed this session.
   */
  const triggerAuthPrompt = useCallback(() => {
    // Don't show if disabled, user is signed in, or already dismissed this session
    if (!enabled || isSignedIn || dismissedThisSession) return;

    setShouldShowModal(true);
  }, [enabled, isSignedIn, dismissedThisSession]);

  /**
   * Handles modal dismissal when user clicks "Continue as guest".
   * Closes the modal and marks as dismissed for this session.
   * User can browse freely without the auth prompt showing again until they refresh.
   */
  const dismissModal = useCallback(() => {
    setShouldShowModal(false);
    setDismissedThisSession(true); // Don't show again this session
  }, []);

  /**
   * Closes modal without marking as dismissed.
   * Used when modal is closed programmatically (e.g., user navigated away).
   * Modal can potentially show again later if conditions are met.
   */
  const closeModal = useCallback(() => {
    setShouldShowModal(false);
  }, []);

  /**
   * Resets auth prompt state to initial values.
   * Useful for testing or admin actions.
   * Clears all view counts and closes modal.
   */
  const reset = useCallback(() => {
    const freshState: AuthPromptState = {
      totalViewCount: 0,
      lastReset: new Date().toDateString(),
    };
    saveState(freshState);
    setShouldShowModal(false);
    setDismissedThisSession(false);
  }, [saveState]);

  return {
    shouldShowModal,
    totalViewCount: state.totalViewCount,
    incrementViewCount,
    triggerAuthPrompt,
    dismissModal,
    closeModal,
    reset,
    // Debug info
    state,
  };
}
