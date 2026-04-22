Progressive Web App (PWA) Setup
=================================

Complete guide to configuring SATHI as a Progressive Web App with service workers and offline capabilities.

.. contents:: Table of Contents
   :local:
   :depth: 3

Overview
--------

SATHI is configured as a Progressive Web App (PWA) to provide:

- **Offline Access**: Continue using the app without internet
- **Install to Home Screen**: Native app-like experience
- **Fast Loading**: Cached resources for instant access
- **Background Sync**: Queue actions when offline
- **Push Notifications**: Engage users with updates (future)

PWA Components
--------------

SATHI's PWA implementation consists of:

1. **Web App Manifest**: Defines app metadata and appearance
2. **Service Worker**: Handles caching and offline functionality
3. **Content Security Policy**: Allows service worker registration
4. **HTTPS**: Required for service worker security

Web App Manifest
----------------

Configuration
~~~~~~~~~~~~~

The manifest is served by django-pwa at ``/manifest.json``.

**Settings Configuration:**

.. code-block:: python

    # chaviprom/settings.py
    
    INSTALLED_APPS = [
        # ... other apps
        'pwa',
    ]
    
    # PWA Configuration
    PWA_APP_NAME = 'SATHI'
    PWA_APP_DESCRIPTION = 'Self Reported Assessment and Tracking for Health Insights'
    PWA_APP_THEME_COLOR = '#0066cc'
    PWA_APP_BACKGROUND_COLOR = '#ffffff'
    PWA_APP_DISPLAY = 'standalone'
    PWA_APP_SCOPE = '/'
    PWA_APP_ORIENTATION = 'any'
    PWA_APP_START_URL = '/'
    PWA_APP_STATUS_BAR_COLOR = 'default'
    PWA_APP_ICONS = [
        {
            'src': '/static/images/icons/icon-72x72.png',
            'sizes': '72x72',
            'type': 'image/png'
        },
        {
            'src': '/static/images/icons/icon-96x96.png',
            'sizes': '96x96',
            'type': 'image/png'
        },
        {
            'src': '/static/images/icons/icon-128x128.png',
            'sizes': '128x128',
            'type': 'image/png'
        },
        {
            'src': '/static/images/icons/icon-144x144.png',
            'sizes': '144x144',
            'type': 'image/png'
        },
        {
            'src': '/static/images/icons/icon-152x152.png',
            'sizes': '152x152',
            'type': 'image/png'
        },
        {
            'src': '/static/images/icons/icon-192x192.png',
            'sizes': '192x192',
            'type': 'image/png'
        },
        {
            'src': '/static/images/icons/icon-384x384.png',
            'sizes': '384x384',
            'type': 'image/png'
        },
        {
            'src': '/static/images/icons/icon-512x512.png',
            'sizes': '512x512',
            'type': 'image/png'
        }
    ]
    PWA_APP_ICONS_APPLE = [
        {
            'src': '/static/images/icons/icon-152x152.png',
            'sizes': '152x152',
            'type': 'image/png'
        }
    ]
    PWA_APP_SPLASH_SCREEN = [
        {
            'src': '/static/images/icons/splash-640x1136.png',
            'media': '(device-width: 320px) and (device-height: 568px) and (-webkit-device-pixel-ratio: 2)'
        }
    ]
    PWA_APP_DIR = 'ltr'
    PWA_APP_LANG = 'en-US'

Template Integration
~~~~~~~~~~~~~~~~~~~~

Add manifest link to base template:

.. code-block:: html

    <!-- templates/base.html -->
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        
        <!-- PWA Manifest -->
        <link rel="manifest" href="{% url 'manifest' %}">
        
        <!-- Apple Touch Icons -->
        <link rel="apple-touch-icon" href="{% static 'images/icons/icon-152x152.png' %}">
        
        <!-- Theme Color -->
        <meta name="theme-color" content="#0066cc">
        
        <!-- ... rest of head -->
    </head>
    <body>
        <!-- ... content -->
    </body>
    </html>

