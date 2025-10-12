import { NextRequest, NextResponse } from 'next/server';
import { backendApi } from '@/lib/api-client';
import { ProcessingStatusResponse } from '@/types/api';

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const response = await backendApi.get<ProcessingStatusResponse>(
      `/process/status/${id}`
    );

    return NextResponse.json(response);
  } catch (error) {
    console.error(`Error fetching processing status:`, error);
    return NextResponse.json(
      { error: 'Failed to fetch processing status' },
      { status: 500 }
    );
  }
}