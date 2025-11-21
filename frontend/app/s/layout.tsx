import { ReactNode } from 'react';

export default function PublicSampleLayout({
  children,
}: {
  children: ReactNode;
}) {
  // Minimal layout without sidebar for public shareable pages
  return children;
}
