Data Integration Guide
======================

Guide for integrating and extending SATHI's data models, particularly the date reference system.

.. contents:: Table of Contents
   :local:
   :depth: 3

Overview
--------

SATHI uses a flexible date reference system that allows users to select different starting points for calculating time intervals in PROM data visualization. This system is crucial for:

- Time-based analysis of patient outcomes
- Calculating intervals from significant clinical events
- Flexible reporting relative to different milestones

Date Reference System
---------------------

Current Date Types
~~~~~~~~~~~~~~~~~~

The system supports three types of date references:

1. **Patient Registration Date** (``date_of_registration``)
   
   - Field: ``Patient.date_of_registration``
   - Reference key: ``'date_of_registration'``
   - When patient was registered in the system

2. **Diagnosis Dates** (``date_of_diagnosis_<id>``)
   
   - Field: ``Diagnosis.date_of_diagnosis``
   - Reference key pattern: ``'date_of_diagnosis_{diagnosis.id}'``
   - When specific diagnosis was made

3. **Treatment Start Dates** (``date_of_start_of_treatment_<id>``)
   
   - Field: ``Treatment.date_of_start_of_treatment``
   - Reference key pattern: ``'date_of_start_of_treatment_{treatment.id}'``
   - When specific treatment began

Key Functions
~~~~~~~~~~~~~

Located in ``patientapp/utils.py``:

**get_patient_available_start_dates(patient)**

Collects all available date references for a patient.

.. code-block:: python

    from patientapp.utils import get_patient_available_start_dates
    
    available_dates = get_patient_available_start_dates(patient)
    # Returns: [(reference_key, display_name, date_value), ...]
    
    # Example output:
    # [
    #     ('date_of_registration', 'Date of Registration', datetime.date(2024, 1, 15)),
    #     ('date_of_diagnosis_123', 'Diagnosis: Cancer', datetime.date(2024, 2, 1)),
    #     ('date_of_start_of_treatment_456', 'Start of Treatment: Chemotherapy', datetime.date(2024, 2, 15))
    # ]

**get_patient_start_date(patient, start_date_reference)**

Retrieves the actual date value for a given reference key.

.. code-block:: python

    from patientapp.utils import get_patient_start_date
    
    start_date = get_patient_start_date(patient, 'date_of_diagnosis_123')
    # Returns: datetime.date(2024, 2, 1)

Adding New Date Fields
----------------------

This section explains how to add new date fields to existing models and integrate them into the date reference system.

Step 1: Add Date Field to Model
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Add your new date field to the model:

.. code-block:: python

    # In patientapp/models.py
    class Treatment(models.Model):
        # ... existing fields ...
        date_of_start_of_treatment = models.DateField(
            null=True, 
            blank=True,
            verbose_name="Date of Start of Treatment"
        )
        
        # NEW: Add your new date field
        date_of_follow_up = models.DateField(
            null=True, 
            blank=True,
            verbose_name="Date of Follow-up"
        )

**Create Migration:**

.. code-block:: bash

    python manage.py makemigrations
    python manage.py migrate

Step 2: Update get_patient_available_start_dates()
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Add logic to collect your new date field:

.. code-block:: python

    def get_patient_available_start_dates(patient):
        """Get all available start dates for a patient."""
        available_dates = []
        
        try:
            # Registration date
            if patient.date_of_registration:
                available_dates.append((
                    'date_of_registration',
                    'Date of Registration',
                    patient.date_of_registration
                ))
            
            # Diagnosis dates
            for diagnosis in patient.diagnosis_set.all():
                if diagnosis.date_of_diagnosis:
                    diagnosis_name = diagnosis.diagnosis.diagnosis if diagnosis.diagnosis else "Unknown"
                    available_dates.append((
                        f'date_of_diagnosis_{diagnosis.id}',
                        f'Diagnosis: {diagnosis_name}',
                        diagnosis.date_of_diagnosis
                    ))
            
            # Treatment dates (existing + new)
            for diagnosis in patient.diagnosis_set.all():
                diagnosis_name = diagnosis.diagnosis.diagnosis if diagnosis.diagnosis else "Unknown"
                treatments = diagnosis.treatment_set.filter(
                    models.Q(date_of_start_of_treatment__isnull=False) | 
                    models.Q(date_of_follow_up__isnull=False)  # NEW: Include follow-up dates
                ).order_by('date_of_start_of_treatment')
                
                for i, treatment in enumerate(treatments):
                    treatment_types = ", ".join([
                        tt.treatment_type 
                        for tt in treatment.treatment_type.all()
                    ]) if treatment.treatment_type.exists() else f"Treatment {i+1}"
                    
                    # Existing start date
                    if treatment.date_of_start_of_treatment:
                        available_dates.append((
                            f'date_of_start_of_treatment_{treatment.id}',
                            f'Start of Treatment: {treatment_types} ({diagnosis_name})',
                            treatment.date_of_start_of_treatment
                        ))
                    
                    # NEW: Add follow-up date
                    if treatment.date_of_follow_up:
                        available_dates.append((
                            f'date_of_follow_up_{treatment.id}',
                            f'Follow-up: {treatment_types} ({diagnosis_name})',
                            treatment.date_of_follow_up
                        ))
            
            # Sort by date
            available_dates.sort(key=lambda x: x[2])
            
        except Exception as e:
            logger.error(f"Error getting dates for patient {patient.id}: {e}")
        
        return available_dates

