import posthog from 'posthog-js';
import { Sample } from '@/types/api';

/**
 * Analytics helper for PostHog event tracking
 *
 * Usage:
 *   import { analytics } from '@/lib/analytics';
 *   analytics.samplePlayed(sample, 'player');
 *
 * All methods are safe to call even if PostHog is not initialized.
 * They will silently fail and log warnings in development mode.
 */

/**
 * Helper to safely capture events only when PostHog is loaded
 * This is the ONLY way to capture events - never call posthog.capture directly
 */
function safeCapture(eventName: string, properties?: Record<string, any>) {
  try {
    // Check if PostHog is available and loaded
    if (typeof window === 'undefined') return;
    if (!posthog) return;
    if (!posthog.__loaded) {
      if (process.env.NODE_ENV === 'development') {
        console.warn(`[Analytics] PostHog not loaded yet, skipping event: ${eventName}`);
      }
      return;
    }

    posthog.capture(eventName, properties);
  } catch (error) {
    // Never throw - analytics should never break the app
    if (process.env.NODE_ENV === 'development') {
      console.error(`[Analytics] Error capturing event ${eventName}:`, error);
    }
  }
}

/**
 * Helper to safely track TikTok Pixel events
 * Only fires if TikTok Pixel is loaded
 */
function trackTikTokEvent(eventName: string, properties?: Record<string, any>) {
  try {
    if (typeof window === 'undefined') return;
    if (!(window as any).ttq) {
      if (process.env.NODE_ENV === 'development') {
        console.warn(`[TikTok Pixel] Not loaded yet, skipping event: ${eventName}`);
      }
      return;
    }

    (window as any).ttq.track(eventName, properties);

    if (process.env.NODE_ENV === 'development') {
      console.log(`[TikTok Pixel] Event tracked: ${eventName}`, properties);
    }
  } catch (error) {
    // Never throw - analytics should never break the app
    if (process.env.NODE_ENV === 'development') {
      console.error(`[TikTok Pixel] Error tracking event ${eventName}:`, error);
    }
  }
}

