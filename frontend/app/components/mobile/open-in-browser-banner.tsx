'use client';

import { useState, useEffect } from 'react';
import { ExternalLink, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { isTikTokBrowser, getBrowserName, openInDefaultBrowser } from '@/lib/browser-detection';

/**
 * Open In Browser Banner
 *
 * Shows a dismissible banner when user is browsing in TikTok's in-app browser.
 * Encourages them to open in their default browser for better experience.
 *
 * Features:
 * - Auto-detects TikTok browser
 * - Dismissible (stores preference in localStorage)
 * - Positioned at top of screen with subtle animation
 * - Clear CTA to open in default browser
 */
export function OpenInBrowserBanner() {
  const [isVisible, setIsVisible] = useState(false);
  const [isMounted, setIsMounted] = useState(false);

  useEffect(() => {
    setIsMounted(true);

    // Check if we're in TikTok browser
    if (!isTikTokBrowser()) return;

    // Check if user has dismissed this banner before
    const dismissed = localStorage.getItem('open-in-browser-dismissed');
    if (dismissed === 'true') return;

    // Show banner after a brief delay for better UX
    const timer = setTimeout(() => {
      setIsVisible(true);
    }, 1000);

    return () => clearTimeout(timer);
  }, []);

  const handleDismiss = () => {
    setIsVisible(false);
    localStorage.setItem('open-in-browser-dismissed', 'true');
  };

  const handleOpenInBrowser = () => {
    openInDefaultBrowser();
    handleDismiss();
  };

  // Don't render on server or if not visible
  if (!isMounted || !isVisible) return null;

  return (
    <div className="fixed top-0 left-0 right-0 z-50 animate-in slide-in-from-top duration-300">
      <div className="bg-gradient-to-r from-[hsl(338,82%,65%)] to-[hsl(338,82%,55%)] text-white px-4 py-3 shadow-lg">
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-2 flex-1 min-w-0">
            <ExternalLink className="w-4 h-4 flex-shrink-0" />
            <p className="text-sm font-medium truncate">
              For the best experience, open in your browser
            </p>
          </div>

          <div className="flex items-center gap-2 flex-shrink-0">
            <Button
              size="sm"
              variant="secondary"
              className="h-7 px-3 text-xs bg-white/20 hover:bg-white/30 text-white border-0"
              onClick={handleOpenInBrowser}
            >
              Open
            </Button>
            <button
              onClick={handleDismiss}
              className="p-1 rounded hover:bg-white/20 transition-colors"
              aria-label="Dismiss"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
