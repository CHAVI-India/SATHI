Testing Guide
=============

Comprehensive guide to testing SATHI application components, features, and integrations.

.. contents:: Table of Contents
   :local:
   :depth: 3

Overview
--------

SATHI uses multiple testing approaches:

- **Unit Tests**: Test individual functions and methods
- **Integration Tests**: Test component interactions
- **UI/UX Tests**: Test user interface and experience
- **Performance Tests**: Test load and response times
- **Security Tests**: Test authentication and authorization

Testing Stack
-------------

Tools & Frameworks
~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Tool
     - Purpose
   * - **pytest**
     - Test runner and framework
   * - **pytest-django**
     - Django-specific test utilities
   * - **factory_boy**
     - Test data generation
   * - **coverage.py**
     - Code coverage measurement
   * - **Selenium**
     - Browser automation for UI tests
   * - **Locust**
     - Load and performance testing

Installation
~~~~~~~~~~~~

.. code-block:: bash

    pip install pytest pytest-django pytest-cov
    pip install factory-boy faker
    pip install selenium webdriver-manager
    pip install locust

Configuration
~~~~~~~~~~~~~

**pytest.ini:**

.. code-block:: ini

    [pytest]
    DJANGO_SETTINGS_MODULE = chaviprom.settings
    python_files = tests.py test_*.py *_tests.py
    python_classes = Test*
    python_functions = test_*
    addopts = --reuse-db --nomigrations --cov=. --cov-report=html

**conftest.py:**

.. code-block:: python

    import pytest
    from django.contrib.auth.models import User, Group, Permission
    from patientapp.models import Patient, Institution
    
    @pytest.fixture
    def test_user(db):
        """Create a test user."""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        return user
    
    @pytest.fixture
    def test_institution(db):
        """Create a test institution."""
        return Institution.objects.create(
            name='Test Hospital',
            address='123 Test St'
        )
    
    @pytest.fixture
    def test_patient(db, test_institution):
        """Create a test patient."""
        return Patient.objects.create(
            name='Test Patient',
            patient_id='P001',
            institution=test_institution,
            date_of_registration='2024-01-01'
        )

Unit Testing
------------

Model Tests
~~~~~~~~~~~

**Test Patient Model:**

.. code-block:: python

    # patientapp/tests/test_models.py
    import pytest
    from datetime import date
    from patientapp.models import Patient, Institution
    
    @pytest.mark.django_db
    class TestPatientModel:
        
        def test_patient_creation(self, test_institution):
            """Test creating a patient."""
            patient = Patient.objects.create(
                name='John Doe',
                patient_id='P12345',
                institution=test_institution,
                date_of_registration=date(2024, 1, 1)
            )
            
            assert patient.name == 'John Doe'
            assert patient.patient_id == 'P12345'
            assert patient.institution == test_institution
        
        def test_patient_str(self, test_patient):
            """Test patient string representation."""
            assert str(test_patient) == 'Test Patient (P001)'
        
        def test_patient_age_calculation(self, test_patient):
            """Test age calculation."""
            test_patient.date_of_birth = date(1990, 1, 1)
            test_patient.save()
            
            # Age should be calculated correctly
            assert test_patient.age >= 34

View Tests
~~~~~~~~~~

**Test Patient List View:**

.. code-block:: python

    # patientapp/tests/test_views.py
    import pytest
    from django.urls import reverse
    from django.contrib.auth.models import Permission
    
    @pytest.mark.django_db
    class TestPatientListView:
        
        def test_patient_list_requires_login(self, client):
            """Test that patient list requires authentication."""
            url = reverse('patient_list')
            response = client.get(url)
            
            # Should redirect to login
            assert response.status_code == 302
            assert '/account/login/' in response.url
        
        def test_patient_list_requires_permission(self, client, test_user):
            """Test that patient list requires view permission."""
            client.force_login(test_user)
            url = reverse('patient_list')
            response = client.get(url)
            
            # Should return 403 without permission
            assert response.status_code == 403
        
        def test_patient_list_with_permission(self, client, test_user, test_patient):
            """Test patient list with proper permission."""
            # Add permission
            permission = Permission.objects.get(codename='view_patient')
            test_user.user_permissions.add(permission)
            
            client.force_login(test_user)
            url = reverse('patient_list')
            response = client.get(url)
            
            assert response.status_code == 200
            assert 'patients' in response.context

Form Tests
~~~~~~~~~~

**Test Patient Form:**

