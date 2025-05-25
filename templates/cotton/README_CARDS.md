# Card Components Documentation

This document describes the card-related components available in the Django Cotton component library.

## Components Overview

1. **Card** (`c-card`) - Flexible container component for structured content
2. **Field Display** (`c-field_display`) - Component for displaying label-value pairs

---

## Card Component (`c-card`)

A flexible card component that can display various types of content with customizable styling.

### Props

| Prop | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `title` | string | ❌ | - | Card title/header text |
| `subtitle` | string | ❌ | - | Optional subtitle below the title |
| `header_actions` | string | ❌ | - | HTML content for header action buttons |
| `footer` | string | ❌ | - | HTML content for card footer |
| `class` | string | ❌ | - | Additional CSS classes for the card container |
| `header_class` | string | ❌ | - | Additional CSS classes for the header section |
| `body_class` | string | ❌ | - | Additional CSS classes for the body section |
| `footer_class` | string | ❌ | - | Additional CSS classes for the footer section |
| `shadow` | string | ❌ | `"md"` | Shadow level: "none", "sm", "md", "lg", "xl" |
| `rounded` | string | ❌ | `"md"` | Border radius: "none", "sm", "md", "lg", "xl" |
| `border` | string | ❌ | `"light"` | Border style: "none", "light", "medium", "strong" |
| `padding` | string | ❌ | `"md"` | Padding level: "none", "sm", "md", "lg", "xl" |
| `header_bg` | string | ❌ | `"bg-gray-50"` | Header background color class |
| `body_bg` | string | ❌ | `"bg-white"` | Body background color class |
| `footer_bg` | string | ❌ | `"bg-gray-50"` | Footer background color class |

### Usage Examples

#### Basic Card
```html
{% load cotton %}

<c-card title="Patient Information">
    <p>Card content goes here...</p>
</c-card>
```

#### Card with Header Actions
```html
<c-card 
    title="Diagnoses"
    header_actions='<button class="btn btn-primary">Add New</button>'>
    <p>Diagnoses list...</p>
</c-card>
```

#### Customized Styling
```html
<c-card 
    title="Important Notice"
    subtitle="Please read carefully"
    shadow="lg"
    border="strong"
    padding="lg"
    header_bg="bg-blue-50"
    body_bg="bg-blue-25">
    <p>Important content...</p>
</c-card>
```

#### Card with Footer
```html
<c-card 
    title="Summary"
    footer='<div class="text-right"><button class="btn">Save</button></div>'>
    <p>Summary content...</p>
</c-card>
```

#### Nested Cards
```html
<c-card title="Main Container" shadow="lg">
    <div class="space-y-4">
        <c-card title="Sub Item 1" shadow="sm" padding="sm">
            <p>Sub content 1</p>
        </c-card>
        <c-card title="Sub Item 2" shadow="sm" padding="sm">
            <p>Sub content 2</p>
        </c-card>
    </div>
</c-card>
```

---

## Field Display Component (`c-field_display`)

A component for displaying label-value pairs in a consistent format, perfect for use inside cards.

### Props

| Prop | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `label` | string | ✅ | - | The field label/name |
| `value` | any | ✅ | - | The field value to display |
| `type` | string | ❌ | `"text"` | Display type: "text", "badge", "date", "number", "email", "link" |
| `layout` | string | ❌ | `"vertical"` | Layout style: "vertical", "horizontal", "inline" |
| `label_class` | string | ❌ | - | Additional CSS classes for the label |
| `value_class` | string | ❌ | - | Additional CSS classes for the value |
| `badge_color` | string | ❌ | `"blue"` | Badge color: "blue", "green", "red", "yellow", "purple", "gray" |
| `href` | string | ❌ | - | URL for type="link" |
| `target` | string | ❌ | - | Link target for type="link" |
| `format` | string | ❌ | `"F j, Y"` | Date format for type="date" |
| `empty_text` | string | ❌ | `"—"` | Text to show when value is empty |

### Usage Examples

#### Basic Field Display
```html
{% load cotton %}

<c-field_display 
    label="Patient Name"
    :value="patient.name" />
```

#### Different Display Types
```html
<!-- Badge Display -->
<c-field_display 
    label="Status"
    :value="patient.status"
    type="badge"
    badge_color="green" />

<!-- Date Display -->
<c-field_display 
    label="Created Date"
    :value="patient.created_date"
    type="date"
    format="M d, Y" />

<!-- Number Display -->
<c-field_display 
    label="Age"
    :value="patient.age"
    type="number" />

<!-- Email Display -->
<c-field_display 
    label="Email"
    :value="patient.email"
    type="email" />

<!-- Link Display -->
<c-field_display 
    label="Website"
    :value="patient.website"
    type="link"
    target="_blank" />
```

