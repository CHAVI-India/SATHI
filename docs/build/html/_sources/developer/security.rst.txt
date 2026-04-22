Security & Permissions
=======================

Complete guide to SATHI's security architecture, permissions system, and access control.

.. contents:: Table of Contents
   :local:
   :depth: 3

Overview
--------

SATHI implements a multi-layered security architecture:

- **Authentication**: Django Allauth with email-based login
- **Authorization**: Role-based access control (RBAC) with Django groups
- **Data Isolation**: Institution-based row-level security
- **Encryption**: Field-level encryption for sensitive data
- **Session Security**: Secure session management with IP/agent binding
- **Content Security**: CSP headers and security middleware

Django Groups & Permissions
----------------------------

SATHI uses Django's built-in groups system to manage user permissions efficiently.

Group Structure
~~~~~~~~~~~~~~~

Four primary groups organize user roles:

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Group Name
     - Purpose
   * - **Patients**
     - Access to questionnaires and personal health data
   * - **Healthcare Providers**
     - View and manage patients within their institution
   * - **Patient Registration Staff**
     - Register and manage patient information
   * - **Questionnaire Creators**
     - Create and manage questionnaires and items

.. note::
   The exact group name doesn't matter - the permissions assigned to each group are what's important.

Patients Group
~~~~~~~~~~~~~~

**Purpose:** Allow patients to complete questionnaires and view their own data.

**Required Permissions:**

1. **View PatientQuestionnaire** (``promapp.view_patientquestionnaire``)
   
   - Allows patients to see questionnaires assigned to them
   - Required for questionnaire list page

2. **Add QuestionnaireItemResponse** (``promapp.add_questionnaireitemresponse``)
   
   - Allows patients to submit responses to questions
   - Required for answering questionnaires

3. **Add QuestionnaireSubmission** (``promapp.add_questionnairesubmission``)
   
   - Allows patients to create new submissions
   - Required for completing questionnaires

**Configuration:**

.. code-block:: python

    # In Django admin or shell
    from django.contrib.auth.models import Group, Permission
    
    patients_group = Group.objects.create(name='Patients')
    
    # Add permissions
    patients_group.permissions.add(
        Permission.objects.get(codename='view_patientquestionnaire'),
        Permission.objects.get(codename='add_questionnaireitemresponse'),
        Permission.objects.get(codename='add_questionnairesubmission'),
    )

Healthcare Providers Group
~~~~~~~~~~~~~~~~~~~~~~~~~~

**Purpose:** Enable healthcare providers to view and manage patients within their institution.

**Core Permissions:**

1. **View Patient** (``patientapp.view_patient``)
   
   - View patient information and lists
   - Access patient detail pages

2. **View PatientQuestionnaire** (``promapp.view_patientquestionnaire``)
   
   - See assigned questionnaires

3. **Add PatientQuestionnaire** (``promapp.add_patientquestionnaire``)
   
   - Assign questionnaires to patients

4. **View QuestionnaireItemResponse** (``promapp.view_questionnaireitemresponse``)
   
   - Review patient responses

5. **View QuestionnaireSubmission** (``promapp.view_questionnairesubmission``)
   
   - See completed submissions

**Optional Permissions (Based on Role):**

6. **Add Diagnosis** (``patientapp.add_diagnosis``)
   
   - Add diagnoses to patients

7. **Change Diagnosis** (``patientapp.change_diagnosis``)
   
   - Update patient diagnoses

8. **Add Treatment** (``patientapp.add_treatment``)
   
   - Add treatments to diagnoses

9. **Change Treatment** (``patientapp.change_treatment``)
   
   - Update patient treatments

**Security Notes:**

.. warning::
   - **Institution-based Access Control**: Providers can only view/manage patients from their own institution
   - **No Delete Permissions**: Intentionally excluded for data integrity and audit trails
   - **Provider Profile Required**: Users must have a Provider profile linked to an Institution
   - **Patient Portal Exclusion**: Providers should NOT access the patient portal

**Configuration:**

.. code-block:: python

    providers_group = Group.objects.create(name='Healthcare Providers')
    
    # Core permissions
    providers_group.permissions.add(
        Permission.objects.get(codename='view_patient'),
        Permission.objects.get(codename='view_patientquestionnaire'),
        Permission.objects.get(codename='add_patientquestionnaire'),
        Permission.objects.get(codename='view_questionnaireitemresponse'),
        Permission.objects.get(codename='view_questionnairesubmission'),
    )
    
    # Optional clinical permissions
    providers_group.permissions.add(
        Permission.objects.get(codename='add_diagnosis'),
        Permission.objects.get(codename='change_diagnosis'),
        Permission.objects.get(codename='add_treatment'),
        Permission.objects.get(codename='change_treatment'),
    )