Creating App Icons
~~~~~~~~~~~~~~~~~~

**Required Sizes:**

- 72x72, 96x96, 128x128, 144x144, 152x152, 192x192, 384x384, 512x512

**Generate Icons:**

.. code-block:: bash

    # Using ImageMagick
    convert logo.png -resize 72x72 icon-72x72.png
    convert logo.png -resize 96x96 icon-96x96.png
    convert logo.png -resize 128x128 icon-128x128.png
    convert logo.png -resize 144x144 icon-144x144.png
    convert logo.png -resize 152x152 icon-152x152.png
    convert logo.png -resize 192x192 icon-192x192.png
    convert logo.png -resize 384x384 icon-384x384.png
    convert logo.png -resize 512x512 icon-512x512.png

**Place icons in:**

.. code-block:: text

    static/images/icons/
    ├── icon-72x72.png
    ├── icon-96x96.png
    ├── icon-128x128.png
    ├── icon-144x144.png
    ├── icon-152x152.png
    ├── icon-192x192.png
    ├── icon-384x384.png
    └── icon-512x512.png

Service Worker
--------------

Service Worker Basics
~~~~~~~~~~~~~~~~~~~~~

A service worker is a JavaScript file that:

- Runs in the background, separate from web pages
- Intercepts network requests
- Manages caching strategies
- Enables offline functionality

**Requirements:**

1. **HTTPS**: Service workers only work on HTTPS (or localhost)
2. **CSP Permissions**: Content Security Policy must allow workers
3. **Proper Registration**: Must be registered from the main page

Service Worker File
~~~~~~~~~~~~~~~~~~~

Located at ``static/js/serviceworker.js``:

.. code-block:: javascript

    // Service Worker for SATHI PWA
    
    const CACHE_VERSION = 'djangopwa-v2';
    const CACHE_FILES = [
        '/static/css/output.css',
        '/static/js/htmx.min.js',
        // Add other critical static files
    ];
    
    // Install Event - Cache critical resources
    self.addEventListener('install', function(event) {
        console.log('[ServiceWorker] Installing...');
        
        event.waitUntil(
            caches.open(CACHE_VERSION)
                .then(cache => {
                    console.log('[ServiceWorker] Caching critical resources');
                    return cache.addAll(CACHE_FILES);
                })
        );
        
        // Activate immediately
        self.skipWaiting();
    });
    
    // Activate Event - Clean up old caches
    self.addEventListener('activate', function(event) {
        console.log('[ServiceWorker] Activating...');
        
        event.waitUntil(
            caches.keys().then(cacheNames => {
                return Promise.all(
                    cacheNames.map(cacheName => {
                        if (cacheName !== CACHE_VERSION) {
                            console.log('[ServiceWorker] Deleting old cache:', cacheName);
                            return caches.delete(cacheName);
                        }
                    })
                );
            })
        );
        
        // Take control of all pages immediately
        return self.clients.claim();
    });
    
    // Fetch Event - Implement caching strategies
    self.addEventListener('fetch', function(event) {
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
        
        event.respondWith(
            handleFetch(request)
        );
    });
    
    async function handleFetch(request) {
        const url = new URL(request.url);
        
        // Network-first strategy for HTML pages
        if (request.destination === 'document' || 
            request.headers.get('accept')?.includes('text/html')) {
            return networkFirst(request);
        }
        
        // Cache-first strategy for static assets
        if (request.destination === 'style' || 
            request.destination === 'script' ||
            request.destination === 'image' ||
            request.destination === 'font') {
            return cacheFirst(request);
        }
        
        // Network-only for everything else (API calls, etc.)
        return fetch(request);
    }
    
    // Network-first strategy
    async function networkFirst(request) {
        try {
            const response = await fetch(request);
            
            // Cache successful responses
            if (response.ok) {
                const cache = await caches.open(CACHE_VERSION);
                cache.put(request, response.clone());
            }
            
            return response;
        } catch (error) {
            // Fall back to cache if network fails
            const cached = await caches.match(request);
            if (cached) {
                return cached;
            }
            
            // Return offline page if available
            return caches.match('/offline.html') || 
                   new Response('Offline', { status: 503 });
        }
    }
    
    // Cache-first strategy
    async function cacheFirst(request) {
        const cached = await caches.match(request);
        
        if (cached) {
            return cached;
        }
        
        try {
            const response = await fetch(request);
            
            if (response.ok) {
                const cache = await caches.open(CACHE_VERSION);
                cache.put(request, response.clone());
            }
            
            return response;
        } catch (error) {
            return new Response('Network error', { status: 503 });
        }
    }

