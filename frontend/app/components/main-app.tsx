'use client';

import React, { useState, useMemo } from 'react';
import { SimpleSidebar } from '@/components/features/simple-sidebar';
import { SearchFilters } from '@/components/features/search-filters';
import { SoundsTable } from '@/components/features/sounds-table';
import { BottomPlayer } from '@/components/features/bottom-player';
import { Download, Music } from 'lucide-react';
import { Sample } from '@/data/mock-samples';
import { toast } from 'sonner';
import { Toaster } from '@/components/ui/sonner';

interface MainAppProps {
  initialSamples: Sample[];
}

export default function MainApp({ initialSamples }: MainAppProps) {
  const [samples] = useState<Sample[]>(initialSamples);
  const [currentSample, setCurrentSample] = useState<Sample | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [activeSection, setActiveSection] = useState('browse');
  const [selectedGenre, setSelectedGenre] = useState('all');
  const [selectedBPM, setSelectedBPM] = useState('all');
  const [selectedVideoType, setSelectedVideoType] = useState('all');
  const [sortBy, setSortBy] = useState('recent');
  const [downloadedSamples, setDownloadedSamples] = useState<Set<string>>(new Set());
  const [credits, setCredits] = useState(10);

  const filteredSamples = useMemo(() => {
    let filtered = [...samples];

    if (searchQuery) {
      filtered = filtered.filter(sample =>
        sample.creatorUsername.toLowerCase().includes(searchQuery.toLowerCase()) ||
        sample.description.toLowerCase().includes(searchQuery.toLowerCase())
      );
    }

    if (selectedGenre !== 'all') {
      filtered = filtered.filter(sample => {
        const genres = ['house', 'hip hop', 'drill', 'pop', 'rnb', 'techno', 'trap'];
        const sampleGenre = genres[sample.id.charCodeAt(0) % genres.length];
        return sampleGenre === selectedGenre;
      });
    }

    if (selectedBPM !== 'all') {
      filtered = filtered.filter(sample => {
        const bpm = 120 + (sample.id.charCodeAt(0) % 60);
        switch (selectedBPM) {
          case 'slow': return bpm >= 60 && bpm < 90;
          case 'medium': return bpm >= 90 && bpm < 120;
          case 'fast': return bpm >= 120 && bpm < 150;
          case 'very-fast': return bpm >= 150;
          default: return true;
        }
      });
    }

    if (selectedVideoType !== 'all') {
      filtered = filtered.filter(sample => {
        const videoTypes = ['viral', 'inspirational', 'funny', 'dance', 'trending', 'motivational', 'lifestyle', 'educational'];
        const sampleVideoType = videoTypes[sample.creatorUsername.charCodeAt(0) % videoTypes.length];
        return sampleVideoType === selectedVideoType;
      });
    }

    switch (sortBy) {
      case 'popular':
        filtered.sort((a, b) => b.id.length - a.id.length);
        break;
      case 'name':
        filtered.sort((a, b) => a.creatorUsername.localeCompare(b.creatorUsername));
        break;
      case 'recent':
      default:
        filtered.sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime());
        break;
    }

    return filtered;
  }, [samples, searchQuery, selectedGenre, selectedBPM, selectedVideoType, sortBy]);

  const handleSamplePreview = (sample: Sample) => {
    if (currentSample?.id === sample.id) {
      setIsPlaying(!isPlaying);
    } else {
      setCurrentSample(sample);
      setIsPlaying(true);
    }
  };

  const handleSampleDownload = (sample: Sample) => {
    if (downloadedSamples.has(sample.id)) {
      toast.success('Download started!', {
        description: `Downloading ${sample.creatorUsername} sample as WAV`,
      });
    } else {
      if (credits <= 0) {
        toast.error('No credits remaining', {
          description: 'Purchase more credits to download samples',
        });
        return;
      }

      setCredits(prev => prev - 1);
      setDownloadedSamples(prev => new Set([...prev, sample.id]));

      toast.success('Sample purchased!', {
        description: `Used 1 credit. ${credits - 1} credits remaining`,
      });
    }
  };


  const handleSectionChange = (section: string) => {
    setActiveSection(section);
  };

  const handlePlayerPlayPause = () => {
    setIsPlaying(!isPlaying);
  };

  const handlePlayerNext = () => {
    if (!currentSample) return;
    const currentIndex = filteredSamples.findIndex(s => s.id === currentSample.id);
    const nextIndex = (currentIndex + 1) % filteredSamples.length;
    const nextSample = filteredSamples[nextIndex];
    setCurrentSample(nextSample);
    setIsPlaying(true);
  };

  const handlePlayerPrevious = () => {
    if (!currentSample) return;
    const currentIndex = filteredSamples.findIndex(s => s.id === currentSample.id);
    const prevIndex = currentIndex === 0 ? filteredSamples.length - 1 : currentIndex - 1;
    const prevSample = filteredSamples[prevIndex];
    setCurrentSample(prevSample);
    setIsPlaying(true);
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Sidebar */}
      <SimpleSidebar
        activeSection={activeSection}
        onSectionChange={handleSectionChange}
      />

      {/* Main Content */}
      <div className="ml-64 flex flex-col min-h-screen">
        {/* Header */}
        <div className="border-b border-border px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              {activeSection === 'browse' ? (
                <Music className="w-5 h-5" />
              ) : (
                <Download className="w-5 h-5" />
              )}
              <h1 className="text-xl font-semibold">
                {activeSection === 'browse' ? 'Browse Samples' : 'My Downloads'}
              </h1>
            </div>
            <div className="text-sm text-muted-foreground">
              {credits} credits
            </div>
          </div>
        </div>

        {/* Filters */}
        {activeSection === 'browse' && (
          <SearchFilters
            searchQuery={searchQuery}
            onSearchChange={setSearchQuery}
            selectedGenre={selectedGenre}
            onGenreChange={setSelectedGenre}
            selectedBPM={selectedBPM}
            onBPMChange={setSelectedBPM}
            selectedVideoType={selectedVideoType}
            onVideoTypeChange={setSelectedVideoType}
            sortBy={sortBy}
            onSortChange={setSortBy}
            resultCount={filteredSamples.length}
          />
        )}

        {/* Content */}
        <div className="flex-1 overflow-auto" style={{ paddingBottom: currentSample ? '100px' : '0' }}>
          {activeSection === 'browse' && (
            <SoundsTable
              samples={filteredSamples}
              currentSample={currentSample}
              isPlaying={isPlaying}
              downloadedSamples={downloadedSamples}
              onSamplePreview={handleSamplePreview}
              onSampleDownload={handleSampleDownload}
            />
          )}

          {activeSection === 'library' && (
            downloadedSamples.size === 0 ? (
              <div className="flex items-center justify-center h-96">
                <div className="text-center">
                  <Download className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
                  <h3 className="text-lg font-medium mb-2">No Downloads Yet</h3>
                  <p className="text-muted-foreground">
                    Your downloaded samples will appear here
                  </p>
                </div>
              </div>
            ) : (
              <SoundsTable
                samples={samples.filter(sample => downloadedSamples.has(sample.id))}
                currentSample={currentSample}
                isPlaying={isPlaying}
                downloadedSamples={downloadedSamples}
                onSamplePreview={handleSamplePreview}
                onSampleDownload={handleSampleDownload}
              />
            )
          )}
        </div>
      </div>

      {/* Bottom Player */}
      <BottomPlayer
        sample={currentSample}
        isPlaying={isPlaying}
        onPlayPause={handlePlayerPlayPause}
        onNext={handlePlayerNext}
        onPrevious={handlePlayerPrevious}
        onDownload={handleSampleDownload}
      />

      <Toaster />
    </div>
  );
}