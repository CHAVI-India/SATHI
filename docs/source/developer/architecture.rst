Architecture
============

This document provides a comprehensive overview of SATHI's system architecture, data models, and design patterns.

.. contents:: Table of Contents
   :local:
   :depth: 3

System Overview
---------------

SATHI (Self-reported Assessment and Tracking for Health Insights) is a Django-based web application designed to collect, manage, and analyze Patient-Reported Outcome Measures (PROMs). The system follows a modular architecture with clear separation of concerns across multiple Django apps.

**Core Capabilities:**

- Multi-institutional patient management with encrypted PHI
- Flexible PROM questionnaire creation and administration
- Real-time construct score calculation with clinical significance detection
- Population-level aggregation and comparison analytics
- Multi-language support with translatable content
- Role-based access control (RBAC) with institution-level data isolation

**Architecture Principles:**

1. **Security First**: All PHI encrypted at rest, institution-based data isolation
2. **Modularity**: Separate apps for distinct functional domains
3. **Extensibility**: Pluggable AI services, customizable scoring equations
4. **Performance**: Lazy loading, database indexing, query optimization
5. **Internationalization**: Multi-language support via django-parler

Django Apps Structure
---------------------

SATHI is organized into four primary Django applications, each with specific responsibilities:

patientapp
~~~~~~~~~~

**Purpose**: Patient and clinical data management

**Responsibilities:**

- Patient demographic information (encrypted)
- Institution management and access control
- Diagnosis and treatment tracking
- Clinical timeline management

**Key Models**: ``Patient``, ``Institution``, ``Diagnosis``, ``Treatment``

promapp
~~~~~~~

**Purpose**: PROM questionnaire and scoring engine

**Responsibilities:**

- Questionnaire structure and item management
- Response scale definitions (Likert, Range)
- Construct score calculation
- Composite scoring
- Multi-language translations
- AI-augmented services (TTS, STT)

**Key Models**: ``Questionnaire``, ``Item``, ``ConstructScale``, ``QuestionnaireSubmission``

providerapp
~~~~~~~~~~~

**Purpose**: Healthcare provider management

**Responsibilities:**

- Provider account management
- Provider type classification
- Institution assignment
- Account expiry tracking

**Key Models**: ``Provider``, ``ProviderType``

chaviprom
~~~~~~~~~

**Purpose**: Core project configuration and cross-cutting concerns

**Responsibilities:**

- Django settings and configuration
- URL routing
- Authentication and security middleware
- Context processors
- Signal handlers

Technology Stack
----------------

**Backend Framework:**

- **Django 5.x**: Web framework
- **Python 3.13**: Programming language
- **PostgreSQL**: Primary database (supports encrypted fields)

**Security & Authentication:**

- **django-two-factor-auth**: 2FA implementation
- **django-ratelimit**: Rate limiting for security
- **django-recaptcha**: Bot protection
- **secured-fields**: Field-level encryption for PHI

**Frontend:**

- **HTMX**: Dynamic content loading without JavaScript frameworks
- **TailwindCSS**: Utility-first CSS framework
- **django-cotton**: Component-based templating
- **Plotly/Bokeh**: Interactive data visualization

**Internationalization:**

- **django-parler**: Multi-language model translations
- **gettext**: String translations

**Performance:**

- **Memcached**: Caching layer (production)
- **Gunicorn**: WSGI HTTP server
- **WhiteNoise**: Static file serving

**Development Tools:**

- **Sphinx**: Documentation generation
- **django-debug-toolbar**: Development debugging

Data Model Architecture
-----------------------

The data model is organized into three primary domains: **Clinical Data**, **PROM Structure**, and **PROM Responses**.

Clinical Data Domain
~~~~~~~~~~~~~~~~~~~~

Institution
^^^^^^^^^^^

**Purpose**: Multi-tenancy and data isolation

.. code-block:: python

    class Institution(models.Model):
        id = UUIDField(primary_key=True)
        name = CharField(max_length=255)
        created_date = DateTimeField(auto_now_add=True)
        modified_date = DateTimeField(auto_now=True)

**Relationships:**

