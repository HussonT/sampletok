'use client';

import React, { useState, useRef, useEffect } from 'react';
import { Sample } from '@/types/api';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Slider } from '@/components/ui/slider';
import { Badge } from '@/components/ui/badge';
import { Avatar, AvatarImage, AvatarFallback } from '@/components/ui/avatar';
import {
  Play,
  Pause,
  Download,
  ExternalLink,
  Volume2,
  VolumeX,
  Music,
} from 'lucide-react';
import { HlsAudioPlayer } from './hls-audio-player';
import { ShareButtons } from '@/components/share-buttons';
import { useRouter } from 'next/navigation';

interface PublicSamplePlayerProps {
  sample: Sample;
}

export function PublicSamplePlayer({ sample }: PublicSamplePlayerProps) {
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [volume, setVolume] = useState(0.7);
  const [isMuted, setIsMuted] = useState(false);
  const audioRef = useRef<HTMLAudioElement>(null);
  const router = useRouter();

  useEffect(() => {
    if (audioRef.current) {
      audioRef.current.volume = isMuted ? 0 : volume;
    }
  }, [volume, isMuted]);

  const handlePlayPause = async () => {
    if (!audioRef.current) return;

    try {
      if (isPlaying) {
        audioRef.current.pause();
      } else {
        await audioRef.current.play();
      }
      setIsPlaying(!isPlaying);
    } catch (error) {
      console.error('Error playing audio:', error);
    }
  };

  const handleTimeUpdate = () => {
    if (audioRef.current) {
      setCurrentTime(audioRef.current.currentTime);
    }
  };

  const handleSeek = (value: number[]) => {
    const time = value[0];
    setCurrentTime(time);
    if (audioRef.current) {
      audioRef.current.currentTime = time;
    }
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const handleDownload = () => {
    // Redirect to sign-up to download
    router.push('/');
  };

  const handleOpenOriginal = () => {
    const url = sample.source === 'instagram' ? sample.instagram_url : sample.tiktok_url;
    if (url) {
      window.open(url, '_blank', 'noopener,noreferrer');
    }
  };

  const duration = sample.duration_seconds || 0;
  const creatorAvatar = sample.tiktok_creator?.avatar_thumb ||
                        sample.instagram_creator?.profile_pic_url;
  const creatorName = sample.creator_name || sample.creator_username || 'Unknown';
  const platform = sample.source === 'instagram' ? 'Instagram' : 'TikTok';

  return (
    <div className="container max-w-4xl mx-auto px-4 py-8 md:py-16">
      {/* Header */}
      <div className="text-center mb-8">
        <div className="inline-flex items-center gap-2 mb-4 text-muted-foreground">
          <Music className="h-5 w-5" />
          <span className="text-sm font-medium">Sample the Internet</span>
        </div>
        <h1 className="text-3xl md:text-4xl font-bold mb-2">{sample.title}</h1>
        <p className="text-muted-foreground">
          Transformed from {platform} by @{sample.creator_username}
        </p>
      </div>

      {/* Main Player Card */}
      <Card className="p-6 md:p-8 mb-6">
        {/* Waveform */}
        {sample.waveform_url && (
          <div className="mb-6 rounded-lg overflow-hidden bg-muted/30">
            <img
              src={sample.waveform_url}
              alt="Audio waveform"
              className="w-full h-32 md:h-48 object-cover"
            />
          </div>
        )}

        {/* Audio Controls */}
        <div className="space-y-4">
          {/* Play Button and Progress */}
          <div className="flex items-center gap-4">
            <Button
              size="lg"
              className="h-14 w-14 rounded-full"
              onClick={handlePlayPause}
            >
              {isPlaying ? (
                <Pause className="h-6 w-6" />
              ) : (
                <Play className="h-6 w-6 ml-0.5" />
              )}
            </Button>

            <div className="flex-1 space-y-2">
              <Slider
                value={[currentTime]}
                max={duration}
                step={0.1}
                onValueChange={handleSeek}
                className="cursor-pointer"
              />
              <div className="flex justify-between text-xs text-muted-foreground">
                <span>{formatTime(currentTime)}</span>
                <span>{formatTime(duration)}</span>
              </div>
            </div>
          </div>

          {/* Volume Control */}
          <div className="flex items-center gap-3">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setIsMuted(!isMuted)}
            >
              {isMuted || volume === 0 ? (
                <VolumeX className="h-4 w-4" />
              ) : (
                <Volume2 className="h-4 w-4" />
              )}
            </Button>
            <Slider
              value={[isMuted ? 0 : volume]}
              max={1}
              step={0.01}
              onValueChange={(v) => {
                setVolume(v[0]);
                setIsMuted(false);
              }}
              className="w-24 cursor-pointer"
            />
          </div>
        </div>

        {/* Hidden Audio Element */}
        <HlsAudioPlayer
          hlsUrl={sample.audio_url_hls}
          mp3Url={sample.audio_url_mp3}
          audioRef={audioRef}
          onTimeUpdate={handleTimeUpdate}
          onEnded={() => setIsPlaying(false)}
          preload="metadata"
        />
      </Card>

      {/* Sample Metadata */}
      <Card className="p-6 mb-6">
        <div className="flex items-start gap-4 mb-6">
          <Avatar className="h-16 w-16">
            <AvatarImage src={creatorAvatar} alt={creatorName} />
            <AvatarFallback>{creatorName[0]?.toUpperCase()}</AvatarFallback>
          </Avatar>
          <div className="flex-1">
            <h3 className="font-semibold text-lg">{creatorName}</h3>
            <p className="text-sm text-muted-foreground">@{sample.creator_username}</p>
            {sample.description && (
              <p className="text-sm mt-2">{sample.description}</p>
            )}
          </div>
        </div>

        {/* Metadata Badges */}
        <div className="flex flex-wrap gap-2 mb-6">
          {sample.bpm && (
            <Badge variant="secondary">
              <Music className="h-3 w-3 mr-1" />
              {sample.bpm} BPM
            </Badge>
          )}
          {sample.key && (
            <Badge variant="secondary">Key: {sample.key}</Badge>
          )}
          {sample.duration_seconds && (
            <Badge variant="secondary">
              {Math.floor(sample.duration_seconds)}s
            </Badge>
          )}
          {sample.tags && sample.tags.map((tag) => (
            <Badge key={tag} variant="outline">
              {tag}
            </Badge>
          ))}
        </div>

        {/* Action Buttons */}
        <div className="flex flex-col sm:flex-row gap-3">
          <Button onClick={handleDownload} className="flex-1">
            <Download className="h-4 w-4 mr-2" />
            Sign up to Download
          </Button>
          <Button
            variant="outline"
            onClick={handleOpenOriginal}
            className="flex-1"
          >
            <ExternalLink className="h-4 w-4 mr-2" />
            View Original
          </Button>
        </div>
      </Card>

      {/* Share Section */}
      <Card className="p-6">
        <h3 className="font-semibold mb-4">Share this sample</h3>
        <ShareButtons sampleId={sample.id} sampleTitle={sample.title || ''} />
      </Card>

      {/* Footer CTA */}
      <div className="text-center mt-12 space-y-4">
        <h2 className="text-2xl font-bold">Transform your content into samples</h2>
        <p className="text-muted-foreground">
          Tag @sampletheinternet on Instagram or TikTok to turn your videos into music samples
        </p>
        <Button size="lg" onClick={() => router.push('/')}>
          Get Started Free
        </Button>
      </div>
    </div>
  );
}
