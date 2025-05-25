# List Card Component Documentation

The List Card component (`c-list_card`) provides a modern, responsive alternative to traditional HTML tables for displaying collections of items. It supports dynamic fields, embedded components, and flexible layouts.

## Component Overview

The List Card component automatically handles:
- **Responsive layouts** (grid or list)
- **Dynamic item rendering** with access to each item via `{{ item }}`
- **Empty states** with customizable messages
- **Header with item counts** and action buttons
- **Hover effects** and smooth transitions
- **Embedded components** like buttons within each item

---

## Props

| Prop | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `title` | string | ❌ | - | List title/header text |
| `subtitle` | string | ❌ | - | Optional subtitle below the title |
| `items` | list/QuerySet | ✅ | - | Collection of items to display |
| `empty_message` | string | ❌ | `"No items found"` | Message when no items exist |
| `show_count` | boolean | ❌ | `true` | Whether to show item count in header |
| `class` | string | ❌ | - | Additional CSS classes for container |
| `item_class` | string | ❌ | - | Additional CSS classes for each item |
| `shadow` | string | ❌ | `"md"` | Shadow level: "none", "sm", "md", "lg", "xl" |
| `border` | string | ❌ | `"light"` | Border style: "none", "light", "medium", "strong" |
| `padding` | string | ❌ | `"md"` | Container padding: "none", "sm", "md", "lg", "xl" |
| `item_padding` | string | ❌ | `"sm"` | Individual item padding: "none", "sm", "md", "lg" |
| `layout` | string | ❌ | `"grid"` | Layout style: "grid", "list" |
| `columns` | string | ❌ | `"2"` | Grid columns: "1", "2", "3", "4", "auto" |
| `gap` | string | ❌ | `"md"` | Gap between items: "sm", "md", "lg" |
| `header_actions` | string | ❌ | - | HTML content for header action buttons |

---

## Usage Examples

### Basic Patient List

```html
{% load cotton %}

<c-list_card title="Patients" items="{{ patients }}">
    <div class="flex justify-between items-start">
        <div>
            <h3 class="font-medium text-gray-900">{{ item.name }}</h3>
            <p class="text-sm text-gray-500">ID: {{ item.patient_id }}</p>
            <p class="text-xs text-gray-400">{{ item.institution.name }}</p>
        </div>
        <div class="flex space-x-2">
            <c-view_button href="{% url 'patient_detail' item.id %}">
                View
            </c-view_button>
            <c-edit_button href="{% url 'patient_update' item.id %}">
                Edit
            </c-edit_button>
        </div>
    </div>
</c-list_card>
```

### List Layout with Action Buttons

```html
<c-list_card 
    title="Treatment Types" 
    items="{{ treatment_types }}"
    layout="list"
    columns="1">
    <div class="flex justify-between items-center">
        <div>
            <h3 class="font-medium">{{ item.treatment_type }}</h3>
            <p class="text-sm text-gray-500">{{ item.description }}</p>
        </div>
        <div class="flex space-x-2">
            <c-edit_button href="{% url 'treatment_type_update' item.id %}">
                Edit
            </c-edit_button>
            <c-delete_button href="{% url 'treatment_type_delete' item.id %}">
                Delete
            </c-delete_button>
        </div>
    </div>
</c-list_card>
```

### Grid Layout with Field Displays

```html
<c-list_card 
    title="Diagnoses" 
    items="{{ diagnoses }}"
    columns="3"
    item_padding="md">
    <div class="space-y-3">
        <h3 class="font-medium text-lg">{{ item.diagnosis }}</h3>
        
        <div class="space-y-2">
            <c-field_display 
                label="Patient"
                value="{{ item.patient.name }}"
                layout="horizontal" />
            
            <c-field_display 
                label="Date"
                value="{{ item.created_date }}"
                type="date"
                layout="horizontal" />
            
            <c-field_display 
                label="Status"
                value="{{ item.status }}"
                type="badge"
                badge_color="green"
                layout="horizontal" />
        </div>
        
        <div class="flex space-x-2 pt-2">
            <c-view_button href="{% url 'diagnosis_detail' item.id %}" size="sm">
                View
            </c-view_button>
            <c-edit_button href="{% url 'diagnosis_update' item.id %}" size="sm">
                Edit
            </c-edit_button>
        </div>
    </div>
</c-list_card>
```

### With Header Actions

```html
<c-list_card 
    title="Recent Patients" 
    subtitle="Last 10 patients added"
    items="{{ recent_patients }}"
    header_actions='<c-create_button href="{% url "patient_create" %}">Add Patient</c-create_button>'>
    <div class="flex items-center space-x-4">
        <div class="flex-shrink-0">
            <div class="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center">
                <span class="text-blue-600 font-medium">{{ item.name|first }}</span>
            </div>
        </div>
        <div class="flex-1 min-w-0">
            <h3 class="font-medium text-gray-900 truncate">{{ item.name }}</h3>
            <p class="text-sm text-gray-500">{{ item.patient_id }}</p>
        </div>
        <div class="flex space-x-2">
            <c-view_button href="{% url 'patient_detail' item.id %}" size="sm">
                View
            </c-view_button>
        </div>
    </div>
</c-list_card>
```

