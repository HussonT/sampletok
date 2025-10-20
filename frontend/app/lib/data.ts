import { unstable_cache } from 'next/cache';
import { Sample, PaginatedResponse, SampleFilters, Tag, PopularTagsResponse, TagSuggestionsResponse, AddTagsRequest } from '@/types/api';

// Fetch samples with caching
export const getSamples = unstable_cache(
  async (filters?: SampleFilters): Promise<PaginatedResponse<Sample>> => {
    const params = new URLSearchParams();

    if (filters) {
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          params.append(key, String(value));
        }
      });
    }

    const url = `${process.env.BACKEND_URL}/api/v1/samples${params.toString() ? `?${params}` : ''}`;

    const response = await fetch(url, {
      next: {
        revalidate: 5, // Revalidate every 5 seconds for fresh data
        tags: ['samples']
      }
    });

    if (!response.ok) {
      throw new Error('Failed to fetch samples');
    }

    return response.json();
  },
  ['samples'], // Cache key
  {
    revalidate: 5,
    tags: ['samples']
  }
);

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

// Tag-related functions

// Get popular tags
export const getPopularTags = unstable_cache(
  async (limit: number = 30): Promise<PopularTagsResponse> => {
    const response = await fetch(
      `${process.env.BACKEND_URL}/api/v1/tags/popular?limit=${limit}`,
      {
        next: {
          revalidate: 60,
          tags: ['popular-tags']
        }
      }
    );

    if (!response.ok) {
      throw new Error('Failed to fetch popular tags');
    }

    return response.json();
  },
  ['popular-tags'],
  {
    revalidate: 60,
    tags: ['popular-tags']
  }
);

// Search tags (no cache, user input)
export async function searchTags(query: string, limit: number = 20): Promise<Tag[]> {
  const response = await fetch(
    `${process.env.BACKEND_URL}/api/v1/tags?search=${encodeURIComponent(query)}&limit=${limit}`,
    {
      cache: 'no-store'
    }
  );

  if (!response.ok) {
    throw new Error('Failed to search tags');
  }

  return response.json();
}

// Get tag suggestions for a sample
export async function getTagSuggestions(sampleId: string): Promise<TagSuggestionsResponse> {
  const response = await fetch(
    `${process.env.BACKEND_URL}/api/v1/tags/samples/${sampleId}/suggestions`,
    {
      cache: 'no-store'
    }
  );

  if (!response.ok) {
    throw new Error('Failed to get tag suggestions');
  }

  return response.json();
}

// Add tags to a sample
export async function addTagsToSample(sampleId: string, tagNames: string[]): Promise<Tag[]> {
  const body: AddTagsRequest = { tag_names: tagNames };

  const response = await fetch(
    `${process.env.BACKEND_URL}/api/v1/tags/samples/${sampleId}/tags`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
      cache: 'no-store'
    }
  );

  if (!response.ok) {
    throw new Error('Failed to add tags');
  }

  return response.json();
}

// Remove tag from a sample
export async function removeTagFromSample(sampleId: string, tagName: string): Promise<void> {
  const response = await fetch(
    `${process.env.BACKEND_URL}/api/v1/tags/samples/${sampleId}/tags/${encodeURIComponent(tagName)}`,
    {
      method: 'DELETE',
      cache: 'no-store'
    }
  );

  if (!response.ok) {
    throw new Error('Failed to remove tag');
  }
}