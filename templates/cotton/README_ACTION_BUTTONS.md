# Action Button Components Documentation

This document describes the standardized action button components for your CHAVI PROM application. These components provide consistent styling, icons, and behavior for common actions.

## Color Coding System

Each action type has a specific color scheme for visual consistency:

- **View**: Blue outline (`text-blue-600`, `border-blue-600`)
- **Edit**: Yellow/Orange (`text-yellow-700`, `bg-yellow-50`)
- **Delete**: Red (`text-red-700`, `bg-red-50`)
- **Save**: Green solid (`text-white`, `bg-green-600`)
- **Create**: Blue solid (`text-white`, `bg-blue-600`)
- **Create Translations**: Purple (`text-purple-700`, `bg-purple-50`)
- **Create Rules**: Indigo (`text-indigo-700`, `bg-indigo-50`)
- **Create Rule Groups**: Teal (`text-teal-700`, `bg-teal-50`)

## Individual Components

### 1. View Button (`view_button.html`)

**Purpose**: For viewing/displaying items
**Style**: Blue outline with eye icon
**Element**: `<a>` tag

```django
{% load cotton %}

<!-- Basic view button -->
<c-view_button href="{% url 'questionnaire_detail' questionnaire.id %}">
    View Details
</c-view_button>

<!-- With custom text -->
<c-view_button href="{% url 'item_detail' item.id %}">
    {% translate "View Item" %}
</c-view_button>
```

### 2. Edit Button (`edit_button.html`)

**Purpose**: For editing/updating items
**Style**: Yellow/Orange with pencil icon
**Element**: `<a>` tag

```django
<!-- Basic edit button -->
<c-edit_button href="{% url 'questionnaire_update' questionnaire.id %}">
    Edit
</c-edit_button>

<!-- With custom styling -->
<c-edit_button href="{% url 'item_update' item.id %}" class="ml-2">
    {% translate "Edit Item" %}
</c-edit_button>
```

### 3. Delete Button (`delete_button.html`)

**Purpose**: For deleting items
**Style**: Red with trash icon and built-in confirmation
**Element**: `<button>` tag

```django
<!-- Basic delete button with HTMX -->
<c-delete_button hx_delete="{% url 'questionnaire_delete' questionnaire.id %}" 
                 hx_target="#questionnaire-{{ questionnaire.id }}"
                 hx_swap="outerHTML">
    Delete
</c-delete_button>

<!-- With custom confirmation message -->
<c-delete_button hx_post="{% url 'item_delete' item.id %}"
                 hx_confirm="{% translate 'Are you sure you want to delete this item? This action cannot be undone.' %}">
    {% translate "Delete Item" %}
</c-delete_button>

<!-- Traditional form submission -->
<c-delete_button type="submit" onclick="return confirm('Are you sure?')">
    Delete
</c-delete_button>
```

### 4. Save Button (`save_button.html`)

**Purpose**: For saving/submitting forms
**Style**: Green solid with checkmark icon
**Element**: `<button>` tag (defaults to type="submit")

```django
<!-- Basic save button -->
<c-save_button>
    Save Changes
</c-save_button>

<!-- With loading state -->
<c-save_button loading="true">
    Saving...
</c-save_button>

<!-- With HTMX -->
<c-save_button hx_post="{% url 'questionnaire_update' questionnaire.id %}"
               hx_target="#form-container">
    {% translate "Save Questionnaire" %}
</c-save_button>
```

### 5. Create Button (`create_button.html`)

**Purpose**: For general creation actions
**Style**: Blue solid with plus icon
**Element**: `<a>` tag

```django
<!-- Basic create button -->
<c-create_button href="{% url 'questionnaire_create' %}">
    Create New Questionnaire
</c-create_button>

<!-- With custom text -->
<c-create_button href="{% url 'item_create' %}">
    {% translate "Add New Item" %}
</c-create_button>
```

### 6. Create Translations Button (`create_translations_button.html`)

**Purpose**: For creating translations
**Style**: Purple with globe icon
**Element**: `<a>` tag

```django
<!-- Basic translations button -->
<c-create_translations_button href="{% url 'questionnaire_translation_create' questionnaire.id %}">
    Create Translations
</c-create_translations_button>

<!-- With custom text -->
<c-create_translations_button href="{% url 'item_translation_create' item.id %}">
    {% translate "Add Translations" %}
</c-create_translations_button>
```

