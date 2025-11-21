'use client';

import React from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { usePathname } from 'next/navigation';
import {
  Music,
  Download,
  Home,
  Heart,
  RefreshCw,
  FolderOpen,
  Settings,
} from 'lucide-react';
import {
  SignInButton,
  SignUpButton,
  SignedIn,
  SignedOut,
  UserButton,
  useUser,
} from '@clerk/nextjs';
import { AddSampleDialog } from './add-sample-dialog';
import { AddInstagramDialog } from './add-instagram-dialog';
import { CreditBalance } from './credit-balance';

interface AppSidebarProps {
  activeSection?: string;
  onSectionChange?: (section: string) => void;
  onProcessingStarted?: (taskId: string, url: string) => void;
}

export function AppSidebar({ activeSection, onSectionChange, onProcessingStarted }: AppSidebarProps) {
  const { user, isLoaded, isSignedIn } = useUser();
  const pathname = usePathname();

  // Helper function to check if path is active
  const isActive = (path: string) => {
    if (path === '/') {
      return pathname === '/';
    }
    return pathname?.startsWith(path) || false;
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center gap-3 px-6 h-16 border-b flex-shrink-0">
        <div className="w-14 h-14 flex items-center justify-center">
          <Image
            src="/icons/favicon.png"
            alt="Sample the Internet"
            width={56}
            height={56}
            className="w-full h-full object-contain"
          />
        </div>
        <h2 className="font-bold text-sidebar-foreground text-sm whitespace-nowrap">Sample the Internet</h2>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto px-4 py-4">
        <div className="space-y-6">
          {/* Explore Section */}
          <div>
            <div className="px-2 py-1.5 text-xs font-semibold text-sidebar-foreground/60">
              Explore
            </div>
            <div className="space-y-1 mt-1">
              <Link href="/" className="w-full">
                <button
                  className={`w-full flex items-center gap-2 px-3 py-2 rounded-md text-sm transition-colors ${
                    isActive('/')
                      ? 'bg-primary text-primary-foreground font-semibold shadow-sm'
                      : 'text-sidebar-foreground hover:bg-sidebar-accent/50'
                  }`}
                >
                  <Home className="w-4 h-4" />
                  <span>Explore</span>
                </button>
              </Link>
            </div>
          </div>

          {/* Create Section */}
          {onProcessingStarted && (
            <div>
              <div className="px-2 py-1.5 text-xs font-semibold text-sidebar-foreground/60">
                Create
              </div>
              <div className="space-y-1 mt-1">
                <AddSampleDialog
                  onProcessingStarted={onProcessingStarted}
                  variant="sidebar"
                />
                <AddInstagramDialog
                  onProcessingStarted={onProcessingStarted}
                  variant="sidebar"
                />
                <Link href="/tiktok-connect" className="w-full">
                  <button
                    className={`w-full flex items-center gap-2 px-3 py-2 rounded-md text-sm transition-colors ${
                      isActive('/tiktok-connect')
                        ? 'bg-primary text-primary-foreground font-semibold shadow-sm'
                        : 'text-sidebar-foreground hover:bg-sidebar-accent/50'
                    }`}
                  >
                    <RefreshCw className="w-4 h-4" />
                    <span>sync a tok-collection</span>
                  </button>
                </Link>
              </div>
            </div>
          )}

          {/* Library Section - Protected Navigation (only when signed in) */}
          <SignedIn>
            <div>
              <div className="px-2 py-1.5 text-xs font-semibold text-sidebar-foreground/60">
                Library
              </div>
              <div className="space-y-1 mt-1">
                <Link href="/my-downloads" className="w-full">
                  <button
                    className={`w-full flex items-center gap-2 px-3 py-2 rounded-md text-sm transition-colors ${
                      isActive('/my-downloads')
                        ? 'bg-primary text-primary-foreground font-semibold shadow-sm'
                        : 'text-sidebar-foreground hover:bg-sidebar-accent/50'
                    }`}
                  >
                    <Download className="w-4 h-4" />
                    <span>My Downloads</span>
                  </button>
                </Link>
                <Link href="/my-collections" className="w-full">
                  <button
                    className={`w-full flex items-center gap-2 px-3 py-2 rounded-md text-sm transition-colors ${
                      isActive('/my-collections')
                        ? 'bg-primary text-primary-foreground font-semibold shadow-sm'
                        : 'text-sidebar-foreground hover:bg-sidebar-accent/50'
                    }`}
                  >
                    <FolderOpen className="w-4 h-4" />
                    <span>My Collections</span>
                  </button>
                </Link>
                <Link href="/my-favorites" className="w-full">
                  <button
                    className={`w-full flex items-center gap-2 px-3 py-2 rounded-md text-sm transition-colors ${
                      isActive('/my-favorites')
                        ? 'bg-primary text-primary-foreground font-semibold shadow-sm'
                        : 'text-sidebar-foreground hover:bg-sidebar-accent/50'
                    }`}
                  >
                    <Heart className="w-4 h-4" />
                    <span>My Favorites</span>
                  </button>
                </Link>
              </div>
            </div>
          </SignedIn>
        </div>
      </div>

      {/* Credit Balance */}
      <CreditBalance />

      {/* Auth Section */}
      <div className="px-4 py-3 border-t">
        <SignedOut>
          <div className="flex flex-col gap-1.5">
            <SignInButton mode="modal">
              <button className="w-full px-3 py-1.5 text-xs text-sidebar-foreground/70 hover:text-sidebar-foreground hover:bg-sidebar-accent/30 rounded transition-colors">
                Sign In
              </button>
            </SignInButton>
            <SignUpButton mode="modal">
              <button className="w-full px-3 py-1.5 text-xs text-sidebar-foreground/70 hover:text-sidebar-foreground hover:bg-sidebar-accent/30 rounded transition-colors">
                Sign Up
              </button>
            </SignUpButton>
          </div>
        </SignedOut>
        <SignedIn>
          <Link href="/settings" className="w-full mb-2">
            <button
              className="w-full flex items-center gap-2 px-3 py-2 rounded-md text-sm transition-colors text-sidebar-foreground hover:bg-sidebar-accent/50"
            >
              <Settings className="w-4 h-4" />
              <span>Settings</span>
            </button>
          </Link>
          {isLoaded && user && (
            <div className="flex items-center gap-2.5 p-2 rounded hover:bg-sidebar-accent/20 transition-colors">
              <UserButton
                appearance={{
                  elements: {
                    userButtonAvatarBox: "w-8 h-8"
                  }
                }}
              />
              <div className="flex-1 min-w-0">
                <p className="text-xs font-normal text-sidebar-foreground/60 truncate">
                  {user.fullName || user.firstName || 'User'}
                </p>
                <p className="text-[10px] text-sidebar-foreground/40 truncate">
                  {user.primaryEmailAddress?.emailAddress}
                </p>
              </div>
            </div>
          )}
        </SignedIn>
      </div>

      {/* Footer */}
      <div className="px-4 py-2 border-t">
        <p className="text-xs text-sidebar-foreground/60 text-left">
          make music at the speed of culture
        </p>
      </div>
    </div>
  );
}