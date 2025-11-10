'use client';

import { useRef, useEffect, useState } from 'react';
import Image from 'next/image';
import { Sample } from '@/types/api';
import { Badge } from '@/components/ui/badge';
import { Avatar, AvatarImage, AvatarFallback } from '@/components/ui/avatar';
import { Button } from '@/components/ui/button';
import { Heart, Volume2, VolumeX, Play, Pause, Users, Download, Music2, Waves, Activity, Clock, Video, CheckCircle, ImageIcon } from 'lucide-react';
import { getAvatarWithFallback } from '@/lib/avatar';
import { useAuth, useClerk } from '@clerk/nextjs';
import { toast } from 'sonner';

interface VideoFeedItemProps {
  sample: Sample;
  index: number;
  isActive: boolean;
  onFavoriteChange?: (sampleId: string, isFavorited: boolean) => void;
  onAuthRequired?: () => void;
  globalMuted: boolean;
  onMuteChange: (muted: boolean) => void;
}

export function VideoFeedItem({
  sample,
  index,
  isActive,
  onFavoriteChange,
  onAuthRequired,
  globalMuted,
  onMuteChange
}: VideoFeedItemProps) {
  const { isSignedIn, getToken } = useAuth();
  const { openSignUp } = useClerk();
  const videoRef = useRef<HTMLVideoElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isFavorited, setIsFavorited] = useState(sample.is_favorited || false);
  const [isTogglingFavorite, setIsTogglingFavorite] = useState(false);
  const [waveformError, setWaveformError] = useState(false);

  // Auto-play/pause based on whether this video is in view
  useEffect(() => {
    if (!videoRef.current) return;

    if (isActive) {
      // Auto-play when scrolled into view (muted by default for autoplay policy)
      videoRef.current.play().catch((err) => {
        console.error('Autoplay failed:', err);
        setIsPlaying(false);
      });
      setIsPlaying(true);
    } else {
      // Pause when scrolled out of view
      videoRef.current.pause();
      setIsPlaying(false);
    }
  }, [isActive]);

  const togglePlayPause = () => {
    if (!videoRef.current) return;

    if (isPlaying) {
      videoRef.current.pause();
      setIsPlaying(false);
    } else {
      videoRef.current.play().catch(err => {
        console.error('Error playing video:', err);
      });
      setIsPlaying(true);
    }
  };

  const toggleMute = () => {
    if (!videoRef.current) return;
    const newMutedState = !globalMuted;
    videoRef.current.muted = newMutedState;
    onMuteChange(newMutedState);
  };

  // Sync video element mute state with global state
  useEffect(() => {
    if (videoRef.current) {
      videoRef.current.muted = globalMuted;
    }
  }, [globalMuted]);

  const handleFavorite = async () => {
    // Trigger auth prompt if not authenticated
    if (!isSignedIn) {
      onAuthRequired?.();
      return;
    }

    try {
      setIsTogglingFavorite(true);
      const newFavoritedState = !isFavorited;

      // Optimistic update
      setIsFavorited(newFavoritedState);

      const token = await getToken();
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/samples/${sample.id}/favorite`,
        {
          method: newFavoritedState ? 'POST' : 'DELETE',
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        }
      );

      if (!response.ok) {
        // Revert on error
        setIsFavorited(!newFavoritedState);
        throw new Error('Failed to update favorite');
      }

      // Notify parent component
      onFavoriteChange?.(sample.id, newFavoritedState);

      // Show subtle feedback
      if (newFavoritedState) {
        toast.success('Added to favorites');
      }
    } catch (error) {
      console.error('Error toggling favorite:', error);
      toast.error('Failed to update favorite');
    } finally {
      setIsTogglingFavorite(false);
    }
  };

  const formatCount = (count: number) => {
    if (count >= 1000000) return `${(count / 1000000).toFixed(1)}M`;
    if (count >= 1000) return `${(count / 1000).toFixed(1)}K`;
    return count.toString();
  };

  const formatDuration = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const getCreatorInfo = () => {
    if (sample.source === 'instagram' && sample.instagram_creator) {
      return {
        name: sample.instagram_creator.full_name || sample.instagram_creator.username,
        username: `@${sample.instagram_creator.username}`,
        avatar: sample.instagram_creator.profile_pic_url,
        verified: sample.instagram_creator.is_verified,
      };
    }

    if (sample.tiktok_creator) {
      return {
        name: sample.tiktok_creator.nickname || sample.tiktok_creator.username,
        username: `@${sample.tiktok_creator.username}`,
        avatar: sample.tiktok_creator.avatar_thumb,
        verified: sample.tiktok_creator.verified,
      };
    }

    return {
      name: sample.creator_name || 'Unknown Creator',
      username: sample.creator_username ? `@${sample.creator_username}` : '',
      avatar: undefined,
      verified: false,
    };
  };

  const creator = getCreatorInfo();

  return (
    <div
      data-index={index}
      className="relative h-screen w-full snap-start snap-always flex items-center justify-center bg-[hsl(0,0%,17%)]"
    >
      {/* Video Player - More visible, less blurred */}
      {sample.video_url ? (
        <video
          ref={videoRef}
          src={sample.video_url}
          className="absolute inset-0 w-full h-full object-contain opacity-75 blur-[2px]"
          loop
          playsInline
          muted={globalMuted}
          onEnded={() => setIsPlaying(false)}
        />
      ) : sample.thumbnail_url ? (
        <Image
          src={sample.thumbnail_url}
          alt={creator.name}
          fill
          className="object-contain opacity-75 blur-[2px]"
          unoptimized
        />
      ) : (
        <div className="absolute inset-0 bg-gradient-to-b from-gray-900 to-black" />
      )}

      {/* Dark overlay for contrast - lighter for better video visibility */}
      <div className="absolute inset-0 bg-black/30 pointer-events-none z-10" />

      {/* MAIN AUDIO-FOCUSED LAYOUT */}
      <div className="relative z-20 w-full h-full flex flex-col p-4 pt-16 pb-28">

        {/* TOP: Large Audio Metadata Cards */}
        <div className="flex gap-3 mb-4">
          {/* BPM Card */}
          <div className="flex-1 bg-gradient-to-br from-[hsl(338,82%,65%)]/20 to-[hsl(338,82%,65%)]/5 backdrop-blur-md rounded-xl p-2.5 border border-[hsl(338,82%,65%)]/30">
            <div className="flex items-center gap-1 mb-1">
              <Activity className="w-3 h-3 text-[hsl(338,82%,65%)] stroke-[1.5]" />
              <span className="text-[9px] text-gray-400 uppercase tracking-wide">BPM</span>
            </div>
            <div className="text-2xl font-bold text-white leading-none">
              {sample.bpm ? Math.round(sample.bpm) : '--'}
            </div>
          </div>

          {/* Key Card */}
          <div className="flex-1 bg-gradient-to-br from-[hsl(338,82%,65%)]/20 to-[hsl(338,82%,65%)]/5 backdrop-blur-md rounded-xl p-2.5 border border-[hsl(338,82%,65%)]/30">
            <div className="flex items-center gap-1 mb-1">
              <Music2 className="w-3 h-3 text-[hsl(338,82%,65%)] stroke-[1.5]" />
              <span className="text-[9px] text-gray-400 uppercase tracking-wide">Key</span>
            </div>
            <div className="text-2xl font-bold text-white leading-none">
              {sample.key || '--'}
            </div>
          </div>

          {/* Duration Card */}
          <div className="flex-1 bg-gradient-to-br from-[hsl(338,82%,65%)]/20 to-[hsl(338,82%,65%)]/5 backdrop-blur-md rounded-xl p-2.5 border border-[hsl(338,82%,65%)]/30">
            <div className="flex items-center gap-1 mb-1">
              <Clock className="w-3 h-3 text-[hsl(338,82%,65%)] stroke-[1.5]" />
              <span className="text-[9px] text-gray-400 uppercase tracking-wide">Length</span>
            </div>
            <div className="text-2xl font-bold text-white leading-none">
              {sample.duration_seconds ? formatDuration(sample.duration_seconds) : '--'}
            </div>
          </div>
        </div>

        {/* Creator Card */}
        <div className="bg-white/5 backdrop-blur-md rounded-xl border border-white/10 p-2.5 mb-3">
          <div className="flex gap-2.5">
            <Avatar className="w-11 h-11 ring-2 ring-[hsl(338,82%,65%)]/30 flex-shrink-0">
              <AvatarImage
                src={creator.avatar || getAvatarWithFallback(null, creator.username)}
                alt={creator.name}
              />
              <AvatarFallback className="text-sm bg-gradient-to-br from-[hsl(338,82%,65%)] to-[hsl(338,82%,55%)]">
                {creator.name[0]?.toUpperCase() || '?'}
              </AvatarFallback>
            </Avatar>

            <div className="flex-1 min-w-0">
              {/* Name and username */}
              <div className="mb-1">
                <div className="flex items-center gap-1">
                  <span className="font-semibold text-white text-sm truncate">{creator.name}</span>
                  {creator.verified && (
                    <CheckCircle className="w-3 h-3 text-[hsl(338,82%,65%)] fill-[hsl(338,82%,65%)] flex-shrink-0" />
                  )}
                </div>
                <p className="text-[11px] text-gray-400 truncate">{creator.username}</p>
              </div>

              {/* Bio/Signature (TikTok) or Private indicator (Instagram) */}
              {sample.source === 'tiktok' && sample.tiktok_creator?.signature && (
                <p className="text-[11px] text-gray-400 line-clamp-1 mb-1.5">
                  {sample.tiktok_creator.signature}
                </p>
              )}
              {sample.source === 'instagram' && sample.instagram_creator?.is_private && (
                <p className="text-[11px] text-gray-400 italic mb-1.5">
                  🔒 Private account
                </p>
              )}

              {/* Stats Grid */}
              <div className="grid grid-cols-3 gap-1.5">
                {/* Followers */}
                <div className="flex flex-col items-center bg-white/5 rounded-lg py-1">
                  <div className="flex items-center gap-0.5 text-[11px] font-semibold text-white">
                    <Users className="w-2.5 h-2.5" />
                    <span>
                      {sample.source === 'tiktok' && sample.tiktok_creator
                        ? formatCount(sample.tiktok_creator.follower_count)
                        : sample.source === 'instagram' && sample.instagram_creator
                        ? formatCount(sample.instagram_creator.follower_count)
                        : '--'}
                    </span>
                  </div>
                  <span className="text-[9px] text-gray-400">Followers</span>
                </div>

                {/* Likes (TikTok) or Posts (Instagram) */}
                <div className="flex flex-col items-center bg-white/5 rounded-lg py-1">
                  <div className="flex items-center gap-0.5 text-[11px] font-semibold text-white">
                    {sample.source === 'tiktok' ? (
                      <>
                        <Heart className="w-2.5 h-2.5" />
                        <span>{sample.tiktok_creator ? formatCount(sample.tiktok_creator.heart_count) : '--'}</span>
                      </>
                    ) : (
                      <>
                        <ImageIcon className="w-2.5 h-2.5" />
                        <span>{sample.instagram_creator ? formatCount(sample.instagram_creator.media_count) : '--'}</span>
                      </>
                    )}
                  </div>
                  <span className="text-[9px] text-gray-400">
                    {sample.source === 'tiktok' ? 'Likes' : 'Posts'}
                  </span>
                </div>

                {/* Videos/Media */}
                <div className="flex flex-col items-center bg-white/5 rounded-lg py-1">
                  <div className="flex items-center gap-0.5 text-[11px] font-semibold text-white">
                    <Video className="w-2.5 h-2.5" />
                    <span>
                      {sample.source === 'tiktok' && sample.tiktok_creator
                        ? formatCount(sample.tiktok_creator.video_count)
                        : sample.source === 'instagram' && sample.instagram_creator
                        ? formatCount(sample.instagram_creator.media_count)
                        : '--'}
                    </span>
                  </div>
                  <span className="text-[9px] text-gray-400">
                    {sample.source === 'tiktok' ? 'Videos' : 'Media'}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Sample title/description */}
          {(sample.title || sample.description) && (
            <p className="text-[11px] text-white/80 mt-2 pt-2 border-t border-white/10 line-clamp-1">
              {sample.title || sample.description}
            </p>
          )}
        </div>

        {/* WAVEFORM */}
        <div className="mb-4">
          <div className="w-full h-24">
            {sample.waveform_url && !waveformError ? (
              <Image
                src={sample.waveform_url}
                alt="Audio Waveform"
                width={800}
                height={112}
                className="w-full h-full object-contain"
                unoptimized
                onError={() => setWaveformError(true)}
              />
            ) : (
              <svg className="w-full h-full" viewBox="0 0 100 60" preserveAspectRatio="none">
                <defs>
                  <linearGradient id={`gradient-mobile-${sample.id}`} x1="0%" y1="0%" x2="0%" y2="100%">
                    <stop offset="0%" stopColor="hsl(338, 82%, 65%)" stopOpacity="0.8" />
                    <stop offset="100%" stopColor="hsl(270, 70%, 60%)" stopOpacity="0.6" />
                  </linearGradient>
                </defs>
                {Array.from({ length: 80 }).map((_, i) => {
                  const seed = sample.id.charCodeAt(0) + sample.id.charCodeAt(sample.id.length - 1) + i;
                  const height = ((seed * 9.7) % 52) + 8;
                  const y = (60 - height) / 2;
                  return (
                    <rect
                      key={i}
                      x={(i * 100) / 80}
                      y={y}
                      width="0.8"
                      height={height}
                      fill={`url(#gradient-mobile-${sample.id})`}
                      className="transition-all"
                    />
                  );
                })}
              </svg>
            )}
          </div>
        </div>

        {/* Spacer */}
        <div className="flex-1" />
      </div>

      {/* RIGHT SIDE: Vertical Action Button Stack (TikTok-style) */}
      <div className="absolute right-3 bottom-32 z-30 flex flex-col gap-3">
        {/* Save Sample Button - Primary CTA */}
        <button
          onClick={handleFavorite}
          disabled={isTogglingFavorite}
          className={`rounded-xl w-14 h-14 font-semibold text-xs text-white backdrop-blur-md transition-all flex flex-col items-center justify-center gap-0.5 ${
            isFavorited
              ? 'bg-gradient-to-br from-[hsl(338,82%,65%)] to-[hsl(338,82%,55%)] shadow-lg shadow-[hsl(338,82%,65%)]/50'
              : 'bg-white/10 border border-white/20 hover:bg-white/20 active:scale-95'
          }`}
        >
          <Heart className={`w-6 h-6 ${isFavorited ? 'fill-white' : ''}`} />
          <span className="text-[9px] leading-tight">{isFavorited ? 'Saved' : 'Save'}</span>
        </button>

        {/* Download Button */}
        <button
          onClick={() => {
            if (!isSignedIn) {
              onAuthRequired?.();
              return;
            }
            // TODO: Implement actual download logic for authenticated users
            toast.info('Download feature coming soon!');
          }}
          className="rounded-xl w-14 h-14 bg-white/10 border border-white/20 backdrop-blur-md hover:bg-white/20 active:scale-95 transition-all flex items-center justify-center"
        >
          <Download className="w-6 h-6 text-white" />
        </button>

        {/* Play/Pause Control */}
        <button
          onClick={togglePlayPause}
          className="rounded-xl w-14 h-14 bg-white/10 border border-white/20 backdrop-blur-md hover:bg-white/20 active:scale-95 transition-all flex items-center justify-center"
        >
          {isPlaying ? (
            <Pause className="w-6 h-6 text-white" />
          ) : (
            <Play className="w-6 h-6 text-white" />
          )}
        </button>

        {/* Mute Control */}
        <button
          onClick={toggleMute}
          className="rounded-xl w-14 h-14 bg-white/10 border border-white/20 backdrop-blur-md hover:bg-white/20 active:scale-95 transition-all flex items-center justify-center"
        >
          {globalMuted ? (
            <VolumeX className="w-6 h-6 text-white" />
          ) : (
            <Volume2 className="w-6 h-6 text-white" />
          )}
        </button>
      </div>
    </div>
  );
}
