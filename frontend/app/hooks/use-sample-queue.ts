'use client';

import { useState, useEffect, useCallback } from 'react';
import { useInfiniteQuery } from '@tanstack/react-query';
import { Sample, PaginatedResponse } from '@/types/api';

interface UseSampleQueueOptions {
  apiClient: any; // Will be the authenticated or public API client
  enabled?: boolean;
}

export function useSampleQueue({ apiClient, enabled = true }: UseSampleQueueOptions) {
  const [page, setPage] = useState(0);

  // Fetch samples with infinite query
  const {
    data,
    fetchNextPage,
    hasNextPage,
    isLoading,
    isFetchingNextPage,
    refetch
  } = useInfiniteQuery({
    queryKey: ['mobile-feed-infinite'],
    queryFn: async ({ pageParam }: { pageParam: number }) => {
      const response = await apiClient.get('/samples', {
        limit: 10,
        skip: pageParam * 10,
        status: 'completed',
      });
      return response as PaginatedResponse<Sample>;
    },
    getNextPageParam: (lastPage: PaginatedResponse<Sample>, allPages: PaginatedResponse<Sample>[]) => {
      // If there are more items, return next page number
      if (lastPage.has_more) {
        return allPages.length;
      }
      return undefined;
    },
    initialPageParam: 0,
    enabled,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  // Flatten all samples from all pages
  const samples = data?.pages.flatMap(page => page.items) || [];

  const loadMore = useCallback(() => {
    if (hasNextPage && !isFetchingNextPage) {
      fetchNextPage();
    }
  }, [hasNextPage, isFetchingNextPage, fetchNextPage]);

  const reset = useCallback(() => {
    refetch();
  }, [refetch]);

  return {
    samples,
    loadMore,
    hasMore: hasNextPage || false,
    isLoading: isLoading || isFetchingNextPage,
    reset,
    refetch: reset, // Alias for consistency
  };
}
