UI Components Reference
=======================

Complete reference for Django Cotton UI components used in SATHI.

.. contents:: Table of Contents
   :local:
   :depth: 3

Overview
--------

SATHI uses Django Cotton for reusable, maintainable UI components. All components follow consistent design patterns and support Tailwind CSS styling.

**Key Benefits:**

- Consistent UI across the application
- Reduced code duplication
- Easier maintenance and updates
- Built-in accessibility features
- Mobile-responsive by default

Card Components
---------------

Card Component
~~~~~~~~~~~~~~

Flexible container for structured content.

**Basic Usage:**

.. code-block:: html

    {% load cotton %}
    
    <c-card title="Patient Information">
        <p>Card content goes here...</p>
    </c-card>

**Props:**

.. list-table::
   :header-rows: 1
   :widths: 20 15 15 50

   * - Prop
     - Type
     - Default
     - Description
   * - ``title``
     - string
     - -
     - Card title/header text
   * - ``subtitle``
     - string
     - -
     - Optional subtitle below title
   * - ``header_actions``
     - string
     - -
     - HTML for header action buttons
   * - ``footer``
     - string
     - -
     - HTML content for footer
   * - ``shadow``
     - string
     - "md"
     - Shadow level: none, sm, md, lg, xl
   * - ``rounded``
     - string
     - "md"
     - Border radius: none, sm, md, lg, xl
   * - ``border``
     - string
     - "light"
     - Border style: none, light, medium, strong
   * - ``padding``
     - string
     - "md"
     - Padding level: none, sm, md, lg, xl
   * - ``header_bg``
     - string
     - "bg-gray-50"
     - Header background color
   * - ``body_bg``
     - string
     - "bg-white"
     - Body background color
   * - ``footer_bg``
     - string
     - "bg-gray-50"
     - Footer background color

**Advanced Examples:**

.. code-block:: html

    <!-- Card with header actions -->
    <c-card 
        title="Diagnoses"
        header_actions='<button class="btn btn-primary">Add New</button>'>
        <p>Diagnoses list...</p>
    </c-card>
    
    <!-- Card with footer -->
    <c-card 
        title="Patient Details"
        footer='<div class="text-right"><button>Save</button></div>'>
        <p>Form fields...</p>
    </c-card>
    
    <!-- Custom styling -->
    <c-card 
        title="Important Notice"
        shadow="lg"
        rounded="xl"
        border="strong"
        header_bg="bg-red-50"
        body_bg="bg-red-100">
        <p>Critical information...</p>
    </c-card>

**Mobile Responsiveness:**

.. code-block:: html

    <!-- Responsive content inside cards -->
    <c-card title="Patient Info" padding="md">
        <div class="flex flex-col sm:flex-row sm:justify-between gap-3">
            <div class="flex-1 min-w-0">
                <h3 class="truncate">{{ patient.name }}</h3>
                <p class="text-sm text-gray-600">{{ patient.id }}</p>
            </div>
            <div class="flex space-x-2 sm:flex-shrink-0">
                <!-- Action buttons -->
            </div>
        </div>
    </c-card>

Field Display Component
~~~~~~~~~~~~~~~~~~~~~~~

Display label-value pairs with optional badge styling.

**Usage:**

.. code-block:: html

    <c-field_display 
        label="Patient Name" 
        value="{{ patient.name }}" />
    
    <!-- With badge -->
    <c-field_display 
        label="Status" 
        value="Active"
        badge="true"
        badge_color="green" />

**Props:**

- ``label`` - Field label text
- ``value`` - Field value to display
- ``badge`` - Display as badge (true/false)
- ``badge_color`` - Badge color: blue, green, red, yellow, gray

Button Components
-----------------

Button Component
~~~~~~~~~~~~~~~~

Versatile button with multiple variants and sizes.

**Props:**

- ``variant`` - Style: primary, secondary, danger, success, outline, ghost
- ``size`` - Size: sm, md, lg, xl
- ``type`` - Type: button, submit, reset
- ``disabled`` - Boolean
- ``full_width`` - Boolean
- ``loading`` - Boolean
- ``icon_left`` - SVG path for left icon
- ``icon_right`` - SVG path for right icon
- ``href`` - URL for navigation
- HTMX attributes: ``hx_get``, ``hx_post``, ``hx_target``, ``hx_swap``, ``hx_trigger``, ``hx_confirm``

**Examples:**

.. code-block:: html

    <!-- Basic primary button -->
    <c-button>Save</c-button>
    
    <!-- Secondary button with icon -->
    <c-button 
        variant="secondary" 
        icon_left="<path d='M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z'/>">
        Add New
    </c-button>
    
    <!-- Danger button with confirmation -->
    <c-button 
        variant="danger" 
        hx_post="/delete/123/" 
        hx_confirm="Are you sure?">
        Delete
    </c-button>
    
    <!-- Loading button -->
    <c-button loading="true">
        Processing...
    </c-button>
    
    <!-- Full width button -->
    <c-button full_width="true">
        Full Width Button
    </c-button>

