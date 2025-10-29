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

  const url = `${process.env.BACKEND_URL}/api/v1/samples${params.toString() ? `?${params}` : ''}`;

  const headers: HeadersInit = {
    'Content-Type': 'application/json',
  };

  // Include auth token if provided
  if (authToken) {
    headers['Authorization'] = `Bearer ${authToken}`;
  }

  const response = await fetch(url, {
    headers,
    next: {
      revalidate: 5, // Revalidate every 5 seconds for fresh data
      tags: ['samples']
    }
  });

  if (!response.ok) {
    throw new Error('Failed to fetch samples');
  }

  return response.json();
}

// Fetch single sample with caching
export const getSampleById = unstable_cache(
  async (id: string): Promise<Sample> => {
    const response = await fetch(
      `${process.env.BACKEND_URL}/api/v1/samples/${id}`,
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
    `${process.env.BACKEND_URL}/api/v1/process/status/${taskId}`,
    {
      cache: 'no-store' // Always fetch fresh
    }
  );

  if (!response.ok) {
    throw new Error('Failed to fetch processing status');
  }

  return response.json();
}