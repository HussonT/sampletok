import { NextRequest, NextResponse } from 'next/server';
import { backendApi } from '@/lib/api-client';
import { ProcessingStatusResponse } from '@/types/api';

export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const response = await backendApi.get<ProcessingStatusResponse>(
      `/process/status/${params.id}`
    );

    return NextResponse.json(response);
  } catch (error) {
    console.error(`Error fetching processing status for ${params.id}:`, error);
    return NextResponse.json(
      { error: 'Failed to fetch processing status' },
      { status: 500 }
    );
  }
}