Step 3: Update get_patient_start_date()
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Add parsing logic for your new date field:

.. code-block:: python

    def get_patient_start_date(patient, start_date_reference):
        """Retrieve the actual date value for a given reference key."""
        
        if not start_date_reference:
            return patient.date_of_registration
        
        # Registration date
        if start_date_reference == 'date_of_registration':
            return patient.date_of_registration
        
        # Diagnosis date
        if start_date_reference.startswith('date_of_diagnosis_'):
            diagnosis_id = start_date_reference.replace('date_of_diagnosis_', '')
            try:
                diagnosis = patient.diagnosis_set.get(id=diagnosis_id)
                return diagnosis.date_of_diagnosis
            except Diagnosis.DoesNotExist:
                return patient.date_of_registration
        
        # Treatment start date
        if start_date_reference.startswith('date_of_start_of_treatment_'):
            treatment_id = start_date_reference.replace('date_of_start_of_treatment_', '')
            try:
                treatment = Treatment.objects.get(id=treatment_id)
                return treatment.date_of_start_of_treatment
            except Treatment.DoesNotExist:
                return patient.date_of_registration
        
        # NEW: Follow-up date
        if start_date_reference.startswith('date_of_follow_up_'):
            treatment_id = start_date_reference.replace('date_of_follow_up_', '')
            try:
                treatment = Treatment.objects.get(id=treatment_id)
                return treatment.date_of_follow_up
            except Treatment.DoesNotExist:
                return patient.date_of_registration
        
        # Default fallback
        return patient.date_of_registration

Step 4: Update Forms
~~~~~~~~~~~~~~~~~~~~~

If your new date field should be editable, add it to the relevant forms:

.. code-block:: python

    # In patientapp/forms.py
    class TreatmentForm(forms.ModelForm):
        class Meta:
            model = Treatment
            fields = [
                'treatment_type',
                'date_of_start_of_treatment',
                'date_of_follow_up',  # NEW
                # ... other fields
            ]

Step 5: Update Templates
~~~~~~~~~~~~~~~~~~~~~~~~

Add the new field to display templates:

.. code-block:: html

    <!-- In templates/patientapp/treatment_detail.html -->
    <c-field_display 
        label="Start Date" 
        value="{{ treatment.date_of_start_of_treatment }}" />
    
    <!-- NEW -->
    <c-field_display 
        label="Follow-up Date" 
        value="{{ treatment.date_of_follow_up }}" />

Adding New Models with Dates
-----------------------------

If you're adding a completely new model with date fields:

Step 1: Create the Model
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    # In patientapp/models.py
    class Procedure(models.Model):
        """New model for tracking medical procedures."""
        patient = models.ForeignKey(
            Patient,
            on_delete=models.CASCADE,
            related_name='procedures'
        )
        procedure_type = models.CharField(max_length=255)
        date_of_procedure = models.DateField(
            null=True,
            blank=True,
            verbose_name="Date of Procedure"
        )
        
        class Meta:
            ordering = ['-date_of_procedure']
        
        def __str__(self):
            return f"{self.procedure_type} - {self.date_of_procedure}"

Step 2: Integrate into Date Reference System
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    def get_patient_available_start_dates(patient):
        """Get all available start dates for a patient."""
        available_dates = []
        
        # ... existing code ...
        
        # NEW: Add procedure dates
        for procedure in patient.procedures.filter(date_of_procedure__isnull=False):
            available_dates.append((
                f'date_of_procedure_{procedure.id}',
                f'Procedure: {procedure.procedure_type}',
                procedure.date_of_procedure
            ))
        
        available_dates.sort(key=lambda x: x[2])
        return available_dates

