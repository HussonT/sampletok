'use client';

import { useState } from 'react';
import { Home, Heart, Search, User, Plus } from 'lucide-react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { AddSampleModal } from './add-sample-modal';

export function MobileBottomNav() {
  const pathname = usePathname();
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);

  const tabs = [
    { href: '/mobile', icon: Home, label: 'Feed' },
    { href: '/mobile/favorites', icon: Heart, label: 'Favorites' },
  ];

  const rightTabs = [
    { href: '/mobile/search', icon: Search, label: 'Search' },
    { href: '/mobile/profile', icon: User, label: 'Profile' },
  ];

  return (
    <>
      <nav className="fixed bottom-0 left-0 right-0 bg-[hsl(0,0%,17%)] border-t border-white/10 z-50 safe-area-inset-bottom">
        <div className="flex justify-around items-center h-16 relative">
          {/* Left tabs */}
          {tabs.map(({ href, icon: Icon, label }) => {
            const isActive = pathname === href;
            return (
              <Link
                key={href}
                href={href}
                className={`flex flex-col items-center justify-center w-full h-full transition-colors ${
                  isActive ? 'text-[hsl(338,82%,65%)]' : 'text-gray-400 hover:text-gray-300'
                }`}
              >
                <Icon className="w-6 h-6" />
                <span className="text-xs mt-1">{label}</span>
              </Link>
            );
          })}

          {/* Center + button */}
          <div className="w-full flex items-center justify-center">
            <button
              onClick={() => setIsAddModalOpen(true)}
              className="absolute -top-5 w-14 h-14 rounded-full bg-gradient-to-br from-[hsl(338,82%,65%)] to-[hsl(338,82%,55%)] hover:from-[hsl(338,82%,70%)] hover:to-[hsl(338,82%,60%)] shadow-lg shadow-[hsl(338,82%,65%)]/25 flex items-center justify-center transition-all active:scale-95 border-4 border-[hsl(0,0%,17%)]"
            >
              <Plus className="w-7 h-7 text-white" strokeWidth={3} />
            </button>
          </div>

          {/* Right tabs */}
          {rightTabs.map(({ href, icon: Icon, label }) => {
            const isActive = pathname === href;
            return (
              <Link
                key={href}
                href={href}
                className={`flex flex-col items-center justify-center w-full h-full transition-colors ${
                  isActive ? 'text-[hsl(338,82%,65%)]' : 'text-gray-400 hover:text-gray-300'
                }`}
              >
                <Icon className="w-6 h-6" />
                <span className="text-xs mt-1">{label}</span>
              </Link>
            );
          })}
        </div>
      </nav>

      {/* Add Sample Modal */}
      <AddSampleModal isOpen={isAddModalOpen} onClose={() => setIsAddModalOpen(false)} />
    </>
  );
}
