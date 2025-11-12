# Service Worker Caching Strategy

This document outlines the comprehensive caching strategy implemented for the SampleTok PWA.

## Overview

The service worker uses a multi-layered caching approach optimized for audio sample discovery:

1. **Cache-First**: For immutable assets that don't change
2. **Network-First**: For API calls that need fresh data
3. **Stale-While-Revalidate**: For resources that benefit from instant loading but should update in background

## Caching Strategies by Resource Type

### 1. API Routes (`api-cache`)
- **Strategy**: Network First
- **Timeout**: 10 seconds
- **Max Entries**: 100
- **Max Age**: 1 hour
- **Pattern**: `https://.*\.sampletok\.com/api/.*`

Attempts network request first with 10s timeout. Falls back to cache if network fails or is slow.

### 2. Audio Files (`audio-cache`)
- **Strategy**: Cache First
- **Max Entries**: 50
- **Max Age**: 30 days
- **Pattern**: `.mp3`, `.wav`, `.m3u8`, `.ts`
- **Range Requests**: Enabled

Audio files are cached aggressively for instant playback. Supports HTTP Range requests for seeking.

### 3. Images (`image-cache`)
- **Strategy**: Stale While Revalidate
- **Max Entries**: 150
- **Max Age**: 7 days
- **Pattern**: `.jpg`, `.jpeg`, `.png`, `.gif`, `.webp`, `.svg`, `.ico`

Serves from cache immediately while fetching fresh version in background.

### 4. CDN Assets (`cdn-cache`)
- **Strategy**: Cache First
- **Max Entries**: 200
- **Max Age**: 30 days
- **Pattern**: `https://.*\.r2\.dev/.*`

Cloudflare R2 assets cached aggressively since they're immutable.

### 5. Social Media Assets (`social-media-cache`)
- **Strategy**: Stale While Revalidate
- **Max Entries**: 100
- **Max Age**: 1 day
- **Pattern**: TikTok, Instagram, Facebook CDN URLs

Creator avatars and social media assets with shorter cache lifetime.

### 6. Static Assets (`static-assets`)
- **Strategy**: Cache First
- **Max Entries**: 100
- **Max Age**: 1 year
- **Pattern**: `.js`, `.css`, `.woff`, `.woff2`, `.ttf`, `.otf`, `.eot`

Font and stylesheet files cached for long periods.

### 7. Next.js Build Assets (`next-static`)
- **Strategy**: Cache First
- **Max Entries**: 200
- **Max Age**: 1 year
- **Pattern**: `/_next/(static|image).*`

Next.js build artifacts with content hashes cached permanently.

## Offline Fallback

### Offline Page
When the user is offline and navigates to a page that's not cached, they see:
- Custom branded offline page at `/offline.html`
- "You're Offline" message with retry button
- Automatic redirect when connection restored
- Online/offline status detection

### API Fallback
Failed API requests return:
```json
{
  "error": "offline",
  "message": "You are currently offline. Please check your connection."
}
```
Status: 503 Service Unavailable

### Image Fallback
Failed image requests return SVG placeholder with "Offline" text.

## Cache Size Limits

Total maximum cache entries across all caches:
- **Audio**: 50 files (~60MB)
- **Images**: 150 files (~30MB)
- **CDN**: 200 files (~100MB)
- **API**: 100 responses (~5MB)
- **Static**: 100 files (~20MB)
- **Social**: 100 files (~10MB)
- **Next.js**: 200 files (~50MB)

**Estimated Total**: ~275MB maximum cache size

## Testing the Service Worker

### Development Mode
Service worker is disabled in development to avoid caching issues:
```bash
npm run dev  # SW disabled
```

### Production Mode
Build and test with service worker enabled:
```bash
npm run build
npm start  # SW enabled
```

### Testing Offline Functionality

1. **Open DevTools**
   - Chrome: F12 → Application → Service Workers
   - Enable "Offline" checkbox

2. **Test Scenarios**
   - Navigate to pages (should show offline page)
   - Reload cached pages (should work)
   - Try API calls (should show offline error)
   - Play previously loaded audio (should work from cache)
   - View cached images (should display)

3. **Clear Cache**
   ```javascript
   // In browser console
   caches.keys().then(keys => {
     keys.forEach(key => caches.delete(key));
   });
   ```

## Custom Service Worker Features

The `sw-custom.js` file provides:

### 1. Offline Page Caching
Pre-caches offline page during install event.

### 2. Cache Cleanup
Removes old cache versions during activation.

### 3. Custom API Responses
Returns structured JSON errors for offline API calls.

### 4. Image Placeholders
Serves SVG placeholder for failed image requests.

### 5. Message Handling
Supports client-to-SW communication:
- `SKIP_WAITING`: Force SW activation
- `CACHE_URLS`: Pre-cache specific URLs
- `CLEAR_CACHE`: Clear all caches


## Performance Impact

### Cache Hit Rates (Expected)
- Audio files: ~90% (frequently replayed)
- Images: ~85% (creator avatars, waveforms)
- API calls: ~30% (fresh data needed)
- Static assets: ~95% (immutable)

### Load Time Improvements
- First load: No improvement
- Repeat visits: 60-80% faster
- Offline browsing: Cached pages instant
- Audio playback: <50ms from cache vs 200-500ms from network

## Troubleshooting

### Service Worker Not Updating
1. Unregister SW in DevTools
2. Clear all caches
3. Hard refresh (Cmd+Shift+R / Ctrl+Shift+F5)
4. Rebuild application

### Cache Not Working
1. Check console for SW errors
2. Verify SW registration successful
3. Check cache patterns match URLs
4. Test in production mode (not dev)

### Offline Page Not Showing
1. Verify `/offline.html` exists in `public/`
2. Check SW installed successfully
3. Test offline mode in DevTools
4. Verify fallbacks config in `next.config.mjs`

## Best Practices

1. **Always test in production mode** - SW disabled in dev
2. **Monitor cache size** - Stays under 500MB total
3. **Version cache names** - Force cache busting when needed
4. **Test offline scenarios** - Ensure graceful degradation
5. **Clear old caches** - Implement version-based cleanup

## Resources

- [Workbox Documentation](https://developer.chrome.com/docs/workbox/)
- [Service Worker API](https://developer.mozilla.org/en-US/docs/Web/API/Service_Worker_API)
- [PWA Best Practices](https://web.dev/pwa/)
- [Cache Storage API](https://developer.mozilla.org/en-US/docs/Web/API/Cache)
