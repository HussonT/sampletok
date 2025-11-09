# Mobile PWA - Tinder-Style Sample Discovery

## Overview
Transform SampleTok into a mobile-first Progressive Web App with a Tinder-style swipeable card interface for discovering audio samples. The mobile experience focuses on frictionless browsing with TikTok video playback, gamified swipe interactions, and strategic authentication prompts to maximize user conversion.

## Vision
- **Tinder-style swipe interface**: Left = dismiss, Right = add to favorites
- **TikTok video integration**: Show source video while browsing samples
- **Guest-friendly browsing**: Users can scroll freely without login
- **Strategic auth triggers**: Swipe actions prompt Clerk sign-up flow
- **Frictionless conversion**: Easy onboarding to convert browsers to users

---

## Architecture Overview

### Technology Stack
- **PWA Framework**: next-pwa (Next.js PWA plugin)
- **Animation Library**: framer-motion (smooth swipe animations)
- **Video Embed**: TikTok oEmbed API / iframe
- **Authentication**: Clerk (existing)
- **State Management**: React Context + localStorage (guest state)
- **Offline Storage**: Service Worker + IndexedDB
- **Analytics**: PostHog / Mixpanel (event tracking)

### Route Structure
```
/mobile                    # Mobile landing page (swipe feed)
/mobile/favorites          # User's liked samples
/mobile/search             # Filter by BPM, key, creator
/mobile/profile            # User settings and stats
/mobile/onboarding         # First-time user tutorial
```

---

## Reusable Components from Existing Codebase

### ✅ Can Reuse (Minimal Changes)

#### 1. Audio Playback System
**Location**: `frontend/app/components/features/audio-player.tsx`, `hls-audio-player.tsx`
**Reuse Strategy**:
- Adapt for mobile with simplified controls
- Remove desktop-only features (waveform scrubbing)
- Keep HLS streaming for performance
- Add mobile-specific touch controls

#### 2. Sample Data Models
**Location**: `frontend/app/types/sample.ts`
**Reuse Strategy**:
- Use existing `Sample` type definition
- Reuse API client methods (`lib/api-client.ts`)
- Leverage existing TanStack Query hooks

#### 3. Authentication (Clerk)
**Location**: Throughout frontend with `@clerk/nextjs`
**Reuse Strategy**:
- Trigger existing Clerk modal programmatically
- Use `useAuth()` hook for user state
- Leverage existing user session management

#### 4. Backend API Endpoints
**Existing Endpoints to Reuse**:
- `GET /api/v1/samples` - Fetch sample feed (add mobile filters)
- `GET /api/v1/samples/{id}` - Get sample details
- `POST /api/v1/samples/{id}/download` - Track downloads

**New Endpoints Needed**:
- `POST /api/v1/samples/{id}/like` - Add to favorites
- `DELETE /api/v1/samples/{id}/like` - Remove from favorites
- `POST /api/v1/samples/{id}/dismiss` - Mark as "not interested"
- `GET /api/v1/mobile/feed` - Personalized mobile feed

#### 5. TikTok Creator Data
**Location**: `backend/app/models/tiktok_creator.py`, `app/services/tiktok/creator_service.py`
**Reuse Strategy**:
- Display creator info in swipe cards
- Use existing cached creator data
- No changes needed

#### 6. Waveform Visualization
**Location**: Sample processing pipeline generates waveform PNGs
**Reuse Strategy**:
- Display as static image in mobile cards
- No interactive waveform needed (simplify UX)

### ❌ Cannot Reuse (Mobile-Specific)

#### 1. Desktop Table UI
**Location**: `frontend/app/components/features/sounds-table.tsx`
**Why**: Completely different interaction model (table rows vs swipe cards)

#### 2. Desktop Player Bar
**Location**: `frontend/app/components/features/bottom-player.tsx`
**Why**: Desktop-oriented layout, needs mobile redesign

#### 3. Desktop Navigation
**Location**: `frontend/app/components/layout/`
**Why**: Mobile uses bottom tab navigation instead of sidebar

---

## Implementation Plan

### Phase 1: PWA Foundation (Day 1)

#### Task 1.1: Install PWA Dependencies
```bash
cd frontend
npm install next-pwa
npm install framer-motion
npm install react-use-gesture  # For swipe detection
```

#### Task 1.2: Configure PWA Manifest
**File**: `frontend/public/manifest.json`
```json
{
  "name": "SampleTok - Audio Sample Discovery",
  "short_name": "SampleTok",
  "description": "Discover TikTok audio samples with swipeable cards",
  "start_url": "/mobile",
  "display": "standalone",
  "background_color": "#000000",
  "theme_color": "#10b981",
  "orientation": "portrait",
  "icons": [
    {
      "src": "/icons/icon-192x192.png",
      "sizes": "192x192",
      "type": "image/png"
    },
    {
      "src": "/icons/icon-512x512.png",
      "sizes": "512x512",
      "type": "image/png"
    },
    {
      "src": "/icons/icon-maskable-512x512.png",
      "sizes": "512x512",
      "type": "image/png",
      "purpose": "maskable"
    }
  ]
}
```

