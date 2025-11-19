'use client';

import { useState, useEffect } from 'react';
import { X, ExternalLink, Music2 } from 'lucide-react';
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
    <div className="fixed inset-0 z-[100] bg-black/95 backdrop-blur-md flex items-center justify-center p-6 animate-in fade-in duration-500">
      {/* Arrow pointing to top-right menu */}
      <div className="absolute top-20 right-20 pointer-events-none">
        <svg width="120" height="120" viewBox="0 0 120 120" className="text-[hsl(338,82%,65%)]">
          {/* Curved arrow path */}
          <path
            d="M 10 110 Q 60 60 100 20"
            fill="none"
            stroke="currentColor"
            strokeWidth="3"
            strokeLinecap="round"
            className="drop-shadow-lg"
          />
          {/* Arrowhead */}
          <path
            d="M 100 20 L 85 25 L 95 35 Z"
            fill="currentColor"
            className="drop-shadow-lg"
          />
        </svg>
        <div className="text-[hsl(338,82%,65%)] text-sm font-semibold -mt-2 text-center drop-shadow-lg">
          Tap here
        </div>
      </div>

      {/* Close button */}
      <button
        onClick={handleDismiss}
        className="absolute top-4 right-4 p-2 rounded-full bg-white/10 hover:bg-white/20 transition-colors"
        aria-label="Continue anyway"
      >
        <X className="w-6 h-6 text-white" />
      </button>

      {/* Content */}
      <div className="max-w-md text-center space-y-6">
        {/* Icon */}
        <div className="flex justify-center mb-6">
          <div className="relative">
            <div className="absolute inset-0 bg-[hsl(338,82%,65%)] blur-3xl opacity-50 animate-pulse" />
            <div className="relative bg-gradient-to-br from-[hsl(338,82%,65%)] to-[hsl(338,82%,55%)] p-6 rounded-3xl">
              <Music2 className="w-16 h-16 text-white" />
            </div>
          </div>
        </div>

        {/* Title */}
        <h2 className="text-3xl font-bold text-white mb-3">
          Better Experience Ahead
        </h2>

        {/* Description */}
        <p className="text-lg text-gray-300 mb-6">
          For the best audio playback and full features, open SampleTok in your default browser
        </p>

        {/* Instructions */}
        <div className="bg-white/5 rounded-xl p-6 mb-6 text-left border border-white/10">
          <p className="text-white font-semibold mb-3 flex items-center gap-2">
            <ExternalLink className="w-5 h-5 text-[hsl(338,82%,65%)]" />
            How to open in browser:
          </p>
          <ol className="space-y-2 text-gray-300 text-sm">
            <li className="flex gap-3">
              <span className="font-bold text-[hsl(338,82%,65%)]">1.</span>
              <span>Tap the <strong className="text-white">⋯ menu</strong> in the top-right corner</span>
            </li>
            <li className="flex gap-3">
              <span className="font-bold text-[hsl(338,82%,65%)]">2.</span>
              <span>Select <strong className="text-white">"Open in Browser"</strong></span>
            </li>
            <li className="flex gap-3">
              <span className="font-bold text-[hsl(338,82%,65%)]">3.</span>
              <span>Enjoy full audio playback!</span>
            </li>
          </ol>
        </div>

        {/* Continue anyway button */}
        <Button
          onClick={handleDismiss}
          variant="ghost"
          className="text-gray-400 hover:text-white hover:bg-white/10"
        >
          Continue in TikTok anyway
        </Button>
      </div>
    </div>
  );
}
