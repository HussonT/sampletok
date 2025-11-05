# Option 2: Dual Experience - Comprehensive Implementation Plan

## Executive Summary

This document provides a detailed, step-by-step implementation plan for **Option 2: Mobile Native Discovery with Video-First Swipe Interface**, as outlined in MOBILE_STRATEGY.md. This is a thorough, production-ready blueprint covering architecture, component design, data flow, PWA setup, and phased rollout.

**Key Insight**: We already have everything needed! Our Sample model stores `video_url`, `thumbnail_url`, and all metadata. We just need to build the mobile UI to display these videos in a TikTok-style swipe feed.

---

## Table of Contents

1. [Current State Analysis](#current-state-analysis)
2. [Technical Architecture](#technical-architecture)
3. [PWA Configuration](#pwa-configuration)
4. [Device Detection & Routing](#device-detection--routing)
5. [Mobile Component Architecture](#mobile-component-architecture)
6. [Data Flow & State Management](#data-flow--state-management)
7. [Backend Requirements](#backend-requirements)
8. [Implementation Phases](#implementation-phases)
9. [Testing Strategy](#testing-strategy)
10. [Performance Optimization](#performance-optimization)
11. [Deployment & Rollout](#deployment--rollout)

---

## 1. Current State Analysis

### What We Already Have ✅

**Database Schema** (`backend/app/models/sample.py`):
```python
class Sample:
    # Video assets - ALL stored in our R2/S3/GCS
    video_url = Column(String)           # ✅ No-watermark video from TikTok
    thumbnail_url = Column(String)       # ✅ Video poster/thumbnail
    cover_url = Column(String)           # ✅ Cover image

    # Audio assets
    audio_url_mp3 = Column(String)       # ✅ Extracted sample MP3
    audio_url_wav = Column(String)       # ✅ Extracted sample WAV
    audio_url_hls = Column(String)       # ✅ HLS streaming playlist
    waveform_url = Column(String)        # ✅ Waveform visualization

    # TikTok metadata
    tiktok_url = Column(String)          # ✅ Original TikTok URL
    creator_username = Column(String)    # ✅ @username
    creator_name = Column(String)        # ✅ Display name
    description = Column(Text)           # ✅ Video description
    view_count = Column(Integer)         # ✅ TikTok views
    like_count = Column(Integer)         # ✅ TikTok likes

    # Audio analysis
    bpm = Column(Integer)                # ✅ Detected BPM
    key = Column(String)                 # ✅ Musical key
    duration_seconds = Column(Float)     # ✅ Duration
    tags = Column(JSONB)                 # ✅ Hashtags
```

**Storage Architecture** (`backend/app/services/storage/s3.py`):
- All files uploaded to R2/S3/GCS with public URLs
- Aggressive caching headers: `Cache-Control: public, max-age=31536000, immutable`
- HTTP range request support for progressive video loading
- CDN-ready (Cloudflare R2 includes global CDN)

**Processing Pipeline** (Inngest):
- Downloads TikTok video (no watermark) via RapidAPI
- Uploads video to our storage
- Extracts audio and generates MP3/WAV/HLS
- Analyzes BPM, key, duration
- All URLs stored in database

**Frontend Stack**:
- Next.js 15 with App Router
- React 19
- Tailwind CSS
- Clerk authentication
- TanStack Query for data fetching
- Route groups: `(app)` for authenticated pages

### What We Need to Build 🔨

1. **Mobile UI Components**:
   - Vertical swipe card component
   - Video player with overlay
   - Bottom tab navigation
   - Gesture handlers (swipe, tap, long-press)
   - Details sheet (swipe-up)
   - Filter/settings sheet

2. **PWA Setup**:
   - Service worker for offline support
   - App manifest for "Add to Home Screen"
   - iOS splash screens
   - App icons

3. **Device Detection & Routing**:
   - Detect mobile vs desktop
   - Render different layouts based on device
   - Maintain shared state (favorites, downloads)

4. **Mobile-Optimized API**:
   - Feed endpoint with pagination
   - Engagement tracking (views, skips)
   - Algorithm for personalized feed

5. **Performance Optimizations**:
   - Video preloading strategy
   - Card virtualization (only render 3 cards at once)
   - Gesture throttling
   - Memory management

---

## 2. Technical Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Device                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐              ┌──────────────┐               │
│  │   Mobile     │              │   Desktop    │               │
│  │   Layout     │              │   Layout     │               │
│  │              │              │              │               │
│  │ • Swipe Feed │              │ • Data Table │               │
│  │ • Bottom Nav │              │ • Sidebar    │               │
│  │ • Video Card │              │ • Bottom Bar │               │
│  └──────────────┘              └──────────────┘               │
│         │                              │                       │
│         └──────────────┬───────────────┘                       │
│                        │                                       │
│               ┌────────▼────────┐                              │
│               │  Shared State   │                              │
│               │                 │                              │
│               │ • AudioContext  │                              │
│               │ • QueryClient   │                              │
│               │ • Auth State    │                              │
│               └────────┬────────┘                              │
│                        │                                       │
└────────────────────────┼───────────────────────────────────────┘
                         │
                         │ HTTPS
                         │
                ┌────────▼────────┐
                │  Next.js API    │
                │   (Vercel)      │
                └────────┬────────┘
                         │
                         │
        ┌────────────────┼────────────────┐
        │                │                │
┌───────▼───────┐ ┌─────▼──────┐ ┌──────▼──────┐
│   FastAPI     │ │ PostgreSQL │ │   R2/CDN    │
│   Backend     │ │            │ │             │
│               │ │ • Samples  │ │ • Videos    │
│ • /feed       │ │ • Users    │ │ • Audio     │
│ • /samples    │ │ • Favorites│ │ • Images    │
│ • /track      │ │            │ │             │
└───────────────┘ └────────────┘ └─────────────┘
```

### Data Flow

**Mobile Discovery Flow**:
```
1. User opens app on mobile
   → DeviceDetector checks screen width
   → Renders MobileLayout (instead of DesktopLayout)

2. MobileLayout loads
   → Mounts SwipeFeed component
   → Fetches /api/v1/feed (20 samples)
   → Displays first card (video + overlay)

3. Video plays automatically
   → Loads video from R2 via CDN
   → Plays sample audio (MP3/HLS) over video
   → User sees: video + audio + metadata overlay

4. User swipes right (favorite)
   → POST /api/v1/favorites
   → Optimistic update (instant UI feedback)
   → Card animates off screen
   → Next card loads and plays

5. User swipes left (skip)
   → POST /api/v1/track (engagement data)
   → Next card loads

6. Infinite scroll
   → When 5 cards remaining, fetch next 20
   → Prefetch videos for next 2 cards
```

**Sync Between Mobile & Desktop**:
```
Mobile:
  User favorites sample
    → POST /favorites
    → Synced to database

Desktop:
  User opens /my-favorites
    → GET /favorites
    → Shows all favorites (including from mobile)
```

### Responsive Strategy: CSS Media Queries + Component Composition

**Approach**: Use CSS media queries to detect device type, then conditionally render mobile or desktop components.

```typescript
// lib/hooks/use-device-type.ts
export function useDeviceType() {
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const mediaQuery = window.matchMedia('(max-width: 768px)');
    setIsMobile(mediaQuery.matches);

    const handler = (e: MediaQueryListEvent) => setIsMobile(e.matches);
    mediaQuery.addEventListener('change', handler);
    return () => mediaQuery.removeEventListener('change', handler);
  }, []);

  return { isMobile, isDesktop: !isMobile };
}
```

**Why this approach?**
- ✅ No separate mobile domain needed (sampletok.com works for both)
- ✅ No user agent sniffing (unreliable)
- ✅ Respects user's device orientation (portrait tablet = mobile, landscape = desktop)
- ✅ Same codebase, shared data fetching
- ✅ SEO-friendly (single URL for both experiences)

---

## 3. PWA Configuration

### Progressive Web App Setup

**Goal**: Make the mobile web app installable like a native app.

#### 3.1 App Manifest

Create `frontend/public/manifest.json`:

```json
{
  "name": "Sampletok - TikTok Sample Discovery",
  "short_name": "Sampletok",
  "description": "Discover and download trending TikTok audio samples",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#000000",
  "theme_color": "#000000",
  "orientation": "portrait",
  "icons": [
    {
      "src": "/icons/icon-72x72.png",
      "sizes": "72x72",
      "type": "image/png",
      "purpose": "maskable any"
    },
    {
      "src": "/icons/icon-96x96.png",
      "sizes": "96x96",
      "type": "image/png",
      "purpose": "maskable any"
    },
    {
      "src": "/icons/icon-128x128.png",
      "sizes": "128x128",
      "type": "image/png",
      "purpose": "maskable any"
    },
    {
      "src": "/icons/icon-144x144.png",
      "sizes": "144x144",
      "type": "image/png",
      "purpose": "maskable any"
    },
    {
      "src": "/icons/icon-152x152.png",
      "sizes": "152x152",
      "type": "image/png",
      "purpose": "maskable any"
    },
    {
      "src": "/icons/icon-192x192.png",
      "sizes": "192x192",
      "type": "image/png",
      "purpose": "maskable any"
    },
    {
      "src": "/icons/icon-384x384.png",
      "sizes": "384x384",
      "type": "image/png",
      "purpose": "maskable any"
    },
    {
      "src": "/icons/icon-512x512.png",
      "sizes": "512x512",
      "type": "image/png",
      "purpose": "maskable any"
    }
  ],
  "shortcuts": [
    {
      "name": "Explore Samples",
      "short_name": "Explore",
      "description": "Browse trending TikTok samples",
      "url": "/",
      "icons": [{ "src": "/icons/explore.png", "sizes": "96x96" }]
    },
    {
      "name": "My Favorites",
      "short_name": "Favorites",
      "description": "View your saved favorites",
      "url": "/my-favorites",
      "icons": [{ "src": "/icons/favorites.png", "sizes": "96x96" }]
    }
  ],
  "screenshots": [
    {
      "src": "/screenshots/mobile-swipe.png",
      "sizes": "1170x2532",
      "type": "image/png",
      "form_factor": "narrow"
    },
    {
      "src": "/screenshots/desktop-table.png",
      "sizes": "1920x1080",
      "type": "image/png",
      "form_factor": "wide"
    }
  ]
}
```

Link in `app/layout.tsx`:
```typescript
<link rel="manifest" href="/manifest.json" />
```

#### 3.2 iOS Meta Tags

Add to `app/layout.tsx`:

```typescript
<meta name="apple-mobile-web-app-capable" content="yes" />
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent" />
<meta name="apple-mobile-web-app-title" content="Sampletok" />

{/* iOS Splash Screens (for all device sizes) */}
<link rel="apple-touch-startup-image" href="/splash/iphone5.png" media="(device-width: 320px) and (device-height: 568px)" />
<link rel="apple-touch-startup-image" href="/splash/iphone6.png" media="(device-width: 375px) and (device-height: 667px)" />
<link rel="apple-touch-startup-image" href="/splash/iphonex.png" media="(device-width: 375px) and (device-height: 812px)" />
<link rel="apple-touch-startup-image" href="/splash/iphonexr.png" media="(device-width: 414px) and (device-height: 896px)" />
<link rel="apple-touch-startup-image" href="/splash/iphonemax.png" media="(device-width: 414px) and (device-height: 896px)" />

{/* App Icons */}
<link rel="apple-touch-icon" sizes="180x180" href="/icons/apple-touch-icon.png" />
<link rel="icon" type="image/png" sizes="32x32" href="/icons/favicon-32x32.png" />
<link rel="icon" type="image/png" sizes="16x16" href="/icons/favicon-16x16.png" />
```

#### 3.3 Service Worker (Next.js 15)

Create `public/sw.js`:

```javascript
const CACHE_NAME = 'sampletok-v1';
const RUNTIME_CACHE = 'sampletok-runtime-v1';

// Assets to cache on install
const PRECACHE_ASSETS = [
  '/',
  '/my-favorites',
  '/offline',
];

// Install event - precache assets
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(PRECACHE_ASSETS))
  );
  self.skipWaiting();
});

// Activate event - clean old caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames
          .filter(name => name !== CACHE_NAME && name !== RUNTIME_CACHE)
          .map(name => caches.delete(name))
      );
    })
  );
  self.clients.claim();
});

