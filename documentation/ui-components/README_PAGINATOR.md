# Paginator Component Documentation

## Overview

The Paginator component (`c-paginator`) is a reusable pagination component designed for Django ListView pagination. It provides a responsive, accessible, and customizable pagination interface that works seamlessly with Django's built-in pagination system.

## Component Location
```
templates/cotton/paginator.html
```

## Props Reference

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `page_obj` | Django Page | Required | Django Page object from ListView pagination |
| `is_paginated` | Boolean | Required | Whether pagination is active (from ListView context) |
| `class` | String | "" | Additional CSS classes for the container |
| `show_info` | Boolean | true | Whether to show "Showing X to Y of Z results" text |
| `show_page_numbers` | Boolean | true | Whether to show individual page numbers |
| `preserve_params` | Boolean | true | Whether to preserve URL parameters in pagination links |

## Basic Usage

### 1. Simple Pagination
```html
{% load cotton %}

<c-paginator 
    :page_obj="page_obj" 
    :is_paginated="is_paginated" />
```

### 2. Customized Pagination
```html
<c-paginator 
    :page_obj="page_obj" 
    :is_paginated="is_paginated" 
    show_info="true"
    show_page_numbers="true"
    preserve_params="true"
    class="my-8" />
```

### 3. Minimal Pagination (Mobile-friendly)
```html
<c-paginator 
    :page_obj="page_obj" 
    :is_paginated="is_paginated" 
    show_info="false"
    show_page_numbers="false" />
```

## Features

### Responsive Design
- **Mobile**: Shows only Previous/Next buttons for better touch interaction
- **Desktop**: Full pagination with page numbers and result information
- **Adaptive**: Automatically adjusts based on screen size

### Accessibility
- **ARIA labels**: Proper `aria-label` and `aria-current` attributes
- **Screen reader support**: Hidden text for Previous/Next icons
- **Keyboard navigation**: All links are keyboard accessible
- **Focus states**: Clear focus indicators for keyboard users

### Visual States
- **Current page**: Highlighted with blue background and border
- **Disabled states**: Grayed out Previous/Next when not available
- **Hover effects**: Smooth transitions on interactive elements
- **Loading states**: Consistent styling during navigation

### URL Parameter Preservation
- **Search filters**: Maintains search queries across pages
- **Sort parameters**: Preserves sorting options
- **Custom parameters**: Keeps any additional URL parameters
- **Clean URLs**: Only adds necessary pagination parameters

### HTMX Integration
- **Built-in support**: Automatic HTMX attributes on all pagination links
- **Partial updates**: Updates only the content area, not the full page
- **State preservation**: Maintains search and filter state during navigation
- **Graceful degradation**: Works with or without JavaScript enabled

## Integration with Django Views

### ListView Setup
```python
# views.py
from django.views.generic import ListView
from django.core.paginator import Paginator

class PatientListView(ListView):
    model = Patient
    template_name = 'patientapp/patient_list.html'
    context_object_name = 'patients'
    paginate_by = 10  # Number of items per page
    
    def get_queryset(self):
        queryset = super().get_queryset()
        # Add filtering logic here
        return queryset
```

### Template Integration
```html
<!-- templates/patientapp/patient_list.html -->
{% extends 'base.html' %}
{% load cotton %}

{% block content %}
<div class="container mx-auto px-4">
    <!-- Your list content here -->
    {% for patient in patients %}
        <!-- Patient cards or table rows -->
    {% endfor %}
    
    <!-- Pagination -->
    <c-paginator 
        :page_obj="page_obj" 
        :is_paginated="is_paginated" />
</div>
{% endblock %}
```

## Styling Options

### Container Customization
```html
<!-- Add custom spacing -->
<c-paginator 
    :page_obj="page_obj" 
    :is_paginated="is_paginated" 
    class="mt-8 mb-4" />

<!-- Custom background -->
<c-paginator 
    :page_obj="page_obj" 
    :is_paginated="is_paginated" 
    class="bg-gray-50 shadow-lg" />
```

### Component Variants

#### Minimal Pagination
```html
<!-- Only Previous/Next buttons -->
<c-paginator 
    :page_obj="page_obj" 
    :is_paginated="is_paginated" 
    show_page_numbers="false"
    show_info="false" />
```

