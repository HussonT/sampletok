'use client';

import { usePathname } from 'next/navigation';
import { AppSidebar } from '@/components/features/app-sidebar';
import { useEffect, useState, useRef, useCallback } from 'react';
import { ProcessingContext } from '@/contexts/processing-context';

export default function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const [activeSection, setActiveSection] = useState('explore');
  const processingHandlerRef = useRef<((taskId: string, url: string) => void) | null>(null);

  // Update active section based on pathname
  useEffect(() => {
    if (pathname === '/') {
      setActiveSection('explore');
    } else if (pathname?.includes('/my-downloads')) {
      setActiveSection('downloads');
    } else if (pathname?.includes('/my-favorites')) {
      setActiveSection('favorites');
    }
  }, [pathname]);

  const registerProcessingHandler = useCallback((handler: (taskId: string, url: string) => void) => {
    processingHandlerRef.current = handler;
  }, []);

  const unregisterProcessingHandler = useCallback(() => {
    processingHandlerRef.current = null;
  }, []);

  const handleProcessingStarted = useCallback((taskId: string, url: string) => {
    if (processingHandlerRef.current) {
      processingHandlerRef.current(taskId, url);
    }
  }, []);

  return (
    <ProcessingContext.Provider value={{ registerProcessingHandler, unregisterProcessingHandler }}>
      <div className="flex h-screen w-screen overflow-hidden">
        {/* Sidebar - Fixed width */}
        <div className="w-64 flex-shrink-0 border-r border-border bg-sidebar">
          <AppSidebar
            activeSection={activeSection}
            onSectionChange={setActiveSection}
            onProcessingStarted={handleProcessingStarted}
          />
        </div>

        {/* Main Content - Takes remaining space */}
        <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
          {children}
        </div>
      </div>
    </ProcessingContext.Provider>
  );
}