.. code-block:: python

    # patientapp/tests/test_forms.py
    import pytest
    from datetime import date
    from patientapp.forms import PatientForm
    
    @pytest.mark.django_db
    class TestPatientForm:
        
        def test_valid_patient_form(self, test_institution):
            """Test form with valid data."""
            form_data = {
                'name': 'Jane Doe',
                'patient_id': 'P67890',
                'institution': test_institution.id,
                'date_of_registration': date(2024, 1, 15),
                'gender': 'F',
            }
            
            form = PatientForm(data=form_data)
            assert form.is_valid()
        
        def test_invalid_patient_form_missing_required(self):
            """Test form with missing required fields."""
            form_data = {
                'name': 'Jane Doe',
                # Missing patient_id
            }
            
            form = PatientForm(data=form_data)
            assert not form.is_valid()
            assert 'patient_id' in form.errors

Utility Function Tests
~~~~~~~~~~~~~~~~~~~~~~

**Test Date Reference Functions:**

.. code-block:: python

    # patientapp/tests/test_utils.py
    import pytest
    from datetime import date
    from patientapp.utils import (
        get_patient_available_start_dates,
        get_patient_start_date
    )
    from patientapp.models import Diagnosis, Treatment
    
    @pytest.mark.django_db
    class TestDateReferenceFunctions:
        
        def test_get_available_start_dates(self, test_patient):
            """Test getting all available start dates."""
            dates = get_patient_available_start_dates(test_patient)
            
            # Should include registration date
            assert len(dates) >= 1
            assert dates[0][0] == 'date_of_registration'
        
        def test_get_start_date_registration(self, test_patient):
            """Test getting registration date."""
            start_date = get_patient_start_date(
                test_patient,
                'date_of_registration'
            )
            
            assert start_date == test_patient.date_of_registration
        
        def test_get_start_date_invalid_reference(self, test_patient):
            """Test invalid reference falls back to registration."""
            start_date = get_patient_start_date(
                test_patient,
                'invalid_reference'
            )
            
            assert start_date == test_patient.date_of_registration

Integration Testing
-------------------

Institution-Based Access Control
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Test Provider Access:**

.. code-block:: python

    # patientapp/tests/test_institution_access.py
    import pytest
    from django.contrib.auth.models import User, Permission
    from providerapp.models import Provider
    from patientapp.models import Patient, Institution
    from patientapp.utils import (
        filter_patients_by_institution,
        check_patient_access
    )
    
    @pytest.mark.django_db
    class TestInstitutionAccess:
        
        @pytest.fixture
        def institution_a(self, db):
            return Institution.objects.create(name='Hospital A')
        
        @pytest.fixture
        def institution_b(self, db):
            return Institution.objects.create(name='Hospital B')
        
        @pytest.fixture
        def provider_user(self, db, institution_a):
            user = User.objects.create_user(
                username='provider',
                password='test123'
            )
            Provider.objects.create(
                user=user,
                institution=institution_a
            )
            return user
        
        def test_provider_sees_only_own_institution_patients(
            self, provider_user, institution_a, institution_b
        ):
            """Test provider can only see their institution's patients."""
            # Create patients in both institutions
            patient_a = Patient.objects.create(
                name='Patient A',
                patient_id='PA001',
                institution=institution_a
            )
            patient_b = Patient.objects.create(
                name='Patient B',
                patient_id='PB001',
                institution=institution_b
            )
            
            # Filter patients
            all_patients = Patient.objects.all()
            filtered = filter_patients_by_institution(
                all_patients,
                provider_user
            )
            
            # Should only see institution A patients
            assert patient_a in filtered
            assert patient_b not in filtered
        
        def test_provider_cannot_access_other_institution_patient(
            self, provider_user, institution_b
        ):
            """Test provider cannot access other institution's patient."""
            patient_b = Patient.objects.create(
                name='Patient B',
                patient_id='PB001',
                institution=institution_b
            )
            
            # Should not have access
            has_access = check_patient_access(provider_user, patient_b)
            assert not has_access

Questionnaire Workflow
~~~~~~~~~~~~~~~~~~~~~~

**Test Complete Questionnaire Flow:**