#### Info-Only Pagination
```html
<!-- Only show result information -->
<c-paginator 
    :page_obj="page_obj" 
    :is_paginated="is_paginated" 
    show_page_numbers="false"
    show_info="true" />
```

#### Full-Featured Pagination
```html
<!-- All features enabled (default) -->
<c-paginator 
    :page_obj="page_obj" 
    :is_paginated="is_paginated" 
    show_page_numbers="true"
    show_info="true"
    preserve_params="true" />
```

## Advanced Usage

### With Search and Filters
```html
<!-- Search form -->
<form method="get" class="mb-6">
    <input type="text" name="search" value="{{ request.GET.search }}" 
           placeholder="Search patients..." class="form-input">
    <select name="status" class="form-select">
        <option value="">All Statuses</option>
        <option value="active">Active</option>
        <option value="inactive">Inactive</option>
    </select>
    <button type="submit" class="btn btn-primary">Search</button>
</form>

<!-- Results -->
<div class="space-y-4">
    {% for patient in patients %}
        <!-- Patient cards -->
    {% endfor %}
</div>

<!-- Pagination preserves search parameters -->
<c-paginator 
    :page_obj="page_obj" 
    :is_paginated="is_paginated" 
    preserve_params="true" />
```

### Custom Page Ranges
The component shows pages within a range of ±3 from the current page. For large datasets, this provides a good balance between usability and performance.

```
Example with current page 15:
[Previous] [12] [13] [14] [15] [16] [17] [18] [Next]
```

### HTMX Integration

The paginator component has built-in HTMX support for seamless partial page updates. All pagination links automatically include HTMX attributes when used in an HTMX-enabled context.

#### Automatic HTMX Support
```html
<!-- Main template with HTMX container -->
<div id="patientsTable" hx-get="{% url 'patient_list' %}" hx-trigger="load">
    <!-- Partial template content will be loaded here -->
</div>

<!-- In the partial template -->
<c-paginator 
    :page_obj="page_obj" 
    :is_paginated="is_paginated" />
```

#### How It Works
The paginator component automatically adds these HTMX attributes to all pagination links:
- `hx-get`: Same URL as the href attribute
- `hx-target="#patientsTable"`: Targets the main container
- Preserves all URL parameters (search, filters, etc.)

#### View Configuration
```python
# views.py
class PatientListView(ListView):
    model = Patient
    template_name = 'patientapp/patient_list.html'
    paginate_by = 10
    
    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        
        # Return partial template for HTMX requests
        if request.headers.get('HX-Request'):
            self.template_name = 'patientapp/partials/patient_table.html'
            
        return response
```

#### Complete HTMX Example
```html
<!-- Main template: patient_list.html -->
{% extends 'base.html' %}
{% load cotton %}

{% block content %}
<div class="container">
    <!-- Search form with HTMX -->
    <form hx-get="{% url 'patient_list' %}" 
          hx-target="#patientsTable" 
          hx-trigger="change from:select, keyup[target.name=='search'] delay:500ms">
        <!-- Search fields -->
    </form>
    
    <!-- HTMX container -->
    <div id="patientsTable" hx-get="{% url 'patient_list' %}" hx-trigger="load">
        <!-- Content loaded via HTMX -->
    </div>
</div>
{% endblock %}

<!-- Partial template: partials/patient_table.html -->
{% load cotton %}

<!-- List content -->
{% for patient in patients %}
    <!-- Patient cards -->
{% endfor %}

<!-- Pagination with automatic HTMX support -->
<c-paginator 
    :page_obj="page_obj" 
    :is_paginated="is_paginated" />
```

#### Benefits of HTMX Integration
- **No page reloads**: Smooth pagination experience
- **Preserves state**: Search and filter parameters maintained
- **Fast navigation**: Only updates the content area
- **SEO friendly**: URLs still update for bookmarking
- **Graceful degradation**: Works without JavaScript

## Best Practices

### 1. Consistent Pagination Size
```python
# settings.py or view
PAGINATION_SIZE = 20  # Use consistent page sizes across the app

# views.py
class PatientListView(ListView):
    paginate_by = settings.PAGINATION_SIZE
```

