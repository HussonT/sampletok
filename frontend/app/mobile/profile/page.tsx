'use client';

import { useEffect, useState } from 'react';
import { useAuth, useClerk, SignInButton } from '@clerk/nextjs';
import { useRouter } from 'next/navigation';
import { User, Settings, LogOut, Monitor, Smartphone, Zap, Database, ExternalLink, Coins, Crown, Sparkles } from 'lucide-react';
import { Switch } from '@/components/ui/switch';
import { Separator } from '@/components/ui/separator';
import { useMobileSettings } from '@/hooks/use-mobile-settings';
import { createAuthenticatedClient } from '@/lib/api-client';
import { UserStats } from '@/types/api';
import { toast } from 'sonner';

export default function ProfilePage() {
  const { isSignedIn, isLoaded, getToken } = useAuth();
  const { signOut, user } = useClerk();
  const router = useRouter();
  const { settings, updateSetting, isLoaded: settingsLoaded } = useMobileSettings();
  const [stats, setStats] = useState<UserStats | null>(null);
  const [isLoadingStats, setIsLoadingStats] = useState(true);
  const [statsError, setStatsError] = useState<string | null>(null);

  // Fetch user stats
  useEffect(() => {
    if (!isSignedIn || !isLoaded) {
      setIsLoadingStats(false);
      return;
    }

    const fetchStats = async () => {
      try {
        const token = await getToken();
        if (!token) {
          setStatsError('Unable to authenticate');
          setIsLoadingStats(false);
          return;
        }

        const apiClient = createAuthenticatedClient(getToken);
        const data = await apiClient.get<UserStats>('/users/me/stats');
        setStats(data);
        setStatsError(null);
      } catch (error) {
        console.error('Error fetching user stats:', error);
        setStatsError('Failed to load stats');
      } finally {
        setIsLoadingStats(false);
      }
    };

    fetchStats();
  }, [isSignedIn, isLoaded]);

  const handleSignOut = async () => {
    try {
      await signOut();
      toast.success('Signed out successfully');
    } catch (error) {
      console.error('Error signing out:', error);
      toast.error('Failed to sign out');
    }
  };

  const handleDesktopRedirect = () => {
    // Redirect to main domain (desktop version)
    window.location.href = window.location.origin.replace('/mobile', '');
  };

  if (!isLoaded || !settingsLoaded) {
    return (
      <div className="flex flex-col items-center justify-center h-screen bg-black">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-[hsl(338,82%,65%)]"></div>
        <p className="text-gray-400 mt-4">Loading profile...</p>
      </div>
    );
  }

  if (!isSignedIn) {
    return (
      <div className="flex flex-col items-center justify-center h-screen text-center p-8 bg-black relative overflow-hidden">
        {/* Gradient background effect */}
        <div className="absolute inset-0 bg-gradient-to-br from-[hsl(338,82%,65%)]/5 via-transparent to-transparent" />

        <div className="relative z-10 space-y-6">
          {/* Icon with gradient background */}
          <div className="mx-auto w-24 h-24 rounded-full bg-gradient-to-br from-[hsl(338,82%,65%)]/20 to-[hsl(338,82%,65%)]/5 flex items-center justify-center backdrop-blur-sm border border-[hsl(338,82%,65%)]/20">
            <User className="w-12 h-12 text-[hsl(338,82%,65%)]" />
          </div>

          <div className="space-y-3">
            <h2 className="text-2xl font-bold text-white">
              Sign in to access your profile
            </h2>
            <p className="text-gray-400 text-base max-w-sm mx-auto">
              View your stats, settings, and preferences
            </p>
          </div>

          <SignInButton mode="modal">
            <button className="bg-gradient-to-br from-[hsl(338,82%,65%)] to-[hsl(338,82%,55%)] hover:from-[hsl(338,82%,60%)] hover:to-[hsl(338,82%,50%)] px-8 py-4 rounded-full text-white font-semibold shadow-lg shadow-[hsl(338,82%,65%)]/25 transition-all duration-200 active:scale-95">
              Sign In
            </button>
          </SignInButton>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-black pb-20">
      {/* Header */}
      <div className="sticky top-0 z-10 bg-black/95 backdrop-blur-sm border-b border-white/10 px-4 py-4">
        <div className="flex items-center gap-3">
          <User className="w-6 h-6 text-[hsl(338,82%,65%)]" />
          <h1 className="text-xl font-bold text-white">Profile</h1>
        </div>
      </div>

      {/* User Info Card */}
      <div className="p-4">
        <div className="bg-gradient-to-br from-[hsl(338,82%,65%)]/10 to-[hsl(338,82%,65%)]/5 backdrop-blur-md rounded-2xl border border-[hsl(338,82%,65%)]/20 p-4">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-14 h-14 rounded-full bg-gradient-to-br from-[hsl(338,82%,65%)] to-[hsl(338,82%,55%)] flex items-center justify-center text-white text-xl font-bold">
              {user?.firstName?.charAt(0) || user?.username?.charAt(0) || 'U'}
            </div>
            <div className="flex-1 min-w-0">
              <h2 className="text-lg font-semibold text-white truncate">
                {user?.firstName && user?.lastName
                  ? `${user.firstName} ${user.lastName}`
                  : user?.username || 'User'}
              </h2>
              <p className="text-sm text-gray-400 truncate">
                {user?.primaryEmailAddress?.emailAddress || ''}
              </p>
            </div>
          </div>

          {/* Credits Balance - Prominent Display */}
          {isLoadingStats ? (
            <div className="flex items-center justify-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-[hsl(338,82%,65%)]"></div>
            </div>
          ) : statsError ? (
            <div className="text-center py-4">
              <p className="text-sm text-red-400">{statsError}</p>
            </div>
          ) : stats ? (
            <>
              {/* Credits Card - Prominent */}
              <div className="bg-gradient-to-r from-[hsl(338,82%,65%)] to-[hsl(338,82%,55%)] rounded-xl p-4 mb-3">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <Coins className="w-5 h-5 text-white" />
                      <span className="text-sm text-white/90 font-medium">Credit Balance</span>
                    </div>
                    <div className="text-3xl font-bold text-white">{stats.credits}</div>
                    <p className="text-xs text-white/80 mt-1">Available credits</p>
                  </div>
                  <div className="w-16 h-16 rounded-full bg-white/20 backdrop-blur-sm flex items-center justify-center">
                    <Coins className="w-8 h-8 text-white" />
                  </div>
                </div>
              </div>

              {/* Upgrade Button - Prominent CTA */}
              <button
                onClick={() => router.push('/pricing')}
                className="w-full bg-gradient-to-r from-yellow-500 to-yellow-400 hover:from-yellow-400 hover:to-yellow-300 rounded-xl p-4 mb-3 transition-all duration-200 active:scale-[0.98] shadow-lg shadow-yellow-500/25"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-white/30 backdrop-blur-sm flex items-center justify-center">
                      <Crown className="w-5 h-5 text-white" />
                    </div>
                    <div className="text-left">
                      <div className="flex items-center gap-2">
                        <span className="text-white font-bold text-base">Upgrade to Pro</span>
                        <Sparkles className="w-4 h-4 text-white/90" />
                      </div>
                      <p className="text-xs text-white/90">Get unlimited downloads & more</p>
                    </div>
                  </div>
                  <ExternalLink className="w-5 h-5 text-white/80" />
                </div>
              </button>
            </>
          ) : null}
        </div>
      </div>

      {/* Settings Section */}
      <div className="px-4 pb-4">
        <div className="bg-white/5 backdrop-blur-md rounded-2xl border border-white/10 overflow-hidden">
          <div className="px-4 py-3 border-b border-white/10">
            <div className="flex items-center gap-2">
              <Settings className="w-5 h-5 text-[hsl(338,82%,65%)]" />
              <h3 className="text-lg font-semibold text-white">Settings</h3>
            </div>
          </div>

          <div className="divide-y divide-white/10">
            {/* Auto-play Videos */}
            <div className="px-4 py-4 flex items-center justify-between">
              <div className="flex items-start gap-3 flex-1 mr-4">
                <Smartphone className="w-5 h-5 text-[hsl(338,82%,65%)] mt-0.5 flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-white font-medium mb-1">Auto-play videos</p>
                  <p className="text-xs text-gray-400">
                    Automatically play videos when scrolled into view
                  </p>
                </div>
              </div>
              <Switch
                checked={settings.autoPlayVideos}
                onCheckedChange={(checked) => updateSetting('autoPlayVideos', checked)}
              />
            </div>

            {/* Haptic Feedback */}
            <div className="px-4 py-4 flex items-center justify-between">
              <div className="flex items-start gap-3 flex-1 mr-4">
                <Zap className="w-5 h-5 text-[hsl(338,82%,65%)] mt-0.5 flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-white font-medium mb-1">Haptic feedback</p>
                  <p className="text-xs text-gray-400">
                    Vibrate on taps and interactions
                  </p>
                </div>
              </div>
              <Switch
                checked={settings.hapticFeedback}
                onCheckedChange={(checked) => updateSetting('hapticFeedback', checked)}
              />
            </div>

            {/* Data Saver Mode */}
            <div className="px-4 py-4 flex items-center justify-between">
              <div className="flex items-start gap-3 flex-1 mr-4">
                <Database className="w-5 h-5 text-[hsl(338,82%,65%)] mt-0.5 flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-white font-medium mb-1">Data saver mode</p>
                  <p className="text-xs text-gray-400">
                    Reduce data usage (lower quality videos)
                  </p>
                </div>
              </div>
              <Switch
                checked={settings.dataSaverMode}
                onCheckedChange={(checked) => updateSetting('dataSaverMode', checked)}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Actions Section */}
      <div className="px-4 space-y-3">
        {/* Link to Desktop Version */}
        <button
          onClick={handleDesktopRedirect}
          className="w-full bg-white/5 hover:bg-white/10 backdrop-blur-md rounded-xl border border-white/10 px-4 py-4 flex items-center gap-3 transition-colors"
        >
          <Monitor className="w-5 h-5 text-[hsl(338,82%,65%)]" />
          <div className="flex-1 text-left">
            <p className="text-white font-medium">Desktop version</p>
            <p className="text-xs text-gray-400">Switch to full desktop experience</p>
          </div>
          <ExternalLink className="w-4 h-4 text-gray-400" />
        </button>

        {/* Sign Out */}
        <button
          onClick={handleSignOut}
          className="w-full bg-red-500/10 hover:bg-red-500/20 backdrop-blur-md rounded-xl border border-red-500/20 px-4 py-4 flex items-center gap-3 transition-colors"
        >
          <LogOut className="w-5 h-5 text-red-400" />
          <div className="flex-1 text-left">
            <p className="text-red-400 font-medium">Sign out</p>
            <p className="text-xs text-red-400/70">Log out of your account</p>
          </div>
        </button>
      </div>

      {/* App Info */}
      <div className="px-4 pt-6 pb-4 text-center">
        <p className="text-xs text-gray-500">
          SampleTok Mobile v1.0
        </p>
        <p className="text-xs text-gray-600 mt-1">
          Discover and save audio samples from TikTok
        </p>
      </div>
    </div>
  );
}
