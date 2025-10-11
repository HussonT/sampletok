import React from 'react';
import { TikTokCreator } from '@/types/api';
import { HoverCard, HoverCardContent, HoverCardTrigger } from '@/components/ui/hover-card';
import { Badge } from '@/components/ui/badge';
import { Users, Heart, Video, CheckCircle } from 'lucide-react';

interface CreatorHoverCardProps {
  creator: TikTokCreator;
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

  return (
    <HoverCard>
      <HoverCardTrigger asChild>
        {children}
      </HoverCardTrigger>
      <HoverCardContent className="w-80" side="top">
        <div className="flex gap-4">
          {/* Avatar */}
          <div className="flex-shrink-0">
            {creator.avatar_medium ? (
              <img
                src={creator.avatar_medium}
                alt={creator.nickname || creator.username}
                className="w-16 h-16 rounded-full object-cover"
              />
            ) : (
              <div className="w-16 h-16 rounded-full bg-primary/20 flex items-center justify-center">
                <span className="text-xl font-bold text-primary">
                  {(creator.nickname || creator.username).charAt(0).toUpperCase()}
                </span>
              </div>
            )}
          </div>

          {/* Creator Info */}
          <div className="flex-1 space-y-2">
            {/* Name and username */}
            <div>
              <div className="flex items-center gap-2">
                <h4 className="font-semibold text-sm">
                  {creator.nickname || creator.username}
                </h4>
                {creator.verified && (
                  <CheckCircle className="w-4 h-4 text-blue-500 fill-blue-500" />
                )}
              </div>
              <p className="text-xs text-muted-foreground">@{creator.username}</p>
            </div>

            {/* Bio/Signature */}
            {creator.signature && (
              <p className="text-xs text-muted-foreground line-clamp-2">
                {creator.signature}
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

              <div className="flex flex-col items-center">
                <div className="flex items-center gap-1 text-xs font-semibold">
                  <Heart className="w-3 h-3" />
                  <span>{formatCount(creator.heart_count)}</span>
                </div>
                <span className="text-xs text-muted-foreground">Likes</span>
              </div>

              <div className="flex flex-col items-center">
                <div className="flex items-center gap-1 text-xs font-semibold">
                  <Video className="w-3 h-3" />
                  <span>{formatCount(creator.video_count)}</span>
                </div>
                <span className="text-xs text-muted-foreground">Videos</span>
              </div>
            </div>
          </div>
        </div>
      </HoverCardContent>
    </HoverCard>
  );
}