Link Button Component
~~~~~~~~~~~~~~~~~~~~~

Button-styled anchor tag for navigation.

**Usage:**

.. code-block:: html

    <!-- Navigation button -->
    <c-link_button href="{% url 'questionnaire_list' %}">
        View Questionnaires
    </c-link_button>
    
    <!-- External link -->
    <c-link_button 
        href="https://example.com" 
        target="_blank" 
        variant="outline">
        External Link
    </c-link_button>

Icon Button Component
~~~~~~~~~~~~~~~~~~~~~

Button containing only an icon.

**Usage:**

.. code-block:: html

    <!-- Edit button -->
    <c-icon_button 
        icon="<path d='M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.828-2.828z'/>"
        aria_label="Edit"
        title="Edit item"
        variant="ghost" />
    
    <!-- Delete button with HTMX -->
    <c-icon_button 
        icon="<path fill-rule='evenodd' d='M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z' clip-rule='evenodd'/>"
        variant="danger"
        size="sm"
        hx_delete="/api/item/123/"
        hx_confirm="Delete this item?"
        aria_label="Delete" />

Button Group Component
~~~~~~~~~~~~~~~~~~~~~~

Groups related buttons together.

**Usage:**

.. code-block:: html

    <!-- Horizontal button group -->
    <c-button_group rounded="true" shadow="true">
        <c-button variant="outline">Previous</c-button>
        <c-button variant="outline">Next</c-button>
    </c-button_group>
    
    <!-- Vertical button group -->
    <c-button_group vertical="true">
        <c-button variant="secondary">Edit</c-button>
        <c-button variant="secondary">Duplicate</c-button>
        <c-button variant="danger">Delete</c-button>
    </c-button_group>

Common Icon Paths
~~~~~~~~~~~~~~~~~

Heroicons SVG paths for common actions:

.. code-block:: html

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

Dropdown Components
-------------------

Important Syntax Note
~~~~~~~~~~~~~~~~~~~~~

When passing dynamic values to Django Cotton components, use the ``:`` prefix:

- ``:options="variable_name"`` instead of ``options=variable_name``
- ``:selected="request.GET.field"`` instead of ``selected=request.GET.field``
- ``:errors="form.field.errors"`` instead of ``errors=form.field.errors``

Static strings can be passed without the ``:`` prefix.

Filter Dropdown
~~~~~~~~~~~~~~~

For search/filter forms with HTMX integration.

**Props:**

- ``name`` - Select element name (required)
- ``label`` - Label text (required)
- ``placeholder`` - Default option text
- ``options`` - List of options (required)
- ``selected`` - Currently selected value
- ``required`` - Boolean
- ``help_text`` - Help text below dropdown
- ``hx_get`` - HTMX get URL
- ``hx_target`` - HTMX target element
- ``hx_trigger`` - HTMX trigger event (default: "change")

**Examples:**

.. code-block:: html

    <!-- Basic filter dropdown -->
    <c-filter_dropdown 
        name="institution" 
        label="Institution"
        placeholder="All Institutions"
        :options="institutions"
        :selected="request.GET.institution" />
    
    <!-- With HTMX integration -->
    <c-filter_dropdown 
        name="gender" 
        label="Gender"
        placeholder="All Genders"
        :options="gender_choices"
        :selected="request.GET.gender"
        hx_get="{% url 'patient_list' %}"
        hx_target="#patientsTable" />
    
    <!-- With help text -->
    <c-filter_dropdown 
        name="diagnosis" 
        label="Diagnosis"
        placeholder="All Diagnoses"
        :options="diagnoses"
        :selected="request.GET.diagnosis"
        help_text="Select a diagnosis to filter patients" />

**Option Formats:**

1. Objects with id/name attributes:

   .. code-block:: python

       institutions = [
           {'id': 1, 'name': 'Hospital A'},
           {'id': 2, 'name': 'Hospital B'}
       ]

2. Tuples (value, label):

   .. code-block:: python

       gender_choices = [
           ('M', 'Male'),
           ('F', 'Female')
       ]

3. Simple strings:

   .. code-block:: python

       diagnoses = ['Cancer', 'Diabetes', 'Heart Disease']

Form Dropdown
~~~~~~~~~~~~~

For Django form fields with validation support.

**Additional Props:**

- ``errors`` - Form field errors to display
- ``create_link`` - URL for creating new options
- ``create_text`` - Text for create link (default: "Create new option")
- ``create_link_target`` - Target for create link

**Examples:**

