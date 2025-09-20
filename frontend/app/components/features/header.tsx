import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { 
  Search, 
  Plus, 
  Filter, 
  User, 
  Library, 
  Download, 
  Settings, 
  LogOut, 
  ExternalLink 
} from 'lucide-react';

interface HeaderProps {
  onAddTikTok: (url: string) => void;
  onToggleFilters: () => void;
  isFiltersOpen: boolean;
  totalSamples: number;
}

export function Header({ onAddTikTok, onToggleFilters, isFiltersOpen, totalSamples }: HeaderProps) {
  const [tiktokUrl, setTiktokUrl] = useState('');
  const [isAddDialogOpen, setIsAddDialogOpen] = useState(false);
  const [downloadFormat, setDownloadFormat] = useState('wav');
  
  const handleAddSample = () => {
    if (tiktokUrl.trim()) {
      onAddTikTok(tiktokUrl.trim());
      setTiktokUrl('');
      setIsAddDialogOpen(false);
    }
  };

  const isValidTikTokUrl = (url: string) => {
    return url.includes('tiktok.com') || url.includes('vm.tiktok.com');
  };

  return (
    <header className="sticky top-0 z-40 w-full border-b border-border bg-card/95 backdrop-blur supports-[backdrop-filter]:bg-card/80">
      <div className="flex h-16 items-center justify-between px-6">
        {/* Logo & Brand */}
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-br from-primary to-primary/80 rounded-xl flex items-center justify-center shadow-lg">
              <svg viewBox="0 0 24 24" className="w-6 h-6 text-white" fill="currentColor">
                <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
              </svg>
            </div>
            <div>
              <h1 className="text-xl font-bold text-white">Sampletok</h1>
              <p className="text-xs text-primary font-medium">Make music at the speed of culture!</p>
            </div>
          </div>
          <Badge variant="secondary" className="hidden sm:flex bg-primary/20 text-primary border-primary/30">
            {totalSamples} samples
          </Badge>
        </div>

        {/* Main Actions */}
        <div className="flex items-center gap-2">
          {/* Add Sample Dialog */}
          <Dialog open={isAddDialogOpen} onOpenChange={setIsAddDialogOpen}>
            <DialogTrigger asChild>
              <Button variant="default" size="sm" className="bg-primary hover:bg-primary/90 text-white font-medium shadow-lg">
                <Plus className="w-4 h-4 mr-1" />
                Add Sample
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Add TikTok Sample</DialogTitle>
              </DialogHeader>
              <div className="space-y-4 pt-4">
                <div className="space-y-2">
                  <Label>TikTok URL</Label>
                  <Input
                    placeholder="Paste TikTok video URL here..."
                    value={tiktokUrl}
                    onChange={(e) => setTiktokUrl(e.target.value)}
                    className={
                      tiktokUrl && !isValidTikTokUrl(tiktokUrl) 
                        ? 'border-destructive' 
                        : ''
                    }
                  />
                  {tiktokUrl && !isValidTikTokUrl(tiktokUrl) && (
                    <p className="text-xs text-destructive">
                      Please enter a valid TikTok URL
                    </p>
                  )}
                </div>

                <div className="space-y-2">
                  <Label>Download Format</Label>
                  <Select value={downloadFormat} onValueChange={setDownloadFormat}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="wav">WAV (24-bit, 48kHz)</SelectItem>
                      <SelectItem value="mp3">MP3 (320kbps)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="flex justify-end gap-2 pt-4">
                  <Button 
                    variant="outline" 
                    onClick={() => setIsAddDialogOpen(false)}
                  >
                    Cancel
                  </Button>
                  <Button 
                    onClick={handleAddSample}
                    disabled={!tiktokUrl || !isValidTikTokUrl(tiktokUrl)}
                  >
                    Add Sample
                  </Button>
                </div>
              </div>
            </DialogContent>
          </Dialog>

          {/* Filter Toggle */}
          <Button 
            variant="outline" 
            size="sm"
            onClick={onToggleFilters}
            className={isFiltersOpen ? 'bg-accent' : ''}
          >
            <Filter className="w-4 h-4" />
          </Button>

          {/* User Menu */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" className="relative h-9 w-9 rounded-full">
                <Avatar className="h-9 w-9">
                  <AvatarImage src="/placeholder-avatar.jpg" alt="User" />
                  <AvatarFallback>
                    <User className="w-4 h-4" />
                  </AvatarFallback>
                </Avatar>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent className="w-56" align="end" forceMount>
              <div className="flex items-center justify-start gap-2 p-2">
                <div className="flex flex-col space-y-1 leading-none">
                  <p className="font-medium">Producer Alex</p>
                  <p className="w-[200px] truncate text-sm text-muted-foreground">
                    alex@example.com
                  </p>
                </div>
              </div>
              <DropdownMenuSeparator />
              <DropdownMenuItem>
                <Library className="mr-2 h-4 w-4" />
                <span>My Library</span>
              </DropdownMenuItem>
              <DropdownMenuItem>
                <Download className="mr-2 h-4 w-4" />
                <span>Downloads</span>
              </DropdownMenuItem>
              <DropdownMenuItem>
                <Settings className="mr-2 h-4 w-4" />
                <span>Settings</span>
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem>
                <ExternalLink className="mr-2 h-4 w-4" />
                <span>Feedback</span>
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem>
                <LogOut className="mr-2 h-4 w-4" />
                <span>Log out</span>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>
    </header>
  );
}