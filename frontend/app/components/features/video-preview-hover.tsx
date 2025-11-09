"use client";

import React, { useState, useRef } from 'react';
import { Volume2, VolumeX } from 'lucide-react';
import {
  HoverCard,
  HoverCardContent,
  HoverCardTrigger,
} from '@/components/ui/hover-card';
import { Button } from '@/components/ui/button';

// TikTok icon component
const TikTokIcon = ({ className }: { className?: string }) => (
  <svg
    viewBox="0 0 24 24"
    fill="currentColor"
    className={className}
    xmlns="http://www.w3.org/2000/svg"
  >
    <path d="M19.59 6.69a4.83 4.83 0 0 1-3.77-4.25V2h-3.45v13.67a2.89 2.89 0 0 1-5.2 1.74 2.89 2.89 0 0 1 2.31-4.64 2.93 2.93 0 0 1 .88.13V9.4a6.84 6.84 0 0 0-1-.05A6.33 6.33 0 0 0 5 20.1a6.34 6.34 0 0 0 10.86-4.43v-7a8.16 8.16 0 0 0 4.77 1.52v-3.4a4.85 4.85 0 0 1-1-.1z"/>
  </svg>
);

// Instagram icon component
const InstagramIcon = ({ className }: { className?: string }) => (
  <svg
    viewBox="0 0 24 24"
    fill="currentColor"
    className={className}
    xmlns="http://www.w3.org/2000/svg"
  >
    <path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zm0-2.163c-3.259 0-3.667.014-4.947.072-4.358.2-6.78 2.618-6.98 6.98-.059 1.281-.073 1.689-.073 4.948 0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98 1.281.058 1.689.072 4.948.072 3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98-1.281-.059-1.69-.073-4.949-.073zm0 5.838c-3.403 0-6.162 2.759-6.162 6.162s2.759 6.163 6.162 6.163 6.162-2.759 6.162-6.163c0-3.403-2.759-6.162-6.162-6.162zm0 10.162c-2.209 0-4-1.79-4-4 0-2.209 1.791-4 4-4s4 1.791 4 4c0 2.21-1.791 4-4 4zm6.406-11.845c-.796 0-1.441.645-1.441 1.44s.645 1.44 1.441 1.44c.795 0 1.439-.645 1.439-1.44s-.644-1.44-1.439-1.44z"/>
  </svg>
);

interface VideoPreviewHoverProps {
  videoUrl?: string;
  tiktokUrl?: string;
  instagramUrl?: string;
  source?: 'tiktok' | 'instagram';
}

export function VideoPreviewHover({ videoUrl, tiktokUrl, instagramUrl, source = 'tiktok' }: VideoPreviewHoverProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [hasError, setHasError] = useState(false);
  const [isMuted, setIsMuted] = useState(true);
  const videoRef = useRef<HTMLVideoElement>(null);

  // Determine which URL and icon to use based on source
  const platformUrl = source === 'instagram' ? instagramUrl : tiktokUrl;
  const PlatformIcon = source === 'instagram' ? InstagramIcon : TikTokIcon;
  const platformName = source === 'instagram' ? 'Instagram' : 'TikTok';

  const handleOpenChange = (open: boolean) => {
    setIsOpen(open);

    if (open && videoRef.current) {
      // Reset error state and try to play
      setHasError(false);
      setIsMuted(true); // Reset to muted on new hover
      videoRef.current.muted = true;

      // Small delay to ensure video element is ready
      setTimeout(() => {
        videoRef.current?.play().catch((error) => {
          console.error('Video play error:', error);
          setHasError(true);
        });
      }, 50);
    } else if (!open && videoRef.current) {
      // Pause and reset when closing
      videoRef.current.pause();
      videoRef.current.currentTime = 0;
    }
  };

  const toggleMute = () => {
    if (videoRef.current) {
      const newMutedState = !isMuted;
      setIsMuted(newMutedState);
      videoRef.current.muted = newMutedState;
    }
  };

  // If no video URL, just render the regular icon button
  if (!videoUrl) {
    return (
      <a
        href={platformUrl || '#'}
        target="_blank"
        rel="noopener noreferrer"
        className="flex items-center justify-center w-8 h-8 hover:bg-secondary/50 rounded-md transition-colors group"
        title={`View on ${platformName}`}
      >
        <PlatformIcon className="w-5 h-5 text-muted-foreground group-hover:text-primary transition-colors" />
      </a>
    );
  }

  return (
    <HoverCard open={isOpen} onOpenChange={handleOpenChange} openDelay={0} closeDelay={100}>
      <HoverCardTrigger asChild>
        <a
          href={platformUrl || '#'}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center justify-center w-8 h-8 hover:bg-secondary/50 rounded-md transition-colors group"
          title={`View on ${platformName}`}
          onMouseEnter={() => setIsOpen(true)}
          onMouseLeave={(e) => {
            // Only close if not moving to the content
            const relatedTarget = e.relatedTarget;
            if (!relatedTarget || !(relatedTarget instanceof Element) || !relatedTarget.closest('[role="dialog"]')) {
              setIsOpen(false);
            }
          }}
        >
          <PlatformIcon className="w-5 h-5 text-muted-foreground group-hover:text-primary transition-colors" />
        </a>
      </HoverCardTrigger>
      <HoverCardContent
        side="left"
        align="center"
        className="w-[320px] p-0 border-2 border-primary/20"
        onMouseLeave={() => setIsOpen(false)}
      >
        <div className="relative bg-black rounded-md overflow-hidden" style={{ aspectRatio: '9/16' }}>
          {!hasError ? (
            <video
              ref={videoRef}
              src={videoUrl}
              loop
              muted
              playsInline
              preload="auto"
              className="w-full h-full object-cover"
              onError={() => setHasError(true)}
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center text-muted-foreground text-sm">
              <div className="text-center p-4">
                <p>Video preview unavailable</p>
                <p className="text-xs mt-2">Click to view on {platformName}</p>
              </div>
            </div>
          )}
          {isOpen && !hasError && (
            <>
              <div className="absolute bottom-2 left-2 bg-black/50 text-white text-xs px-2 py-1 rounded">
                Preview
              </div>
              <Button
                size="sm"
                variant="ghost"
                className="absolute bottom-2 right-2 bg-black/70 hover:bg-black/90 text-white p-2 h-8 w-8"
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  toggleMute();
                }}
              >
                {isMuted ? (
                  <VolumeX className="w-4 h-4" />
                ) : (
                  <Volume2 className="w-4 h-4" />
                )}
              </Button>
            </>
          )}
        </div>
      </HoverCardContent>
    </HoverCard>
  );
}
