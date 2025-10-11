import { NextRequest, NextResponse } from 'next/server';
import { backendApi } from '@/lib/api-client';
import { ProcessingTaskResponse, TikTokURLInput } from '@/types/api';

export async function POST(request: NextRequest) {
  try {
    const body: TikTokURLInput = await request.json();

    // Validate URL
    if (!body.url) {
      return NextResponse.json(
        { error: 'URL is required' },
        { status: 400 }
      );
    }

    // Validate TikTok URL format
    const tiktokPattern = /^(https?:\/\/)?(www\.)?(tiktok\.com|vm\.tiktok\.com)\/.*/;
    if (!tiktokPattern.test(body.url)) {
      return NextResponse.json(
        { error: 'Invalid TikTok URL format' },
        { status: 400 }
      );
    }

    const response = await backendApi.post<ProcessingTaskResponse>(
      '/process/tiktok',
      body
    );

    return NextResponse.json(response, { status: 202 });
  } catch (error) {
    console.error('Error processing TikTok URL:', error);

    // Check if it's a specific error from backend
    const errorMessage = error instanceof Error ? error.message : 'Failed to process TikTok URL';

    return NextResponse.json(
      { error: errorMessage },
      { status: 500 }
    );
  }
}