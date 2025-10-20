# List Card Component Documentation

## Overview

The List Card component (`c-list_card`) is a specialized component designed to handle empty states for list displays. Due to Django Cotton's limitations with slots in loops, this component focuses on providing consistent empty state handling while actual item rendering is done through manual iteration with individual card components.

## Component Location
```
templates/cotton/list_card.html
```

## Key Limitation
⚠️ **Important**: Django Cotton slots do not work properly within loops. Therefore, this component only handles empty states, and actual item rendering must be done through manual iteration in your templates.

## Props Reference

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `items` | QuerySet/List | Required | The collection of items to check for empty state |
| `empty_message` | String | "No items found" | Message displayed when no items exist |
| `class` | String | "" | Additional CSS classes for the empty state container |

## Usage Pattern

### 1. Basic Empty State Handling
```html
{% load cotton %}

<!-- Check for empty state -->
<c-list_card :items="patients" empty_message="{% translate 'No patients found' %}" />

<!-- Manual iteration for actual content -->
<div class="space-y-4">
    {% for patient in patients %}
    <c-card shadow="sm" border="light" padding="md" class="w-full">
        <!-- Your item content here -->
        <div class="flex justify-between items-center">
            <div>
                <h3 class="font-medium">{{ patient.name }}</h3>
                <p class="text-sm text-gray-500">{{ patient.patient_id }}</p>
            </div>
            <div class="flex space-x-2">
                <c-view_button href="{% url 'patient_detail' patient.id %}">
                    View
                </c-view_button>
            </div>
        </div>
    </c-card>
    {% endfor %}
</div>
```

### 2. Complete Patient List Example
```html
{% load i18n %}
{% load cotton %}

<!-- Empty state handling -->
<c-list_card :items="patients" empty_message="{% translate 'No patients found' %}" />

<!-- Patient cards with comprehensive information -->
<div class="space-y-4">
    {% for patient in patients %}
    <c-card 
        shadow="sm" 
        border="light" 
        padding="md" 
        class="w-full hover:shadow-md transition-shadow duration-200">
        
        <div class="space-y-4">
            <!-- Top row: Patient info and actions -->
            <div class="flex justify-between items-start">
                <div class="flex-1 min-w-0">
                    <div class="flex items-center space-x-4">
                        <div class="flex-1 min-w-0">
                            <h3 class="text-lg font-medium text-gray-900 truncate">{{ patient.name }}</h3>
                            <p class="text-sm text-gray-600">ID: {{ patient.patient_id }}</p>
                        </div>
                        <div class="flex items-center space-x-6 text-sm text-gray-600">
                            <span>Age: {{ patient.age }}</span>
                            <span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                                {{ patient.gender }}
                            </span>
                            {% if patient.institution %}
                            <span>{{ patient.institution.name }}</span>
                            {% endif %}
                        </div>
                    </div>
                </div>
                
                <div class="flex space-x-2 ml-4">
                    <c-view_button href="{% url 'patient_detail' patient.id %}" size="sm">
                        {% translate "View" %}
                    </c-view_button>
                    <c-link_button href="{% url 'patient_questionnaire_management' patient.id %}" variant="success" size="sm">
                        {% translate "Manage" %}
                    </c-link_button>
                </div>
            </div>
            
            <!-- Bottom row: Medical information -->
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4 pt-3 border-t border-gray-100">
                <!-- Diagnoses -->
                <div>
                    <h4 class="text-sm font-medium text-gray-700 mb-2">{% translate "Diagnoses" %}</h4>
                    {% if patient.diagnosis_set.all %}
                        <div class="flex flex-wrap gap-1">
                            {% for diagnosis in patient.diagnosis_set.all %}
                            <span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                                {{ diagnosis.diagnosis|truncatechars:30 }}
                            </span>
                            {% endfor %}
                        </div>
                    {% else %}
                        <p class="text-sm text-gray-500 italic">{% translate "No diagnoses recorded" %}</p>
                    {% endif %}
                </div>
                
                <!-- Treatments -->
                <div>
                    <h4 class="text-sm font-medium text-gray-700 mb-2">{% translate "Treatments" %}</h4>
                    {% regroup patient.diagnosis_set.all by id as diagnosis_list %}
                    {% if diagnosis_list %}
                        <div class="flex flex-wrap gap-1">
                            {% for diagnosis in patient.diagnosis_set.all %}
                                {% for treatment in diagnosis.treatment_set.all %}
                                    {% for treatment_type in treatment.treatment_type.all %}
                                    <span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                                        {{ treatment_type.treatment_type|truncatechars:25 }}
                                    </span>
                                    {% endfor %}
                                {% endfor %}
                            {% endfor %}
                        </div>
                    {% else %}
                        <p class="text-sm text-gray-500 italic">{% translate "No treatments recorded" %}</p>
                    {% endif %}
                </div>
            </div>
        </div>
    </c-card>
    {% endfor %}
</div>
```

## Empty State Features

