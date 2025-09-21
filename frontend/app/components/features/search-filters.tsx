import React from 'react';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Search
} from 'lucide-react';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { AddSampleDialog } from '@/components/features/add-sample-dialog';

interface SearchFiltersProps {
  searchQuery: string;
  onSearchChange: (query: string) => void;
  selectedGenre: string;
  onGenreChange: (genre: string) => void;
  selectedBPM: string;
  onBPMChange: (bpm: string) => void;
  selectedVideoType: string;
  onVideoTypeChange: (videoType: string) => void;
  sortBy: string;
  onSortChange: (sort: string) => void;
  resultCount: number;
}

export function SearchFilters({
  searchQuery,
  onSearchChange,
  selectedGenre,
  onGenreChange,
  selectedBPM,
  onBPMChange,
  selectedVideoType,
  onVideoTypeChange,
  sortBy,
  onSortChange,
  resultCount
}: SearchFiltersProps) {
  const popularGenres = [
    'house', 'hip hop', 'drill', 'pop', 'rnb', 'techno', 'trap'
  ];

  const popularVideoTypes = [
    'viral', 'inspirational', 'funny', 'dance', 'trending'
  ];

  return (
    <div className="bg-background border-b border-border">
      <div className="px-6 py-4 space-y-4">
        {/* Search and Filters Row */}
        <div className="flex items-center gap-4">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input
              placeholder="Search samples..."
              value={searchQuery}
              onChange={(e) => onSearchChange(e.target.value)}
              className="pl-10 bg-input-background"
            />
          </div>
          
          <Select value={selectedGenre} onValueChange={onGenreChange}>
            <SelectTrigger className="w-[140px] bg-input-background">
              <SelectValue placeholder="Genre" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Genres</SelectItem>
              <SelectItem value="house">House</SelectItem>
              <SelectItem value="hip hop">Hip Hop</SelectItem>
              <SelectItem value="drill">Drill</SelectItem>
              <SelectItem value="pop">Pop</SelectItem>
              <SelectItem value="rnb">R&B</SelectItem>
              <SelectItem value="techno">Techno</SelectItem>
              <SelectItem value="trap">Trap</SelectItem>
            </SelectContent>
          </Select>

          <Select value={selectedBPM} onValueChange={onBPMChange}>
            <SelectTrigger className="w-[120px] bg-input-background">
              <SelectValue placeholder="BPM" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All BPM</SelectItem>
              <SelectItem value="slow">60-90</SelectItem>
              <SelectItem value="medium">90-120</SelectItem>
              <SelectItem value="fast">120-150</SelectItem>
              <SelectItem value="very-fast">150+</SelectItem>
            </SelectContent>
          </Select>

          <Select value={selectedVideoType} onValueChange={onVideoTypeChange}>
            <SelectTrigger className="w-[140px] bg-input-background">
              <SelectValue placeholder="Video Type" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Types</SelectItem>
              <SelectItem value="viral">Viral</SelectItem>
              <SelectItem value="inspirational">Inspirational</SelectItem>
              <SelectItem value="funny">Funny</SelectItem>
              <SelectItem value="dance">Dance</SelectItem>
              <SelectItem value="trending">Trending</SelectItem>
              <SelectItem value="motivational">Motivational</SelectItem>
              <SelectItem value="lifestyle">Lifestyle</SelectItem>
              <SelectItem value="educational">Educational</SelectItem>
            </SelectContent>
          </Select>

          <Select value={sortBy} onValueChange={onSortChange}>
            <SelectTrigger className="w-[140px] bg-input-background">
              <SelectValue placeholder="Sort by" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="recent">Most recent</SelectItem>
              <SelectItem value="popular">Most popular</SelectItem>
              <SelectItem value="name">Name A-Z</SelectItem>
            </SelectContent>
          </Select>

          <AddSampleDialog />
        </div>

        {/* Popular Genres */}
        <div className="flex items-center gap-2">
          <span className="text-sm text-muted-foreground mr-2">Popular:</span>
          {popularGenres.map((genre) => (
            <Badge
              key={genre}
              variant={selectedGenre === genre ? "default" : "secondary"}
              className={`cursor-pointer text-xs px-2 py-1 ${
                selectedGenre === genre 
                  ? 'bg-primary text-primary-foreground' 
                  : 'bg-secondary/50 text-secondary-foreground hover:bg-secondary'
              }`}
              onClick={() => onGenreChange(selectedGenre === genre ? 'all' : genre)}
            >
              {genre}
            </Badge>
          ))}
        </div>

        {/* Popular Video Types */}
        <div className="flex items-center gap-2">
          <span className="text-sm text-muted-foreground mr-2">Video Vibes:</span>
          {popularVideoTypes.map((videoType) => (
            <Badge
              key={videoType}
              variant={selectedVideoType === videoType ? "default" : "secondary"}
              className={`cursor-pointer text-xs px-2 py-1 ${
                selectedVideoType === videoType 
                  ? 'bg-primary text-primary-foreground' 
                  : 'bg-secondary/50 text-secondary-foreground hover:bg-secondary'
              }`}
              onClick={() => onVideoTypeChange(selectedVideoType === videoType ? 'all' : videoType)}
            >
              {videoType}
            </Badge>
          ))}
        </div>

        {/* Results Count */}
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">
            {resultCount.toLocaleString()} samples found
          </p>
          {(searchQuery || selectedGenre !== 'all' || selectedBPM !== 'all' || selectedVideoType !== 'all') && (
            <Button 
              variant="ghost" 
              size="sm"
              onClick={() => {
                onSearchChange('');
                onGenreChange('all');
                onBPMChange('all');
                onVideoTypeChange('all');
              }}
              className="text-xs"
            >
              Clear filters
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}