### 2. Performance Optimization
```python
# Use select_related and prefetch_related for better performance
class PatientListView(ListView):
    def get_queryset(self):
        return Patient.objects.select_related('institution').prefetch_related('diagnosis_set')
```

### 3. SEO-Friendly URLs
```python
# urls.py
urlpatterns = [
    path('patients/', PatientListView.as_view(), name='patient_list'),
    path('patients/page/<int:page>/', PatientListView.as_view(), name='patient_list_page'),
]
```

### 4. Error Handling
```python
# views.py
from django.core.paginator import EmptyPage, PageNotAnInteger
from django.http import Http404

class PatientListView(ListView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            # Handle pagination errors gracefully
            page = self.request.GET.get('page', 1)
            if not page.isdigit() or int(page) < 1:
                raise Http404("Page not found")
        except (EmptyPage, PageNotAnInteger):
            raise Http404("Page not found")
        return context
```

## Accessibility Features

### Screen Reader Support
- Previous/Next buttons include hidden text descriptions
- Current page is marked with `aria-current="page"`
- Navigation is wrapped in proper `<nav>` element with `aria-label`

### Keyboard Navigation
- All pagination links are keyboard accessible
- Clear focus indicators for keyboard users
- Logical tab order through pagination controls

### Color and Contrast
- High contrast colors for better visibility
- Current page uses blue theme for clear indication
- Disabled states are clearly differentiated

## Browser Support

- **Modern browsers**: Full support for all features
- **IE11**: Basic functionality with graceful degradation
- **Mobile browsers**: Optimized touch-friendly interface
- **Screen readers**: Full accessibility support

## Performance Considerations

### Template Efficiency
- Minimal template logic for fast rendering
- Efficient URL parameter handling
- Optimized for large page ranges

### Network Optimization
- Clean URLs reduce parameter bloat
- Efficient parameter preservation
- Minimal JavaScript requirements

## Troubleshooting

### Common Issues

#### Pagination Not Showing
```python
# Ensure your view has pagination enabled
class MyListView(ListView):
    paginate_by = 10  # This is required
```

#### Parameters Not Preserved
```html
<!-- Ensure preserve_params is enabled -->
<c-paginator 
    :page_obj="page_obj" 
    :is_paginated="is_paginated" 
    preserve_params="true" />
```

#### Styling Issues
```html
<!-- Check for CSS conflicts -->
<c-paginator 
    :page_obj="page_obj" 
    :is_paginated="is_paginated" 
    class="custom-pagination" />
```

## Related Components
- [`c-list_card`](README_LIST_CARDS.md) - For list displays that use pagination
- [`c-card`](README_CARDS.md) - Individual item containers
- [Filter Dropdowns](README_DROPDOWNS.md) - For search and filter functionality

## Examples in Codebase
- `templates/patientapp/partials/patient_table.html` - Patient list with pagination
- `templates/patientapp/patient_list.html` - Main list page implementation

## Migration from Custom Pagination

### Before (Custom HTML)
```html
{% if is_paginated %}
<div class="pagination">
    {% if page_obj.has_previous %}
        <a href="?page={{ page_obj.previous_page_number }}">Previous</a>
    {% endif %}
    
    <span>Page {{ page_obj.number }} of {{ page_obj.paginator.num_pages }}</span>
    
    {% if page_obj.has_next %}
        <a href="?page={{ page_obj.next_page_number }}">Next</a>
    {% endif %}
</div>
{% endif %}
```

### After (Component)
```html
<c-paginator 
    :page_obj="page_obj" 
    :is_paginated="is_paginated" />
```

## Benefits

### 1. **Consistency**
- Uniform pagination across all list views
- Standardized styling and behavior
- Consistent accessibility features

### 2. **Maintainability**
- Centralized pagination logic
- Easy to update styling globally
- Reduced code duplication

### 3. **User Experience**
- Responsive design for all devices
- Smooth transitions and hover effects
- Clear visual feedback

### 4. **Developer Experience**
- Simple integration with Django views
- Flexible customization options
- Comprehensive documentation 