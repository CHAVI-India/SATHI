# Celery Integration for Parallel Plot Loading

## Overview

This document outlines the plan to integrate Celery for parallel plot generation on the PRO Review page (`prom_review.html`), replacing the current sequential loading approach.

---

## Current Architecture

### Request Flow

1. **Page Load**: `prom_review.html` loads with placeholder divs for plots
2. **JavaScript Initialization**: `initializePlotProgressLoader()` runs on `DOMContentLoaded`
3. **Sequential Loading**: `startSequentialLoading()` loads plots in 3 phases:
   - Phase 1: Topline + Composite construct plots
   - Phase 2: Other construct plots
   - Phase 3: Item response plots
4. **Per-Plot Fetch**: `loadSinglePlot()` makes individual `fetch()` requests **sequentially** (awaits each)

### Key Files

| File | Purpose |
|------|---------|
| `templates/promapp/prom_review.html` | Main page with JS plot loader (lines 175-522) |
| `patientapp/views.py` | Plot endpoints: `prom_review_construct_plot` (line 1005), `prom_review_composite_plot` (line 1250), `prom_review_item_plot` (line 1391) |
| `patientapp/utils.py` | Plot generation: `ConstructScoreData._create_bokeh_plot()` (line 804), `create_item_response_plot()` (line 1543) |
| `templates/promapp/partials/construct_plot.html` | Returns `{{ score_data.bokeh_plot|safe }}` |
| `templates/promapp/partials/item_plot.html` | Returns `{{ bokeh_plot|safe }}` |

### Current Bottleneck

```javascript
// prom_review.html lines 415-417
for (const plot of plotsToLoad) {
    await loadSinglePlot(plot);  // BLOCKS until complete
}
```

Each plot waits for the previous one to finish. With N plots, total time ≈ N × (aggregation_time + plot_render_time).

### Backend Timing (from response headers)

- `X-Timing-Aggregation`: Time spent calculating aggregation statistics (~100-300ms per plot)
- `X-Timing-Plot`: Time spent rendering Bokeh plot (~10-50ms per plot)

---

## Proposed Architecture with Celery

### High-Level Flow

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Browser       │     │   Django        │     │   Celery        │
│   (Frontend)    │     │   (Backend)     │     │   (Workers)     │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                       │
         │  1. POST /dispatch-plots                      │
         │  (all plot params)    │                       │
         │──────────────────────>│                       │
         │                       │  2. Queue N tasks     │
         │                       │──────────────────────>│
         │  3. Return task_ids   │                       │
         │<──────────────────────│                       │
         │                       │                       │
         │  4. Poll /task-status │                       │
         │  (batch of task_ids)  │  3. Execute in        │
         │──────────────────────>│     parallel          │
         │                       │<─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─│
         │  5. Return completed  │                       │
         │     results (HTML)    │                       │
         │<──────────────────────│                       │
         │                       │                       │
         │  6. Render plots as   │                       │
         │     they complete     │                       │
         ▼                       ▼                       ▼
```

### Implementation Steps

#### Step 1: Celery Configuration

Create `chaviprom/celery.py`:
```python
import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chaviprom.settings')

app = Celery('chaviprom')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
```

Update `chaviprom/__init__.py`:
```python
from .celery import app as celery_app
__all__ = ('celery_app',)
```

Add to `chaviprom/settings.py`:
```python
INSTALLED_APPS = [
    # ... existing apps ...
    'celery_progress',  # Add this for progress tracking
]

# Celery Configuration
# Using RabbitMQ as message broker
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'amqp://guest:guest@localhost:5672//')

# Using Django database as result backend (via django_celery_results)
CELERY_RESULT_BACKEND = 'django-db'

CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
```

Add to `chaviprom/urls.py`:
```python
from django.urls import path, include

urlpatterns = [
    # ... existing patterns ...
    path('celery-progress/', include('celery_progress.urls')),  # Progress tracking endpoint
]
```

#### Step 2: Create Celery Tasks

Create `patientapp/tasks.py`:
```python
from celery import shared_task
from django.template.loader import render_to_string

