import { Suspense } from 'react';
import { auth } from '@clerk/nextjs/server';
import { getSamples } from '@/lib/data';
import MainApp from '@/components/main-app';
import { SampleFilters } from '@/types/api';

interface HomeProps {
  searchParams: Promise<{
    search?: string;
    genre?: string;
    status?: string;
    page?: string;
  }>;
}

export default async function Home({ searchParams }: HomeProps) {
  // Await searchParams as required in Next.js 15
  const params = await searchParams;

  // Get auth token from Clerk (server-side)
  const { getToken } = await auth();
  const authToken = await getToken();

  // Parse filters from URL search params
  const filters: SampleFilters = {
    search: params.search,
    genre: params.genre,
    status: params.status,
    skip: params.page ? (parseInt(params.page) - 1) * 20 : 0,
    limit: 20
  };

  // Fetch data on the server with error handling (with auth token)
  let samplesData;
  try {
    console.log('[BUILD] NEXT_PUBLIC_API_URL:', process.env.NEXT_PUBLIC_API_URL || 'NOT SET');
    samplesData = await getSamples(filters, authToken);
    console.log('[BUILD] Successfully fetched', samplesData?.items?.length || 0, 'samples');
  } catch (error) {
    console.error('[BUILD] Failed to fetch samples:', error);
    // Return empty data if backend is unavailable
    samplesData = { items: [], total: 0 };
  }

  return (
    <Suspense fallback={<div>Loading samples...</div>}>
      <MainApp
        initialSamples={samplesData.items}
        totalSamples={samplesData.total}
        currentFilters={filters}
      />
    </Suspense>
  );
}