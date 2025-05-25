# Dropdown Components Documentation

This document describes the three specialized dropdown components available in the Django Cotton component library.

## ⚠️ Important Syntax Note

When passing dynamic values (variables) to Django Cotton components, use the `:` prefix:
- `:options="variable_name"` instead of `options=variable_name`
- `:selected="request.GET.field"` instead of `selected=request.GET.field`
- `:errors="form.field.errors"` instead of `errors=form.field.errors`

Static strings can be passed without the `:` prefix.

## Components Overview

1. **Filter Dropdown** (`c-filter_dropdown`) - For search/filter forms with HTMX integration
2. **Form Dropdown** (`c-form_dropdown`) - For regular Django forms with validation support  
3. **Language Selector** (`c-language_selector`) - For navbar language switching

---

## Filter Dropdown (`c-filter_dropdown`)

Used for search and filter forms, typically with HTMX integration for dynamic updates.

### Props

| Prop | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `name` | string | ✅ | - | The name attribute for the select element |
| `id` | string | ❌ | `name` | The id attribute for the select element |
| `label` | string | ✅ | - | The label text displayed above the dropdown |
| `placeholder` | string | ❌ | - | The default option text (e.g., "All Institutions") |
| `options` | list | ✅ | - | List of options (objects, tuples, or strings) |
| `selected` | string | ❌ | - | Currently selected value |
| `required` | boolean | ❌ | `false` | Whether the field is required |
| `help_text` | string | ❌ | - | Optional help text below the dropdown |
| `class` | string | ❌ | - | Additional CSS classes |
| `hx_get` | string | ❌ | - | HTMX get URL for dynamic updates |
| `hx_target` | string | ❌ | - | HTMX target element |
| `hx_trigger` | string | ❌ | `"change"` | HTMX trigger event |

### Usage Examples

#### Basic Filter Dropdown
```html
{% load cotton %}

<c-filter_dropdown 
    name="institution" 
    label="Institution"
    placeholder="All Institutions"
    :options="institutions"
    :selected="request.GET.institution" />
```

**Important:** Use `:options="variable"` and `:selected="variable"` syntax for dynamic values in Django Cotton components.

#### With HTMX Integration
```html
<c-filter_dropdown 
    name="gender" 
    label="Gender"
    placeholder="All Genders"
    :options="gender_choices"
    :selected="request.GET.gender"
    hx_get="{% url 'patient_list' %}"
    hx_target="#patientsTable" />
```

#### With Help Text
```html
<c-filter_dropdown 
    name="diagnosis" 
    label="Diagnosis"
    placeholder="All Diagnoses"
    :options="diagnoses"
    :selected="request.GET.diagnosis"
    help_text="Select a diagnosis to filter patients" />
```

### Option Formats Supported

1. **Objects with id/name attributes:**
   ```python
   institutions = [
       {'id': 1, 'name': 'Hospital A'},
       {'id': 2, 'name': 'Hospital B'}
   ]
   ```

2. **Tuples (value, label):**
   ```python
   gender_choices = [
       ('M', 'Male'),
       ('F', 'Female')
   ]
   ```

3. **Simple strings:**
   ```python
   diagnoses = ['Cancer', 'Diabetes', 'Heart Disease']
   ```

---

## Form Dropdown (`c-form_dropdown`)

Used for Django form fields with validation support and error handling.

### Props

| Prop | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `name` | string | ✅ | - | The name attribute for the select element |
| `id` | string | ❌ | `name` | The id attribute for the select element |
| `label` | string | ✅ | - | The label text displayed above the dropdown |
| `placeholder` | string | ❌ | - | The default option text (e.g., "---------") |
| `options` | list | ✅ | - | List of options (objects, tuples, or strings) |
| `selected` | string | ❌ | - | Currently selected value |
| `required` | boolean | ❌ | `false` | Whether the field is required |
| `errors` | list | ❌ | - | Form field errors to display |
| `help_text` | string | ❌ | - | Optional help text below the dropdown |
| `class` | string | ❌ | - | Additional CSS classes |
| `hx_get` | string | ❌ | - | HTMX get URL for dynamic updates |
| `hx_target` | string | ❌ | - | HTMX target element |
| `hx_trigger` | string | ❌ | - | HTMX trigger event |
| `create_link` | string | ❌ | - | URL for creating new options |
| `create_text` | string | ❌ | `"Create new option"` | Text for the create link |
| `create_link_target` | string | ❌ | - | Target for the create link |

### Usage Examples

#### Basic Form Dropdown
```html
{% load cotton %}

<c-form_dropdown 
    name="construct_scale" 
    label="Construct Scale"
    placeholder="---------"
    :options="form.construct_scale.field.queryset"
    :selected="form.construct_scale.value"
    :errors="form.construct_scale.errors"
    required=true />
```

#### With Create Link
```html
<c-form_dropdown 
    name="treatment_type" 
    label="Treatment Type"
    placeholder="---------"
    options=treatment_types
    selected=form.treatment_type.value
    errors=form.treatment_type.errors
    create_link="{% url 'treatment_type_create' %}"
    create_text="Add New Treatment Type"
    create_link_target="_blank" />
```

#### With HTMX for Dynamic Fields
```html
<c-form_dropdown 
    name="response_type" 
    label="Response Type"
    placeholder="---------"
    options=form.response_type.field.choices
    selected=form.response_type.value
    errors=form.response_type.errors
    hx_get="/promapp/get-response-fields/"
    hx_target="#response-fields"
    hx_trigger="change" />
```

### Special Features

