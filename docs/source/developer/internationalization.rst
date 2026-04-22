Internationalization & Translation
===================================

Complete guide to adding new languages, translating content, and managing multilingual support in SATHI.

.. contents:: Table of Contents
   :local:
   :depth: 3

Overview
--------

SATHI supports comprehensive internationalization (i18n) through two complementary systems:

1. **Django Parler**: For translating database content (questionnaires, items, responses)
2. **Django gettext**: For translating the user interface (templates, messages, labels)

This dual approach allows:

- Healthcare workers to create questionnaires in multiple languages
- Patients to view the interface in their preferred language
- Administrators to manage translations through both UI and files

Architecture
------------

Translation Layers
~~~~~~~~~~~~~~~~~~

**Database Content (Parler)**
   - Questionnaire names and descriptions
   - Item text and instructions
   - Likert/Range scale labels
   - Construct scale names
   - Diagnosis and treatment names

**User Interface (gettext)**
   - Navigation menus
   - Form labels and buttons
   - Error messages
   - Help text and instructions
   - Static page content

Language Configuration
----------------------

Supported Languages
~~~~~~~~~~~~~~~~~~~

Languages are configured in ``chaviprom/settings.py``:

.. code-block:: python

   # Load from environment variable
   LANGUAGES_STRING = env('LANGUAGES', default='en:English,hi:Hindi,bn:Bengali')
   
   # Parse into Django format
   LANGUAGES = [
       tuple(lang.split(':')) 
       for lang in LANGUAGES_STRING.split(',')
   ]
   
   # Example result:
   # LANGUAGES = [
   #     ('en', 'English'),
   #     ('hi', 'Hindi'),
   #     ('bn', 'Bengali'),
   # ]

**Environment Variable Format:**

.. code-block:: bash

   # In .env file
   LANGUAGES=en:English,hi:Hindi,bn:Bengali,ta:Tamil,te:Telugu

Default Language
~~~~~~~~~~~~~~~~

.. code-block:: python

   LANGUAGE_CODE = 'en'  # Default language
   
   PARLER_LANGUAGES = {
       None: (
           {'code': 'en'},
           {'code': 'hi'},
           {'code': 'bn'},
       ),
       'default': {
           'fallback': 'en',
           'hide_untranslated': False,
       }
   }

Adding a New Language
---------------------

Step 1: Update Environment Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Add the new language to your ``.env`` file:

.. code-block:: bash

   # Before
   LANGUAGES=en:English,hi:Hindi,bn:Bengali
   
   # After (adding Tamil)
   LANGUAGES=en:English,hi:Hindi,bn:Bengali,ta:Tamil

**Language Code Reference:**

- ``en`` - English
- ``hi`` - Hindi
- ``bn`` - Bengali
- ``ta`` - Tamil
- ``te`` - Telugu
- ``mr`` - Marathi
- ``gu`` - Gujarati
- ``kn`` - Kannada
- ``ml`` - Malayalam
- ``pa`` - Punjabi
- ``or`` - Odia
- ``as`` - Assamese

Step 2: Update Parler Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Edit ``chaviprom/settings.py`` to add the language code to ``PARLER_LANGUAGES``:

.. code-block:: python

   PARLER_LANGUAGES = {
       None: (
           {'code': 'en'},
           {'code': 'hi'},
           {'code': 'bn'},
           {'code': 'ta'},  # New language
       ),
       'default': {
           'fallback': 'en',
           'hide_untranslated': False,
       }
   }

Step 3: Create Translation Files
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Prerequisites:**

- ``gettext`` must be installed on your system
- Linux: ``sudo apt-get install gettext``
- macOS: ``brew install gettext``
- Windows: Download from `GNU gettext <https://gnuwin32.sourceforge.net/packages/gettext.htm>`_

**Generate Message Files:**

.. code-block:: bash

   # Create .po file for new language (Tamil example)
   python manage.py makemessages -l ta -i "venv" -i "node_modules"
   
   # For multiple languages at once
   python manage.py makemessages -l ta -l te -l mr -i "venv" -i "node_modules"

**What This Does:**

- Scans all Python and template files for translatable strings
- Creates ``locale/ta/LC_MESSAGES/django.po``
- Extracts strings marked with ``{% trans %}`` and ``gettext()``
- Ignores virtual environment and node_modules

