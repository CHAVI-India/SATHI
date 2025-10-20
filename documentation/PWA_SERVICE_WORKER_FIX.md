# PWA Service Worker "Insecure Operation" Error Fix

## Problem

Console error in production (HTTPS environment):
```
django-pwa: ServiceWorker registration failed: DOMException: The operation is insecure.
```

## Root Cause

The error occurs due to **missing `Service-Worker-Allowed` HTTP header** when serving the service worker file. This is the primary issue. Additionally, CSP headers need proper configuration.

Service Workers require:
1. **Secure context** (HTTPS or localhost) ✓ Already configured
2. **`Service-Worker-Allowed` HTTP header** ✗ Was missing (CRITICAL)
3. **CSP permissions** for `worker-src` ✗ Was missing
4. **CSP permissions** for `manifest-src` ✗ Was missing

### Why `Service-Worker-Allowed` is Critical

When a service worker is registered with a scope (e.g., `/`), the browser checks:
1. Is the origin secure (HTTPS)?
2. Does the `Service-Worker-Allowed` header permit this scope?

Without this header, the browser restricts the service worker to only control URLs in the same directory as the service worker file itself. Since we want it to control the entire site (`scope: '/'`), we **must** include this header.

## Solution Applied

### 1. **Added Custom Service Worker View with Required Header** (CRITICAL FIX)

Created custom view in `/chaviprom/views.py`:

```python
def service_worker_view(request):
    """
    Custom service worker view that adds the Service-Worker-Allowed header.
    This header is required to allow the service worker to control the root scope.
    """
    sw_path = settings.PWA_SERVICE_WORKER_PATH
    
    try:
        with open(sw_path, 'r') as f:
            content = f.read()
        
        response = HttpResponse(content, content_type='application/javascript')
        # Allow service worker to control the entire site (root scope)
        response['Service-Worker-Allowed'] = '/'
        # Cache control for service worker updates
        response['Cache-Control'] = 'max-age=0, no-cache, no-store, must-revalidate'
        return response
    except FileNotFoundError:
        return HttpResponse('Service Worker not found', status=404)
```

**Key headers added:**
- **`Service-Worker-Allowed: /`** - Allows service worker to control entire site
- **`Cache-Control: max-age=0, no-cache`** - Ensures service worker updates are fetched immediately

### 2. **Updated URL Configuration**

Modified `/chaviprom/urls.py` to use custom view:

```python
from chaviprom.views import IndexView, service_worker_view

urlpatterns = [
    path('i18n/', include('django.conf.urls.i18n')),
    # Custom service worker with Service-Worker-Allowed header
    path('serviceworker.js', service_worker_view, name='serviceworker'),
]
```

This overrides the default django-pwa service worker URL to add the required header.

### 3. **Added CSP Directives for Service Workers**

Updated `/chaviprom/settings.py` to include:

```python
# Service Worker and Web Worker support
CSP_WORKER_SRC = ("'self'",)  # Allow service workers from same origin
CSP_MANIFEST_SRC = ("'self'",)  # Allow manifest.json from same origin
```

These directives tell the browser's Content Security Policy to allow:
- Service Workers to be loaded from the same origin (`worker-src`)
- The PWA manifest file to be loaded (`manifest-src`)

### 4. **Fixed Manifest URL in Base Template**

Updated `/templates/base.html`:

```html
<!-- Before -->
<link rel="manifest" href="manifest.json">

<!-- After -->
<link rel="manifest" href="{% url 'manifest' %}">
```

This ensures the manifest URL is properly resolved through Django's URL routing.

## Verification Steps

After deploying these changes:

1. **Check Service-Worker-Allowed Header** (MOST IMPORTANT):
   ```bash
   curl -I https://your-domain.com/serviceworker.js
   ```
   Should include:
   ```
   Service-Worker-Allowed: /
   Content-Type: application/javascript
   Cache-Control: max-age=0, no-cache, no-store, must-revalidate
   ```

2. **Check Service Worker Registration**: Open browser DevTools → Console → Should see:
   ```
   Service Worker registered successfully
   ```
   (No "insecure operation" error)

3. **Check Application Tab**: DevTools → Application → Service Workers → Should show:
   - Status: Activated and running
   - Source: /serviceworker.js
   - Scope: / (entire site)