### Compact List with Badges

```html
<c-list_card 
    title="Active Treatments" 
    items="{{ active_treatments }}"
    layout="list"
    item_padding="sm"
    gap="sm">
    <div class="flex justify-between items-center">
        <div class="flex items-center space-x-3">
            <div>
                <h4 class="font-medium text-sm">{{ item.treatment_intent }}</h4>
                <p class="text-xs text-gray-500">{{ item.patient.name }}</p>
            </div>
        </div>
        <div class="flex items-center space-x-3">
            <c-field_display 
                label=""
                value="{{ item.status }}"
                type="badge"
                badge_color="{% if item.status == 'Active' %}green{% else %}gray{% endif %}" />
            
            <div class="flex space-x-1">
                <c-edit_button href="{% url 'treatment_update' item.id %}" size="sm">
                    Edit
                </c-edit_button>
            </div>
        </div>
    </div>
</c-list_card>
```

---

## Layout Options

### Grid Layout (Default)
- **Responsive columns** that adapt to screen size
- **Card-like appearance** for each item
- **Best for**: Items with multiple fields or complex content

```html
<c-list_card items="{{ items }}" layout="grid" columns="3">
    <!-- Item content -->
</c-list_card>
```

### List Layout
- **Single column** with horizontal items
- **Compact appearance** for simple items
- **Best for**: Simple items with minimal content

```html
<c-list_card items="{{ items }}" layout="list">
    <!-- Item content -->
</c-list_card>
```

---

## Column Options

| Columns | Responsive Behavior |
|---------|-------------------|
| `"1"` | Always single column |
| `"2"` | 1 col mobile → 2 cols tablet+ |
| `"3"` | 1 col mobile → 2 cols tablet → 3 cols desktop |
| `"4"` | 1 col mobile → 2 cols tablet → 3 cols desktop → 4 cols xl |
| `"auto"` | 1 col mobile → 2 cols sm → 3 cols lg → 4 cols xl |

---

## Styling Options

### Shadow Levels
- `shadow="none"` - No shadow
- `shadow="sm"` - Small shadow
- `shadow="md"` - Medium shadow (default)
- `shadow="lg"` - Large shadow
- `shadow="xl"` - Extra large shadow

### Border Styles
- `border="none"` - No border
- `border="light"` - Light gray border (default)
- `border="medium"` - Medium gray border
- `border="strong"` - Strong gray border

### Padding Levels
- `padding="none"` - No container padding
- `padding="sm"` - Small container padding
- `padding="md"` - Medium container padding (default)
- `padding="lg"` - Large container padding
- `padding="xl"` - Extra large container padding

### Item Padding
- `item_padding="none"` - No item padding
- `item_padding="sm"` - Small item padding (default)
- `item_padding="md"` - Medium item padding
- `item_padding="lg"` - Large item padding

---

## Best Practices

1. **Use Semantic Content**: Structure item content with proper headings and descriptions
2. **Consistent Action Placement**: Place action buttons in the same position across items
3. **Responsive Design**: Choose appropriate column counts for your content
4. **Empty States**: Provide meaningful empty messages for better UX
5. **Loading States**: Consider adding loading indicators for dynamic content
6. **Accessibility**: Use proper heading hierarchy and ARIA labels
7. **Performance**: Use pagination for large datasets

---

## Migration from Tables

### Before (Traditional Table)
```html
<table class="table">
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
                <a href="{% url 'patient_update' patient.id %}">Edit</a>
            </td>
        </tr>
        {% endfor %}
    </tbody>
</table>
```

### After (List Card)
```html
{% load cotton %}

<c-list_card title="Patients" items="{{ patients }}">
    <div class="flex justify-between items-start">
        <div>
            <h3 class="font-medium">{{ item.name }}</h3>
            <p class="text-sm text-gray-500">{{ item.patient_id }}</p>
        </div>
        <div class="flex space-x-2">
            <c-view_button href="{% url 'patient_detail' item.id %}">View</c-view_button>
            <c-edit_button href="{% url 'patient_update' item.id %}">Edit</c-edit_button>
        </div>
    </div>
</c-list_card>
```

### Benefits of List Cards
- ✅ **Mobile responsive** without horizontal scrolling
- ✅ **More flexible layouts** with custom content
- ✅ **Better visual hierarchy** with cards and spacing
- ✅ **Embedded components** like buttons and badges
- ✅ **Consistent styling** with the rest of the component system
- ✅ **Empty states** handled automatically
- ✅ **Hover effects** and smooth transitions 