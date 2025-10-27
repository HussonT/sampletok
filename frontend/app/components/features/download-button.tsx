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

      // Call the download endpoint (uses Clerk ID from JWT for authentication)
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/samples/${sample.id}/download`,
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
        description: `${format.toUpperCase()} file saved to your downloads`,
      });

      onDownloadComplete?.();
    } catch (error) {
      console.error('Download error:', error);
      toast.error('Download failed', {
        id: 'download',
        description: 'Please try again or contact support if the issue persists',
      });
    } finally {
      setIsDownloading(false);
    }
  };

  const getTooltipText = () => {
    if (!isSignedIn) {
      return 'Sign in to download';
    }
    if (sample.is_downloaded) {
      return `Download ${format.toUpperCase()} again`;
    }
    return `Download ${format.toUpperCase()}`;
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