Patient Registration Staff Group
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Purpose:** Administrative staff for patient registration and data management.

**Core Permissions:**

1. **View Patient** (``patientapp.view_patient``)
   
   - View existing patients, check for duplicates

2. **Add Patient** (``patientapp.add_patient``)
   
   - Register new patients

3. **Change Patient** (``patientapp.change_patient``)
   
   - Update patient information

4. **View Institution** (``patientapp.view_institution``)
   
   - See available institutions

**Optional Permissions:**

5. **Add Diagnosis** (``patientapp.add_diagnosis``)
   
   - Initial diagnosis entry

6. **Change Diagnosis** (``patientapp.change_diagnosis``)
   
   - Update diagnosis information

7. **View DiagnosisList** (``patientapp.view_diagnosislist``)
   
   - See available diagnoses

8. **View TreatmentType** (``patientapp.view_treatmenttype``)
   
   - See available treatment types

**Security Notes:**

.. note::
   - Same institution-based filtering applies
   - No questionnaire or response access
   - No delete permissions
   - Limited clinical data access

Questionnaire Creators Group
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Purpose:** Create and manage questionnaires, items, and scales.

**Required Permissions:**

All permissions need **View**, **Add**, and **Change** for:

1. **Questionnaire** (``promapp.view/add/change_questionnaire``)
2. **Item** (``promapp.view/add/change_item``)
3. **LikertScale** (``promapp.view/add/change_likertscale``)
4. **LikertScaleResponseOption** (``promapp.view/add/change_likertscaleresponseoption``)
5. **RangeScale** (``promapp.view/add/change_rangescale``)
6. **ConstructScale** (``promapp.view/add/change_constructscale``)
7. **QuestionnaireItem** (``promapp.view/add/change_questionnaireitem``)

**Configuration:**

.. code-block:: python

    creators_group = Group.objects.create(name='Questionnaire Creators')
    
    models = [
        'questionnaire', 'item', 'likertscale', 
        'likertscaleresponseoption', 'rangescale',
        'constructscale', 'questionnaireitem'
    ]
    
    for model in models:
        creators_group.permissions.add(
            Permission.objects.get(codename=f'view_{model}'),
            Permission.objects.get(codename=f'add_{model}'),
            Permission.objects.get(codename=f'change_{model}'),
        )

.. note::
   - Delete permissions not recommended except for privileged users
   - Permissions also allow adding translations to items

Institution-Based Access Control
---------------------------------

SATHI implements row-level security based on institutions to ensure data isolation.

Architecture
~~~~~~~~~~~~

**Key Principles:**

- **Providers**: Can only see/manage patients from their institution
- **Non-providers** (superusers, admin): Can see all patients
- **Patients**: Can only see their own data

**Implementation Approach:**

- View-level filtering combined with mixin approach
- Clear and explicit behavior
- Django-native patterns
- Easy to test and debug

Utility Functions
~~~~~~~~~~~~~~~~~

Located in ``patientapp/utils.py``:

**get_user_institution(user)**

Get the institution for the current user if they are a provider.

.. code-block:: python

    from patientapp.utils import get_user_institution
    
    institution = get_user_institution(request.user)
    if institution:
        # User is a provider with an institution
        pass

**is_provider_user(user)**

Check if the user is a provider.

.. code-block:: python

    from patientapp.utils import is_provider_user
    
    if is_provider_user(request.user):
        # Apply provider-specific logic
        pass

**filter_patients_by_institution(queryset, user)**

Filter a Patient queryset based on user's institution.

.. code-block:: python

    from patientapp.utils import filter_patients_by_institution
    
    patients = Patient.objects.all()
    accessible_patients = filter_patients_by_institution(patients, request.user)

**check_patient_access(user, patient)**

Check if a user can access a specific patient.

.. code-block:: python

    from patientapp.utils import check_patient_access
    
    if not check_patient_access(request.user, patient):
        raise PermissionDenied

**get_accessible_patient_or_404(user, pk)**

Get a patient by pk, ensuring the user has access.

.. code-block:: python

    from patientapp.utils import get_accessible_patient_or_404
    
    patient = get_accessible_patient_or_404(request.user, patient_id)

Institution Filter Mixin
~~~~~~~~~~~~~~~~~~~~~~~~

For class-based views, use ``InstitutionFilterMixin``:

.. code-block:: python

    from patientapp.utils import InstitutionFilterMixin
    from django.views.generic import ListView
    
    class PatientListView(InstitutionFilterMixin, ListView):
        model = Patient
        template_name = 'patientapp/patient_list.html'
        
        # Mixin automatically filters queryset by institution