Step 4: Translate Interface Strings
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Edit the generated ``.po`` file at ``locale/ta/LC_MESSAGES/django.po``:

.. code-block:: po

   # Example translations
   msgid "Welcome"
   msgstr "வரவேற்பு"
   
   msgid "Patient Portal"
   msgstr "நோயாளி போர்ட்டல்"
   
   msgid "Complete Questionnaire"
   msgstr "கேள்வித்தாளை முடிக்கவும்"
   
   msgid "Submit"
   msgstr "சமர்ப்பிக்கவும்"

**Translation Tools:**

- **Poedit**: GUI editor for .po files (`poedit.net <https://poedit.net/>`_)
- **Lokalize**: KDE translation tool
- **Manual editing**: Any text editor works

Step 5: Compile Translations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

After editing ``.po`` files, compile them to binary format:

.. code-block:: bash

   # Compile all languages
   python manage.py compilemessages -i "venv" -i "node_modules"
   
   # Compile specific language
   python manage.py compilemessages -l ta -i "venv" -i "node_modules"

**Output:**

- Creates ``locale/ta/LC_MESSAGES/django.mo`` (binary file)
- This file is used by Django at runtime
- Must recompile after every ``.po`` file change

Step 6: Restart Server
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Development
   python manage.py runserver
   
   # Production (Supervisor)
   sudo supervisorctl restart chaviprom

Database Content Translation
-----------------------------

Translating Through Admin Interface
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

SATHI uses Django Parler for database content translation. All translatable models have language tabs in the admin interface.

**Translating a Questionnaire:**

1. Navigate to **Admin → Questionnaires → Select Questionnaire**
2. Click the **language tabs** at the top (English | Hindi | Bengali | Tamil)
3. Switch to target language tab
4. Enter translated content:
   - Name
   - Description
   - Instructions
5. Click **Save**

**Translating Items:**

1. Navigate to **Admin → Items → Select Item**
2. Switch to target language tab
3. Translate:
   - Item name (question text)
   - Item instructions
   - Media descriptions
4. Click **Save**

**Translating Likert Scales:**

1. Navigate to **Admin → Likert Scales → Select Scale**
2. Switch to target language tab
3. Translate scale name
4. Navigate to **Likert Scale Response Elements**
5. Translate each response option text
6. Click **Save**

Translating Through Django Shell
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For bulk translations or programmatic updates:

.. code-block:: python

   from promapp.models import Questionnaire
   
   # Get questionnaire
   q = Questionnaire.objects.get(id=1)
   
   # Set English translation
   q.set_current_language('en')
   q.name = "Patient Health Questionnaire"
   q.description = "Assess patient health status"
   q.save()
   
   # Set Hindi translation
   q.set_current_language('hi')
   q.name = "रोगी स्वास्थ्य प्रश्नावली"
   q.description = "रोगी स्वास्थ्य स्थिति का आकलन करें"
   q.save()
   
   # Set Tamil translation
   q.set_current_language('ta')
   q.name = "நோயாளி சுகாதார கேள்வித்தாள்"
   q.description = "நோயாளி சுகாதார நிலையை மதிப்பிடவும்"
   q.save()

Checking Available Translations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from promapp.models import Item
   
   item = Item.objects.get(id=1)
   
   # Get all available translations
   translations = item.get_available_languages()
   # Returns: ['en', 'hi', 'bn']
   
   # Check if translation exists
   if item.has_translation('ta'):
       item.set_current_language('ta')
       print(item.name)

User Interface Translation
---------------------------

Template Translation
~~~~~~~~~~~~~~~~~~~~

Use ``{% trans %}`` and ``{% blocktrans %}`` template tags:

**Simple Translation:**

.. code-block:: django

   {% load i18n %}
   
   <h1>{% trans "Welcome to SATHI" %}</h1>
   <p>{% trans "Complete your questionnaires" %}</p>
   
   <button>{% trans "Submit" %}</button>

**Translation with Variables:**

