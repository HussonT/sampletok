'use client';

import { useState, useEffect } from 'react';
import { X, MoveUpRight } from 'lucide-react';
import { isTikTokBrowser } from '@/lib/browser-detection';

/**
 * Open In Browser Banner
 *
 * Shows a dismissible banner when user is browsing in TikTok's in-app browser.
 * Points to the top-right menu (where TikTok's "Open in Browser" option is located).
 *
 * Features:
 * - Auto-detects TikTok browser
 * - Dismissible (stores preference in localStorage)
 * - Positioned at top of screen with arrow pointing to top-right
 * - Mimics TikTok's native UI pattern
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
    }, 1500);

    return () => clearTimeout(timer);
  }, []);

  const handleDismiss = () => {
    setIsVisible(false);
    localStorage.setItem('open-in-browser-dismissed', 'true');
  };

  // Don't render on server or if not visible
  if (!isMounted || !isVisible) return null;

  return (
    <div className="fixed top-0 left-0 right-0 z-50 animate-in slide-in-from-top duration-300">
      <div className="bg-gradient-to-r from-[hsl(338,82%,65%)] to-[hsl(338,82%,55%)] text-white px-4 py-2.5 shadow-lg">
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-2 flex-1 min-w-0">
            <p className="text-sm font-medium">
              Tap the menu
            </p>
            <MoveUpRight className="w-4 h-4 animate-pulse" />
            <p className="text-sm font-medium truncate">
              to open in browser for full experience
            </p>
          </div>

          <button
            onClick={handleDismiss}
            className="p-1 rounded hover:bg-white/20 transition-colors flex-shrink-0"
            aria-label="Dismiss"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
