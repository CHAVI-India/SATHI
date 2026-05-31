Roles and Permissions Configuration Guide
==========================================

Overview
--------

This document provides a comprehensive guide to configuring user roles and permissions in CHAVI-PROM. The system uses Django's built-in groups and permissions system to implement role-based access control (RBAC).

Default User Groups
-------------------

The following standard groups should be created for typical deployments:

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
   * - **REDCap Data Managers**
     - Manage REDCap integration and data export

1. Patients Group
-----------------

**Purpose:** Allow patients to complete questionnaires and view their own data.

Required Permissions
~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Permission
     - Purpose
   * - ``promapp.view_patientquestionnaire``
     - See questionnaires assigned to them
   * - ``promapp.add_questionnaireitemresponse``
     - Submit responses to questions
   * - ``promapp.add_questionnairesubmission``
     - Create new submissions

Configuration
~~~~~~~~~~~~~

.. code-block:: python

    from django.contrib.auth.models import Group, Permission

    patients_group = Group.objects.create(name='Patients')

    # Add permissions
    patients_group.permissions.add(
        Permission.objects.get(codename='view_patientquestionnaire'),
        Permission.objects.get(codename='add_questionnaireitemresponse'),
        Permission.objects.get(codename='add_questionnairesubmission'),
    )

2. Healthcare Providers Group
-----------------------------

**Purpose:** Enable healthcare providers to view and manage patients within their institution.

Core Permissions
~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Permission
     - Purpose
   * - ``patientapp.view_patient``
     - View patient information and lists
   * - ``promapp.view_patientquestionnaire``
     - See assigned questionnaires
   * - ``promapp.add_patientquestionnaire``
     - Assign questionnaires to patients
   * - ``promapp.view_questionnaireitemresponse``
     - Review patient responses
   * - ``promapp.view_questionnairesubmission``
     - See completed submissions

Optional Clinical Permissions (Role-Based)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Permission
     - Purpose
   * - ``patientapp.add_diagnosis``
     - Add diagnoses to patients
   * - ``patientapp.change_diagnosis``
     - Update patient diagnoses
   * - ``patientapp.add_treatment``
     - Add treatments to diagnoses
   * - ``patientapp.change_treatment``
     - Update patient treatments
   * - ``patientapp.add_patientproject``
     - Assign patients to projects

Configuration
~~~~~~~~~~~~~

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
        Permission.objects.get(codename='add_patientproject'),
    )

Security Notes
~~~~~~~~~~~~~~

.. warning::
   - **Institution-based Access Control**: Providers can only view/manage patients from their own institution
   - **No Delete Permissions**: Intentionally excluded for data integrity and audit trails
   - **Provider Profile Required**: Users must have a Provider profile linked to an Institution
   - **Patient Portal Exclusion**: Providers should NOT access the patient portal

3. Patient Registration Staff Group
-----------------------------------

**Purpose:** Administrative staff for patient registration and data management.

Core Permissions
~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Permission
     - Purpose
   * - ``patientapp.view_patient``
     - View existing patients, check for duplicates
   * - ``patientapp.add_patient``
     - Register new patients
   * - ``patientapp.change_patient``
     - Update patient information
   * - ``patientapp.view_institution``
     - See available institutions

Optional Permissions (Extended Role)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Permission
     - Purpose
   * - ``patientapp.add_diagnosis``
     - Initial diagnosis entry during registration
   * - ``patientapp.change_diagnosis``
     - Update diagnosis information
   * - ``patientapp.view_diagnosislist``
     - See available diagnoses
   * - ``patientapp.view_treatmenttype``
     - See available treatment types
   * - ``patientapp.add_treatment``
     - Add treatments during registration
   * - ``patientapp.add_patientproject``
     - Assign patients to projects during registration

Configuration
~~~~~~~~~~~~~

.. code-block:: python

    registration_staff_group = Group.objects.create(name='Patient Registration Staff')

    # Core permissions
    registration_staff_group.permissions.add(
        Permission.objects.get(codename='view_patient'),
        Permission.objects.get(codename='add_patient'),
        Permission.objects.get(codename='change_patient'),
        Permission.objects.get(codename='view_institution'),
    )

    # Optional permissions for extended registration role
    registration_staff_group.permissions.add(
        Permission.objects.get(codename='add_diagnosis'),
        Permission.objects.get(codename='change_diagnosis'),
        Permission.objects.get(codename='view_diagnosislist'),
        Permission.objects.get(codename='view_treatmenttype'),
        Permission.objects.get(codename='add_treatment'),
        Permission.objects.get(codename='add_patientproject'),
    )

