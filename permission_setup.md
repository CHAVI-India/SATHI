This document will collate the permission setup required for the system to function properly. This will work with the group feature provided by Django which allows users to be put into groups with specific permissions easily

# Groups to be created:

| Group Name | Group Purpose |
| ---------- | -------|
| Patients | This group will be used to provide patients with the ability to access their questionnaires |
| Questionnaire Creators | This group will be used to provide capability to add new questionnaires and modify existing ones |
| Healthcare Providers | This group will be used to provide healthcare providers with the ability to view and manage patients within their institution |
| Patient Registration Staff | This group will be used to provide staff with the ability to register new patients and manage patient information |


> Note:  
> The exact group name does not matter. The permissions inside it matter.


# Permissions

## Group for Patients
1. **View** permission for **PatientQuestionnaire** Model : So that patients can view patient questionnaires available to them.
2. **Add** permission for **QuestionnaireItemResponse** Model : So that patients can add responses to questionnaires. 
3. **Add** permission for **QuestionnaireSubmission** Model: So that patients can add a new submission for their questionnaires


## Group for Healthcare Providers

This group is designed for healthcare providers (doctors, nurses, clinicians) who need to view and manage patients within their institution. The system implements institution-based row-level security, ensuring providers can only access patients from their own institution.

1. **View** permission for **Patient** Model: So that providers can view patient information and access patient lists.
2. **View** permission for **PatientQuestionnaire** Model: So that providers can see which questionnaires are assigned to patients.
3. **Add** permission for **PatientQuestionnaire** Model: So that providers can assign questionnaires to patients.
4. **View** permission for **QuestionnaireItemResponse** Model: So that providers can review patient responses to questionnaires.
5. **View** permission for **QuestionnaireSubmission** Model: So that providers can see completed questionnaire submissions.

### Additional Permissions (Optional - based on provider role):
6. **Add** permission for **Diagnosis** Model: For providers who need to add diagnoses to patients.
7. **Change** permission for **Diagnosis** Model: For providers who need to update patient diagnoses.
8. **Add** permission for **Treatment** Model: For providers who need to add treatments to patient diagnoses.
9. **Change** permission for **Treatment** Model: For providers who need to update patient treatments.

### Security Notes:
- **Institution-based Access Control**: Providers can only view/manage patients from their own institution. This is enforced at the view level using custom utility functions.
- **No Delete Permissions**: Delete permissions are intentionally not included for data integrity and audit trail purposes.
- **Provider Profile Required**: Users must have a Provider profile linked to an Institution to access patient data.
- **Patient Portal Exclusion**: Providers should NOT be given access to the patient portal - this is reserved for patients to view their own data only.


## Group for Patient Registration Staff

This group is designed for administrative staff responsible for patient registration, admission, and patient data management. These users typically work at the front desk, admissions department, or patient registration areas.

### Core Permissions:
1. **View** permission for **Patient** Model: So that registration staff can view existing patient information and check for duplicates.
2. **Add** permission for **Patient** Model: So that registration staff can register new patients in the system.
3. **Change** permission for **Patient** Model: So that registration staff can update patient information when needed.
4. **View** permission for **Institution** Model: So that registration staff can see available institutions when registering patients.

### Additional Permissions (Optional - based on role scope):
5. **Add** permission for **Diagnosis** Model: For registration staff who also handle initial diagnosis entry.
6. **Change** permission for **Diagnosis** Model: For registration staff who need to update diagnosis information.
7. **View** permission for **DiagnosisList** Model: So that registration staff can see available diagnoses when adding them.
8. **View** permission for **TreatmentType** Model: So that registration staff can see available treatment types if they handle treatment data.

### Security Notes:
- **Institution-based Access Control**: Registration staff can only register patients for their own institution (same institution-based filtering applies).
- **No Questionnaire Access**: Registration staff typically don't need access to questionnaire management or patient responses.
- **No Delete Permissions**: Delete permissions are intentionally not included for data integrity and audit trail purposes.
- **Limited Clinical Data**: Access to clinical data (responses, questionnaires) should be limited unless specifically required for their role.


## Group for Questionnaire creators  

1. **View**, **Add** and **Change** permissions for **Questionnaire** Model: So that new questionnaires can be added.  
2. **View**, **Add** and **Change** permissions for **Item** Model: So that new items can be added.  
3. **View**, **Add** and **Change** permissions for **LikertScaleResponse** Model: So that new Likert Scales can be added.   
4. **View**, **Add** and **Change** permissions for **LikertScaleResponseOptions** Model: So that new Likert Scales Response Options can be added. 
5. **View**, **Add** and **Change** permissions for **RangeScale** Model: So that new Range Scales can be added. 
6. **View**, **Add** and **Change** permissions for **ConstructScale** Model: So that new Construct Scales can be added. 
7. **View**, **Add** and **Change** permissions for **QuestionaireItem** Model: So that items can be added to questionnaires. 

> Note:
> Delete options are not recommended except for higher privilged users. If desired another similiar group can be considered with delete privileges

> Important:
> These permissions also allow users to add translations to the created items. 


# Implementation Notes

## Institution-Based Security
The system implements institution-based row-level security for patient data:
- **Automatic Filtering**: Views automatically filter patient data based on the provider's institution
- **Access Control Utilities**: Custom utility functions in `patientapp/utils.py` handle institution-based filtering
- **Permission Decorators**: Function-based views use `@permission_required` decorators
- **Mixin Classes**: Class-based views use `InstitutionFilterMixin` for consistent filtering

## UI Permission Checks
The user interface respects permissions:
- **Navbar Links**: Patient-related links only show for users with `patientapp.view_patient` permission
- **Action Buttons**: Buttons like "Manage Questionnaires" require both patient view and questionnaire management permissions
- **Template Guards**: All patient-related functionality is wrapped in permission checks

## Testing Permissions
To test the permission system:
1. Create users without any permissions - they should not see patient-related links or pages
2. Create providers with different institution assignments - they should only see their institution's patients
3. Create patients - they should only access their own data through the patient portal
4. Create registration staff - they should be able to add/edit patients but not access questionnaire data
5. Test institution-based filtering - users should only see patients from their assigned institution