#### Task 1.3: Configure Next.js PWA
**File**: `frontend/next.config.js`
```javascript
const withPWA = require('next-pwa')({
  dest: 'public',
  register: true,
  skipWaiting: true,
  disable: process.env.NODE_ENV === 'development',
  runtimeCaching: [
    {
      urlPattern: /^https:\/\/.*\.sampletok\.com\/api\/.*/i,
      handler: 'NetworkFirst',
      options: {
        cacheName: 'api-cache',
        expiration: {
          maxEntries: 100,
          maxAgeSeconds: 60 * 60 // 1 hour
        }
      }
    },
    {
      urlPattern: /\.(?:mp3|wav)$/i,
      handler: 'CacheFirst',
      options: {
        cacheName: 'audio-cache',
        expiration: {
          maxEntries: 50,
          maxAgeSeconds: 30 * 24 * 60 * 60 // 30 days
        }
      }
    }
  ]
});

module.exports = withPWA({
  // existing config
});
```

#### Task 1.4: Create App Icons
- Generate icons using https://www.pwabuilder.com/imageGenerator
- Place in `frontend/public/icons/`
- Sizes: 192x192, 512x512, maskable variant

#### Task 1.5: Mobile Detection Middleware
**File**: `frontend/middleware.ts`
```typescript
import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function middleware(request: NextRequest) {
  const userAgent = request.headers.get('user-agent') || '';
  const isMobile = /iPhone|iPad|iPod|Android/i.test(userAgent);

  // Auto-redirect mobile users to /mobile route (optional)
  if (isMobile && request.nextUrl.pathname === '/' && !request.cookies.get('prefer-desktop')) {
    return NextResponse.redirect(new URL('/mobile', request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: '/',
};
```

---

### Phase 2: Swipeable Card UI (Days 2-3)

#### Task 2.1: Create Mobile Layout
**File**: `frontend/app/mobile/layout.tsx`
```typescript
import { MobileBottomNav } from '@/components/mobile/mobile-bottom-nav';

export default function MobileLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen bg-black text-white">
      {/* Full-screen mobile content */}
      <main className="pb-20">{children}</main>

      {/* Fixed bottom navigation */}
      <MobileBottomNav />
    </div>
  );
}
```

#### Task 2.2: Swipe Card Component
**File**: `frontend/app/components/mobile/swipe-card.tsx`
```typescript
import { motion, useMotionValue, useTransform } from 'framer-motion';
import { useGesture } from 'react-use-gesture';
import { Sample } from '@/types/sample';

interface SwipeCardProps {
  sample: Sample;
  onSwipeLeft: () => void;
  onSwipeRight: () => void;
  style?: any;
}

export function SwipeCard({ sample, onSwipeLeft, onSwipeRight, style }: SwipeCardProps) {
  const x = useMotionValue(0);
  const rotate = useTransform(x, [-200, 200], [-25, 25]);
  const opacity = useTransform(x, [-200, -100, 0, 100, 200], [0, 1, 1, 1, 0]);

  const bind = useGesture({
    onDrag: ({ offset: [ox] }) => {
      x.set(ox);
    },
    onDragEnd: ({ offset: [ox], velocity: [vx] }) => {
      if (Math.abs(ox) > 100 || Math.abs(vx) > 0.5) {
        // Swipe complete
        if (ox > 0) {
          onSwipeRight();
        } else {
          onSwipeLeft();
        }
      } else {
        // Spring back to center
        x.set(0);
      }
    },
  });

  return (
    <motion.div
      {...bind()}
      style={{
        x,
        rotate,
        opacity,
        ...style,
      }}
      className="absolute inset-0 touch-none"
    >
      {/* TikTok Video Embed */}
      <div className="relative h-[70vh] bg-gray-900 rounded-2xl overflow-hidden">
        <iframe
          src={`https://www.tiktok.com/embed/v2/${sample.tiktok_video_id}`}
          className="w-full h-full"
          allow="autoplay; encrypted-media;"
        />

        {/* Swipe Overlays */}
        <motion.div
          className="absolute inset-0 bg-red-500/80 flex items-center justify-center"
          style={{ opacity: useTransform(x, [-200, 0], [1, 0]) }}
        >
          <span className="text-6xl">👎</span>
        </motion.div>

        <motion.div
          className="absolute inset-0 bg-green-500/80 flex items-center justify-center"
          style={{ opacity: useTransform(x, [0, 200], [0, 1]) }}
        >
          <span className="text-6xl">❤️</span>
        </motion.div>
      </div>

      {/* Sample Info */}
      <div className="mt-4 space-y-2">
        <h3 className="text-xl font-bold">{sample.creator_name || 'Unknown'}</h3>
        <div className="flex gap-4 text-sm text-gray-400">
          <span>{sample.bpm} BPM</span>
          <span>{sample.key}</span>
          <span>{sample.duration}s</span>
        </div>

        {/* Waveform Preview */}
        <img
          src={sample.waveform_url}
          alt="Waveform"
          className="w-full h-16 object-cover rounded-lg"
        />
      </div>
    </motion.div>
  );
}
```

#### Task 2.3: Sample Queue Hook
**File**: `frontend/app/hooks/use-sample-queue.ts`
```typescript
import { useState, useEffect } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import { Sample } from '@/types/sample';

