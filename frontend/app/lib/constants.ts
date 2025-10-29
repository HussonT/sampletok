/**
 * Frontend constants for TikTok collections feature
 *
 * These should match the backend configuration in app/core/config.py
 */

// Collection Processing
export const MAX_VIDEOS_PER_BATCH = 30 as const;

// Polling Configuration for Collection Status
export const POLLING_INTERVALS = {
  /** Initial polling interval (first 5 polls): 3 seconds */
  INITIAL: 3000,
  /** Medium polling interval (polls 6-10): 5 seconds */
  MEDIUM: 5000,
  /** Longer polling interval (polls 11-15): 10 seconds */
  LONG: 10000,
  /** Maximum polling interval (after 15 polls): 30 seconds */
  MAX: 30000,
} as const;

// Polling Thresholds
export const POLLING_THRESHOLDS = {
  /** Switch to medium interval after this many polls */
  MEDIUM_AFTER: 5,
  /** Switch to long interval after this many polls */
  LONG_AFTER: 10,
  /** Switch to max interval after this many polls */
  MAX_AFTER: 15,
} as const;

/**
 * Get polling interval based on poll count
 * Implements exponential backoff for status polling
 *
 * @param pollCount Current number of polls
 * @returns Polling interval in milliseconds
 */
export function getPollingInterval(pollCount: number): number {
  if (pollCount <= POLLING_THRESHOLDS.MEDIUM_AFTER) {
    return POLLING_INTERVALS.INITIAL;
  }
  if (pollCount <= POLLING_THRESHOLDS.LONG_AFTER) {
    return POLLING_INTERVALS.MEDIUM;
  }
  if (pollCount <= POLLING_THRESHOLDS.MAX_AFTER) {
    return POLLING_INTERVALS.LONG;
  }
  return POLLING_INTERVALS.MAX;
}
