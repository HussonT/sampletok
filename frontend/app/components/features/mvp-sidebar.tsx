import React from 'react';
import { Button } from '@/components/ui/button';
import { 
  Music, 
  Download,
  Home
} from 'lucide-react';

interface MVPSidebarProps {
  activeSection?: string;
  onSectionChange?: (section: string) => void;
}

export function MVPSidebar({ activeSection = 'browse', onSectionChange }: MVPSidebarProps) {
  const navigationItems = [
    { id: 'browse', label: 'Browse Samples', icon: Home },
    { id: 'library', label: 'My Downloads', icon: Download },
  ];

  return (
    <div className="w-64 h-full bg-sidebar border-r border-sidebar-border flex flex-col">
      {/* Logo/Brand */}
      <div className="p-6 border-b border-sidebar-border">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center">
            <Music className="w-5 h-5 text-white" />
          </div>
          <h2 className="font-bold text-sidebar-foreground">Sampletok</h2>
        </div>
      </div>

      {/* Navigation */}
      <div className="flex-1 p-4">
        <div className="space-y-2">
          {navigationItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeSection === item.id;
            
            return (
              <Button
                key={item.id}
                variant={isActive ? 'secondary' : 'ghost'}
                className={`w-full justify-start h-10 px-3 ${
                  isActive 
                    ? 'bg-sidebar-accent text-sidebar-accent-foreground' 
                    : 'text-sidebar-foreground/80 hover:text-sidebar-foreground hover:bg-sidebar-accent/50'
                }`}
                onClick={() => onSectionChange?.(item.id)}
              >
                <Icon className="w-4 h-4 mr-3" />
                <span>{item.label}</span>
              </Button>
            );
          })}
        </div>
      </div>

      {/* Footer */}
      <div className="p-4 border-t border-sidebar-border">
        <p className="text-xs text-sidebar-foreground/60 text-center">
          Convert TikTok videos to samples
        </p>
      </div>
    </div>
  );
}