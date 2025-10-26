# Caching Implementation Checklist

## 📋 Implementation Plan - Phase 1 (High Impact)

### ✅ Pre-Implementation
- [x] Verify memcached is configured in settings.py
- [x] Analyze current code for cache usage
- [x] Document cache key patterns
- [x] Create implementation checklist

---

## 🔧 Phase 1: Core Caching Implementation

### Step 1: Add Cache Import to Views ✅ COMPLETE
**File**: `/mnt/share/chavi-prom/patientapp/views.py`

- [x] Add import at top of file:
  ```python
  from django.core.cache import cache
  import hashlib
  import json
  ```

---

### Step 2: Implement Aggregation Caching in `prom_review_construct_plot` ✅ COMPLETE
**File**: `/mnt/share/chavi-prom/patientapp/views.py`
**Function**: `prom_review_construct_plot` (lines ~1262-1307)

- [x] Create cache key generator function
- [x] Add cache.get() before aggregation calculation
- [x] Add cache.set() after aggregation calculation
- [x] Add logging for cache hits/misses
- [ ] Test with single construct

**Cache Key Pattern**:
```python
cache_key = f"agg_{construct_id}_{start_date_ref}_{time_interval}_{agg_type}_{gender}_{diagnosis}_{treatment}_{min_age}_{max_age}"
```

**TTL**: 3600 seconds (1 hour)

---

### Step 3: Implement Aggregation Caching in `prom_review_composite_plot` ✅ N/A
**File**: `/mnt/share/chavi-prom/patientapp/views.py`
**Function**: `prom_review_composite_plot` (lines ~1323-1439)

- [x] Composite plots don't have aggregation calculations
- [x] Skipped - not applicable

---

### Step 4: Cache Historical Construct Scores ✅ COMPLETE
**File**: `/mnt/share/chavi-prom/patientapp/views.py`
**Function**: `prom_review_construct_plot` (lines ~1214-1250)

- [x] Create cache key for historical scores query
- [x] Add cache.get() before database query
- [x] Add cache.set() after query with list conversion
- [ ] Test query result caching

**Cache Key Pattern**:
```python
cache_key = f"scores_{patient_id}_{construct_id}_{questionnaire_filter}_{time_range}_{max_time_interval}"
```

**TTL**: 300 seconds (5 minutes)

---

### Step 5: Cache Historical Item Responses ✅ COMPLETE
**File**: `/mnt/share/chavi-prom/patientapp/views.py`
**Function**: `prom_review_item_plot` (lines ~1399-1429)

- [x] Create cache key for item responses query
- [x] Add cache.get() before database query
- [x] Add cache.set() after query with list conversion
- [ ] Test with multiple items

**Cache Key Pattern**:
```python
cache_key = f"item_resp_{patient_id}_{item_id}_{time_range}_{max_time_interval}"
```

**TTL**: 300 seconds (5 minutes)

---

### Step 6: Cache Historical Composite Scores ✅ COMPLETE
**File**: `/mnt/share/chavi-prom/patientapp/views.py`
**Function**: `prom_review_composite_plot` (lines ~1385-1416)

- [x] Create cache key for composite scores query
- [x] Add cache.get() before database query
- [x] Add cache.set() after query
- [ ] Test composite score caching

**Cache Key Pattern**:
```python
cache_key = f"comp_scores_{patient_id}_{composite_id}_{time_range}_{max_time_interval}"
```

**TTL**: 300 seconds (5 minutes)

---

## 🔔 Phase 2: Cache Invalidation

### Step 7: Create Cache Invalidation Signals
**File**: `/mnt/share/chavi-prom/patientapp/signals.py` (create new file)

- [ ] Create signals.py file
- [ ] Import necessary modules
- [ ] Create signal handler for QuestionnaireSubmission
- [ ] Invalidate patient-specific caches
- [ ] Invalidate aggregation caches
- [ ] Test signal firing

**Signal Pattern**:
```python
@receiver(post_save, sender=QuestionnaireSubmission)
def invalidate_patient_cache(sender, instance, **kwargs):
    patient_id = instance.patient.id
    cache.delete_pattern(f"scores_{patient_id}_*")
    cache.delete_pattern(f"item_resp_{patient_id}_*")
    cache.delete_pattern(f"comp_scores_{patient_id}_*")
    cache.delete_pattern("agg_*")
```

---

### Step 8: Register Signals in AppConfig
**File**: `/mnt/share/chavi-prom/patientapp/apps.py`

- [ ] Import signals in ready() method
- [ ] Test signal registration
- [ ] Verify signals fire on submission

---

## 📊 Phase 3: Monitoring & Optimization

### Step 9: Add Cache Performance Logging
**File**: `/mnt/share/chavi-prom/patientapp/views.py`

- [ ] Create cache logger
- [ ] Add cache hit/miss logging to all cache.get() calls
- [ ] Add cache key logging
- [ ] Test log output

**Logging Pattern**:
```python
cache_logger = logging.getLogger('cache_performance')
cached_data = cache.get(cache_key)
cache_logger.info(f"Cache {'HIT' if cached_data else 'MISS'}: {cache_key}")
```

---