Security Notes
~~~~~~~~~~~~~~

.. note::
   - Same institution-based filtering applies as for providers
   - No questionnaire or response access (clinical data only)
   - No delete permissions
   - Limited clinical data access based on optional permissions
   - Can be combined with ``add_diagnosis`` and ``add_treatment`` for comprehensive registration workflow

4. Questionnaire Creators Group
-------------------------------

**Purpose:** Create and manage questionnaires, items, and scales.

Required Permissions
~~~~~~~~~~~~~~~~~~~~

All permissions need **View**, **Add**, and **Change** for the following models:

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Model
     - Permission Pattern
   * - Questionnaire
     - ``promapp.view/add/change_questionnaire``
   * - Item
     - ``promapp.view/add/change_item``
   * - LikertScale
     - ``promapp.view/add/change_likertscale``
   * - LikertScaleResponseOption
     - ``promapp.view/add/change_likertscaleresponseoption``
   * - RangeScale
     - ``promapp.view/add/change_rangescale``
   * - ConstructScale
     - ``promapp.view/add/change_constructscale``
   * - QuestionnaireItem
     - ``promapp.view/add/change_questionnaireitem``
   * - Construct
     - ``promapp.view/add/change_construct``
   * - CompositeConstruct
     - ``promapp.view/add/change_compositeconstruct``

Configuration
~~~~~~~~~~~~~

.. code-block:: python

    creators_group = Group.objects.create(name='Questionnaire Creators')

    models = [
        'questionnaire', 'item', 'likertscale',
        'likertscaleresponseoption', 'rangescale',
        'constructscale', 'questionnaireitem',
        'construct', 'compositeconstruct'
    ]

    for model in models:
        creators_group.permissions.add(
            Permission.objects.get(codename=f'view_{model}'),
            Permission.objects.get(codename=f'add_{model}'),
            Permission.objects.get(codename=f'change_{model}'),
        )

Notes
~~~~~

- Delete permissions not recommended except for privileged users
- Permissions also allow adding translations to items

5. REDCap Data Managers Group
-------------------------------

**Purpose:** Manage REDCap integration, field mappings, and data export.

Required Permissions
~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 50 50

   * - Model
     - Permissions
   * - ``RedcapFormToQuestionnaireMapping``
     - ``view``, ``add``, ``change``, ``delete``
   * - ``RedcapFieldToItemMapping``
     - ``view``, ``add``, ``change``, ``delete``
   * - ``RedcapStudyIDtoPatientIDMap``
     - ``view``, ``add``, ``change``, ``delete``
   * - ``RedcapInstanceToSubmissionMapping``
     - ``view``, ``add``, ``change``

Configuration
~~~~~~~~~~~~~

.. code-block:: python

    from django.contrib.contenttypes.models import ContentType

    redcap_managers, _ = Group.objects.get_or_create(name='REDCap Data Managers')

    # Add all REDCap permissions
    redcap_models = [
        'redcapformtoquestionnairemapping',
        'redcapfieldtoitemmapping',
        'redcapstudyidtopatientidmap',
        'redcapinstancetosubmissionmapping',
    ]

    for model in redcap_models:
        for action in ['view', 'add', 'change', 'delete']:
            try:
                perm = Permission.objects.get(
                    codename=f'{action}_{model}',
                    content_type__app_label='patientapp'
                )
                redcap_managers.permissions.add(perm)
            except Permission.DoesNotExist:
                pass  # Model may not exist yet (run migrations first)

REDCap Permission Details
~~~~~~~~~~~~~~~~~~~~~~~~~

Generated Permission Codenames
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Django automatically creates permissions using the pattern ``{action}_{modelname}``:

- ``view_redcapformtoquestionnairemapping`` – View form mappings
- ``add_redcapformtoquestionnairemapping`` – Create new form mappings
- ``change_redcapformtoquestionnairemapping`` – Edit form mappings
- ``delete_redcapformtoquestionnairemapping`` – Delete form mappings