#### Different Layouts
```html
<!-- Horizontal Layout -->
<c-field_display 
    label="Patient ID"
    :value="patient.id"
    layout="horizontal" />

<!-- Inline Layout -->
<c-field_display 
    label="Gender"
    :value="patient.gender"
    layout="inline" />
```

#### Grid Layout with Multiple Fields
```html
<dl class="grid grid-cols-1 md:grid-cols-2 gap-6">
    <c-field_display 
        label="Patient ID"
        :value="patient.patient_id"
        type="number" />
    
    <c-field_display 
        label="Name"
        :value="patient.name" />
    
    <c-field_display 
        label="Age"
        :value="patient.age"
        type="number" />
    
    <c-field_display 
        label="Gender"
        :value="patient.gender"
        type="badge"
        badge_color="blue" />
</dl>
```

---

## Real-World Example: Patient Detail Page

Here's a complete example showing the 4-level hierarchy in action, based on the patient detail page implementation:

```html
{% load cotton %}

<!-- Level 1: Primary Section -->
<c-card 
    title="Patient Information"
    shadow="lg"
    border="medium"
    padding="sm">
    <dl class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <c-field_display 
            label="Patient ID"
            value="{{ patient.patient_id }}"
            type="number"
            layout="horizontal" />
        <c-field_display 
            label="Name"
            value="{{ patient.name }}"
            layout="horizontal" />
        <!-- More fields... -->
    </dl>
</c-card>

<!-- Level 2: Secondary Section with Action Button -->
<div class="flex justify-between items-center mb-4">
    <div></div>
    <c-create_button href="{% url 'diagnosis_create' patient.id %}">
        Add Diagnosis
    </c-create_button>
</div>

<c-card 
    title="Diagnoses"
    shadow="lg"
    border="medium"
    padding="sm">
    <div class="space-y-4">
        {% for diagnosis in diagnoses %}
        <!-- Level 2: Individual Diagnosis -->
        <c-card 
            shadow="lg"
            border="medium"
            padding="sm">
            <div class="flex justify-between items-start mb-3">
                <div>
                    <h4 class="text-lg font-medium">{{ diagnosis.diagnosis }}</h4>
                    <p class="text-xs text-gray-500">{{ diagnosis.created_date|date:"F j, Y" }}</p>
                </div>
                <div class="flex space-x-2">
                    <c-edit_button href="{% url 'diagnosis_update' diagnosis.id %}">
                        Edit
                    </c-edit_button>
                    <c-delete_button href="{% url 'diagnosis_delete' diagnosis.id %}">
                        Delete
                    </c-delete_button>
                </div>
            </div>
            
            <!-- Level 3: Nested Section -->
            <div class="mt-4">
                <div class="flex justify-between items-center mb-3">
                    <div></div>
                    <c-create_button href="{% url 'treatment_create' diagnosis.id %}" size="sm">
                        Add Treatment
                    </c-create_button>
                </div>
                
                <c-card 
                    title="Treatments"
                    shadow="sm"
                    border="light"
                    padding="sm">
                    <div class="space-y-2">
                        {% for treatment in diagnosis.treatment_set.all %}
                        <!-- Level 4: Individual Items (not cards) -->
                        <div class="bg-gray-50 border border-gray-200 rounded p-3">
                            <div class="flex justify-between items-start">
                                <div>
                                    <p class="font-medium text-sm">{{ treatment.treatment_intent }}</p>
                                    <p class="text-xs text-gray-500">{{ treatment.treatment_type }}</p>
                                </div>
                                <div class="flex space-x-2">
                                    <c-edit_button href="{% url 'treatment_update' treatment.id %}">
                                        Edit
                                    </c-edit_button>
                                    <c-delete_button href="{% url 'treatment_delete' treatment.id %}">
                                        Delete
                                    </c-delete_button>
                                </div>
                            </div>
                        </div>
                        {% endfor %}
                    </div>
                </c-card>
            </div>
        </c-card>
        {% endfor %}
    </div>
</c-card>
```

This example demonstrates:
- **Proper header styling** with `title` props
- **4-level visual hierarchy** with appropriate shadows and borders
- **Action button placement** outside of cards
- **Field display components** with horizontal layout for compactness
- **Avoiding over-nesting** by using simple divs for individual treatments

---

## Complete Example: Patient Information Card

