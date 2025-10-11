import { NextRequest, NextResponse } from 'next/server';
import { backendApi } from '@/lib/api-client';
import { Sample, SampleUpdate } from '@/types/api';

export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const response = await backendApi.get<Sample>(`/samples/${params.id}`);
    return NextResponse.json(response);
  } catch (error) {
    console.error(`Error fetching sample ${params.id}:`, error);
    return NextResponse.json(
      { error: 'Sample not found' },
      { status: 404 }
    );
  }
}

export async function PATCH(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const body: SampleUpdate = await request.json();
    const response = await backendApi.patch<Sample>(
      `/samples/${params.id}`,
      body
    );
    return NextResponse.json(response);
  } catch (error) {
    console.error(`Error updating sample ${params.id}:`, error);
    return NextResponse.json(
      { error: 'Failed to update sample' },
      { status: 500 }
    );
  }
}

export async function DELETE(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    await backendApi.delete(`/samples/${params.id}`);
    return NextResponse.json({ message: 'Sample deleted successfully' });
  } catch (error) {
    console.error(`Error deleting sample ${params.id}:`, error);
    return NextResponse.json(
      { error: 'Failed to delete sample' },
      { status: 500 }
    );
  }
}