- One-to-Many with ``Patient``
- One-to-Many with ``Provider``

**Security**: All patient and provider data is filtered by institution to ensure data isolation.

Patient
^^^^^^^

**Purpose**: Store patient demographic and clinical information

.. code-block:: python

    class Patient(models.Model):
        id = UUIDField(primary_key=True)
        institution = ForeignKey(Institution)
        user = OneToOneField(User)  # Django auth user
        name = EncryptedCharField(max_length=255, searchable=True)
        patient_id = EncryptedCharField(max_length=255, searchable=True)
        date_of_registration = EncryptedDateField(searchable=True)
        age = PositiveIntegerField(db_index=True)
        gender = CharField(choices=GenderChoices, db_index=True)
        preferred_language = CharField(choices=LANGUAGES)

**Encryption**: Name, patient_id, and dates are encrypted using ``secured_fields``

**Indexes**: Composite indexes on ``(institution, gender)``, ``(institution, age)`` for filtering

**Relationships:**

- Belongs to ``Institution``
- Linked to Django ``User`` (1:1)
- Has many ``Diagnosis`` (1:N)
- Has many ``PatientQuestionnaire`` (1:N)

Diagnosis
^^^^^^^^^

**Purpose**: Track patient diagnoses with ICD-11 coding

.. code-block:: python

    class Diagnosis(models.Model):
        id = UUIDField(primary_key=True)
        patient = ForeignKey(Patient)
        diagnosis = ForeignKey(DiagnosisList)
        date_of_diagnosis = EncryptedDateField(searchable=True)

**Relationships:**

- Belongs to ``Patient``
- References ``DiagnosisList`` (standardized diagnosis catalog)
- Has many ``Treatment`` (1:N)

Treatment
^^^^^^^^^

**Purpose**: Track treatment episodes with dates and intent

.. code-block:: python

    class Treatment(models.Model):
        id = UUIDField(primary_key=True)
        diagnosis = ForeignKey(Diagnosis)
        treatment_type = ManyToManyField(TreatmentType)
        treatment_intent = CharField(choices=TreatmentIntentChoices)
        date_of_start_of_treatment = EncryptedDateField()
        currently_ongoing_treatment = BooleanField(default=False)
        date_of_end_of_treatment = EncryptedDateField()

**Validation**: Custom ``clean()`` method ensures:

- Start date not in future
- End date not before start date
- Ongoing treatments have no end date
- Completed treatments have end date

**Relationships:**

- Belongs to ``Diagnosis``
- Has many ``TreatmentType`` (M:N)

PROM Structure Domain
~~~~~~~~~~~~~~~~~~~~~

ConstructScale
^^^^^^^^^^^^^^

**Purpose**: Define latent trait measurement with scoring equation

.. code-block:: python

    class ConstructScale(models.Model):
        id = UUIDField(primary_key=True)
        name = CharField(max_length=255)  # e.g., "Physical Function"
        instrument_name = CharField()  # e.g., "EORTC QLQ-C30"
        instrument_version = CharField()
        scale_equation = CharField(max_length=1025)  # e.g., "{q1} + {q2} + {q3}"
        minimum_number_of_items = IntegerField()
        scale_better_score_direction = CharField(choices=DirectionChoices)
        scale_threshold_score = DecimalField()
        scale_minimum_clinical_important_difference = DecimalField()
        scale_normative_score_mean = DecimalField()
        scale_normative_score_standard_deviation = DecimalField()

**Equation Validation**: Uses Lark parser to validate mathematical equations

**Clinical Parameters:**

- **Threshold Score**: Clinical significance cutoff
- **MCID**: Minimum clinically important difference
- **Normative Score**: Population reference values (mean ± SD)

**Relationships:**

- Has many ``Item`` (M:N)
- Referenced by ``CompositeConstructScaleScoring``

Item
^^^^

**Purpose**: Individual questions in a questionnaire

