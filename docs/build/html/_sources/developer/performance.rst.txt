Performance Optimization
========================

Guide to optimizing SATHI's performance for better user experience and scalability.

.. contents:: Table of Contents
   :local:
   :depth: 3

Overview
--------

SATHI implements several performance optimization strategies:

- **Lazy Loading**: Progressive loading of plots and heavy content
- **Caching**: Memcached for database query results
- **Database Optimization**: Efficient queries and indexing
- **Frontend Optimization**: Minimal JavaScript, optimized CSS
- **HTMX**: Partial page updates without full reloads

Performance Metrics
-------------------

Target Performance Goals
~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 40 30 30

   * - Metric
     - Target
     - Critical Threshold
   * - Initial Page Load
     - < 2 seconds
     - < 5 seconds
   * - Time to Interactive
     - < 3 seconds
     - < 6 seconds
   * - PROM Review Page (cold cache)
     - < 5 seconds
     - < 10 seconds
   * - PROM Review Page (warm cache)
     - < 2 seconds
     - < 4 seconds
   * - Database Query Time
     - < 100ms
     - < 500ms
   * - Plot Generation
     - < 200ms each
     - < 1 second each

Lazy Loading Implementation
----------------------------

Overview
~~~~~~~~

Lazy loading dramatically improves initial page load by deferring non-critical content.

**Before Lazy Loading:**

- Initial page load: 12.3 seconds (blocking)
- User sees white screen with loader
- All 60+ plots generated synchronously

**After Lazy Loading:**

- Initial page load: 1-2 seconds (85% faster!)
- Page appears immediately with data
- Plots load progressively as user scrolls
- Hidden tabs don't load until viewed

PROM Review Page Optimization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The PROM Review page was the primary performance bottleneck.

**Performance Breakdown (Before):**

.. code-block:: text

    Total Load Time: 12.3 seconds
    ├── Item Response Processing: 4.7s (31 items × ~150ms)
    ├── Construct Score Calculation: 3.2s (29 constructs)
    ├── Aggregation Statistics: 2.8s (population data)
    ├── Plot Generation: 1.4s (60+ Bokeh plots)
    └── Template Rendering: 0.2s

**Bottleneck Analysis:**

1. **Item Responses**: 31 items × 150ms = 4.7 seconds
   
   - Fetch historical data for each item
   - Calculate percentages
   - Generate Bokeh plot

2. **Construct Scores**: 29 constructs × 110ms = 3.2 seconds
   
   - Query submissions
   - Calculate scores
   - Generate plot

3. **Aggregation**: 7.2 seconds for population statistics
   
   - Most expensive operation
   - Queries across all patients
   - Complex calculations

Lazy Loading Strategy
~~~~~~~~~~~~~~~~~~~~~

**Implementation:**

.. code-block:: python

    # patientapp/views.py
    
    @login_required
    @permission_required('patientapp.view_patient')
    def prom_review(request, pk):
        """Main PROM review view - skip plot generation."""
        patient = get_accessible_patient_or_404(request.user, pk)
        
        # Get construct scores WITHOUT plots
        construct_scores = ConstructScoreData(
            patient=patient,
            generate_plot=False  # Skip plot generation
        )
        
        # Get item responses WITHOUT plots
        item_responses = get_item_responses(
            patient=patient,
            generate_plots=False  # Skip plot generation
        )
        
        context = {
            'patient': patient,
            'construct_scores': construct_scores,
            'item_responses': item_responses,
        }
        
        return render(request, 'promapp/prom_review.html', context)

**Lazy Load Endpoints:**

.. code-block:: python

    @login_required
    @permission_required('patientapp.view_patient')
    def prom_review_construct_plot(request, pk, construct_id):
        """Lazy-load a single construct plot via HTMX."""
        patient = get_accessible_patient_or_404(request.user, pk)
        
        # Get filters from request
        filters = get_filters_from_request(request)
        
        # Generate ONLY this plot
        construct_score = ConstructScoreData(
            patient=patient,
            construct_id=construct_id,
            filters=filters,
            generate_plot=True  # Generate this one plot
        )
        
        return render(request, 'promapp/partials/construct_plot.html', {
            'score_data': construct_score
        })

**Template Integration:**

.. code-block:: html

    <!-- templates/promapp/components/construct_score_card.html -->
    <div class="plot-container">
        <!-- Placeholder with loading spinner -->
        <div 
            hx-get="{% url 'prom_review_construct_plot' patient.id construct.id %}?{{ request.GET.urlencode }}"
            hx-trigger="revealed"
            hx-swap="outerHTML">
            
            <div class="loading-spinner">
                <svg class="animate-spin h-8 w-8 text-blue-600">
                    <!-- Spinner SVG -->
                </svg>
                <p>Loading plot...</p>
            </div>
        </div>
    </div>