.. code-block:: python

    def get_patient_start_date(patient, start_date_reference):
        """Retrieve the actual date value for a given reference key."""
        
        # ... existing code ...
        
        # NEW: Procedure date
        if start_date_reference.startswith('date_of_procedure_'):
            procedure_id = start_date_reference.replace('date_of_procedure_', '')
            try:
                procedure = patient.procedures.get(id=procedure_id)
                return procedure.date_of_procedure
            except Procedure.DoesNotExist:
                return patient.date_of_registration
        
        return patient.date_of_registration

Time Interval Calculations
---------------------------

How Time Intervals Work
~~~~~~~~~~~~~~~~~~~~~~~

The system calculates time intervals between:

1. **Start Date**: Selected reference date (e.g., diagnosis date)
2. **Submission Date**: When questionnaire was completed

**Example:**

.. code-block:: python

    from datetime import datetime, timedelta
    
    start_date = datetime(2024, 1, 15).date()  # Diagnosis date
    submission_date = datetime(2024, 4, 15).date()  # Questionnaire date
    
    # Calculate weeks
    days_diff = (submission_date - start_date).days
    weeks = days_diff / 7
    # Result: 13 weeks

Using Time Intervals in Views
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from patientapp.utils import get_patient_start_date
    
    def prom_review(request, pk):
        patient = get_object_or_404(Patient, pk=pk)
        
        # Get selected start date reference
        start_date_ref = request.GET.get('start_date_reference', 'date_of_registration')
        start_date = get_patient_start_date(patient, start_date_ref)
        
        # Filter submissions by time interval
        max_weeks = int(request.GET.get('max_time_interval', 52))
        cutoff_date = start_date + timedelta(weeks=max_weeks)
        
        submissions = QuestionnaireSubmission.objects.filter(
            patient_questionnaire__patient=patient,
            submission_date__gte=start_date,
            submission_date__lte=cutoff_date
        )

Data Import/Export
------------------

CSV Import for Items
~~~~~~~~~~~~~~~~~~~~

SATHI supports bulk import of questionnaire items with translations.

**CSV Format:**

.. code-block:: text

    id,construct_scale,item_number,response_type,language_code,name,likert_response,range_response,is_required,item_missing_value,item_better_score_direction,item_threshold_score,item_minimum_clinical_important_difference,item_normative_score_mean,item_normative_score_standard_deviation,discrimination_parameter,difficulty_parameter,pseudo_guessing_parameter
    550e8400-e29b-41d4-a716-446655440000,123e4567-e89b-12d3-a456-426614174000,1,Likert,en,"How are you feeling?",789e4567-e89b-12d3-a456-426614174000,,true,0,"Higher is Better",5,2,10,2,1.5,0.5,0.1

**Import Process:**

.. code-block:: python

    from django.core.management import call_command
    
    # Import items from CSV
    call_command('import_items', 'path/to/items.csv')

**Field Descriptions:**

- ``id``: UUID for the item
- ``construct_scale``: UUID of the construct scale
- ``item_number``: Order in questionnaire
- ``response_type``: Likert, Range, Number, or Text
- ``language_code``: Language for this translation
- ``name``: Question text
- ``likert_response``: UUID of Likert scale (if applicable)
- ``range_response``: UUID of Range scale (if applicable)

CSV Export for Responses
~~~~~~~~~~~~~~~~~~~~~~~~~

Export patient questionnaire responses:

.. code-block:: python

    from promapp.views import export_questionnaire_responses
    
    # Export all responses for a questionnaire
    response = export_questionnaire_responses(
        request,
        questionnaire_id=questionnaire.id
    )
    # Returns CSV file download

**Export Includes:**

- Patient ID (encrypted)
- Institution name
- Submission date and time
- All item responses
- Response values for each question type

Best Practices
--------------

Date Field Naming
~~~~~~~~~~~~~~~~~

**DO:**

- Use descriptive names: ``date_of_diagnosis``, ``date_of_follow_up``
- Include ``date_of_`` prefix for consistency
- Use snake_case naming convention

**DON'T:**

- Use ambiguous names: ``date``, ``when``
- Mix naming conventions
- Omit the ``date_of_`` prefix

Data Validation
~~~~~~~~~~~~~~~

**Always validate dates:**

