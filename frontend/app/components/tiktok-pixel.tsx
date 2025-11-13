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
    console.log('[TikTok Pixel] Cookie consent status:', consent);

    if (consent === 'accepted') {
      console.log('[TikTok Pixel] Consent accepted, loading pixel');
      setHasConsent(true);
    } else if (consent === 'declined') {
      console.log('[TikTok Pixel] Consent declined');
      setHasConsent(false);
      // Revoke consent if pixel already loaded
      if (window.ttq) {
        window.ttq.revokeConsent();
      }
    } else {
      console.log('[TikTok Pixel] No consent yet, waiting for user action');
    }

    // Listen for consent changes via custom event
    const handleConsentChange = (e: Event) => {
      const customEvent = e as CustomEvent;
      console.log('[TikTok Pixel] Consent changed to:', customEvent.detail);
      if (customEvent.detail === 'accepted') {
        setHasConsent(true);
        // Force reload if pixel was already loaded
        if (window.ttq && pixelLoaded) {
          window.ttq.grantConsent();
          window.ttq.page();
          console.log('[TikTok Pixel] Granted consent and triggered page view');
        }
      } else if (customEvent.detail === 'declined') {
        setHasConsent(false);
        if (window.ttq) {
          window.ttq.revokeConsent();
        }
      }
    };

    window.addEventListener('cookieConsentChanged', handleConsentChange);
    return () => window.removeEventListener('cookieConsentChanged', handleConsentChange);
  }, [pixelLoaded]);

  // Only load the pixel if consent is given
  if (!hasConsent) {
    console.log('[TikTok Pixel] Not rendering script - no consent');
    return null;
  }

  console.log('[TikTok Pixel] Rendering script with consent');

  return (
    <>
      <Script
        id="tiktok-pixel"
        strategy="beforeInteractive"
        onLoad={() => {
          console.log('[TikTok Pixel] Script loaded successfully');
          setPixelLoaded(true);
          if (window.ttq) {
            console.log('[TikTok Pixel] ttq object available:', window.ttq);
            window.ttq.grantConsent();
            console.log('[TikTok Pixel] Consent granted via API');
          }
        }}
        onError={(e) => {
          console.error('[TikTok Pixel] Script loading error:', e);
        }}
        dangerouslySetInnerHTML={{
          __html: `
console.log('[TikTok Pixel] Initializing pixel code');
!function (w, d, t) {
  w.TiktokAnalyticsObject=t;var ttq=w[t]=w[t]||[];ttq.methods=["page","track","identify","instances","debug","on","off","once","ready","alias","group","enableCookie","disableCookie","holdConsent","revokeConsent","grantConsent"],ttq.setAndDefer=function(t,e){t[e]=function(){t.push([e].concat(Array.prototype.slice.call(arguments,0)))}};for(var i=0;i<ttq.methods.length;i++)ttq.setAndDefer(ttq,ttq.methods[i]);ttq.instance=function(t){for(
var e=ttq._i[t]||[],n=0;n<ttq.methods.length;n++)ttq.setAndDefer(e,ttq.methods[n]);return e},ttq.load=function(e,n){var r="https://analytics.tiktok.com/i18n/pixel/events.js",o=n&&n.partner;ttq._i=ttq._i||{},ttq._i[e]=[],ttq._i[e]._u=r,ttq._t=ttq._t||{},ttq._t[e]=+new Date,ttq._o=ttq._o||{},ttq._o[e]=n||{};n=document.createElement("script")
;n.type="text/javascript",n.async=!0,n.src=r+"?sdkid="+e+"&lib="+t;e=document.getElementsByTagName("script")[0];e.parentNode.insertBefore(n,e)};

  console.log('[TikTok Pixel] Loading pixel with ID: D4B3ABJC77UCI3HO33M0');
  ttq.load('D4B3ABJC77UCI3HO33M0');
  console.log('[TikTok Pixel] Triggering initial page view');
  ttq.page();
  console.log('[TikTok Pixel] Initialization complete, ttq object:', ttq);
}(window, document, 'ttq');
          `,
        }}
      />
    </>
  );
}
