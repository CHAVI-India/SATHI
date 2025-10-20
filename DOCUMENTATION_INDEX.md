# CHAVI-PROM Documentation Index

Welcome to the CHAVI-PROM (Patient Reported Outcomes Measurement) system documentation. This index provides centralized access to all project documentation organized by category.

## 📋 **Core System Documentation**

### [Main README](./README.md)
**Primary system overview and feature documentation**
- Complete feature list for patients and questionnaire designers
- Export functionality and permissions
- Construct & composite score calculations
- Translation system overview
- Installation and setup instructions

### [System Features](./system_features.md)
**Detailed feature specifications and technical notes**
- Patient questionnaire capabilities
- Audio/video integration
- Model relationships (QuestionnaireItemResponse, PatientQuestionnaire)
- Response types and data storage

### [Features to be Implemented](./features_to_be_implemented.md)
**Roadmap and planned enhancements**
- Notification system
- Patient information system
- Model-based predictions
- Documentation integration

---



---

## 👥 **User Management & Access Control**

### [Permission Setup](./permission_setup.md)
**Django groups and permissions configuration**
- Patient group permissions
- Healthcare provider access
- Questionnaire creator capabilities
- Patient registration staff roles
- Institution-based row-level security

---

## 🏥 **Patient & Clinical Features**

### [Patient Portal](./patient_portal.md)
**Patient-facing portal specifications**
- Consolidated questionnaire view
- Response tracking and visualization
- Personal health data access
- Plot generation and display

### [Result UI for HCP](./Result%20UI%20for%20HCP.md)
**Healthcare provider interface documentation**
- Clinical result viewing
- Patient data management
- Provider-specific features

---

## 🎨 **UI Components & Templates**

### [Tailwind CSS Setup](./TAILWIND_CSS_SETUP.md)
**Tailwind CSS v4 integration and build process**
- NPM setup and configuration
- Development and production workflows
- Custom styling and theming
- Troubleshooting guide

### Cotton Template Components
**Reusable UI component library documentation**

#### [Cards](./templates/cotton/README_CARDS.md)
- Card component (`c-card`) usage
- Field display component (`c-field_display`)
- Styling options and examples

#### [Buttons](./templates/cotton/README_BUTTONS.md)
- Button component variations
- Action button implementations
- Styling and interaction patterns

#### [Action Buttons](./templates/cotton/README_ACTION_BUTTONS.md)
- Specialized action button components
- Form submission buttons
- Interactive elements

#### [Dropdowns](./templates/cotton/README_DROPDOWNS.md)
- Dropdown menu components
- Selection interfaces
- Navigation dropdowns

#### [List Cards](./templates/cotton/README_LIST_CARDS.md)
- List-based card layouts
- Data presentation components
- Responsive list designs

#### [Paginator](./templates/cotton/README_PAGINATOR.md)
- Pagination component implementation
- Navigation controls
- Page size management

---

## 🏢 **Institution & Security**

### [Institution Security](./patientapp/README_INSTITUTION_SECURITY.md)
**Institution-based access control**
- Row-level security implementation
- Multi-tenant architecture
- Data isolation mechanisms

---

## 📊 **Data Integration**

### [Date Integration Guide](./DATE_INTEGRATION_GUIDE.md)
**Date handling and integration specifications**
- Date format standards
- Integration patterns
- Data consistency requirements

---

## 🔧 **Development & Maintenance**

### Environment Setup
- See main [README.md](./README.md) for installation instructions
- Security configuration in [SECURITY_REMEDIATION.md](./SECURITY_REMEDIATION.md)
- Permission setup in [permission_setup.md](./permission_setup.md)

### Monitoring & Logging
- Rate limiting logs: [RATE_LIMITING_DOCUMENTATION.md](./RATE_LIMITING_DOCUMENTATION.md)
- Security audit logs: [SECURITY_REMEDIATION.md](./SECURITY_REMEDIATION.md)
- System monitoring guidelines in respective component docs

---

## 📝 **Quick Navigation**

| Category | Key Documents |
|----------|---------------|
| **Getting Started** | [README.md](./README.md), [system_features.md](./system_features.md) |
| **Security** | [SECURITY_REMEDIATION.md](./SECURITY_REMEDIATION.md), [RATE_LIMITING_DOCUMENTATION.md](./RATE_LIMITING_DOCUMENTATION.md) |
| **User Management** | [permission_setup.md](./permission_setup.md), [patientapp/README_INSTITUTION_SECURITY.md](./patientapp/README_INSTITUTION_SECURITY.md) |
| **UI Components** | [TAILWIND_CSS_SETUP.md](./TAILWIND_CSS_SETUP.md), [templates/cotton/README_CARDS.md](./templates/cotton/README_CARDS.md), [templates/cotton/README_BUTTONS.md](./templates/cotton/README_BUTTONS.md) |
| **Patient Features** | [patient_portal.md](./patient_portal.md), [Result UI for HCP.md](./Result%20UI%20for%20HCP.md) |
| **Development** | [features_to_be_implemented.md](./features_to_be_implemented.md), [DATE_INTEGRATION_GUIDE.md](./DATE_INTEGRATION_GUIDE.md) |

---

## 📞 **Support & Contribution**

For questions about specific features or components, refer to the relevant documentation above. Each document contains detailed implementation notes, usage examples, and configuration options.

**Last Updated**: August 2025  
**System Version**: CHAVI-PROM Django Application

---

*This index is maintained to provide easy access to all project documentation. Please update this file when adding new documentation.*