interface QueueState {
  samples: Sample[];
  currentIndex: number;
  likedIds: string[];
  dismissedIds: string[];
}

export function useSampleQueue() {
  const [state, setState] = useState<QueueState>({
    samples: [],
    currentIndex: 0,
    likedIds: JSON.parse(localStorage.getItem('liked_samples') || '[]'),
    dismissedIds: JSON.parse(localStorage.getItem('dismissed_samples') || '[]'),
  });

  // Fetch initial samples
  const { data: samplesData } = useQuery({
    queryKey: ['mobile-feed', state.currentIndex],
    queryFn: () => apiClient.getSamples({
      limit: 20,
      exclude_ids: [...state.likedIds, ...state.dismissedIds],
    }),
  });

  useEffect(() => {
    if (samplesData?.samples) {
      setState(prev => ({
        ...prev,
        samples: [...prev.samples, ...samplesData.samples],
      }));
    }
  }, [samplesData]);

  const swipeLeft = (sampleId: string) => {
    const newDismissed = [...state.dismissedIds, sampleId];
    localStorage.setItem('dismissed_samples', JSON.stringify(newDismissed));
    setState(prev => ({
      ...prev,
      currentIndex: prev.currentIndex + 1,
      dismissedIds: newDismissed,
    }));
  };

  const swipeRight = (sampleId: string) => {
    const newLiked = [...state.likedIds, sampleId];
    localStorage.setItem('liked_samples', JSON.stringify(newLiked));
    setState(prev => ({
      ...prev,
      currentIndex: prev.currentIndex + 1,
      likedIds: newLiked,
    }));
  };

  const currentSample = state.samples[state.currentIndex];
  const hasMore = state.currentIndex < state.samples.length - 5;

  return {
    currentSample,
    nextSample: state.samples[state.currentIndex + 1],
    swipeLeft,
    swipeRight,
    hasMore,
    isLoading: !samplesData,
  };
}
```

#### Task 2.4: Mobile Feed Page
**File**: `frontend/app/mobile/page.tsx`
```typescript
'use client';

import { SwipeCard } from '@/components/mobile/swipe-card';
import { useSampleQueue } from '@/hooks/use-sample-queue';
import { useAuth } from '@clerk/nextjs';
import { useState } from 'react';

export default function MobileFeedPage() {
  const { currentSample, nextSample, swipeLeft, swipeRight, hasMore } = useSampleQueue();
  const { isSignedIn, userId } = useAuth();
  const [showAuthPrompt, setShowAuthPrompt] = useState(false);

  const handleSwipe = (direction: 'left' | 'right') => {
    // Trigger auth prompt on first swipe for guests
    if (!isSignedIn && !showAuthPrompt) {
      setShowAuthPrompt(true);
      return;
    }

    if (direction === 'left') {
      swipeLeft(currentSample.id);
    } else {
      swipeRight(currentSample.id);
      // Sync to backend if logged in
      if (isSignedIn) {
        // API call to like sample
      }
    }
  };

  if (!currentSample) {
    return <div className="flex items-center justify-center h-screen">Loading...</div>;
  }

  return (
    <div className="relative h-screen p-4">
      {/* Card Stack */}
      <div className="relative h-full">
        {/* Next card (behind) */}
        {nextSample && (
          <SwipeCard
            sample={nextSample}
            onSwipeLeft={() => {}}
            onSwipeRight={() => {}}
            style={{ scale: 0.95, zIndex: 0 }}
          />
        )}

        {/* Current card (front) */}
        <SwipeCard
          sample={currentSample}
          onSwipeLeft={() => handleSwipe('left')}
          onSwipeRight={() => handleSwipe('right')}
          style={{ zIndex: 1 }}
        />
      </div>

      {/* Auth Prompt Modal */}
      {showAuthPrompt && (
        <AuthPromptModal
          onClose={() => setShowAuthPrompt(false)}
          onSignUp={() => {
            // Trigger Clerk sign-in
          }}
        />
      )}
    </div>
  );
}
```

---

### Phase 3: Authentication Flow (Days 4-5)

#### Task 3.1: Auth Prompt Modal
**File**: `frontend/app/components/mobile/auth-prompt-modal.tsx`
```typescript
import { SignInButton } from '@clerk/nextjs';
import { Dialog, DialogContent } from '@/components/ui/dialog';

interface AuthPromptModalProps {
  onClose: () => void;
  onSignUp: () => void;
}