// Fetch event - network first, fallback to cache
self.addEventListener('fetch', (event) => {
  // Skip non-GET requests
  if (event.request.method !== 'GET') return;

  // API requests: network first
  if (event.request.url.includes('/api/')) {
    event.respondWith(
      fetch(event.request)
        .then(response => {
          // Clone and cache successful API responses
          const responseClone = response.clone();
          caches.open(RUNTIME_CACHE).then(cache => {
            cache.put(event.request, responseClone);
          });
          return response;
        })
        .catch(() => {
          // Fallback to cache if offline
          return caches.match(event.request);
        })
    );
    return;
  }

  // Static assets: cache first
  event.respondWith(
    caches.match(event.request)
      .then(cachedResponse => {
        if (cachedResponse) {
          return cachedResponse;
        }
        return fetch(event.request).then(response => {
          // Cache successful responses
          if (response.status === 200) {
            const responseClone = response.clone();
            caches.open(RUNTIME_CACHE).then(cache => {
              cache.put(event.request, responseClone);
            });
          }
          return response;
        });
      })
      .catch(() => {
        // Offline fallback page
        if (event.request.mode === 'navigate') {
          return caches.match('/offline');
        }
      })
  );
});
```

Register in `app/layout.tsx`:

```typescript
useEffect(() => {
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/sw.js')
      .then(reg => console.log('Service Worker registered', reg))
      .catch(err => console.error('Service Worker registration failed', err));
  }
}, []);
```

#### 3.4 Install Prompt

Create `components/pwa-install-prompt.tsx`:

```typescript
'use client';

import { useEffect, useState } from 'react';
import { Download, X } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>;
}

