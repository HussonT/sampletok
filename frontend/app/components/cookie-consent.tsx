'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import Link from 'next/link';
import posthog from 'posthog-js';

export function CookieConsent() {
  const [showBanner, setShowBanner] = useState(false);

  useEffect(() => {
    // Check if user has already made a choice
    const consent = localStorage.getItem('cookie_consent');
    if (!consent) {
      // Delay showing banner by 1 second for better UX
      const timer = setTimeout(() => {
        setShowBanner(true);
      }, 1000);
      return () => clearTimeout(timer);
    } else if (consent === 'accepted') {
      // User previously accepted, ensure tracking is enabled
      posthog.opt_in_capturing();
    } else if (consent === 'declined') {
      // User previously declined, ensure tracking is disabled
      posthog.opt_out_capturing();
    }
  }, []);

  const acceptCookies = () => {
    localStorage.setItem('cookie_consent', 'accepted');
    posthog.opt_in_capturing();
    setShowBanner(false);

    // Track consent acceptance
    posthog.capture('cookie_consent_given', {
      consent_type: 'all',
    });

    // Trigger custom event for TikTok Pixel to reload
    window.dispatchEvent(new CustomEvent('cookieConsentChanged', { detail: 'accepted' }));
  };

  const declineCookies = () => {
    localStorage.setItem('cookie_consent', 'declined');
    posthog.opt_out_capturing();
    setShowBanner(false);

    // This will still be captured if opt_out_capturing_by_default is false
    posthog.capture('cookie_consent_declined');
  };

  if (!showBanner) return null;

  return (
    <div className="fixed bottom-0 left-0 right-0 z-50 p-4 md:p-6 animate-in slide-in-from-bottom duration-300">
      <Card className="mx-auto max-w-4xl p-4 md:p-6 shadow-lg border-2 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div className="flex-1">
            <h3 className="text-lg font-semibold mb-2">Cookie Consent</h3>
            <p className="text-sm text-muted-foreground">
              We use cookies to improve your experience, analyze usage, and personalize content.
              By clicking &quot;Accept&quot;, you consent to our use of cookies. Learn more in our{' '}
              <Link href="/privacy" className="underline hover:text-primary">
                Privacy Policy
              </Link>
              .
            </p>
          </div>
          <div className="flex gap-3">
            <Button variant="outline" onClick={declineCookies} className="flex-1 md:flex-none">
              Decline
            </Button>
            <Button onClick={acceptCookies} className="flex-1 md:flex-none">
              Accept
            </Button>
          </div>
        </div>
      </Card>
    </div>
  );
}
