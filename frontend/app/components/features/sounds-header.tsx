import React from 'react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { 
  Search, 
  RotateCcw, 
  Download, 
  Settings,
  ChevronDown
} from 'lucide-react';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

interface SoundsHeaderProps {
  activeTab?: string;
  onTabChange?: (tab: string) => void;
  searchQuery?: string;
  onSearchChange?: (query: string) => void;
  resultCount?: number;
}

export function SoundsHeader({ 
  activeTab = 'samples', 
  onTabChange, 
  searchQuery = '', 
  onSearchChange,
  resultCount = 1315
}: SoundsHeaderProps) {
  const tabs = [
    { id: 'samples', label: 'Samples' },
    { id: 'presets', label: 'Presets' },
    { id: 'packs', label: 'Packs' }
  ];

  const genres = [
    'house', 'drums', 'hyperpop', 'botanica', 'synth', 'indie electronic', 
    'pop', 'vocals', 'grooves', 'rnb', 'percussion', 'chords', 'fx', 
    'keys', 'melodic stack', 'songstarters', 'yamaha', 'hip hop', 'bass', 'drill'
  ];

  return (
    <div className="bg-background border-b border-border">
      {/* Main Header */}
      <div className="flex items-center justify-between px-6 py-3 border-b border-border">
        <div className="flex items-center gap-4">
          <h1 className="text-2xl font-bold text-foreground">Sounds</h1>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="sm">
            <RotateCcw className="w-4 h-4 mr-2" />
            Sync All
          </Button>
          <Button variant="ghost" size="sm">
            <Download className="w-4 h-4" />
          </Button>
          <Button variant="ghost" size="sm">
            <Settings className="w-4 h-4" />
          </Button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex items-center px-6 py-2 border-b border-border">
        <div className="flex">
          {tabs.map((tab) => (
            <Button
              key={tab.id}
              variant={activeTab === tab.id ? 'default' : 'ghost'}
              size="sm"
              className={`rounded-none border-b-2 ${
                activeTab === tab.id 
                  ? 'border-primary bg-transparent text-primary hover:bg-transparent' 
                  : 'border-transparent text-muted-foreground hover:text-foreground'
              }`}
              onClick={() => onTabChange?.(tab.id)}
            >
              {tab.label}
            </Button>
          ))}
        </div>
      </div>

      {/* Filters */}
      <div className="px-6 py-4 space-y-4">
        {/* Filter Dropdowns */}
        <div className="flex items-center gap-3">
          <Select>
            <SelectTrigger className="w-[140px] bg-input-background">
              <SelectValue placeholder="Instruments" />
              <ChevronDown className="w-4 h-4" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Instruments</SelectItem>
              <SelectItem value="drums">Drums</SelectItem>
              <SelectItem value="synth">Synth</SelectItem>
              <SelectItem value="bass">Bass</SelectItem>
              <SelectItem value="keys">Keys</SelectItem>
            </SelectContent>
          </Select>

          <Select>
            <SelectTrigger className="w-[120px] bg-input-background">
              <SelectValue placeholder="Genres" />
              <ChevronDown className="w-4 h-4" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Genres</SelectItem>
              <SelectItem value="house">House</SelectItem>
              <SelectItem value="hip-hop">Hip Hop</SelectItem>
              <SelectItem value="techno">Techno</SelectItem>
              <SelectItem value="pop">Pop</SelectItem>
            </SelectContent>
          </Select>

          <Select>
            <SelectTrigger className="w-[100px] bg-input-background">
              <SelectValue placeholder="Key" />
              <ChevronDown className="w-4 h-4" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Keys</SelectItem>
              <SelectItem value="c">C</SelectItem>
              <SelectItem value="c-sharp">C#</SelectItem>
              <SelectItem value="d">D</SelectItem>
            </SelectContent>
          </Select>

          <Select>
            <SelectTrigger className="w-[100px] bg-input-background">
              <SelectValue placeholder="BPM" />
              <ChevronDown className="w-4 h-4" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All BPM</SelectItem>
              <SelectItem value="slow">60-90</SelectItem>
              <SelectItem value="medium">90-120</SelectItem>
              <SelectItem value="fast">120+</SelectItem>
            </SelectContent>
          </Select>

          <Select>
            <SelectTrigger className="w-[180px] bg-input-background">
              <SelectValue placeholder="One-Shots & Loops" />
              <ChevronDown className="w-4 h-4" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Types</SelectItem>
              <SelectItem value="one-shots">One-Shots</SelectItem>
              <SelectItem value="loops">Loops</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Genre Tags */}
        <div className="flex flex-wrap items-center gap-2">
          {genres.map((genre) => (
            <Badge
              key={genre}
              variant="secondary"
              className="bg-secondary/50 text-secondary-foreground hover:bg-secondary cursor-pointer text-xs px-2 py-1"
            >
              {genre}
            </Badge>
          ))}
          <Button variant="ghost" size="sm" className="text-muted-foreground text-xs">
            <ChevronDown className="w-3 h-3 ml-1" />
          </Button>
        </div>

        {/* Search and Results */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <Input
                placeholder="Search Splice"
                value={searchQuery}
                onChange={(e) => onSearchChange?.(e.target.value)}
                className="pl-10 w-64 bg-input-background"
              />
            </div>
            <p className="text-sm text-muted-foreground">
              {resultCount.toLocaleString()} results
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="sm">
              <Search className="w-4 h-4" />
            </Button>
            <Button variant="ghost" size="sm">
              <Download className="w-4 h-4" />
            </Button>
            <Select>
              <SelectTrigger className="w-[240px] bg-input-background">
                <SelectValue placeholder="Newest" />
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
          </div>
        </div>
      </div>
    </div>
  );
}