.. code-block:: python

    class Item(TranslatableModel):
        id = UUIDField(primary_key=True)
        construct_scale = ManyToManyField(ConstructScale)
        translations = TranslatedFields(
            name = CharField(max_length=500),  # Question text
            media = FileField(upload_to='item_media/')  # Audio/video/image
        )
        abbreviated_item_id = CharField(unique=True)
        item_number = IntegerField()  # For equation references {q1}, {q2}
        response_type = CharField(choices=ResponseTypeChoices)
        likert_response = ForeignKey(LikertScale, null=True)
        range_response = ForeignKey(RangeScale, null=True)
        # Clinical parameters (optional, item-level)
        item_better_score_direction = CharField()
        item_threshold_score = DecimalField()
        item_minimum_clinical_important_difference = DecimalField()

**Translation**: Question text and media translatable via django-parler

**Response Types:**

- **Text**: Free-form text input
- **Number**: Numeric input
- **Likert**: Ordered categorical scale
- **Range**: Numeric slider (e.g., 0-10)
- **Media**: Audio/video recording by patient

**Validation**: Ensures response type matches selected scale (Likert or Range)

LikertScale & LikertScaleResponseOption
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Purpose**: Define ordered categorical response scales

.. code-block:: python

    class LikertScale(models.Model):
        id = UUIDField(primary_key=True)
        likert_scale_name = CharField()
    
    class LikertScaleResponseOption(TranslatableModel):
        id = UUIDField(primary_key=True)
        likert_scale = ForeignKey(LikertScale)
        option_order = IntegerField()
        translations = TranslatedFields(
            option_text = CharField(),  # e.g., "Not at all", "A little"
            option_media = FileField()
        )
        option_emoji = CharField()
        option_value = DecimalField()  # Numeric value for scoring

**Features:**

- Viridis color palette for visual representation
- Automatic text color selection based on background luminance
- Translatable option text and media

RangeScale
^^^^^^^^^^

**Purpose**: Define numeric slider scales

.. code-block:: python

    class RangeScale(TranslatableModel):
        id = UUIDField(primary_key=True)
        range_scale_name = CharField()
        max_value = DecimalField()
        min_value = DecimalField()
        increment = DecimalField()
        translations = TranslatedFields(
            min_value_text = CharField(),  # e.g., "No Pain"
            max_value_text = CharField()   # e.g., "Worst Pain"
        )

**Validation**: Ensures min < max and (max - min) divisible by increment

Questionnaire
^^^^^^^^^^^^^

**Purpose**: Collection of items presented to patients

.. code-block:: python

    class Questionnaire(TranslatableModel):
        id = UUIDField(primary_key=True)
        translations = TranslatedFields(
            name = CharField(),
            description = TextField()
        )
        questionnaire_order = IntegerField()
        questionnaire_answer_interval = DurationField()
        questionnaire_redirect = ForeignKey('self', null=True)

**Relationships:**

- Has many ``QuestionnaireItem`` (M:N through table with order)
- Can redirect to another ``Questionnaire`` after completion

QuestionnaireItem
^^^^^^^^^^^^^^^^^

**Purpose**: Junction table linking questionnaires to items with ordering

.. code-block:: python

    class QuestionnaireItem(models.Model):
        questionnaire = ForeignKey(Questionnaire)
        item = ForeignKey(Item)
        item_order = IntegerField()

**Features**: Allows same item to appear in multiple questionnaires with different ordering

PROM Response Domain
~~~~~~~~~~~~~~~~~~~~

PatientQuestionnaire
^^^^^^^^^^^^^^^^^^^^

**Purpose**: Assignment of questionnaire to patient

.. code-block:: python

    class PatientQuestionnaire(models.Model):
        id = UUIDField(primary_key=True)
        patient = ForeignKey(Patient)
        questionnaire = ForeignKey(Questionnaire)
        date_assigned = DateTimeField(auto_now_add=True)
        is_active = BooleanField(default=True)

**Relationships:**

- Links ``Patient`` to ``Questionnaire``
- Has many ``QuestionnaireSubmission`` (1:N)

QuestionnaireSubmission
^^^^^^^^^^^^^^^^^^^^^^^

**Purpose**: Single completion of a questionnaire by a patient

