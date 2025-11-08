'use client';

import { useState, useTransition } from 'react';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { processInstagramUrl } from '@/actions/samples';
import { toast } from 'sonner';
import { Loader2, Plus, Link2, Instagram } from 'lucide-react';

interface AddInstagramDialogProps {
  onProcessingStarted?: (taskId: string, url: string) => void;
  variant?: 'default' | 'sidebar';
}

export function AddInstagramDialog({ onProcessingStarted, variant = 'default' }: AddInstagramDialogProps) {
  const [open, setOpen] = useState(false);
  const [url, setUrl] = useState('');
  const [isPending, startTransition] = useTransition();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!url.trim()) {
      toast.error('Please enter an Instagram URL');
      return;
    }

    startTransition(async () => {
      const result = await processInstagramUrl(url);

      if (result.success && result.data) {
        // Immediately add to processing tasks for optimistic UI
        if (onProcessingStarted && result.data.task_id) {
          onProcessingStarted(result.data.task_id, url);
        }

        toast.success('Processing started!', {
          description: 'Watch the progress in real-time below.',
        });
        setUrl('');
        setOpen(false);
      } else {
        toast.error('Failed to process URL', {
          description: result.error,
        });
      }
    });
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        {variant === 'sidebar' ? (
          <button className="w-full flex items-center gap-2 px-3 py-2 rounded-md text-sm transition-colors text-sidebar-foreground hover:bg-sidebar-accent/50">
            <Instagram className="w-4 h-4" />
            <span>sample a gram</span>
          </button>
        ) : (
          <Button>
            <Instagram className="mr-2 h-4 w-4" />
            sample a gram
          </Button>
        )}
      </DialogTrigger>
      <DialogContent className="sm:max-w-[525px]">
        <form onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle>Add Instagram Sample</DialogTitle>
            <DialogDescription>
              Enter an Instagram URL to extract and add the audio sample to your library.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="url" className="text-right">
                Instagram URL
              </Label>
              <Input
                id="url"
                type="url"
                placeholder="https://www.instagram.com/reel/..."
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                disabled={isPending}
                className="col-span-3"
              />
            </div>
            <div className="col-span-4 text-sm text-muted-foreground ml-[108px]">
              Paste any Instagram reel or post URL to extract its audio
            </div>
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setOpen(false)} disabled={isPending}>
              Cancel
            </Button>
            <Button type="submit" disabled={isPending}>
              {isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Processing...
                </>
              ) : (
                <>
                  <Link2 className="mr-2 h-4 w-4" />
                  Process URL
                </>
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
