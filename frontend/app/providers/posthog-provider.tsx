'use client';

import { Suspense, useEffect, useState, createContext, useContext } from 'react';
import { usePathname, useSearchParams } from 'next/navigation';
import { useAuth, useUser } from '@clerk/nextjs';
import posthog from 'posthog-js';
import { PostHogProvider as PHProvider } from 'posthog-js/react';

/**
 * PostHog Provider for React integration
 *
 * Handles:
 * - PostHog initialization with proper loading states
 * - Pageview tracking
 * - User identification via Clerk
 * - PWA detection
 */

// Context to track PostHog initialization status
const PostHogContext = createContext<{ isLoaded: boolean }>({ isLoaded: false });

export const usePostHog = () => useContext(PostHogContext);

function PostHogPageViewInner(): null {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const { isSignedIn, userId } = useAuth();
  const { user } = useUser();
  const { isLoaded } = usePostHog();

  // Track pageviews
  useEffect(() => {
    if (!isLoaded || !pathname) return;

    try {
      let url = window.origin + pathname;
      if (searchParams.toString()) {
        url = url + `?${searchParams.toString()}`;
      }

      posthog.capture('$pageview', {
        $current_url: url,
      });
    } catch (error) {
      console.error('[PostHog] Error tracking pageview:', error);
    }
  }, [pathname, searchParams, isLoaded]);

  // Identify user with Clerk data
  useEffect(() => {
    if (!isLoaded) return;

    try {
      if (isSignedIn && userId && user) {
        posthog.identify(userId, {
          email: user.primaryEmailAddress?.emailAddress,
          username: user.username,
          first_name: user.firstName,
          last_name: user.lastName,
          created_at: user.createdAt,
        });

        // Set user properties
        posthog.people.set({
          email: user.primaryEmailAddress?.emailAddress,
          name: `${user.firstName} ${user.lastName}`.trim(),
        });
      }

      // Reset on logout (critical for shared devices/PWA)
      if (!isSignedIn && posthog.get_distinct_id()) {
        posthog.reset();
      }
    } catch (error) {
      console.error('[PostHog] Error identifying user:', error);
    }
  }, [isSignedIn, userId, user, isLoaded]);

  return null;
}

function PostHogPageView() {
  return (
    <Suspense fallback={null}>
      <PostHogPageViewInner />
    </Suspense>
  );
}

function PWADetection(): null {
  const { isLoaded } = usePostHog();

  useEffect(() => {
    if (!isLoaded) return;

    try {
      // Detect if running as PWA
      const isPWA = window.matchMedia('(display-mode: standalone)').matches ||
                    (window.navigator as any).standalone ||
                    document.referrer.includes('android-app://');

      if (isPWA) {
        posthog.capture('pwa_installed', {
          platform: navigator.platform,
          user_agent: navigator.userAgent,
        });
      }

      // Listen for installation event
      const handleBeforeInstall = (e: Event) => {
        e.preventDefault();
        posthog.capture('pwa_install_prompt_shown');
      };

      const handleAppInstalled = () => {
        posthog.capture('pwa_installed', {
          platform: navigator.platform,
          user_agent: navigator.userAgent,
        });
      };

      window.addEventListener('beforeinstallprompt', handleBeforeInstall);
      window.addEventListener('appinstalled', handleAppInstalled);

      return () => {
        window.removeEventListener('beforeinstallprompt', handleBeforeInstall);
        window.removeEventListener('appinstalled', handleAppInstalled);
      };
    } catch (error) {
      console.error('[PostHog] Error in PWA detection:', error);
    }
  }, [isLoaded]);

  return null;
}

export function PostHogProvider({ children }: { children: React.ReactNode }) {
  const [isLoaded, setIsLoaded] = useState(false);

  // Initialize PostHog once on mount
  useEffect(() => {
    const posthogKey = process.env.NEXT_PUBLIC_POSTHOG_KEY;
    const posthogHost = process.env.NEXT_PUBLIC_POSTHOG_HOST;

    // Skip PostHog initialization if no key is provided
    if (!posthogKey) {
      if (process.env.NODE_ENV === 'development') {
        console.log('[PostHog] Skipping - no API key provided');
      }
      return;
    }

    // Already initialized
    if (posthog.__loaded) {
      setIsLoaded(true);
      return;
    }

    if (typeof window === 'undefined') {
      return;
    }

    const apiHost = posthogHost || 'https://us.i.posthog.com'; // Default to US host

    if (process.env.NODE_ENV === 'development') {
      console.log('[PostHog] Initializing with host:', apiHost);
    }

    try {
      posthog.init(posthogKey, {
        api_host: apiHost,
        person_profiles: 'identified_only',
        capture_pageview: false, // We handle this manually
        capture_pageleave: true,
        session_recording: {
          recordCrossOriginIframes: false,
          maskAllInputs: true,
          maskTextSelector: '[data-private]',
        },
        autocapture: true,
        capture_performance: true,
        capture_exceptions: false, // Disable to avoid recursive errors
        opt_in_site_apps: true, // Enable PostHog site apps
        loaded: (ph) => {
          if (process.env.NODE_ENV === 'development') {
            ph.debug();
            console.log('[PostHog] Initialized successfully with host:', apiHost);
          }
          setIsLoaded(true);
        },
        on_xhr_error: (error) => {
          // Silently handle network errors
          if (process.env.NODE_ENV === 'development') {
            console.warn('[PostHog] Network error (non-critical):', error);
          }
        },
      });
    } catch (error) {
      console.error('[PostHog] Failed to initialize:', error);
    }
  }, []);

  // If no PostHog key, just render children without PostHog wrapper
  if (!process.env.NEXT_PUBLIC_POSTHOG_KEY) {
    return <>{children}</>;
  }

  return (
    <PostHogContext.Provider value={{ isLoaded }}>
      <PHProvider client={posthog}>
        <PostHogPageView />
        <PWADetection />
        {children}
      </PHProvider>
    </PostHogContext.Provider>
  );
}