export function PWAInstallPrompt() {
  const [deferredPrompt, setDeferredPrompt] = useState<BeforeInstallPromptEvent | null>(null);
  const [showPrompt, setShowPrompt] = useState(false);

  useEffect(() => {
    const handler = (e: Event) => {
      e.preventDefault();
      setDeferredPrompt(e as BeforeInstallPromptEvent);

      // Show prompt after user has interacted with the app (delay 10 seconds)
      setTimeout(() => {
        setShowPrompt(true);
      }, 10000);
    };

    window.addEventListener('beforeinstallprompt', handler);
    return () => window.removeEventListener('beforeinstallprompt', handler);
  }, []);

  const handleInstall = async () => {
    if (!deferredPrompt) return;

    deferredPrompt.prompt();
    const { outcome } = await deferredPrompt.userChoice;

    if (outcome === 'accepted') {
      console.log('PWA installed');
    }

    setDeferredPrompt(null);
    setShowPrompt(false);
  };

  if (!showPrompt || !deferredPrompt) return null;

  return (
    <div className="fixed bottom-20 left-4 right-4 bg-card border rounded-lg p-4 shadow-lg z-50 animate-slide-up">
      <button
        onClick={() => setShowPrompt(false)}
        className="absolute top-2 right-2 text-muted-foreground hover:text-foreground"
      >
        <X className="w-4 h-4" />
      </button>

      <div className="flex items-start gap-3 pr-6">
        <div className="bg-primary/10 p-2 rounded-lg">
          <Download className="w-5 h-5 text-primary" />
        </div>
        <div className="flex-1">
          <h3 className="font-semibold mb-1">Install Sampletok</h3>
          <p className="text-sm text-muted-foreground mb-3">
            Add to your home screen for quick access and offline favorites
          </p>
          <Button onClick={handleInstall} size="sm" className="w-full">
            Install App
          </Button>
        </div>
      </div>
    </div>
  );
}
```

---

## 4. Device Detection & Routing

### 4.1 Device Detection Hook

Create `lib/hooks/use-device-type.ts`:

```typescript
'use client';

import { useState, useEffect } from 'react';

export function useDeviceType() {
  // Default to desktop for SSR (prevents hydration mismatch)
  const [isMobile, setIsMobile] = useState(false);
  const [isLoaded, setIsLoaded] = useState(false);

  useEffect(() => {
    const mediaQuery = window.matchMedia('(max-width: 768px)');

    // Set initial value
    setIsMobile(mediaQuery.matches);
    setIsLoaded(true);

    // Listen for changes (orientation, window resize)
    const handler = (e: MediaQueryListEvent) => {
      setIsMobile(e.matches);
    };

    mediaQuery.addEventListener('change', handler);
    return () => mediaQuery.removeEventListener('change', handler);
  }, []);

  return {
    isMobile,
    isDesktop: !isMobile,
    isLoaded, // Use this to prevent flash of wrong layout
  };
}
```

### 4.2 Responsive Layout Wrapper

Create `components/layouts/responsive-layout.tsx`:

```typescript
'use client';

import { useDeviceType } from '@/lib/hooks/use-device-type';
import { MobileLayout } from './mobile-layout';
import { DesktopLayout } from './desktop-layout';
import { ReactNode } from 'react';

interface ResponsiveLayoutProps {
  children: ReactNode;
}

export function ResponsiveLayout({ children }: ResponsiveLayoutProps) {
  const { isMobile, isLoaded } = useDeviceType();

  // Show loading skeleton to prevent flash
  if (!isLoaded) {
    return (
      <div className="h-screen w-screen bg-background" />
    );
  }

  return isMobile ? (
    <MobileLayout>{children}</MobileLayout>
  ) : (
    <DesktopLayout>{children}</DesktopLayout>
  );
}
```

### 4.3 Update Root Layout

Modify `app/(app)/layout.tsx`:

```typescript
import { ResponsiveLayout } from '@/components/layouts/responsive-layout';

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <ResponsiveLayout>
      {children}
    </ResponsiveLayout>
  );
}
```

---

## 5. Mobile Component Architecture

### 5.1 Component Tree

```
MobileLayout
├── TopBar (logo, user avatar)
├── SwipeFeed (main content)
│   ├── SwipeCard (single sample)
│   │   ├── VideoPlayer
│   │   │   └── HTML5 <video>
│   │   ├── AudioOverlay
│   │   │   └── HLSAudioPlayer (from existing component)
│   │   ├── MetadataOverlay
│   │   │   ├── SampleTitle
│   │   │   ├── CreatorInfo
│   │   │   └── AudioStats (BPM, key, duration)
│   │   ├── ActionButtons
│   │   │   ├── FavoriteButton (heart)
│   │   │   ├── AudioModeToggle (sample/original/both)
│   │   │   └── MoreButton (open details sheet)
│   │   └── GestureHandler
│   │       ├── onSwipeLeft (skip)
│   │       ├── onSwipeRight (favorite)
│   │       ├── onSwipeUp (details)
│   │       ├── onTap (pause/play video)
│   │       └── onDoubleTap (favorite)
│   ├── LoadingSpinner (between cards)
│   └── EndOfFeedMessage
├── DetailsSheet (swipe-up panel)
│   ├── CreatorDetails
│   ├── TagsList
│   ├── DownloadButton
│   └── ShareButton
└── BottomTabNav
    ├── HomeTab (🏠)
    ├── FavoritesTab (♡)
    ├── CollectionsTab (⚡)
    └── ProfileTab (👤)
```

### 5.2 Core Components

#### SwipeCard Component

`components/mobile/swipe-card.tsx`:

```typescript
'use client';

import { useState, useRef, useEffect } from 'react';
import { motion, useMotionValue, useTransform, PanInfo } from 'framer-motion';
import { Sample } from '@/types/api';
import { VideoPlayer } from './video-player';
import { AudioOverlay } from './audio-overlay';
import { MetadataOverlay } from './metadata-overlay';
import { ActionButtons } from './action-buttons';
import { Heart } from 'lucide-react';

interface SwipeCardProps {
  sample: Sample;
  isActive: boolean; // Is this card currently visible?
  onSwipeLeft: () => void;
  onSwipeRight: () => void;
  onSwipeUp: () => void;
  onTap: () => void;
  style?: React.CSSProperties;
}