- ``view_redcapfieldtoitemmapping`` – View field mappings
- ``add_redcapfieldtoitemmapping`` – Create field mappings
- ``change_redcapfieldtoitemmapping`` – Edit field mappings
- ``delete_redcapfieldtoitemmapping`` – Remove field mappings

- ``view_redcapstudyidtopatientidmap`` – View patient ID mappings
- ``add_redcapstudyidtopatientidmap`` – Assign study IDs to patients
- ``change_redcapstudyidtopatientidmap`` – Edit patient ID mappings
- ``delete_redcapstudyidtopatientidmap`` – Clear patient ID mappings

- ``view_redcapinstancetosubmissionmapping`` – View submission matches
- ``add_redcapinstancetosubmissionmapping`` – Create submission matches
- ``change_redcapinstancetosubmissionmapping`` – Edit submission matches

Permission Mapping to Operations
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. list-table::
   :header-rows: 1
   :widths: 30 20 50

   * - Operation
     - Permission
     - Notes
   * - View Form Mappings list
     - view_redcapformtoquestionnairemapping
     - Required to see form mappings page
   * - Add Form Mapping
     - add_redcapformtoquestionnairemapping
     - "Add Form Mapping" button visibility
   * - Edit Form Mapping
     - change_redcapformtoquestionnairemapping
     - Edit button + update view access
   * - Delete Form Mapping
     - delete_redcapformtoquestionnairemapping
     - Delete button + delete view access
   * - View Field Mappings
     - view_redcapfieldtoitemmapping
     - Saved mappings section visibility
   * - Add Field Mappings
     - add_redcapfieldtoitemmapping
     - Suggested mappings + Save button
   * - Edit Field Mapping
     - change_redcapfieldtoitemmapping
     - Edit row toggle + save
   * - Delete Field Mapping
     - delete_redcapfieldtoitemmapping
     - Remove button
   * - Assign Patient Study ID
     - change_redcapstudyidtopatientidmap
     - Assign/Edit button
   * - Match Submissions
     - change_redcapinstancetosubmissionmapping
     - Match link access
   * - Clear Patient Mapping
     - delete_redcapstudyidtopatientidmap
     - Clear button + delete view

REDCap Role Recommendations
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Role
     - Suggested Permissions
   * - REDCap Data Manager
     - All view/add/change/delete permissions on all 4 models
   * - Project Coordinator
     - view/add/change on Form/Field mappings; view/change on Patient IDs; view on Submission matching
   * - Research Assistant
     - view on all models; change on Patient IDs and Submission matching (for data entry)
   * - Read-only Auditor
     - view permissions only on all models

Additional Requirements
~~~~~~~~~~~~~~~~~~~~~~~~~

- Data export requires **staff status** (``request.user.is_staff``)
- Grant staff status via Django admin for users who need to export data

Permission Matrix Summary
-------------------------

.. list-table::
   :header-rows: 1
   :widths: 20 15 15 20 15 15

   * - Group
     - Patient Data
     - Clinical Data
     - Questionnaires
     - REDCap
     - Institution Filter
   * - **Patients**
     - Own data only
     - -
     - View/Submit
     - -
     - N/A
   * - **Healthcare Providers**
     - View/Manage
     - Diagnosis/Treatment
     - View/Assign
     - -
     - Yes
   * - **Patient Registration Staff**
     - Add/Change
     - Optional
     - -
     - -
     - Yes
   * - **Questionnaire Creators**
     - -
     - -
     - Full CRUD
     - -
     - No
   * - **REDCap Data Managers**
     - View
     - -
     - View
     - Full CRUD
     - Yes

Implementation Guide
--------------------

Creating Groups Programmatically
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Run this in Django shell or as a migration/data script:

