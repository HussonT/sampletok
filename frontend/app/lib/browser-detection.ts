/**
 * Browser Detection Utilities
 *
 * Detects in-app browsers (TikTok, Instagram, Facebook, etc.) that may have
 * limited functionality or different media playback behavior.
 */

export function isTikTokBrowser(): boolean {
  if (typeof window === 'undefined') return false;

  const userAgent = window.navigator.userAgent.toLowerCase();

  // TikTok uses BytedanceWebview or has 'tiktok' in the user agent
  return userAgent.includes('bytedancewebview') ||
         userAgent.includes('tiktok') ||
         userAgent.includes('musical_ly'); // TikTok's original name
}

export function isInstagramBrowser(): boolean {
  if (typeof window === 'undefined') return false;

  const userAgent = window.navigator.userAgent.toLowerCase();
  return userAgent.includes('instagram');
}

export function isFacebookBrowser(): boolean {
  if (typeof window === 'undefined') return false;

  const userAgent = window.navigator.userAgent.toLowerCase();
  return userAgent.includes('fban') || userAgent.includes('fbav');
}

export function isInAppBrowser(): boolean {
  return isTikTokBrowser() || isInstagramBrowser() || isFacebookBrowser();
}

export function getBrowserName(): string {
  if (isTikTokBrowser()) return 'TikTok';
  if (isInstagramBrowser()) return 'Instagram';
  if (isFacebookBrowser()) return 'Facebook';
  return 'Browser';
}

/**
 * Opens the current URL in the device's default browser
 * Works on iOS and Android
 */
export function openInDefaultBrowser(): void {
  if (typeof window === 'undefined') return;

  const currentUrl = window.location.href;

  // Try to open in default browser
  // This works by creating a link that the in-app browser will handle
  const link = document.createElement('a');
  link.href = currentUrl;
  link.target = '_blank';
  link.rel = 'noopener noreferrer';

  // Trigger click
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}