Service Worker Registration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Register the service worker in your base template:

.. code-block:: html

    <!-- templates/base.html -->
    <script>
        // Register Service Worker
        if ('serviceWorker' in navigator) {
            window.addEventListener('load', function() {
                navigator.serviceWorker.register('/serviceworker.js')
                    .then(function(registration) {
                        console.log('ServiceWorker registered:', registration.scope);
                    })
                    .catch(function(error) {
                        console.log('ServiceWorker registration failed:', error);
                    });
            });
        }
    </script>

Content Security Policy (CSP)
------------------------------

CSP Configuration
~~~~~~~~~~~~~~~~~

Service workers require specific CSP directives:

.. code-block:: python

    # chaviprom/settings.py
    
    # Content Security Policy
    CSP_DEFAULT_SRC = ("'self'",)
    CSP_SCRIPT_SRC = ("'self'", "'unsafe-inline'", "cdn.jsdelivr.net")
    CSP_STYLE_SRC = ("'self'", "'unsafe-inline'", "fonts.googleapis.com")
    CSP_FONT_SRC = ("'self'", "fonts.gstatic.com")
    CSP_IMG_SRC = ("'self'", "data:", "https:")
    CSP_CONNECT_SRC = ("'self'",)
    
    # CRITICAL: Service Worker and PWA support
    CSP_WORKER_SRC = ("'self'",)  # Allows service workers from same origin
    CSP_MANIFEST_SRC = ("'self'",)  # Allows manifest.json from same origin
    
    # For reCAPTCHA (if used)
    CSP_SCRIPT_SRC += ("https://www.google.com", "https://www.gstatic.com")
    CSP_FRAME_SRC = ("https://www.google.com",)

Common CSP Issues
~~~~~~~~~~~~~~~~~

**Service Worker Not Registering:**

.. code-block:: text

    Error: DOMException: The operation is insecure.

**Solution:**

1. Ensure HTTPS is enabled (or using localhost)
2. Add ``CSP_WORKER_SRC = ("'self'",)`` to settings
3. Add ``CSP_MANIFEST_SRC = ("'self'",)`` to settings
4. Clear browser cache and reload

**Manifest Not Loading:**

.. code-block:: text

    Error: Manifest: Line 1, column 1, Syntax error.

**Solution:**

1. Use Django URL tag: ``{% url 'manifest' %}``
2. Don't hardcode ``/manifest.json``
3. Ensure django-pwa is in INSTALLED_APPS

Caching Strategies
------------------

Network-First Strategy
~~~~~~~~~~~~~~~~~~~~~~

**Best for:** HTML pages, dynamic content

**How it works:**

1. Try to fetch from network
2. If successful, cache the response
3. If network fails, serve from cache
4. If no cache, show offline page

**Use cases:**

- Main application pages
- User dashboards
- Dynamic content that changes frequently

.. code-block:: javascript

    async function networkFirst(request) {
        try {
            const response = await fetch(request);
            if (response.ok) {
                const cache = await caches.open(CACHE_VERSION);
                cache.put(request, response.clone());
            }
            return response;
        } catch (error) {
            return await caches.match(request) || 
                   await caches.match('/offline.html');
        }
    }

