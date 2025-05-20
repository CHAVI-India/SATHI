This is the new Django application for Patient Reported outcomes. 

The following features are provided:

# Patients

Patients can log into the system using an username and password and can see all the questionnaires they have to answer.

1. Questionnaires are displayed with a clear indicator of which questionnaire is to be answered first.  
2. All questionnaires can be translated into native language of the patient.  
3. Questionnaires can be answered on the mobile device of choice and the system will automatically fit to the display using a responsive layout.  
4. Each question is displayed one at a time.   
5. To reduce response burden, conditional logic can be implemented to ensure that the patients can skip questions based on the responses they provide to the previous questions. Currently this system is based on rules and rule groups which need to be provided by the questionnaire designer.  
6. As this is a patient reported questionnaire system to preserve patient autonomy no question is required to be answered in a questionnaire. The patient may choose to answer only those questions they desire.  
7. Questionnaires are displayed with large fonts and for Likert responses, we display buttons with clear text. Additionally media can be integrated inside the buttons if required.   
8. It is possible to configure a minimum time interval between responses to the same questionnaire preventing spurious submissions.   
9. Permission based access to the page where users can access questionnaires.   

# Questionnaire designers

For designers of questionnaires the following features are provided:  
1. Role based access control for setting up questionnaires. 
2. Translation for questionnaire text.
3. Ability to add media elements like audio / video with the questionnaire. 
4. Ability to add multiple items to each questionnaire and reuse items between questionnaires. This enables users to create item banks. 
5. Link items to constructs or scales which measure the underlying latent trait. 
6. Flexible option types:
    - Plain text
    - Numbers
    - Likert responses
    - Range based selection
7. Option types can be used between questionnaires. 
8. Ability to add specific questionnaires for specific patients. 
9. Ability to specify rules to display questions in the questionnaire. These rules can be grouped so that they can evaluated independantly. 
10. Ability to flexibly rearrange items in the questionnaire and change the response type. 
11. Automatic conversion into the patient facing questionnaire form without any coding. 
12. Specify parameters like the time interval between successive responses to the questionnaire and redirection options. 
13. Assigned questionnaires are immediately displayed to the patient.

# Add Patient

Users can add patients to the system using a single page form and assign the questionnaires forms avaialble for them using a simple interface. Appropriate privilges and permissions are provided for this.

Users can choose to add diagnoses, and treatments for diagnoses for the patients. 

# Translations
The system allows users to add translations for questionnaires, items, and options in the Likert and Range scale options values. Media translations are also supported. Once an item is translated it can be used in multiple questionnaires. The same is true for Likert scale and Range Scale translations. 

The ability to add translations is provided for the users with appropriate permissions. 


# Security

Patient identifies are securekly encrypted in the database. 