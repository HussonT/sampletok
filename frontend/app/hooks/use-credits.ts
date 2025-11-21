'use client';

import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useAuth } from '@clerk/nextjs';
import { createAuthenticatedClient } from '@/lib/api-client';

interface CreditBalanceData {
  credits: number;
  has_subscription: boolean;
  subscription_tier: string | null;
  monthly_credits: number | null;
  next_renewal: string | null;
}

const CREDITS_QUERY_KEY = ['credits', 'balance'];

/**
 * Hook to fetch and manage credit balance
 * Uses React Query for caching and event-driven refetch
 */
export function useCredits() {
  const { getToken, isSignedIn } = useAuth();
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: CREDITS_QUERY_KEY,
    queryFn: async () => {
      const token = await getToken();
      if (!token) {
        throw new Error('No auth token available');
      }

      const api = createAuthenticatedClient(async () => token);
      return api.get<CreditBalanceData>('/credits/balance');
    },
    enabled: isSignedIn,
    staleTime: 5 * 60 * 1000, // 5 minutes
    gcTime: 10 * 60 * 1000, // 10 minutes
    refetchOnWindowFocus: true, // Refetch when user returns to tab
    refetchOnMount: false, // Don't refetch on every mount
  });

  /**
   * Manually refetch credits (call after credit-changing operations)
   */
  const refetch = () => {
    return queryClient.invalidateQueries({ queryKey: CREDITS_QUERY_KEY });
  };

  return {
    credits: query.data?.credits ?? null,
    creditData: query.data ?? null,
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error,
    refetch,
  };
}

/**
 * Hook to trigger credit refetch from any component
 */
export function useRefreshCredits() {
  const queryClient = useQueryClient();

  return () => {
    queryClient.invalidateQueries({ queryKey: CREDITS_QUERY_KEY });
  };
}