from celery_progress.backend import ProgressRecorder

@shared_task(bind=True)
def generate_plots_batch_task(self, patient_id, plots, filters):
    """
    Generate multiple plots in a single task with progress tracking.
    
    Args:
        patient_id: UUID of the patient
        plots: List of {'type': 'construct'|'composite'|'item', 'id': uuid}
        filters: Dict of filter parameters
    
    Returns:
        List of {'plot_id': uuid, 'plot_type': str, 'html': str, 'metadata': dict}
    """
    progress_recorder = ProgressRecorder(self)
    results = []
    
    for i, plot in enumerate(plots):
        # Update progress
        progress_recorder.set_progress(
            i + 1, 
            len(plots), 
            description=f"Generating {plot['type']} plot {i + 1}/{len(plots)}"
        )
        
        # Generate plot based on type
        if plot['type'] == 'construct':
            html, metadata = generate_construct_plot(patient_id, plot['id'], filters)
        elif plot['type'] == 'composite':
            html, metadata = generate_composite_plot(patient_id, plot['id'], filters)
        elif plot['type'] == 'item':
            html, metadata = generate_item_plot(patient_id, plot['id'], filters)
        
        results.append({
            'plot_id': str(plot['id']),
            'plot_type': plot['type'],
            'html': html,
            'metadata': metadata
        })
    
    return results

def generate_construct_plot(patient_id, construct_id, filters):
    """Generate a single construct plot and return (HTML, metadata)."""
    # Extract logic from prom_review_construct_plot view
    pass

def generate_composite_plot(patient_id, composite_id, filters):
    """Generate a single composite plot and return (HTML, metadata)."""
    pass

def generate_item_plot(patient_id, item_id, filters):
    """Generate a single item plot and return (HTML, metadata)."""
    pass
```

#### Step 3: Create API Endpoints

Add to `patientapp/views.py`:
```python
@login_required
def dispatch_plot_tasks(request, pk):
    """Dispatch all plot generation tasks to Celery and return task IDs."""
    # Parse plot list from request
    # Queue tasks for each plot
    # Return JSON: {'tasks': [{'id': task_id, 'plot_type': 'construct', 'plot_id': uuid}, ...]}
    pass

@login_required
def check_plot_tasks(request):
    """Check status of multiple tasks and return completed results."""
    # Accept list of task_ids
    # Return JSON: {'completed': [{'task_id': id, 'html': '...', 'metadata': {...}}, ...], 'pending': [...]}
    pass
```

#### Step 4: Update Frontend JavaScript

Add the celery-progress JavaScript library to `prom_review.html`:
```html
{% block extra_js %}
<script src="{% static 'celery_progress/celery_progress.js' %}"></script>
{% endblock %}
```

Replace sequential loading in `prom_review.html`:
```javascript
async function startParallelLoading() {
    // 1. Collect all plots to load
    const plots = collectAllPendingPlots();
    
    // 2. Dispatch batch task
    const response = await fetch('/patients/{pk}/prom-review/dispatch-plots/', {
        method: 'POST',
        headers: {'Content-Type': 'application/json', 'X-CSRFToken': csrfToken},
        body: JSON.stringify({plots: plots, filters: getCurrentFilters()})
    });
    const {task_id} = await response.json();
    
    // 3. Use celery-progress library for progress tracking
    const progressUrl = `/celery-progress/${task_id}/`;
    
    CeleryProgressBar.initProgressBar(progressUrl, {
        // Called on each progress update
        onProgress: function(progressBarElement, progressBarMessageElement, progress) {
            const percent = Math.round((progress.current / progress.total) * 100);
            updateProgressUI(percent, progress.current, progress.total, progress.description);
        },
        
        // Called when task completes successfully
        onSuccess: function(progressBarElement, progressBarMessageElement, result) {
            // Render all completed plots
            for (const plotResult of result) {
                renderPlot(plotResult.plot_id, plotResult.plot_type, plotResult.html);
            }
            completeProgressBar();
        },
        
        // Called on task error
        onError: function(progressBarElement, progressBarMessageElement, excMessage) {
            console.error('Batch task failed:', excMessage);
            fallbackToSequentialLoading();
        },
        
        // Polling interval in ms
        pollInterval: 500
    });
}

