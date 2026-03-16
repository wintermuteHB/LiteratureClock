// Literature Clock — Service Worker
// Offline-first: cache all assets, serve from cache, update in background

const CACHE_NAME = 'lit-clock-v1';
const ASSETS = [
  './',
  './index.html',
  './css/style.css',
  './js/clock.js',
  './data/quotes.json',
  './favicon.svg',
  './manifest.json',
];

// Install: pre-cache all assets
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(ASSETS))
  );
  self.skipWaiting();
});

// Activate: clean up old caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((key) => key !== CACHE_NAME)
          .map((key) => caches.delete(key))
      )
    )
  );
  self.clients.claim();
});

// Fetch: cache-first, network fallback, background update
self.addEventListener('fetch', (event) => {
  // Only handle same-origin requests (skip Google Fonts etc.)
  if (!event.request.url.startsWith(self.location.origin)) return;

  event.respondWith(
    caches.match(event.request).then((cached) => {
      // Return cached version immediately
      const fetchPromise = fetch(event.request)
        .then((response) => {
          // Update cache with fresh version
          if (response.ok) {
            const clone = response.clone();
            caches.open(CACHE_NAME).then((cache) => {
              cache.put(event.request, clone);
            });
          }
          return response;
        })
        .catch(() => cached); // Network failed, cached is all we have

      return cached || fetchPromise;
    })
  );
});
