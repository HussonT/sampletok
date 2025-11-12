// Custom Service Worker handlers for SampleTok PWA
// This file contains custom logic that extends the auto-generated service worker

// Cache names
const CACHE_VERSION = 'v1';
const OFFLINE_CACHE = `offline-${CACHE_VERSION}`;

// Install event - cache offline page
self.addEventListener('install', (event) => {
  console.log('[SW] Installing service worker...');

  event.waitUntil(
    caches.open(OFFLINE_CACHE).then((cache) => {
      console.log('[SW] Caching offline page');
      return cache.addAll([
        '/offline.html',
        '/icons/icon-192x192.png',
        '/manifest.json',
      ]);
    })
  );

  // Activate immediately
  self.skipWaiting();
});

// Activate event - cleanup old caches
self.addEventListener('activate', (event) => {
  console.log('[SW] Activating service worker...');

  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          // Delete old caches that don't match current version
          if (cacheName.startsWith('offline-') && cacheName !== OFFLINE_CACHE) {
            console.log('[SW] Deleting old cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    })
  );

  // Take control of all pages immediately
  return self.clients.claim();
});

// Fetch event - custom fallback logic
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET requests
  if (request.method !== 'GET') {
    return;
  }

  // Skip chrome-extension and other non-http(s) requests
  if (!url.protocol.startsWith('http')) {
    return;
  }

  // Custom handling for API requests
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(
      fetch(request)
        .catch(() => {
          // Return offline JSON response for API failures
          return new Response(
            JSON.stringify({
              error: 'offline',
              message: 'You are currently offline. Please check your connection.',
            }),
            {
              status: 503,
              statusText: 'Service Unavailable',
              headers: {
                'Content-Type': 'application/json',
              },
            }
          );
        })
    );
    return;
  }

  // For navigation requests, show offline page if network fails
  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request).catch(() => {
        return caches.match('/offline.html');
      })
    );
    return;
  }

  // For all other requests, try network first, then cache, then offline fallback
  event.respondWith(
    fetch(request)
      .then((response) => {
        // Clone the response before caching
        const responseToCache = response.clone();

        // Cache successful responses
        if (response.status === 200) {
          caches.open(OFFLINE_CACHE).then((cache) => {
            cache.put(request, responseToCache);
          });
        }

        return response;
      })
      .catch(() => {
        // Try to return from cache
        return caches.match(request).then((cachedResponse) => {
          if (cachedResponse) {
            return cachedResponse;
          }

          // If it's an image, return placeholder
          if (request.destination === 'image') {
            return new Response(
              '<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200"><rect width="200" height="200" fill="#2b2b2b"/><text x="50%" y="50%" text-anchor="middle" fill="#666" font-family="sans-serif" font-size="14">Offline</text></svg>',
              {
                headers: {
                  'Content-Type': 'image/svg+xml',
                  'Cache-Control': 'no-store',
                },
              }
            );
          }

          // Return offline page for documents
          return caches.match('/offline.html');
        });
      })
  );
});

// Listen for messages from clients
self.addEventListener('message', (event) => {
  console.log('[SW] Received message:', event.data);

  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }

  if (event.data && event.data.type === 'CACHE_URLS') {
    const urlsToCache = event.data.urls || [];
    event.waitUntil(
      caches.open(OFFLINE_CACHE).then((cache) => {
        return cache.addAll(urlsToCache);
      })
    );
  }

  if (event.data && event.data.type === 'CLEAR_CACHE') {
    event.waitUntil(
      caches.keys().then((cacheNames) => {
        return Promise.all(
          cacheNames.map((cacheName) => caches.delete(cacheName))
        );
      })
    );
  }
});

console.log('[SW] Custom service worker loaded');