export function SwipeCard({
  sample,
  isActive,
  onSwipeLeft,
  onSwipeRight,
  onSwipeUp,
  onTap,
  style
}: SwipeCardProps) {
  const [audioMode, setAudioMode] = useState<'sample' | 'original' | 'both'>('sample');
  const [showHeartAnimation, setShowHeartAnimation] = useState(false);
  const [heartPosition, setHeartPosition] = useState({ x: 0, y: 0 });

  const cardRef = useRef<HTMLDivElement>(null);
  const x = useMotionValue(0);
  const y = useMotionValue(0);

  // Transform x position to rotation
  const rotate = useTransform(x, [-200, 200], [-25, 25]);

  // Transform x position to opacity (fade out when swiping)
  const opacity = useTransform(
    x,
    [-200, -150, 0, 150, 200],
    [0, 0.5, 1, 0.5, 0]
  );

  const handleDragEnd = (event: MouseEvent | TouchEvent | PointerEvent, info: PanInfo) => {
    const swipeThreshold = 100;

    // Horizontal swipes
    if (Math.abs(info.offset.x) > swipeThreshold) {
      if (info.offset.x > 0) {
        // Swipe right = favorite
        onSwipeRight();
      } else {
        // Swipe left = skip
        onSwipeLeft();
      }
    }

    // Vertical swipe up
    else if (info.offset.y < -swipeThreshold) {
      onSwipeUp();
    }
  };

  const handleDoubleTap = (e: React.MouseEvent) => {
    // Show heart animation at tap location
    const rect = cardRef.current?.getBoundingClientRect();
    if (rect) {
      setHeartPosition({
        x: e.clientX - rect.left,
        y: e.clientY - rect.top,
      });
      setShowHeartAnimation(true);

      // Trigger favorite action
      onSwipeRight();

      // Hide heart after animation
      setTimeout(() => setShowHeartAnimation(false), 1000);
    }
  };

  return (
    <motion.div
      ref={cardRef}
      className="absolute inset-0 touch-none"
      style={{
        x,
        y,
        rotate,
        opacity,
        ...style
      }}
      drag={isActive}
      dragConstraints={{ left: 0, right: 0, top: 0, bottom: 0 }}
      onDragEnd={handleDragEnd}
      onClick={onTap}
      onDoubleClick={handleDoubleTap}
    >
      <div className="relative h-full w-full bg-black rounded-lg overflow-hidden">
        {/* Video Player */}
        <VideoPlayer
          videoUrl={sample.video_url}
          posterUrl={sample.thumbnail_url}
          isPlaying={isActive}
        />

        {/* Audio Overlay (plays sample audio) */}
        <AudioOverlay
          sample={sample}
          audioMode={audioMode}
          isPlaying={isActive}
        />

        {/* Metadata Overlay (bottom gradient) */}
        <MetadataOverlay sample={sample} />

        {/* Action Buttons */}
        <ActionButtons
          sample={sample}
          audioMode={audioMode}
          onAudioModeChange={setAudioMode}
        />

        {/* Double-tap heart animation */}
        {showHeartAnimation && (
          <motion.div
            className="absolute pointer-events-none"
            style={{
              left: heartPosition.x,
              top: heartPosition.y,
            }}
            initial={{ scale: 0, opacity: 1 }}
            animate={{ scale: 2, opacity: 0 }}
            transition={{ duration: 0.8 }}
          >
            <Heart className="w-16 h-16 text-red-500 fill-red-500" />
          </motion.div>
        )}

        {/* Swipe indicators */}
        <motion.div
          className="absolute top-20 left-8 text-6xl font-bold text-green-500 rotate-[-20deg]"
          style={{
            opacity: useTransform(x, [0, 150], [0, 1]),
          }}
        >
          LIKE
        </motion.div>

        <motion.div
          className="absolute top-20 right-8 text-6xl font-bold text-red-500 rotate-[20deg]"
          style={{
            opacity: useTransform(x, [-150, 0], [1, 0]),
          }}
        >
          SKIP
        </motion.div>
      </div>
    </motion.div>
  );
}
```

#### VideoPlayer Component

`components/mobile/video-player.tsx`:

```typescript
'use client';

import { useRef, useEffect, useState } from 'react';

interface VideoPlayerProps {
  videoUrl: string;
  posterUrl: string;
  isPlaying: boolean;
}

export function VideoPlayer({ videoUrl, posterUrl, isPlaying }: VideoPlayerProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [isLoaded, setIsLoaded] = useState(false);

  useEffect(() => {
    if (!videoRef.current) return;

    if (isPlaying && isLoaded) {
      videoRef.current.play();
    } else {
      videoRef.current.pause();
    }
  }, [isPlaying, isLoaded]);

  return (
    <div className="absolute inset-0">
      <video
        ref={videoRef}
        src={videoUrl}
        poster={posterUrl}
        className="w-full h-full object-cover"
        loop
        muted // Video is muted, we play sample audio separately
        playsInline
        preload="metadata"
        onLoadedData={() => setIsLoaded(true)}
      />

      {/* Loading overlay */}
      {!isLoaded && (
        <div className="absolute inset-0 bg-black/50 flex items-center justify-center">
          <div className="w-12 h-12 border-4 border-white/20 border-t-white rounded-full animate-spin" />
        </div>
      )}
    </div>
  );
}
```

#### SwipeFeed Component (Main Container)

`components/mobile/swipe-feed.tsx`:

```typescript
'use client';

import { useState, useEffect, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Sample } from '@/types/api';
import { SwipeCard } from './swipe-card';
import { createAuthenticatedClient } from '@/lib/api-client';
import { useAuth } from '@clerk/nextjs';
import { AnimatePresence } from 'framer-motion';

export function SwipeFeed() {
  const { getToken } = useAuth();
  const [currentIndex, setCurrentIndex] = useState(0);
  const [samples, setSamples] = useState<Sample[]>([]);
  const [viewedSampleIds, setViewedSampleIds] = useState<Set<string>>(new Set());

  // Fetch feed
  const { data, fetchNextPage, hasNextPage, isFetchingNextPage } = useQuery({
    queryKey: ['mobile-feed'],
    queryFn: async ({ pageParam = 0 }) => {
      const apiClient = createAuthenticatedClient(getToken);
      const response = await apiClient.get<{ items: Sample[]; total: number }>('/feed', {
        skip: pageParam,
        limit: 20,
        exclude_ids: Array.from(viewedSampleIds), // Don't show already-seen samples
      });
      return response;
    },
    initialPageParam: 0,
    getNextPageParam: (lastPage, allPages) => {
      const loadedCount = allPages.reduce((sum, page) => sum + page.items.length, 0);
      return lastPage.items.length > 0 ? loadedCount : undefined;
    },
  });

  // Update samples list when data changes
  useEffect(() => {
    if (data?.pages) {
      const allSamples = data.pages.flatMap(page => page.items);
      setSamples(allSamples);
    }
  }, [data]);

  // Prefetch next page when nearing end
  useEffect(() => {
    if (currentIndex > samples.length - 5 && hasNextPage && !isFetchingNextPage) {
      fetchNextPage();
    }
  }, [currentIndex, samples.length, hasNextPage, isFetchingNextPage, fetchNextPage]);

  const handleSwipeRight = useCallback(async (sample: Sample) => {
    // Favorite the sample
    const apiClient = createAuthenticatedClient(getToken);
    await apiClient.post(`/samples/${sample.id}/favorite`);

    // Track engagement
    await apiClient.post(`/samples/${sample.id}/track`, {
      action: 'favorited',
      listen_duration: 0, // TODO: track actual listen time
    });

    // Mark as viewed
    setViewedSampleIds(prev => new Set([...prev, sample.id]));

    // Move to next card
    setCurrentIndex(prev => prev + 1);
  }, [getToken]);

  const handleSwipeLeft = useCallback(async (sample: Sample) => {
    // Track skip
    const apiClient = createAuthenticatedClient(getToken);
    await apiClient.post(`/samples/${sample.id}/track`, {
      action: 'skipped',
      listen_duration: 0,
    });

    // Mark as viewed
    setViewedSampleIds(prev => new Set([...prev, sample.id]));

    // Move to next card
    setCurrentIndex(prev => prev + 1);
  }, [getToken]);

  const handleSwipeUp = useCallback((sample: Sample) => {
    // Open details sheet
    // TODO: implement details sheet
  }, []);

  const handleTap = useCallback(() => {
    // Toggle video play/pause
    // TODO: implement video pause
  }, []);

  // Render cards (only render 3 at a time for performance)
  const visibleCards = samples.slice(currentIndex, currentIndex + 3);

  return (
    <div className="relative h-full w-full">
      <AnimatePresence>
        {visibleCards.map((sample, index) => (
          <SwipeCard
            key={sample.id}
            sample={sample}
            isActive={index === 0}
            onSwipeLeft={() => handleSwipeLeft(sample)}
            onSwipeRight={() => handleSwipeRight(sample)}
            onSwipeUp={() => handleSwipeUp(sample)}
            onTap={handleTap}
            style={{
              zIndex: visibleCards.length - index,
              scale: 1 - index * 0.05, // Stack effect
            }}
          />
        ))}
      </AnimatePresence>

      {/* End of feed message */}
      {currentIndex >= samples.length && !hasNextPage && (
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="text-center">
            <p className="text-lg font-semibold mb-2">You've seen all samples!</p>
            <p className="text-muted-foreground">Check back later for more</p>
          </div>
        </div>
      )}
    </div>
  );
}
```

### 5.3 Bottom Tab Navigation

`components/mobile/bottom-tab-nav.tsx`:

```typescript
'use client';

