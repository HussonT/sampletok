'use client';

import { useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { analytics } from '@/lib/analytics';
import posthog from 'posthog-js';

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);

    // Track error with analytics
    analytics.errorOccurred('app_error', error.message, {
      error_digest: error.digest,
      error_stack: error.stack,
    });

    // Also capture exception for error tracking
    if (posthog && posthog.__loaded) {
      posthog.captureException(error);
    }
  }, [error]);

  return (
    <div className="flex flex-col items-center justify-center min-h-screen gap-4">
      <h2 className="text-2xl font-bold">Something went wrong!</h2>
      <p className="text-muted-foreground">{error.message}</p>
      <Button onClick={reset}>Try again</Button>
    </div>
  );
}