**Key Features:**

- ``hx-trigger="revealed"`` - Loads when scrolled into viewport
- ``hx-swap="outerHTML"`` - Replaces placeholder with plot
- Filter parameters passed via ``{{ request.GET.urlencode }}``
- Graceful degradation if HTMX fails

Performance Impact
~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 40 30 30

   * - Metric
     - Before
     - After
   * - Initial Page Load
     - 12.3s (blocking)
     - 1-2s (85% faster)
   * - Time to Interactive
     - 12.3s
     - 1-2s
   * - Total Time to All Plots
     - 12.3s
     - ~12s (progressive)
   * - User Perceived Performance
     - Poor (white screen)
     - Excellent (instant)
   * - Filter Application
     - 12s+ reload
     - Instant update

Caching Strategy
----------------

Memcached Configuration
~~~~~~~~~~~~~~~~~~~~~~~

SATHI uses Memcached for caching expensive database queries.

**Settings:**

.. code-block:: python

    # chaviprom/settings.py
    
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.memcached.PyMemcacheCache',
            'LOCATION': '127.0.0.1:11211',
            'TIMEOUT': 300,  # 5 minutes default
            'OPTIONS': {
                'no_delay': True,
                'ignore_exc': True,
                'max_pool_size': 4,
                'use_pooling': True,
            }
        }
    }

Cache Key Strategy
~~~~~~~~~~~~~~~~~~

**Patient-Specific Data:**

.. code-block:: python

    from django.core.cache import cache
    
    def get_patient_construct_scores(patient, filters):
        """Get construct scores with caching."""
        
        # Build cache key
        cache_key = f"construct_scores:{patient.id}:{hash(str(filters))}"
        
        # Try cache first
        cached_data = cache.get(cache_key)
        if cached_data:
            return cached_data
        
        # Calculate if not cached
        scores = calculate_construct_scores(patient, filters)
        
        # Cache for 5 minutes
        cache.set(cache_key, scores, timeout=300)
        
        return scores

**Aggregation Data:**

.. code-block:: python

    def get_aggregation_statistics(filters):
        """Get population-level aggregation with caching."""
        
        # Aggregation is shared across patients with same filters
        cache_key = f"aggregation:{hash(str(filters))}"
        
        cached_data = cache.get(cache_key)
        if cached_data:
            return cached_data
        
        # Calculate aggregation (expensive!)
        stats = calculate_aggregation_statistics(filters)
        
        # Cache for 1 hour (changes less frequently)
        cache.set(cache_key, stats, timeout=3600)
        
        return stats

Cache Invalidation
~~~~~~~~~~~~~~~~~~

**Signal-Based Invalidation:**

.. code-block:: python

    # patientapp/signals.py
    from django.db.models.signals import post_save
    from django.dispatch import receiver
    from django.core.cache import cache
    
    @receiver(post_save, sender=QuestionnaireSubmission)
    def invalidate_patient_cache(sender, instance, **kwargs):
        """Invalidate cache when new submission is created."""
        patient = instance.patient_questionnaire.patient
        
        # Clear all cache keys for this patient
        cache_pattern = f"construct_scores:{patient.id}:*"
        cache.delete_pattern(cache_pattern)
        
        # Clear aggregation cache (affects population stats)
        cache.delete_pattern("aggregation:*")

**Manual Cache Clearing:**

.. code-block:: python

    from django.core.cache import cache
    
    # Clear all caches
    cache.clear()
    
    # Clear specific pattern
    cache.delete_pattern("construct_scores:*")

Cache Performance Impact
~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 40 30 30

   * - Scenario
     - Time (No Cache)
     - Time (With Cache)
   * - Cold Cache (First Load)
     - 12s
     - 12s
   * - Warm Cache (Aggregation)
     - 12s
     - 5s (58% faster)
   * - Full Cache Hit
     - 12s
     - 2s (83% faster)
   * - Aggregation Calculation
     - 7.2s
     - 0.1s (99% faster)

Database Optimization
---------------------

Query Optimization
~~~~~~~~~~~~~~~~~~

**Use select_related() for Foreign Keys:**