Cache-First Strategy
~~~~~~~~~~~~~~~~~~~~~

**Best for:** Static assets (CSS, JS, images, fonts)

**How it works:**

1. Check cache first
2. If found, return cached version
3. If not cached, fetch from network
4. Cache the response for next time

**Use cases:**

- CSS files
- JavaScript files
- Images
- Fonts
- Static resources

.. code-block:: javascript

    async function cacheFirst(request) {
        const cached = await caches.match(request);
        if (cached) {
            return cached;
        }
        
        const response = await fetch(request);
        if (response.ok) {
            const cache = await caches.open(CACHE_VERSION);
            cache.put(request, response.clone());
        }
        return response;
    }

Network-Only Strategy
~~~~~~~~~~~~~~~~~~~~~~

**Best for:** API calls, form submissions, real-time data

**How it works:**

1. Always fetch from network
2. Never cache
3. Fail if network unavailable

**Use cases:**

- POST/PUT/DELETE requests
- API endpoints
- Authentication requests
- Real-time data

.. code-block:: javascript

    function networkOnly(request) {
        return fetch(request);
    }

Cache Management
----------------

Cache Versioning
~~~~~~~~~~~~~~~~

Update cache version when deploying changes:

.. code-block:: javascript

    // Increment version on each deployment
    const CACHE_VERSION = 'djangopwa-v3';  // Changed from v2

**Old caches are automatically deleted on activation.**

Manual Cache Clearing
~~~~~~~~~~~~~~~~~~~~~

Clear all caches programmatically:

.. code-block:: javascript

    // In browser console or admin page
    caches.keys().then(cacheNames => {
        cacheNames.forEach(cacheName => {
            caches.delete(cacheName);
        });
    });

Cache Size Limits
~~~~~~~~~~~~~~~~~

**Browser Limits:**

- Chrome: ~6% of free disk space
- Firefox: ~10% of free disk space
- Safari: ~50MB

**Best Practices:**

- Cache only essential resources
- Use cache-first for static assets only
- Implement cache expiration
- Monitor cache size

Offline Support
---------------

Offline Page
~~~~~~~~~~~~

Create a dedicated offline page:

.. code-block:: html

    <!-- templates/offline.html -->
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Offline - SATHI</title>
        <style>
            body {
                font-family: system-ui, -apple-system, sans-serif;
                display: flex;
                align-items: center;
                justify-content: center;
                min-height: 100vh;
                margin: 0;
                background: #f3f4f6;
            }
            .offline-container {
                text-align: center;
                padding: 2rem;
            }
            h1 {
                color: #1f2937;
                margin-bottom: 1rem;
            }
            p {
                color: #6b7280;
                margin-bottom: 2rem;
            }
            button {
                background: #0066cc;
                color: white;
                border: none;
                padding: 0.75rem 1.5rem;
                border-radius: 0.5rem;
                cursor: pointer;
                font-size: 1rem;
            }
            button:hover {
                background: #0052a3;
            }
        </style>
    </head>
    <body>
        <div class="offline-container">
            <h1>You're Offline</h1>
            <p>Please check your internet connection and try again.</p>
            <button onclick="window.location.reload()">Retry</button>
        </div>
    </body>
    </html>

**Cache offline page in service worker:**

.. code-block:: javascript

    const CACHE_FILES = [
        '/offline.html',
        // ... other files
    ];

Background Sync (Future)
~~~~~~~~~~~~~~~~~~~~~~~~~

Queue form submissions when offline:

.. code-block:: javascript

    // Register background sync
    self.addEventListener('sync', function(event) {
        if (event.tag === 'sync-questionnaires') {
            event.waitUntil(syncQuestionnaires());
        }
    });
    
    async function syncQuestionnaires() {
        // Get queued submissions from IndexedDB
        // Send to server when online
        // Clear queue on success
    }

