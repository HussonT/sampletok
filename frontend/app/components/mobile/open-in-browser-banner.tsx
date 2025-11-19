'use client';

import { useState, useEffect } from 'react';
import { ExternalLink } from 'lucide-react';
import { isTikTokBrowser } from '@/lib/browser-detection';
import { Button } from '@/components/ui/button';

/**
 * Open In Browser Overlay
 *
 * Shows a full-screen overlay when user is browsing in TikTok's in-app browser.
 * Encourages them to open in their default browser for full functionality.
 *
 * Features:
 * - Auto-detects TikTok browser
 * - Full-screen overlay (impossible to miss)
 * - Temporarily dismissible for this session
 * - Clear instructions on how to open in browser
 */
export function OpenInBrowserBanner() {
  const [isVisible, setIsVisible] = useState(false);
  const [isMounted, setIsMounted] = useState(false);

  useEffect(() => {
    setIsMounted(true);

    // Check if we're in TikTok browser
    if (!isTikTokBrowser()) return;

    // Always show overlay in TikTok browser - don't check localStorage
    // This is intentional: TikTok's webview has playback limitations
    // and users should be encouraged to use their default browser
    const timer = setTimeout(() => {
      setIsVisible(true);
    }, 800);

    return () => clearTimeout(timer);
  }, []);

  const handleDismiss = () => {
    // Temporarily hide for this session only
    // Will reappear on next page load
    setIsVisible(false);
  };

  // Don't render on server or if not visible
  if (!isMounted || !isVisible) return null;

  return (
    <div className="fixed inset-0 z-[100] bg-black/95 backdrop-blur-md flex flex-col items-center justify-center p-4 animate-in fade-in duration-500">
      {/* Arrow pointing to top-right menu */}
      <div className="absolute top-4 right-4 pointer-events-none">
        <svg width="80" height="80" viewBox="0 0 80 80" className="text-[hsl(338,82%,65%)]">
          {/* Curved arrow path */}
          <path
            d="M 10 70 Q 40 40 65 15"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.5"
            strokeLinecap="round"
            className="drop-shadow-lg"
          />
          {/* Arrowhead */}
          <path
            d="M 65 15 L 55 18 L 62 25 Z"
            fill="currentColor"
            className="drop-shadow-lg"
          />
        </svg>
        <div className="text-[hsl(338,82%,65%)] text-xs font-semibold -mt-1 text-center drop-shadow-lg">
          Tap here
        </div>
      </div>

      {/* Content */}
      <div className="max-w-md w-full text-center space-y-4 mt-8">
        {/* Title */}
        <h2 className="text-2xl sm:text-3xl font-bold text-white">
          Better Experience Ahead
        </h2>

        {/* Description */}
        <p className="text-base sm:text-lg text-gray-300">
          For the best audio playback and full features, open SampleTok in your default browser
        </p>

        {/* Instructions */}
        <div className="bg-white/5 rounded-xl p-4 sm:p-6 text-left border border-white/10">
          <p className="text-white font-semibold mb-3 flex items-center gap-2 text-sm sm:text-base">
            <ExternalLink className="w-4 h-4 sm:w-5 sm:h-5 text-[hsl(338,82%,65%)]" />
            How to open in browser:
          </p>
          <ol className="space-y-2 text-gray-300 text-sm">
            <li className="flex gap-2">
              <span className="font-bold text-[hsl(338,82%,65%)] shrink-0">1.</span>
              <span>Tap the <strong className="text-white">⋯ menu</strong> in the top-right corner</span>
            </li>
            <li className="flex gap-2">
              <span className="font-bold text-[hsl(338,82%,65%)] shrink-0">2.</span>
              <span>Select <strong className="text-white">"Open in Browser"</strong></span>
            </li>
            <li className="flex gap-2">
              <span className="font-bold text-[hsl(338,82%,65%)] shrink-0">3.</span>
              <span>Enjoy full audio playback!</span>
            </li>
          </ol>
        </div>

        {/* Continue anyway button */}
        <Button
          onClick={handleDismiss}
          variant="ghost"
          className="text-gray-400 hover:text-white hover:bg-white/10 mt-4"
        >
          Continue in TikTok anyway
        </Button>
      </div>
    </div>
  );
}
