"use client";

import { useEffect, useState } from "react";
import Script from "next/script";

declare global {
  interface Window {
    ttq?: any;
  }
}

export function TikTokPixel() {
  const [hasConsent, setHasConsent] = useState(false);
  const [pixelLoaded, setPixelLoaded] = useState(false);

  useEffect(() => {
    // Check for cookie consent
    const consent = localStorage.getItem('cookie_consent');

    if (consent === 'accepted') {
      setHasConsent(true);
    } else if (consent === 'declined') {
      setHasConsent(false);
      // Revoke consent if pixel already loaded
      if (window.ttq) {
        window.ttq.revokeConsent();
      }
    }

    // Listen for consent changes
    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === 'cookie_consent') {
        if (e.newValue === 'accepted') {
          setHasConsent(true);
          if (window.ttq && pixelLoaded) {
            window.ttq.grantConsent();
            window.ttq.page();
          }
        } else if (e.newValue === 'declined') {
          setHasConsent(false);
          if (window.ttq) {
            window.ttq.revokeConsent();
          }
        }
      }
    };

    window.addEventListener('storage', handleStorageChange);
    return () => window.removeEventListener('storage', handleStorageChange);
  }, [pixelLoaded]);

  // Only load the pixel if consent is given
  if (!hasConsent) {
    return null;
  }

  return (
    <>
      <Script
        id="tiktok-pixel"
        strategy="afterInteractive"
        onLoad={() => {
          setPixelLoaded(true);
          if (window.ttq) {
            window.ttq.grantConsent();
          }
        }}
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
    </>
  );
}
