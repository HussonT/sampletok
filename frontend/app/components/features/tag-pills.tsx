'use client';

import { Badge } from '@/components/ui/badge';
import { useQuery } from '@tanstack/react-query';
import { publicApi } from '@/lib/api-client';
import { cn } from '@/lib/utils';

interface TagPillsProps {
  activeTags: string[];
  onToggleTag: (tag: string) => void;
}

export function TagPills({ activeTags, onToggleTag }: TagPillsProps) {
  const { data: popularTags, isLoading } = useQuery({
    queryKey: ['tags', 'popular'],
    queryFn: async () => {
      const response = await publicApi.get<Array<{tag: string, count: number}>>('/samples/tags/popular?limit=30');
      return response;
    },
    staleTime: 5 * 60 * 1000, // Cache for 5 minutes
  });

  if (isLoading || !popularTags) {
    return <div className="h-10 animate-pulse bg-muted rounded" />;
  }

  return (
    <div className="flex flex-wrap gap-2 py-4">
      {popularTags.map(({ tag, count }) => {
        const isActive = activeTags.includes(tag);

        return (
          <Badge
            key={tag}
            variant={isActive ? "default" : "outline"}
            className={cn(
              "cursor-pointer transition-colors",
              "hover:bg-primary hover:text-primary-foreground",
              isActive && "bg-primary text-primary-foreground"
            )}
            onClick={() => onToggleTag(tag)}
          >
            {tag}
            <span className="ml-1.5 text-xs opacity-70">{count}</span>
          </Badge>
        );
      })}
    </div>
  );
}