.. code-block:: python

    # Bad: N+1 queries
    patients = Patient.objects.all()
    for patient in patients:
        print(patient.institution.name)  # Extra query per patient
    
    # Good: Single query with JOIN
    patients = Patient.objects.select_related('institution')
    for patient in patients:
        print(patient.institution.name)  # No extra query

**Use prefetch_related() for Many-to-Many:**

.. code-block:: python

    # Bad: N+1 queries
    treatments = Treatment.objects.all()
    for treatment in treatments:
        for tt in treatment.treatment_type.all():  # Extra query per treatment
            print(tt.treatment_type)
    
    # Good: 2 queries total
    treatments = Treatment.objects.prefetch_related('treatment_type')
    for treatment in treatments:
        for tt in treatment.treatment_type.all():  # No extra query
            print(tt.treatment_type)

**Use only() to Limit Fields:**

.. code-block:: python

    # Bad: Fetches all fields
    patients = Patient.objects.all()
    
    # Good: Only fetch needed fields
    patients = Patient.objects.only('id', 'name', 'date_of_registration')

**Use values() for Dictionaries:**

.. code-block:: python

    # Bad: Creates model instances
    patient_names = [p.name for p in Patient.objects.all()]
    
    # Good: Returns dictionaries (faster)
    patient_names = Patient.objects.values_list('name', flat=True)

Database Indexing
~~~~~~~~~~~~~~~~~

**Add Indexes to Frequently Queried Fields:**

.. code-block:: python

    # patientapp/models.py
    
    class QuestionnaireSubmission(models.Model):
        patient_questionnaire = models.ForeignKey(
            PatientQuestionnaire,
            on_delete=models.CASCADE
        )
        submission_date = models.DateTimeField(
            auto_now_add=True,
            db_index=True  # Index for date filtering
        )
        
        class Meta:
            indexes = [
                models.Index(
                    fields=['patient_questionnaire', 'submission_date'],
                    name='submission_patient_date_idx'
                ),
            ]

**Composite Indexes:**

.. code-block:: python

    class QuestionnaireItemResponse(models.Model):
        # ... fields ...
        
        class Meta:
            indexes = [
                # Composite index for common query pattern
                models.Index(
                    fields=['questionnaire_submission', 'item'],
                    name='response_submission_item_idx'
                ),
            ]

Query Analysis
~~~~~~~~~~~~~~

**Use Django Debug Toolbar:**

.. code-block:: python

    # settings.py (development only)
    if DEBUG:
        INSTALLED_APPS += ['debug_toolbar']
        MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']
        INTERNAL_IPS = ['127.0.0.1']

**Log Slow Queries:**

.. code-block:: python

    # settings.py
    LOGGING = {
        'version': 1,
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
            },
        },
        'loggers': {
            'django.db.backends': {
                'handlers': ['console'],
                'level': 'DEBUG',
            },
        },
    }

Frontend Optimization
---------------------

Tailwind CSS Optimization
~~~~~~~~~~~~~~~~~~~~~~~~~

**Production Build:**

.. code-block:: bash

    # Build optimized CSS (removes unused classes)
    npm run build:css

**Configuration:**

.. code-block:: javascript

    // tailwind.config.js
    module.exports = {
        content: [
            './templates/**/*.html',
            './static/js/**/*.js',
        ],
        theme: {
            extend: {},
        },
        plugins: [],
    }

**Result:**

- Development CSS: ~3.5MB
- Production CSS: ~50KB (98% reduction)

HTMX Optimization
~~~~~~~~~~~~~~~~~

**Partial Page Updates:**

.. code-block:: html

    <!-- Only update specific section, not entire page -->
    <form hx-post="/patients/filter/" 
          hx-target="#patient-table"
          hx-swap="innerHTML">
        <!-- Filters -->
    </form>
    
    <div id="patient-table">
        <!-- Only this section updates -->
    </div>

**Request Indicators:**

.. code-block:: html

    <!-- Show loading state during request -->
    <button hx-post="/submit/" 
            hx-indicator="#spinner">
        Submit
    </button>
    
    <div id="spinner" class="htmx-indicator">
        Loading...
    </div>

Static File Optimization
~~~~~~~~~~~~~~~~~~~~~~~~

**Compression:**

.. code-block:: python

    # settings.py
    
    # Enable GZip compression
    MIDDLEWARE = [
        'django.middleware.gzip.GZipMiddleware',
        # ... other middleware
    ]

**Static File Caching:**

