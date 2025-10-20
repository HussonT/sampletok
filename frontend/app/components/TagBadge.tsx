'use client';

import { Tag, TagCategory } from '@/app/types/api';
import { X } from 'lucide-react';

interface TagBadgeProps {
  tag: Tag | string; // Support both Tag objects and string tags (legacy)
  onRemove?: () => void;
  clickable?: boolean;
  onClick?: () => void;
  size?: 'sm' | 'md' | 'lg';
}

const categoryColors: Record<TagCategory, string> = {
  [TagCategory.GENRE]: 'bg-purple-100 text-purple-800 hover:bg-purple-200',
  [TagCategory.MOOD]: 'bg-blue-100 text-blue-800 hover:bg-blue-200',
  [TagCategory.INSTRUMENT]: 'bg-green-100 text-green-800 hover:bg-green-200',
  [TagCategory.CONTENT]: 'bg-orange-100 text-orange-800 hover:bg-orange-200',
  [TagCategory.TEMPO]: 'bg-red-100 text-red-800 hover:bg-red-200',
  [TagCategory.EFFECT]: 'bg-yellow-100 text-yellow-800 hover:bg-yellow-200',
  [TagCategory.OTHER]: 'bg-gray-100 text-gray-800 hover:bg-gray-200',
};

const sizeClasses = {
  sm: 'text-xs px-2 py-0.5',
  md: 'text-sm px-2.5 py-1',
  lg: 'text-base px-3 py-1.5',
};

export default function TagBadge({
  tag,
  onRemove,
  clickable = false,
  onClick,
  size = 'sm',
}: TagBadgeProps) {
  const isTagObject = typeof tag === 'object' && 'category' in tag;
  const displayName = isTagObject ? tag.display_name : tag;
  const category = isTagObject ? tag.category : TagCategory.OTHER;
  const colorClass = categoryColors[category];

  const handleClick = () => {
    if (clickable && onClick) {
      onClick();
    }
  };

  return (
    <span
      className={`
        inline-flex items-center gap-1 rounded-full font-medium transition-colors
        ${colorClass}
        ${sizeClasses[size]}
        ${clickable ? 'cursor-pointer' : ''}
        ${onRemove ? 'pr-1' : ''}
      `}
      onClick={handleClick}
    >
      <span>{displayName}</span>
      {onRemove && (
        <button
          onClick={(e) => {
            e.stopPropagation();
            onRemove();
          }}
          className="ml-0.5 rounded-full p-0.5 hover:bg-black/10 transition-colors"
          aria-label={`Remove ${displayName} tag`}
        >
          <X size={size === 'sm' ? 12 : size === 'md' ? 14 : 16} />
        </button>
      )}
    </span>
  );
}
