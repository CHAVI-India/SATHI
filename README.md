![CodeRabbit Pull Request Reviews](https://img.shields.io/coderabbit/prs/github/CHAVI-India/chavi-prom?utm_source=oss&utm_medium=github&utm_campaign=CHAVI-India%2Fchavi-prom&labelColor=171717&color=FF570A&link=https%3A%2F%2Fcoderabbit.ai&label=CodeRabbit+Reviews)

[![DOI](https://zenodo.org/badge/981641906.svg)](https://doi.org/10.5281/zenodo.19044354)

# SATHI - Self Reported Assessment and Tracking for Health Insights

Welcome to **SATHI** (Self Reported Assessment and Tracking for Health Insights). This is a comprehensive Django-based application for collecting, managing, and analyzing patient-reported outcomes with advanced features for patients, healthcare providers, and questionnaire designers.

---

## � **Documentation**

### **Comprehensive Documentation Site**
For complete documentation including installation guides, user manuals, and API references, visit:

**[📖 SATHI Documentation](https://sathi.readthedocs.io/en/latest/#)** 

The documentation is organized into three main sections:

- **👤 Patient Documentation**: Guides for patients using SATHI to complete questionnaires
- **🏥 Healthcare Worker Documentation**: Instructions for healthcare providers managing patients and reviewing results
- **💻 Developer Documentation**: Technical documentation for installation, configuration, and extending SATHI

---

## � **Quick Start**

### For Patients
See [Patient Documentation](./docs/build/html/patient/index.html) for:
- Getting started guide
- Answering questionnaires
- Viewing your results
- Two-factor authentication setup

### For Healthcare Workers
See [Healthcare Worker Documentation](./docs/build/html/healthcare_worker/index.html) for:
- Patient management
- Creating and assigning questionnaires
- Reviewing patient results
- Understanding clinical scores

### For Developers
See [Developer Documentation](./docs/build/html/developer/index.html) for:
- **Installation**: Production deployment with Nginx, Gunicorn, Supervisor, and Let's Encrypt SSL
- **Architecture**: System design, data models, and design patterns
- **Frontend Development**: Tailwind CSS, language switching, vertical tabs
- **UI Components**: Complete Django Cotton component library reference
- **API Reference**: Complete API documentation with docstrings
- **Configuration**: Environment variables and settings
- **Contributing**: Development guidelines

---

## 🎯 **Key Features**

### For Patients
- 📱 Mobile-responsive questionnaire interface
- 🌍 Multi-language support with dynamic font selection
- 🎯 Conditional logic to reduce response burden
- 📊 Personal health data portal with visualizations
- 🎤 Audio/video integration for enhanced accessibility

### For Healthcare Providers
- 📈 Comprehensive patient response dashboard
- 🎯 Construct and composite score tracking
- 🚦 Clinical significance indicators with color coding
- 📊 Interactive plots with normative and threshold scores
- 👥 Result aggregation across patient populations

### For Questionnaire Designers
- 🔐 Role-based access control
- 📝 Item bank creation and reuse
- 🎨 Flexible response types (Text, Number, Likert, Range)
- 🧮 Complex scoring equations with variables and conditionals
- 🌐 Translation management for multi-language support
- � CSV import/export for bulk operations

### Security Features
- 🔒 Encrypted patient identifiers
- 🔐 Two-factor authentication (Email OTP and TOTP)
- 🏢 Institution-based row-level security
- 🛡️ Rate limiting and reCAPTCHA protection
- 📋 Comprehensive audit logging

---

## �️ **Technology Stack**

- **Backend**: Django 6.0, Python 3.13, PostgreSQL
- **Frontend**: HTMX, TailwindCSS, django-cotton
- **Security**: django-two-factor-auth, django-ratelimit, django-recaptcha
- **Deployment**: Nginx, Gunicorn, Supervisor, Memcached
- **Visualization**: Plotly, Bokeh
- **Internationalization**: django-parler

---

## 📦 **Installation**

### Quick Development Setup

```bash
# Clone repository
git clone https://github.com/CHAVI-India/chavi-prom.git
cd chavi-prom

# Create virtual environment
python3.13 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Setup database
sudo -u postgres psql -c "CREATE DATABASE chaviprom;"
sudo -u postgres psql -c "CREATE USER chaviprom_user WITH PASSWORD 'password';"

# Configure environment
cp sampleenv.txt .env
# Edit .env with your settings

# Run migrations
python manage.py migrate
python manage.py createsuperuser
python manage.py collectstatic --noinput

# Start development server
python manage.py runserver
```

### Production Deployment

For complete production deployment instructions including Nginx, Gunicorn, Supervisor, and SSL configuration, see:

**[📖 Installation Guide](./docs/build/html/developer/installation.html)**

---

## 📞 **Support & Contribution**

### Getting Help
- Check the [📖 SATHI Documentation](./docs/build/html/index.html)
- Open an issue on GitHub
- Contact the development team

### Contributing
See [Contributing Guide](./docs/build/html/developer/contributing.html) for:
- Development setup
- Code style guidelines
- Pull request process
- Testing requirements

### Additional Resources
Legacy technical documentation is available in the `documentation/` directory for reference, but the primary documentation is now in Sphinx format.

---

## 📄 **License**

This project is open source. See LICENSE file for details.

---

**Last Updated**: April 2026  
**Documentation Version**: 1.0

*For the most up-to-date documentation, build the Sphinx docs: `cd docs && make html`*



prom_review_construct_plot (called once per construct)
│
├─── views.py: Pre-check loop ──────────────────────────────── N queries
│    └── for each aggregation patient:
│        └── get_patient_start_date_for_aggregation()
│            └── SELECT FROM diagnosis/treatment WHERE patient=X
│
│    [if patients_with_requested_start_date > 0]
│
└─── aggregate_construct_scores_by_time_interval()
     │
     ├─ 1. patients_queryset.count()  ─────────────────────── COUNT query #1
     │      (logging line 2045)
     │
     ├─ 2. patients_queryset.prefetch_related() ──────────── 4 queries
     │      ├── SELECT * FROM patient WHERE ...
     │      ├── SELECT * FROM diagnosis WHERE patient_id IN (...)
     │      ├── SELECT * FROM diagnosis_list WHERE id IN (...)
     │      └── SELECT * FROM treatment + treatment_type WHERE ...
     │
     ├─ 3. QuestionnaireConstructScore.filter(            ─── 1 query ✅ (bulk)
     │       patient_id__in=[...], construct=X)
     │      └── SELECT all scores for this construct
     │              across ALL aggregation patients
     │
     ├─ 4. all_scores.count()  ───────────────────────────── COUNT query #2
     │      (logging line 2092)         ⚠️ RE-EXECUTES query #3!
     │
     ├─ 5. Diagnosis.objects.get(id=...) ─────────────────── 1 query
     │      OR Treatment.objects.get(id=...)   (reference obj)
     │
     ├─ 6. [in-memory loop — no queries] ✅
     │      for each patient in patients_list:
     │          _get_patient_start_date_bulk()   (uses prefetched data)
     │          filter scores from scores_by_patient dict
     │          calculate time intervals
     │
     ├─ 7. patients_queryset.count()  ───────────────────── COUNT query #3
     │      (metadata line 2303)          ⚠️ same count, third time!
     │
     └─ 8. for patient in patients_queryset:  ────────────── N+1 queries
               (non-contributing loop line 2292) ⚠️ re-fetches patients!
               └── get_patient_start_date_for_aggregation()
                   └── SELECT FROM diagnosis/treatment  (slow version)


TOTAL PER CONSTRUCT:
┌─────────────────────────────────────────────┬──────────────┐
│ Step                                        │ Queries      │
├─────────────────────────────────────────────┼──────────────┤
│ Pre-check loop (views.py)                   │ N            │
│ Patient prefetch                            │ 4            │
│ Bulk scores fetch                           │ 1 ✅          │
│ all_scores.count() (duplicate)             │ 1 ⚠️          │
│ Reference obj lookup                        │ 1            │
│ patients_queryset.count() × 2 (duplicate)  │ 2 ⚠️          │
│ Non-contributing loop re-fetch             │ 1 + N ⚠️      │
├─────────────────────────────────────────────┼──────────────┤
│ TOTAL                                       │ 10 + 2N      │
└─────────────────────────────────────────────┴──────────────┘
  where N = number of aggregation patients

With 50 aggregation patients → ~110 queries per construct
With 29 constructs → ~3,190 queries total



prom_review_construct_plot (called once per construct)
│
└─── aggregate_construct_scores_by_time_interval()
     │
     ├─ 1. patients_queryset.count()  ─────────────────────── COUNT query #1
     │
     ├─ 2. patients_queryset.prefetch_related() ──────────── 4 queries (bulk)
     │
     ├─ 3. QuestionnaireConstructScore.filter()  ─────────── 1 query (bulk)
     │
     ├─ 4. all_scores.count()  ───────────────────────────── COUNT query #2 ⚠️
     │
     ├─ 5. Reference obj lookup ──────────────────────────── 1 query
     │
     ├─ 6. [in-memory loop — 0 queries] ✅
     │
     ├─ 7. patients_queryset.count()  ───────────────────── COUNT query #3 ⚠️
     │
     └─ 8. Non-contributing loop  ────────────────────────── N+1 queries ⚠️

TOTAL: 10 + N  (down from 10 + 2N)