.. code-block:: nginx

    # nginx.conf
    location /static/ {
        alias /var/www/chavi-prom/staticfiles/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

Image Optimization
~~~~~~~~~~~~~~~~~~

**Use Appropriate Formats:**

- PNG: Icons, logos (lossless)
- JPEG: Photos (lossy, smaller)
- SVG: Icons, simple graphics (scalable)
- WebP: Modern browsers (best compression)

**Optimize Images:**

.. code-block:: bash

    # Optimize PNG
    optipng -o7 image.png
    
    # Optimize JPEG
    jpegoptim --max=85 image.jpg
    
    # Convert to WebP
    cwebp -q 80 image.jpg -o image.webp

Monitoring & Profiling
----------------------

Django Debug Toolbar
~~~~~~~~~~~~~~~~~~~~

**Installation:**

.. code-block:: bash

    pip install django-debug-toolbar

**Configuration:**

.. code-block:: python

    # settings.py (development only)
    if DEBUG:
        INSTALLED_APPS += ['debug_toolbar']
        MIDDLEWARE.insert(0, 'debug_toolbar.middleware.DebugToolbarMiddleware')
        INTERNAL_IPS = ['127.0.0.1']

**Features:**

- SQL query analysis
- Template rendering time
- Cache hit/miss statistics
- Signal execution time

Python Profiling
~~~~~~~~~~~~~~~~

**cProfile:**

.. code-block:: python

    import cProfile
    import pstats
    
    def profile_view():
        profiler = cProfile.Profile()
        profiler.enable()
        
        # Your code here
        result = expensive_function()
        
        profiler.disable()
        stats = pstats.Stats(profiler)
        stats.sort_stats('cumulative')
        stats.print_stats(20)  # Top 20 functions
        
        return result

**django-silk:**

.. code-block:: bash

    pip install django-silk

.. code-block:: python

    # settings.py
    INSTALLED_APPS += ['silk']
    MIDDLEWARE += ['silk.middleware.SilkyMiddleware']

Performance Testing
~~~~~~~~~~~~~~~~~~~

**Load Testing with Locust:**

.. code-block:: python

    # locustfile.py
    from locust import HttpUser, task, between
    
    class SATHIUser(HttpUser):
        wait_time = between(1, 3)
        
        @task
        def view_patient_list(self):
            self.client.get("/patients/")
        
        @task(3)  # 3x more frequent
        def view_prom_review(self):
            self.client.get("/patients/123/prom-review/")

.. code-block:: bash

    # Run load test
    locust -f locustfile.py --host=http://localhost:8000

Best Practices
--------------

General Guidelines
~~~~~~~~~~~~~~~~~~

**DO:**

- Use lazy loading for heavy content
- Cache expensive calculations
- Optimize database queries
- Use indexes on frequently queried fields
- Monitor performance regularly
- Profile before optimizing
- Measure impact of changes

**DON'T:**

- Premature optimization
- Cache everything blindly
- Ignore database query counts
- Load all data at once
- Skip performance testing
- Optimize without measuring

Checklist
~~~~~~~~~

**Before Deployment:**

- [ ] Run production CSS build
- [ ] Enable caching in production
- [ ] Add database indexes
- [ ] Optimize images
- [ ] Enable GZip compression
- [ ] Test with realistic data volumes
- [ ] Profile critical views
- [ ] Load test with expected traffic

**Ongoing:**

- [ ] Monitor cache hit rates
- [ ] Review slow query logs
- [ ] Check page load times
- [ ] Analyze user metrics
- [ ] Update cache strategies
- [ ] Optimize new features

Troubleshooting
---------------

Common Issues
~~~~~~~~~~~~~

**Slow Page Loads:**

1. Check database query count (Django Debug Toolbar)
2. Add select_related/prefetch_related
3. Enable caching
4. Implement lazy loading

**High Memory Usage:**

1. Limit queryset size with pagination
2. Use values() instead of model instances
3. Clear old cache entries
4. Optimize image sizes

**Cache Not Working:**

1. Verify Memcached is running: ``systemctl status memcached``
2. Check cache key generation
3. Verify cache timeout settings
4. Test cache with simple example

**Database Slow:**

1. Add missing indexes
2. Optimize complex queries
3. Use database query analysis
4. Consider read replicas for scaling

Resources
---------

- `Django Performance Tips <https://docs.djangoproject.com/en/stable/topics/performance/>`_
- `Django Debug Toolbar <https://django-debug-toolbar.readthedocs.io/>`_
- `Memcached Documentation <https://memcached.org/>`_
- `HTMX Documentation <https://htmx.org/docs/>`_
- `Tailwind CSS Optimization <https://tailwindcss.com/docs/optimizing-for-production>`_
