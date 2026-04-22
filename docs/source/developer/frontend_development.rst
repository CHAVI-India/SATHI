Frontend Development
====================

This guide covers frontend development in SATHI including Tailwind CSS setup, UI components, and responsive design patterns.

.. contents:: Table of Contents
   :local:
   :depth: 2

Tailwind CSS Setup
------------------

SATHI uses Tailwind CSS v4 compiled locally for production-ready performance.

Overview
~~~~~~~~

**Benefits:**

- Better performance with smaller CSS file size
- No CDN dependency
- Faster load times with browser caching
- Offline support

File Structure
~~~~~~~~~~~~~~

.. code-block:: text

    chavi-prom/
    ├── package.json                    # NPM configuration
    ├── static/
    │   └── src/
    │       ├── input.css              # Source CSS (tracked in git)
    │       └── output.css             # Compiled CSS (gitignored)
    └── templates/
        └── base.html                  # References output.css

Development Workflow
~~~~~~~~~~~~~~~~~~~~

**During Development:**

.. code-block:: bash

    # Terminal 1: Tailwind watch mode
    npm run tailwind:watch
    
    # Terminal 2: Django development server
    python manage.py runserver

The watch command monitors templates and automatically rebuilds CSS when changes are detected.

**Building for Production:**

.. code-block:: bash

    npm run tailwind:build
    python manage.py collectstatic

NPM Scripts
~~~~~~~~~~~

Available scripts in ``package.json``:

- ``npm run tailwind:build`` - Build CSS once (production)
- ``npm run tailwind:watch`` - Watch mode for development

Customizing Tailwind
~~~~~~~~~~~~~~~~~~~~

Create ``tailwind.config.js`` in project root:

.. code-block:: javascript

    module.exports = {
      theme: {
        extend: {
          colors: {
            'brand-blue': '#0066cc',
          },
        },
      },
    }

Then rebuild: ``npm run tailwind:build``

Adding Custom CSS
~~~~~~~~~~~~~~~~~

Edit ``static/src/input.css``:

.. code-block:: css

    @import "tailwindcss";
    
    /* Your custom CSS here */
    .custom-class {
      /* custom styles */
    }

Troubleshooting
~~~~~~~~~~~~~~~

**CSS Not Updating:**

- Ensure ``npm run tailwind:watch`` is running
- Verify valid Tailwind classes
- Try rebuilding: ``npm run tailwind:build``

**Styles Not Appearing:**

- Check ``static/src/output.css`` exists
- Verify Django static files configuration
- Run ``python manage.py collectstatic`` for production

**Node Modules Missing:**

.. code-block:: bash

    npm install
    npm run tailwind:build

Language Switching
------------------

SATHI supports automatic language switching based on patient preferences.

How It Works
~~~~~~~~~~~~

**Patient Login Flow:**

1. Patient logs in with credentials
2. ``PatientLanguageMiddleware`` detects authenticated user
3. Retrieves ``preferred_language`` from patient record
4. Activates language in Django's translation system
5. Stores preference in session
6. Redirects to language-prefixed URL (e.g., ``/en/`` → ``/hi/``)
7. All pages displayed in preferred language

URL Structure
~~~~~~~~~~~~~

Language-based URLs using Django's ``i18n_patterns``:

- English: ``https://example.com/en/patientapp/...``
- Hindi: ``https://example.com/hi/patientapp/...``
- Bengali: ``https://example.com/bn/patientapp/...``

Configuration
~~~~~~~~~~~~~

Set in ``.env`` file:

.. code-block:: bash

    DJANGO_LANGUAGES=en-gb:English,hi:Hindi,bn:Bengali
    DJANGO_LANGUAGE_CODE=en-gb
    PARLER_DEFAULT_LANGUAGE=en-gb
    PARLER_LANGUAGES=en-gb,hi,hi

Components
~~~~~~~~~~

**Patient Model** (``patientapp/models.py``):

- Contains ``preferred_language`` field
- Uses ``settings.LANGUAGES`` for choices
- Indexed for performance