.. code-block:: python

    from django.contrib.auth.models import Group, Permission
    from django.contrib.contenttypes.models import ContentType

    def setup_groups():
        """Create all standard groups with their permissions."""

        # 1. Patients Group
        patients, _ = Group.objects.get_or_create(name='Patients')
        patient_perms = [
            'view_patientquestionnaire',
            'add_questionnaireitemresponse',
            'add_questionnairesubmission',
        ]
        for codename in patient_perms:
            perm = Permission.objects.get(codename=codename)
            patients.permissions.add(perm)

        # 2. Healthcare Providers Group
        providers, _ = Group.objects.get_or_create(name='Healthcare Providers')
        provider_perms = [
            'view_patient',
            'view_patientquestionnaire',
            'add_patientquestionnaire',
            'view_questionnaireitemresponse',
            'view_questionnairesubmission',
            # Optional clinical
            'add_diagnosis',
            'change_diagnosis',
            'add_treatment',
            'change_treatment',
            'add_patientproject',
        ]
        for codename in provider_perms:
            perm = Permission.objects.get(codename=codename)
            providers.permissions.add(perm)

        # 3. Patient Registration Staff Group
        registration, _ = Group.objects.get_or_create(name='Patient Registration Staff')
        reg_perms = [
            'view_patient',
            'add_patient',
            'change_patient',
            'view_institution',
            # Optional for comprehensive registration
            'add_diagnosis',
            'change_diagnosis',
            'view_diagnosislist',
            'view_treatmenttype',
            'add_treatment',
            'add_patientproject',
        ]
        for codename in reg_perms:
            perm = Permission.objects.get(codename=codename)
            registration.permissions.add(perm)

        # 4. Questionnaire Creators Group
        creators, _ = Group.objects.get_or_create(name='Questionnaire Creators')
        models = [
            'questionnaire', 'item', 'likertscale',
            'likertscaleresponseoption', 'rangescale',
            'constructscale', 'questionnaireitem',
            'construct', 'compositeconstruct'
        ]
        for model in models:
            for action in ['view', 'add', 'change']:
                perm = Permission.objects.get(codename=f'{action}_{model}')
                creators.permissions.add(perm)

        # 5. REDCap Data Managers Group
        redcap, _ = Group.objects.get_or_create(name='REDCap Data Managers')
        redcap_models = [
            'redcapformtoquestionnairemapping',
            'redcapfieldtoitemmapping',
            'redcapstudyidtopatientidmap',
            'redcapinstancetosubmissionmapping',
        ]
        for model in redcap_models:
            for action in ['view', 'add', 'change', 'delete']:
                try:
                    perm = Permission.objects.get(
                        codename=f'{action}_{model}',
                        content_type__app_label='patientapp'
                    )
                    redcap.permissions.add(perm)
                except Permission.DoesNotExist:
                    pass

        print("All groups and permissions configured successfully!")

    # Run the setup
    setup_groups()

Assigning Users to Groups
~~~~~~~~~~~~~~~~~~~~~~~~~~

Via Django Admin:

1. Go to ``/admin/auth/user/``
2. Select user
3. Add to groups in the "Groups" section

Or programmatically:

.. code-block:: python

    from django.contrib.auth.models import User, Group

    user = User.objects.get(username='john_doe')
    providers_group = Group.objects.get(name='Healthcare Providers')
    user.groups.add(providers_group)

Best Practices
--------------

DO:
~~~

- Use Django groups for role-based access
- Apply principle of least privilege
- Test permissions thoroughly
- Document permission requirements
- Use institution-based filtering for providers and registration staff
- Grant ``add_diagnosis`` and ``add_treatment`` to registration staff for comprehensive intake workflow

DON'T:
~~~~~~

- Grant delete permissions without careful consideration
- Give providers access to patient portal
- Allow cross-institution data access
- Hardcode permissions in views
- Grant staff status unnecessarily (only for REDCap data export)

Troubleshooting
---------------

Users Can't Access Patients
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. Check user has correct group membership
2. Verify Provider profile exists and is linked to Institution (for providers)
3. Check patient belongs to user's institution
4. Verify permissions are assigned to group

Permission Denied Errors
~~~~~~~~~~~~~~~~~~~~~~~~

1. Check user is authenticated
2. Verify user has required permissions
3. Check institution-based access control
4. Review view decorators and mixins

Missing Permissions
~~~~~~~~~~~~~~~~~~~

If permissions don't exist, run:

.. code-block:: bash

    python manage.py migrate
    python manage.py shell -c "from django.contrib.auth.models import Permission; Permission.objects.all().count()"

Related Documentation
---------------------

- `Django Permissions Documentation <https://docs.djangoproject.com/en/stable/topics/auth/default/#permissions-and-authorization>`_
- `Security Guide <./security.rst>`_ - Complete security architecture
- `Patient Form Implementation </templates/patientapp/patient_form.html>`_ - Permission-based form sections
