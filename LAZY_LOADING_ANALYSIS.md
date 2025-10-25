# PROM Review Lazy Loading Implementation Plan

## Current Architecture Analysis

### Template Hierarchy
```
prom_review.html (main page)
├── filters_section.html (filters - stays on page)
├── main_content.html (gets replaced by HTMX)
    ├── aggregation_metadata_card.html
    ├── patient_info_card.html (with plot indicators)
    ├── questionnaire_overview_card.html
    ├── topline_vertical_tabs.html
    │   └── For each important_construct_scores:
    │       ├── Construct score card
    │       ├── **PLOT: {{ score_data.bokeh_plot|safe }}** (line 104)
    │       ├── Summary section
    │       └── Related item cards (with plots)
    ├── other_constructs_vertical_tabs.html
    │   └── For each other_construct_scores:
    │       ├── Construct score card
    │       ├── **PLOT: {{ construct_score.bokeh_plot|safe }}** (line 104)
    │       ├── Summary section
    │       └── Related item cards (with plots)
    └── composite_scores_vertical_tabs.html
        └── For each composite_construct_scores:
            ├── Composite score card
            ├── **PLOT: {{ score_data.bokeh_plot|safe }}** (line 109)
            └── Summary section
```

### Item Cards (nested in construct tabs)
```
item_card_base.html (base template)
├── likert_item_card.html
│   └── **PLOT: {{ item_response.bokeh_plot|safe }}** (line 39)
├── numeric_item_card.html
│   └── **PLOT: {{ item_response.bokeh_plot|safe }}**
├── text_item_card.html (no plot)
└── media_item_card.html (no plot)
```

## Performance Bottleneck Breakdown

### From Log Analysis (12.3 second total load):

1. **Item Response Processing: 4.7 seconds**
   - 31 item responses
   - Each item: fetch historical data, calculate percentages, generate Bokeh plot
   - ~150ms per item

2. **Construct Score Processing: 7.2 seconds** ⚠️ MAIN BOTTLENECK
   - 29 construct scores (important + other)
   - For EACH construct:
     * Aggregate data from 11 patients
     * Calculate statistics (median/IQR)
     * Generate Bokeh plot with aggregation overlay
   - ~248ms per construct

3. **Composite Scores: ~0.3 seconds**
   - 3 composite construct scores
   - Minimal aggregation

## Lazy Loading Strategy

### Phase 1: Initial Page Load (Target: <2 seconds)
**What loads immediately:**
- ✅ Patient info card (no plots)
- ✅ Questionnaire overview
- ✅ Aggregation metadata summary
- ✅ Construct score CARDS (numbers, badges, summaries) - NO PLOTS
- ✅ Composite score CARDS - NO PLOTS
- ✅ Vertical tab navigation
- ✅ Placeholder divs for plots

**What's deferred:**
- ❌ All Bokeh plots (construct + item)
- ❌ Aggregation calculations

### Phase 2: Lazy Load Plots (Triggered after page render)
**Approach: Progressive Loading**

1. **Load visible tab first** (topline/other/composite - whichever is active)
2. **Load other tabs on-demand** (when user switches tabs)
3. **Load item plots last** (nested within construct tabs)

### Implementation Architecture

#### Backend Changes:

**New View Endpoints:**
```python
# 1. Main view - returns page WITHOUT plots
def prom_review(request, pk):
    # Current logic BUT skip plot generation
    # Set flag: generate_plots = False
    # Return construct/item data WITHOUT bokeh_plot attribute
    
# 2. Lazy load construct plot
def prom_review_construct_plot(request, pk, construct_id):
    # Get single construct
    # Run aggregation for THIS construct only
    # Generate Bokeh plot
    # Return HTML fragment with plot

# 3. Lazy load item plot  
def prom_review_item_plot(request, pk, item_id):
    # Get single item
    # Get historical responses
    # Generate Bokeh plot
    # Return HTML fragment with plot

# 4. Lazy load all plots for a tab (batch)
def prom_review_tab_plots(request, pk, tab_type):
    # tab_type: 'topline', 'other', 'composite'
    # Generate all plots for constructs in that tab
    # Return JSON with plot HTML for each construct
```

