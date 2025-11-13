import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";
import { ClerkProvider } from "@clerk/nextjs";
import { Toaster } from "@/components/ui/sonner";
import { PostHogProvider } from "@/providers/posthog-provider";
import { CookieConsent } from "@/components/cookie-consent";
import { TikTokPixel } from "@/components/tiktok-pixel";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Sampletok - Make music at the speed of culture",
  description: "Discover TikTok audio samples with swipeable cards - browse and download premium samples for your next viral song",
  applicationName: "SampleTok",
  appleWebApp: {
    capable: true,
    statusBarStyle: "black-translucent",
    title: "SampleTok",
  },
  formatDetection: {
    telephone: false,
  },
  manifest: "/manifest.json",
  icons: {
    icon: [
      { url: "/icons/favicon-16x16.png", sizes: "16x16", type: "image/png" },
      { url: "/icons/favicon-32x32.png", sizes: "32x32", type: "image/png" },
    ],
    apple: [
      { url: "/icons/apple-touch-icon.png", sizes: "180x180", type: "image/png" },
    ],
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 5,
  userScalable: true,
  themeColor: "#10b981",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <ClerkProvider>
      <html lang="en" className="dark" suppressHydrationWarning>
        <body className={inter.className}>
          <PostHogProvider>
            {children}
            <Toaster />
            <CookieConsent />
          </PostHogProvider>
          <TikTokPixel />
        </body>
      </html>
    </ClerkProvider>
  );
}