.. code-block:: python

    class QuestionnaireSubmission(models.Model):
        id = UUIDField(primary_key=True)
        patient_questionnaire = ForeignKey(PatientQuestionnaire)
        patient = ForeignKey(Patient, db_index=True)
        submission_date = DateTimeField(auto_now_add=True, db_index=True)
        is_complete = BooleanField(default=False)

**Indexes**: Composite index on ``(patient, submission_date)`` for timeline queries

**Relationships:**

- Belongs to ``PatientQuestionnaire``
- Has many ``QuestionnaireItemResponse`` (1:N)
- Has many ``QuestionnaireConstructScore`` (1:N)

QuestionnaireItemResponse
^^^^^^^^^^^^^^^^^^^^^^^^^

**Purpose**: Patient's answer to a single item

.. code-block:: python

    class QuestionnaireItemResponse(models.Model):
        id = UUIDField(primary_key=True)
        questionnaire_submission = ForeignKey(QuestionnaireSubmission)
        questionnaire_item = ForeignKey(QuestionnaireItem)
        response_text = TextField(null=True)
        response_number = DecimalField(null=True)
        response_likert = ForeignKey(LikertScaleResponseOption, null=True)
        response_range = DecimalField(null=True)
        response_media = FileField(null=True)
        response_date = DateTimeField(auto_now_add=True)

**Polymorphic Storage**: Different fields for different response types

QuestionnaireConstructScore
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Purpose**: Calculated construct score from item responses

.. code-block:: python

    class QuestionnaireConstructScore(models.Model):
        id = UUIDField(primary_key=True)
        questionnaire_submission = ForeignKey(QuestionnaireSubmission)
        construct = ForeignKey(ConstructScale)
        score = DecimalField()
        items_answered = IntegerField()
        total_items = IntegerField()
        calculation_date = DateTimeField(auto_now_add=True)

**Calculation**: Scores computed using construct's equation with item responses

**Indexes**: Optimized for time-series queries on ``(construct, questionnaire_submission__patient)``

Composite & Advanced Models
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

CompositeConstructScaleScoring
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Purpose**: Combine multiple construct scores into higher-level metrics

.. code-block:: python

    class CompositeConstructScaleScoring(models.Model):
        id = UUIDField(primary_key=True)
        composite_construct_scale_name = CharField()
        construct_scales = ManyToManyField(ConstructScale)
        scoring_type = CharField(choices=ScoringTypeChoices)
        # Average, Sum, Median, Mode, Min, Max

**Use Case**: Create summary scores like FACT TOI (Trial Outcome Index)

AIAPIConfiguration
^^^^^^^^^^^^^^^^^^

**Purpose**: Configure AI-augmented services (TTS, STT, etc.)

.. code-block:: python

    class AIAPIConfiguration(models.Model):
        ai_provider = CharField()
        ai_capability = CharField(choices=AICapabilitiesChoices)
        utility_function_path = CharField()  # Python import path
        api_url = CharField()
        api_key_environment_variable_name = CharField()

**Capabilities**: Text-to-Speech, Speech-to-Text, Image/Video Generation

**Validation**: Ensures utility function exists and is callable, API key in environment

Data Flow Architecture
----------------------

Questionnaire Creation Flow
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. **Define Construct Scale** → Set name, equation, clinical parameters
2. **Create Response Scales** → Define Likert or Range scales (if needed)
3. **Create Items** → Write questions, assign response types and scales
4. **Build Questionnaire** → Select items, set order, configure redirects
5. **Assign to Patients** → Create ``PatientQuestionnaire`` records

Patient Response Flow
~~~~~~~~~~~~~~~~~~~~~

1. **Patient Login** → 2FA authentication
2. **View Assigned Questionnaires** → Filtered by ``PatientQuestionnaire.is_active``
3. **Answer Questions** → Create ``QuestionnaireItemResponse`` records
4. **Submit Questionnaire** → Mark ``QuestionnaireSubmission.is_complete = True``
5. **Calculate Scores** → Generate ``QuestionnaireConstructScore`` records
6. **Trigger Signals** → Cache invalidation, audit logging

Score Calculation Flow
~~~~~~~~~~~~~~~~~~~~~~

