import { Skeleton } from '@/components/ui/skeleton';
import { Loader2, Music } from 'lucide-react';

export default function Loading() {
  return (
    <div className="flex h-screen bg-background">
      {/* Sidebar skeleton */}
      <div className="w-64 border-r p-4 space-y-6">
        <div className="flex items-center gap-2 mb-6">
          <Skeleton className="h-8 w-8 rounded" />
          <Skeleton className="h-6 w-24" />
        </div>
        <div className="space-y-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <div
              key={i}
              className="flex items-center gap-3 animate-in fade-in-50"
              style={{ animationDelay: `${i * 50}ms` }}
            >
              <Skeleton className="h-5 w-5 rounded" />
              <Skeleton className="h-5 flex-1" />
            </div>
          ))}
        </div>
      </div>

      {/* Main content skeleton */}
      <div className="flex-1 flex flex-col">
        {/* Header skeleton */}
        <div className="border-b px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Skeleton className="h-5 w-5" />
            <Skeleton className="h-6 w-24" />
          </div>
          <Skeleton className="h-5 w-20" />
        </div>

        {/* Loading bar */}
        <div className="w-full h-1 bg-muted overflow-hidden">
          <div
            className="h-full bg-primary animate-shimmer"
            style={{
              backgroundImage: 'linear-gradient(90deg, transparent, hsl(var(--primary) / 0.8), transparent)',
              backgroundSize: '200% 100%',
            }}
          />
        </div>

        {/* Content area with centered loader */}
        <div className="flex-1 flex items-center justify-center">
          <div className="flex flex-col items-center gap-4">
            <div className="relative">
              <Music className="w-16 h-16 text-primary/20" />
              <Loader2 className="w-16 h-16 text-primary animate-spin absolute inset-0" />
            </div>
            <p className="text-sm text-muted-foreground animate-pulse">Loading samples...</p>
          </div>
        </div>

        {/* Player skeleton */}
        <div className="border-t p-4">
          <div className="flex items-center gap-4">
            <Skeleton className="h-12 w-12 rounded" />
            <div className="flex-1 space-y-2">
              <Skeleton className="h-4 w-48" />
              <Skeleton className="h-3 w-32" />
            </div>
            <div className="flex gap-2">
              <Skeleton className="h-10 w-10 rounded-full" />
              <Skeleton className="h-10 w-10 rounded-full" />
              <Skeleton className="h-10 w-10 rounded-full" />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}