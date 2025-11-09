'use client';

import { MobileBottomNav } from '@/components/mobile/mobile-bottom-nav';
import { QueryProvider } from '@/providers/query-provider';

export default function MobileLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <QueryProvider>
      <div className="min-h-screen bg-black text-white">
        {/* Full-screen mobile content */}
        <main className="pb-20">{children}</main>

        {/* Fixed bottom navigation */}
        <MobileBottomNav />
      </div>
    </QueryProvider>
  );
}