1. **Fetch Item Responses** → Get all responses for submission
2. **Group by Construct** → Organize responses by construct scale
3. **Validate Minimum Items** → Check ``minimum_number_of_items`` met
4. **Parse Equation** → Use Lark parser to build AST
5. **Transform & Evaluate** → Substitute item values, compute result
6. **Store Score** → Save to ``QuestionnaireConstructScore``
7. **Check Clinical Significance** → Compare to threshold, MCID, normative values

Aggregation & Analytics Flow
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. **Filter Patients** → Apply demographic filters (gender, diagnosis, treatment, age)
2. **Fetch Historical Scores** → Bulk query for all patients' construct scores
3. **Calculate Time Intervals** → Relative to start date (registration, diagnosis, treatment)
4. **Aggregate by Interval** → Compute median/mean with IQR/CI for each timepoint
5. **Generate Plots** → Create Bokeh/Plotly visualizations with population comparison
6. **Cache Results** → Store aggregated data in Memcached (1 hour TTL)

Security Architecture
---------------------

Data Encryption
~~~~~~~~~~~~~~~

**Field-Level Encryption** (via ``secured_fields``):

- Patient name, patient_id
- All clinical dates (diagnosis, treatment, registration)
- Searchable encryption allows filtering without decryption

**Encryption Keys**: Stored in environment variables, never in code

Institution-Based Isolation
~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Access Control Pattern**:

.. code-block:: python

    def get_accessible_patient_or_404(user, patient_pk):
        # Get user's institutions
        user_institutions = get_user_institutions(user)
        
        # Filter patient by institution
        patient = Patient.objects.filter(
            pk=patient_pk,
            institution__in=user_institutions
        ).first()
        
        if not patient:
            raise Http404
        return patient

**Enforcement**: All views use institution filtering, preventing cross-institution data access

Role-Based Access Control
~~~~~~~~~~~~~~~~~~~~~~~~~~

**Django Permissions**:

- ``patientapp.view_patient``
- ``patientapp.add_patient``
- ``promapp.view_questionnaire``
- ``promapp.add_constructscale``

**Permission Checks**: ``@permission_required`` decorators on all views

Authentication & 2FA
~~~~~~~~~~~~~~~~~~~~

**Multi-Factor Authentication**:

- TOTP (Time-based One-Time Password)
- Backup codes for account recovery
- Session binding to prevent token replay
- Rate limiting on login attempts

**Session Security**:

- CSRF protection
- Secure cookies (HTTPOnly, Secure, SameSite)
- IP and User-Agent binding

Performance Optimization
------------------------

Database Indexing
~~~~~~~~~~~~~~~~~

**Strategic Indexes**:

- Composite indexes on frequently filtered combinations
- Foreign key indexes on all relationships
- Date indexes for timeline queries

**Example**:

.. code-block:: python

    class Meta:
        indexes = [
            models.Index(fields=['institution', 'gender']),
            models.Index(fields=['patient', 'submission_date']),
        ]

Query Optimization
~~~~~~~~~~~~~~~~~~

**Techniques**:

- ``select_related()`` for forward foreign keys
- ``prefetch_related()`` for reverse foreign keys and M2M
- Bulk operations to reduce database round-trips
- Lazy evaluation with ``only()`` and ``defer()``

**Example**:

.. code-block:: python

    patients = Patient.objects.select_related(
        'institution'
    ).prefetch_related(
        'diagnosis_set__diagnosis',
        'diagnosis_set__treatment_set__treatment_type'
    )

Lazy Loading with HTMX
~~~~~~~~~~~~~~~~~~~~~~

**Plot Generation**:

- Main page loads without plots (1-2s)
- Plots loaded on-demand via HTMX ``hx-trigger="revealed"``
- 85% faster initial page load

**Benefits**:

- Progressive enhancement
- Reduced server load
- Better user experience

Caching Strategy
~~~~~~~~~~~~~~~~

**Cache Layers**:

1. **Patient-Specific Data** (5 min TTL)
   - Individual scores
   - Item responses
   
2. **Aggregation Data** (1 hour TTL)
   - Population statistics
   - Shared across patients with same filters
   