export function AuthPromptModal({ onClose, onSignUp }: AuthPromptModalProps) {
  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent className="bg-black border-gray-800 text-white">
        <div className="space-y-6 text-center">
          <div className="text-6xl">🎵</div>

          <h2 className="text-2xl font-bold">
            Sign up to save your favorites!
          </h2>

          <p className="text-gray-400">
            Create an account to:
          </p>

          <ul className="text-left space-y-2 text-gray-300">
            <li>❤️ Save favorite samples</li>
            <li>⬇️ Download audio files</li>
            <li>🎁 Get free credits</li>
            <li>🔥 Access premium features</li>
          </ul>

          <SignInButton mode="modal">
            <button className="w-full bg-green-600 hover:bg-green-700 text-white py-3 rounded-lg font-semibold">
              Sign Up (Free)
            </button>
          </SignInButton>

          <button
            onClick={onClose}
            className="text-gray-400 text-sm underline"
          >
            Continue browsing as guest
          </button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
```

#### Task 3.2: Post-Login Sync
**File**: `frontend/app/hooks/use-auth-sync.ts`
```typescript
import { useEffect } from 'react';
import { useAuth } from '@clerk/nextjs';
import { useMutation } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';

export function useAuthSync() {
  const { isSignedIn, userId } = useAuth();

  const syncGuestData = useMutation({
    mutationFn: async () => {
      const likedIds = JSON.parse(localStorage.getItem('liked_samples') || '[]');
      const dismissedIds = JSON.parse(localStorage.getItem('dismissed_samples') || '[]');

      // Sync liked samples to backend
      await Promise.all(
        likedIds.map((id: string) => apiClient.likeSample(id))
      );

      // Sync dismissed samples
      await Promise.all(
        dismissedIds.map((id: string) => apiClient.dismissSample(id))
      );

      // Clear local storage after sync
      localStorage.removeItem('liked_samples');
      localStorage.removeItem('dismissed_samples');
    },
  });

  useEffect(() => {
    if (isSignedIn && userId) {
      const hasGuestData =
        localStorage.getItem('liked_samples') ||
        localStorage.getItem('dismissed_samples');

      if (hasGuestData) {
        syncGuestData.mutate();
      }
    }
  }, [isSignedIn, userId]);

  return { isSyncing: syncGuestData.isPending };
}
```

---

### Phase 4: Backend API Endpoints (Day 6)

#### Task 4.1: Like/Unlike Endpoints
**File**: `backend/app/api/v1/endpoints/samples.py`
```python
@router.post("/{sample_id}/like")
async def like_sample(
    sample_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Add sample to user's favorites"""
    # Check if already liked
    existing = await db.execute(
        select(SampleLike).where(
            SampleLike.user_id == current_user.id,
            SampleLike.sample_id == sample_id
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Already liked")

    # Create like
    like = SampleLike(user_id=current_user.id, sample_id=sample_id)
    db.add(like)

    # Increment like count on sample
    await db.execute(
        update(Sample)
        .where(Sample.id == sample_id)
        .values(like_count=Sample.like_count + 1)
    )

    await db.commit()
    return {"status": "success"}

@router.delete("/{sample_id}/like")
async def unlike_sample(
    sample_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Remove sample from favorites"""
    result = await db.execute(
        delete(SampleLike).where(
            SampleLike.user_id == current_user.id,
            SampleLike.sample_id == sample_id
        )
    )

    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Like not found")

    # Decrement like count
    await db.execute(
        update(Sample)
        .where(Sample.id == sample_id)
        .values(like_count=Sample.like_count - 1)
    )

    await db.commit()
    return {"status": "success"}
```

#### Task 4.2: Dismiss Endpoint
**File**: `backend/app/api/v1/endpoints/samples.py`
```python
@router.post("/{sample_id}/dismiss")
async def dismiss_sample(
    sample_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Mark sample as 'not interested' for this user"""
    # Create dismissal record
    dismissal = SampleDismissal(user_id=current_user.id, sample_id=sample_id)
    db.add(dismissal)
    await db.commit()
    return {"status": "success"}
```

#### Task 4.3: Mobile Feed Endpoint
**File**: `backend/app/api/v1/endpoints/mobile.py`
```python
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, and_, not_
from app.models import Sample, SampleLike, SampleDismissal

router = APIRouter(prefix="/mobile", tags=["mobile"])

@router.get("/feed")
async def get_mobile_feed(
    limit: int = Query(20, le=50),
    cursor: str | None = None,
    current_user: User = Depends(get_current_user_optional),  # Optional auth
    db: AsyncSession = Depends(get_db)
):
    """
    Get personalized mobile feed
    Excludes liked/dismissed samples for authenticated users
    """
    query = select(Sample).where(Sample.status == "completed")

    # Exclude liked/dismissed for logged-in users
    if current_user:
        liked_ids = await db.execute(
            select(SampleLike.sample_id).where(SampleLike.user_id == current_user.id)
        )
        dismissed_ids = await db.execute(
            select(SampleDismissal.sample_id).where(SampleDismissal.user_id == current_user.id)
        )

        exclude_ids = [*liked_ids.scalars(), *dismissed_ids.scalars()]
        if exclude_ids:
            query = query.where(not_(Sample.id.in_(exclude_ids)))

    # Pagination
    if cursor:
        query = query.where(Sample.created_at < cursor)

    query = query.order_by(Sample.created_at.desc()).limit(limit)

    result = await db.execute(query)
    samples = result.scalars().all()

    return {
        "samples": samples,
        "next_cursor": samples[-1].created_at if samples else None,
        "has_more": len(samples) == limit
    }
```

#### Task 4.4: Database Models
**File**: `backend/app/models/sample_interaction.py`
```python
from sqlalchemy import Column, String, DateTime, ForeignKey, Index
from sqlalchemy.sql import func
from app.models.base import Base

class SampleLike(Base):
    __tablename__ = "sample_likes"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    sample_id = Column(String, ForeignKey("samples.id"), nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("ix_sample_likes_user_sample", "user_id", "sample_id", unique=True),
    )

class SampleDismissal(Base):
    __tablename__ = "sample_dismissals"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    sample_id = Column(String, ForeignKey("samples.id"), nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("ix_sample_dismissals_user_sample", "user_id", "sample_id", unique=True),
    )
```

#### Task 4.5: Database Migration
```bash
cd backend
alembic revision --autogenerate -m "Add sample likes and dismissals for mobile"
alembic upgrade head
```

---

### Phase 5: Mobile Features (Days 7-8)

#### Task 5.1: Bottom Navigation
**File**: `frontend/app/components/mobile/mobile-bottom-nav.tsx`
```typescript
import { Home, Heart, Search, User } from 'lucide-react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

export function MobileBottomNav() {
  const pathname = usePathname();

  const tabs = [
    { href: '/mobile', icon: Home, label: 'Feed' },
    { href: '/mobile/favorites', icon: Heart, label: 'Favorites' },
    { href: '/mobile/search', icon: Search, label: 'Search' },
    { href: '/mobile/profile', icon: User, label: 'Profile' },
  ];

  return (
    <nav className="fixed bottom-0 left-0 right-0 bg-black border-t border-gray-800 z-50">
      <div className="flex justify-around items-center h-16">
        {tabs.map(({ href, icon: Icon, label }) => {
          const isActive = pathname === href;
          return (
            <Link
              key={href}
              href={href}
              className={`flex flex-col items-center justify-center w-full h-full ${
                isActive ? 'text-green-500' : 'text-gray-400'
              }`}
            >
              <Icon className="w-6 h-6" />
              <span className="text-xs mt-1">{label}</span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
```

#### Task 5.2: Favorites Page
**File**: `frontend/app/mobile/favorites/page.tsx`
```typescript
'use client';

import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import { useAuth } from '@clerk/nextjs';

export default function FavoritesPage() {
  const { isSignedIn } = useAuth();

  const { data: favorites } = useQuery({
    queryKey: ['favorites'],
    queryFn: () => apiClient.getFavorites(),
    enabled: isSignedIn,
  });

  if (!isSignedIn) {
    return (
      <div className="flex flex-col items-center justify-center h-screen text-center p-8">
        <Heart className="w-16 h-16 text-gray-600 mb-4" />
        <h2 className="text-xl font-bold mb-2">Sign in to see your favorites</h2>
        <SignInButton mode="modal">
          <button className="mt-4 bg-green-600 px-6 py-2 rounded-lg">
            Sign In
          </button>
        </SignInButton>
      </div>
    );
  }

  return (
    <div className="p-4">
      <h1 className="text-2xl font-bold mb-6">Your Favorites</h1>
      <div className="grid grid-cols-2 gap-4">
        {favorites?.samples.map(sample => (
          <SampleCard key={sample.id} sample={sample} />
        ))}
      </div>
    </div>
  );
}
```

#### Task 5.3: Pull-to-Refresh
**File**: `frontend/app/components/mobile/pull-to-refresh.tsx`
```typescript
import { useState } from 'react';
import { useGesture } from 'react-use-gesture';
import { motion } from 'framer-motion';

export function PullToRefresh({ onRefresh, children }) {
  const [pulling, setPulling] = useState(false);
  const [pullDistance, setPullDistance] = useState(0);

  const bind = useGesture({
    onDrag: ({ movement: [, my], direction: [, dy], last }) => {
      if (window.scrollY === 0 && dy > 0) {
        setPullDistance(Math.min(my, 100));
        if (last && my > 60) {
          setPulling(true);
          onRefresh().finally(() => {
            setPulling(false);
            setPullDistance(0);
          });
        } else if (last) {
          setPullDistance(0);
        }
      }
    },
  });

  return (
    <div {...bind()} className="relative">
      <motion.div
        className="absolute top-0 left-0 right-0 flex justify-center py-2"
        animate={{ height: pullDistance }}
      >
        {pulling ? '🔄 Refreshing...' : pullDistance > 60 ? '🎵 Release to refresh' : ''}
      </motion.div>
      {children}
    </div>
  );
}
```

#### Task 5.4: Haptic Feedback
**File**: `frontend/app/utils/haptics.ts`
```typescript
export function triggerHaptic(style: 'light' | 'medium' | 'heavy' = 'medium') {
  if (typeof window === 'undefined') return;

  // iOS Haptic Engine
  if ('vibrate' in navigator) {
    const patterns = {
      light: [10],
      medium: [20],
      heavy: [30],
    };
    navigator.vibrate(patterns[style]);
  }

  // For devices with Haptic API (newer iOS/Android)
  if ('HapticFeedback' in window) {
    (window as any).HapticFeedback.impact(style);
  }
}
```

---

### Phase 6: Performance Optimization (Day 9)

#### Task 6.1: Video Preloading
**File**: `frontend/app/hooks/use-video-preload.ts`
```typescript
import { useEffect } from 'react';

export function useVideoPreload(videoUrls: string[]) {
  useEffect(() => {
    // Preload next 2 videos
    const preloadUrls = videoUrls.slice(0, 2);

    preloadUrls.forEach(url => {
      const link = document.createElement('link');
      link.rel = 'prefetch';
      link.as = 'video';
      link.href = url;
      document.head.appendChild(link);
    });

    return () => {
      // Cleanup
      document.querySelectorAll('link[rel="prefetch"][as="video"]').forEach(el => el.remove());
    };
  }, [videoUrls]);
}
```

#### Task 6.2: Image Optimization
- Use Next.js `<Image>` component for waveforms and avatars
- Add `loading="lazy"` for below-fold images
- Serve WebP format with fallback

#### Task 6.3: Code Splitting
**File**: `frontend/app/mobile/page.tsx`
```typescript
import dynamic from 'next/dynamic';

const SwipeCard = dynamic(() => import('@/components/mobile/swipe-card'), {
  loading: () => <div className="animate-pulse bg-gray-800 rounded-2xl h-[70vh]" />,
});

const AuthPromptModal = dynamic(() => import('@/components/mobile/auth-prompt-modal'), {
  ssr: false,
});
```

---

### Phase 7: Analytics & A/B Testing (Day 10)

#### Task 7.1: Event Tracking
**File**: `frontend/app/utils/analytics.ts`
```typescript
import posthog from 'posthog-js';

export const trackSwipe = (direction: 'left' | 'right', sampleId: string, isGuest: boolean) => {
  posthog.capture('swipe', {
    direction,
    sample_id: sampleId,
    is_guest: isGuest,
  });
};

export const trackAuthPrompt = (action: 'shown' | 'dismissed' | 'completed') => {
  posthog.capture('auth_prompt', { action });
};

export const trackConversion = (userId: string, guestActionsCount: number) => {
  posthog.capture('guest_conversion', {
    user_id: userId,
    guest_actions: guestActionsCount,
  });
};
```

#### Task 7.2: A/B Testing Setup
```typescript
// Test: When to show auth prompt
const authPromptTrigger = posthog.getFeatureFlag('auth_prompt_trigger');
// Variants: 'immediate', 'after_5_swipes', 'after_10_swipes'

const shouldShowAuthPrompt = () => {
  if (authPromptTrigger === 'immediate') return swipeCount === 1;
  if (authPromptTrigger === 'after_5_swipes') return swipeCount === 5;
  if (authPromptTrigger === 'after_10_swipes') return swipeCount === 10;
  return false;
};
```

---

### Phase 8: Polish & Edge Cases (Days 11-12)

#### Task 8.1: Onboarding Tutorial
**File**: `frontend/app/components/mobile/onboarding-tutorial.tsx`
```typescript
import { useState } from 'react';
import { Dialog } from '@/components/ui/dialog';

export function OnboardingTutorial() {
  const [step, setStep] = useState(0);
  const hasSeenTutorial = localStorage.getItem('seen_tutorial');

  if (hasSeenTutorial) return null;

  const steps = [
    {
      title: 'Swipe to Discover',
      description: 'Swipe right ❤️ to save samples, left 👎 to pass',
      animation: <SwipeAnimation />,
    },
    {
      title: 'Watch & Listen',
      description: 'See the original TikTok video and hear the audio',
      animation: <VideoAnimation />,
    },
    {
      title: 'Save Your Favorites',
      description: 'Sign up (free) to save samples and download audio',
      animation: <HeartAnimation />,
    },
  ];

  const currentStep = steps[step];

  return (
    <Dialog open>
      <div className="p-8 text-center">
        <div className="mb-8">{currentStep.animation}</div>
        <h2 className="text-2xl font-bold mb-4">{currentStep.title}</h2>
        <p className="text-gray-400 mb-8">{currentStep.description}</p>

        <button
          onClick={() => {
            if (step < steps.length - 1) {
              setStep(step + 1);
            } else {
              localStorage.setItem('seen_tutorial', 'true');
            }
          }}
          className="bg-green-600 px-8 py-3 rounded-lg"
        >
          {step < steps.length - 1 ? 'Next' : 'Get Started'}
        </button>
      </div>
    </Dialog>
  );
}
```

#### Task 8.2: Error States
```typescript
// No internet
<div className="fixed top-4 left-4 right-4 bg-red-600 text-white p-4 rounded-lg">
  ⚠️ No internet connection. Some features may not work.
</div>

// No more samples
<div className="flex flex-col items-center justify-center h-screen">
  <span className="text-6xl mb-4">🎉</span>
  <h2 className="text-2xl font-bold mb-2">You're all caught up!</h2>
  <p className="text-gray-400 mb-6">Check back later for more samples</p>
  <button onClick={refresh} className="bg-green-600 px-6 py-2 rounded-lg">
    Refresh Feed
  </button>
</div>

// Video load failure
<div className="bg-gray-900 h-[70vh] flex flex-col items-center justify-center">
  <span className="text-4xl mb-4">📹</span>
  <p className="text-gray-400 mb-4">Video unavailable</p>
  <button onClick={skipToNext} className="text-green-500 underline">
    Skip to next sample
  </button>
</div>
```

#### Task 8.3: Accessibility
```typescript
// Keyboard navigation (for desktop testing)
useEffect(() => {
  const handleKeyPress = (e: KeyboardEvent) => {
    if (e.key === 'ArrowLeft') swipeLeft();
    if (e.key === 'ArrowRight') swipeRight();
    if (e.key === ' ') toggleAudio();
  };
  window.addEventListener('keydown', handleKeyPress);
  return () => window.removeEventListener('keydown', handleKeyPress);
}, []);

// Screen reader support
<div role="region" aria-label="Sample discovery feed">
  <button
    aria-label={`Dismiss sample by ${sample.creator_name}`}
    onClick={swipeLeft}
  >
    <XIcon />
  </button>
  <button
    aria-label={`Like sample by ${sample.creator_name}`}
    onClick={swipeRight}
  >
    <HeartIcon />
  </button>
</div>
```

---

## Reusable Components from Instagram Plan

While the Instagram Collections plan is unrelated to mobile PWA, we can borrow some architectural patterns:

### ✅ Patterns to Reuse

1. **Error Handling Matrix**: Apply same error categorization (invalid input, auth failure, network timeout, etc.)
2. **Monitoring Strategy**: Track success rates, processing times, failure patterns
3. **Database Migration Guidelines**: Follow same Alembic best practices
4. **Testing Strategy**: Unit tests, integration tests, manual test cases
5. **Deployment Checklist**: Pre-deployment, deployment, post-deployment phases

### ❌ Components NOT Reusable

- Gallery-DL integration (not needed)
- Cookie management (not needed)
- Collection processing pipeline (different use case)
- Instagram-specific services (not needed)

---

## Success Metrics (3 Months Post-Launch)

### Adoption Metrics
- [ ] 50% of mobile visitors use swipe interface
- [ ] 30% conversion rate (guest → signed-up user)
- [ ] Average 50 swipes per session
- [ ] 80% completion rate (users who swipe at least 5 times)

### Technical Metrics
- [ ] <2s time to first swipe (page load)
- [ ] <100ms swipe gesture latency
- [ ] >90% video playback success rate
- [ ] <5% API error rate

### User Engagement
- [ ] 40% of swiped samples are liked (not dismissed)
- [ ] 60% of users return within 24 hours
- [ ] Average 3 sessions per week per user
- [ ] 70% of liked samples are later downloaded

---

## Risk Mitigation

### Risk 1: Poor Mobile Performance
**Impact**: High bounce rate, bad user experience
**Mitigation**:
- Aggressive code splitting and lazy loading
- Service worker caching for repeat visits
- Preload only next 2 samples (not entire queue)
- Optimize video embed size and quality

### Risk 2: TikTok Embed Issues
**Impact**: Videos don't load, broken experience
**Mitigation**:
- Fallback to thumbnail + audio if embed fails
- Add "Skip" button for broken videos
- Monitor embed failure rate and alert
- Consider alternative: direct video URL with custom player

### Risk 3: Low Guest-to-User Conversion
**Impact**: Users browse but don't sign up
**Mitigation**:
- A/B test auth prompt timing and messaging
- Show concrete benefits (credits, downloads)
- Add social proof ("Join 10,000+ producers")
- Offer sign-up bonus (5 free credits)

### Risk 4: Auth Friction
**Impact**: Users abandon during sign-up
**Mitigation**:
- Use Clerk's streamlined social sign-in
- Allow Google/Apple one-click sign-up
- Save guest progress during sign-up flow
- Auto-sync liked samples after auth

---

## Deployment Checklist

### Pre-Deployment
- [ ] Generate all PWA icons (192x192, 512x512, maskable)
- [ ] Test PWA installation on iOS Safari and Android Chrome
- [ ] Verify service worker caching works offline
- [ ] Run Lighthouse audit (target: >90 mobile score)
- [ ] Test swipe gestures on real devices (iOS & Android)
- [ ] Load test mobile API endpoints (simulate 1000 concurrent users)
- [ ] Set up PostHog/Mixpanel analytics
- [ ] Configure A/B testing flags

### Deployment
- [ ] Deploy backend with new `/mobile/feed` and like/dismiss endpoints
- [ ] Run database migrations (`alembic upgrade head`)
- [ ] Deploy frontend with mobile routes
- [ ] Verify PWA manifest served correctly
- [ ] Test end-to-end on mobile devices
- [ ] Enable analytics event tracking
- [ ] Monitor error rates for first 24 hours

### Post-Deployment
- [ ] Create user documentation (how to install PWA)
- [ ] Announce mobile feature to users (email, social)
- [ ] Monitor conversion funnel (swipe → auth → sign-up)
- [ ] Collect user feedback (NPS survey)
- [ ] Track A/B test results weekly
- [ ] Iterate on auth prompt timing based on data

---

## Future Enhancements (Post-MVP)

### Phase 2 Features
1. **Undo Button**: Float undo button for 3s after swipe
2. **Filters**: Filter feed by BPM range, key, genre
3. **Daily Discovery Limit**: Free tier gets 50 swipes/day, paid unlimited
4. **Share Samples**: Share individual samples to social media
5. **Super Like**: Long-press to "super like" and auto-download
6. **Collections**: Create custom playlists from liked samples
7. **Discovery Preferences**: Set preferred BPM, key, genre
8. **Streak Rewards**: Daily swipe streak unlocks bonus credits

### Phase 3 Features
1. **AR Filters**: Apply filters to TikTok videos while browsing
2. **Collaborative Playlists**: Share collections with friends
3. **AI Recommendations**: ML-based personalized feed
4. **Live Swipe Parties**: Real-time group discovery sessions
5. **Sample Battles**: Swipe-based voting for best samples
6. **Creator Profiles**: Follow creators, see their samples

---

## Questions & Decisions Needed

### Before Implementation
1. **Auth Prompt Timing**: When to show? (Recommend: after 3 swipes)
2. **Guest Swipe Limit**: Should we limit? (Recommend: unlimited browsing)
3. **Video Auto-Play**: Muted or unmuted? (Recommend: muted with tap to unmute)
4. **Like Count Display**: Show on cards? (Recommend: yes, for social proof)
5. **Undo Functionality**: Allow? (Recommend: yes, 3s window)

### Technical Decisions
1. **Swipe Library**: framer-motion vs react-spring? (Recommend: framer-motion)
2. **Video Player**: TikTok embed vs custom? (Recommend: TikTok embed initially)
3. **Analytics Platform**: PostHog vs Mixpanel? (Recommend: PostHog - open source)
4. **State Management**: Context vs Zustand? (Recommend: Context for MVP)
5. **Offline Support**: How much caching? (Recommend: last 20 samples + metadata)

---

## Estimated Timeline

- **Phase 1 (PWA Setup)**: 1 day
- **Phase 2 (Swipe UI)**: 2-3 days
- **Phase 3 (Auth Flow)**: 1-2 days
- **Phase 4 (Backend)**: 1-2 days
- **Phase 5 (Mobile Features)**: 2 days
- **Phase 6 (Performance)**: 1 day
- **Phase 7 (Analytics)**: 1 day
- **Phase 8 (Polish)**: 1-2 days

**Total**: ~10-14 days for full implementation

---

## Technical Deep Dive: TikTok Embed

### TikTok oEmbed API
```typescript
// Fetch embed HTML
const response = await fetch(
  `https://www.tiktok.com/oembed?url=${encodeURIComponent(tiktokUrl)}`
);
const data = await response.json();

// Returns:
{
  "version": "1.0",
  "type": "video",
  "title": "Video title",
  "author_url": "https://www.tiktok.com/@username",
  "author_name": "Username",
  "width": "100%",
  "height": "100%",
  "html": "<iframe src='https://www.tiktok.com/embed/v2/7123456789'></iframe>",
  "thumbnail_url": "https://...",
  "thumbnail_width": 720,
  "thumbnail_height": 1280
}
```

### Embed Configuration
```html
<!-- TikTok Embed v2 -->
<iframe
  src="https://www.tiktok.com/embed/v2/7123456789?music_info=0&description=0"
  width="100%"
  height="100%"
  frameborder="0"
  allow="autoplay; encrypted-media; picture-in-picture"
  allowfullscreen
></iframe>
```

### Query Parameters
- `music_info=0` - Hide music info overlay
- `description=0` - Hide description text
- `autoplay=1` - Auto-play video

---

This plan provides a comprehensive roadmap for building a mobile-first PWA with Tinder-style swipe discovery. The architecture leverages existing backend infrastructure while creating a new mobile-optimized frontend experience focused on conversion and engagement.
