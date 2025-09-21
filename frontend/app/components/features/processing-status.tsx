'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { ProcessingStatus, ProcessingStatusResponse } from '@/types/api';
import { Loader2, CheckCircle, XCircle } from 'lucide-react';

interface ProcessingStatusProps {
  taskId: string;
  onComplete?: () => void;
}

export function ProcessingStatusCard({ taskId, onComplete }: ProcessingStatusProps) {
  const [status, setStatus] = useState<ProcessingStatusResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  useEffect(() => {
    if (!taskId) return;

    const checkStatus = async () => {
      try {
        const response = await fetch(`/api/process/status/${taskId}`);
        if (!response.ok) throw new Error('Failed to fetch status');

        const data: ProcessingStatusResponse = await response.json();
        setStatus(data);

        // If completed or failed, stop polling and refresh
        if (data.status === ProcessingStatus.COMPLETED || data.status === ProcessingStatus.FAILED) {
          if (data.status === ProcessingStatus.COMPLETED && onComplete) {
            onComplete();
          }
          router.refresh();
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error');
      }
    };

    // Initial check
    checkStatus();

    // Poll every 2 seconds if still processing
    const interval = setInterval(() => {
      if (status?.status === ProcessingStatus.PROCESSING || status?.status === ProcessingStatus.PENDING) {
        checkStatus();
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [taskId, status?.status, router, onComplete]);

  if (error) {
    return (
      <Card className="border-red-200">
        <CardContent className="pt-6">
          <div className="flex items-center gap-2 text-red-600">
            <XCircle className="h-4 w-4" />
            <span className="text-sm">{error}</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!status) {
    return (
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center gap-2">
            <Loader2 className="h-4 w-4 animate-spin" />
            <span className="text-sm">Loading status...</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  const getStatusIcon = () => {
    switch (status.status) {
      case ProcessingStatus.COMPLETED:
        return <CheckCircle className="h-4 w-4 text-green-600" />;
      case ProcessingStatus.FAILED:
        return <XCircle className="h-4 w-4 text-red-600" />;
      default:
        return <Loader2 className="h-4 w-4 animate-spin" />;
    }
  };

  const getStatusColor = () => {
    switch (status.status) {
      case ProcessingStatus.COMPLETED:
        return 'bg-green-100 text-green-800';
      case ProcessingStatus.FAILED:
        return 'bg-red-100 text-red-800';
      case ProcessingStatus.PROCESSING:
        return 'bg-blue-100 text-blue-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-medium">Processing Status</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              {getStatusIcon()}
              <span className="text-sm font-medium">
                {status.message || status.status}
              </span>
            </div>
            <Badge className={getStatusColor()}>
              {status.status}
            </Badge>
          </div>

          {status.progress !== undefined && status.status === ProcessingStatus.PROCESSING && (
            <Progress value={status.progress} className="h-2" />
          )}

          {status.error && (
            <div className="text-sm text-red-600">
              Error: {status.error}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}