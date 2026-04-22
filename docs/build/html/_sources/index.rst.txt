SATHI Documentation
===================

**Self Reported Assessment and Tracking for Health Insights**

Welcome to SATHI, an open-source Django application for collecting, managing, and analyzing patient-reported outcomes (PROMs) and patient-reported experience measures (PREMs).

.. raw:: html

   <div style="text-align: center; margin: 40px 0;">
      <p style="font-size: 1.2em; color: #555;">
         A comprehensive platform for understanding patient concerns through PROMs and PREMs
      </p>
   </div>

----

Documentation Sections
----------------------

.. raw:: html

   <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px; margin: 30px 0;">
      
      <div style="border: 2px solid #0066cc; border-radius: 8px; padding: 20px; text-align: center; background: #f8f9fa;">
         <div style="font-size: 3em; margin-bottom: 10px;">👤</div>
         <h3 style="margin: 10px 0; color: #0066cc;">Patient Documentation</h3>
         <p style="color: #666; margin: 10px 0;">Guides for completing questionnaires and viewing your health data</p>
         <a href="patient/index.html" style="display: inline-block; margin-top: 10px; padding: 10px 20px; background: #0066cc; color: white; text-decoration: none; border-radius: 5px; font-weight: bold;">View Patient Docs →</a>
      </div>
      
      <div style="border: 2px solid #28a745; border-radius: 8px; padding: 20px; text-align: center; background: #f8f9fa;">
         <div style="font-size: 3em; margin-bottom: 10px;">🏥</div>
         <h3 style="margin: 10px 0; color: #28a745;">Healthcare Worker Documentation</h3>
         <p style="color: #666; margin: 10px 0;">Managing patients, questionnaires, and reviewing clinical results</p>
         <a href="healthcare_worker/index.html" style="display: inline-block; margin-top: 10px; padding: 10px 20px; background: #28a745; color: white; text-decoration: none; border-radius: 5px; font-weight: bold;">View HCP Docs →</a>
      </div>
      
      <div style="border: 2px solid #6f42c1; border-radius: 8px; padding: 20px; text-align: center; background: #f8f9fa;">
         <div style="font-size: 3em; margin-bottom: 10px;">💻</div>
         <h3 style="margin: 10px 0; color: #6f42c1;">Developer Documentation</h3>
         <p style="color: #666; margin: 10px 0;">Installation, architecture, API reference, and technical guides</p>
         <a href="developer/index.html" style="display: inline-block; margin-top: 10px; padding: 10px 20px; background: #6f42c1; color: white; text-decoration: none; border-radius: 5px; font-weight: bold;">View Dev Docs →</a>
      </div>
      
   </div>

----

Key Features
------------

For Patients
~~~~~~~~~~~~

📱 **Mobile-Responsive Interface**
   Complete questionnaires on any device with an adaptive, user-friendly interface

🌍 **Multi-Language Support**
   Questionnaires available in multiple languages with dynamic font selection

🎯 **Conditional Logic**
   Smart questionnaires that adapt based on your responses to reduce burden

📊 **Personal Health Portal**
   View your questionnaire history and health data visualizations

🎤 **Multimedia Support**
   Audio and video integration for enhanced accessibility

🔒 **Privacy & Security**
   Encrypted data with secure authentication and two-factor protection

For Healthcare Providers
~~~~~~~~~~~~~~~~~~~~~~~~~

📈 **Comprehensive Dashboard**
   Monitor patient responses with intuitive visualizations and clinical indicators

🎯 **Clinical Scoring**
   Track construct scores, composite scores, and item-level responses

🚦 **Significance Indicators**
   Color-coded alerts for clinically significant changes and thresholds

📊 **Interactive Plots**
   Bokeh-powered visualizations with normative scores and trend analysis

👥 **Population Aggregation**
   Compare individual patients against population statistics

🏢 **Institution Security**
   Row-level security ensures providers only access their institution's data

📤 **Data Export**
   Export patient responses in CSV format for external analysis

For Questionnaire Designers
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

🔐 **Role-Based Access**
   Granular permissions for questionnaire creation and management

📝 **Item Bank System**
   Create reusable items and share across multiple questionnaires

🎨 **Flexible Response Types**
   Support for Text, Number, Likert scales, and Range selections

🧮 **Advanced Scoring**
   Complex equations with variables, conditionals, and composite calculations

🌐 **Translation Management**
   Built-in support for multi-language questionnaire content

📥 **Bulk Operations**
   CSV import/export for efficient item and questionnaire management

🔄 **Conditional Display**
   Rule-based logic to show/hide questions based on previous responses

For Developers
~~~~~~~~~~~~~~

🏗️ **Modern Architecture**
   Django 6.0, Python 3.13, PostgreSQL with clean separation of concerns

⚡ **Performance Optimized**
   Lazy loading, Memcached integration, and optimized database queries

🎨 **Modern Frontend**
   HTMX for dynamic updates, TailwindCSS for styling, Django Cotton components

🔒 **Enterprise Security**
   Field-level encryption, rate limiting, reCAPTCHA, comprehensive audit logging

📱 **Progressive Web App**
   Service workers, offline support, and installable on mobile devices

🧪 **Testing Framework**
   Comprehensive test suite with pytest, Selenium, and Locust

📚 **Complete Documentation**
   API reference, architecture guides, and development workflows

🐳 **Deployment Ready**
   Production configurations for Nginx, Gunicorn, Supervisor, and SSL

Technology Stack
----------------

**Backend**
   - Django 6.0
   - Python 3.13
   - PostgreSQL
   - Memcached

**Frontend**
   - HTMX (dynamic updates)
   - TailwindCSS v4 (styling)
   - django-cotton (components)
   - Bokeh & Plotly (visualizations)

**Security**
   - django-allauth (authentication)
   - django-ratelimit (rate limiting)
   - django-recaptcha (bot protection)
   - django-secured-fields (encryption)

**Deployment**
   - Nginx (web server)
   - Gunicorn (WSGI server)
   - Supervisor (process management)
   - Let's Encrypt (SSL certificates)

**Internationalization**
   - django-parler (model translations)
   - gettext (UI translations)

Quick Links
-----------

- `GitHub Repository <https://github.com/CHAVI-India/chavi-prom>`_
- `Issue Tracker <https://github.com/CHAVI-India/chavi-prom/issues>`_
- `Contributing Guidelines <developer/contributing.html>`_
- `License <https://github.com/CHAVI-India/chavi-prom/blob/main/LICENSE>`_

----

.. toctree::
   :maxdepth: 2
   :hidden:
   :caption: Documentation

   patient/index
   healthcare_worker/index
   developer/index





