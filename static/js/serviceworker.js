var staticCacheName = 'djangopwa-v2';
var oldCaches = ['djangopwa-v1'];

// Install event - skip caching homepage during install
self.addEventListener('install', function(event) {
  event.waitUntil(
    caches.open(staticCacheName).then(function(cache) {
      // Cache static assets only, not the homepage
      return cache.addAll([
        // Add specific static assets here if needed
        // e.g., '/static/css/main.css', '/static/js/app.js'
      ]);
    })
  );
  // Force the waiting service worker to become the active service worker
  self.skipWaiting();
});

// Activate event - clean up old caches
self.addEventListener('activate', function(event) {
  event.waitUntil(
    caches.keys().then(function(cacheNames) {
      return Promise.all(
        cacheNames.map(function(cacheName) {
          if (oldCaches.indexOf(cacheName) !== -1 || (cacheName !== staticCacheName && cacheName.startsWith('djangopwa-'))) {
            console.log('Deleting old cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    }).then(function() {
      // Take control of all pages immediately
      return self.clients.claim();
    })
  );
});

// Fetch event - network-first strategy for HTML, cache-first for static assets
self.addEventListener('fetch', function(event) {
  var requestUrl = new URL(event.request.url);
  
  // Network-first strategy for HTML pages (including homepage)
  if (requestUrl.origin === location.origin && 
      (event.request.headers.get('accept').includes('text/html') || requestUrl.pathname === '/')) {
    event.respondWith(
      fetch(event.request)
        .then(function(response) {
          // Clone the response before caching
          var responseToCache = response.clone();
          caches.open(staticCacheName).then(function(cache) {
            cache.put(event.request, responseToCache);
          });
          return response;
        })
        .catch(function() {
          // Fallback to cache if network fails
          return caches.match(event.request);
        })
    );
    return;
  }
  
  // Cache-first strategy for static assets (CSS, JS, images)
  if (requestUrl.origin === location.origin && 
      (requestUrl.pathname.startsWith('/static/') || 
       requestUrl.pathname.match(/\.(css|js|png|jpg|jpeg|gif|svg|woff|woff2|ttf|eot)$/))) {
    event.respondWith(
      caches.match(event.request).then(function(response) {
        return response || fetch(event.request).then(function(fetchResponse) {
          return caches.open(staticCacheName).then(function(cache) {
            cache.put(event.request, fetchResponse.clone());
            return fetchResponse;
          });
        });
      })
    );
    return;
  }
  
  // For everything else, just fetch from network
  event.respondWith(fetch(event.request));
});