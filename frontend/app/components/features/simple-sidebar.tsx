'use client';

import React from 'react';
import { Music, Download } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface SimpleSidebarProps {
  activeSection: string;
  onSectionChange: (section: string) => void;
}

export function SimpleSidebar({ activeSection, onSectionChange }: SimpleSidebarProps) {
  return (
    <div className="w-64 bg-card border-r border-border h-screen flex flex-col fixed left-0 top-0">
      <div className="p-4 border-b border-border">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-primary rounded flex items-center justify-center">
            <span className="text-xs font-bold text-white">S</span>
          </div>
          <span className="font-semibold text-foreground">Sampletok</span>
        </div>
      </div>

      <nav className="flex-1 p-4">
        <div className="space-y-1">
          <Button
            variant={activeSection === 'browse' ? 'secondary' : 'ghost'}
            className="w-full justify-start"
            onClick={() => onSectionChange('browse')}
          >
            <Music className="mr-2 h-4 w-4" />
            Browse Samples
          </Button>

          <Button
            variant={activeSection === 'library' ? 'secondary' : 'ghost'}
            className="w-full justify-start"
            onClick={() => onSectionChange('library')}
          >
            <Download className="mr-2 h-4 w-4" />
            My Downloads
          </Button>
        </div>
      </nav>

      <div className="p-4 border-t border-border">
        <p className="text-xs text-muted-foreground">
          make music at the speed of culture
        </p>
      </div>
    </div>
  );
}