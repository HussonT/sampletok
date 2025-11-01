"use client";

import React, { useState, useEffect } from 'react';
import { useAuth } from '@clerk/nextjs';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Heart, Loader2 } from 'lucide-react';
import { Stem } from '@/types/api';
import { createAuthenticatedClient } from '@/lib/api-client';
import { toast } from 'sonner';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';

interface StemFavoriteButtonProps {
  stem: Stem;
  variant?: 'default' | 'ghost' | 'outline';
  size?: 'default' | 'sm' | 'lg' | 'icon';
  className?: string;
  onFavoriteChange?: (isFavorited: boolean) => void;
}

export function StemFavoriteButton({
  stem,
  variant = 'ghost',
  size = 'sm',
  className = '',
  onFavoriteChange
}: StemFavoriteButtonProps) {
  const { isSignedIn, getToken } = useAuth();
  const router = useRouter();

  // Local state for optimistic UI updates
  const [isFavorited, setIsFavorited] = useState(stem.is_favorited || false);
  const [isLoading, setIsLoading] = useState(false);

  // Sync with prop changes
  useEffect(() => {
    setIsFavorited(stem.is_favorited || false);
  }, [stem.is_favorited]);

  const handleToggleFavorite = async () => {
    // Redirect to sign-in if not authenticated
    if (!isSignedIn) {
      toast.info('Please sign in to add favorites', {
        description: 'You need to be signed in to save favorites',
      });
      // Store the current URL as return URL
      const returnUrl = encodeURIComponent(window.location.pathname + window.location.search);
      router.push(`/sign-in?redirect_url=${returnUrl}`);
      return;
    }

    // Optimistic UI update
    const previousState = isFavorited;
    const willBeFavorited = !isFavorited;
    setIsFavorited(willBeFavorited);
    onFavoriteChange?.(willBeFavorited);

    try {
      setIsLoading(true);

      // Create authenticated API client (uses Clerk ID from JWT)
      const api = createAuthenticatedClient(getToken);

      if (previousState) {
        // Remove from favorites
        await api.delete(`/stems/${stem.id}/favorite`);
        toast.success('Removed from favorites', {
          description: 'Stem removed from your favorites',
        });
      } else {
        // Add to favorites
        await api.post(`/stems/${stem.id}/favorite`);
        toast.success('Added to favorites', {
          description: 'Stem saved to your favorites',
        });
      }

    } catch (error) {
      console.error('Favorite toggle error:', error);
      // Revert optimistic update on error
      setIsFavorited(previousState);
      onFavoriteChange?.(previousState);
      toast.error('Failed to update favorite', {
        description: 'Please try again or contact support if the issue persists',
      });
    } finally {
      setIsLoading(false);
    }
  };

  const getTooltipText = () => {
    if (!isSignedIn) {
      return 'Sign in to favorite';
    }
    return isFavorited ? 'Remove from favorites' : 'Add to favorites';
  };

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <Button
            variant={variant}
            size={size}
            className={`${className} ${isFavorited ? 'text-red-500 hover:text-red-600' : ''}`}
            onClick={handleToggleFavorite}
            disabled={isLoading}
          >
            {isLoading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Heart
                className={`w-4 h-4 ${isFavorited ? 'fill-current' : ''}`}
              />
            )}
          </Button>
        </TooltipTrigger>
        <TooltipContent side="top">
          <p>{getTooltipText()}</p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
