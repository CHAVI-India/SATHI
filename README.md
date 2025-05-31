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

# Score calculation

Each item in the system belongs to a construct which measures a latent trait. A construct can have a single or multiple items. Answers provided to these items (aside from text based answers), can be used to calculate scores for the contructs. These scores can then be tracked in the user interface. 

Two types of scores are computed:
1. Construct score : These are directly related to the items and support complex equations
2. Composite scores : These are obtained by combining multiple construct scores. Simple addition, multiplication, average, median, mode, minimum and maximum are supported.


# Health care provider interface

A comprehensive healthcare provider interface is provided with the following features:
1. Each patients responses can be viewed in a single page.
2. The number of questionnaires available , the number of times each questionnaire has been answered as well as the last date of submission are shown.
3. Topline results show the score of constructs which exceed clinical threshold score or normative scores. The last submitted score is shown along with the indicator if the score has improved or worsened. Improving scores are indicated with a green color and deteriorating scores with a orange color icon. The score also shows an indicator of the direction of change. 
4. We show a plot of the scores over time. In each plot, the normative, threshold scores and standard deviations of the normative scores are shown if available. 
6. Additional scores of other constructs which do get presented in the topline results section will be shown in section below the topline results. 
7. Composite scores of the constructs will also be shown here.
8. Item wise scores are shown with plots if they are numeric, range or likert type responses. 
    - For numeric and range type responses the plot shows the value over time. 
    - For likert type responses, we show the last value along with a change indicator. The change indicator and the item value background receive a different color with darker shades indicating worse outcomes. 
    - The plot for the likert responses will also show the same color scheme. 


Plots are created using Bokeh which allow interactivity like panning, zooming, and tooltips with the data. 


# Add Patient

Users can add patients to the system using a single page form and assign the questionnaires forms avaialble for them using a simple interface. Appropriate privilges and permissions are provided for this.

Users can choose to add diagnoses, and treatments for diagnoses for the patients. 

# Translations

The system allows users to add translations for questionnaires, items, and options in the Likert and Range scale options values. Media translations are also supported. Once an item is translated it can be used in multiple questionnaires. The same is true for Likert scale and Range Scale translations. 

The ability to add translations is provided for the users with appropriate permissions. 


# Security

Patient identifies are securekly encrypted in the database. 

# Item Import/Export Guide

This guide explains how to format your CSV file for importing Items and their translations into the system.

## CSV Format

The CSV file should be formatted as follows:

```csv
id,construct_scale,item_number,response_type,language_code,name,likert_response,range_response,is_required,item_missing_value,item_better_score_direction,item_threshold_score,item_minimum_clinical_important_difference,item_normative_score_mean,item_normative_score_standard_deviation,discrimination_parameter,difficulty_parameter,pseudo_guessing_parameter
550e8400-e29b-41d4-a716-446655440000,123e4567-e89b-12d3-a456-426614174000,1,Likert,en,"How are you feeling?",789e4567-e89b-12d3-a456-426614174000,,true,0,"Higher is Better",5,2,10,2,1.5,0.5,0.1
```

## Required Fields

1. `id`: UUID of the Item (required for updates, can be empty for new items)
2. `construct_scale`: UUID of the related ConstructScale
3. `item_number`: Integer number of the item in the construct scale
4. `response_type`: One of: 'Text', 'Number', 'Likert', 'Range'
5. `language_code`: Language code for the translation (e.g., 'en', 'es', 'fr')
6. `name`: The translated text for the item

## Optional Fields

7. `likert_response`: UUID of the LikertScale (required if response_type is 'Likert')
8. `range_response`: UUID of the RangeScale (required if response_type is 'Range')
9. `is_required`: Boolean (true/false)
10. `item_missing_value`: Decimal value for missing responses
11. `item_better_score_direction`: One of: 'Higher is Better', 'Lower is Better', 'Middle is Better', 'No Direction'
12. `item_threshold_score`: Decimal value
13. `item_minimum_clinical_important_difference`: Decimal value
14. `item_normative_score_mean`: Decimal value
15. `item_normative_score_standard_deviation`: Decimal value
16. `discrimination_parameter`: Float value
17. `difficulty_parameter`: Float value
18. `pseudo_guessing_parameter`: Float value

## Translation Guidelines

1. **One Language Per Import**
   - Each CSV file should contain translations for only one language
   - The `language_code` column should have the same value for all rows
   - Example: All rows should have `language_code=en` for English translations

2. **Multiple Languages**
   - To import multiple languages, create separate CSV files for each language
   - Use the same `id` values across files to link translations to the same Item
   - Example:
     ```csv
     # english.csv
     id,...,language_code,name
     550e8400-e29b-41d4-a716-446655440000,...,en,"How are you feeling?"

     # spanish.csv
     id,...,language_code,name
     550e8400-e29b-41d4-a716-446655440000,...,es,"¿Cómo te sientes?"
     ```

3. **Translation Updates**
   - To update an existing translation, use the same `id` and `language_code`
   - The system will update the existing translation rather than creating a new one

## Response Type Requirements

1. **Likert Response**
   - If `response_type` is 'Likert', `likert_response` must be provided
   - `range_response` should be empty

2. **Range Response**
   - If `response_type` is 'Range', `range_response` must be provided
   - `likert_response` should be empty

3. **Text/Number Response**
   - If `response_type` is 'Text' or 'Number', both `likert_response` and `range_response` should be empty

## Example CSV Files

### English Translation
```csv
id,construct_scale,item_number,response_type,language_code,name,likert_response,range_response,is_required
550e8400-e29b-41d4-a716-446655440000,123e4567-e89b-12d3-a456-426614174000,1,Likert,en,"How are you feeling?",789e4567-e89b-12d3-a456-426614174000,,true
660e8400-e29b-41d4-a716-446655440001,123e4567-e89b-12d3-a456-426614174000,2,Likert,en,"Rate your pain",789e4567-e89b-12d3-a456-426614174000,,true
```

### Spanish Translation
```csv
id,construct_scale,item_number,response_type,language_code,name,likert_response,range_response,is_required
550e8400-e29b-41d4-a716-446655440000,123e4567-e89b-12d3-a456-426614174000,1,Likert,es,"¿Cómo te sientes?",789e4567-e89b-12d3-a456-426614174000,,true
660e8400-e29b-41d4-a716-446655440001,123e4567-e89b-12d3-a456-426614174000,2,Likert,es,"Califica tu dolor",789e4567-e89b-12d3-a456-426614174000,,true
```

## Import Process

1. Prepare your CSV file following the format above
2. Go to the Django admin interface
3. Navigate to Items
4. Click the "Import" button
5. Upload your CSV file
6. Review the preview
7. Confirm the import

## Troubleshooting

1. **Missing Required Fields**
   - Ensure all required fields are present in your CSV
   - Check that the `language_code` is valid

2. **Invalid UUIDs**
   - Verify that all UUIDs (id, construct_scale, likert_response, range_response) are valid
   - Check that referenced objects exist in the database

3. **Response Type Mismatch**
   - Ensure the correct response fields are provided for each response type
   - Check that likert_response is provided for Likert items
   - Check that range_response is provided for Range items

4. **Translation Issues**
   - Verify that the language_code is consistent throughout the file
   - Check that the name field contains the translated text
   - Ensure the id matches the item you want to translate