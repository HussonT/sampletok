"use client";

import React, { useState } from 'react';
import { useAuth, useClerk } from '@clerk/nextjs';
import { Button } from '@/components/ui/button';
import { Download, Loader2 } from 'lucide-react';
import { Sample } from '@/types/api';
import { toast } from 'sonner';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';

interface DownloadButtonProps {
  sample: Sample;
  format?: 'wav' | 'mp3';
  variant?: 'default' | 'ghost' | 'outline';
  size?: 'default' | 'sm' | 'lg' | 'icon';
  className?: string;
  showCount?: boolean;
  onDownloadComplete?: () => void;
}

export function DownloadButton({
  sample,
  format = 'wav',
  variant = 'ghost',
  size = 'sm',
  className = '',
  showCount = false,
  onDownloadComplete
}: DownloadButtonProps) {
  const { isSignedIn, getToken } = useAuth();
  const { openSignUp } = useClerk();
  const [isDownloading, setIsDownloading] = useState(false);

  const handleDownload = async () => {
    // Open Clerk sign-up modal if not authenticated
    if (!isSignedIn) {
      const currentUrl = window.location.pathname + window.location.search;
      openSignUp({
        redirectUrl: currentUrl,
        afterSignUpUrl: currentUrl,
      });
      return;
    }

    try {
      setIsDownloading(true);
      toast.loading('Starting download...', { id: 'download' });

      // Ensure API URL is configured
      const apiUrl = process.env.NEXT_PUBLIC_API_URL;
      if (!apiUrl) {
        throw new Error('API URL not configured. Please set NEXT_PUBLIC_API_URL environment variable.');
      }

      // Call the download endpoint (uses Clerk ID from JWT for authentication)
      const response = await fetch(
        `${apiUrl}/api/v1/samples/${sample.id}/download`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${await getToken()}`,
          },
          body: JSON.stringify({ download_type: format }),
        }
      );

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));

        // Handle 403 (no subscription or no credits) with helpful messages
        if (response.status === 403) {
          const detail = errorData.detail || '';

          if (detail.includes('subscription required') || detail.includes('Active subscription')) {
            toast.error('Subscription Required', {
              id: 'download',
              description: 'You need an active subscription to download samples.',
              action: {
                label: 'Subscribe Now',
                onClick: () => window.location.href = '/pricing'
              },
              duration: 5000,
            });
            return;
          }

          if (detail.includes('Insufficient credits') || detail.includes('credits')) {
            toast.error('No Credits Available', {
              id: 'download',
              description: 'You need at least 1 credit to download. Top up your credits to continue.',
              action: {
                label: 'Buy Credits',
                onClick: () => window.location.href = '/top-up'
              },
              duration: 5000,
            });
            return;
          }
        }

        // Only log unexpected errors (not 403s which are handled above)
        console.error('Download failed:', response.status, errorData);
        throw new Error(errorData.detail || 'Download failed');
      }

      // Get the blob and trigger download
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${sample.creator_username || 'unknown'}_${sample.id}.${format}`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);

      toast.success('Download complete!', {
        id: 'download',
        description: sample.is_downloaded
          ? `${format.toUpperCase()} file saved to your downloads (Free re-download)`
          : `${format.toUpperCase()} file saved to your downloads (1 credit used)`,
      });

      onDownloadComplete?.();
    } catch (error) {
      console.error('Download error:', error);

      // Show helpful error message
      const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';

      // If error mentions credits or subscription, show helpful toast
      if (errorMessage.toLowerCase().includes('credit') || errorMessage.toLowerCase().includes('subscription')) {
        toast.error('Cannot Download', {
          id: 'download',
          description: errorMessage,
          action: {
            label: errorMessage.toLowerCase().includes('subscription') ? 'Subscribe' : 'Buy Credits',
            onClick: () => window.location.href = errorMessage.toLowerCase().includes('subscription') ? '/pricing' : '/top-up'
          },
          duration: 5000,
        });
      } else {
        toast.error('Download failed', {
          id: 'download',
          description: errorMessage || 'Please try again or contact support if the issue persists',
        });
      }
    } finally {
      setIsDownloading(false);
    }
  };

  const getTooltipText = () => {
    if (!isSignedIn) {
      return 'Sign in to download';
    }
    if (sample.is_downloaded) {
      return `Download ${format.toUpperCase()} again (Free - Already purchased)`;
    }
    return `Download ${format.toUpperCase()} (1 credit)`;
  };

  const getButtonText = () => {
    if (isDownloading) {
      return null;
    }
    if (showCount && sample.download_count) {
      return `${sample.download_count}`;
    }
    return null;
  };

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <Button
            variant={variant}
            size={size}
            className={`${className} ${sample.is_downloaded ? 'text-pink-500 hover:text-pink-600' : ''}`}
            onClick={handleDownload}
            disabled={isDownloading}
          >
            {isDownloading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <>
                <Download className={`w-4 h-4 ${sample.is_downloaded ? 'fill-current' : ''}`} />
                {getButtonText() && <span className="ml-1">{getButtonText()}</span>}
              </>
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