function renderPlot(plotId, plotType, html) {
    let container;
    if (plotType === 'construct') {
        container = document.getElementById(`plot-${plotId}`);
    } else if (plotType === 'composite') {
        container = document.getElementById(`composite-plot-${plotId}`);
    } else if (plotType === 'item') {
        container = document.getElementById(`plot-item-${plotId}`);
    }
    
    if (container) {
        container.innerHTML = html;
        // Execute any scripts in the response (for Bokeh)
        const scripts = container.querySelectorAll('script');
        scripts.forEach(script => {
            const newScript = document.createElement('script');
            newScript.textContent = script.textContent;
            document.head.appendChild(newScript);
        });
        container.removeAttribute('data-plot-pending');
    }
}
```

---

## Benefits

| Aspect | Current (Sequential) | Proposed (Parallel) |
|--------|---------------------|---------------------|
| **Total Time** | N × avg_time | max(all_times) + overhead |
| **Server Load** | 1 request at a time | N concurrent workers |
| **User Experience** | Plots appear one by one | Plots appear as ready |
| **Scalability** | Limited by serial execution | Scales with worker count |

### Example Timing

With 10 plots, each taking ~200ms:
- **Sequential**: 10 × 200ms = **2000ms**
- **Parallel** (4 workers): ~200ms × 3 batches = **~600ms** + polling overhead

---

## Dependencies

Already installed (from `requirements.txt`):
- `celery==5.6.3`
- `django_celery_results==2.6.0`

To be added to `requirements.txt`:
- `celery-progress` - Drop-in, dependency-free progress bars for Django/Celery (https://pypi.org/project/celery-progress/)

Required infrastructure:
- **RabbitMQ** as message broker (default: `amqp://guest:guest@localhost:5672//`)
- Celery worker process(es)
- Database tables for `django_celery_results` (run migrations)

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Celery worker not running | Fallback to sequential loading if dispatch fails |
| Task timeout | Set reasonable timeout, show error state for failed plots |
| Memory pressure from parallel tasks | Limit concurrent tasks per worker |
| Result backend storage | Use short TTL for task results (5 min) |

---

## Testing Plan

1. Unit tests for Celery tasks (mock DB queries)
2. Integration tests for dispatch/status endpoints
3. Load testing with multiple concurrent users
4. Fallback behavior when Celery is unavailable

---

## Future Enhancements

- **WebSocket/SSE**: Replace polling with push notifications for completed tasks
- **Caching**: Cache computed aggregation data across tasks
- **Priority Queue**: Load visible plots before hidden tab plots
- **Multiple Workers**: Split plots across multiple Celery tasks for true parallelism

---

## Configuration Summary

| Component | Technology | Connection String |
|-----------|------------|-------------------|
| Message Broker | RabbitMQ | `amqp://guest:guest@localhost:5672//` |
| Result Backend | Django DB | `django-db` (via `django_celery_results`) |
| Progress Tracking | celery-progress | Built-in with `ProgressRecorder` |
| Worker Pool | gevent | 50 concurrent greenlets (I/O optimized) |

---

## Starting the Celery Worker

The workload is **I/O-bound** (database queries dominate), so we use gevent for high concurrency:

```bash
# Install gevent
pip install gevent

# Start worker with gevent pool (recommended for I/O-bound tasks)
celery -A chaviprom worker -l INFO -P gevent -c 50

# Or use settings defaults (configured in settings.py)
celery -A chaviprom worker -l INFO
```

### Worker Pool Options

| Pool Type | Best For | Concurrency |
|-----------|----------|-------------|
| `prefork` (default) | CPU-bound tasks | 1-2x CPU cores |
| `gevent` | I/O-bound tasks (DB, network) | 50-100+ greenlets |
| `eventlet` | I/O-bound (alternative to gevent) | 50-100+ |
| `solo` | Development/debugging | 1 |
