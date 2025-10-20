'use client';

import { Tag } from '@/app/types/api';
import TagBadge from './TagBadge';

interface TagListProps {
  tags: (Tag | string)[];
  onTagClick?: (tag: Tag | string) => void;
  onTagRemove?: (tag: Tag | string) => void;
  maxDisplay?: number;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export default function TagList({
  tags,
  onTagClick,
  onTagRemove,
  maxDisplay,
  size = 'sm',
  className = '',
}: TagListProps) {
  if (!tags || tags.length === 0) {
    return null;
  }

  const displayTags = maxDisplay ? tags.slice(0, maxDisplay) : tags;
  const remainingCount = maxDisplay && tags.length > maxDisplay ? tags.length - maxDisplay : 0;

  return (
    <div className={`flex flex-wrap gap-1.5 ${className}`}>
      {displayTags.map((tag, index) => {
        const key = typeof tag === 'object' ? tag.id : `${tag}-${index}`;
        return (
          <TagBadge
            key={key}
            tag={tag}
            onClick={onTagClick ? () => onTagClick(tag) : undefined}
            onRemove={onTagRemove ? () => onTagRemove(tag) : undefined}
            clickable={!!onTagClick}
            size={size}
          />
        );
      })}
      {remainingCount > 0 && (
        <span className="text-xs text-gray-500 self-center">
          +{remainingCount} more
        </span>
      )}
    </div>
  );
}
