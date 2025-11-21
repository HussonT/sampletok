'use client';

import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Copy, Check, Facebook, Twitter, Link2 } from 'lucide-react';
import { Instagram } from 'lucide-react';

interface ShareButtonsProps {
  sampleId: string;
  sampleTitle: string;
}

export function ShareButtons({ sampleId, sampleTitle }: ShareButtonsProps) {
  const [copied, setCopied] = useState(false);

  // Generate share URL with UTM parameters
  const getShareUrl = (platform: string) => {
    const baseUrl = typeof window !== 'undefined'
      ? `${window.location.origin}/s/${sampleId}`
      : `https://app.sampletheinternet.com/s/${sampleId}`;

    const params = new URLSearchParams({
      utm_source: platform.toLowerCase(),
      utm_medium: platform === 'copy' ? 'link' : 'social',
      utm_campaign: 'sample_share',
    });

    return `${baseUrl}?${params.toString()}`;
  };

  // Generate platform-specific share URLs
  const shareUrls = {
    twitter: `https://twitter.com/intent/tweet?text=${encodeURIComponent(
      `🎵 Check out this sample: ${sampleTitle}`
    )}&url=${encodeURIComponent(getShareUrl('twitter'))}&via=sampletheinternet`,
    facebook: `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(
      getShareUrl('facebook')
    )}`,
    // Instagram doesn't support direct URL sharing, so we'll just copy the link
    instagram: getShareUrl('instagram'),
    copy: getShareUrl('copy'),
  };

  const handleCopyLink = async () => {
    try {
      await navigator.clipboard.writeText(shareUrls.copy);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (error) {
      console.error('Failed to copy link:', error);
    }
  };

  const handleShare = (platform: 'twitter' | 'facebook') => {
    window.open(
      shareUrls[platform],
      'share-dialog',
      'width=626,height=436'
    );
  };

  return (
    <div className="flex flex-wrap gap-3">
      {/* Twitter Share */}
      <Button
        variant="outline"
        onClick={() => handleShare('twitter')}
        className="flex-1 min-w-[120px]"
      >
        <Twitter className="h-4 w-4 mr-2" />
        Twitter
      </Button>

      {/* Facebook Share */}
      <Button
        variant="outline"
        onClick={() => handleShare('facebook')}
        className="flex-1 min-w-[120px]"
      >
        <Facebook className="h-4 w-4 mr-2" />
        Facebook
      </Button>

      {/* Instagram (just copy link since IG doesn't support direct sharing) */}
      <Button
        variant="outline"
        onClick={handleCopyLink}
        className="flex-1 min-w-[120px]"
      >
        <Instagram className="h-4 w-4 mr-2" />
        Instagram
      </Button>

      {/* Copy Link */}
      <Button
        variant="outline"
        onClick={handleCopyLink}
        className="flex-1 min-w-[120px]"
      >
        {copied ? (
          <>
            <Check className="h-4 w-4 mr-2 text-green-500" />
            Copied!
          </>
        ) : (
          <>
            <Link2 className="h-4 w-4 mr-2" />
            Copy Link
          </>
        )}
      </Button>
    </div>
  );
}
