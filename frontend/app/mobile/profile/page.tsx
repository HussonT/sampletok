'use client';

import { useAuth, SignInButton, UserButton } from '@clerk/nextjs';
import { User } from 'lucide-react';

export default function ProfilePage() {
  const { isSignedIn } = useAuth();

  if (!isSignedIn) {
    return (
      <div className="flex flex-col items-center justify-center h-screen text-center p-8 bg-black">
        <User className="w-16 h-16 text-gray-600 mb-4" />
        <h2 className="text-xl font-bold mb-2 text-white">
          Sign in to access your profile
        </h2>
        <p className="text-gray-400 mb-6">
          View your stats, settings, and preferences
        </p>
        <SignInButton mode="modal">
          <button className="bg-green-600 hover:bg-green-700 px-6 py-3 rounded-lg text-white font-semibold">
            Sign In
          </button>
        </SignInButton>
      </div>
    );
  }

  return (
    <div className="p-6 bg-black min-h-screen">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-white">Profile</h1>
        <UserButton />
      </div>

      <div className="flex flex-col items-center justify-center h-64 text-center">
        <User className="w-12 h-12 text-gray-600 mb-4" />
        <p className="text-gray-400">
          Profile stats and settings coming soon
        </p>
        <p className="text-sm text-gray-500 mt-2">
          Coming in Phase 5
        </p>
      </div>
    </div>
  );
}
