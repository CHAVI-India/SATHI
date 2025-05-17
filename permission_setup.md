This document will collate the permission setup required for the system to function properly. This will work with the group feature provided by Django which allows users to be put into groups with specific permissions easily

# Groups to be created:

| Group Name | Group Purpose |
| ---------- | -------|
| Patients | This group will be used to provide patients with the ability to access their questionnaires |


> Note:  
> The exact group name does not matter. The permissions inside it matter.


# Permissions

## Group for Patients
1. **View** permission for **PatientQuestionnaire** Model : So that patients can view patient questionnaires available to them.
2. **Add** permission for **QuestionnaireItemResponse** Model : So that patients can add responses to questionnaires. 