#### Frontend Changes:

**Template Modifications:**

1. **topline_vertical_tabs.html** (line 103-105):
```html
<!-- BEFORE -->
<div class="plot-container mb-3 bg-white rounded p-2" id="plot-{{ score_data.construct.id }}">
    {{ score_data.bokeh_plot|safe }}
</div>

<!-- AFTER -->
<div class="plot-container mb-3 bg-white rounded p-2" 
     id="plot-{{ score_data.construct.id }}"
     hx-get="{% url 'prom_review_construct_plot' patient.id score_data.construct.id %}"
     hx-trigger="revealed"
     hx-swap="innerHTML">
    <!-- Loading placeholder -->
    <div class="flex items-center justify-center h-64">
        <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
        <span class="ml-3 text-gray-600">Loading plot...</span>
    </div>
</div>
```

2. **Same pattern for:**
   - `other_constructs_vertical_tabs.html` (line 103-105)
   - `composite_scores_vertical_tabs.html` (line 108-110)
   - `likert_item_card.html` (line 38-40)
   - `numeric_item_card.html`

**HTMX Triggers:**
- `revealed` - loads when element scrolls into viewport
- `intersect once` - alternative, loads when visible

#### URL Routes:
```python
# patientapp/urls.py
path('patients/<uuid:pk>/prom-review/construct-plot/<uuid:construct_id>/', 
     views.prom_review_construct_plot, 
     name='prom_review_construct_plot'),
     
path('patients/<uuid:pk>/prom-review/item-plot/<uuid:item_id>/', 
     views.prom_review_item_plot, 
     name='prom_review_item_plot'),
```

## Expected Performance Improvement

### Current:
- Initial page load: **12.3 seconds**
- User sees: Nothing (white screen with loader)

### After Lazy Loading:
- Initial page load: **1-2 seconds** (85% faster)
- User sees: Full page with data, scores, summaries
- Plots load progressively: 
  - Visible plots: 1-2 seconds after page load
  - Hidden plots: Load when user scrolls/switches tabs
  - Total time to all plots loaded: Still ~12 seconds, but non-blocking

### User Experience:
✅ Page appears instantly
✅ Can read summaries immediately
✅ Can navigate tabs while plots load
✅ Plots appear progressively (no jarring full-page reload)
✅ Feels much faster even though total time is similar

## Additional Optimizations (Future)

1. **Caching** - Cache aggregated statistics per construct
2. **Batch Loading** - Load all visible plots in one request
3. **WebSockets** - Push plots as they're generated
4. **Service Workers** - Pre-cache plots for offline viewing
5. **Plot Simplification** - Reduce Bokeh complexity for faster rendering

## Implementation Steps

1. ✅ Analyze templates (DONE)
2. Create new view endpoints for lazy loading
3. Modify main view to skip plot generation
4. Update templates with HTMX lazy load attributes
5. Add URL routes
6. Test with single construct
7. Roll out to all constructs and items
8. Add loading indicators and error handling
9. Performance testing and optimization

## Risks & Considerations

- **HTMX dependency**: Already using HTMX, so no new dependency
- **SEO**: Not applicable (authenticated user dashboard)
- **Accessibility**: Ensure loading states are announced to screen readers
- **Error handling**: Need fallback if plot generation fails
- **Filter changes**: Need to clear/reload lazy-loaded plots when filters change
- **Browser compatibility**: HTMX works on all modern browsers

## Filter Integration

When user applies filters:
1. Main content reloads (current behavior)
2. All plot containers reset to loading state
3. Plots lazy-load again with new filter parameters
4. Pass filter params to lazy-load endpoints via URL query string
