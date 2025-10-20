![CodeRabbit Pull Request Reviews](https://img.shields.io/coderabbit/prs/github/CHAVI-India/chavi-prom?utm_source=oss&utm_medium=github&utm_campaign=CHAVI-India%2Fchavi-prom&labelColor=171717&color=FF570A&link=https%3A%2F%2Fcoderabbit.ai&label=CodeRabbit+Reviews)

# SATHI - System Features Detailed

**SATHI** (Self Reported Assessment and Tracking for Health Insights) is a comprehensive Django application for Patient Reported Outcomes. 

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

## Patient Portal

A patient portal is provided which can be accessed by the patients themselves. They can use this to keep track of their questionnaires, their responses and see a graphical representation of the key issues that have affected them based on the responses to the questionnaires. This allows them be participants in te system and be the beneficiaries from their own responses. 



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
14. Constructs and Items can be easily imported through the admin interface for bulk item creation. 

# Export Questionnaire Responses

The system provides functionality to export patient questionnaire responses in CSV format, which can be used for data analysis, reporting, or integration with other systems.

## Export Features

1. **Permission-Based Access**: Only users with the appropriate permissions (`promapp.view_questionnaireitemresponse`) can access the export functionality.

2. **Institution-Based Filtering**: Non-superusers can only export data for patients belonging to their institutions, ensuring data privacy and security.

3. **Flexible Export Options**:
   - Export responses for all patients for a specific questionnaire
   - Export responses for a specific patient for a specific questionnaire

4. **Data Included in Export**:
   - Patient ID (encrypted)
   - Institution name
   - Submission date and time
   - Responses for each question (text, number, likert, and range response types)

5. **CSV Format**: Data is exported in standard CSV format for easy import into spreadsheet applications or data analysis tools.

## How to Use the Export Feature

1. Navigate to the "Export Questionnaire Responses" option in the navigation menu.
2. Select the questionnaire you want to export responses for.
3. (Optional) Select a specific patient to filter responses for just that patient.
4. Click the export button to download the CSV file.

## Export Permissions

To use the export feature, users must have the following permissions:
- `promapp.view_questionnaire` - To view and select questionnaires
- `promapp.view_questionnaireitemresponse` - To view and export responses

These permissions can be assigned to user groups through the Django admin interface.

## Item Import/Export Guide

This guide explains how to format your CSV file for importing Items and their translations into the system. It is important to ensure that the construct scales exist prior to doing Item import. However as Items have a translated field, therefore the import process has been modified to accomodate the translations.

### CSV Format

The CSV file should be formatted as follows:

```csv
id,construct_scale,item_number,response_type,language_code,name,likert_response,range_response,is_required,item_missing_value,item_better_score_direction,item_threshold_score,item_minimum_clinical_important_difference,item_normative_score_mean,item_normative_score_standard_deviation,discrimination_parameter,difficulty_parameter,pseudo_guessing_parameter
550e8400-e29b-41d4-a716-446655440000,123e4567-e89b-12d3-a456-426614174000,1,Likert,en,"How are you feeling?",789e4567-e89b-12d3-a456-426614174000,,true,0,"Higher is Better",5,2,10,2,1.5,0.5,0.1
```

### Required Fields

1. `id`: UUID of the Item (required for updates, can be empty for new items)
2. `construct_scale`: UUID of the related ConstructScale
3. `item_number`: Integer number of the item in the construct scale
4. `response_type`: One of: 'Text', 'Number', 'Likert', 'Range'
5. `language_code`: Language code for the translation (e.g., 'en', 'es', 'fr')
6. `name`: The translated text for the item

### Optional Fields

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

### Translation Guidelines

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

### Example CSV Files

#### English Translation
```csv
id,construct_scale,item_number,response_type,language_code,name,likert_response,range_response,is_required
550e8400-e29b-41d4-a716-446655440000,123e4567-e89b-12d3-a456-426614174000,1,Likert,en,"How are you feeling?",789e4567-e89b-12d3-a456-426614174000,,true
660e8400-e29b-41d4-a716-446655440001,123e4567-e89b-12d3-a456-426614174000,2,Likert,en,"Rate your pain",789e4567-e89b-12d3-a456-426614174000,,true
```

#### Spanish Translation
```csv
id,construct_scale,item_number,response_type,language_code,name,likert_response,range_response,is_required
550e8400-e29b-41d4-a716-446655440000,123e4567-e89b-12d3-a456-426614174000,1,Likert,es,"¿Cómo te sientes?",789e4567-e89b-12d3-a456-426614174000,,true
660e8400-e29b-41d4-a716-446655440001,123e4567-e89b-12d3-a456-426614174000,2,Likert,es,"Califica tu dolor",789e4567-e89b-12d3-a456-426614174000,,true
```

### Import Process

1. Prepare your CSV file following the format above
2. Go to the Django admin interface
3. Navigate to Items
4. Click the "Import" button
5. Upload your CSV file
6. Review the preview
7. Confirm the import

# Construct & Composite Score calculation

Each item in the system belongs to a construct which measures a latent trait. A construct can have a single or multiple items. Answers provided to these items (aside from text based answers), can be used to calculate scores for the contructs. These scores can then be tracked in the user interface. 

Two types of scores are computed:
1. Construct score : These are directly related to the items and support complex equations
2. Composite scores : These are obtained by combining multiple construct scores. Simple addition, multiplication, average, median, mode, minimum and maximum are supported.

## Construct Scale Equations

Construct scale equations allow you to define how item responses are combined to calculate a construct score. The equation system supports a powerful syntax including arithmetic operations, functions, conditionals, and variable assignments.

### Basic Syntax

- **Question References**: Use `{qN}` to reference items (e.g., `{q1}`, `{q2}`)
- **Arithmetic Operators**: `+`, `-`, `*`, `/`, `^` (power)
- **Parentheses**: Use `()` for grouping operations
- **Multi-line Equations**: Equations can span multiple lines for better readability

### Available Functions

- `abs(x)` - Absolute value
- `min(x, y, ...)` - Minimum value
- `max(x, y, ...)` - Maximum value
- `sum(x, y, ...)` - Sum of values
- `round(x)` - Round to nearest integer
- `sqrt(x)` - Square root
- `count_available(x, y, ...)` - Count non-null values

### Conditional Logic

- **Basic if-then-else**: `if condition then value1 else value2`
- **Multiple conditions**: `if condition1 then value1 elif condition2 then value2 else value3`
- **Comparison operators**: `>`, `<`, `>=`, `<=`, `==`, `!=`
- **Logical operators**: `and`, `or`, `xor`

### Variable Assignments

Variables allow you to break complex equations into readable, maintainable steps. Use the `=` operator to assign values to variables.

**Variable Naming Rules:**
- Must start with a letter or underscore
- Can contain letters, numbers, and underscores
- Cannot use reserved keywords: `if`, `then`, `else`, `elif`, `and`, `or`, `xor`, `null`, `abs`, `min`, `max`, `sum`, `round`, `sqrt`, `count_available`

**Return Value:**
- Single assignment returns the assigned value
- Multiple statements return the value of the **last statement**
- The final line determines the construct scale score

### Equation Examples

**Simple Average:**
```
({q1} + {q2} + {q3}) / 3
```

**Using Variables:**
```
RS = {q1} + {q2} + {q3}
RS / 3
```

**Complex Scoring with Variables:**
```
total_score = sum({q1}, {q2}, {q3}, {q4})
item_count = count_available({q1}, {q2}, {q3}, {q4})
if item_count >= 3 then total_score / item_count else null
```

**Conditional Scoring:**
```
if {q1} == 1 and {q2} == 1 then 1
elif {q1} == 1 and {q2} == 2 then 2
elif {q1} == 2 and {q2} == 1 then 3
else 0
```

**Percentage Score with Variables:**
```
raw_score = sum({q1}, {q2}, {q3})
max_score = 15
(raw_score / max_score) * 100
```

**Handling Missing Data:**
```
available = count_available({q1}, {q2}, {q3}, {q4}, {q5})
total = sum({q1}, {q2}, {q3}, {q4}, {q5})
if available >= 3 then (total / available) * 5 else null
```

### Minimum Number of Items

You can specify a minimum number of items that must be answered for the score to be calculated. If fewer items are answered, the score will be `null`. This is set separately from the equation and helps ensure score validity.

### Validation

Equations are validated when saved to ensure:
- Correct syntax
- Valid question references (only questions in the construct scale)
- Proper use of functions and operators
- Variables are assigned before use
- No reserved keywords used as variable names

Validation errors provide clear, user-friendly messages to help you fix any issues.


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

## Result Aggregation
The construct score plots also display the aggregated results in addition to threhold and normative scores. Aggregated results are results obtained from other patients who have answered questionnaires with the same set of constructs. The index patient is excluded from the calculation of the  statistics. 
The display allows visualization of the following :  
1. Median with interquartile range (default)  
2. Mean with 95% confidence intervals of mean  
3. Mean with 0.5 - 2.5 standard deviations.  


Aggregated results are displayed for the construct score using dotted lines and error bars. These allow you to compare the results reported by the patient against the usual patient population. Aggregation takes into account the time interval from the date. For example, if you desired to aggregate the response data of all patients with a diagnosis of breast cancer who have received neoadjuvant chemotherapy from the date of start of neoadjuvant cheomotherapy then the system will get the data for the corresponding construct scores from patients who have a diagnosis of breast cancer AND received neoadjuvant chemotherapy as the treatment. It will then calculate the summary statistics for the scores at the time-intervals corresponding to the the index patient and display them on the plot.



Plots are created using Bokeh which allow interactivity like panning, zooming, and tooltips with the data. 


## Score Interpretation

Interpretation is provided for the construct scores : 

The focus of the interpretation is on two aspects -
1. The current score
2. Change with respect to the previous score


Clinical importance of the current score for the construct scores is determined according to the following rules:

### Direction: Higher is better

Check if normative score, standard deviation of normative score, threshold score and minimal important difference (MID) are available.

| Threshold Score | MID | Normative Score | SD of Normative Score | Interpretation |
| ------- | ------ | ------| ------ | ----- |
| Available | Available | Available | Available | Score <= threshold score by MID or more is significant |
| Available | Available | NA | NA | As above |
| Available | NA | Available | Available | Score <= normative score by 0.5SD or more is significant |
| NA | NA | Available | Avialable | Score <= normative by 0.5SD or more is significant |
| Available | NA | Available | NA | Score < threshold score (any value) is significant |
| NA | NA | Available | NA | Score < normative score (any value is significant) |
| NA | NA | NA | NA | NA |

For the last clause the construct score will not be included in the significance section. 

### Direction Lower is better

Check if normative score, standard deviation of normative score, threshold score and minimal important difference (MID) are available.

| Threshold Score | MID | Normative Score | SD of Normative Score | Interpretation |
| ------- | ------ | ------| ------ | ----- |
| Available | Available | Available | Available | Score >= threshold score by MID or more is significant |
| Available | Available | NA | NA | As above |
| Available | NA | Available | Available | Score >= normative score by 0.5SD or more is significant |
| NA | NA | Available | Avialable | Score >= normative by 0.5SD or more is significant |
| Available | NA | Available | NA | Score > threshold score (any value) is significant |
| NA | NA | Available | NA | Score > normative score (any value is significant) |
| NA | NA | NA | NA | NA |

For the last clause the construct score will not be included in the significance section. 


### Direction Middle is better 

Check if normative score, standard deviation of normative score, threshold score and minimal important difference (MID) are available.

| Threshold Score | MID | Normative Score | SD of Normative Score | Interpretation |
| ------- | ------ | ------| ------ | ----- |
| Available | Available | Available | Available | Score which is > or < threshold score by MID or more is significant |
| Available | Available | NA | NA | As above |
| Available | NA | Available | Available | Score > or < than normative score by 0.5SD or more is significant |
| NA | NA | Available | Avialable | Score > or < than normative by 0.5SD or more is significant |
| Available | NA | Available | NA | Score > or < than threshold score (any value) is significant |
| NA | NA | Available | NA | Score > or < than  normative score (any value is significant) |
| NA | NA | NA | NA | NA |

For the last clause the construct score will not be included in the significance section. 

For each of the construct score we will also determine the change with respect to a previous score if available based on the following rules

### Direction Higher is Better

If MID is available then check the difference between the current score and the previous score. If the current score is lower than the previous score by a value greater than the MID then it is clinical important. 
If SD of Normative score is available then check the difference between the current score and the previous score. If the current score is lower than the previous score by a value more than 1 SD then it is clinically important
If both of these are available the MID takes precedence. If none are available then the score change exceeding 10% (that is if current score is lower than the previous score by 10% or more) will be considered clinically important. 

### Direction Lower is Better

If MID is available then check the difference between the current score and the previous score. If the current score is higher than the previous score by a value greater than the MID then it is clinical important. 
If SD of Normative score is available then check the difference between the current score and the previous score. If the current score is higher than the previous score by a value more than 1 SD then it is clinically important
If both of these are available the MID takes precedence. If none are available then the score change exceeding 10% (that is if current score is higher than the previous score by 10% or more) will be considered clinically important. 

### Direction Middle is Better

If MID is available then check the difference between the current score and the previous score. If the current score is higher or lower than the previous score by a value greater than the MID then it is clinical important. 
If SD of Normative score is available then check the difference between the current score and the previous score. If the current score is higher or lower than the previous score by a value more than 1 SD then it is clinically important
If both of these are available the MID takes precedence. If none are available then the score change exceeding 10% (that is if current score is higher or lower than the previous score by 10% or more) will be considered clinically important. 

All construct scores which meet either the criteria for clinical importance based on current score or change from previous score or both will be grouped. Note that if a score meets both criteria it takes precedence in the order. Remaining ordering will be done alphabetically.



# Add Patient

Users can add patients to the system using a single page form and assign the questionnaires forms avaialble for them using a simple interface. Appropriate privilges and permissions are provided for this.

Users can choose to add diagnoses, and treatments for diagnoses for the patients. 

# Translations

The system allows users to add translations for questionnaires, items, and options in the Likert and Range scale options values. Media translations are also supported. Once an item is translated it can be used in multiple questionnaires. The same is true for Likert scale and Range Scale translations. 

The ability to add translations is provided for the users with appropriate permissions. 

It is possible to dynamically change the display font to one more suitable for the language and use different types of google fonts for different langugages. This allows text to be properly legible across langugages. 

# Security

Patient identifiers are securely encrypted in the database. These identifiers include name, hospital unique ID, date of registration, date of start and date of end of treatment. 
Additionally, the system supports two factor authentication with login implemented via an email based OTP. Additionally TOTP apps are also supported. It is possible to support SMS gateways in the future.



