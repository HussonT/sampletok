'use server';

import { revalidatePath, revalidateTag } from 'next/cache';
import { backendApi } from '@/lib/api-client';
import { Sample, SampleUpdate, ProcessingTaskResponse, ProcessingStatusResponse, TikTokURLInput, InstagramURLInput } from '@/types/api';

export async function processTikTokUrl(url: string) {
  try {
    const input: TikTokURLInput = { url };

    const response = await backendApi.post<ProcessingTaskResponse>(
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
    const input: InstagramURLInput = { url };

    const response = await backendApi.post<ProcessingTaskResponse>(
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
    const response = await backendApi.patch<Sample>(
      `/samples/${id}`,
      updates
    );

    // Revalidate both the list and individual sample
    revalidatePath('/');
    revalidatePath(`/samples/${id}`);
    await revalidateTag('samples', '/');
    await revalidateTag(`sample-${id}`, `/samples/${id}`);

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
    await backendApi.delete(`/samples/${id}`);

    // Revalidate the samples list
    revalidatePath('/');
    await revalidateTag('samples', '/');

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
    // Note: backendApi doesn't support Next.js cache options, but this is
    // called frequently so we want fresh data anyway
    return await backendApi.get<ProcessingStatusResponse>(`/process/status/${taskId}`);
  } catch (error) {
    console.error('Failed to get processing status:', error);
    return null;
  }
}