### Step 10: Create Cache Utility Functions
**File**: `/mnt/share/chavi-prom/patientapp/cache_utils.py` (create new file)

- [ ] Create generate_cache_key() function
- [ ] Create get_cached_or_calculate() wrapper function
- [ ] Create invalidate_patient_cache() function
- [ ] Create invalidate_aggregation_cache() function
- [ ] Refactor views to use utility functions

---

## 🧪 Testing Checklist

### Step 11: Functional Testing

- [ ] Test cache miss (first load) - should work as before
- [ ] Test cache hit (second load) - should be faster
- [ ] Test different patients - should get different data
- [ ] Test same patient with different filters - should cache separately
- [ ] Test multiple users viewing same patient - should share aggregation cache
- [ ] Test cache invalidation on new submission
- [ ] Test cache expiration (wait for TTL)

---

### Step 12: Performance Testing

- [ ] Measure page load time before caching
- [ ] Measure page load time after caching (cold cache)
- [ ] Measure page load time after caching (warm cache)
- [ ] Measure aggregation calculation time (cached vs uncached)
- [ ] Document performance improvements
- [ ] Check memcached memory usage

---

### Step 13: Security Testing

- [ ] Verify patient A cannot see patient B's cached data
- [ ] Verify institution filtering still works with cache
- [ ] Verify encrypted fields are not cached in plain text
- [ ] Test cache key collision scenarios
- [ ] Verify cache invalidation on patient data updates

---

## 📝 Documentation

### Step 14: Update Documentation

- [ ] Document cache key patterns in code comments
- [ ] Document TTL values and rationale
- [ ] Update CACHING_ANALYSIS.md with implementation notes
- [ ] Create cache troubleshooting guide
- [ ] Document cache monitoring procedures

---

## 🚀 Deployment Checklist

### Step 15: Pre-Deployment

- [ ] Verify memcached is running in production
- [ ] Check memcached memory allocation
- [ ] Review cache configuration in settings.py
- [ ] Test in staging environment
- [ ] Create rollback plan

---

### Step 16: Deployment

- [ ] Deploy code changes
- [ ] Monitor application logs for cache hits/misses
- [ ] Monitor memcached stats
- [ ] Monitor page load times
- [ ] Monitor error rates

---

### Step 17: Post-Deployment

- [ ] Verify cache is working (check logs)
- [ ] Measure performance improvements
- [ ] Monitor cache hit rates
- [ ] Check for any cache-related errors
- [ ] Document actual performance gains

---

## 🎯 Success Criteria

- [ ] Page load time reduced by 60-70% (warm cache)
- [ ] Aggregation calculation time reduced by 90%
- [ ] Database query count reduced by 60-80%
- [ ] No data leakage between patients
- [ ] Cache invalidation working correctly
- [ ] No increase in error rates
- [ ] Memcached memory usage within limits

---

## 🔄 Rollback Plan

If issues occur:

- [ ] Disable cache by setting TTL to 0
- [ ] Revert code changes
- [ ] Clear memcached: `echo 'flush_all' | nc localhost 11211`
- [ ] Monitor for resolution
- [ ] Investigate root cause

---

## 📌 Notes

### Cache Key Patterns Summary:
```
Aggregation:        agg_{construct_id}_{filters_hash}
Construct Scores:   scores_{patient_id}_{construct_id}_{filters}
Item Responses:     item_resp_{patient_id}_{item_id}_{filters}
Composite Scores:   comp_scores_{patient_id}_{composite_id}_{filters}
```

### TTL Values:
- Aggregation: 3600s (1 hour) - changes infrequently
- Patient data: 300s (5 minutes) - balance freshness vs performance

### Cache Invalidation Triggers:
- New QuestionnaireSubmission → Invalidate patient + aggregation
- Patient data update → Invalidate patient caches
- Manual flush → Clear all caches

---

## 🏁 Implementation Order

**Priority 1 (Highest Impact):**
1. Step 2: Aggregation caching in construct plots
2. Step 3: Aggregation caching in composite plots

**Priority 2 (High Impact):**
3. Step 4: Historical construct scores caching
4. Step 5: Historical item responses caching
5. Step 6: Historical composite scores caching

**Priority 3 (Essential):**
6. Step 7-8: Cache invalidation signals

**Priority 4 (Monitoring):**
7. Step 9: Cache performance logging
8. Step 11-13: Testing

**Priority 5 (Polish):**
9. Step 10: Cache utility functions
10. Step 14: Documentation

---

## ⏱️ Estimated Time

- Phase 1 (Steps 1-6): 2-3 hours
- Phase 2 (Steps 7-8): 1 hour
- Phase 3 (Steps 9-10): 1 hour
- Testing (Steps 11-13): 1-2 hours
- Documentation (Step 14): 30 minutes
- **Total: 5.5-7.5 hours**

---

## 🎓 Learning Resources

- Django Cache Framework: https://docs.djangoproject.com/en/5.2/topics/cache/
- Memcached Best Practices: https://github.com/memcached/memcached/wiki/ProgrammingTricks
- Cache Invalidation Patterns: https://martinfowler.com/bliki/TwoHardThings.html

---

**Status**: Ready to implement
**Created**: 2025-10-26
**Last Updated**: 2025-10-26
