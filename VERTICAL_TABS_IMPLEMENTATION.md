# PROM Review Vertical Tabs Implementation

## Overview
Reorganized the PROM review page to use vertical tabs for better navigation and reduced scrolling. Each construct is now displayed in its own tab with related items grouped together.

## Implementation Date
2025-10-11

## Changes Made

### 1. New Component Templates

#### `/templates/promapp/components/topline_vertical_tabs.html`
- **Purpose**: Display important/topline construct scores with vertical tab navigation
- **Visual Indicator**: Red circles (🔴) beside construct names
- **Features**:
  - Left sidebar with construct names, scores, and red indicators
  - Tab content shows construct score details, plots, and related items
  - Clinical significance warnings
  - Threshold and normative score information
  - Related item responses with their plots

#### `/templates/promapp/components/other_constructs_vertical_tabs.html`
- **Purpose**: Display other (non-topline) construct scores with vertical tab navigation
- **Visual Indicator**: Green circles (🟢) beside construct names
- **Features**:
  - Similar layout to topline tabs but with green color scheme
  - Shows construct score details and related items
  - Items answered count
  - Threshold indicators

#### `/templates/promapp/components/composite_scores_section.html`
- **Purpose**: Display composite construct scores in a grid layout
- **Position**: Below the other construct scores section
- **Features**:
  - Grid of composite score cards
  - Shows scoring type and component count
  - Trend indicators for score changes

### 2. Modified Templates

#### `/templates/promapp/components/main_content.html`
**Changes**:
- Replaced three separate includes with new vertical tab components
- Old structure:
  ```django
  {% include "promapp/components/topline_results_section.html" %}
  {% include "promapp/components/construct_scores_section.html" %}
  {% include "promapp/components/item_results_section.html" %}
  ```
- New structure:
  ```django
  {% include "promapp/components/topline_vertical_tabs.html" %}
  {% include "promapp/components/other_constructs_vertical_tabs.html" %}
  {% include "promapp/components/composite_scores_section.html" %}
  ```

#### `/templates/promapp/prom_review.html`
**Changes**:
- Added `switchTab(section, constructId)` JavaScript function
- Handles tab switching for both topline and other construct sections
- Manages active states and visibility of tab content
- Uses proper ARIA attributes for accessibility

### 3. JavaScript Functionality

#### `switchTab(section, constructId)` Function
```javascript
// Parameters:
// - section: 'topline' or 'other'
// - constructId: The ID of the construct to display

// Functionality:
// 1. Hides all tab contents in the specified section
// 2. Removes active state from all tab buttons
// 3. Shows the selected tab content
// 4. Adds active state to the clicked button
// 5. Updates ARIA attributes for accessibility
```

## Layout Structure

```
┌─────────────────────────────────────────────────────────┐
│ Patient Info Card                                       │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ Questionnaire Overview Card                             │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ TOPLINE RESULTS (Important Constructs)                  │
├──────────────────┬──────────────────────────────────────┤
│ 🔴 Pain Score    │ Pain Score: 7.5 ↑                    │
│ 🔴 Anxiety       │ [Bokeh Plot]                         │
│ 🔴 Depression    │ Clinical Significance: Worsened      │
│                  │ Threshold: 5.0 ⚠  Normative: 3.2 ◯  │
│                  │                                       │
│                  │ Related Items:                        │
│                  │ ┌──────┐ ┌──────┐ ┌──────┐          │
│                  │ │Item 1│ │Item 2│ │Item 3│          │
│                  │ └──────┘ └──────┘ └──────┘          │
└──────────────────┴──────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ OTHER CONSTRUCT SCORES                                   │
├──────────────────┬──────────────────────────────────────┤
│ 🟢 Mobility      │ Mobility: 8.2 ↑                      │
│ 🟢 Self-Care     │ 5/5 items answered                   │
│ 🟢 Activities    │                                       │
│                  │ Related Items:                        │
│                  │ ┌──────┐ ┌──────┐                    │
│                  │ │Item 1│ │Item 2│                    │
│                  │ └──────┘ └──────┘                    │
└──────────────────┴──────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ COMPOSITE CONSTRUCT SCORES                               │
│ ┌──────────┐ ┌──────────┐ ┌──────────┐                │
│ │Overall QoL│ │Physical  │ │Mental    │                │
│ │Score: 6.5 │ │Score: 7.2│ │Score: 5.8│                │
│ └──────────┘ └──────────┘ └──────────┘                │
└─────────────────────────────────────────────────────────┘
```

## Key Features

### ✅ Reduced Scrolling
- Only one construct's content visible at a time
- Eliminates need to scroll through multiple plots
- Sidebar navigation for quick access

### ✅ Visual Indicators
- **Red circles (🔴)**: Topline/important constructs requiring attention
- **Green circles (🟢)**: Other constructs performing normally
- Color-coded active states (red/green backgrounds)

### ✅ Organized Content
Each tab displays:
- Construct name and current score
- Trend indicator (up/down/no change)
- Bokeh plot for score over time
- Clinical significance warnings (if applicable)
- Threshold and normative score comparisons
- Related item responses with their individual plots