export const analytics = {
  // ============================================
  // Sample Events
  // ============================================

  sampleViewed(sample: Sample) {
    safeCapture('sample_viewed', {
      sample_id: sample.id,
      creator: sample.tiktok_creator?.username || sample.instagram_creator?.username || sample.creator_username,
      source: sample.source,
      bpm: sample.bpm,
      key: sample.key,
      duration: sample.duration_seconds,
      has_stems: false, // Will be updated when stem features are added
      view_count: sample.view_count,
      like_count: sample.like_count,
    });

    // Track ViewContent on TikTok Pixel
    trackTikTokEvent('ViewContent', {
      content_type: 'product',
      content_id: sample.id,
      content_name: sample.tiktok_creator?.username || sample.creator_username || 'Unknown Creator',
    });
  },

  samplePlayed(sample: Sample, source: 'table' | 'player' | 'mobile_feed') {
    safeCapture('sample_played', {
      sample_id: sample.id,
      creator: sample.tiktok_creator?.username || sample.instagram_creator?.username || sample.creator_username,
      source,
      has_hls: !!sample.audio_url_hls,
      bpm: sample.bpm,
      key: sample.key,
    });
  },

  samplePaused(sample: Sample, currentTime: number) {
    safeCapture('sample_paused', {
      sample_id: sample.id,
      current_time: currentTime,
      duration: sample.duration_seconds,
    });
  },

  sampleCompleted(sample: Sample, playDuration: number) {
    safeCapture('sample_completed', {
      sample_id: sample.id,
      play_duration: playDuration,
      sample_duration: sample.duration_seconds,
      completion_rate: sample.duration_seconds ? playDuration / sample.duration_seconds : 0,
    });
  },

  sampleSeeked(sample: Sample, from: number, to: number) {
    safeCapture('sample_seeked', {
      sample_id: sample.id,
      from_time: from,
      to_time: to,
      seek_distance: Math.abs(to - from),
    });
  },

  videoPreviewViewed(sample: Sample) {
    safeCapture('video_preview_viewed', {
      sample_id: sample.id,
      creator: sample.tiktok_creator?.username || sample.instagram_creator?.username || sample.creator_username,
    });
  },

  sampleDownloaded(sample: Sample, downloadType: 'wav' | 'mp3' | 'stem') {
    safeCapture('sample_downloaded', {
      sample_id: sample.id,
      download_type: downloadType,
      creator: sample.tiktok_creator?.username || sample.instagram_creator?.username || sample.creator_username,
      bpm: sample.bpm,
      key: sample.key,
    });
  },

  sampleFavorited(sample: Sample, isFavorited: boolean) {
    safeCapture(isFavorited ? 'sample_favorited' : 'sample_unfavorited', {
      sample_id: sample.id,
      creator: sample.tiktok_creator?.username || sample.instagram_creator?.username || sample.creator_username,
    });
  },

  // ============================================
  // TikTok/Instagram Processing Events
  // ============================================

  urlSubmitted(url: string, source: 'tiktok' | 'instagram') {
    safeCapture(`${source}_url_submitted`, {
      url_domain: new URL(url).hostname,
      source,
    });
  },

  // ============================================
  // Collection Events
  // ============================================

  collectionCreated(collectionId: string, collectionName: string, videoCount: number) {
    safeCapture('collection_created', {
      collection_id: collectionId,
      collection_name: collectionName,
      video_count: videoCount,
    });
  },

  collectionViewed(collectionId: string, collectionName: string, sampleCount: number) {
    safeCapture('collection_viewed', {
      collection_id: collectionId,
      collection_name: collectionName,
      sample_count: sampleCount,
    });
  },

  sampleAddedToCollection(sampleId: string, collectionId: string) {
    safeCapture('sample_added_to_collection', {
      sample_id: sampleId,
      collection_id: collectionId,
    });
  },

  collectionReset(collectionId: string) {
    safeCapture('collection_reset', {
      collection_id: collectionId,
    });
  },

  // ============================================
  // Search & Filter Events
  // ============================================

  searchPerformed(query: string, resultCount: number) {
    safeCapture('search_performed', {
      query_length: query.length,
      result_count: resultCount,
      has_results: resultCount > 0,
    });

    // Track Search on TikTok Pixel
    trackTikTokEvent('Search', {
      query: query,
      content_type: 'product',
    });
  },

  filterApplied(filterType: string, filterValue: string | number) {
    safeCapture('filter_applied', {
      filter_type: filterType,
      filter_value: filterValue,
    });
  },

  filterCleared(filterType?: string) {
    safeCapture('filter_cleared', {
      filter_type: filterType || 'all',
    });
  },

  // ============================================
  // Mobile PWA Events
  // ============================================

  mobileSwipe(direction: 'left' | 'right', sample: Sample) {
    safeCapture('mobile_swipe', {
      direction,
      sample_id: sample.id,
      creator: sample.tiktok_creator?.username || sample.instagram_creator?.username || sample.creator_username,
    });
  },

  pullToRefresh() {
    safeCapture('pull_to_refresh');
  },

  mobileFeedViewed() {
    safeCapture('mobile_feed_viewed', {
      platform: navigator.platform,
      user_agent: navigator.userAgent,
    });
  },

  // ============================================
  // Monetization Events
  // ============================================

  creditsViewed(currentBalance: number) {
    safeCapture('credits_viewed', {
      balance: currentBalance,
    });
  },

  creditsPurchased(creditsAdded: number, amount: number) {
    safeCapture('credits_purchased', {
      credits: creditsAdded,
      amount,
    });
  },

  subscriptionViewed(tier?: string) {
    safeCapture('subscription_viewed', {
      tier,
    });

    // Track Lead on TikTok Pixel (user viewing pricing = lead interest)
    trackTikTokEvent('Lead', {
      content_type: 'product',
      content_id: tier || 'pricing_page',
      content_name: tier ? `${tier.charAt(0).toUpperCase() + tier.slice(1)} Plan` : 'Pricing Page',
    });
  },

  subscriptionStarted(tier: string) {
    safeCapture('subscription_started', {
      tier,
    });

    // Track InitiateCheckout on TikTok Pixel
    trackTikTokEvent('InitiateCheckout', {
      content_type: 'product',
      content_id: tier,
      content_name: `${tier.charAt(0).toUpperCase() + tier.slice(1)} Plan`,
      contents: [
        {
          content_type: 'product',
          content_name: `${tier.charAt(0).toUpperCase() + tier.slice(1)} Plan`,
        }
      ],
    });
  },

  subscriptionCompleted(tier: string, price?: number, currency?: string) {
    safeCapture('subscription_completed', {
      tier,
      price,
      currency,
    });

    // Track Subscribe event on TikTok Pixel
    if (price && currency) {
      trackTikTokEvent('Subscribe', {
        content_type: 'product',
        content_name: `${tier.charAt(0).toUpperCase() + tier.slice(1)} Plan`,
        currency: currency.toUpperCase(),
        value: price,
      });
    }
  },

  // ============================================
  // Stem Separation Events
  // ============================================

  stemSeparationRequested(sampleId: string, stemTypes: string[], creditsDeducted: number) {
    safeCapture('stem_separation_requested', {
      sample_id: sampleId,
      stem_types: stemTypes,
      stem_count: stemTypes.length,
      credits_deducted: creditsDeducted,
    });
  },

  stemDownloaded(stemId: string, stemType: string, sampleId: string) {
    safeCapture('stem_downloaded', {
      stem_id: stemId,
      stem_type: stemType,
      sample_id: sampleId,
    });
  },

  // ============================================
  // Performance Events
  // ============================================

  hlsStreamLoaded(sample: Sample, loadTime: number) {
    safeCapture('hls_stream_loaded', {
      sample_id: sample.id,
      load_time_ms: loadTime,
    });
  },

  hlsFallbackUsed(sample: Sample, reason: string) {
    safeCapture('hls_fallback_used', {
      sample_id: sample.id,
      reason,
    });
  },

  audioBufferStalled(sample: Sample, stalledDuration: number) {
    safeCapture('audio_buffer_stalled', {
      sample_id: sample.id,
      stalled_duration_ms: stalledDuration,
    });
  },

  // ============================================
  // Navigation Events
  // ============================================

  pageViewed(pageName: string, additionalProps?: Record<string, any>) {
    safeCapture('page_viewed', {
      page_name: pageName,
      ...additionalProps,
    });
  },

  navigationClicked(destination: string, source: string) {
    safeCapture('navigation_clicked', {
      destination,
      source,
    });
  },

  buttonClicked(buttonName: string, context?: string) {
    safeCapture('button_clicked', {
      button_name: buttonName,
      context,
    });

    // Track ClickButton on TikTok Pixel
    trackTikTokEvent('ClickButton', {
      content_type: 'product',
      content_name: buttonName,
    });
  },

  // ============================================
  // Error Events
  // ============================================

  errorOccurred(errorType: string, errorMessage: string, context?: Record<string, any>) {
    safeCapture('error_occurred', {
      error_type: errorType,
      error_message: errorMessage,
      ...context,
    });
  },

  // ============================================
  // User Preferences
  // ============================================

  themeChanged(theme: 'light' | 'dark') {
    safeCapture('theme_changed', {
      theme,
    });
  },

  settingsChanged(setting: string, value: any) {
    safeCapture('settings_changed', {
      setting,
      value,
    });
  },
};

