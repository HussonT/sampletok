import { unstable_cache } from 'next/cache';
import { Sample, PaginatedResponse, SampleFilters } from '@/types/api';

// Fetch samples with optional authentication
export async function getSamples(filters?: SampleFilters, authToken?: string | null): Promise<PaginatedResponse<Sample>> {
  const params = new URLSearchParams();

  if (filters) {
    Object.entries(filters).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        params.append(key, String(value));
      }
    });
  }

  const baseUrl = process.env.NEXT_PUBLIC_API_URL;
  if (!baseUrl) {
    console.error('[getSamples] NEXT_PUBLIC_API_URL is not set');
    throw new Error('NEXT_PUBLIC_API_URL environment variable is not set');
  }

  const url = `${baseUrl}/api/v1/samples${params.toString() ? `?${params}` : ''}`;
  console.log('[getSamples] Fetching from:', url);

  const headers: HeadersInit = {
    'Content-Type': 'application/json',
  };

  // Include auth token if provided
  if (authToken) {
    headers['Authorization'] = `Bearer ${authToken}`;
  }

  try {
    const response = await fetch(url, {
      headers,
      next: {
        revalidate: 5, // Revalidate every 5 seconds for fresh data
        tags: ['samples']
      }
    });

    if (!response.ok) {
      const errorText = await response.text().catch(() => 'No error details');
      console.error('[getSamples] Failed to fetch:', { url, status: response.status, statusText: response.statusText, error: errorText });
      throw new Error(`Failed to fetch samples: ${response.status} ${response.statusText}`);
    }

    return response.json();
  } catch (error) {
    console.error('[getSamples] Error fetching samples:', { url, error });
    throw error;
  }
}

// Fetch single sample with caching
export const getSampleById = unstable_cache(
  async (id: string): Promise<Sample> => {
    const response = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL}/api/v1/samples/${id}`,
      {
        next: {
          revalidate: 60,
          tags: [`sample-${id}`]
        }
      }
    );

    if (!response.ok) {
      throw new Error('Sample not found');
    }

    return response.json();
  },
  ['sample'],
  {
    revalidate: 60,
    tags: ['sample']
  }
);

// Get processing status (no cache, real-time)
export async function getProcessingStatus(taskId: string) {
  const response = await fetch(
    `${process.env.NEXT_PUBLIC_API_URL}/api/v1/process/status/${taskId}`,
    {
      cache: 'no-store' // Always fetch fresh
    }
  );

  if (!response.ok) {
    throw new Error('Failed to fetch processing status');
  }

  return response.json();
}