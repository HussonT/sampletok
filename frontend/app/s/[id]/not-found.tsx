import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { AlertCircle } from 'lucide-react';

export default function NotFound() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-background to-background/95 flex items-center justify-center p-4">
      <Card className="max-w-md w-full p-8 text-center">
        <div className="mb-6 flex justify-center">
          <div className="h-16 w-16 rounded-full bg-destructive/10 flex items-center justify-center">
            <AlertCircle className="h-8 w-8 text-destructive" />
          </div>
        </div>

        <h1 className="text-2xl font-bold mb-2">Sample Not Found</h1>
        <p className="text-muted-foreground mb-6">
          This sample could not be found or is still being processed. It may have been removed or the link might be incorrect.
        </p>

        <div className="space-y-3">
          <Button asChild className="w-full">
            <Link href="/">Browse Samples</Link>
          </Button>
          <p className="text-sm text-muted-foreground">
            Transform your content into samples by tagging @sampletheinternet on TikTok or Instagram
          </p>
        </div>
      </Card>
    </div>
  );
}