**Methods:**

- ``get_queryset()``: Automatically filters by institution
- ``get_object()``: Ensures user has access to the object

Protected Views
~~~~~~~~~~~~~~~

**Function-Based Views:**

.. code-block:: python

    from patientapp.utils import get_accessible_patient_or_404
    
    @login_required
    @permission_required('patientapp.view_patient')
    def patient_detail(request, pk):
        patient = get_accessible_patient_or_404(request.user, pk)
        # ... rest of view

**Class-Based Views:**

.. code-block:: python

    from patientapp.utils import InstitutionFilterMixin
    
    class PatientCreateView(InstitutionFilterMixin, CreateView):
        model = Patient
        # Institution automatically enforced

Security Features
~~~~~~~~~~~~~~~~~

**Institution Dropdown Filtering:**

- Providers: Only see their institution
- Non-providers: See all institutions

**Patient Creation:**

- Providers: Can only create patients in their institution
- Form automatically pre-selects and locks provider's institution

**Patient Updates:**

- Providers: Cannot move patients to different institutions
- Institution field automatically enforced

**Error Handling:**

- 404 errors for patients not in user's institution
- Clear error messages
- Audit logging

Content Security Policy (CSP)
------------------------------

SATHI implements strict CSP headers for security.

Configuration
~~~~~~~~~~~~~

Located in ``chaviprom/settings.py``:

.. code-block:: python

    # Content Security Policy
    CSP_DEFAULT_SRC = ("'self'",)
    CSP_SCRIPT_SRC = ("'self'", "'unsafe-inline'", "cdn.jsdelivr.net")
    CSP_STYLE_SRC = ("'self'", "'unsafe-inline'", "fonts.googleapis.com")
    CSP_FONT_SRC = ("'self'", "fonts.gstatic.com")
    CSP_IMG_SRC = ("'self'", "data:", "https:")
    CSP_CONNECT_SRC = ("'self'",)
    
    # Service Worker and PWA support
    CSP_WORKER_SRC = ("'self'",)
    CSP_MANIFEST_SRC = ("'self'",)
    
    # reCAPTCHA support
    CSP_SCRIPT_SRC += ("https://www.google.com", "https://www.gstatic.com")
    CSP_FRAME_SRC = ("https://www.google.com",)

PWA Service Workers
~~~~~~~~~~~~~~~~~~~

**Requirements:**

1. **Secure Context**: HTTPS or localhost
2. **CSP Permissions**: ``worker-src`` and ``manifest-src``

**Service Worker Registration:**

.. code-block:: html

    <!-- templates/base.html -->
    <link rel="manifest" href="{% url 'manifest' %}">
    
    <script>
        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.register('/serviceworker.js');
        }
    </script>

**Caching Strategy:**

.. code-block:: javascript

    // static/js/serviceworker.js
    
    // Network-first for HTML pages
    if (request.destination === 'document') {
        return fetch(request)
            .then(response => {
                cache.put(request, response.clone());
                return response;
            })
            .catch(() => cache.match(request));
    }
    
    // Cache-first for static assets
    if (request.destination === 'style' || 
        request.destination === 'script' ||
        request.destination === 'image') {
        return cache.match(request)
            .then(response => response || fetch(request));
    }

Field-Level Encryption
----------------------

SATHI uses ``django-secured-fields`` for encrypting sensitive patient data.

Configuration
~~~~~~~~~~~~~

**Environment Variable:**

.. code-block:: bash

    # .env file
    DJANGO_SECURED_FIELDS_KEY=your-encryption-key-here

**Generate Encryption Key:**

.. code-block:: bash

    python manage.py generate_key

**Key Rotation:**

.. code-block:: bash

    # Comma-separated list for key rotation
    DJANGO_SECURED_FIELDS_KEY=new-key,old-key-1,old-key-2

Encrypted Fields
~~~~~~~~~~~~~~~~

**Patient Model:**

.. code-block:: python

    from secured_fields import EncryptedCharField
    
    class Patient(models.Model):
        name = EncryptedCharField(max_length=255)
        patient_id = EncryptedCharField(max_length=50, unique=True)
        # ... other fields

**Usage:**

.. code-block:: python

    # Encryption/decryption is automatic
    patient = Patient.objects.create(
        name="John Doe",  # Automatically encrypted
        patient_id="P12345"
    )
    
    # Decryption is automatic when accessing
    print(patient.name)  # "John Doe" (decrypted)

**Searching Encrypted Fields:**

.. code-block:: python

    # Cannot use __icontains or __startswith
    # Must decrypt server-side for search
    
    def search_patients(query):
        patients = Patient.objects.all()
        results = [
            p for p in patients 
            if query.lower() in p.name.lower()
        ]
        return results

