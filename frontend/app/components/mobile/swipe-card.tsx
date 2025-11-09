'use client';

import { motion, useMotionValue, useTransform, PanInfo } from 'framer-motion';
import { Sample } from '@/types/api';
import { Badge } from '@/components/ui/badge';
import { Play, Pause } from 'lucide-react';
import { useState, useRef, useEffect } from 'react';
import { Avatar, AvatarImage, AvatarFallback } from '@/components/ui/avatar';
import { HlsAudioPlayer } from '@/components/features/hls-audio-player';

interface SwipeCardProps {
  sample: Sample;
  onSwipeLeft: () => void;
  onSwipeRight: () => void;
  style?: any;
  isActive?: boolean;
}

export function SwipeCard({
  sample,
  onSwipeLeft,
  onSwipeRight,
  style,
  isActive = true
}: SwipeCardProps) {
  const x = useMotionValue(0);
  const y = useMotionValue(0);
  const rotate = useTransform(x, [-200, 200], [-25, 25]);
  const opacity = useTransform(x, [-200, -100, 0, 100, 200], [0, 1, 1, 1, 0]);

  // Overlay opacities
  const dismissOverlay = useTransform(x, [-200, 0], [1, 0]);
  const likeOverlay = useTransform(x, [0, 200], [0, 1]);

  const [isPlaying, setIsPlaying] = useState(false);
  const audioRef = useRef<HTMLAudioElement>(null);

  // Auto-pause when card becomes inactive
  useEffect(() => {
    if (!isActive && audioRef.current) {
      audioRef.current.pause();
      setIsPlaying(false);
    }
  }, [isActive]);

  const togglePlayPause = () => {
    if (!audioRef.current) return;

    if (isPlaying) {
      audioRef.current.pause();
      setIsPlaying(false);
    } else {
      audioRef.current.play().catch(err => {
        console.error('Error playing audio:', err);
      });
      setIsPlaying(true);
    }
  };

  const handleDragEnd = (event: MouseEvent | TouchEvent | PointerEvent, info: PanInfo) => {
    const swipeThreshold = 100;
    const velocityThreshold = 500;

    // Check if swipe was strong enough
    if (Math.abs(info.offset.x) > swipeThreshold || Math.abs(info.velocity.x) > velocityThreshold) {
      if (info.offset.x > 0) {
        onSwipeRight();
      } else {
        onSwipeLeft();
      }
    }
  };

  const formatCount = (count: number) => {
    if (count >= 1000000) return `${(count / 1000000).toFixed(1)}M`;
    if (count >= 1000) return `${(count / 1000).toFixed(1)}K`;
    return count.toString();
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
    <motion.div
      drag={isActive}
      dragConstraints={{ left: 0, right: 0, top: 0, bottom: 0 }}
      dragElastic={1}
      onDragEnd={handleDragEnd}
      style={{
        x,
        y,
        rotate,
        opacity,
        ...style,
      }}
      className="absolute inset-0 touch-none select-none"
    >
      <div className="relative h-full bg-gray-900 rounded-2xl overflow-hidden shadow-2xl">
        {/* TikTok/Instagram Video/Thumbnail */}
        <div className="relative h-[70vh] bg-gradient-to-b from-gray-900 to-black">
          {sample.thumbnail_url && (
            <img
              src={sample.thumbnail_url}
              alt={creator.name}
              className="w-full h-full object-cover"
            />
          )}

          {/* Play/Pause Overlay Button */}
          <button
            onClick={(e) => {
              e.stopPropagation();
              togglePlayPause();
            }}
            className="absolute inset-0 flex items-center justify-center bg-black/20 hover:bg-black/30 transition-colors z-10"
          >
            <div className="bg-white/90 rounded-full p-4 hover:bg-white transition-colors">
              {isPlaying ? (
                <Pause className="w-12 h-12 text-black" />
              ) : (
                <Play className="w-12 h-12 text-black ml-1" />
              )}
            </div>
          </button>

          {/* Hidden Audio Player */}
          <HlsAudioPlayer
            hlsUrl={sample.audio_url_hls}
            mp3Url={sample.audio_url_mp3}
            audioRef={audioRef}
            preload="metadata"
            onEnded={() => setIsPlaying(false)}
          />

          {/* Swipe Overlays */}
          <motion.div
            className="absolute inset-0 bg-red-500/80 flex items-center justify-center pointer-events-none"
            style={{ opacity: dismissOverlay }}
          >
            <div className="text-8xl transform -rotate-12">👎</div>
          </motion.div>

          <motion.div
            className="absolute inset-0 bg-green-500/80 flex items-center justify-center pointer-events-none"
            style={{ opacity: likeOverlay }}
          >
            <div className="text-8xl transform rotate-12">❤️</div>
          </motion.div>

          {/* Top gradient overlay for text readability */}
          <div className="absolute top-0 left-0 right-0 h-32 bg-gradient-to-b from-black/60 to-transparent pointer-events-none" />
        </div>

        {/* Sample Info */}
        <div className="absolute bottom-0 left-0 right-0 p-6 bg-gradient-to-t from-black via-black/95 to-transparent">
          {/* Creator Info */}
          <div className="flex items-center gap-3 mb-3">
            <Avatar className="w-12 h-12 border-2 border-white/20">
              <AvatarImage src={creator.avatar} alt={creator.name} />
              <AvatarFallback className="bg-gray-700 text-white">
                {creator.name[0]?.toUpperCase() || '?'}
              </AvatarFallback>
            </Avatar>
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <h3 className="text-lg font-bold text-white">{creator.name}</h3>
                {creator.verified && (
                  <span className="text-blue-500">✓</span>
                )}
              </div>
              <p className="text-sm text-gray-400">{creator.username}</p>
            </div>
          </div>

          {/* Description */}
          {sample.description && (
            <p className="text-sm text-white/90 mb-3 line-clamp-2">
              {sample.description}
            </p>
          )}

          {/* Audio Metadata */}
          <div className="flex flex-wrap gap-2 mb-3">
            {sample.bpm && (
              <Badge variant="secondary" className="bg-purple-600/20 text-purple-300 border-purple-600/30">
                {Math.round(sample.bpm)} BPM
              </Badge>
            )}
            {sample.key && (
              <Badge variant="secondary" className="bg-blue-600/20 text-blue-300 border-blue-600/30">
                {sample.key}
              </Badge>
            )}
            {sample.duration_seconds && (
              <Badge variant="secondary" className="bg-green-600/20 text-green-300 border-green-600/30">
                {Math.floor(sample.duration_seconds)}s
              </Badge>
            )}
          </div>

          {/* Stats */}
          <div className="flex gap-4 text-sm text-gray-400">
            <span>❤️ {formatCount(sample.like_count)}</span>
            <span>👁️ {formatCount(sample.view_count)}</span>
            {sample.download_count && sample.download_count > 0 && (
              <span>⬇️ {formatCount(sample.download_count)}</span>
            )}
          </div>

          {/* Waveform Preview */}
          {sample.waveform_url && (
            <div className="mt-3">
              <img
                src={sample.waveform_url}
                alt="Waveform"
                className="w-full h-12 object-cover rounded-lg opacity-80"
              />
            </div>
          )}
        </div>
      </div>
    </motion.div>
  );
}
