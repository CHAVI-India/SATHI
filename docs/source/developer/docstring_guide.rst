Writing Documentation
=====================

This guide explains how to write effective docstrings for SATHI's codebase. All docstrings are automatically extracted and included in the API reference documentation.

Docstring Style
---------------

SATHI uses **Google-style docstrings**, which are readable both in code and when rendered by Sphinx.

Basic Structure
~~~~~~~~~~~~~~~

.. code-block:: python

    def function_name(param1, param2):
        """Short one-line summary.

        Longer description that provides more context about what the
        function does, when to use it, and any important considerations.

        Args:
            param1 (type): Description of param1.
            param2 (type): Description of param2.

        Returns:
            type: Description of return value.

        Raises:
            ExceptionType: When and why this exception is raised.

        Examples:
            >>> function_name('value1', 'value2')
            'result'
        """
        pass

Documenting Views
-----------------

Django views should include information about:

- Purpose of the view
- Required permissions
- URL parameters
- Query parameters
- Context variables passed to templates
- Return type (rendered template, redirect, JSON response)

Function-Based Views
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    @login_required
    @permission_required('patientapp.view_patient', raise_exception=True)
    def prom_review(request, pk):
        """Display PRO Review page for a patient's questionnaire responses.

        This view provides a comprehensive dashboard for reviewing patient-reported
        outcomes over time, with filtering and population comparison capabilities.

        Args:
            request (HttpRequest): The HTTP request object.
            pk (int): Primary key of the patient.

        Query Parameters:
            questionnaire_filter (str, optional): Filter by questionnaire ID.
            time_range (str, optional): Number of submissions to display (default: '5').
            max_time_interval (float, optional): Maximum time from start date.
            time_interval (str, optional): Time unit ('days', 'weeks', 'months', 'years').
            aggregation_type (str, optional): Type of aggregation ('median_iqr', 'mean_ci', etc.).
            patient_filter_gender (str, optional): Gender filter for population comparison.
            patient_filter_diagnosis (str, optional): Diagnosis filter for comparison.
            patient_filter_treatment (str, optional): Treatment filter for comparison.

        Returns:
            HttpResponse: Rendered prom_review.html template with context containing:
                - patient: Patient object
                - assigned_questionnaires: QuerySet of PatientQuestionnaire objects
                - submissions: QuerySet of QuestionnaireSubmission objects
                - aggregated_patients: QuerySet for population comparison
                - Various filter parameters

        Raises:
            Http404: If patient not found or user lacks access.
            PermissionDenied: If user lacks view_patient permission.

        Examples:
            Access via URL: /patients/123/prom-review/
            With filters: /patients/123/prom-review/?time_range=10&questionnaire_filter=5
        """
        pass

Class-Based Views
~~~~~~~~~~~~~~~~~

.. code-block:: python

    class PatientListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
        """Display paginated list of patients with filtering capabilities.

        This view provides a searchable, filterable list of patients accessible
        to the current user based on their institution permissions.

        Attributes:
            model (Model): Patient model.
            template_name (str): Template path.
            context_object_name (str): Name for patient list in context.
            paginate_by (int): Number of patients per page.
            permission_required (str): Required permission string.

        Query Parameters:
            patient_select (str, optional): UUID of selected patient.
            institution (str, optional): Filter by institution ID.
            gender (str, optional): Filter by gender.
            diagnosis (str, optional): Filter by diagnosis ID.

        Context Variables:
            patients: Paginated QuerySet of Patient objects.
            institutions: QuerySet of Institution objects for filter dropdown.
            diagnoses: QuerySet of Diagnosis objects for filter dropdown.

        Examples:
            Access via URL: /patients/
            With filters: /patients/?gender=M&institution=5
        """
        pass

Documenting Models
------------------

Django models should document:

- Purpose of the model
- Key relationships
- Important fields
- Custom methods
- Validation rules