**Custom Middleware** (``patientapp/middleware.py``):

- ``PatientLanguageMiddleware`` runs after authentication
- Checks for Patient profile
- Activates preferred language
- Handles redirects with query string preservation

**Settings** (``chaviprom/settings.py``):

- Middleware added after ``AuthenticationMiddleware``
- Placed before ``ClickjackingMiddleware``

Benefits
~~~~~~~~

- **Automatic**: No manual switching required
- **Persistent**: Stored in database and session
- **User-Friendly**: Immediate language display on login
- **Flexible**: Patients can change preference anytime
- **Secure**: Only authenticated patients trigger switching
- **Performant**: Database indexing and session caching

Vertical Tabs Implementation
-----------------------------

The PROM Review page uses vertical tabs for better navigation and reduced scrolling.

Overview
~~~~~~~~

Each construct is displayed in its own tab with related items grouped together.

Layout Structure
~~~~~~~~~~~~~~~~

.. code-block:: text

    ┌─────────────────────────────────────────────────────┐
    │ TOPLINE RESULTS (Important Constructs)              │
    ├──────────────┬──────────────────────────────────────┤
    │ 🔴 Pain      │ Pain Score: 7.5 ↑                    │
    │ 🔴 Anxiety   │ [Bokeh Plot]                         │
    │ 🔴 Depression│ Clinical Significance: Worsened      │
    │              │ Related Items: [Item Cards]          │
    └──────────────┴──────────────────────────────────────┘

Key Features
~~~~~~~~~~~~

**Reduced Scrolling:**

- Only one construct's content visible at a time
- Sidebar navigation for quick access
- Eliminates scrolling through multiple plots

**Visual Indicators:**

- Red circles (🔴): Topline/important constructs
- Green circles (🟢): Other constructs
- Color-coded active states

**Organized Content:**

Each tab displays:

- Construct name and current score
- Trend indicator (up/down/no change)
- Bokeh plot for score over time
- Clinical significance warnings
- Threshold and normative score comparisons
- Related item responses with plots

JavaScript Functionality
~~~~~~~~~~~~~~~~~~~~~~~~

**switchTab(section, constructId):**

.. code-block:: javascript

    // Parameters:
    // - section: 'topline' or 'other'
    // - constructId: The ID of the construct to display
    
    // Functionality:
    // 1. Hides all tab contents in section
    // 2. Removes active state from all buttons
    // 3. Shows selected tab content
    // 4. Adds active state to clicked button
    // 5. Updates ARIA attributes

CSS Classes
~~~~~~~~~~~

**Active Tab Button (Topline):**

.. code-block:: css

    bg-red-50 border-l-4 border-red-500 text-red-700

**Active Tab Button (Other):**

.. code-block:: css

    bg-green-50 border-l-4 border-green-500 text-green-700

**Inactive Tab Button:**

.. code-block:: css

    text-gray-700 hover:bg-gray-50

Accessibility
~~~~~~~~~~~~~

- Proper ARIA attributes (``role="tab"``, ``aria-selected``, ``aria-controls``)
- Keyboard navigation support
- Screen reader friendly
- Focus indicators visible

Responsive Design
~~~~~~~~~~~~~~~~~

- Tailwind CSS classes ensure mobile compatibility
- Sidebar collapses on smaller screens
- Grid layouts adapt to screen size

Templates
~~~~~~~~~

**Component Templates:**

- ``/templates/promapp/components/topline_vertical_tabs.html``
- ``/templates/promapp/components/other_constructs_vertical_tabs.html``
- ``/templates/promapp/components/composite_scores_section.html``

**Main Template:**

- ``/templates/promapp/prom_review.html`` - Contains switchTab() function

Django Cotton Components
------------------------

SATHI uses Django Cotton for reusable UI components.

Card Component
~~~~~~~~~~~~~~

