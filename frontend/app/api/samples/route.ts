import { NextRequest, NextResponse } from 'next/server';
import { backendApi } from '@/lib/api-client';
import { Sample, PaginatedResponse, SampleFilters } from '@/types/api';

export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams;

    const filters: SampleFilters = {
      skip: searchParams.get('skip') ? parseInt(searchParams.get('skip')!) : undefined,
      limit: searchParams.get('limit') ? parseInt(searchParams.get('limit')!) : undefined,
      genre: searchParams.get('genre') || undefined,
      status: searchParams.get('status') || undefined,
      search: searchParams.get('search') || undefined,
    };

    // Remove undefined values
    const cleanFilters = Object.fromEntries(
      Object.entries(filters).filter(([_, v]) => v !== undefined)
    );

    const response = await backendApi.get<PaginatedResponse<Sample>>(
      '/samples',
      cleanFilters
    );

    return NextResponse.json(response);
  } catch (error) {
    console.error('Error fetching samples:', error);
    return NextResponse.json(
      { error: 'Failed to fetch samples' },
      { status: 500 }
    );
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();

    const response = await backendApi.post<Sample>('/samples', body);

    return NextResponse.json(response, { status: 201 });
  } catch (error) {
    console.error('Error creating sample:', error);
    return NextResponse.json(
      { error: 'Failed to create sample' },
      { status: 500 }
    );
  }
}