.. code-block:: python

    # promapp/tests/test_questionnaire_workflow.py
    import pytest
    from promapp.models import (
        Questionnaire,
        Item,
        QuestionnaireItem,
        PatientQuestionnaire,
        QuestionnaireSubmission,
        QuestionnaireItemResponse
    )
    
    @pytest.mark.django_db
    class TestQuestionnaireWorkflow:
        
        def test_complete_questionnaire_submission(
            self, test_patient, test_user
        ):
            """Test complete questionnaire submission workflow."""
            # Create questionnaire
            questionnaire = Questionnaire.objects.create(
                name='Test Questionnaire'
            )
            
            # Create item
            item = Item.objects.create(
                name='How are you feeling?',
                response_type='Text'
            )
            
            # Add item to questionnaire
            QuestionnaireItem.objects.create(
                questionnaire=questionnaire,
                item=item,
                item_number=1
            )
            
            # Assign to patient
            pq = PatientQuestionnaire.objects.create(
                patient=test_patient,
                questionnaire=questionnaire
            )
            
            # Create submission
            submission = QuestionnaireSubmission.objects.create(
                patient_questionnaire=pq
            )
            
            # Add response
            response = QuestionnaireItemResponse.objects.create(
                questionnaire_submission=submission,
                item=item,
                response_value='Feeling good'
            )
            
            # Verify workflow
            assert submission.patient_questionnaire == pq
            assert response.questionnaire_submission == submission
            assert response.response_value == 'Feeling good'

UI/UX Testing
-------------

Vertical Tabs Testing
~~~~~~~~~~~~~~~~~~~~~

**Manual Test Checklist:**

.. code-block:: text

    PROM Review Page - Vertical Tabs
    
    ✓ Visual Verification:
      □ Topline Results section appears with red circles
      □ Other Construct Scores section appears with green circles
      □ Composite Construct Scores section appears (if applicable)
      □ First tab is active by default
    
    ✓ Tab Interaction:
      □ Clicking tab switches content
      □ Active tab has colored background and left border
      □ Only one tab content visible at a time
      □ Tab switching is instant (no delay)
    
    ✓ Content Display:
      □ Construct name displayed
      □ Current score displayed
      □ Trend indicator (arrow) displayed
      □ Bokeh plot renders correctly
      □ Related items section appears
      □ Item plots render correctly
    
    ✓ Filter Integration:
      □ Questionnaire filter updates tabs
      □ Time range filter updates plots
      □ Active tab remains selected after filter
      □ All filters work with tabs
    
    ✓ Responsive Design:
      □ Desktop (1920px+): 3-column item grid
      □ Tablet (768px-1024px): 2-column item grid
      □ Mobile (320px-767px): 1-column item grid
      □ Sidebar adapts to screen size
    
    ✓ Accessibility:
      □ Keyboard navigation works (Tab key)
      □ Enter/Space activates tabs
      □ Screen reader announces tab roles
      □ ARIA attributes present
    
    ✓ Performance:
      □ Page loads in < 2 seconds
      □ Plots load progressively
      □ No JavaScript errors in console
      □ No layout shift when switching tabs

Selenium UI Tests
~~~~~~~~~~~~~~~~~

**Automated UI Test:**

.. code-block:: python

    # tests/test_ui.py
    import pytest
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    
    @pytest.fixture
    def browser():
        """Create browser instance."""
        driver = webdriver.Chrome()
        yield driver
        driver.quit()
    
    @pytest.mark.ui
    def test_vertical_tabs_switching(browser, live_server, test_patient):
        """Test vertical tabs switch correctly."""
        # Login
        browser.get(f'{live_server.url}/account/login/')
        browser.find_element(By.NAME, 'login').send_keys('testuser')
        browser.find_element(By.NAME, 'password').send_keys('testpass123')
        browser.find_element(By.CSS_SELECTOR, 'button[type="submit"]').click()
        
        # Navigate to PROM review
        browser.get(
            f'{live_server.url}/patients/{test_patient.id}/prom-review/'
        )
        
        # Wait for page load
        WebDriverWait(browser, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, 'vertical-tabs'))
        )
        
        # Find tab buttons
        tabs = browser.find_elements(By.CSS_SELECTOR, '[role="tab"]')
        assert len(tabs) > 0
        
        # Click second tab
        if len(tabs) > 1:
            tabs[1].click()
            
            # Wait for content to switch
            WebDriverWait(browser, 5).until(
                EC.visibility_of_element_located(
                    (By.ID, tabs[1].get_attribute('aria-controls'))
                )
            )
            
            # Verify active state
            assert 'bg-red-500' in tabs[1].get_attribute('class') or \
                   'bg-green-500' in tabs[1].get_attribute('class')

Performance Testing
-------------------

Load Testing with Locust
~~~~~~~~~~~~~~~~~~~~~~~~~

**Basic Load Test:**

