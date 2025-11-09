import React from 'react';
import Image from 'next/image';
import { TikTokCreator, InstagramCreator } from '@/types/api';
import { HoverCard, HoverCardContent, HoverCardTrigger } from '@/components/ui/hover-card';
import { Users, Heart, Video, CheckCircle, ImageIcon } from 'lucide-react';
import { getAvatarWithFallback } from '@/lib/avatar';

interface CreatorHoverCardProps {
  creator: TikTokCreator | InstagramCreator;
  children: React.ReactNode;
}

export function CreatorHoverCard({ creator, children }: CreatorHoverCardProps) {
  const formatCount = (count: number): string => {
    if (count >= 1000000) {
      return `${(count / 1000000).toFixed(1)}M`;
    } else if (count >= 1000) {
      return `${(count / 1000).toFixed(0)}K`;
    }
    return count.toString();
  };

  // Type guard to check if creator is TikTok or Instagram
  const isTikTokCreator = (creator: TikTokCreator | InstagramCreator): creator is TikTokCreator => {
    return 'tiktok_id' in creator;
  };

  const isInstagramCreator = (creator: TikTokCreator | InstagramCreator): creator is InstagramCreator => {
    return 'instagram_id' in creator;
  };

  // Get avatar URL based on creator type
  const getAvatarUrl = () => {
    if (isTikTokCreator(creator)) {
      return creator.avatar_medium || creator.avatar_large;
    } else if (isInstagramCreator(creator)) {
      return creator.profile_pic_url;
    }
    return null;
  };

  // Get display name based on creator type
  const getDisplayName = () => {
    if (isTikTokCreator(creator)) {
      return creator.nickname || creator.username;
    } else {
      return creator.full_name || creator.username;
    }
  };

  // Get verification status based on creator type
  const isVerified = () => {
    if (isTikTokCreator(creator)) {
      return creator.verified;
    } else if (isInstagramCreator(creator)) {
      return creator.is_verified;
    }
    return false;
  };

  return (
    <HoverCard>
      <HoverCardTrigger asChild>
        {children}
      </HoverCardTrigger>
      <HoverCardContent className="w-80" side="top">
        <div className="flex gap-4">
          {/* Avatar */}
          <div className="flex-shrink-0 relative">
            <Image
              src={getAvatarWithFallback(getAvatarUrl(), creator.username)}
              alt={getDisplayName()}
              width={64}
              height={64}
              className="w-16 h-16 rounded-full object-cover"
              unoptimized
              onError={(e) => {
                // Fallback to generated avatar on error
                const target = e.target as HTMLImageElement;
                target.src = getAvatarWithFallback(null, creator.username);
              }}
            />
          </div>

          {/* Creator Info */}
          <div className="flex-1 space-y-2">
            {/* Name and username */}
            <div>
              <div className="flex items-center gap-2">
                <h4 className="font-semibold text-sm">
                  {getDisplayName()}
                </h4>
                {isVerified() && (
                  <CheckCircle className="w-4 h-4 text-blue-500 fill-blue-500" />
                )}
              </div>
              <p className="text-xs text-muted-foreground">@{creator.username}</p>
            </div>

            {/* Bio/Signature (TikTok only) */}
            {isTikTokCreator(creator) && creator.signature && (
              <p className="text-xs text-muted-foreground line-clamp-2">
                {creator.signature}
              </p>
            )}

            {/* Private account indicator (Instagram only) */}
            {isInstagramCreator(creator) && creator.is_private && (
              <p className="text-xs text-muted-foreground italic">
                🔒 Private account
              </p>
            )}

            {/* Stats */}
            <div className="grid grid-cols-3 gap-2 pt-2">
              <div className="flex flex-col items-center">
                <div className="flex items-center gap-1 text-xs font-semibold">
                  <Users className="w-3 h-3" />
                  <span>{formatCount(creator.follower_count)}</span>
                </div>
                <span className="text-xs text-muted-foreground">Followers</span>
              </div>

              {isTikTokCreator(creator) && (
                <div className="flex flex-col items-center">
                  <div className="flex items-center gap-1 text-xs font-semibold">
                    <Heart className="w-3 h-3" />
                    <span>{formatCount(creator.heart_count)}</span>
                  </div>
                  <span className="text-xs text-muted-foreground">Likes</span>
                </div>
              )}

              {isInstagramCreator(creator) && (
                <div className="flex flex-col items-center">
                  <div className="flex items-center gap-1 text-xs font-semibold">
                    <ImageIcon className="w-3 h-3" />
                    <span>{formatCount(creator.media_count)}</span>
                  </div>
                  <span className="text-xs text-muted-foreground">Posts</span>
                </div>
              )}

              <div className="flex flex-col items-center">
                <div className="flex items-center gap-1 text-xs font-semibold">
                  <Video className="w-3 h-3" />
                  <span>{formatCount(isTikTokCreator(creator) ? creator.video_count : creator.media_count)}</span>
                </div>
                <span className="text-xs text-muted-foreground">
                  {isTikTokCreator(creator) ? 'Videos' : 'Media'}
                </span>
              </div>
            </div>
          </div>
        </div>
      </HoverCardContent>
    </HoverCard>
  );
}