.. code-block:: python

    class Patient(models.Model):
        """Represents a patient in the SATHI system.

        Patients are the primary subjects of PROM data collection. Each patient
        belongs to an institution and can have multiple diagnoses, treatments,
        and questionnaire submissions.

        Attributes:
            name (EncryptedCharField): Patient's full name (encrypted).
            patient_id (EncryptedCharField): Unique patient identifier (encrypted).
            date_of_birth (EncryptedDateField): Patient's date of birth (encrypted).
            gender (str): Patient's gender (M/F/O).
            institution (ForeignKey): Institution this patient belongs to.
            diagnoses (ManyToManyField): Patient's diagnoses through PatientDiagnosis.
            treatments (ManyToManyField): Patient's treatments through PatientTreatment.

        Methods:
            get_age(): Calculate patient's current age.
            get_latest_submission(): Get most recent questionnaire submission.
            has_active_questionnaires(): Check if patient has assigned questionnaires.

        Examples:
            >>> patient = Patient.objects.get(pk=1)
            >>> patient.get_age()
            45
            >>> patient.diagnoses.count()
            2
        """

        name = EncryptedCharField(max_length=255)
        patient_id = EncryptedCharField(max_length=100, unique=True)
        
        def get_age(self):
            """Calculate patient's current age in years.

            Returns:
                int: Patient's age in complete years.

            Examples:
                >>> patient.date_of_birth = date(1980, 1, 1)
                >>> patient.get_age()
                44
            """
            pass

Documenting Forms
-----------------

Django forms should document:

- Purpose of the form
- Fields and their validation
- Custom clean methods
- Save behavior

.. code-block:: python

    class PatientForm(forms.ModelForm):
        """Form for creating and updating patient records.

        This form handles patient demographic information with proper validation
        for encrypted fields and institution assignment.

        Fields:
            name: Patient's full name (required).
            patient_id: Unique identifier (required, validated for uniqueness).
            date_of_birth: Patient's DOB (required, must be in past).
            gender: Patient's gender (required, choices: M/F/O).
            institution: Institution assignment (required).

        Meta:
            model (Model): Patient model.
            fields (list): List of included fields.

        Methods:
            clean_patient_id(): Validate patient ID uniqueness.
            clean_date_of_birth(): Ensure DOB is not in future.

        Examples:
            >>> form = PatientForm(data={'name': 'John Doe', ...})
            >>> if form.is_valid():
            ...     patient = form.save()
        """

        class Meta:
            model = Patient
            fields = ['name', 'patient_id', 'date_of_birth', 'gender', 'institution']

        def clean_patient_id(self):
            """Validate patient ID is unique within institution.

            Returns:
                str: Validated patient ID.

            Raises:
                ValidationError: If patient ID already exists in institution.
            """
            pass

Documenting Utilities
---------------------

Utility functions should document:

- Purpose and use cases
- Parameters and types
- Return values
- Side effects
- Performance considerations

.. code-block:: python

    def calculate_construct_score(item_responses, equation, min_items=None):
        """Calculate construct score from item responses using equation.

        This function evaluates a mathematical equation using item responses
        as variables (Q1, Q2, etc.) and returns the calculated score.

        Args:
            item_responses (dict): Mapping of item numbers to response values.
                Example: {1: 3, 2: 4, 3: 2}
            equation (str): Mathematical equation using Q1, Q2, etc.
                Example: "(Q1 + Q2 + Q3) / 3"
            min_items (int, optional): Minimum items required for valid score.
                If fewer items answered, returns None.

        Returns:
            float or None: Calculated score, or None if insufficient items.

        Raises:
            ValueError: If equation is invalid or contains undefined variables.
            ZeroDivisionError: If equation results in division by zero.

        Notes:
            - Equation is evaluated in a restricted namespace for security
            - Only mathematical operators and functions are allowed
            - Missing item responses are treated as None

        Examples:
            >>> responses = {1: 3, 2: 4, 3: 5}
            >>> calculate_construct_score(responses, "(Q1 + Q2 + Q3) / 3")
            4.0

            >>> responses = {1: 3, 2: 4}  # Missing Q3
            >>> calculate_construct_score(responses, "(Q1 + Q2 + Q3) / 3", min_items=3)
            None

        Performance:
            O(n) where n is the number of items in the equation.
        """
        pass

Documenting Classes
-------------------

Utility classes should document:

- Purpose and responsibilities
- Initialization parameters
- Public methods
- Usage examples