- **Error Handling**: Automatically displays form validation errors
- **Complex Objects**: Supports objects with `instrument_name` and `instrument_version` for detailed display
- **Create Links**: Built-in support for "Create new option" links
- **Validation Styling**: Automatically applies error styling when errors are present

---

## Language Selector (`c-language_selector`)

Used for language switching in navigation bars with auto-submit functionality.

### Props

| Prop | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `name` | string | ❌ | `"language"` | The name attribute for the select element |
| `id` | string | ❌ | `name` | The id attribute for the select element |
| `languages` | list | ❌ | Django's available languages | Custom language list |
| `current_language` | string | ❌ | Current Django language | Currently selected language code |
| `variant` | string | ❌ | `"navbar"` | Styling variant: "navbar" or "mobile" |
| `class` | string | ❌ | - | Additional CSS classes |
| `auto_submit` | boolean | ❌ | `true` | Whether to auto-submit on change |

### Usage Examples

#### Basic Language Selector (Navbar)
```html
{% load cotton %}

<form action="{% url 'set_language' %}" method="post">
    {% csrf_token %}
    <c-language_selector />
</form>
```

#### Mobile Variant
```html
<form action="{% url 'set_language' %}" method="post">
    {% csrf_token %}
    <c-language_selector variant="mobile" />
</form>
```

#### Custom Languages
```html
<c-language_selector 
    languages=custom_languages
    current_language=user.preferred_language />
```

#### Without Auto-Submit
```html
<c-language_selector 
    auto_submit=false
    class="custom-language-selector" />
```

---

## Migration Guide

### From Existing Templates

#### Replace Filter Dropdowns
**Before:**
```html
<div>
    <label for="institution" class="block text-sm font-medium text-gray-700">Institution</label>
    <select name="institution" id="institution" 
            class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm py-3">
        <option value="">All Institutions</option>
        {% for institution in institutions %}
        <option value="{{ institution.id }}" {% if request.GET.institution == institution.id|stringformat:"s" %}selected{% endif %}>
            {{ institution.name }}
        </option>
        {% endfor %}
    </select>
</div>
```

**After:**
```html
{% load cotton %}
<c-filter_dropdown 
    name="institution" 
    label="Institution"
    placeholder="All Institutions"
    :options="institutions"
    :selected="request.GET.institution" />
```

#### Replace Form Dropdowns
**Before:**
```html
<div>
    <label for="id_construct_scale" class="block text-sm font-medium text-gray-700 mb-1">Construct Scale</label>
    <select name="construct_scale" id="id_construct_scale" class="w-full px-3 py-2 border rounded">
        <option value="">---------</option>
        {% for scale in form.construct_scale.field.queryset %}
        <option value="{{ scale.id }}" {% if form.construct_scale.value == scale.id|stringformat:"s" %}selected{% endif %}>
            {{ scale.name }}
        </option>
        {% endfor %}
    </select>
    {% if form.construct_scale.errors %}
    <div class="text-red-500 text-sm mt-1">{{ form.construct_scale.errors }}</div>
    {% endif %}
</div>
```

**After:**
```html
{% load cotton %}
<c-form_dropdown 
    name="construct_scale" 
    label="Construct Scale"
    placeholder="---------"
    :options="form.construct_scale.field.queryset"
    :selected="form.construct_scale.value"
    :errors="form.construct_scale.errors" />
```

#### Replace Language Selectors
**Before:**
```html
<select name="language" onchange="this.form.submit()" class="bg-blue-700 text-white px-2 py-1 rounded text-sm">
    {% get_available_languages as languages %}
    {% get_current_language as LANGUAGE_CODE %}
    {% for code, name in languages %}
    <option value="{{ code }}" {% if code == LANGUAGE_CODE %}selected{% endif %}>{{ name }}</option>
    {% endfor %}
</select>
```

**After:**
```html
{% load cotton %}
<c-language_selector />
```

---

## Best Practices

1. **Use the Right Component**: Choose the appropriate dropdown type for your use case
2. **Consistent Naming**: Use descriptive names that match your form fields
3. **Error Handling**: Always pass form errors to form dropdowns
4. **HTMX Integration**: Use filter dropdowns for dynamic filtering
5. **Accessibility**: The components include proper labels and ARIA attributes
6. **Performance**: Components handle different option formats efficiently

## Styling

All dropdown components use Tailwind CSS classes and follow the project's design system:
- **Enhanced Visibility**: Thicker borders (`border-2`) and stronger default border color (`border-gray-400`)
- **Interactive States**: 
  - Hover effects (`hover:border-gray-500`, `hover:bg-blue-50`)
  - Enhanced focus states (`focus:border-blue-600`, `focus:ring-2`, `focus:ring-blue-500`)
  - Smooth transitions (`transition-colors duration-200`)
- **Visual Depth**: Drop shadows (`shadow-md`) for better contrast against white backgrounds
- **Error States**: Red borders and focus rings for form validation
- **Proper Text Visibility**: 
  - Options: `text-gray-900 bg-white` for clear readability
  - Placeholders: `text-gray-600 bg-gray-50` for subtle distinction
- **Responsive Design**: Consistent spacing and typography across devices

### Enhanced Visibility Features

The dropdown components are specifically designed to stand out against white page backgrounds:
- **Stronger Borders**: `border-2 border-gray-400` instead of thin gray borders
- **Drop Shadows**: `shadow-md` provides depth and separation from the background
- **Hover States**: Visual feedback when interacting with dropdowns
- **Focus Indicators**: Clear blue focus rings with opacity for accessibility 