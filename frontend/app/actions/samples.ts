'use server';

import { revalidatePath, revalidateTag } from 'next/cache';
import { auth } from '@clerk/nextjs/server';
import { createAuthenticatedClient } from '@/lib/api-client';
import { Sample, SampleUpdate, ProcessingTaskResponse, ProcessingStatusResponse, TikTokURLInput, InstagramURLInput } from '@/types/api';

export async function processTikTokUrl(url: string) {
  try {
    const { getToken } = await auth();
    const token = await getToken();

    if (!token) {
      return {
        success: false,
        error: 'Authentication required'
      };
    }

    const apiClient = createAuthenticatedClient(async () => token);
    const input: TikTokURLInput = { url };

    const response = await apiClient.post<ProcessingTaskResponse>(
      '/process/tiktok',
      input
    );

    // Revalidate the samples list to show the new pending item
    revalidatePath('/');
    await revalidateTag('samples', '/');

    return { success: true, data: response };
  } catch (error) {
    console.error('Failed to process TikTok URL:', error);
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Failed to process URL'
    };
  }
}

export async function processInstagramUrl(url: string) {
  try {
    const { getToken } = await auth();
    const token = await getToken();

    if (!token) {
      return {
        success: false,
        error: 'Authentication required'
      };
    }

    const apiClient = createAuthenticatedClient(async () => token);
    const input: InstagramURLInput = { url };

    const response = await apiClient.post<ProcessingTaskResponse>(
      '/process/instagram',
      input
    );

    // Revalidate the samples list to show the new pending item
    revalidatePath('/');
    await revalidateTag('samples', '/');

    return { success: true, data: response };
  } catch (error) {
    console.error('Failed to process Instagram URL:', error);
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Failed to process URL'
    };
  }
}

export async function updateSample(id: string, updates: SampleUpdate) {
  try {
    const { getToken } = await auth();
    const token = await getToken();

    if (!token) {
      return {
        success: false,
        error: 'Authentication required'
      };
    }

    const apiClient = createAuthenticatedClient(async () => token);
    const response = await apiClient.patch<Sample>(
      `/samples/${id}`,
      updates
    );

    // Revalidate both the list and individual sample
    revalidatePath('/');
    revalidatePath(`/samples/${id}`);
    revalidateTag('samples');
    revalidateTag(`sample-${id}`);

    return { success: true, data: response };
  } catch (error) {
    console.error('Failed to update sample:', error);
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Failed to update sample'
    };
  }
}

export async function deleteSample(id: string) {
  try {
    const { getToken } = await auth();
    const token = await getToken();

    if (!token) {
      return {
        success: false,
        error: 'Authentication required'
      };
    }

    const apiClient = createAuthenticatedClient(async () => token);
    await apiClient.delete(`/samples/${id}`);

    // Revalidate the samples list
    revalidatePath('/');
    revalidateTag('samples');

    return { success: true };
  } catch (error) {
    console.error('Failed to delete sample:', error);
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Failed to delete sample'
    };
  }
}

export async function getProcessingStatus(taskId: string): Promise<ProcessingStatusResponse | null> {
  try {
    const { getToken } = await auth();
    const token = await getToken();

    if (!token) {
      return null;
    }

    const apiClient = createAuthenticatedClient(async () => token);
    return await apiClient.get<ProcessingStatusResponse>(`/process/status/${taskId}`);
  } catch (error) {
    console.error('Failed to get processing status:', error);
    return null;
  }
}