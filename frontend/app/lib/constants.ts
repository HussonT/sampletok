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

// Subscription Tiers
export const SUBSCRIPTION_TIERS = {
  BASIC: {
    name: 'Basic',
    tier: 'basic' as const,
    credits: 100,
    price: {
      monthly: 9.99,
      annual: 99.50, // 17% discount (2 months free)
    },
    features: [
      '100 credits per month',
      'Process up to 100 videos/month',
      'High-quality audio extraction',
      'BPM and key detection',
      'Download MP3 & WAV formats',
      'Email support',
    ],
  },
  PRO: {
    name: 'Pro',
    tier: 'pro' as const,
    credits: 400,
    price: {
      monthly: 16.99,
      annual: 169.22, // 17% discount
    },
    features: [
      '400 credits per month',
      'Process up to 400 videos/month',
      'Everything in Basic',
      '10% discount on top-up credits',
      'Priority processing',
      'Priority email support',
    ],
    popular: true,
  },
  ULTIMATE: {
    name: 'Ultimate',
    tier: 'ultimate' as const,
    credits: 1500,
    price: {
      monthly: 49.99,
      annual: 497.90, // 17% discount
    },
    features: [
      '1,500 credits per month',
      'Process up to 1,500 videos/month',
      'Everything in Pro',
      '20% discount on top-up credits',
      'Fastest processing speed',
      'Priority support with dedicated assistance',
    ],
  },
} as const;

// Billing intervals
export type BillingInterval = 'month' | 'year';

// Calculate savings percentage for annual billing
export const ANNUAL_DISCOUNT_PERCENT = 17;

// Top-Up Packages (One-time credit purchases)
export const TOPUP_PACKAGES = {
  SMALL: {
    name: 'Small Pack',
    package: 'small' as const,
    credits: 50,
    basePrice: 6.99,
    description: 'Perfect for occasional extra videos',
  },
  MEDIUM: {
    name: 'Medium Pack',
    package: 'medium' as const,
    credits: 150,
    basePrice: 17.99,
    description: 'Great for burst projects',
    popular: true,
  },
  LARGE: {
    name: 'Large Pack',
    package: 'large' as const,
    credits: 500,
    basePrice: 49.99,
    description: 'Maximum value for heavy users',
  },
} as const;

// Tier-based top-up discounts
export const TOPUP_DISCOUNTS = {
  basic: 0,
  pro: 10,
  ultimate: 20,
} as const;
