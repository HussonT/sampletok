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
import { processTikTokUrl } from '@/actions/samples';
import { toast } from 'sonner';
import { Loader2, Plus, Link2 } from 'lucide-react';
import { useRouter } from 'next/navigation';

export function AddSampleDialog() {
  const [open, setOpen] = useState(false);
  const [url, setUrl] = useState('');
  const [isPending, startTransition] = useTransition();
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!url.trim()) {
      toast.error('Please enter a TikTok URL');
      return;
    }

    startTransition(async () => {
      const result = await processTikTokUrl(url);

      if (result.success) {
        toast.success('Processing started!', {
          description: 'Your TikTok video is being processed. It will appear in your library soon.',
        });
        setUrl('');
        setOpen(false);
        // The page will automatically refresh due to revalidatePath in the server action
        router.refresh();
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
        <Button>
          <Plus className="mr-2 h-4 w-4" />
          Add Sample
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[525px]">
        <form onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle>Add TikTok Sample</DialogTitle>
            <DialogDescription>
              Enter a TikTok URL to extract and add the audio sample to your library.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="url" className="text-right">
                TikTok URL
              </Label>
              <Input
                id="url"
                type="url"
                placeholder="https://www.tiktok.com/@user/video/..."
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                disabled={isPending}
                className="col-span-3"
              />
            </div>
            <div className="col-span-4 text-sm text-muted-foreground ml-[108px]">
              Paste any TikTok video URL to extract its audio
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