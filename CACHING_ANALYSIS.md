# Caching Analysis for CHAVI-PROM Django Application

## Executive Summary

**Current State**: ❌ **NO CACHING IMPLEMENTED for calculations and database queries**

Despite having memcached configured in production settings, the application is **NOT using Django's cache framework** for any of the expensive calculations or database queries in the PROM review views and utilities.

---

## Cache Configuration Status

### Settings Configuration (`chaviprom/settings.py`)

**Production** (lines 592-597):
```python
CACHES = {
    'default': {
        "BACKEND": "django.core.cache.backends.memcached.PyMemcacheCache",
        "LOCATION": "127.0.0.1:11211",
    }
}
```
✅ Memcached is configured for production

**Development** (lines 612-616):
```python
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.dummy.DummyCache",
    }
}
```
✅ DummyCache configured for development (no actual caching)

---

## Current Cache Usage Analysis

### 1. Views (`patientapp/views.py`)

**Search Results**: ❌ **NO cache imports or usage found**

```bash
grep -i "cache" patientapp/views.py
```

**Only match**: Line 818-819 - Comment about "Cache construct object for template header use"
- This is just an in-memory dictionary (`construct_obj_by_id`), NOT Django cache
- Local variable that doesn't persist across requests

**Conclusion**: 
- No `from django.core.cache import cache`
- No `@cache_page` decorators
- No `cache.get()` or `cache.set()` calls
- **Views perform all calculations fresh on every request**

---

### 2. Utils (`patientapp/utils.py`)

**Search Results**: ❌ **NO Django cache usage found**

```bash
grep -i "cache" patientapp/utils.py
```

**Only matches**: References to `reference_objects_cache` (lines 1711-1810)
- This is a **local dictionary parameter**, NOT Django cache
- Used for bulk operations to avoid N+1 queries within a single request
- Does NOT persist across requests
- Example:
  ```python
  def _get_patient_start_date_bulk(patient, start_date_reference, reference_objects_cache):
      cached_diagnosis = reference_objects_cache.get('diagnosis')  # Local dict, not Django cache
  ```

**Conclusion**:
- No `from django.core.cache import cache`
- No cache.get() or cache.set() for Django cache
- All aggregation calculations run fresh every time
- Database queries are not cached

---

## What Should Be Cached (High-Impact Opportunities)

### 🔴 Critical: Aggregation Statistics (Biggest Bottleneck)

**Current Problem**:
- Every PROM review page load calculates aggregation statistics from scratch
- Queries 11+ patients, fetches all their construct scores
- Calculates median/IQR for each time interval
- Takes ~7.2 seconds for 29 constructs

**Cache Opportunity**:
```python
# In prom_review_construct_plot view (lines 1262-1307)
cache_key = f"aggregation_{construct_id}_{start_date_ref}_{time_interval}_{aggregation_type}_{gender}_{diagnosis}_{treatment}_{min_age}_{max_age}"
aggregated_statistics = cache.get(cache_key)

if not aggregated_statistics:
    # Calculate aggregation (expensive)
    aggregated_data, metadata = aggregate_construct_scores_by_time_interval(...)
    aggregated_statistics = calculate_aggregation_statistics(aggregated_data, aggregation_type)
    
    # Cache for 1 hour (aggregation data changes infrequently)
    cache.set(cache_key, aggregated_statistics, 3600)
```

**Impact**: Could reduce construct plot generation from 7.2s to <1s

---

### 🟡 High Priority: Historical Scores Queries

**Current Problem**:
- Each plot fetches historical scores from database
- Same patient's scores fetched multiple times per page load
- No query result caching

**Cache Opportunity**:
```python
# Cache historical construct scores per patient
cache_key = f"construct_scores_{patient_id}_{construct_id}_{questionnaire_filter}_{time_range}"
historical_scores = cache.get(cache_key)

if not historical_scores:
    historical_scores = QuestionnaireConstructScore.objects.filter(...).select_related(...)
    cache.set(cache_key, list(historical_scores), 300)  # 5 minutes
```

