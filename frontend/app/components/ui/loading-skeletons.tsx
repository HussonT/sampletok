import { Skeleton } from '@/components/ui/skeleton';
import { Card, CardContent } from '@/components/ui/card';
import { Loader2 } from 'lucide-react';

/**
 * Full-page centered loading spinner
 * Use for: Page-level loading, data fetching
 */
export function PageLoader({ message }: { message?: string }) {
  return (
    <div className="flex-1 flex flex-col items-center justify-center gap-4">
      <Loader2 className="w-10 h-10 animate-spin text-primary" />
      {message && (
        <p className="text-sm text-muted-foreground animate-pulse">{message}</p>
      )}
    </div>
  );
}

/**
 * Table row loading skeleton
 * Use for: SoundsTable, data tables
 */
export function TableLoadingSkeleton({ rows = 5 }: { rows?: number }) {
  return (
    <div className="space-y-4">
      {Array.from({ length: rows }).map((_, i) => (
        <div
          key={i}
          className="flex items-center gap-4 p-4 border border-border rounded-lg bg-card/50 animate-in fade-in-50"
          style={{ animationDelay: `${i * 50}ms` }}
        >
          {/* Waveform */}
          <Skeleton className="h-20 w-48 rounded" />

          {/* Content */}
          <div className="flex-1 space-y-2.5">
            <Skeleton className="h-5 w-3/4" />
            <div className="flex gap-2">
              <Skeleton className="h-4 w-20" />
              <Skeleton className="h-4 w-16" />
              <Skeleton className="h-4 w-24" />
            </div>
          </div>

          {/* Actions */}
          <div className="flex gap-2">
            <Skeleton className="h-10 w-10 rounded-full" />
            <Skeleton className="h-10 w-10 rounded-full" />
            <Skeleton className="h-10 w-10 rounded-full" />
          </div>
        </div>
      ))}
    </div>
  );
}

/**
 * Card loading skeleton
 * Use for: Collections, grid layouts
 */
export function CardSkeleton({ count = 3 }: { count?: number }) {
  return (
    <div className="grid gap-4">
      {Array.from({ length: count }).map((_, i) => (
        <Card
          key={i}
          className="animate-in fade-in-50"
          style={{ animationDelay: `${i * 75}ms` }}
        >
          <CardContent className="p-6">
            <div className="flex items-start gap-4">
              {/* Icon */}
              <Skeleton className="w-16 h-16 rounded-lg flex-shrink-0" />

              {/* Content */}
              <div className="flex-1 space-y-3">
                <div className="space-y-2">
                  <Skeleton className="h-6 w-3/4" />
                  <Skeleton className="h-4 w-1/2" />
                </div>
                <div className="flex gap-4">
                  <Skeleton className="h-4 w-24" />
                  <Skeleton className="h-4 w-20" />
                </div>
                <Skeleton className="h-10 w-32" />
              </div>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

/**
 * Grid of sample cards loading skeleton
 * Use for: Sample grids, media galleries
 */
export function SampleGridSkeleton({ count = 8 }: { count?: number }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          className="space-y-3 animate-in fade-in-50"
          style={{ animationDelay: `${i * 30}ms` }}
        >
          <Skeleton className="aspect-square w-full rounded-lg" />
          <div className="space-y-2">
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-3 w-1/2" />
          </div>
        </div>
      ))}
    </div>
  );
}

/**
 * Inline loading spinner
 * Use for: Button states, inline actions
 */
export function InlineLoader({ message }: { message?: string }) {
  return (
    <div className="flex items-center gap-2 text-sm text-muted-foreground">
      <Loader2 className="w-4 h-4 animate-spin" />
      {message && <span>{message}</span>}
    </div>
  );
}

/**
 * Shimmer effect loading bar
 * Use for: Progress indication, streaming content
 */
export function LoadingBar() {
  return (
    <div className="w-full h-1 bg-muted overflow-hidden">
      <div className="h-full bg-primary animate-shimmer"
           style={{
             backgroundImage: 'linear-gradient(90deg, transparent, hsl(var(--primary) / 0.8), transparent)',
             backgroundSize: '200% 100%',
             animation: 'shimmer 1.5s infinite'
           }}
      />
    </div>
  );
}