**Usage:**

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
     - Optional subtitle
   * - ``header_actions``
     - string
     - -
     - HTML for header buttons
   * - ``footer``
     - string
     - -
     - HTML for footer
   * - ``shadow``
     - string
     - "md"
     - Shadow level: none, sm, md, lg, xl
   * - ``rounded``
     - string
     - "md"
     - Border radius: none, sm, md, lg, xl
   * - ``padding``
     - string
     - "md"
     - Padding level: none, sm, md, lg, xl

**Mobile Responsiveness:**

.. code-block:: html

    <!-- Responsive content inside cards -->
    <c-card title="Patient Info" padding="md">
        <div class="flex flex-col sm:flex-row sm:justify-between gap-3">
            <div class="flex-1 min-w-0">
                <h3 class="truncate">{{ patient.name }}</h3>
            </div>
        </div>
    </c-card>

Field Display Component
~~~~~~~~~~~~~~~~~~~~~~~

**Usage:**

.. code-block:: html

    <c-field_display 
        label="Patient Name" 
        value="{{ patient.name }}"
        badge="true"
        badge_color="blue" />

**Props:**

- ``label`` - Field label text
- ``value`` - Field value to display
- ``badge`` - Display as badge (true/false)
- ``badge_color`` - Badge color (blue, green, red, yellow, gray)

Button Components
~~~~~~~~~~~~~~~~~

**Primary Button:**

.. code-block:: html

    <c-button 
        text="Save Changes"
        type="submit"
        color="primary" />

**Action Buttons:**

.. code-block:: html

    <c-action_buttons>
        <c-button text="Edit" color="primary" />
        <c-button text="Delete" color="danger" />
    </c-action_buttons>

Dropdown Component
~~~~~~~~~~~~~~~~~~

**Usage:**

.. code-block:: html

    <c-dropdown 
        label="Actions"
        items='[
            {"text": "Edit", "url": "/edit/"},
            {"text": "Delete", "url": "/delete/"}
        ]' />

List Card Component
~~~~~~~~~~~~~~~~~~~

**Usage:**

.. code-block:: html

    <c-list_card 
        items="{{ patients }}"
        title_field="name"
        subtitle_field="patient_id" />

Paginator Component
~~~~~~~~~~~~~~~~~~~

**Usage:**

.. code-block:: html

    <c-paginator 
        page_obj="{{ page_obj }}"
        base_url="/patients/" />

Best Practices
--------------

Responsive Design
~~~~~~~~~~~~~~~~~

**Mobile-First Approach:**

.. code-block:: html

    <!-- Stack on mobile, grid on desktop -->
    <div class="flex flex-col sm:grid sm:grid-cols-2 gap-4">
        <!-- Content -->
    </div>

**Responsive Padding:**

.. code-block:: html

    <!-- Smaller padding on mobile -->
    <div class="p-4 sm:p-6 lg:p-8">
        <!-- Content -->
    </div>

**Text Truncation:**

.. code-block:: html

    <!-- Prevent overflow on small screens -->
    <h3 class="truncate">{{ long_text }}</h3>

Accessibility
~~~~~~~~~~~~~

**ARIA Attributes:**

.. code-block:: html

    <button 
        role="tab"
        aria-selected="true"
        aria-controls="panel-1">
        Tab 1
    </button>

**Keyboard Navigation:**

- Ensure all interactive elements are keyboard accessible
- Use proper focus indicators
- Support Tab, Enter, and Arrow keys

**Screen Readers:**

- Use semantic HTML elements
- Provide alt text for images
- Add ARIA labels where needed

Performance
~~~~~~~~~~~

**Lazy Loading:**

- Use HTMX ``hx-trigger="revealed"`` for plots
- Load content on-demand
- Reduce initial page load time

**CSS Optimization:**

- Build Tailwind CSS for production
- Remove unused styles
- Minimize file size

**Image Optimization:**

- Use appropriate image formats
- Compress images
- Implement responsive images

Resources
---------

- `Tailwind CSS Documentation <https://tailwindcss.com/docs/>`_
- `Django Cotton Documentation <https://django-cotton.com/>`_
- `HTMX Documentation <https://htmx.org/docs/>`_
- `Django i18n Documentation <https://docs.djangoproject.com/en/stable/topics/i18n/>`_