3. **Static Content** (Indefinite)
   - Questionnaire structure
   - Response scales

**Cache Invalidation**: Signals on ``QuestionnaireSubmission.post_save``

Extensibility Points
--------------------

Custom Scoring Equations
~~~~~~~~~~~~~~~~~~~~~~~~~

**Equation Parser**: Lark-based grammar supports:

- Basic arithmetic: ``+``, ``-``, ``*``, ``/``, ``^``
- Functions: ``sqrt()``, ``abs()``, ``min()``, ``max()``
- Item references: ``{q1}``, ``{q2}``, etc.
- Conditional logic (future enhancement)

**Example Equations**:

- EORTC: ``(1 - ({q1} + {q2}) / 8) * 100``
- Average: ``({q1} + {q2} + {q3}) / 3``
- Weighted: ``{q1} * 0.5 + {q2} * 0.3 + {q3} * 0.2``

Pluggable AI Services
~~~~~~~~~~~~~~~~~~~~~

**Architecture**: Function-based plugins via ``AIAPIConfiguration``

**Integration Pattern**:

1. Create utility function in ``promapp/ai_utils/``
2. Register in ``AIAPIConfiguration`` with import path
3. System dynamically loads and calls function

**Supported Services**:

- Text-to-Speech (TTS)
- Speech-to-Text (STT)
- Image/Video generation

Multi-Language Support
~~~~~~~~~~~~~~~~~~~~~~

**Translation Layers**:

1. **Model Translations** (django-parler)
   - Questionnaire names/descriptions
   - Item text and media
   - Response option text
   
2. **UI Translations** (gettext)
   - Interface strings
   - Help text
   - Error messages

**Language Selection**: Per-patient preference stored in ``Patient.preferred_language``

Design Patterns
---------------

Repository Pattern
~~~~~~~~~~~~~~~~~~

**Utility Functions**: Centralized data access in ``patientapp/utils.py`` and ``promapp/utils.py``

**Benefits**:

- Consistent query patterns
- Easier testing and mocking
- Performance optimization in one place

Signal-Based Architecture
~~~~~~~~~~~~~~~~~~~~~~~~~

**Django Signals**: Used for cross-cutting concerns

**Examples**:

- Cache invalidation on data changes
- Audit logging for security events
- User language preference updates

**Pattern**:

.. code-block:: python

    @receiver(post_save, sender=QuestionnaireSubmission)
    def invalidate_cache(sender, instance, **kwargs):
        cache_key = f"patient_{instance.patient_id}_scores"
        cache.delete(cache_key)

Component-Based Templates
~~~~~~~~~~~~~~~~~~~~~~~~~

**Django Cotton**: Reusable UI components

**Benefits**:

- Consistent UI across application
- Easier maintenance
- Reduced code duplication

**Example Components**:

- ``c-action_buttons``
- ``c-card``
- ``c-dropdown``

Future Enhancements
-------------------

**Planned Features**:

1. **Adaptive Testing** (CAT)
   - IRT-based item selection
   - Reduced patient burden
   
2. **Advanced Analytics**
   - Machine learning predictions
   - Trend analysis
   - Risk stratification
   
3. **Mobile App**
   - Native iOS/Android apps
   - Offline data collection
   - Push notifications
   
4. **API Layer**
   - RESTful API for external integrations
   - FHIR compliance
   - Webhook support

**Technical Debt**:

- Migrate to async views for better concurrency
- Implement GraphQL for flexible data queries
- Add comprehensive integration tests
- Enhance caching with Redis Cluster

Conclusion
----------

SATHI's architecture balances security, performance, and extensibility through:

- **Modular Design**: Clear separation of concerns across Django apps
- **Robust Data Model**: Comprehensive PROM structure with clinical parameters
- **Security-First**: Encryption, isolation, and RBAC at every layer
- **Performance**: Strategic indexing, caching, and lazy loading
- **Extensibility**: Pluggable AI services, custom equations, multi-language support

This architecture supports the core mission of collecting and analyzing patient-reported outcomes while maintaining the highest standards of data security and clinical utility.
