'use client';

import React from 'react';
import { Loader2, CheckCircle2, X } from 'lucide-react';
import { ProcessingStatus } from '@/types/api';

export interface ProcessingTask {
  taskId: string;
  url: string;
  status: ProcessingStatus;
  message?: string;
  progress?: number;
}

interface ProcessingQueueProps {
  tasks: ProcessingTask[];
  onRemoveTask?: (taskId: string) => void;
}

export function ProcessingQueue({ tasks, onRemoveTask }: ProcessingQueueProps) {
  if (tasks.length === 0) return null;

  const getStatusText = (task: ProcessingTask) => {
    if (task.message) return task.message;
    switch (task.status) {
      case ProcessingStatus.PENDING:
        return 'Queued for processing';
      case ProcessingStatus.PROCESSING:
        return 'Processing TikTok audio';
      case ProcessingStatus.COMPLETED:
        return 'Successfully added to library';
      case ProcessingStatus.FAILED:
        return 'Failed to process';
      default:
        return 'Processing';
    }
  };

  return (
    <div className="border-b border-border bg-background">
      <div className="px-6 py-3">
        <div className="space-y-2">
          {tasks.map((task) => (
            <div
              key={task.taskId}
              className="flex items-start gap-3 py-2"
            >
              <div className="flex-shrink-0 mt-0.5">
                {task.status === ProcessingStatus.COMPLETED ? (
                  <CheckCircle2 className="w-4 h-4 text-green-500" />
                ) : (
                  <Loader2 className="w-4 h-4 text-primary animate-spin" />
                )}
              </div>

              <div className="flex-1 min-w-0">
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-foreground">
                      {getStatusText(task)}
                    </p>
                    <p className="text-xs text-muted-foreground truncate mt-0.5">
                      {new URL(task.url).pathname.split('/').pop() || task.url}
                    </p>
                  </div>

                  {onRemoveTask && task.status === ProcessingStatus.COMPLETED && (
                    <button
                      onClick={() => onRemoveTask(task.taskId)}
                      className="text-muted-foreground hover:text-foreground transition-colors"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  )}
                </div>

                {task.progress !== undefined && task.status === ProcessingStatus.PROCESSING && (
                  <div className="w-full bg-secondary rounded-full h-1 mt-2">
                    <div
                      className="bg-primary h-1 rounded-full transition-all duration-500"
                      style={{ width: `${task.progress}%` }}
                    />
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}