.. code-block:: python

    # locustfile.py
    from locust import HttpUser, task, between
    from locust import events
    
    class SATHIUser(HttpUser):
        wait_time = between(1, 3)
        
        def on_start(self):
            """Login before testing."""
            self.client.post('/account/login/', {
                'login': 'testuser',
                'password': 'testpass123'
            })
        
        @task(3)
        def view_patient_list(self):
            """View patient list (common action)."""
            self.client.get('/patients/')
        
        @task(5)
        def view_prom_review(self):
            """View PROM review (most common action)."""
            self.client.get('/patients/123e4567-e89b-12d3-a456-426614174000/prom-review/')
        
        @task(1)
        def view_patient_detail(self):
            """View patient detail (less common)."""
            self.client.get('/patients/123e4567-e89b-12d3-a456-426614174000/')
        
        @task(2)
        def apply_filters(self):
            """Apply filters on PROM review."""
            self.client.get(
                '/patients/123e4567-e89b-12d3-a456-426614174000/prom-review/',
                params={
                    'questionnaire': 'all',
                    'time_range': '5',
                    'start_date_reference': 'date_of_registration'
                }
            )

**Run Load Test:**

.. code-block:: bash

    # Start with 10 users, spawn 2 per second
    locust -f locustfile.py --host=http://localhost:8000 \
           --users 10 --spawn-rate 2
    
    # Open web UI at http://localhost:8089

**Performance Targets:**

.. list-table::
   :header-rows: 1
   :widths: 40 30 30

   * - Endpoint
     - Target (95th percentile)
     - Max Acceptable
   * - Patient List
     - < 500ms
     - < 1000ms
   * - PROM Review (cold cache)
     - < 2000ms
     - < 5000ms
   * - PROM Review (warm cache)
     - < 500ms
     - < 1000ms
   * - Patient Detail
     - < 300ms
     - < 600ms

Database Query Testing
~~~~~~~~~~~~~~~~~~~~~~

**Test Query Count:**

.. code-block:: python

    import pytest
    from django.test.utils import override_settings
    from django.db import connection
    from django.test.utils import CaptureQueriesContext
    
    @pytest.mark.django_db
    def test_patient_list_query_count(client, test_user, test_patient):
        """Test patient list doesn't have N+1 queries."""
        # Add permission
        from django.contrib.auth.models import Permission
        permission = Permission.objects.get(codename='view_patient')
        test_user.user_permissions.add(permission)
        
        client.force_login(test_user)
        
        # Capture queries
        with CaptureQueriesContext(connection) as context:
            response = client.get('/patients/')
        
        # Should use select_related/prefetch_related
        # Acceptable query count: ~5-10 queries
        assert len(context.captured_queries) < 15

Security Testing
----------------

Permission Tests
~~~~~~~~~~~~~~~~

**Test View Permissions:**

.. code-block:: python

    # tests/test_security.py
    import pytest
    from django.urls import reverse
    
    @pytest.mark.django_db
    class TestViewPermissions:
        
        def test_anonymous_cannot_access_patient_list(self, client):
            """Test anonymous users cannot access patient list."""
            response = client.get(reverse('patient_list'))
            assert response.status_code == 302  # Redirect to login
        
        def test_user_without_permission_cannot_access(
            self, client, test_user
        ):
            """Test users without permission get 403."""
            client.force_login(test_user)
            response = client.get(reverse('patient_list'))
            assert response.status_code == 403
        
        def test_user_with_permission_can_access(
            self, client, test_user
        ):
            """Test users with permission can access."""
            from django.contrib.auth.models import Permission
            permission = Permission.objects.get(codename='view_patient')
            test_user.user_permissions.add(permission)
            
            client.force_login(test_user)
            response = client.get(reverse('patient_list'))
            assert response.status_code == 200

CSRF Protection Tests
~~~~~~~~~~~~~~~~~~~~~

**Test CSRF Token Required:**

.. code-block:: python

    @pytest.mark.django_db
    def test_post_requires_csrf_token(client, test_user):
        """Test POST requests require CSRF token."""
        client.force_login(test_user)
        
        # POST without CSRF token
        response = client.post('/patients/create/', {
            'name': 'Test Patient',
            'patient_id': 'P001'
        })
        
        # Should fail with 403
        assert response.status_code == 403

Test Data Factories
-------------------

Using factory_boy
~~~~~~~~~~~~~~~~~

**Define Factories:**

