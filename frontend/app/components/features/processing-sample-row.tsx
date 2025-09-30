import React from 'react';
import { Loader2, XCircle } from 'lucide-react';
import { ProcessingStatus } from '@/types/api';

interface ProcessingSampleRowProps {
  taskId: string;
  url: string;
  status: ProcessingStatus;
  message?: string;
  progress?: number;
}

export function ProcessingSampleRow({
  taskId,
  url,
  status,
  message,
  progress
}: ProcessingSampleRowProps) {
  const getStatusText = () => {
    if (message) return message;
    switch (status) {
      case ProcessingStatus.PENDING:
        return 'Queued for processing...';
      case ProcessingStatus.PROCESSING:
        return 'Processing video...';
      case ProcessingStatus.FAILED:
        return 'Processing failed';
      default:
        return 'Processing...';
    }
  };

  const isFailed = status === ProcessingStatus.FAILED;

  return (
    <tr
      className={`border-b border-border ${isFailed ? 'bg-red-50/50' : 'bg-blue-50/50'} animate-pulse`}
      key={taskId}
    >
      <td className="py-3 px-4">
        <div className="w-8 h-8 flex items-center justify-center">
          {isFailed ? (
            <XCircle className="w-4 h-4 text-red-600" />
          ) : (
            <Loader2 className="w-4 h-4 animate-spin text-blue-600" />
          )}
        </div>
      </td>
      <td className="py-3 px-4" colSpan={2}>
        <div className="space-y-1">
          <div className="text-sm font-medium text-foreground">
            {getStatusText()}
          </div>
          <div className="text-xs text-muted-foreground truncate max-w-md">
            {url}
          </div>
          {progress !== undefined && !isFailed && (
            <div className="w-full bg-gray-200 rounded-full h-1.5 mt-2">
              <div
                className="bg-blue-600 h-1.5 rounded-full transition-all duration-300"
                style={{ width: `${progress}%` }}
              />
            </div>
          )}
        </div>
      </td>
      <td className="py-3 px-4 text-center text-muted-foreground" colSpan={6}>
        <span className="text-xs italic">
          {isFailed ? 'Failed to process' : 'Processing in progress...'}
        </span>
      </td>
    </tr>
  );
}