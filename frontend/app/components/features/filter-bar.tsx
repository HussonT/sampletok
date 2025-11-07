'use client';

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

// Hard-coded options (must match database format: lowercase "major"/"minor" with flat notation)
const MUSICAL_KEYS = [
  'A major', 'A minor',
  'Ab major', 'Ab minor',
  'B major', 'B minor',
  'Bb major', 'Bb minor',
  'C major', 'C minor',
  'C# major', 'C# minor',
  'D major', 'D minor',
  'E major', 'E minor',
  'Eb major',
  'F major', 'F minor',
  'F# major', 'F# minor',
  'G major', 'G minor',
];

const BPM_RANGES = [
  { label: '60-90 (Slow)', min: 60, max: 90 },
  { label: '90-120 (Medium)', min: 90, max: 120 },
  { label: '120-140 (Upbeat)', min: 120, max: 140 },
  { label: '140-180 (Fast)', min: 140, max: 180 },
];

interface FilterBarProps {
  bpmMin: number | null;
  bpmMax: number | null;
  musicalKey: string | null;
  sortBy: string;
  hasSearch?: boolean;
  onBpmChange: (min: number | null, max: number | null) => void;
  onKeyChange: (key: string | null) => void;
  onSortChange: (sort: string) => void;
}

export function FilterBar({
  bpmMin,
  bpmMax,
  musicalKey,
  sortBy,
  hasSearch = false,
  onBpmChange,
  onKeyChange,
  onSortChange,
}: FilterBarProps) {
  return (
    <div className="flex items-center gap-3 py-3 border-y mb-4">
      {/* Key Filter */}
      <Select value={musicalKey || '__all__'} onValueChange={(v) => onKeyChange(v === '__all__' ? null : v)}>
        <SelectTrigger className="w-[140px]">
          <SelectValue placeholder="Key" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="__all__">All Keys</SelectItem>
          {MUSICAL_KEYS.map(key => (
            <SelectItem key={key} value={key}>{key}</SelectItem>
          ))}
        </SelectContent>
      </Select>

      {/* BPM Filter */}
      <Select
        value={bpmMin && bpmMax ? `${bpmMin}-${bpmMax}` : '__all__'}
        onValueChange={(v) => {
          if (v === '__all__') {
            onBpmChange(null, null);
          } else {
            const [min, max] = v.split('-').map(Number);
            onBpmChange(min, max);
          }
        }}
      >
        <SelectTrigger className="w-[160px]">
          <SelectValue placeholder="BPM" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="__all__">All BPMs</SelectItem>
          {BPM_RANGES.map(range => (
            <SelectItem key={range.label} value={`${range.min}-${range.max}`}>
              {range.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      {/* Sort */}
      <div className="ml-auto">
        <Select value={hasSearch ? "relevance" : sortBy} onValueChange={onSortChange} disabled={hasSearch}>
          <SelectTrigger className="w-[180px]">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {hasSearch ? (
              <SelectItem value="relevance">Relevance (Search Active)</SelectItem>
            ) : (
              <>
                <SelectItem value="created_at_desc">Newest</SelectItem>
                <SelectItem value="created_at_asc">Oldest</SelectItem>
                <SelectItem value="views_desc">Most Popular</SelectItem>
                <SelectItem value="bpm_asc">BPM (Low to High)</SelectItem>
                <SelectItem value="bpm_desc">BPM (High to Low)</SelectItem>
              </>
            )}
          </SelectContent>
        </Select>
      </div>
    </div>
  );
}