### 7. Create Rules Button (`create_rules_button.html`)

**Purpose**: For creating questionnaire rules
**Style**: Indigo with cog icon
**Element**: `<a>` tag

```django
<!-- Basic rules button -->
<c-create_rules_button href="{% url 'questionnaire_item_rule_create' questionnaire.id %}">
    Create Rules
</c-create_rules_button>

<!-- With custom text -->
<c-create_rules_button href="{% url 'rule_create' %}">
    {% translate "Add New Rule" %}
</c-create_rules_button>
```

### 8. Create Rule Groups Button (`create_rulegroups_button.html`)

**Purpose**: For creating rule groups
**Style**: Teal with collection icon
**Element**: `<a>` tag

```django
<!-- Basic rule groups button -->
<c-create_rulegroups_button href="{% url 'questionnaire_item_rule_group_create' questionnaire.id %}">
    Create Rule Groups
</c-create_rulegroups_button>

<!-- With custom text -->
<c-create_rulegroups_button href="{% url 'rulegroup_create' %}">
    {% translate "Add Rule Group" %}
</c-create_rulegroups_button>
```

## Universal Action Button (`action_buttons.html`)

For more flexibility, you can use the universal action button component:

```django
<!-- Using the universal component -->
<c-action_buttons action="view" href="{% url 'questionnaire_detail' questionnaire.id %}">
    View Details
</c-action_buttons>

<c-action_buttons action="edit" href="{% url 'questionnaire_update' questionnaire.id %}">
    Edit
</c-action_buttons>

<c-action_buttons action="delete" hx_delete="{% url 'questionnaire_delete' questionnaire.id %}">
    Delete
</c-action_buttons>
```

## Common Props

All button components support these common props:

- `href`: URL for navigation (for `<a>` elements)
- `class`: Additional CSS classes
- `id`: Element ID
- `title`: Tooltip text
- `target`: Link target (for `<a>` elements)
- `attrs`: Additional HTML attributes

### HTMX Props (for applicable buttons):
- `hx_get`, `hx_post`, `hx_delete`: HTMX HTTP methods
- `hx_target`: Target element for HTMX response
- `hx_swap`: How to swap the response
- `hx_confirm`: Confirmation message
- `hx_trigger`: Event trigger

### Button-specific Props:
- `type`: Button type (button, submit, reset)
- `disabled`: Disable the button
- `loading`: Show loading state (for save button)
- `onclick`: JavaScript click handler

## Usage in Tables

These buttons work great in table action columns:

```django
<table class="min-w-full divide-y divide-gray-200">
    <thead>
        <tr>
            <th>Name</th>
            <th>Actions</th>
        </tr>
    </thead>
    <tbody>
        {% for questionnaire in questionnaires %}
        <tr id="questionnaire-{{ questionnaire.id }}">
            <td>{{ questionnaire.name }}</td>
            <td class="space-x-2">
                <c-view_button href="{% url 'questionnaire_detail' questionnaire.id %}">
                    View
                </c-view_button>
                <c-edit_button href="{% url 'questionnaire_update' questionnaire.id %}">
                    Edit
                </c-edit_button>
                <c-create_translations_button href="{% url 'questionnaire_translation_create' questionnaire.id %}">
                    Translations
                </c-create_translations_button>
                <c-delete_button hx_delete="{% url 'questionnaire_delete' questionnaire.id %}"
                                 hx_target="#questionnaire-{{ questionnaire.id }}"
                                 hx_swap="outerHTML">
                    Delete
                </c-delete_button>
            </td>
        </tr>
        {% endfor %}
    </tbody>
</table>
```

## Replacing Existing Buttons

### Before (in your current templates):
```html
<a href="{% url 'questionnaire_update' questionnaire.id %}" 
   class="px-3 py-1.5 text-sm font-medium text-yellow-700 bg-yellow-50 border border-yellow-300 rounded-md hover:bg-yellow-100">
    Edit
</a>
```

### After (using components):
```django
{% load cotton %}
<c-edit_button href="{% url 'questionnaire_update' questionnaire.id %}">
    Edit
</c-edit_button>
```

This approach provides:
- **Consistency**: All buttons follow the same design patterns
- **Maintainability**: Change styling in one place
- **Accessibility**: Built-in ARIA labels and focus states
- **Internationalization**: Automatic translation support
- **HTMX Integration**: Built-in support for dynamic interactions 