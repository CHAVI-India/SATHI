# Institution-Based Access Control Implementation

This document outlines the implementation of institution-based row-level security for the patient management system.

## Overview

The system now implements institution-based access control where:
- **Providers** can only see and manage patients from their own institution
- **Non-providers** (superusers, admin users) can see all patients
- **Patients** can only see their own data

## Implementation Approach

We've used **Option 1 (View-Level Filtering)** combined with **Option 4 (Mixin Approach)** for the following reasons:
- Clear and explicit behavior
- Easy to understand and debug
- Flexible for complex scenarios
- Django-native patterns
- Easy to test

## Key Components

### 1. Utility Functions (`patientapp/utils.py`)

```python
def get_user_institution(user):
    """Get the institution for the current user if they are a provider."""

def is_provider_user(user):
    """Check if the user is a provider."""

def filter_patients_by_institution(queryset, user):
    """Filter a Patient queryset based on the user's institution."""

def check_patient_access(user, patient):
    """Check if a user can access a specific patient."""

def get_accessible_patient_or_404(user, pk):
    """Get a patient by pk, ensuring the user has access to it."""
```

### 2. Institution Filter Mixin

```python
class InstitutionFilterMixin:
    """Mixin for class-based views that automatically filters Patient querysets."""
    
    def get_queryset(self):
        """Filter the queryset based on user's institution."""
        
    def get_object(self, queryset=None):
        """Get the object, ensuring the user has access to it."""
```

## Protected Views

### Function-Based Views (`patientapp/views.py`)
- ✅ `prom_review(request, pk)` - Uses `get_accessible_patient_or_404()`
- ✅ `patient_list(request)` - Uses `filter_patients_by_institution()`
- ✅ `patient_detail(request, pk)` - Uses `get_accessible_patient_or_404()`
- ✅ `patient_portal(request)` - Uses `check_patient_access()`
- ✅ `prom_review_item_search(request, pk)` - Uses `get_accessible_patient_or_404()`

### Class-Based Views (`patientapp/views.py`)
- ✅ `PatientCreateView` - Inherits `InstitutionFilterMixin`, limits institution choices
- ✅ `PatientRestrictedUpdateView` - Inherits `InstitutionFilterMixin`, enforces institution
- ✅ `DiagnosisCreateView` - Uses `get_accessible_patient_or_404()`
- ✅ `DiagnosisUpdateView` - Uses `check_patient_access()` in `get_object()`
- ✅ `TreatmentCreateView` - Uses `check_patient_access()` through diagnosis
- ✅ `TreatmentUpdateView` - Uses `check_patient_access()` in `get_object()`

### PROMAPP Views (`promapp/views.py`)
- ✅ `PatientQuestionnaireManagementView` - Uses `check_patient_access()` in `get_object()`
- ✅ `PatientQuestionnaireListView` - Inherits `InstitutionFilterMixin`

## Protected Templates

All patient-related templates now automatically respect institution filtering:
- ✅ `patient_list.html` - Shows only institution patients
- ✅ `patient_detail.html` - Protected by view-level access control
- ✅ `patient_table.html` - Shows only filtered patients
- ✅ `patient_questionnaire_management.html` - Protected by view access control
- ✅ `prom_review.html` - Protected by view access control

## Security Features

### 1. Institution Dropdown Filtering
- **Providers**: Only see their own institution in dropdowns
- **Non-providers**: See all institutions

### 2. Patient Creation
- **Providers**: Can only create patients in their institution
- **Form automatically pre-selects and locks** provider's institution

### 3. Patient Updates
- **Providers**: Cannot move patients to different institutions
- **Institution field** is automatically enforced

### 4. Error Handling
- **404 errors** for patients not in user's institution
- **PermissionDenied** exceptions with clear messages
- **Graceful fallbacks** for edge cases

## Example Usage

### For Function-Based Views
```python
def patient_detail(request, pk):
    # Automatically checks institution access and raises 404 if not allowed
    patient = get_accessible_patient_or_404(request.user, pk)
    # ... rest of view logic
```

### For Class-Based Views
```python
class PatientCreateView(InstitutionFilterMixin, LoginRequiredMixin, CreateView):
    # Automatically filters querysets and limits institution choices
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Limit institution choices for providers
        user_institution = get_user_institution(self.request.user)
        if user_institution:
            form.fields['institution'].queryset = Institution.objects.filter(id=user_institution.id)
        return form
```

## Testing

To test the implementation:

1. **Create a Provider user** with an institution
2. **Create Patients** in different institutions
3. **Login as the Provider** and verify:
   - Can only see patients from their institution
   - Cannot access patients from other institutions (404 error)
   - Can only create patients in their institution
   - Cannot move patients to other institutions

## User Types and Access

| User Type | Access Level |
|-----------|-------------|
| **Provider** | Only their institution's patients |
| **Superuser** | All patients (no restrictions) |
| **Admin/Staff** | All patients (configurable) |
| **Patient** | Only their own data |

## Security Considerations

1. **Database Level**: Queries are filtered at the Django ORM level
2. **URL Access**: Direct URL access is protected
3. **Form Submissions**: Institution assignments are enforced server-side
4. **AJAX/HTMX**: All dynamic content respects institution filtering
5. **API Access**: Would need additional protection if APIs are implemented

## Future Enhancements

1. **Audit Logging**: Track institution access attempts
2. **Multi-Institution Users**: Support users with access to multiple institutions
3. **Institution Groups**: Support hierarchical institution structures
4. **Database-Level RLS**: Consider PostgreSQL Row Level Security for additional protection 