**Impact**: Reduce database queries by 60-80%

---

### 🟡 High Priority: Item Response Queries

**Current Problem**:
- Item responses fetched fresh for each item plot
- 31 item plots = 31 separate database queries

**Cache Opportunity**:
```python
cache_key = f"item_responses_{patient_id}_{item_id}_{time_range}"
historical_responses = cache.get(cache_key)

if not historical_responses:
    historical_responses = QuestionnaireItemResponse.objects.filter(...).select_related(...)
    cache.set(cache_key, list(historical_responses), 300)
```

**Impact**: Reduce item plot generation time by 50%

---

### 🟢 Medium Priority: Patient Start Dates

**Current Problem**:
- Start date calculations repeated for aggregation patients
- Involves diagnosis/treatment lookups

**Cache Opportunity**:
```python
cache_key = f"start_date_{patient_id}_{start_date_reference}"
start_date = cache.get(cache_key)

if not start_date:
    start_date = get_patient_start_date(patient, start_date_reference)
    cache.set(cache_key, start_date, 1800)  # 30 minutes
```

---

### 🟢 Medium Priority: Filtered Patient Lists

**Current Problem**:
- `get_filtered_patients_for_aggregation()` runs same query repeatedly
- Filters by gender, diagnosis, treatment, age

**Cache Opportunity**:
```python
cache_key = f"filtered_patients_{gender}_{diagnosis}_{treatment}_{min_age}_{max_age}"
patients = cache.get(cache_key)

if not patients:
    patients = get_filtered_patients_for_aggregation(...)
    cache.set(cache_key, list(patients), 600)  # 10 minutes
```

---

## Cache Invalidation Strategy

### When to Invalidate Cache:

1. **New Questionnaire Submission**:
   - Invalidate patient's historical scores
   - Invalidate aggregation statistics for relevant constructs
   - Signal: `post_save` on `QuestionnaireSubmission`

2. **Patient Data Updated**:
   - Invalidate patient's start dates
   - Invalidate filtered patient lists if demographics changed
   - Signal: `post_save` on `Patient`, `Diagnosis`, `Treatment`

3. **Time-Based Expiration**:
   - Aggregation statistics: 1 hour (changes infrequently)
   - Historical scores: 5 minutes (balance freshness vs performance)
   - Filtered patients: 10 minutes
   - Start dates: 30 minutes

### Implementation Pattern:

```python
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.cache import cache

@receiver(post_save, sender=QuestionnaireSubmission)
def invalidate_patient_cache(sender, instance, **kwargs):
    patient_id = instance.patient.id
    
    # Invalidate all cache keys for this patient
    cache.delete_pattern(f"construct_scores_{patient_id}_*")
    cache.delete_pattern(f"item_responses_{patient_id}_*")
    
    # Invalidate aggregation cache (affects all patients)
    cache.delete_pattern("aggregation_*")
```

---

## Recommended Implementation Priority

### Phase 1: Quick Wins (1-2 hours)
1. ✅ Cache aggregation statistics (biggest impact)
2. ✅ Cache historical construct scores
3. ✅ Cache item responses

**Expected Impact**: 60-70% performance improvement

### Phase 2: Optimization (2-3 hours)
4. Cache filtered patient lists
5. Cache patient start dates
6. Implement cache invalidation signals

**Expected Impact**: Additional 15-20% improvement

### Phase 3: Advanced (3-4 hours)
7. Cache entire plot HTML (template fragment caching)
8. Cache Bokeh plot objects
9. Implement cache warming for common filter combinations

**Expected Impact**: Additional 10-15% improvement

---

## Code Examples for Implementation

### Example 1: Cache Aggregation in Construct Plot View

