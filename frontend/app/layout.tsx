import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";
import { ClerkProvider } from "@clerk/nextjs";
import { PostHogProvider } from "@/providers/posthog-provider";
import { CookieConsent } from "@/components/cookie-consent";
import Script from "next/script";
import "./globals.css";

// Note: Toaster is intentionally NOT included here to avoid duplicate toasts.
// Each layout (desktop and mobile) includes its own Toaster with appropriate positioning.

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Sample the Internet - Make music at the speed of culture",
  description: "Discover audio samples from across the internet - browse and download premium samples for your next viral song",
  applicationName: "Sample the Internet",
  appleWebApp: {
    capable: true,
    statusBarStyle: "black-translucent",
    title: "Sample the Internet",
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
            <CookieConsent />
          </PostHogProvider>
          <Script
            id="tiktok-pixel"
            strategy="lazyOnload"
            dangerouslySetInnerHTML={{
              __html: `
!function (w, d, t) {
  w.TiktokAnalyticsObject=t;var ttq=w[t]=w[t]||[];ttq.methods=["page","track","identify","instances","debug","on","off","once","ready","alias","group","enableCookie","disableCookie","holdConsent","revokeConsent","grantConsent"],ttq.setAndDefer=function(t,e){t[e]=function(){t.push([e].concat(Array.prototype.slice.call(arguments,0)))}};for(var i=0;i<ttq.methods.length;i++)ttq.setAndDefer(ttq,ttq.methods[i]);ttq.instance=function(t){for(
var e=ttq._i[t]||[],n=0;n<ttq.methods.length;n++)ttq.setAndDefer(e,ttq.methods[n]);return e},ttq.load=function(e,n){var r="https://analytics.tiktok.com/i18n/pixel/events.js",o=n&&n.partner;ttq._i=ttq._i||{},ttq._i[e]=[],ttq._i[e]._u=r,ttq._t=ttq._t||{},ttq._t[e]=+new Date,ttq._o=ttq._o||{},ttq._o[e]=n||{};n=document.createElement("script")
;n.type="text/javascript",n.async=!0,n.src=r+"?sdkid="+e+"&lib="+t;e=document.getElementsByTagName("script")[0];e.parentNode.insertBefore(n,e)};

  ttq.load('D4B3ABJC77UCI3HO33M0');
  ttq.page();
}(window, document, 'ttq');
              `,
            }}
          />
        </body>
      </html>
    </ClerkProvider>
  );
}