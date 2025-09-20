import React from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Separator } from '@/components/ui/separator';
import { Card } from '@/components/ui/card';
import { X, Search, Filter } from 'lucide-react';

interface FilterPanelProps {
  isOpen: boolean;
  onClose: () => void;
  filters: {
    search: string;
    sortBy: string;
    dateRange: string;
    viewCountRange: string;
    durationRange: string;
  };
  onFilterChange: (key: string, value: string) => void;
  onClearFilters: () => void;
}

export function FilterPanel({ 
  isOpen, 
  onClose, 
  filters, 
  onFilterChange, 
  onClearFilters 
}: FilterPanelProps) {
  if (!isOpen) return null;

  return (
    <>
      {/* Mobile Overlay */}
      <div 
        className="fixed inset-0 bg-black/50 z-40 lg:hidden"
        onClick={onClose}
      />
      
      {/* Filter Panel */}
      <Card className="fixed left-0 top-0 h-full w-80 z-50 lg:relative lg:w-64 bg-card border-r border-border">
        <div className="p-4 space-y-6">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Filter className="w-4 h-4 text-primary" />
              <h3 className="font-semibold text-foreground">Filters</h3>
            </div>
            <div className="flex items-center gap-1">
              <Button 
                variant="ghost" 
                size="sm"
                onClick={onClearFilters}
                className="text-xs"
              >
                Clear
              </Button>
              <Button 
                variant="ghost" 
                size="sm"
                onClick={onClose}
                className="lg:hidden"
              >
                <X className="w-4 h-4" />
              </Button>
            </div>
          </div>

          <Separator />

          {/* Search */}
          <div className="space-y-2">
            <Label>Search Creator</Label>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <Input
                placeholder="Search by username..."
                value={filters.search}
                onChange={(e) => onFilterChange('search', e.target.value)}
                className="pl-10"
              />
            </div>
          </div>

          {/* Sort By */}
          <div className="space-y-2">
            <Label>Sort By</Label>
            <Select 
              value={filters.sortBy} 
              onValueChange={(value) => onFilterChange('sortBy', value)}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="newest">Newest First</SelectItem>
                <SelectItem value="oldest">Oldest First</SelectItem>
                <SelectItem value="most-viewed">Most Viewed</SelectItem>
                <SelectItem value="least-viewed">Least Viewed</SelectItem>
                <SelectItem value="creator-name">Creator Name</SelectItem>
                <SelectItem value="duration-short">Shortest First</SelectItem>
                <SelectItem value="duration-long">Longest First</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Date Range */}
          <div className="space-y-2">
            <Label>Date Added</Label>
            <Select 
              value={filters.dateRange} 
              onValueChange={(value) => onFilterChange('dateRange', value)}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Time</SelectItem>
                <SelectItem value="today">Today</SelectItem>
                <SelectItem value="week">This Week</SelectItem>
                <SelectItem value="month">This Month</SelectItem>
                <SelectItem value="3-months">Last 3 Months</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* View Count Range */}
          <div className="space-y-2">
            <Label>View Count</Label>
            <Select 
              value={filters.viewCountRange} 
              onValueChange={(value) => onFilterChange('viewCountRange', value)}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Any Views</SelectItem>
                <SelectItem value="under-1k">Under 1K</SelectItem>
                <SelectItem value="1k-10k">1K - 10K</SelectItem>
                <SelectItem value="10k-100k">10K - 100K</SelectItem>
                <SelectItem value="100k-1m">100K - 1M</SelectItem>
                <SelectItem value="over-1m">Over 1M</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Duration Range */}
          <div className="space-y-2">
            <Label>Duration</Label>
            <Select 
              value={filters.durationRange} 
              onValueChange={(value) => onFilterChange('durationRange', value)}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Any Length</SelectItem>
                <SelectItem value="under-10s">Under 10s</SelectItem>
                <SelectItem value="10s-30s">10s - 30s</SelectItem>
                <SelectItem value="30s-60s">30s - 1min</SelectItem>
                <SelectItem value="over-60s">Over 1min</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
      </Card>
    </>
  );
}