```python
from django.core.cache import cache
import hashlib
import json

@login_required
@permission_required('patientapp.view_patient', raise_exception=True)
def prom_review_construct_plot(request, pk, construct_id):
    # ... existing code to get filters ...
    
    # Create cache key from all filter parameters
    filter_params = {
        'construct_id': str(construct_id),
        'start_date_reference': start_date_reference,
        'time_interval': time_interval,
        'aggregation_type': aggregation_type,
        'gender': patient_filter_gender,
        'diagnosis': patient_filter_diagnosis,
        'treatment': patient_filter_treatment,
        'min_age': min_age_value,
        'max_age': max_age_value,
    }
    
    # Generate stable cache key
    cache_key_base = json.dumps(filter_params, sort_keys=True)
    cache_key = f"agg_{hashlib.md5(cache_key_base.encode()).hexdigest()}"
    
    # Try to get from cache
    cached_result = cache.get(cache_key)
    if cached_result:
        logger.info(f"Cache HIT for aggregation: {cache_key}")
        aggregated_statistics = cached_result['statistics']
        aggregation_metadata = cached_result['metadata']
    else:
        logger.info(f"Cache MISS for aggregation: {cache_key}")
        # ... existing aggregation calculation code ...
        
        # Cache the result
        cache.set(cache_key, {
            'statistics': aggregated_statistics,
            'metadata': aggregation_metadata
        }, 3600)  # 1 hour
    
    # ... rest of view code ...
```

### Example 2: Cache Historical Scores

```python
def get_cached_construct_scores(patient, construct, filters):
    """Get construct scores with caching."""
    cache_key = f"scores_{patient.id}_{construct.id}_{filters['questionnaire']}_{filters['time_range']}"
    
    scores = cache.get(cache_key)
    if scores is None:
        scores = QuestionnaireConstructScore.objects.filter(
            construct=construct,
            questionnaire_submission__patient=patient
        ).select_related('questionnaire_submission', 'construct')
        
        # Apply filters...
        
        scores = list(scores[:filters['submission_count']])
        cache.set(cache_key, scores, 300)  # 5 minutes
    
    return scores
```

---

## Performance Impact Estimation

### Current Performance (No Caching):
- Initial page load: 1-2 seconds (after lazy loading)
- Each construct plot: ~250ms (with aggregation)
- Each item plot: ~150ms
- Total for all plots: ~12 seconds

### With Caching Implemented:
- Initial page load: 1-2 seconds (same)
- Each construct plot (cached): ~20-30ms (90% faster)
- Each item plot (cached): ~15-20ms (90% faster)
- Total for all plots: ~1-2 seconds (90% faster)

### Cache Hit Rates (Estimated):
- First visit: 0% hit rate (cold cache)
- Subsequent visits (same filters): 95% hit rate
- Different filters: 60-70% hit rate (partial cache reuse)

---

## Monitoring Recommendations

### Add Cache Metrics:

```python
import logging
cache_logger = logging.getLogger('cache_performance')

def log_cache_performance(cache_key, hit):
    cache_logger.info(f"Cache {'HIT' if hit else 'MISS'}: {cache_key}")

# In views:
cached_data = cache.get(cache_key)
log_cache_performance(cache_key, cached_data is not None)
```

### Django Debug Toolbar:
- Already configured (line 547: `debug_toolbar.panels.cache.CachePanel`)
- Shows cache hits/misses in development

---

## Conclusion

**Current State**: 
- ❌ No Django cache usage in views or utils
- ❌ Memcached configured but unused
- ❌ All calculations run fresh every request
- ❌ Database queries not cached

**Recommendation**: 
- ✅ Implement caching for aggregation statistics (highest impact)
- ✅ Cache database query results
- ✅ Add cache invalidation signals
- ✅ Monitor cache performance

**Expected Benefit**: 
- 60-90% reduction in calculation time
- 70-80% reduction in database queries
- Better user experience with faster plot loading
- Reduced server load

**Effort**: 4-8 hours for full implementation
**ROI**: Very high - dramatic performance improvement with moderate effort