.. code-block:: python

    # tests/factories.py
    import factory
    from factory.django import DjangoModelFactory
    from patientapp.models import Patient, Institution
    from django.contrib.auth.models import User
    
    class InstitutionFactory(DjangoModelFactory):
        class Meta:
            model = Institution
        
        name = factory.Sequence(lambda n: f'Hospital {n}')
        address = factory.Faker('address')
    
    class PatientFactory(DjangoModelFactory):
        class Meta:
            model = Patient
        
        name = factory.Faker('name')
        patient_id = factory.Sequence(lambda n: f'P{n:05d}')
        institution = factory.SubFactory(InstitutionFactory)
        date_of_registration = factory.Faker('date_this_year')
        gender = factory.Iterator(['M', 'F', 'O'])
    
    class UserFactory(DjangoModelFactory):
        class Meta:
            model = User
        
        username = factory.Sequence(lambda n: f'user{n}')
        email = factory.LazyAttribute(lambda obj: f'{obj.username}@example.com')
        password = factory.PostGenerationMethodCall('set_password', 'testpass123')

**Use Factories in Tests:**

.. code-block:: python

    from tests.factories import PatientFactory, InstitutionFactory
    
    @pytest.mark.django_db
    def test_with_factory():
        """Test using factory-generated data."""
        # Create 5 patients
        patients = PatientFactory.create_batch(5)
        
        assert len(patients) == 5
        assert all(p.institution is not None for p in patients)

Running Tests
-------------

Run All Tests
~~~~~~~~~~~~~

.. code-block:: bash

    # Run all tests
    pytest
    
    # Run with coverage
    pytest --cov=. --cov-report=html
    
    # Run specific test file
    pytest patientapp/tests/test_models.py
    
    # Run specific test class
    pytest patientapp/tests/test_models.py::TestPatientModel
    
    # Run specific test
    pytest patientapp/tests/test_models.py::TestPatientModel::test_patient_creation

Run Tests by Marker
~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

    # Run only unit tests
    pytest -m unit
    
    # Run only integration tests
    pytest -m integration
    
    # Run only UI tests
    pytest -m ui
    
    # Skip slow tests
    pytest -m "not slow"

Parallel Testing
~~~~~~~~~~~~~~~~

.. code-block:: bash

    # Install pytest-xdist
    pip install pytest-xdist
    
    # Run tests in parallel (4 workers)
    pytest -n 4

Coverage Reports
~~~~~~~~~~~~~~~~

.. code-block:: bash

    # Generate HTML coverage report
    pytest --cov=. --cov-report=html
    
    # Open report
    open htmlcov/index.html
    
    # Generate terminal report
    pytest --cov=. --cov-report=term-missing

Continuous Integration
----------------------

GitHub Actions
~~~~~~~~~~~~~~

**.github/workflows/tests.yml:**

.. code-block:: yaml

    name: Tests
    
    on: [push, pull_request]
    
    jobs:
      test:
        runs-on: ubuntu-latest
        
        services:
          postgres:
            image: postgres:15
            env:
              POSTGRES_PASSWORD: postgres
            options: >-
              --health-cmd pg_isready
              --health-interval 10s
              --health-timeout 5s
              --health-retries 5
        
        steps:
          - uses: actions/checkout@v3
          
          - name: Set up Python
            uses: actions/setup-python@v4
            with:
              python-version: '3.11'
          
          - name: Install dependencies
            run: |
              pip install -r requirements.txt
              pip install pytest pytest-django pytest-cov
          
          - name: Run tests
            run: pytest --cov=. --cov-report=xml
            env:
              DATABASE_URL: postgresql://postgres:postgres@localhost/test_db
          
          - name: Upload coverage
            uses: codecov/codecov-action@v3

Best Practices
--------------

Test Organization
~~~~~~~~~~~~~~~~~

**DO:**

- Organize tests by app (``patientapp/tests/``)
- Use descriptive test names
- Test one thing per test
- Use fixtures for common setup
- Mock external dependencies
- Test edge cases and error conditions

**DON'T:**

- Put all tests in one file
- Test multiple things in one test
- Use real external APIs in tests
- Skip error case testing
- Ignore test failures

Test Coverage Goals
~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 40 30 30

   * - Component
     - Target Coverage
     - Minimum Coverage
   * - Models
     - 90%+
     - 80%
   * - Views
     - 85%+
     - 75%
   * - Forms
     - 90%+
     - 80%
   * - Utilities
     - 95%+
     - 85%
   * - Overall
     - 85%+
     - 75%

Resources
---------

- `pytest Documentation <https://docs.pytest.org/>`_
- `pytest-django <https://pytest-django.readthedocs.io/>`_
- `factory_boy <https://factoryboy.readthedocs.io/>`_
- `Selenium Documentation <https://www.selenium.dev/documentation/>`_
- `Locust Documentation <https://docs.locust.io/>`_
- `Django Testing <https://docs.djangoproject.com/en/stable/topics/testing/>`_
