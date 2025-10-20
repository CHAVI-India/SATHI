# Testing Guide: Vertical Tabs Implementation

## Quick Test Steps

### 1. Access the PROM Review Page
Navigate to a patient's PROM review page:
```
/patients/<patient_id>/prom-review/
```

### 2. Visual Verification

#### Expected Layout
You should see:

**Topline Results Section** (if patient has important constructs):
- Section header: "Topline Results"
- Left sidebar with construct names
- **Red circles (🔴)** beside each construct name
- Current score displayed next to each construct
- First construct tab is active (red background, left border)

**Other Construct Scores Section** (if patient has other constructs):
- Section header: "Other Construct Scores"
- Left sidebar with construct names
- **Green circles (🟢)** beside each construct name
- Current score displayed next to each construct
- First construct tab is active (green background, left border)

**Composite Construct Scores Section** (if applicable):
- Section header: "Composite Construct Scores"
- Grid of composite score cards
- No tabs, just card display

### 3. Tab Interaction Testing

#### Test Topline Tabs
1. Click on the second construct in the topline sidebar
2. **Expected**: 
   - Previous tab content disappears
   - New tab content appears
   - Clicked button gets red background and left border
   - Previous button returns to gray

#### Test Other Construct Tabs
1. Click on different constructs in the other construct sidebar
2. **Expected**:
   - Tab content switches smoothly
   - Active button has green background and left border
   - Only one tab content visible at a time

### 4. Content Verification

For each active tab, verify it displays:
- ✅ Construct name (large, bold)
- ✅ Current score (large number)
- ✅ Trend indicator (up/down/no change arrow)
- ✅ "Better score direction" badge (e.g., "Higher is Better")
- ✅ Bokeh plot showing score over time
- ✅ Clinical significance warning (if applicable, orange box)
- ✅ Threshold and normative score info at bottom
- ✅ "Related Items" section with item cards
- ✅ Item plots within each item card

### 5. Filter Testing

#### Test Questionnaire Filter
1. Change the questionnaire filter dropdown
2. **Expected**:
   - Page updates via HTMX
   - Tabs remain functional
   - Data updates for selected questionnaire
   - Tab structure preserved

#### Test Time Range Filter
1. Change time range (e.g., "3 submissions" to "5 submissions")
2. **Expected**:
   - Plots update with new data
   - Tabs remain functional
   - Active tab stays selected

#### Test Item Filter
1. Select specific items from the item filter
2. **Expected**:
   - Only selected items appear in "Related Items" sections
   - Construct scores still visible
   - Tabs work correctly

### 6. Edge Cases

#### No Important Constructs
- **Expected**: Topline Results section doesn't appear at all
- **Expected**: Other Construct Scores section appears normally

#### No Other Constructs
- **Expected**: Other Construct Scores section doesn't appear
- **Expected**: Topline Results section appears normally

#### No Composite Scores
- **Expected**: Composite Construct Scores section doesn't appear

#### Single Construct
- **Expected**: Tab navigation still works
- **Expected**: Single tab is active by default

### 7. Responsive Testing

#### Desktop (1920px+)
- Sidebar width: 256px (w-64)
- Content area: Flexible (flex-1)
- Item grid: 3 columns (lg:grid-cols-3)

#### Tablet (768px-1024px)
- Item grid: 2 columns (md:grid-cols-2)
- Sidebar should remain visible

#### Mobile (320px-767px)
- Item grid: 1 column
- Check if sidebar adapts appropriately

### 8. JavaScript Console Check

Open browser console (F12) and verify:
- ✅ No JavaScript errors
- ✅ `switchTab` function is defined
- ✅ No Bokeh rendering errors

### 9. Accessibility Testing

#### Keyboard Navigation
1. Press Tab key to navigate through tab buttons
2. Press Enter or Space to activate a tab
3. **Expected**: Tabs switch correctly with keyboard

#### Screen Reader Testing (if available)
1. Use screen reader to navigate tabs
2. **Expected**: 
   - Tab role announced
   - Selected state announced
   - Construct names read correctly

### 10. Performance Check

#### Page Load
- **Expected**: Page loads without significant delay
- **Expected**: All Bokeh plots render within 2-3 seconds

#### Tab Switching
- **Expected**: Instant switching (no delay)
- **Expected**: No flickering or layout shift

## Common Issues and Solutions

### Issue: "switchTab is not defined"
**Cause**: JavaScript not loaded or syntax error
**Solution**: Check `/templates/promapp/prom_review.html` for the `switchTab()` function

### Issue: All tabs visible at once
**Cause**: CSS classes not applying correctly
**Solution**: Verify Tailwind CSS is loaded and `hidden` class works

### Issue: No red/green circles
**Cause**: CSS not rendering colored spans
**Solution**: Check that `bg-red-500` and `bg-green-500` classes are available

### Issue: Bokeh plots not showing
**Cause**: Bokeh resources not loaded or plot data missing
**Solution**: Verify `bokeh_css` and `bokeh_js` in context and CDN accessible

### Issue: Items not grouped correctly
**Cause**: `item_responses_grouped` structure incorrect
**Solution**: Check view logic for grouping items by construct

### Issue: Clicking tabs does nothing
**Cause**: `onclick` handler not firing
**Solution**: Check browser console for errors, verify button IDs match

## Success Criteria

✅ **Visual**: Red circles for topline, green circles for other constructs
✅ **Navigation**: Clicking tabs switches content smoothly
✅ **Content**: All construct details and related items display correctly
✅ **Filters**: All existing filters continue to work
✅ **Plots**: Bokeh plots render in all tabs
✅ **Responsive**: Layout adapts to different screen sizes
✅ **Accessibility**: Keyboard navigation and ARIA attributes work
✅ **Performance**: No lag when switching tabs

## Regression Testing

Verify these existing features still work:
- [ ] Questionnaire filter dropdown
- [ ] Time range selection
- [ ] Date picker
- [ ] Item filter with search
- [ ] Patient demographic filters
- [ ] Population comparison toggle
- [ ] Plot indicators checkboxes
- [ ] Text response "Show more" buttons
- [ ] Image modal for media items

## Browser Compatibility

Test in:
- [ ] Chrome/Chromium (latest)
- [ ] Firefox (latest)
- [ ] Safari (if available)
- [ ] Edge (latest)

## Rollback Plan

If critical issues are found:

1. Revert `/templates/promapp/components/main_content.html`:
```django
<!-- Topline Results -->
{% include "promapp/components/topline_results_section.html" %}

<!-- Construct Scores -->
{% include "promapp/components/construct_scores_section.html" %}

<!-- Item-wise Results -->
{% include "promapp/components/item_results_section.html" %}
```

2. Remove `switchTab()` function from `/templates/promapp/prom_review.html`

3. Old templates will work immediately as they still exist

## Sign-off

After testing, confirm:
- [ ] All visual elements appear correctly
- [ ] Tab navigation works smoothly
- [ ] All filters and features work
- [ ] No JavaScript errors
- [ ] Performance is acceptable
- [ ] Accessibility requirements met

**Tested by**: _______________  
**Date**: _______________  
**Status**: ⬜ Pass ⬜ Fail ⬜ Needs fixes
