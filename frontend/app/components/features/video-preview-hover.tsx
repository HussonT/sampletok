"use client";

import React, { useState, useRef } from 'react';
import { ExternalLink, Volume2, VolumeX } from 'lucide-react';
import {
  HoverCard,
  HoverCardContent,
  HoverCardTrigger,
} from '@/components/ui/hover-card';
import { Button } from '@/components/ui/button';

interface VideoPreviewHoverProps {
  videoUrl?: string;
  tiktokUrl: string;
}

export function VideoPreviewHover({ videoUrl, tiktokUrl }: VideoPreviewHoverProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [hasError, setHasError] = useState(false);
  const [isMuted, setIsMuted] = useState(true);
  const videoRef = useRef<HTMLVideoElement>(null);

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

  // If no video URL, just render the regular link
  if (!videoUrl) {
    return (
      <a
        href={tiktokUrl || '#'}
        target="_blank"
        rel="noopener noreferrer"
        className="text-primary hover:text-primary/80 underline text-sm flex items-center gap-1"
      >
        View on TikTok
        <ExternalLink className="w-3 h-3" />
      </a>
    );
  }

  return (
    <HoverCard open={isOpen} onOpenChange={handleOpenChange} openDelay={0} closeDelay={100}>
      <HoverCardTrigger asChild>
        <a
          href={tiktokUrl || '#'}
          target="_blank"
          rel="noopener noreferrer"
          className="text-primary hover:text-primary/80 underline text-sm flex items-center gap-1"
          onMouseEnter={() => setIsOpen(true)}
          onMouseLeave={(e) => {
            // Only close if not moving to the content
            const relatedTarget = e.relatedTarget;
            if (!relatedTarget || !(relatedTarget instanceof Element) || !relatedTarget.closest('[role="dialog"]')) {
              setIsOpen(false);
            }
          }}
        >
          View on TikTok
          <ExternalLink className="w-3 h-3" />
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
                <p className="text-xs mt-2">Click to view on TikTok</p>
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
