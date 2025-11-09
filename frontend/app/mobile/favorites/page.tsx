'use client';

import { useAuth, SignInButton } from '@clerk/nextjs';
import { Heart } from 'lucide-react';

export default function FavoritesPage() {
  const { isSignedIn } = useAuth();

  if (!isSignedIn) {
    return (
      <div className="flex flex-col items-center justify-center h-screen text-center p-8 bg-black">
        <Heart className="w-16 h-16 text-gray-600 mb-4" />
        <h2 className="text-xl font-bold mb-2 text-white">
          Sign in to see your favorites
        </h2>
        <p className="text-gray-400 mb-6">
          Save samples you love and access them anytime
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
      <h1 className="text-2xl font-bold mb-6 text-white">Your Favorites</h1>
      <div className="flex flex-col items-center justify-center h-64 text-center">
        <Heart className="w-12 h-12 text-gray-600 mb-4" />
        <p className="text-gray-400">
          Favorites will appear here when you swipe right on samples
        </p>
        <p className="text-sm text-gray-500 mt-2">
          Coming in Phase 5
        </p>
      </div>
    </div>
  );
}
