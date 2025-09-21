import { Suspense } from 'react';
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

  // Parse filters from URL search params
  const filters: SampleFilters = {
    search: params.search,
    genre: params.genre,
    status: params.status,
    skip: params.page ? (parseInt(params.page) - 1) * 20 : 0,
    limit: 20
  };

  // Fetch data on the server
  const samplesData = await getSamples(filters);

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