4. **Check CSP Headers**: DevTools → Network tab → Select any page load → Check Response Headers for:
   ```
   Content-Security-Policy: ... worker-src 'self'; manifest-src 'self'; ...
   ```

5. **Check Manifest**: DevTools → Application → Manifest → Should display PWA configuration without errors

## Technical Details

### Why CSP Blocks Service Workers

Content Security Policy (CSP) is a security standard that helps prevent XSS attacks by controlling which resources can be loaded. Without explicit permission via `worker-src`, browsers will block Service Worker registration even on HTTPS.

### CSP Directives Explained

- **`worker-src 'self'`**: Allows Web Workers and Service Workers from the same origin
- **`manifest-src 'self'`**: Allows the PWA manifest file from the same origin
- **`'self'`**: Restricts to same-origin only (secure default)

### Production vs Development

The CSP configuration applies to both environments:
- **Production**: Full CSP enforcement with HTTPS
- **Development**: CSP active but with `CSP_UPGRADE_INSECURE_REQUESTS = False`

Service Workers work in development only on:
- `localhost`
- `127.0.0.1`
- HTTPS connections

## Related Configuration

### Current PWA Settings (settings.py)

```python
PWA_SERVICE_WORKER_PATH = os.path.join(BASE_DIR, 'static/js', 'serviceworker.js')
PWA_APP_NAME = 'SATHI'
PWA_APP_DESCRIPTION = "Self Reported Assessment and Tracking for Health Insights"
PWA_APP_SCOPE = '/'
PWA_APP_START_URL = '/'
```

### Security Settings (Production)

```python
if ENVIRONMENT != 'development':
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    CSP_UPGRADE_INSECURE_REQUESTS = True
    CSP_BLOCK_ALL_MIXED_CONTENT = True
```

## Troubleshooting

### If Service Worker Still Fails

1. **Clear browser cache and service workers**:
   - DevTools → Application → Service Workers → Unregister
   - DevTools → Application → Storage → Clear site data

2. **Check HTTPS configuration**:
   ```bash
   # Verify HTTPS is properly configured
   curl -I https://your-domain.com
   ```

3. **Verify CSP headers are applied**:
   ```bash
   curl -I https://your-domain.com | grep -i content-security-policy
   ```

4. **Check for mixed content**:
   - DevTools → Console → Look for mixed content warnings
   - All resources must be loaded over HTTPS

5. **Verify service worker file is accessible**:
   ```bash
   curl https://your-domain.com/serviceworker.js
   ```

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| "Insecure operation" | Missing `Service-Worker-Allowed` header | Use custom view with header (see solution above) |
| "Insecure operation" (secondary) | Missing CSP directives | Add `CSP_WORKER_SRC` and `CSP_MANIFEST_SRC` |
| Scope restriction error | Service worker can't control root | Add `Service-Worker-Allowed: /` header |
| 404 on serviceworker.js | URL not configured | Add custom URL pattern before pwa.urls |
| Service worker file not found | Wrong path in settings | Verify `PWA_SERVICE_WORKER_PATH` points to correct file |
| Manifest not loading | Wrong URL format | Use `{% url 'manifest' %}` |
| Mixed content errors | HTTP resources on HTTPS page | Ensure all resources use HTTPS |

## Files Modified

1. **`/chaviprom/views.py`** - Added custom `service_worker_view()` with `Service-Worker-Allowed` header (CRITICAL)
2. **`/chaviprom/urls.py`** - Added custom service worker URL pattern to override django-pwa default
3. **`/chaviprom/settings.py`** - Added CSP directives (`CSP_WORKER_SRC`, `CSP_MANIFEST_SRC`)
4. **`/templates/base.html`** - Fixed manifest URL reference
5. **`/documentation/PWA_SERVICE_WORKER_FIX.md`** - This documentation

## References

- [MDN: Service Worker API](https://developer.mozilla.org/en-US/docs/Web/API/Service_Worker_API)
- [MDN: Content Security Policy](https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP)
- [CSP worker-src directive](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Content-Security-Policy/worker-src)
- [django-pwa documentation](https://github.com/silviolleite/django-pwa)
