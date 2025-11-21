import { Metadata } from 'next';
import { notFound } from 'next/navigation';
import { Sample } from '@/types/api';
import { PublicSamplePlayer } from '@/components/features/public-sample-player';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Fetch sample data server-side for SEO
async function getSample(id: string): Promise<Sample | null> {
  try {
    const res = await fetch(`${API_URL}/api/v1/samples/${id}/public`, {
      cache: 'no-store', // Always get fresh data
    });

    if (!res.ok) {
      return null;
    }

    return res.json();
  } catch (error) {
    console.error('Error fetching sample:', error);
    return null;
  }
}

// Generate metadata for SEO and social sharing
export async function generateMetadata({
  params
}: {
  params: Promise<{ id: string }>
}): Promise<Metadata> {
  const { id } = await params;
  const sample = await getSample(id);

  if (!sample) {
    return {
      title: 'Sample Not Found - Sample the Internet',
      description: 'This sample could not be found or is not yet available.',
    };
  }

  const title = sample.title || `Sample by @${sample.creator_username}`;
  const description = sample.description
    ? `${sample.description.substring(0, 155)}...`
    : `BPM: ${sample.bpm || 'Unknown'} | Key: ${sample.key || 'Unknown'} | ${Math.floor(sample.duration_seconds || 0)}s audio sample`;

  const creatorName = sample.creator_name || sample.creator_username || 'Unknown Creator';

  // Get the appropriate source URL
  const sourceUrl = sample.source === 'instagram' ? sample.instagram_url : sample.tiktok_url;
  const platform = sample.source === 'instagram' ? 'Instagram' : 'TikTok';

  // Use waveform as og:image, fallback to thumbnail or cover
  const imageUrl = sample.waveform_url || sample.thumbnail_url || sample.cover_url;

  const metadata: Metadata = {
    title: `${title} - Sample the Internet`,
    description,
    openGraph: {
      title: `${title} 🎵`,
      description: `${description}\n\nBy ${creatorName} on ${platform}`,
      type: 'music.song',
      url: `https://app.sampletheinternet.com/s/${id}`,
      siteName: 'Sample the Internet',
      images: imageUrl ? [
        {
          url: imageUrl,
          width: 1200,
          height: 630,
          alt: `Audio waveform for ${title}`,
        }
      ] : [],
    },
    twitter: {
      card: 'summary_large_image',
      site: '@sampletheinternet',
      creator: '@sampletheinternet',
      title: `${title} 🎵`,
      description: `BPM: ${sample.bpm || 'Unknown'} | Key: ${sample.key || 'Unknown'}\nBy ${creatorName}`,
      images: imageUrl ? [imageUrl] : [],
    },
    other: {
      'music:duration': sample.duration_seconds?.toString() || '0',
      'music:musician': creatorName,
    },
  };

  return metadata;
}

export default async function PublicSamplePage({
  params
}: {
  params: Promise<{ id: string }>
}) {
  const { id } = await params;
  const sample = await getSample(id);

  if (!sample) {
    notFound();
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-background to-background/95">
      <PublicSamplePlayer sample={sample} />
    </div>
  );
}
