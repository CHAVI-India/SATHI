# PWA Service Worker Aggressive Caching Fix

## Problem

When visiting the front page of the site, users would see the service worker JavaScript code instead of the actual website. Only a hard refresh (Ctrl+F5) would load the proper site.

**Root Cause:**
The service worker was implementing an aggressive cache-first strategy that:
1. Cached an empty string (`''`) representing the root path during installation
2. Always served cached content for the homepage without checking for updates
3. Had no cache invalidation or versioning strategy
4. Never fetched fresh content from the network

## Solution Applied

### 1. Implemented Network-First Strategy for HTML Pages

Updated `/static/js/serviceworker.js` with a proper caching strategy:

**Key Changes:**
- **Cache Version**: Bumped from `djangopwa-v1` to `djangopwa-v2`
- **Network-First for HTML**: Homepage and all HTML pages now fetch from network first, with cache as fallback
- **Cache-First for Static Assets**: CSS, JS, images, fonts use cache-first for performance
- **Automatic Cache Cleanup**: Old cache versions are automatically deleted on activation
- **Immediate Activation**: `skipWaiting()` and `clients.claim()` ensure new service worker takes control immediately

### 2. Service Worker Lifecycle

```javascript
// Install: Don't cache homepage during install
self.addEventListener('install', function(event) {
  // Only cache specific static assets if needed
  self.skipWaiting(); // Activate immediately
});

// Activate: Clean up old caches
self.addEventListener('activate', function(event) {
  // Delete old cache versions
  self.clients.claim(); // Take control of all pages
});

// Fetch: Smart caching strategy
self.addEventListener('fetch', function(event) {
  // HTML pages: Network-first (always fresh)
  // Static assets: Cache-first (performance)
  // Everything else: Network only
});
```

### 3. Caching Strategies Explained

**Network-First (HTML Pages):**
1. Try to fetch from network
2. If successful, update cache and return fresh content
3. If network fails (offline), serve from cache
4. **Result**: Users always see the latest content when online

**Cache-First (Static Assets):**
1. Check cache first
2. If found, return cached version immediately
3. If not in cache, fetch from network and cache it
4. **Result**: Fast loading for CSS, JS, images

## Files Modified

1. `/static/js/serviceworker.js` - Updated service worker with proper caching strategy
2. `/staticfiles/js/serviceworker.js` - Updated compiled version
3. `/documentation/PWA_SERVICE_WORKER_CACHE_FIX.md` - This documentation

## Deployment Steps

After deploying these changes:

### 1. Clear Browser Service Worker Cache

Users may need to manually clear their service worker cache once:

**Chrome/Edge:**
1. Open DevTools (F12)
2. Go to Application tab → Service Workers
3. Click "Unregister" next to the old service worker
4. Click "Clear storage" → Clear site data
5. Refresh the page

**Firefox:**
1. Open DevTools (F12)
2. Go to Application tab → Service Workers
3. Click "Unregister"
4. Refresh the page

### 2. Automatic Update

The new service worker will automatically:
- Install itself when users visit the site
- Delete the old `djangopwa-v1` cache
- Take control of all pages immediately
- Start using the network-first strategy

### 3. Verify Fix

After deployment, verify the fix:

1. **Visit homepage** - Should load the actual site, not service worker code
2. **Check DevTools Console** - Should see: `Deleting old cache: djangopwa-v1`
3. **Check Network Tab** - Homepage requests should show `(from ServiceWorker)` but with fresh content
4. **Test Offline** - Disable network in DevTools, refresh should still work (from cache)

## Technical Details

### Why Network-First for HTML?

HTML pages (especially the homepage) contain:
- Dynamic content (user data, messages, notifications)
- Authentication state
- Session-specific information
- Real-time updates

These should always be fresh when online. Cache is only used as an offline fallback.

### Why Cache-First for Static Assets?

Static assets like CSS, JS, images:
- Don't change frequently
- Have versioned filenames (e.g., `main.abc123.css`)
- Can be safely cached for performance
- Reduce server load and bandwidth

### Cache Versioning

The cache version (`djangopwa-v2`) allows us to:
- Force cache invalidation when needed
- Clean up old cached content
- Deploy breaking changes safely
- Manage cache lifecycle

**Future Updates:**
When you need to force a cache refresh, increment the version:
```javascript
var staticCacheName = 'djangopwa-v3';
var oldCaches = ['djangopwa-v1', 'djangopwa-v2'];
```

## Troubleshooting

### Issue: Still Seeing Service Worker Code

**Solution:**
1. Hard refresh (Ctrl+F5 or Cmd+Shift+R)
2. Manually unregister old service worker in DevTools
3. Clear browser cache completely
4. Close and reopen browser

### Issue: Site Not Working Offline

**Solution:**
1. Check DevTools → Application → Service Workers → Status should be "Activated"
2. Visit the homepage while online first (to cache it)
3. Then test offline mode

### Issue: Static Assets Not Loading

**Solution:**
1. Check DevTools → Network tab for 404 errors
2. Run `python manage.py collectstatic` to ensure static files are collected
3. Verify `PWA_SERVICE_WORKER_PATH` in settings.py points to correct file

## Prevention

To prevent similar issues in the future:

1. **Never cache empty strings** - Always specify full URLs
2. **Use network-first for dynamic content** - HTML pages should be fresh
3. **Implement cache versioning** - Allow for cache invalidation
4. **Test service worker changes thoroughly** - Use DevTools to simulate offline/online
5. **Document caching strategies** - Make it clear what's cached and why

## Related Configuration

### Current PWA Settings (settings.py)

```python
PWA_SERVICE_WORKER_PATH = os.path.join(BASE_DIR, 'static/js', 'serviceworker.js')
PWA_APP_NAME = 'SATHI'
PWA_APP_DESCRIPTION = "Self Reported Assessment and Tracking for Health Insights"
PWA_APP_SCOPE = '/'
PWA_APP_START_URL = '/'
```

### CSP Configuration

Service worker requires these CSP directives (already configured):
```python
CSP_WORKER_SRC = ("'self'",)
CSP_MANIFEST_SRC = ("'self'",)
```

## References

- [MDN: Service Worker API](https://developer.mozilla.org/en-US/docs/Web/API/Service_Worker_API)
- [MDN: Using Service Workers](https://developer.mozilla.org/en-US/docs/Web/API/Service_Worker_API/Using_Service_Workers)
- [Service Worker Caching Strategies](https://developers.google.com/web/fundamentals/instant-and-offline/offline-cookbook)
- [django-pwa Documentation](https://github.com/silviolleite/django-pwa)
