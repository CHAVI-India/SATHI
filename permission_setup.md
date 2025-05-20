This document will collate the permission setup required for the system to function properly. This will work with the group feature provided by Django which allows users to be put into groups with specific permissions easily

# Groups to be created:

| Group Name | Group Purpose |
| ---------- | -------|
| Patients | This group will be used to provide patients with the ability to access their questionnaires |
| Questionnaire Creators | This group will be used to provide capability to add new questionnaires and modify existing ones |


> Note:  
> The exact group name does not matter. The permissions inside it matter.


# Permissions

## Group for Patients
1. **View** permission for **PatientQuestionnaire** Model : So that patients can view patient questionnaires available to them.
2. **Add** permission for **QuestionnaireItemResponse** Model : So that patients can add responses to questionnaires. 


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


