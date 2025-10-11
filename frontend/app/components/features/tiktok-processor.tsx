'use client';

import { useState, useTransition } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { processTikTokUrl } from '@/actions/samples';
import { toast } from 'sonner';
import { Loader2, Link2 } from 'lucide-react';

export function TikTokProcessor() {
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
          description: 'Your TikTok video is being processed. This may take a few moments.',
        });
        setUrl('');
        // The page will automatically refresh due to revalidatePath in the server action
      } else {
        toast.error('Failed to process URL', {
          description: result.error,
        });
      }
    });
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Process TikTok Video</CardTitle>
        <CardDescription>
          Enter a TikTok URL to extract and download the audio sample
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="flex gap-2">
          <Input
            type="url"
            placeholder="https://www.tiktok.com/@user/video/..."
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            disabled={isPending}
            className="flex-1"
          />
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
        </form>
      </CardContent>
    </Card>
  );
}