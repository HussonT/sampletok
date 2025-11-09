'use client';

import { Search } from 'lucide-react';

export default function SearchPage() {
  return (
    <div className="p-6 bg-black min-h-screen">
      <h1 className="text-2xl font-bold mb-6 text-white">Search</h1>
      <div className="flex flex-col items-center justify-center h-64 text-center">
        <Search className="w-12 h-12 text-gray-600 mb-4" />
        <p className="text-gray-400">
          Search and filter samples by BPM, key, and creator
        </p>
        <p className="text-sm text-gray-500 mt-2">
          Coming in Phase 5
        </p>
      </div>
    </div>
  );
}
