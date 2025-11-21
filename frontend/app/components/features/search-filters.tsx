import React, { useCallback, useRef } from 'react';
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
import { analytics } from '@/lib/analytics';

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
  onProcessingStarted?: (taskId: string, url: string) => void;
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
  resultCount,
  onProcessingStarted
}: SearchFiltersProps) {
  const popularGenres = [
    'house', 'hip hop', 'drill', 'pop', 'rnb', 'techno', 'trap'
  ];

  const popularVideoTypes = [
    'viral', 'inspirational', 'funny', 'dance', 'trending'
  ];

  const handleSearchChange = (query: string) => {
    onSearchChange(query);

    // Track search when user types (only track non-empty queries)
    if (query.trim()) {
      analytics.searchPerformed(query, resultCount);
    }
  };

  const handleGenreChange = (genre: string) => {
    onGenreChange(genre);

    // Track filter application
    if (genre !== 'all') {
      analytics.filterApplied('genre', genre);
    }
  };

  const handleBPMChange = (bpm: string) => {
    onBPMChange(bpm);

    // Track filter application
    if (bpm !== 'all') {
      analytics.filterApplied('bpm', bpm);
    }
  };

  const handleVideoTypeChange = (videoType: string) => {
    onVideoTypeChange(videoType);

    // Track filter application
    if (videoType !== 'all') {
      analytics.filterApplied('video_type', videoType);
    }
  };

  const handleSortChange = (sort: string) => {
    onSortChange(sort);

    // Track sort change
    analytics.filterApplied('sort', sort);
  };

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
              onChange={(e) => handleSearchChange(e.target.value)}
              className="pl-10 bg-input-background"
            />
          </div>

          <Select value={selectedGenre} onValueChange={handleGenreChange}>
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

          <Select value={selectedBPM} onValueChange={handleBPMChange}>
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

          <Select value={selectedVideoType} onValueChange={handleVideoTypeChange}>
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

          <Select value={sortBy} onValueChange={handleSortChange}>
            <SelectTrigger className="w-[240px] bg-input-background">
              <SelectValue placeholder="Sort by" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="created_at_desc">Newest</SelectItem>
              <SelectItem value="created_at_asc">Oldest</SelectItem>
              <SelectItem value="views_desc">Views (High to Low)</SelectItem>
              <SelectItem value="views_asc">Views (Low to High)</SelectItem>
              <SelectItem value="followers_desc">Artist Followers (High to Low)</SelectItem>
              <SelectItem value="followers_asc">Artist Followers (Low to High)</SelectItem>
              <SelectItem value="bpm_asc">BPM (Low to High)</SelectItem>
              <SelectItem value="bpm_desc">BPM (High to Low)</SelectItem>
            </SelectContent>
          </Select>

          <AddSampleDialog onProcessingStarted={onProcessingStarted} />
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
              onClick={() => handleGenreChange(selectedGenre === genre ? 'all' : genre)}
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
              onClick={() => handleVideoTypeChange(selectedVideoType === videoType ? 'all' : videoType)}
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