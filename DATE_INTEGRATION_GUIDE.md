# Date Integration Guide for Patient App

This guide explains how to integrate new date fields into the existing date reference system used for time interval calculations in patient outcome reporting (PROM) analysis.

## Overview

The patient app uses a flexible date reference system that allows users to select different starting points for calculating time intervals in PROM data visualization. This system is implemented in [`patientapp/utils.py`](patientapp/utils.py) and used throughout the application for plotting and analysis.

## Current Date Reference System

### Existing Date Types

The system currently supports three types of date references:

1. **Patient Registration Date** (`date_of_registration`)
   - Field: [`Patient.date_of_registration`](patientapp/models.py:43)
   - Reference key: `'date_of_registration'`

2. **Diagnosis Dates** (`date_of_diagnosis_<id>`)
   - Field: [`Diagnosis.date_of_diagnosis`](patientapp/models.py:84)
   - Reference key pattern: `'date_of_diagnosis_{diagnosis.id}'`

3. **Treatment Start Dates** (`date_of_start_of_treatment_<id>`)
   - Field: [`Treatment.date_of_start_of_treatment`](patientapp/models.py:128)
   - Reference key pattern: `'date_of_start_of_treatment_{treatment.id}'`

### Key Functions

The date reference system is implemented through two main functions:

1. **[`get_patient_available_start_dates(patient)`](patientapp/utils.py:19-67)**
   - Collects all available date references for a patient
   - Returns list of tuples: `(reference_key, display_name, date_value)`

2. **[`get_patient_start_date(patient, start_date_reference)`](patientapp/utils.py:69-101)**
   - Retrieves the actual date value for a given reference key
   - Handles parsing of reference keys and database lookups

## Adding New Date Fields to Existing Models

### Step 1: Add the Date Field to Your Model

Add your new date field to the existing model:

```python
# In patientapp/models.py
class Treatment(models.Model):
    # ... existing fields ...
    date_of_start_of_treatment = models.DateField(null=True, blank=True)
    date_of_end_of_treatment = models.DateField(null=True, blank=True)
    
    # NEW: Add your new date field
    date_of_follow_up = models.DateField(null=True, blank=True, verbose_name="Date of Follow-up")
```

### Step 2: Update `get_patient_available_start_dates()`

Add logic to collect your new date field in [`get_patient_available_start_dates()`](patientapp/utils.py:19-67):

```python
def get_patient_available_start_dates(patient):
    """Get all available start dates for a patient."""
    available_dates = []
    
    try:
        # ... existing code for registration and diagnosis dates ...
        
        # Add all treatment start dates AND follow-up dates
        for diagnosis in patient.diagnosis_set.all():
            diagnosis_name = diagnosis.diagnosis.diagnosis if diagnosis.diagnosis else "Unknown Diagnosis"
            treatments = diagnosis.treatment_set.filter(
                models.Q(date_of_start_of_treatment__isnull=False) | 
                models.Q(date_of_follow_up__isnull=False)  # NEW: Include follow-up dates
            ).order_by('date_of_start_of_treatment')
            
            for i, treatment in enumerate(treatments):
                treatment_types = ", ".join([tt.treatment_type for tt in treatment.treatment_type.all()]) if treatment.treatment_type.exists() else f"Treatment {i+1}"
                
                # Existing start date logic
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
        logger.error(f"Error getting available start dates for patient {patient.id}: {e}")
    
    return available_dates
```

### Step 3: Update `get_patient_start_date()`

Add handling for your new reference key pattern in [`get_patient_start_date()`](patientapp/utils.py:69-101):

```python
def get_patient_start_date(patient, start_date_reference='date_of_registration'):
    """Get the start date for a patient based on the reference type."""
    try:
        if start_date_reference == 'date_of_registration':
            return patient.date_of_registration
        elif start_date_reference.startswith('date_of_diagnosis_'):
            # ... existing diagnosis logic ...
        elif start_date_reference.startswith('date_of_start_of_treatment_'):
            # ... existing treatment start logic ...
        elif start_date_reference.startswith('date_of_follow_up_'):  # NEW
            # Extract treatment ID from reference
            treatment_id = start_date_reference.replace('date_of_follow_up_', '')
            # Find treatment across all diagnoses
            for diagnosis in patient.diagnosis_set.all():
                treatment = diagnosis.treatment_set.filter(
                    id=treatment_id, 
                    date_of_follow_up__isnull=False
                ).first()
                if treatment:
                    return treatment.date_of_follow_up
            return None
        else:
            # Fallback to registration date
            return patient.date_of_registration
    except Exception as e:
        logger.error(f"Error getting start date for patient {patient.id}: {e}")
        return None
```

## Adding New Models with Date Fields

### Step 1: Create Your New Model

Create a new model with date fields and proper relationships:

```python
# In patientapp/models.py
class Surgery(models.Model):
    """Surgery model for tracking surgical procedures."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)  # Direct patient relationship
    # OR
    diagnosis = models.ForeignKey(Diagnosis, on_delete=models.CASCADE)  # Through diagnosis
    
    surgery_type = models.CharField(max_length=255, null=True, blank=True)
    date_of_surgery = models.DateField(null=True, blank=True, verbose_name="Date of Surgery")
    date_of_recovery = models.DateField(null=True, blank=True, verbose_name="Date of Recovery")
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_date']
        verbose_name = 'Surgery'
        verbose_name_plural = 'Surgeries'

    def __str__(self):
        return f"{self.surgery_type} - {self.patient.name if self.patient else 'Unknown Patient'}"
```

