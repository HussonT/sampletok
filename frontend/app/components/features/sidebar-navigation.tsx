import React from 'react';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { 
  Music, 
  Puzzle, 
  Layers, 
  Heart, 
  Calendar,
  Folder,
  Headphones
} from 'lucide-react';

interface SidebarNavigationProps {
  activeSection?: string;
  onSectionChange?: (section: string) => void;
}

export function SidebarNavigation({ activeSection = 'sounds', onSectionChange }: SidebarNavigationProps) {
  const navigationSections = [
    {
      id: 'browse',
      label: 'Browse',
      items: [
        { id: 'sounds', label: 'Sounds', icon: Music, active: true },
        { id: 'apps-plugins', label: 'Apps & Plugins', icon: Puzzle },
        { id: 'stacks', label: 'Stacks', icon: Layers }
      ]
    },
    {
      id: 'create',
      label: 'Create',
      items: []
    },
    {
      id: 'library',
      label: 'Library',
      items: [
        { id: 'sounds-library', label: 'Sounds', icon: Music },
        { id: 'likes', label: 'Likes', icon: Heart },
        { id: 'daily-picks', label: 'Daily Picks', icon: Calendar }
      ]
    },
    {
      id: 'collections',
      label: 'Collections',
      items: [
        { id: 'all-collections', label: 'All Collections', icon: Folder },
        { id: 'paradise-tropicale', label: 'paradise tropicale', icon: Headphones }
      ]
    }
  ];

  return (
    <div className="w-64 h-full bg-sidebar border-r border-sidebar-border flex flex-col">
      {/* Sidebar Content */}
      <div className="flex-1 p-4 space-y-6">
        {navigationSections.map((section) => (
          <div key={section.id} className="space-y-2">
            <h3 className="text-sm font-medium text-sidebar-foreground/70 uppercase tracking-wider">
              {section.label}
            </h3>
            {section.items.length > 0 && (
              <div className="space-y-1">
                {section.items.map((item) => {
                  const Icon = item.icon;
                  const isActive = activeSection === item.id || (item.id === 'sounds' && activeSection === 'sounds');
                  
                  return (
                    <Button
                      key={item.id}
                      variant={isActive ? 'secondary' : 'ghost'}
                      className={`w-full justify-start h-9 px-3 ${
                        isActive 
                          ? 'bg-sidebar-accent text-sidebar-accent-foreground' 
                          : 'text-sidebar-foreground/80 hover:text-sidebar-foreground hover:bg-sidebar-accent/50'
                      }`}
                      onClick={() => onSectionChange?.(item.id)}
                    >
                      <Icon className="w-4 h-4 mr-3" />
                      <span className="text-sm">{item.label}</span>
                    </Button>
                  );
                })}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}