/**
 * Helper to identify user (usually called automatically by PostHogProvider)
 */
export function identifyUser(userId: string, properties?: Record<string, any>) {
  try {
    if (typeof window === 'undefined') return;
    if (!posthog || !posthog.__loaded) return;
    posthog.identify(userId, properties);
  } catch (error) {
    if (process.env.NODE_ENV === 'development') {
      console.error('[Analytics] Error identifying user:', error);
    }
  }
}

/**
 * Helper to reset user session (on logout)
 */
export function resetUser() {
  try {
    if (typeof window === 'undefined') return;
    if (!posthog || !posthog.__loaded) return;
    posthog.reset();
  } catch (error) {
    if (process.env.NODE_ENV === 'development') {
      console.error('[Analytics] Error resetting user:', error);
    }
  }
}

/**
 * Helper to set user properties
 */
export function setUserProperties(properties: Record<string, any>) {
  try {
    if (typeof window === 'undefined') return;
    if (!posthog || !posthog.__loaded) return;
    posthog.people.set(properties);
  } catch (error) {
    if (process.env.NODE_ENV === 'development') {
      console.error('[Analytics] Error setting user properties:', error);
    }
  }
}

/**
 * Helper to check if a feature flag is enabled
 */
export function isFeatureEnabled(flagKey: string): boolean {
  try {
    if (typeof window === 'undefined') return false;
    if (!posthog || !posthog.__loaded) return false;
    return posthog.isFeatureEnabled(flagKey) || false;
  } catch (error) {
    if (process.env.NODE_ENV === 'development') {
      console.error('[Analytics] Error checking feature flag:', error);
    }
    return false;
  }
}

/**
 * Helper to get feature flag payload
 */
export function getFeatureFlagPayload(flagKey: string): any {
  try {
    if (typeof window === 'undefined') return null;
    if (!posthog || !posthog.__loaded) return null;
    return posthog.getFeatureFlagPayload(flagKey);
  } catch (error) {
    if (process.env.NODE_ENV === 'development') {
      console.error('[Analytics] Error getting feature flag payload:', error);
    }
    return null;
  }
}