.. code-block:: html

    <!-- Basic form dropdown -->
    <c-form_dropdown 
        name="construct_scale" 
        label="Construct Scale"
        placeholder="---------"
        :options="form.construct_scale.field.queryset"
        :selected="form.construct_scale.value"
        :errors="form.construct_scale.errors"
        required=true />
    
    <!-- With create link -->
    <c-form_dropdown 
        name="likert_response" 
        label="Likert Scale"
        :options="likert_scales"
        :selected="form.likert_response.value"
        :errors="form.likert_response.errors"
        create_link="{% url 'likert_scale_create' %}"
        create_text="Create new Likert scale"
        create_link_target="_blank" />

Language Selector
~~~~~~~~~~~~~~~~~

For navbar language switching.

**Usage:**

.. code-block:: html

    <c-language_selector />

Automatically displays available languages from Django settings.

List Card Component
-------------------

Display items in a card-based list layout.

**Usage:**

.. code-block:: html

    <c-list_card 
        items="{{ patients }}"
        title_field="name"
        subtitle_field="patient_id"
        url_field="get_absolute_url" />

**Props:**

- ``items`` - List of items to display
- ``title_field`` - Field name for title
- ``subtitle_field`` - Field name for subtitle
- ``url_field`` - Field name for detail URL
- ``badge_field`` - Field name for badge text
- ``badge_color`` - Badge color

Paginator Component
-------------------

Responsive pagination for Django ListView.

**Basic Usage:**

.. code-block:: html

    <c-paginator 
        :page_obj="page_obj" 
        :is_paginated="is_paginated" />

**Props:**

- ``page_obj`` - Django Page object (required)
- ``is_paginated`` - Boolean (required)
- ``show_info`` - Show result count (default: true)
- ``show_page_numbers`` - Show page numbers (default: true)
- ``preserve_params`` - Preserve URL parameters (default: true)
- ``class`` - Additional CSS classes

**Features:**

- **Responsive**: Mobile shows Previous/Next only, desktop shows full pagination
- **Accessible**: ARIA labels and keyboard navigation
- **HTMX Integration**: Built-in support for partial page updates
- **URL Preservation**: Maintains search and filter parameters

**Examples:**

.. code-block:: html

    <!-- Full pagination -->
    <c-paginator 
        :page_obj="page_obj" 
        :is_paginated="is_paginated" 
        show_info="true"
        show_page_numbers="true"
        class="my-8" />
    
    <!-- Minimal pagination (mobile-friendly) -->
    <c-paginator 
        :page_obj="page_obj" 
        :is_paginated="is_paginated" 
        show_info="false"
        show_page_numbers="false" />

**Django View Setup:**

.. code-block:: python

    from django.views.generic import ListView
    
    class PatientListView(ListView):
        model = Patient
        template_name = 'patientapp/patient_list.html'
        context_object_name = 'patients'
        paginate_by = 10  # Items per page

**Template Integration:**

.. code-block:: html

    {% extends 'base.html' %}
    {% load cotton %}
    
    {% block content %}
    <div class="container mx-auto px-4">
        {% for patient in patients %}
            <!-- Patient cards -->
        {% endfor %}
        
        <c-paginator 
            :page_obj="page_obj" 
            :is_paginated="is_paginated" />
    </div>
    {% endblock %}

Best Practices
--------------

Component Usage
~~~~~~~~~~~~~~~

**DO:**

- Use ``:`` prefix for dynamic values
- Provide required props
- Use semantic HTML inside components
- Test on mobile devices
- Include ARIA labels for accessibility

**DON'T:**

- Mix static and dynamic syntax
- Nest components unnecessarily
- Override component styles directly
- Forget error handling in forms

Responsive Design
~~~~~~~~~~~~~~~~~

.. code-block:: html

    <!-- Good: Mobile-first responsive layout -->
    <c-card title="Details">
        <div class="space-y-4 sm:space-y-0 sm:grid sm:grid-cols-2 sm:gap-6">
            <c-field_display label="Name" value="{{ patient.name }}" />
            <c-field_display label="ID" value="{{ patient.id }}" />
        </div>
    </c-card>
    
    <!-- Good: Responsive button group -->
    <div class="flex flex-col sm:flex-row gap-2">
        <c-button full_width="true">Save</c-button>
        <c-button variant="secondary" full_width="true">Cancel</c-button>
    </div>

Accessibility
~~~~~~~~~~~~~

.. code-block:: html

    <!-- Good: Proper ARIA labels -->
    <c-icon_button 
        icon="..."
        aria_label="Edit patient details"
        title="Edit" />
    
    <!-- Good: Form validation -->
    <c-form_dropdown 
        name="diagnosis"
        label="Diagnosis"
        :errors="form.diagnosis.errors"
        required=true />

Performance
~~~~~~~~~~~

- Use lazy loading for large lists
- Implement HTMX for partial updates
- Minimize nested components
- Cache component renders when possible

Resources
---------

- `Django Cotton Documentation <https://django-cotton.com/>`_
- `Tailwind CSS Components <https://tailwindcss.com/docs/>`_
- `Heroicons <https://heroicons.com/>`_
- `HTMX Documentation <https://htmx.org/>`_
