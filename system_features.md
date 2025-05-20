1. Patients can answer PROM questionnaires in their own language
2. Patients can see PROM questions with audio/video question
3. Patients will be guided on which questionnaires they can answer and the order.
3. Patients can see a patient portal like view of the answer summary for PRO questions with a secure login
4. Doctors can see patient answers belonging to their institute
5. PROM questionnaires can be tailored for diagnoses and other attributes.
6. Application to be distributed locally installable on a server in premises.
7. Users can select PRO Questions for their PROM questionnaire
8. Integrates with voice based chatbots
9. Use computerised adaptive testing as well as standard questionnaire



Notes:
Use parler instead of django-modeltranslation module as when the migrations are created in the development environment they have all the translations in the git repository making it difficult to change languages at the local level. In case of parler, the translations are saved in a seperate table which makes it easy to migrate as seperate languages can be translated by simply adding the codes to the setting



QuestionnaireItemResponse Model & PatientQuestionnaire Model
The QuestionnaireItemResponse stores the response of individual patients for questions (items) in a questionnaire. 
The model has a FK relationship to teh PatientQuestionnaire model which in turn is a M2M field betwen Patient and Questionnaire.
Each questionnaire has multiple items and items can be of the following types:
    1. Text
    2. Number
    3. Range
    4. Likert

We would like to store the response provided by the patient in the corresponding fields. 
The patients will see the items in the questionnaire based on the question_number field order. For each item they will be the text of the question and any media associated with it (fields - name and media). Under the question they will see the widget corresponding to the response_type. 
If it is a text response then there will be a text field and the data entred will be saved into the field called response_value
If it is a number response then there will be a number field and the data will be saved into the field called response_value
If it is a likert response then the user will see buttons corresponding to the likert response options (the fields called option_text and option_media ) need to displayed. The buttons should be styled such that the active button is bright blue colored and inactive buttons are white. The selected value (option_value) will be saved in the field called response_value
If it is a range option then a slider is to be provided with minimum and maximum values along with the increment.  Selected value will be stored in the field called response_value.


# Adding a new language translation

> Requirements
> gettext needs to be installed. Easy to do in linux. Windows is a bit involved see here : https://gnuwin32.sourceforge.net/packages/gettext.htm

1. Step 1 is to add the language code and string to the .env file (see sampleenv.txt for examples)
2. Reload the server to check the language is properly recognized. 
3. Run the command 
```bash
python manage.py makemessages -l bn -i "venv"

```

In this the -l bn refers to the language we want to the translation to appear in in this case bengali
The -i "venv" part means we are ignoring the python libraries which do not need to be translated else it will show a large translation file with all messages to be translated from installed packages.

4. Compile messages
```bash
django-admin compilemessages -i "venv"
```
Again -i "venv" basically allows us to ignore the venv directory