import { Home, Heart, Zap, User } from 'lucide-react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

export function BottomTabNav() {
  const pathname = usePathname();

  const tabs = [
    { icon: Home, label: 'Home', href: '/' },
    { icon: Heart, label: 'Favorites', href: '/my-favorites' },
    { icon: Zap, label: 'Collections', href: '/my-collections' },
    { icon: User, label: 'Profile', href: '/settings' },
  ];

  return (
    <nav className="fixed bottom-0 left-0 right-0 bg-card border-t safe-area-inset-bottom">
      <div className="flex items-center justify-around h-16">
        {tabs.map(({ icon: Icon, label, href }) => {
          const isActive = pathname === href;
          return (
            <Link
              key={href}
              href={href}
              className={`flex flex-col items-center justify-center gap-1 flex-1 h-full transition-colors ${
                isActive ? 'text-foreground' : 'text-muted-foreground'
              }`}
            >
              <Icon className="w-6 h-6" />
              <span className="text-xs">{label}</span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
```

### 5.4 Mobile Layout

`components/layouts/mobile-layout.tsx`:

```typescript
'use client';

import { ReactNode } from 'react';
import { BottomTabNav } from '../mobile/bottom-tab-nav';
import { PWAInstallPrompt } from '../pwa-install-prompt';

interface MobileLayoutProps {
  children: ReactNode;
}

export function MobileLayout({ children }: MobileLayoutProps) {
  return (
    <div className="h-screen w-screen overflow-hidden flex flex-col">
      {/* Main content - full screen */}
      <main className="flex-1 overflow-hidden">
        {children}
      </main>

      {/* Bottom tab navigation */}
      <BottomTabNav />

      {/* PWA install prompt */}
      <PWAInstallPrompt />
    </div>
  );
}
```

---

## 6. Data Flow & State Management

### 6.1 Shared State Architecture

**Problem**: Mobile and desktop need to share state (current audio, favorites, downloads).

**Solution**: Shared context providers that work on both layouts.

```
RootLayout
├── ClerkProvider (auth)
├── QueryClientProvider (data fetching)
├── ThemeProvider (dark mode)
├── AudioPlayerProvider (shared audio state)
│   ├── currentSample
│   ├── isPlaying
│   ├── audioElement
│   └── controls (play, pause, next, prev)
└── ResponsiveLayout
    ├── MobileLayout (mobile UI)
    └── DesktopLayout (desktop UI)
```

### 6.2 Audio Player Context (Shared)

`contexts/audio-player-context.tsx`:

```typescript
'use client';

import { createContext, useContext, useState, useRef, useEffect, ReactNode } from 'react';
import { Sample } from '@/types/api';

interface AudioPlayerContextValue {
  currentSample: Sample | null;
  isPlaying: boolean;
  play: (sample: Sample) => void;
  pause: () => void;
  toggle: () => void;
  next: () => void;
  previous: () => void;
  setPlaylist: (samples: Sample[]) => void;
}

const AudioPlayerContext = createContext<AudioPlayerContextValue | null>(null);

export function AudioPlayerProvider({ children }: { children: ReactNode }) {
  const [currentSample, setCurrentSample] = useState<Sample | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [playlist, setPlaylist] = useState<Sample[]>([]);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  // Create audio element
  useEffect(() => {
    audioRef.current = new Audio();
    audioRef.current.preload = 'metadata';

    return () => {
      audioRef.current?.pause();
      audioRef.current = null;
    };
  }, []);

  const play = (sample: Sample) => {
    if (!audioRef.current) return;

    const audioUrl = sample.audio_url_hls || sample.audio_url_mp3 || sample.audio_url_wav;
    if (!audioUrl) return;

    // If same sample, just resume
    if (currentSample?.id === sample.id) {
      audioRef.current.play();
      setIsPlaying(true);
      return;
    }

    // Load new sample
    setCurrentSample(sample);
    audioRef.current.src = audioUrl;
    audioRef.current.play();
    setIsPlaying(true);
  };

  const pause = () => {
    audioRef.current?.pause();
    setIsPlaying(false);
  };

  const toggle = () => {
    if (isPlaying) {
      pause();
    } else if (currentSample) {
      play(currentSample);
    }
  };

  const next = () => {
    if (!currentSample || playlist.length === 0) return;

    const currentIndex = playlist.findIndex(s => s.id === currentSample.id);
    const nextIndex = (currentIndex + 1) % playlist.length;
    play(playlist[nextIndex]);
  };

  const previous = () => {
    if (!currentSample || playlist.length === 0) return;

    const currentIndex = playlist.findIndex(s => s.id === currentSample.id);
    const prevIndex = currentIndex === 0 ? playlist.length - 1 : currentIndex - 1;
    play(playlist[prevIndex]);
  };

  return (
    <AudioPlayerContext.Provider
      value={{
        currentSample,
        isPlaying,
        play,
        pause,
        toggle,
        next,
        previous,
        setPlaylist,
      }}
    >
      {children}
    </AudioPlayerContext.Provider>
  );
}

export function useAudioPlayer() {
  const context = useContext(AudioPlayerContext);
  if (!context) {
    throw new Error('useAudioPlayer must be used within AudioPlayerProvider');
  }
  return context;
}
```

Now both mobile and desktop can use `useAudioPlayer()` hook to control playback!

---

## 7. Backend Requirements

### 7.1 New API Endpoints

#### Feed Endpoint

Add to `backend/app/api/v1/endpoints/samples.py`:

```python
@router.get("/feed", response_model=dict)
async def get_mobile_feed(
    skip: int = 0,
    limit: int = 20,
    exclude_ids: str = None,  # Comma-separated IDs to exclude
    algorithm: str = "popular",  # popular | recent | personalized
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Mobile-optimized feed endpoint
    Returns samples optimized for swipe interface
    """
    query = select(Sample).where(Sample.status == ProcessingStatus.COMPLETED)

    # Exclude already-seen samples
    if exclude_ids:
        excluded = [uuid.UUID(id) for id in exclude_ids.split(',')]
        query = query.where(Sample.id.notin_(excluded))

    # Apply algorithm
    if algorithm == "popular":
        query = query.order_by(Sample.view_count.desc())
    elif algorithm == "recent":
        query = query.order_by(Sample.created_at.desc())
    elif algorithm == "personalized":
        # TODO: Implement recommendation algorithm
        # For now, fallback to popular
        query = query.order_by(Sample.view_count.desc())

    # Pagination
    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    samples = result.scalars().all()

    # Get total count (for hasNextPage logic)
    count_query = select(func.count(Sample.id)).where(Sample.status == ProcessingStatus.COMPLETED)
    if exclude_ids:
        count_query = count_query.where(Sample.id.notin_(excluded))
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    return {
        "items": samples,
        "total": total,
        "skip": skip,
        "limit": limit,
        "has_more": skip + len(samples) < total
    }
```

#### Engagement Tracking Endpoint

```python
from pydantic import BaseModel

class EngagementTrack(BaseModel):
    action: str  # skipped | favorited | downloaded | shared
    listen_duration: int = 0  # Seconds

@router.post("/samples/{sample_id}/track")
async def track_engagement(
    sample_id: uuid.UUID,
    engagement: EngagementTrack,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Track user engagement with samples (for algorithm)
    """
    # Create engagement record
    engagement_record = SampleEngagement(
        id=uuid.uuid4(),
        user_id=current_user.id,
        sample_id=sample_id,
        action=engagement.action,
        listen_duration=engagement.listen_duration,
        device_type="mobile",  # Can detect from user agent
        created_at=utcnow_naive()
    )

    db.add(engagement_record)
    await db.commit()

    return {"status": "tracked"}
```

### 7.2 Database Schema Changes

Create migration `alembic/versions/xxx_add_engagement_tracking.py`:

```python
"""Add engagement tracking

Revision ID: xxx
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

def upgrade():
    op.create_table(
        'sample_engagements',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('sample_id', UUID(as_uuid=True), sa.ForeignKey('samples.id'), nullable=False),
        sa.Column('action', sa.String, nullable=False),  # skipped, favorited, downloaded, shared
        sa.Column('listen_duration', sa.Integer, default=0),  # Seconds
        sa.Column('device_type', sa.String, default='desktop'),  # mobile or desktop
        sa.Column('created_at', sa.DateTime, nullable=False),
    )

    # Indexes for queries
    op.create_index('ix_engagements_user_id', 'sample_engagements', ['user_id'])
    op.create_index('ix_engagements_sample_id', 'sample_engagements', ['sample_id'])
    op.create_index('ix_engagements_action', 'sample_engagements', ['action'])
    op.create_index('ix_engagements_created_at', 'sample_engagements', ['created_at'])

def downgrade():
    op.drop_table('sample_engagements')
```

### 7.3 Model Changes

Add to `backend/app/models/`:

```python
# backend/app/models/sample_engagement.py

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from app.core.database import Base
from app.utils import utcnow_naive

class SampleEngagement(Base):
    __tablename__ = "sample_engagements"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    sample_id = Column(UUID(as_uuid=True), ForeignKey('samples.id'), nullable=False)
    action = Column(String, nullable=False)  # skipped, favorited, downloaded, shared
    listen_duration = Column(Integer, default=0)  # Seconds
    device_type = Column(String, default='desktop')
    created_at = Column(DateTime, default=utcnow_naive, nullable=False)

    # Relationships
    user = relationship("User")
    sample = relationship("Sample")
```

---

## 8. Implementation Phases

### Phase 1: Foundation (Week 1 - 5 days)

**Goal**: Set up mobile-friendly infrastructure without breaking desktop.

**Tasks**:
- [ ] Create `useDeviceType` hook
- [ ] Create `ResponsiveLayout` wrapper
- [ ] Create mobile layout shell (`MobileLayout` component)
- [ ] Create bottom tab navigation
- [ ] Test: Verify mobile/desktop layouts render correctly
- [ ] Test: Verify existing desktop functionality still works

**Deliverable**: App renders different layouts on mobile vs desktop, but desktop experience unchanged.

---

### Phase 2: Video Swipe Interface (Week 2 - 7 days)

**Goal**: Build basic swipe feed with video playback.

**Tasks**:
- [ ] Create `SwipeCard` component
- [ ] Create `VideoPlayer` component
- [ ] Integrate framer-motion for swipe gestures
- [ ] Create `SwipeFeed` container component
- [ ] Wire up left/right swipe actions
- [ ] Test: Video plays when card is active
- [ ] Test: Swipe left/right changes cards

**Deliverable**: Working swipe feed on mobile with TikTok videos playing.

---

### Phase 3: Audio Integration (Week 3 - 5 days)

**Goal**: Play sample audio over videos.

**Tasks**:
- [ ] Create `AudioPlayerProvider` (shared context)
- [ ] Create `AudioOverlay` component (uses HLS player)
- [ ] Implement audio mode toggle (sample/original/both)
- [ ] Wire up audio controls
- [ ] Test: Sample audio plays over video
- [ ] Test: Audio mode toggle works
- [ ] Test: Audio syncs between mobile and desktop

**Deliverable**: Mobile users can hear extracted samples while watching videos.

---

### Phase 4: Metadata & Actions (Week 4 - 5 days)

**Goal**: Add overlays, buttons, and interactions.

**Tasks**:
- [ ] Create `MetadataOverlay` component
- [ ] Create `ActionButtons` component
- [ ] Wire up favorite action (swipe right / heart button)
- [ ] Add double-tap to favorite with animation
- [ ] Create `DetailsSheet` component (swipe up)
- [ ] Add share functionality
- [ ] Test: Favorite syncs to database
- [ ] Test: Details sheet displays all metadata

**Deliverable**: Full-featured swipe cards with all actions working.

---

### Phase 5: Backend Integration (Week 5 - 5 days)

**Goal**: Implement feed endpoint and engagement tracking.

**Tasks**:
- [ ] Create `/api/v1/feed` endpoint
- [ ] Create `/api/v1/samples/{id}/track` endpoint
- [ ] Create `SampleEngagement` model
- [ ] Create Alembic migration
- [ ] Wire up frontend to new endpoints
- [ ] Test: Feed returns samples correctly
- [ ] Test: Engagement tracking saves to database
- [ ] Test: Exclude already-seen samples works

**Deliverable**: Mobile feed pulls from dedicated endpoint with tracking.

---

### Phase 6: PWA Setup (Week 6 - 3 days)

**Goal**: Make app installable as PWA.

**Tasks**:
- [ ] Create `manifest.json`
- [ ] Create app icons (all sizes)
- [ ] Create iOS splash screens
- [ ] Create service worker (`sw.js`)
- [ ] Register service worker
- [ ] Create `PWAInstallPrompt` component
- [ ] Test: Install prompt appears on mobile
- [ ] Test: App installs to home screen
- [ ] Test: App works offline (favorites cached)

**Deliverable**: Mobile users can install app to home screen.

---

### Phase 7: Polish & Performance (Week 7 - 5 days)

**Goal**: Optimize performance and add animations.

**Tasks**:
- [ ] Implement card virtualization (only render 3 cards)
- [ ] Add video preloading strategy
- [ ] Optimize gesture throttling
- [ ] Add loading skeletons
- [ ] Add error boundaries
- [ ] Add haptic feedback (if supported)
- [ ] Performance audit (Lighthouse)
- [ ] Test: App scores 90+ on Lighthouse mobile
- [ ] Test: Smooth 60fps animations

**Deliverable**: Butter-smooth mobile experience.

---

### Phase 8: Mobile Favorites & Collections (Week 8 - 5 days)

**Goal**: Implement mobile versions of favorites and collections pages.

**Tasks**:
- [ ] Create mobile favorites grid layout
- [ ] Create mobile collections list
- [ ] Create mobile collection detail view
- [ ] Wire up tap-to-play from grid
- [ ] Add pull-to-refresh
- [ ] Test: Favorites sync desktop ↔ mobile
- [ ] Test: Collections work on mobile

**Deliverable**: Mobile users can view favorites and collections.

---

### Total Timeline: 8 Weeks (1 developer, full-time)

---

## 9. Testing Strategy

### 9.1 Device Testing Matrix

| Device | OS | Browser | Priority | Test Cases |
|--------|-----|---------|----------|------------|
| iPhone 14 Pro | iOS 17 | Safari | P0 | All features |
| iPhone SE (2nd gen) | iOS 16 | Safari | P0 | Small screen edge cases |
| Samsung Galaxy S23 | Android 13 | Chrome | P0 | All features |
| iPad Air | iPadOS 17 | Safari | P1 | Tablet landscape mode |
| Pixel 7 | Android 13 | Chrome | P1 | All features |
| Desktop Chrome | macOS | Chrome | P0 | Desktop unchanged |

### 9.2 Test Cases

**Mobile Swipe Feed**:
- [ ] Card swipes left (skip) correctly
- [ ] Card swipes right (favorite) correctly
- [ ] Card swipes up (details sheet) correctly
- [ ] Double-tap triggers favorite with animation
- [ ] Video plays when card is active
- [ ] Video pauses when card is swiped away
- [ ] Audio plays over video
- [ ] Audio mode toggle works (sample/original/both)
- [ ] Infinite scroll loads more samples
- [ ] No duplicate samples in feed
- [ ] End of feed message displays

**PWA**:
- [ ] Install prompt appears after 10 seconds
- [ ] App installs to home screen (iOS)
- [ ] App installs to home screen (Android)
- [ ] App launches in standalone mode
- [ ] Status bar color matches theme
- [ ] Splash screen displays correctly

**Performance**:
- [ ] First Contentful Paint < 1.5s
- [ ] Largest Contentful Paint < 2.5s
- [ ] Time to Interactive < 3.0s
- [ ] Cumulative Layout Shift < 0.1
- [ ] Swipe animations run at 60fps
- [ ] Video preloading works
- [ ] Memory usage < 150MB after 100 swipes

**Cross-Device Sync**:
- [ ] Favorite on mobile → shows on desktop
- [ ] Favorite on desktop → shows on mobile
- [ ] Download on desktop → tracked on mobile
- [ ] Collection created on desktop → visible on mobile

### 9.3 Automated Testing

**Unit Tests**:
```bash
# Test device detection hook
npm test -- use-device-type.test.ts

# Test swipe gestures
npm test -- swipe-card.test.ts
```

**E2E Tests** (Playwright):
```typescript
// tests/mobile-swipe.spec.ts

import { test, expect } from '@playwright/test';

test.describe('Mobile Swipe Feed', () => {
  test.use({ viewport: { width: 375, height: 667 } }); // iPhone SE

  test('should swipe right to favorite', async ({ page }) => {
    await page.goto('/');

    // Wait for first card to load
    await page.waitForSelector('[data-testid="swipe-card"]');

    // Swipe right gesture
    const card = page.locator('[data-testid="swipe-card"]').first();
    const box = await card.boundingBox();

    await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
    await page.mouse.down();
    await page.mouse.move(box.x + box.width + 100, box.y + box.height / 2);
    await page.mouse.up();

    // Verify next card loaded
    await expect(page.locator('[data-testid="swipe-card"]').first()).not.toBe(card);
  });

  test('should play video when card is active', async ({ page }) => {
    await page.goto('/');

    const video = page.locator('video').first();
    await expect(video).toBeVisible();

    // Verify video is playing
    const isPaused = await video.evaluate((v: HTMLVideoElement) => v.paused);
    expect(isPaused).toBe(false);
  });
});
```

---

## 10. Performance Optimization

### 10.1 Video Optimization

**Strategy**:
1. **Adaptive Quality**: Serve different video resolutions based on network speed
2. **Progressive Loading**: Load video in chunks (HTTP range requests)
3. **Preload Strategy**: Preload next 2 videos while current is playing
4. **Cache Aggressively**: Videos cached in browser + service worker

**Implementation**:

```typescript
// Detect network speed
function getNetworkQuality(): 'slow' | 'fast' {
  const connection = (navigator as any).connection;
  if (!connection) return 'fast';

  const effectiveType = connection.effectiveType;
  return effectiveType === '4g' ? 'fast' : 'slow';
}

// Select video quality
function getVideoUrl(sample: Sample): string {
  const quality = getNetworkQuality();

  if (quality === 'slow') {
    // Use lower resolution if available
    return sample.video_url_360p || sample.video_url;
  }

  return sample.video_url; // Full quality
}
```

**Video Preloading**:

```typescript
useEffect(() => {
  if (!isActive || !samples[currentIndex + 1]) return;

  const nextSample = samples[currentIndex + 1];
  const nextVideoUrl = getVideoUrl(nextSample);

  // Prefetch next video
  const link = document.createElement('link');
  link.rel = 'prefetch';
  link.as = 'video';
  link.href = nextVideoUrl;
  document.head.appendChild(link);

  return () => {
    document.head.removeChild(link);
  };
}, [currentIndex, isActive, samples]);
```

### 10.2 Card Virtualization

**Problem**: Rendering 100+ cards at once causes memory issues.

**Solution**: Only render 3 cards (current + 2 ahead).

```typescript
// In SwipeFeed component
const visibleCards = useMemo(() => {
  return samples.slice(currentIndex, currentIndex + 3);
}, [samples, currentIndex]);

// Only render visible cards
return (
  <div className="relative h-full">
    {visibleCards.map((sample, index) => (
      <SwipeCard
        key={sample.id}
        sample={sample}
        isActive={index === 0}
        // Stack cards behind
        style={{
          zIndex: visibleCards.length - index,
          transform: `translateY(${index * 10}px) scale(${1 - index * 0.05})`,
        }}
      />
    ))}
  </div>
);
```

### 10.3 Memory Management

**Monitor memory usage**:

```typescript
useEffect(() => {
  if (process.env.NODE_ENV === 'development') {
    const logMemory = () => {
      const memory = (performance as any).memory;
      if (memory) {
        console.log('Memory:', {
          used: (memory.usedJSHeapSize / 1048576).toFixed(2) + ' MB',
          total: (memory.totalJSHeapSize / 1048576).toFixed(2) + ' MB',
        });
      }
    };

    const interval = setInterval(logMemory, 5000);
    return () => clearInterval(interval);
  }
}, []);
```

**Clean up video elements**:

```typescript
useEffect(() => {
  // Remove old videos from DOM to free memory
  const oldVideos = document.querySelectorAll('video[data-index]');
  oldVideos.forEach((video: HTMLVideoElement) => {
    const index = parseInt(video.dataset.index || '0');
    if (Math.abs(index - currentIndex) > 5) {
      video.src = ''; // Release video memory
      video.load();
    }
  });
}, [currentIndex]);
```

### 10.4 Gesture Throttling

**Prevent jank during swipes**:

```typescript
import { throttle } from 'lodash';

const handleDrag = throttle((info: PanInfo) => {
  // Update UI based on drag
  setDragOffset(info.offset.x);
}, 16); // 60fps = 16ms per frame
```

---

## 11. Deployment & Rollout

### 11.1 Feature Flag Strategy

**Use feature flags to gradually roll out mobile experience**.

Add to `lib/feature-flags.ts`:

```typescript
export const FEATURES = {
  MOBILE_SWIPE_FEED: process.env.NEXT_PUBLIC_ENABLE_MOBILE_SWIPE === 'true',
  MOBILE_PWA: process.env.NEXT_PUBLIC_ENABLE_PWA === 'true',
};
```

Usage:

```typescript
import { FEATURES } from '@/lib/feature-flags';

export function ResponsiveLayout({ children }: ResponsiveLayoutProps) {
  const { isMobile } = useDeviceType();

  // Feature flag: Only show mobile layout if enabled
  if (isMobile && FEATURES.MOBILE_SWIPE_FEED) {
    return <MobileLayout>{children}</MobileLayout>;
  }

  return <DesktopLayout>{children}</DesktopLayout>;
}
```

### 11.2 Rollout Phases

**Phase 1: Internal Testing (Week 1)**
- Enable for team members only
- Test on real devices
- Fix critical bugs
- Gather initial feedback

**Phase 2: Beta (Week 2-3)**
- Enable for 10% of mobile users
- Monitor analytics:
  - Time on site
  - Samples per session
  - Favorite rate
  - Crash rate
- Fix bugs based on user reports

**Phase 3: Gradual Rollout (Week 4-6)**
- 25% → 50% → 75% → 100% of mobile users
- Monitor key metrics:
  - Mobile engagement vs desktop
  - Conversion rate (favorites, downloads)
  - Retention (day 1, day 7, day 30)
- A/B test variations (swipe threshold, animations)

**Phase 4: Full Launch (Week 7)**
- 100% of users
- Announce on social media
- Update marketing site
- Press release

### 11.3 Analytics Tracking

**Key Metrics**:

```typescript
// Track page view
analytics.track('Page Viewed', {
  device: isMobile ? 'mobile' : 'desktop',
  page: pathname,
});

// Track swipe actions
analytics.track('Sample Swiped', {
  direction: 'right', // or 'left'
  sample_id: sample.id,
  session_id: sessionId,
});

// Track video playback
analytics.track('Video Played', {
  sample_id: sample.id,
  watch_duration: duration,
  completion_rate: completion,
});

// Track PWA install
analytics.track('PWA Installed', {
  device: deviceInfo,
  prompt_shown: true,
});
```

**Dashboard Metrics** (Track in Mixpanel/Amplitude):
- Mobile vs Desktop usage split
- Average swipes per session
- Favorite rate (% of samples favorited)
- Video completion rate
- PWA install rate
- Retention curves (mobile vs desktop)

### 11.4 Rollback Plan

**If something goes wrong, quickly rollback**:

1. **Feature Flag Disable**:
   ```bash
   # In Vercel dashboard or .env
   NEXT_PUBLIC_ENABLE_MOBILE_SWIPE=false
   ```
   → Redeploy → Mobile users see desktop layout

2. **Backend Rollback**:
   ```bash
   # Rollback to previous Cloud Run revision
   gcloud run services update-traffic sampletok-backend \
     --to-revisions=<previous-revision>=100
   ```

3. **Database Rollback**:
   ```bash
   # Rollback migration if needed
   cd backend
   alembic downgrade -1
   ```

---

## 12. Success Criteria

### 12.1 Launch Criteria (MVP)

Before launching to users:
- [x] Mobile swipe feed works on iOS Safari
- [x] Mobile swipe feed works on Android Chrome
- [x] Favorites sync desktop ↔ mobile
- [x] Video playback is smooth (no stuttering)
- [x] PWA installs correctly on both platforms
- [x] Lighthouse mobile score > 80
- [x] Zero critical bugs in beta testing
- [x] Analytics tracking working

### 12.2 Success Metrics (Post-Launch)

**3 Months After Launch**:

| Metric | Target | Measurement |
|--------|--------|-------------|
| Mobile traffic % | >30% | Google Analytics |
| Mobile session length | >3 min | Analytics |
| Mobile samples/session | >15 | Custom tracking |
| Mobile favorite rate | >20% | Backend analytics |
| PWA install rate | >5% | Analytics |
| Mobile retention (D7) | >40% | Cohort analysis |
| Mobile → Desktop conversion | >10% | Cross-device tracking |

### 12.3 Product-Market Fit Indicators

**Signs that Option 2 is working**:
- ✅ Mobile users spend more time than desktop users
- ✅ Mobile sessions have higher favorite rates
- ✅ Users install PWA and return regularly
- ✅ Word-of-mouth growth on social media
- ✅ Mobile users eventually convert to desktop for downloads
- ✅ Reduced bounce rate on mobile pages

---

## 13. Risk Assessment & Mitigation

### 13.1 Technical Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Videos don't play on iOS Safari | High | Medium | Test early, fallback to poster + audio |
| PWA doesn't install on iOS | Medium | Low | Follow Apple PWA guidelines exactly |
| Poor performance on old devices | Medium | Medium | Implement adaptive quality, card virtualization |
| Service worker breaks desktop | High | Low | Thorough testing, feature flags |
| CORS issues with R2 videos | High | Low | Verify CORS headers in R2 config |

### 13.2 Product Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Users don't understand swipe UI | Medium | Medium | Onboarding tooltips, tutorial video |
| Mobile users never convert to desktop | Medium | Medium | Clear CTAs for desktop features |
| Mobile cannibalizes desktop usage | Low | Medium | Make desktop better, not worse |
| Videos consume too much bandwidth | Medium | Low | Adaptive quality, WiFi detection |

### 13.3 Business Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Development takes longer than 8 weeks | Medium | High | Phased rollout, MVP scope |
| Team burnout from aggressive timeline | High | Medium | Buffer weeks, clear priorities |
| Budget overruns (R2 bandwidth) | Medium | Medium | Monitor costs weekly, set alerts |

---

## 14. Next Steps

### Immediate (This Week)

1. **Decision**: Commit to Option 2 or not?
2. **Resources**: Assign 1 developer full-time (or 2 part-time)
3. **Design**: Create mobile mockups in Figma (swipe card, bottom nav)
4. **Setup**: Create `mobile` branch for development

### Week 1

- Implement Phase 1 (Foundation)
- Set up device detection
- Create mobile/desktop layout shell
- Test on real devices

### Week 2

- Implement Phase 2 (Video Swipe Interface)
- Build swipe card component
- Integrate video player
- Test swipe gestures

---

## Appendix A: Technology Stack

**Frontend**:
- React 19
- Next.js 15 (App Router)
- Framer Motion (animations)
- TanStack Query (data fetching)
- Tailwind CSS (styling)

**Backend**:
- FastAPI (existing)
- PostgreSQL (existing)
- Cloudflare R2 (existing)

**Libraries**:
- `framer-motion` - Swipe animations
- `react-spring-bottom-sheet` - Details sheet (optional)
- `@tanstack/react-query` - Data fetching (existing)

**PWA**:
- Workbox (service worker, optional)
- Web App Manifest

---

## Appendix B: Design System

**Colors**:
```css
/* Mobile-specific colors */
--mobile-overlay-gradient: linear-gradient(180deg, transparent 0%, rgba(0,0,0,0.8) 100%);
--mobile-action-like: #22c55e; /* Green */
--mobile-action-skip: #ef4444; /* Red */
```

**Typography**:
```css
/* Mobile font sizes (larger than desktop) */
--mobile-title: 1.5rem;
--mobile-body: 1rem;
--mobile-caption: 0.875rem;
```

**Spacing**:
```css
/* Mobile safe areas */
--safe-area-inset-top: env(safe-area-inset-top);
--safe-area-inset-bottom: env(safe-area-inset-bottom);
```

---

## Appendix C: Glossary

- **Swipe Feed**: Vertical stack of cards that users swipe through (TikTok-style)
- **Card Virtualization**: Only rendering cards that are currently visible
- **PWA**: Progressive Web App - web app that can be installed like native
- **Service Worker**: Background script that enables offline functionality
- **HLS**: HTTP Live Streaming - adaptive audio streaming protocol
- **Safe Area**: Area of screen not obscured by notch/home indicator (iOS)
- **Deep Link**: URL that opens specific content in app (e.g., `/s/[id]`)

---

**Document Version**: 1.0
**Last Updated**: 2025-11-04
**Author**: Claude Code
**Status**: Ready for Review & Approval
