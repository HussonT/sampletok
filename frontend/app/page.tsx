import { mockSamples } from '@/data/mock-samples';
import MainApp from '@/components/main-app';

export default function Home() {
  // This is a Server Component by default in Next.js 15
  // We can fetch data here and pass it to the client component
  return <MainApp initialSamples={mockSamples} />;
}