.. code-block:: python

    class ConstructScoreData:
        """Container for construct score data with plot generation.

        This class encapsulates all data related to a construct score including
        historical values, population comparisons, and plot generation.

        Args:
            construct (ConstructScale): The construct scale being measured.
            patient (Patient): Patient whose scores are being analyzed.
            submissions (QuerySet): QuestionnaireSubmission objects to analyze.
            generate_plot (bool, optional): Whether to generate plot. Default True.
            aggregated_patients (QuerySet, optional): Patients for comparison.
            aggregation_type (str, optional): Type of aggregation for comparison.

        Attributes:
            construct (ConstructScale): The construct scale.
            current_score (float): Most recent score value.
            previous_score (float): Previous score for comparison.
            change_direction (str): Direction of change ('up', 'down', 'same').
            is_beneficial (bool): Whether change is clinically beneficial.
            plot_html (str): HTML for the plot, if generated.

        Methods:
            calculate_scores(): Calculate current and historical scores.
            generate_plot(): Create plotly visualization.
            get_change_indicator(): Get HTML for change indicator icon.

        Examples:
            >>> construct_data = ConstructScoreData(
            ...     construct=construct,
            ...     patient=patient,
            ...     submissions=submissions
            ... )
            >>> construct_data.current_score
            75.5
            >>> construct_data.change_direction
            'up'
        """

        def __init__(self, construct, patient, submissions, generate_plot=True):
            """Initialize construct score data container.

            Args:
                construct (ConstructScale): The construct scale.
                patient (Patient): Patient whose scores are analyzed.
                submissions (QuerySet): QuestionnaireSubmission objects.
                generate_plot (bool, optional): Generate plot. Default True.
            """
            pass

Special Sections
----------------

Notes
~~~~~

Use for important information:

.. code-block:: python

    """
    Notes:
        - This function modifies the database
        - Results are cached for 5 minutes
        - Not thread-safe for concurrent modifications
    """

Warnings
~~~~~~~~

Use for critical information:

.. code-block:: python

    """
    Warning:
        This function performs expensive database queries.
        Use sparingly and consider caching results.
    """

See Also
~~~~~~~~

Use to reference related functions:

.. code-block:: python

    """
    See Also:
        calculate_construct_score: For individual construct scoring
        get_aggregated_scores: For population-level aggregation
    """

Best Practices
--------------

**DO:**

- Write docstrings for all public functions, classes, and methods
- Use clear, concise language
- Include examples for complex functionality
- Document all parameters and return values
- Explain the "why" not just the "what"
- Keep docstrings up-to-date when code changes

**DON'T:**

- Write docstrings for obvious/trivial functions
- Repeat the function name in the description
- Include implementation details that may change
- Use vague descriptions like "does stuff"
- Forget to document exceptions
- Leave outdated docstrings

Type Hints
----------

Combine docstrings with type hints for maximum clarity:

.. code-block:: python

    from typing import Optional, List, Dict

    def get_patient_scores(
        patient_id: int,
        construct_ids: Optional[List[int]] = None
    ) -> Dict[int, float]:
        """Get construct scores for a patient.

        Args:
            patient_id: Primary key of the patient.
            construct_ids: List of construct IDs to retrieve.
                If None, retrieves all constructs.

        Returns:
            Dictionary mapping construct IDs to their scores.
        """
        pass

Checking Documentation
----------------------

To verify your docstrings are properly formatted:

1. **Build the documentation:**

   .. code-block:: bash

      cd docs
      make html

2. **Check for warnings:**

   Look for warnings about missing docstrings or formatting issues.

3. **View the output:**

   Open ``docs/build/html/developer/api_reference.html`` in a browser.

4. **Validate examples:**

   Ensure code examples in docstrings are correct and run without errors.

Tools
-----

**Linting Docstrings:**

.. code-block:: bash

    # Install pydocstyle
    pip install pydocstyle

    # Check docstrings
    pydocstyle patientapp/views.py

**Auto-generating Docstring Templates:**

Many IDEs can generate docstring templates:

- **PyCharm**: Type ``"""`` and press Enter
- **VS Code**: Use autoDocstring extension
- **Vim**: Use vim-pydocstring plugin

References
----------

- `Google Python Style Guide <https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings>`_
- `Sphinx Napoleon Extension <https://www.sphinx-doc.org/en/master/usage/extensions/napoleon.html>`_
- `Django Documentation Best Practices <https://docs.djangoproject.com/en/stable/internals/contributing/writing-documentation/>`_