.. code-block:: python

    from django.core.exceptions import ValidationError
    from datetime import date
    
    def clean_date_of_follow_up(self):
        follow_up_date = self.cleaned_data.get('date_of_follow_up')
        start_date = self.cleaned_data.get('date_of_start_of_treatment')
        
        if follow_up_date and start_date:
            if follow_up_date < start_date:
                raise ValidationError(
                    "Follow-up date cannot be before treatment start date"
                )
        
        if follow_up_date and follow_up_date > date.today():
            raise ValidationError(
                "Follow-up date cannot be in the future"
            )
        
        return follow_up_date

Error Handling
~~~~~~~~~~~~~~

**Graceful fallbacks:**

.. code-block:: python

    def get_patient_start_date(patient, start_date_reference):
        """Always return a valid date, even if reference is invalid."""
        try:
            # Attempt to parse reference
            if start_date_reference.startswith('date_of_diagnosis_'):
                diagnosis_id = start_date_reference.replace('date_of_diagnosis_', '')
                diagnosis = patient.diagnosis_set.get(id=diagnosis_id)
                return diagnosis.date_of_diagnosis
        except (Diagnosis.DoesNotExist, ValueError) as e:
            logger.warning(f"Invalid date reference: {start_date_reference}, {e}")
        
        # Always fall back to registration date
        return patient.date_of_registration or date.today()

Testing
-------

Test Date Reference System
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from django.test import TestCase
    from patientapp.models import Patient, Diagnosis, Treatment
    from patientapp.utils import get_patient_available_start_dates, get_patient_start_date
    
    class DateReferenceTestCase(TestCase):
        def setUp(self):
            self.patient = Patient.objects.create(
                name="Test Patient",
                date_of_registration=date(2024, 1, 1)
            )
            
            self.diagnosis = Diagnosis.objects.create(
                patient=self.patient,
                date_of_diagnosis=date(2024, 2, 1)
            )
            
            self.treatment = Treatment.objects.create(
                diagnosis=self.diagnosis,
                date_of_start_of_treatment=date(2024, 3, 1)
            )
        
        def test_available_dates_includes_all_types(self):
            """Test that all date types are included."""
            dates = get_patient_available_start_dates(self.patient)
            
            # Should have registration, diagnosis, and treatment dates
            self.assertEqual(len(dates), 3)
            
            # Check reference keys
            keys = [d[0] for d in dates]
            self.assertIn('date_of_registration', keys)
            self.assertIn(f'date_of_diagnosis_{self.diagnosis.id}', keys)
            self.assertIn(f'date_of_start_of_treatment_{self.treatment.id}', keys)
        
        def test_get_start_date_returns_correct_date(self):
            """Test that correct date is returned for each reference."""
            # Registration date
            date_val = get_patient_start_date(self.patient, 'date_of_registration')
            self.assertEqual(date_val, date(2024, 1, 1))
            
            # Diagnosis date
            date_val = get_patient_start_date(
                self.patient, 
                f'date_of_diagnosis_{self.diagnosis.id}'
            )
            self.assertEqual(date_val, date(2024, 2, 1))
            
            # Treatment date
            date_val = get_patient_start_date(
                self.patient,
                f'date_of_start_of_treatment_{self.treatment.id}'
            )
            self.assertEqual(date_val, date(2024, 3, 1))
        
        def test_invalid_reference_returns_fallback(self):
            """Test that invalid references fall back to registration date."""
            date_val = get_patient_start_date(self.patient, 'invalid_reference')
            self.assertEqual(date_val, self.patient.date_of_registration)

Troubleshooting
---------------

Common Issues
~~~~~~~~~~~~~

**Date Not Appearing in Dropdown:**

1. Check date field is not null in database
2. Verify ``get_patient_available_start_dates()`` includes the field
3. Check filter query in the function
4. Ensure date is properly formatted

**Wrong Date Being Used:**

1. Verify reference key format matches pattern
2. Check ``get_patient_start_date()`` parsing logic
3. Ensure model relationships are correct
4. Check for typos in reference key

**Time Interval Calculations Incorrect:**

1. Verify start date is correct
2. Check submission dates are valid
3. Ensure timezone handling is consistent
4. Validate date arithmetic logic

Resources
---------

- `Django Model Fields <https://docs.djangoproject.com/en/stable/ref/models/fields/>`_
- `Python datetime <https://docs.python.org/3/library/datetime.html>`_
- `Django Migrations <https://docs.djangoproject.com/en/stable/topics/migrations/>`_
- `Django CSV Import/Export <https://django-import-export.readthedocs.io/>`_
