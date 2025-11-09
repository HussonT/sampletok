'use client';

import { Home, Heart, Search, User } from 'lucide-react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

export function MobileBottomNav() {
  const pathname = usePathname();

  const tabs = [
    { href: '/mobile', icon: Home, label: 'Feed' },
    { href: '/mobile/favorites', icon: Heart, label: 'Favorites' },
    { href: '/mobile/search', icon: Search, label: 'Search' },
    { href: '/mobile/profile', icon: User, label: 'Profile' },
  ];

  return (
    <nav className="fixed bottom-0 left-0 right-0 bg-[hsl(0,0%,17%)] border-t border-white/10 z-50 safe-area-inset-bottom">
      <div className="flex justify-around items-center h-16">
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
      </div>
    </nav>
  );
}