### Step 2: Update `get_patient_available_start_dates()`

Add logic to collect dates from your new model:

```python
def get_patient_available_start_dates(patient):
    """Get all available start dates for a patient."""
    available_dates = []
    
    try:
        # ... existing code for registration, diagnosis, and treatment dates ...
        
        # NEW: Add all surgery dates
        surgeries = patient.surgery_set.filter(
            models.Q(date_of_surgery__isnull=False) | 
            models.Q(date_of_recovery__isnull=False)
        ).order_by('date_of_surgery')
        
        for i, surgery in enumerate(surgeries):
            surgery_name = surgery.surgery_type or f"Surgery {i+1}"
            
            # Add surgery date
            if surgery.date_of_surgery:
                available_dates.append((
                    f'date_of_surgery_{surgery.id}',
                    f'Date of Surgery: {surgery_name}',
                    surgery.date_of_surgery
                ))
            
            # Add recovery date
            if surgery.date_of_recovery:
                available_dates.append((
                    f'date_of_recovery_{surgery.id}',
                    f'Recovery Date: {surgery_name}',
                    surgery.date_of_recovery
                ))
        
        # Sort by date
        available_dates.sort(key=lambda x: x[2])
        
    except Exception as e:
        logger.error(f"Error getting available start dates for patient {patient.id}: {e}")
    
    return available_dates
```

### Step 3: Update `get_patient_start_date()`

Add handling for your new model's reference keys:

```python
def get_patient_start_date(patient, start_date_reference='date_of_registration'):
    """Get the start date for a patient based on the reference type."""
    try:
        # ... existing logic for registration, diagnosis, and treatment ...
        
        elif start_date_reference.startswith('date_of_surgery_'):  # NEW
            # Extract surgery ID from reference
            surgery_id = start_date_reference.replace('date_of_surgery_', '')
            surgery = patient.surgery_set.filter(
                id=surgery_id, 
                date_of_surgery__isnull=False
            ).first()
            return surgery.date_of_surgery if surgery else None
            
        elif start_date_reference.startswith('date_of_recovery_'):  # NEW
            # Extract surgery ID from reference
            surgery_id = start_date_reference.replace('date_of_recovery_', '')
            surgery = patient.surgery_set.filter(
                id=surgery_id, 
                date_of_recovery__isnull=False
            ).first()
            return surgery.date_of_recovery if surgery else None
            
        else:
            # Fallback to registration date
            return patient.date_of_registration
    except Exception as e:
        logger.error(f"Error getting start date for patient {patient.id}: {e}")
        return None
```

## Important Considerations

### 1. Database Migrations

After adding new date fields, create and run migrations:

```bash
python manage.py makemigrations patientapp
python manage.py migrate
```

### 2. Null Value Handling

Always use `__isnull=False` filters when querying date fields to ensure only records with valid dates are included:

```python
# Good
diagnosis = patient.diagnosis_set.filter(id=diagnosis_id, date_of_diagnosis__isnull=False).first()

# Bad - might include records with null dates
diagnosis = patient.diagnosis_set.filter(id=diagnosis_id).first()
```

### 3. Reference Key Naming Convention

Follow the established naming pattern for reference keys:

- Pattern: `{field_name}_{record_id}`
- Examples: 
  - `date_of_diagnosis_123e4567-e89b-12d3-a456-426614174000`
  - `date_of_surgery_987fcdeb-51a2-43d7-8f9e-123456789abc`

### 4. Display Names

Provide meaningful display names that help users understand what each date represents:

```python
# Good - descriptive and contextual
f'Start of Treatment: {treatment_types} ({diagnosis_name})'
f'Follow-up: {treatment_types} ({diagnosis_name})'

# Bad - too generic
f'Treatment Date {treatment.id}'
```

### 5. Error Handling

Always wrap database operations in try-catch blocks and log errors appropriately:

```python
try:
    # Database operations
    pass
except Exception as e:
    logger.error(f"Error getting start date for patient {patient.id}: {e}")
    return None
```

### 6. Performance Considerations

- Use `select_related()` and `prefetch_related()` for efficient database queries
- Consider adding database indexes for frequently queried date fields
- Use `Q` objects for complex filtering conditions

### 7. Testing

After implementing new date fields, test:

1. Date collection in [`get_patient_available_start_dates()`](patientapp/utils.py:19-67)
2. Date retrieval in [`get_patient_start_date()`](patientapp/utils.py:69-101)
3. Time interval calculations with new reference dates
4. PROM visualization with different start date references

## Usage in Views

The date reference system is used in [`patientapp/views.py`](patientapp/views.py) in the [`prom_review()`](patientapp/views.py:24-456) function:

```python
# Get available start dates for this patient
available_start_dates = get_patient_available_start_dates(patient)

# Get the actual start date for calculations
start_date = get_patient_start_date(patient, start_date_reference)

# Use in filtering and plotting
if start_date:
    filtered_responses = filter_positive_intervals(historical_responses, start_date, time_interval)
```

## Summary

To integrate new date fields:

1. **Add the date field** to your model with proper null handling
2. **Update `get_patient_available_start_dates()`** to collect your new dates
3. **Update `get_patient_start_date()`** to handle your new reference key patterns
4. **Follow naming conventions** for reference keys and display names
5. **Test thoroughly** to ensure proper integration with the existing system

The system is designed to be extensible, so adding new date types should be straightforward by following these patterns.