```html
{% load cotton %}

<c-card 
    title="Patient Information"
    shadow="lg"
    border="medium"
    header_actions='<button class="btn btn-primary">Edit</button>'>
    
    <dl class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <c-field_display 
            label="Patient ID"
            :value="patient.patient_id"
            type="number" />
        
        <c-field_display 
            label="Name"
            :value="patient.name" />
        
        <c-field_display 
            label="Age"
            :value="patient.age"
            type="number" />
        
        <c-field_display 
            label="Gender"
            :value="patient.gender"
            type="badge"
            badge_color="blue" />
        
        <c-field_display 
            label="Email"
            :value="patient.email"
            type="email" />
        
        <c-field_display 
            label="Created Date"
            :value="patient.created_date"
            type="date" />
    </dl>
    
    <div slot="footer" class="text-right">
        <button class="btn btn-secondary mr-2">Cancel</button>
        <button class="btn btn-primary">Save Changes</button>
    </div>
</c-card>
```

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
- `padding="none"` - No padding
- `padding="sm"` - Small padding
- `padding="md"` - Medium padding (default)
- `padding="lg"` - Large padding
- `padding="xl"` - Extra large padding

### Badge Colors
- `badge_color="blue"` - Blue badge (default)
- `badge_color="green"` - Green badge
- `badge_color="red"` - Red badge
- `badge_color="yellow"` - Yellow badge
- `badge_color="purple"` - Purple badge
- `badge_color="gray"` - Gray badge

---

## Card Headers and Visual Hierarchy

### Header Styling
Cards automatically create a header section with gray background and bottom border when you provide a `title` prop:

```html
<c-card title="Section Title">
    <!-- Content goes here -->
</c-card>
```

**Header Features:**
- Gray background (`bg-gray-50`)
- Bottom border (`border-b border-gray-200`)
- Proper typography (`text-lg font-semibold text-gray-900`)
- Consistent padding that matches the card's padding setting

### Visual Hierarchy Guidelines

For complex layouts with nested information, use this hierarchy:

#### Level 1: Primary Sections
```html
<c-card 
    title="Patient Information"
    shadow="lg"
    border="medium"
    padding="sm">
    <!-- Primary content -->
</c-card>
```

#### Level 2: Secondary Sections
```html
<c-card 
    title="Diagnoses"
    shadow="lg"
    border="medium"
    padding="sm">
    <!-- Secondary content -->
</c-card>
```

#### Level 3: Nested/Tertiary Sections
```html
<c-card 
    title="Treatments"
    shadow="sm"
    border="light"
    padding="sm">
    <!-- Nested content -->
</c-card>
```

#### Level 4: Individual Items
```html
<!-- Use simple divs with styling instead of cards -->
<div class="bg-gray-50 border border-gray-200 rounded p-3">
    <!-- Individual item content -->
</div>
```

### Action Button Placement

When using action buttons with cards, place them outside the card header to avoid Cotton component embedding issues:

```html
<!-- Correct: Button outside card -->
<div class="flex justify-between items-center mb-4">
    <div></div>
    <c-create_button href="/create/">Add Item</c-create_button>
</div>

<c-card title="Section Title">
    <!-- Content -->
</c-card>
```

## Best Practices

1. **Use Semantic Structure**: Wrap field displays in `<dl>` elements for proper semantics
2. **Grid Layouts**: Use CSS Grid for responsive field layouts
3. **Consistent Spacing**: Use the `space-y-*` classes for consistent vertical spacing
4. **Appropriate Types**: Choose the right display type for each field (badge for status, date for timestamps, etc.)
5. **Empty States**: Provide meaningful empty text for optional fields
6. **Visual Hierarchy**: Follow the 4-level hierarchy for complex layouts
7. **Header Titles**: Always use `title` prop for section cards to get proper header styling
8. **Action Buttons**: Place action buttons outside cards, not in header_actions
9. **Avoid Over-nesting**: Don't use cards for individual items at the deepest level

---

## Migration from Traditional HTML

### Before (Traditional HTML)
```html
<div class="bg-white shadow-md rounded-lg p-6">
    <h3 class="text-lg font-semibold mb-4">Patient Information</h3>
    <div class="grid grid-cols-2 gap-4">
        <div>
            <p class="text-sm text-gray-500">Name</p>
            <p class="text-lg text-gray-900">{{ patient.name }}</p>
        </div>
        <div>
            <p class="text-sm text-gray-500">Age</p>
            <p class="text-lg text-gray-900">{{ patient.age }}</p>
        </div>
    </div>
</div>
```

### After (Card Components)
```html
{% load cotton %}

<c-card title="Patient Information">
    <dl class="grid grid-cols-2 gap-4">
        <c-field_display label="Name" :value="patient.name" />
        <c-field_display label="Age" :value="patient.age" type="number" />
    </dl>
</c-card>
```

This approach provides:
- ✅ **Consistent styling** across the application
- ✅ **Reduced code duplication** 
- ✅ **Better maintainability**
- ✅ **Improved accessibility**
- ✅ **Flexible customization options** 