Authentication & Session Security
----------------------------------

Django Allauth Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Email-Based Login:**

.. code-block:: python

    # settings.py
    ACCOUNT_LOGIN_BY_CODE_ENABLED = True
    ACCOUNT_LOGIN_BY_CODE_MAX_ATTEMPTS = 3
    ACCOUNT_LOGIN_BY_CODE_TIMEOUT = 300  # 5 minutes
    ACCOUNT_EMAIL_REQUIRED = True
    ACCOUNT_EMAIL_VERIFICATION = 'mandatory'

**Session Security:**

.. code-block:: python

    # Session settings
    SESSION_COOKIE_SECURE = True  # HTTPS only
    SESSION_COOKIE_HTTPONLY = True  # No JavaScript access
    SESSION_COOKIE_SAMESITE = 'Lax'  # CSRF protection
    SESSION_COOKIE_AGE = 3600  # 1 hour

Rate Limiting
~~~~~~~~~~~~~

**Login Rate Limiting:**

.. code-block:: python

    from django_ratelimit.decorators import ratelimit
    
    @ratelimit(key='user_or_ip', rate='5/m', method='POST')
    def login_view(request):
        # Login logic
        pass

**Password Reset Rate Limiting:**

.. code-block:: python

    PASSWORD_RESET_RATE_LIMIT_COUNT = 2
    PASSWORD_RESET_RATE_LIMIT_PERIOD = '10m'

reCAPTCHA Integration
~~~~~~~~~~~~~~~~~~~~~

**Configuration:**

.. code-block:: python

    # settings.py
    RECAPTCHA_DEFAULT_ACTION = 'generic'
    RECAPTCHA_SCORE_THRESHOLD = 0.5
    
    # Environment variables
    RECAPTCHA_PUBLIC_KEY = os.getenv('RECAPTCHA_PUBLIC_KEY')
    RECAPTCHA_PRIVATE_KEY = os.getenv('RECAPTCHA_PRIVATE_KEY')

**Form Integration:**

.. code-block:: python

    from django_recaptcha.fields import ReCaptchaField
    
    class LoginForm(forms.Form):
        username = forms.CharField()
        password = forms.CharField(widget=forms.PasswordInput)
        captcha = ReCaptchaField()

Best Practices
--------------

Permission Management
~~~~~~~~~~~~~~~~~~~~~

**DO:**

- Use Django groups for role-based access
- Apply principle of least privilege
- Test permissions thoroughly
- Document permission requirements
- Use institution-based filtering for providers

**DON'T:**

- Grant delete permissions without careful consideration
- Give providers access to patient portal
- Allow cross-institution data access
- Hardcode permissions in views

Security Checklist
~~~~~~~~~~~~~~~~~~

**Deployment:**

- [ ] Set ``DEBUG = False`` in production
- [ ] Use strong ``SECRET_KEY``
- [ ] Enable HTTPS with valid SSL certificate
- [ ] Configure CSP headers
- [ ] Set secure cookie flags
- [ ] Enable rate limiting
- [ ] Configure reCAPTCHA
- [ ] Set up encryption keys
- [ ] Review all permissions
- [ ] Test institution-based access control

**Ongoing:**

- [ ] Regular security audits
- [ ] Monitor failed login attempts
- [ ] Review access logs
- [ ] Update dependencies
- [ ] Rotate encryption keys periodically
- [ ] Test backup and recovery

Troubleshooting
---------------

Common Issues
~~~~~~~~~~~~~

**Users Can't Access Patients:**

1. Check user has correct group membership
2. Verify Provider profile exists and is linked to Institution
3. Check patient belongs to provider's institution
4. Verify permissions are assigned to group

**Service Worker Not Registering:**

1. Ensure HTTPS is enabled (or using localhost)
2. Check CSP headers include ``worker-src 'self'``
3. Verify manifest URL is correct
4. Check browser console for errors

**Encrypted Field Search Not Working:**

1. Cannot use Django ORM filters on encrypted fields
2. Must decrypt server-side for searching
3. Use custom search functions
4. Consider using Select2 with AJAX for large datasets

**Permission Denied Errors:**

1. Check user is authenticated
2. Verify user has required permissions
3. Check institution-based access control
4. Review view decorators and mixins

Resources
---------

- `Django Permissions Documentation <https://docs.djangoproject.com/en/stable/topics/auth/default/#permissions-and-authorization>`_
- `Django Allauth Documentation <https://django-allauth.readthedocs.io/>`_
- `django-secured-fields <https://github.com/your-repo/django-secured-fields>`_
- `Content Security Policy Guide <https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP>`_
- `OWASP Security Guidelines <https://owasp.org/>`_