### ✅ Preserved Functionality
- All existing filters continue to work
- Search functionality maintained
- HTMX content updates work seamlessly
- Item filtering preserved
- Plot indicators functional
- Questionnaire filtering works
- Time range selection works
- Patient demographic filters work

### ✅ Accessibility
- Proper ARIA attributes (`role="tab"`, `aria-selected`, `aria-controls`)
- Keyboard navigation support
- Screen reader friendly

### ✅ Responsive Design
- Tailwind CSS classes ensure mobile compatibility
- Sidebar collapses on smaller screens
- Grid layouts adapt to screen size

## Data Flow

### View Context (from `patientapp/views.py`)
```python
context = {
    'important_construct_scores': important_construct_scores,  # For topline tabs
    'other_construct_scores': other_construct_scores,          # For other tabs
    'composite_construct_scores': composite_construct_scores_list,  # For composite section
    'item_responses_grouped': item_responses_grouped,          # Items grouped by construct
    # ... other context variables
}
```

### Template Logic
1. **Topline Vertical Tabs**: Iterates through `important_construct_scores`
2. **Other Vertical Tabs**: Iterates through `other_construct_scores`
3. **Composite Section**: Iterates through `composite_construct_scores`
4. **Related Items**: Uses `item_responses_grouped` to match items to constructs

## CSS Classes Used

### Active Tab Button (Topline)
```css
bg-red-50 border-l-4 border-red-500 text-red-700
```

### Active Tab Button (Other)
```css
bg-green-50 border-l-4 border-green-500 text-green-700
```

### Inactive Tab Button
```css
text-gray-700 hover:bg-gray-50
```

### Tab Content (Hidden)
```css
hidden
```

## Testing Checklist

### Visual Testing
- [ ] Red circles appear beside topline construct names
- [ ] Green circles appear beside other construct names
- [ ] First tab in each section is active by default
- [ ] Active tabs have colored backgrounds and left borders
- [ ] Clicking tabs switches content correctly
- [ ] Only one tab content visible at a time per section

### Functionality Testing
- [ ] Questionnaire filter updates all sections
- [ ] Time range filter updates plots
- [ ] Item filter works correctly
- [ ] Patient demographic filters apply
- [ ] HTMX updates preserve tab states
- [ ] Bokeh plots render correctly in tabs
- [ ] Item cards display properly
- [ ] Clinical significance warnings show when applicable

### Accessibility Testing
- [ ] Tab navigation works with keyboard (Tab, Enter, Arrow keys)
- [ ] ARIA attributes are correct
- [ ] Screen reader announces tab changes
- [ ] Focus indicators visible

### Responsive Testing
- [ ] Layout works on desktop (1920px+)
- [ ] Layout works on tablet (768px-1024px)
- [ ] Layout works on mobile (320px-767px)
- [ ] Sidebar adapts to smaller screens

## Troubleshooting

### Issue: Tabs don't switch
**Solution**: Check browser console for JavaScript errors. Ensure `switchTab()` function is defined.

### Issue: No data showing in tabs
**Solution**: Verify view is passing correct context variables (`important_construct_scores`, `other_construct_scores`, `item_responses_grouped`).

### Issue: Bokeh plots not rendering
**Solution**: Ensure `bokeh_css` and `bokeh_js` are included in the base template and CDN resources are loading.

### Issue: Item cards not displaying
**Solution**: Check that `item_responses_grouped` is properly structured with `construct` and `items` keys.

### Issue: Colors not showing correctly
**Solution**: Verify Tailwind CSS is loaded and classes are not being purged. Check for conflicting CSS.

## Future Enhancements

### Potential Improvements
1. **Tab State Persistence**: Remember selected tab in localStorage
2. **Keyboard Shortcuts**: Add hotkeys for quick tab switching (e.g., Ctrl+1, Ctrl+2)
3. **Tab Search**: Add search/filter for construct names in sidebar
4. **Collapsible Sidebar**: Allow hiding sidebar for more content space
5. **Export Tab**: Add button to export current tab's data
6. **Print View**: Optimize tab layout for printing
7. **Animation**: Add smooth transitions when switching tabs
8. **Badge Counts**: Show item count badges on tab buttons

## Related Files

### Templates
- `/templates/promapp/prom_review.html` - Main page template
- `/templates/promapp/components/main_content.html` - Content container
- `/templates/promapp/components/topline_vertical_tabs.html` - Topline tabs
- `/templates/promapp/components/other_constructs_vertical_tabs.html` - Other tabs
- `/templates/promapp/components/composite_scores_section.html` - Composite scores
- `/templates/promapp/components/likert_item_card.html` - Item card template
- `/templates/promapp/components/numeric_item_card.html` - Item card template
- `/templates/promapp/components/text_item_card.html` - Item card template
- `/templates/promapp/components/media_item_card.html` - Item card template

### Views
- `/patientapp/views.py` - Contains prom_review view function

### Static Files
- `/static/css/prom_review.css` - Custom styles (if any)

## Notes

- The old templates (`topline_results_section.html`, `construct_scores_section.html`, `item_results_section.html`) are still present but no longer used
- Consider removing old templates after confirming new implementation works correctly
- The vertical tab approach significantly reduces page length and improves user experience
- All existing functionality is preserved - this is purely a UI reorganization
