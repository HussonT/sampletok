'use client';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { X } from 'lucide-react';

interface ActiveFiltersProps {
  search: string;
  tags: string[];
  bpmMin: number | null;
  bpmMax: number | null;
  musicalKey: string | null;
  onRemoveTag: (tag: string) => void;
  onClear: (filter: string) => void;
  onClearAll: () => void;
}

export function ActiveFilters({
  search,
  tags,
  bpmMin,
  bpmMax,
  musicalKey,
  onRemoveTag,
  onClear,
  onClearAll,
}: ActiveFiltersProps) {
  const hasFilters = search || tags.length > 0 || bpmMin || bpmMax || musicalKey;

  if (!hasFilters) return null;

  return (
    <div className="flex items-center gap-2 py-3 flex-wrap">
      <span className="text-sm text-muted-foreground">Active filters:</span>

      {search && (
        <Badge variant="secondary" className="gap-2">
          Search: &quot;{search}&quot;
          <X
            className="h-3 w-3 cursor-pointer hover:text-destructive"
            onClick={() => onClear('search')}
          />
        </Badge>
      )}

      {tags.map(tag => (
        <Badge key={tag} variant="secondary" className="gap-2">
          {tag}
          <X
            className="h-3 w-3 cursor-pointer hover:text-destructive"
            onClick={() => onRemoveTag(tag)}
          />
        </Badge>
      ))}

      {(bpmMin || bpmMax) && (
        <Badge variant="secondary" className="gap-2">
          BPM: {bpmMin || 60}-{bpmMax || 180}
          <X
            className="h-3 w-3 cursor-pointer hover:text-destructive"
            onClick={() => onClear('bpm')}
          />
        </Badge>
      )}

      {musicalKey && (
        <Badge variant="secondary" className="gap-2">
          Key: {musicalKey}
          <X
            className="h-3 w-3 cursor-pointer hover:text-destructive"
            onClick={() => onClear('key')}
          />
        </Badge>
      )}

      <Button variant="ghost" size="sm" onClick={onClearAll} className="ml-2">
        Clear all
      </Button>
    </div>
  );
}