### Visual Design
- **Clean layout**: Centered content with proper spacing
- **Icon**: Document icon to represent empty lists
- **Message**: Customizable text with translation support
- **Styling**: Consistent with other components (white background, border, padding)

### Customization
```html
<!-- Custom empty message -->
<c-list_card 
    :items="items" 
    empty_message="{% translate 'No records available at this time' %}" />

<!-- Additional CSS classes -->
<c-list_card 
    :items="items" 
    class="mb-8 shadow-lg" 
    empty_message="{% translate 'No data found' %}" />
```

## Integration with Other Components

### Recommended Card Components
- **`c-card`**: For individual item containers
- **`c-field_display`**: For structured data display within cards
- **Action buttons**: `c-view_button`, `c-edit_button`, `c-delete_button`, etc.

### Layout Patterns
```html
<!-- Spacing between cards -->
<div class="space-y-4">
    {% for item in items %}
    <c-card>...</c-card>
    {% endfor %}
</div>

<!-- Grid layout for smaller cards -->
<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
    {% for item in items %}
    <c-card>...</c-card>
    {% endfor %}
</div>
```

## Best Practices

### 1. Always Handle Empty States
```html
<!-- ✅ Good: Always include empty state handling -->
<c-list_card :items="items" empty_message="{% translate 'No items found' %}" />
<div class="space-y-4">
    {% for item in items %}
    <!-- item content -->
    {% endfor %}
</div>

<!-- ❌ Bad: No empty state handling -->
<div class="space-y-4">
    {% for item in items %}
    <!-- item content -->
    {% endfor %}
</div>
```

### 2. Use Semantic HTML
```html
<!-- ✅ Good: Proper semantic structure -->
<c-card>
    <article class="space-y-4">
        <header>
            <h3>{{ item.title }}</h3>
        </header>
        <main>
            <!-- content -->
        </main>
        <footer>
            <!-- actions -->
        </footer>
    </article>
</c-card>
```

### 3. Responsive Design
```html
<!-- ✅ Good: Responsive layouts -->
<div class="grid grid-cols-1 md:grid-cols-2 gap-4 pt-3 border-t border-gray-100">
    <div><!-- Left column --></div>
    <div><!-- Right column --></div>
</div>
```

### 4. Consistent Spacing
```html
<!-- ✅ Good: Consistent spacing classes -->
<div class="space-y-4">        <!-- Between cards -->
    <c-card class="space-y-4"> <!-- Within cards -->
        <div class="space-x-2"> <!-- Between inline elements -->
```

## Migration from Table-Based Lists

### Before (Table)
```html
<table class="min-w-full">
    <thead>
        <tr>
            <th>Name</th>
            <th>ID</th>
            <th>Actions</th>
        </tr>
    </thead>
    <tbody>
        {% for patient in patients %}
        <tr>
            <td>{{ patient.name }}</td>
            <td>{{ patient.patient_id }}</td>
            <td>
                <a href="{% url 'patient_detail' patient.id %}">View</a>
            </td>
        </tr>
        {% empty %}
        <tr>
            <td colspan="3">No patients found</td>
        </tr>
        {% endfor %}
    </tbody>
</table>
```

### After (List Cards)
```html
<c-list_card :items="patients" empty_message="{% translate 'No patients found' %}" />
<div class="space-y-4">
    {% for patient in patients %}
    <c-card shadow="sm" border="light" padding="md">
        <div class="flex justify-between items-center">
            <div>
                <h3 class="font-medium">{{ patient.name }}</h3>
                <p class="text-sm text-gray-500">{{ patient.patient_id }}</p>
            </div>
            <c-view_button href="{% url 'patient_detail' patient.id %}">
                View
            </c-view_button>
        </div>
    </c-card>
    {% endfor %}
</div>
```

## Benefits

### 1. **Flexibility**
- No table constraints
- Complex layouts possible
- Easy responsive design

### 2. **Consistency**
- Standardized empty states
- Uniform card styling
- Component-based approach

### 3. **User Experience**
- Better mobile experience
- Hover effects and transitions
- Clear visual hierarchy

### 4. **Maintainability**
- Reusable components
- Centralized styling
- Easy to update

## Technical Notes

### Django Cotton Limitations
- **Slots in loops**: Don't work reliably
- **Variable scoping**: Limited in nested contexts
- **Performance**: Manual iteration is more predictable

### Workarounds
- **Manual iteration**: Use standard Django template loops
- **Empty state separation**: Handle empty states separately from content
- **Component composition**: Combine multiple simple components

## Related Components
- [`c-card`](README_CARDS.md) - Individual card containers
- [`c-field_display`](README_CARDS.md) - Structured field display
- [Action Buttons](README_ACTION_BUTTONS.md) - Standardized action buttons
- [Dropdowns](README_DROPDOWNS.md) - Form and filter dropdowns

## Examples in Codebase
- `templates/patientapp/partials/patient_table.html` - Complete patient list implementation
- `templates/patientapp/patient_list.html` - Main list page structure 