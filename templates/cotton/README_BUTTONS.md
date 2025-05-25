# Button Components Documentation

This document describes the Django Cotton button components available in your CHAVI PROM application.

## Components

### 1. Button (`button.html`)
A versatile button component that supports various styles, sizes, icons, and HTMX attributes.

#### Props:
- `variant`: 'primary' (default), 'secondary', 'danger', 'success', 'outline', 'ghost'
- `size`: 'sm', 'md' (default), 'lg', 'xl'
- `type`: 'button' (default), 'submit', 'reset'
- `disabled`: boolean
- `full_width`: boolean
- `loading`: boolean
- `icon_left`: SVG path for left icon
- `icon_right`: SVG path for right icon
- `href`: URL for navigation (makes button clickable)
- `class`: Additional CSS classes
- `id`: Element ID
- HTMX attributes: `hx_get`, `hx_post`, `hx_target`, `hx_swap`, `hx_trigger`, `hx_indicator`, `hx_confirm`
- `onclick`: JavaScript onclick handler
- `attrs`: Additional HTML attributes

#### Usage Examples:

```django
{% load cotton %}

<!-- Basic primary button -->
<c-button>Save</c-button>

<!-- Secondary button with icon -->
<c-button variant="secondary" icon_left="<path d='M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z'/>">
    Add New
</c-button>

<!-- Danger button with confirmation -->
<c-button variant="danger" hx_post="/delete/123/" hx_confirm="Are you sure?">
    Delete
</c-button>

<!-- Large success button -->
<c-button variant="success" size="lg" type="submit">
    Submit Form
</c-button>

<!-- Loading button -->
<c-button loading="true">
    Processing...
</c-button>

<!-- Full width button -->
<c-button full_width="true">
    Full Width Button
</c-button>
```

### 2. Link Button (`link_button.html`)
A button-styled anchor tag for navigation.

#### Props:
Same as Button component, plus:
- `href`: URL to navigate to (required)
- `target`: Link target ('_blank', '_self', etc.)

#### Usage Examples:

```django
<!-- Navigation button -->
<c-link_button href="{% url 'questionnaire_list' %}">
    View Questionnaires
</c-link_button>

<!-- External link button -->
<c-link_button href="https://example.com" target="_blank" variant="outline">
    External Link
</c-link_button>
```

### 3. Icon Button (`icon_button.html`)
A button that contains only an icon, perfect for actions like edit, delete, menu toggles.

#### Props:
Similar to Button component, plus:
- `icon`: SVG path for the icon (required)
- `aria_label`: Accessibility label
- `title`: Tooltip text

#### Usage Examples:

```django
<!-- Edit button -->
<c-icon_button 
    icon="<path d='M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.828-2.828z'/>"
    aria_label="Edit"
    title="Edit item"
    variant="ghost">
</c-icon_button>

<!-- Delete button -->
<c-icon_button 
    icon="<path fill-rule='evenodd' d='M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z' clip-rule='evenodd'/>"
    variant="danger"
    size="sm"
    hx_delete="/api/item/123/"
    hx_confirm="Delete this item?"
    aria_label="Delete">
</c-icon_button>
```

### 4. Button Group (`button_group.html`)
Groups related buttons together with proper styling.

#### Props:
- `vertical`: boolean - Stack buttons vertically
- `rounded`: boolean - Add rounded corners
- `shadow`: boolean - Add shadow
- `class`: Additional CSS classes
- `id`: Element ID

#### Usage Examples:

```django
<!-- Horizontal button group -->
<c-button_group class="button-group" rounded="true" shadow="true">
    <c-button variant="outline">Previous</c-button>
    <c-button variant="outline">Next</c-button>
</c-button_group>

<!-- Vertical button group -->
<c-button_group vertical="true" class="button-group vertical">
    <c-button variant="secondary">Edit</c-button>
    <c-button variant="secondary">Duplicate</c-button>
    <c-button variant="danger">Delete</c-button>
</c-button_group>
```

## Common Icon Paths

Here are some commonly used Heroicons paths you can use with the components:

```django
<!-- Plus icon -->
<path fill-rule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z" clip-rule="evenodd" />

<!-- Edit/Pencil icon -->
<path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.828-2.828z"/>

<!-- Trash/Delete icon -->
<path fill-rule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clip-rule="evenodd"/>

<!-- Eye/View icon -->
<path d="M10 12a2 2 0 100-4 2 2 0 000 4z"/><path fill-rule="evenodd" d="M.458 10C1.732 5.943 5.522 3 10 3s8.268 2.943 9.542 7c-1.274 4.057-5.064 7-9.542 7S1.732 14.057.458 10zM14 10a4 4 0 11-8 0 4 4 0 018 0z" clip-rule="evenodd"/>

<!-- Search icon -->
<path fill-rule="evenodd" d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z" clip-rule="evenodd"/>

<!-- Download icon -->
<path fill-rule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3.293-7.707a1 1 0 011.414 0L9 10.586V3a1 1 0 112 0v7.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z" clip-rule="evenodd"/>
```

## Replacing Existing Buttons

You can now replace existing buttons in your templates. For example, in `questionnaire_list.html`:

### Before:
```html
<a href="{% url 'questionnaire_create' %}" class="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 inline-flex items-center">
  <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-1" viewBox="0 0 20 20" fill="currentColor">
    <path fill-rule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z" clip-rule="evenodd" />
  </svg>
  {% translate "Create New Questionnaire" %}
</a>
```

### After:
```django
{% load cotton %}

<c-link_button 
    href="{% url 'questionnaire_create' %}" 
    icon_left="<path fill-rule='evenodd' d='M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z' clip-rule='evenodd' />">
    {% translate "Create New Questionnaire" %}
</c-link_button>
```

This approach provides consistency, maintainability, and easier theming across your application. 