.. code-block:: django

   {% load i18n %}
   
   {% blocktrans with name=patient.name %}
   Welcome, {{ name }}!
   {% endblocktrans %}
   
   {% blocktrans count counter=items|length %}
   You have {{ counter }} questionnaire to complete.
   {% plural %}
   You have {{ counter }} questionnaires to complete.
   {% endblocktrans %}

**Translation with Context:**

.. code-block:: django

   {% load i18n %}
   
   {# Context helps translators understand usage #}
   {% trans "Date" context "questionnaire submission date" %}
   {% trans "Date" context "patient birth date" %}

Python Code Translation
~~~~~~~~~~~~~~~~~~~~~~~~

Use ``gettext()`` and related functions:

.. code-block:: python

   from django.utils.translation import gettext as _
   from django.utils.translation import gettext_lazy
   from django.utils.translation import ngettext
   
   # Simple translation
   message = _("Questionnaire submitted successfully")
   
   # Lazy translation (for class-level definitions)
   class MyForm(forms.Form):
       name = forms.CharField(
           label=gettext_lazy("Patient Name")
       )
   
   # Plural forms
   def get_message(count):
       return ngettext(
           "%(count)d item completed",
           "%(count)d items completed",
           count
       ) % {'count': count}

Model Translation
~~~~~~~~~~~~~~~~~

For model field help text and verbose names:

.. code-block:: python

   from django.db import models
   from django.utils.translation import gettext_lazy as _
   
   class Patient(models.Model):
       name = models.CharField(
           max_length=200,
           verbose_name=_("Patient Name"),
           help_text=_("Enter the patient's full name")
       )
       
       class Meta:
           verbose_name = _("Patient")
           verbose_name_plural = _("Patients")

Language Switching
------------------

URL-Based Language Switching
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

SATHI uses ``i18n_patterns`` for language prefixes in URLs:

.. code-block:: python

   # chaviprom/urls.py
   from django.conf.urls.i18n import i18n_patterns
   
   urlpatterns = i18n_patterns(
       path('patients/', include('patientapp.urls')),
       path('questionnaires/', include('promapp.urls')),
   )

**URL Examples:**

- ``/en/patients/`` - English
- ``/hi/patients/`` - Hindi
- ``/ta/patients/`` - Tamil

Middleware Configuration
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # settings.py
   MIDDLEWARE = [
       'django.middleware.security.SecurityMiddleware',
       'django.contrib.sessions.middleware.SessionMiddleware',
       'django.middleware.locale.LocaleMiddleware',  # Language detection
       'django.middleware.common.CommonMiddleware',
       # ... other middleware
   ]

Language Selector Widget
~~~~~~~~~~~~~~~~~~~~~~~~

The navbar includes a language dropdown:

.. code-block:: django

   {% load i18n %}
   
   <form action="{% url 'set_language' %}" method="post">
       {% csrf_token %}
       <select name="language" onchange="this.form.submit()">
           {% get_available_languages as languages %}
           {% for lang_code, lang_name in languages %}
               <option value="{{ lang_code }}"
                   {% if lang_code == LANGUAGE_CODE %}selected{% endif %}>
                   {{ lang_name }}
               </option>
           {% endfor %}
       </select>
   </form>

Session-Based Language Preference
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Language preference is stored in the user's session:

.. code-block:: python

   # In views
   from django.utils.translation import activate
   
   def set_user_language(request, language_code):
       activate(language_code)
       request.session[LANGUAGE_SESSION_KEY] = language_code
       return redirect(request.META.get('HTTP_REFERER', '/'))

Translation Workflow
--------------------

Development Workflow
~~~~~~~~~~~~~~~~~~~~

1. **Mark Strings for Translation**

   .. code-block:: python
   
      # In Python
      from django.utils.translation import gettext as _
      message = _("Hello, world!")
   
   .. code-block:: django
   
      {# In templates #}
      {% trans "Hello, world!" %}

2. **Extract Messages**

   .. code-block:: bash
   
      python manage.py makemessages -l ta -i "venv" -i "node_modules"

3. **Translate Strings**

   Edit ``locale/ta/LC_MESSAGES/django.po``

4. **Compile Messages**

   .. code-block:: bash
   
      python manage.py compilemessages -i "venv" -i "node_modules"

5. **Test Translations**

   - Switch language in UI
   - Verify all strings are translated
   - Check for encoding issues

6. **Commit Changes**

   .. code-block:: bash
   
      git add locale/
      git commit -m "Add Tamil translations"

Production Deployment
~~~~~~~~~~~~~~~~~~~~~

1. **Pull Latest Translations**

   .. code-block:: bash
   
      git pull origin main

2. **Compile Messages**

   .. code-block:: bash
   
      python manage.py compilemessages -i "venv" -i "node_modules"

3. **Collect Static Files** (if needed)

   .. code-block:: bash
   
      python manage.py collectstatic --noinput

4. **Restart Application**

   .. code-block:: bash
   
      sudo supervisorctl restart chaviprom

Translation File Structure
--------------------------

Directory Layout
~~~~~~~~~~~~~~~~

.. code-block:: text

   chaviprom/
   ├── locale/
   │   ├── en/
   │   │   └── LC_MESSAGES/
   │   │       ├── django.po
   │   │       └── django.mo
   │   ├── hi/
   │   │   └── LC_MESSAGES/
   │   │       ├── django.po
   │   │       └── django.mo
   │   ├── bn/
   │   │   └── LC_MESSAGES/
   │   │       ├── django.po
   │   │       └── django.mo
   │   └── ta/
   │       └── LC_MESSAGES/
   │           ├── django.po
   │           └── django.mo

PO File Format
~~~~~~~~~~~~~~

.. code-block:: po

   # Translation metadata
   msgid ""
   msgstr ""
   "Project-Id-Version: SATHI 1.0\n"
   "Report-Msgid-Bugs-To: \n"
   "POT-Creation-Date: 2026-04-22 19:00+0530\n"
   "Language: ta\n"
   "MIME-Version: 1.0\n"
   "Content-Type: text/plain; charset=UTF-8\n"
   
   # Simple translation
   #: templates/navbar.html:15
   msgid "Home"
   msgstr "முகப்பு"
   
   # Translation with context
   #: promapp/views.py:45
   msgctxt "questionnaire status"
   msgid "Completed"
   msgstr "முடிந்தது"
   
   # Plural forms
   #: promapp/views.py:67
   msgid "%(count)d questionnaire"
   msgid_plural "%(count)d questionnaires"
   msgstr[0] "%(count)d கேள்வித்தாள்"
   msgstr[1] "%(count)d கேள்வித்தாள்கள்"

Best Practices
--------------

Translation Guidelines
~~~~~~~~~~~~~~~~~~~~~~

1. **Use Descriptive Context**

   .. code-block:: python
   
      # Good
      _("Date", context="submission date")
      _("Date", context="birth date")
      
      # Avoid
      _("Date")

2. **Avoid String Concatenation**

   .. code-block:: python
   
      # Bad
      message = _("Welcome") + " " + user.name
      
      # Good
      message = _("Welcome, %(name)s") % {'name': user.name}

3. **Use Lazy Translation for Class Definitions**

   .. code-block:: python
   
      from django.utils.translation import gettext_lazy as _
      
      class MyModel(models.Model):
           name = models.CharField(verbose_name=_("Name"))

4. **Keep Translations in Sync**

   .. code-block:: bash
   
      # Update all language files when adding new strings
      python manage.py makemessages -a -i "venv" -i "node_modules"

5. **Test All Languages**

   - Switch to each language
   - Verify UI renders correctly
   - Check for text overflow
   - Validate special characters

Font Configuration
~~~~~~~~~~~~~~~~~~

Different languages may require different fonts:

.. code-block:: python

   # settings.py
   LANGUAGE_FONTS = {
       'en': 'Arial, sans-serif',
       'hi': 'Noto Sans Devanagari, sans-serif',
       'bn': 'Noto Sans Bengali, sans-serif',
       'ta': 'Noto Sans Tamil, sans-serif',
   }

In templates:

.. code-block:: django

   {% load i18n %}
   
   <style>
       body {
           font-family: {{ LANGUAGE_FONTS|get:LANGUAGE_CODE }};
       }
   </style>

RTL Language Support
~~~~~~~~~~~~~~~~~~~~

For right-to-left languages (Arabic, Urdu):

.. code-block:: python

   # settings.py
   LANGUAGES_BIDI = ['ar', 'ur', 'he']

.. code-block:: django

   {% load i18n %}
   
   <html dir="{% if LANGUAGE_BIDI %}rtl{% else %}ltr{% endif %}">

Troubleshooting
---------------

Common Issues
~~~~~~~~~~~~~

**Translations Not Appearing**

1. Check ``.mo`` file exists:

   .. code-block:: bash
   
      ls locale/ta/LC_MESSAGES/django.mo

2. Recompile messages:

   .. code-block:: bash
   
      python manage.py compilemessages -i "venv" -i "node_modules"

3. Restart server:

   .. code-block:: bash
   
      python manage.py runserver

**Encoding Errors**

Ensure ``.po`` files use UTF-8:

.. code-block:: po

   "Content-Type: text/plain; charset=UTF-8\n"

**Missing Translations**

Update message files:

.. code-block:: bash

   python manage.py makemessages -l ta -i "venv" -i "node_modules"

**Fuzzy Translations**

Remove ``#, fuzzy`` markers from ``.po`` files after reviewing translations.

Database Translations Not Showing
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. **Check Parler Configuration**

   .. code-block:: python
   
      # Verify language is in PARLER_LANGUAGES
      PARLER_LANGUAGES = {
          None: (
              {'code': 'en'},
              {'code': 'ta'},  # Must be here
          ),
      }

2. **Verify Translation Exists**

   .. code-block:: python
   
      item = Item.objects.get(id=1)
      print(item.get_available_languages())

3. **Check Fallback Settings**

   .. code-block:: python
   
      PARLER_LANGUAGES = {
          'default': {
              'fallback': 'en',
              'hide_untranslated': False,  # Show English if translation missing
          }
      }

Testing Translations
--------------------

Manual Testing
~~~~~~~~~~~~~~

1. **Switch Language in UI**
   - Use language selector in navbar
   - Verify URL changes (``/en/`` → ``/ta/``)

2. **Check All Pages**
   - Navigation menus
   - Forms and labels
   - Error messages
   - Help text

3. **Test Database Content**
   - Create questionnaire in English
   - Add Tamil translation
   - Switch language and verify

Automated Testing
~~~~~~~~~~~~~~~~~

.. code-block:: python

   from django.test import TestCase
   from django.utils.translation import activate
   
   class TranslationTests(TestCase):
       def test_tamil_translation(self):
           activate('ta')
           response = self.client.get('/patients/')
           self.assertContains(response, 'நோயாளர்கள்')
       
       def test_questionnaire_translation(self):
           from promapp.models import Questionnaire
           
           q = Questionnaire.objects.create()
           q.set_current_language('en')
           q.name = "Health Survey"
           q.save()
           
           q.set_current_language('ta')
           q.name = "சுகாதார கணக்கெடுப்பு"
           q.save()
           
           q.set_current_language('ta')
           self.assertEqual(q.name, "சுகாதார கணக்கெடுப்பு")

Resources
---------

External Resources
~~~~~~~~~~~~~~~~~~

- `Django Internationalization Documentation <https://docs.djangoproject.com/en/stable/topics/i18n/>`_
- `Django Parler Documentation <https://django-parler.readthedocs.io/>`_
- `Poedit Translation Editor <https://poedit.net/>`_
- `GNU gettext Manual <https://www.gnu.org/software/gettext/manual/>`_

Translation Services
~~~~~~~~~~~~~~~~~~~~

For professional translations:

- Google Translate API (for initial drafts)
- Professional translation services
- Community translators
- Native speakers for review

Language Codes Reference
~~~~~~~~~~~~~~~~~~~~~~~~~

ISO 639-1 codes for Indian languages:

- ``as`` - Assamese (অসমীয়া)
- ``bn`` - Bengali (বাংলা)
- ``gu`` - Gujarati (ગુજરાતી)
- ``hi`` - Hindi (हिन्दी)
- ``kn`` - Kannada (ಕನ್ನಡ)
- ``ml`` - Malayalam (മലയാളം)
- ``mr`` - Marathi (मराठी)
- ``or`` - Odia (ଓଡ଼ିଆ)
- ``pa`` - Punjabi (ਪੰਜਾਬੀ)
- ``ta`` - Tamil (தமிழ்)
- ``te`` - Telugu (తెలుగు)
