![CodeRabbit Pull Request Reviews](https://img.shields.io/coderabbit/prs/github/CHAVI-India/chavi-prom?utm_source=oss&utm_medium=github&utm_campaign=CHAVI-India%2Fchavi-prom&labelColor=171717&color=FF570A&link=https%3A%2F%2Fcoderabbit.ai&label=CodeRabbit+Reviews)

# SATHI - Self Reported Assessment and Tracking for Health Insights

Welcome to **SATHI** (Self Reported Assessment and Tracking for Health Insights). This is a comprehensive Django-based application for collecting, managing, and analyzing patient-reported outcomes with advanced features for patients, healthcare providers, and questionnaire designers.

---

## 📋 **Core System Documentation**

### [System Features Detailed](./documentation/SYSTEM_FEATURES_DETAILED.md)
**Comprehensive system overview and feature documentation**
- Complete feature list for patients and questionnaire designers
- Export functionality and permissions
- Construct & composite score calculations
- Translation system overview
- Healthcare provider interface details
- Score interpretation and aggregation

### [System Features](./documentation/system_features.md)
**Detailed feature specifications and technical notes**
- Patient questionnaire capabilities
- Audio/video integration
- Model relationships (QuestionnaireItemResponse, PatientQuestionnaire)
- Response types and data storage

### [Features to be Implemented](./documentation/features_to_be_implemented.md)
**Roadmap and planned enhancements**
- Notification system
- Patient information system
- Model-based predictions
- Documentation integration

---

## 👥 **User Management & Access Control**

### [Permission Setup](./documentation/permission_setup.md)
**Django groups and permissions configuration**
- Patient group permissions
- Healthcare provider access
- Questionnaire creator capabilities
- Patient registration staff roles
- Institution-based row-level security

### [Institution Security](./documentation/apps/README_INSTITUTION_SECURITY.md)
**Institution-based access control**
- Row-level security implementation
- Multi-tenant architecture
- Data isolation mechanisms

---

## 🏥 **Patient & Clinical Features**

### [Patient Portal](./documentation/patient_portal.md)
**Patient-facing portal specifications**
- Consolidated questionnaire view
- Response tracking and visualization
- Personal health data access
- Plot generation and display

### [Result UI for HCP](./documentation/Result%20UI%20for%20HCP.md)
**Healthcare provider interface documentation**
- Clinical result viewing
- Patient data management
- Provider-specific features

---

## 🎨 **UI Components & Templates**

### [Tailwind CSS Setup](./documentation/TAILWIND_CSS_SETUP.md)
**Tailwind CSS v4 integration and build process**
- NPM setup and configuration
- Development and production workflows
- Custom styling and theming
- Troubleshooting guide

### [Language Switching Implementation](./documentation/LANGUAGE_SWITCHING_IMPLEMENTATION.md)
**Multi-language support and language switching**
- Language selection interface
- Translation management
- User language preferences

### [Vertical Tabs Implementation](./documentation/VERTICAL_TABS_IMPLEMENTATION.md)
**Vertical tab navigation component**
- Tab component structure
- Navigation patterns
- Responsive design considerations

### Cotton Template Components
**Reusable UI component library documentation**

#### [Cards](./documentation/ui-components/README_CARDS.md)
- Card component (`c-card`) usage
- Field display component (`c-field_display`)
- Styling options and examples

#### [Buttons](./documentation/ui-components/README_BUTTONS.md)
- Button component variations
- Action button implementations
- Styling and interaction patterns

#### [Action Buttons](./documentation/ui-components/README_ACTION_BUTTONS.md)
- Specialized action button components
- Form submission buttons
- Interactive elements

#### [Dropdowns](./documentation/ui-components/README_DROPDOWNS.md)
- Dropdown menu components
- Selection interfaces
- Navigation dropdowns

#### [List Cards](./documentation/ui-components/README_LIST_CARDS.md)
- List-based card layouts
- Data presentation components
- Responsive list designs

#### [Paginator](./documentation/ui-components/README_PAGINATOR.md)
- Pagination component implementation
- Navigation controls
- Page size management

---

## 📊 **Data Integration**

### [Date Integration Guide](./documentation/DATE_INTEGRATION_GUIDE.md)
**Date handling and integration specifications**
- Date format standards
- Integration patterns
- Data consistency requirements

---

## 🔧 **Development & Maintenance**

### [Deployment Guide](./documentation/DEPLOYMENT_GUIDE.md)
**Complete production deployment documentation**
- Ubuntu server setup and configuration
- PostgreSQL database installation
- Nginx, Gunicorn, and Supervisor setup
- Tailwind CSS build integration
- SSL/TLS certificate installation
- Maintenance and troubleshooting procedures

### Environment Setup
- Installation instructions: [SYSTEM_FEATURES_DETAILED.md](./documentation/SYSTEM_FEATURES_DETAILED.md)
- Production deployment: [DEPLOYMENT_GUIDE.md](./documentation/DEPLOYMENT_GUIDE.md)
- Permission configuration: [permission_setup.md](./documentation/permission_setup.md)

---

## 📝 **Quick Navigation**

| Category | Key Documents |
|----------|---------------|
| **Getting Started** | [SYSTEM_FEATURES_DETAILED.md](./documentation/SYSTEM_FEATURES_DETAILED.md), [system_features.md](./documentation/system_features.md) |
| **User Management** | [permission_setup.md](./documentation/permission_setup.md), [README_INSTITUTION_SECURITY.md](./documentation/apps/README_INSTITUTION_SECURITY.md) |
| **UI Components** | [TAILWIND_CSS_SETUP.md](./documentation/TAILWIND_CSS_SETUP.md), [Cotton Components](./documentation/ui-components/), [VERTICAL_TABS_IMPLEMENTATION.md](./documentation/VERTICAL_TABS_IMPLEMENTATION.md) |
| **Patient Features** | [patient_portal.md](./documentation/patient_portal.md), [Result UI for HCP.md](./documentation/Result%20UI%20for%20HCP.md) |
| **Development** | [DEPLOYMENT_GUIDE.md](./documentation/DEPLOYMENT_GUIDE.md), [features_to_be_implemented.md](./documentation/features_to_be_implemented.md) |
| **Data Integration** | [DATE_INTEGRATION_GUIDE.md](./documentation/DATE_INTEGRATION_GUIDE.md) |

---

## 🚀 **Key Features Overview**

### For Patients
- Mobile-responsive questionnaire interface
- Multi-language support with dynamic font selection
- Conditional logic to reduce response burden
- Personal health data portal with visualizations
- Audio/video integration for enhanced accessibility

### For Healthcare Providers
- Comprehensive patient response dashboard
- Construct and composite score tracking
- Clinical significance indicators with color coding
- Interactive plots with normative and threshold scores
- Result aggregation across patient populations

### For Questionnaire Designers
- Role-based access control
- Item bank creation and reuse
- Flexible response types (Text, Number, Likert, Range)
- Complex scoring equations with variables and conditionals
- Translation management for multi-language support
- CSV import/export for bulk operations

### Security Features
- Encrypted patient identifiers
- Two-factor authentication (Email OTP and TOTP)
- Institution-based row-level security
- Rate limiting and reCAPTCHA protection
- Comprehensive audit logging

---

## 📞 **Support & Contribution**

For questions about specific features or components, refer to the relevant documentation above. Each document contains detailed implementation notes, usage examples, and configuration options.

**Last Updated**: October 2025  
**System Version**: SATHI Django Application

---

*This documentation index is maintained to provide easy access to all project documentation. Please update when adding new documentation.*