Testing
-------

Test on Localhost
~~~~~~~~~~~~~~~~~

Service workers work on localhost without HTTPS:

.. code-block:: bash

    python manage.py runserver

**Open:** http://localhost:8000

**Check DevTools:**

1. Open Chrome DevTools (F12)
2. Go to Application tab
3. Click Service Workers
4. Verify registration

Test on HTTPS
~~~~~~~~~~~~~

For production testing:

1. Deploy to HTTPS server
2. Open in browser
3. Check DevTools → Application → Service Workers
4. Verify manifest loaded
5. Test offline mode

Simulate Offline
~~~~~~~~~~~~~~~~

**Chrome DevTools:**

1. Open DevTools (F12)
2. Go to Network tab
3. Select "Offline" from throttling dropdown
4. Reload page
5. Verify offline page appears

**Firefox:**

1. Open DevTools (F12)
2. Go to Network tab
3. Check "Offline" checkbox
4. Reload page

Install to Home Screen
~~~~~~~~~~~~~~~~~~~~~~

**Android Chrome:**

1. Open site in Chrome
2. Tap menu (⋮)
3. Select "Add to Home screen"
4. Confirm installation

**iOS Safari:**

1. Open site in Safari
2. Tap Share button
3. Select "Add to Home Screen"
4. Confirm installation

Troubleshooting
---------------

Common Issues
~~~~~~~~~~~~~

**Service Worker Not Registering**

.. code-block:: text

    Error: DOMException: The operation is insecure.

**Solutions:**

1. Enable HTTPS or use localhost
2. Check CSP headers include ``worker-src 'self'``
3. Verify service worker file is accessible
4. Clear browser cache

**Manifest Not Loading**

.. code-block:: text

    Error: Manifest: Line 1, column 1, Syntax error.

**Solutions:**

1. Use ``{% url 'manifest' %}`` not ``/manifest.json``
2. Ensure django-pwa is installed
3. Check manifest URL in browser
4. Verify JSON syntax

**Caching Issues**

**Problem:** Old content showing after deployment

**Solutions:**

1. Increment ``CACHE_VERSION``
2. Clear browser cache
3. Unregister old service worker
4. Force refresh (Ctrl+Shift+R)

**Install Prompt Not Showing**

**Requirements:**

1. HTTPS enabled
2. Valid manifest.json
3. Service worker registered
4. Icons in correct sizes
5. User hasn't dismissed prompt before

Debugging Tools
~~~~~~~~~~~~~~~

**Chrome DevTools:**

- Application → Service Workers
- Application → Manifest
- Application → Cache Storage
- Network → Offline simulation

**Firefox DevTools:**

- Application → Service Workers
- Application → Manifest
- Storage → Cache Storage

**Lighthouse Audit:**

.. code-block:: bash

    # Run PWA audit
    lighthouse https://your-site.com --view

Best Practices
--------------

Performance
~~~~~~~~~~~

- Cache only essential resources
- Use cache-first for static assets
- Implement network-first for dynamic content
- Set appropriate cache expiration
- Monitor cache size

Security
~~~~~~~~

- Always use HTTPS in production
- Validate cached responses
- Implement CSP headers
- Sanitize user input before caching
- Don't cache sensitive data

User Experience
~~~~~~~~~~~~~~~

- Provide clear offline messaging
- Show loading states
- Handle failed requests gracefully
- Allow manual cache clearing
- Test on slow connections

Resources
---------

- `Service Worker API <https://developer.mozilla.org/en-US/docs/Web/API/Service_Worker_API>`_
- `Web App Manifest <https://developer.mozilla.org/en-US/docs/Web/Manifest>`_
- `PWA Builder <https://www.pwabuilder.com/>`_
- `Workbox (Google's PWA Library) <https://developers.google.com/web/tools/workbox>`_
- `django-pwa Documentation <https://github.com/silviolleite/django-pwa>`_
