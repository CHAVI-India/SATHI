The objective of the page is to provide healthcare providers with a quick birds eye view of the patient reported outcomes. 

Key models for the page:
1. QuestionnaireConstructScore: This provides the scores for the various constructs included in the items. We will leverage the information in Construct Scale model to make the visualization better.
2. QuestionnaireItemResponse: This provides the responses to the individual items in the questionnaire. Data for the visualization will be obtained from the following models:
    - Item : Score and direction information for the item
    - Likert Scale and Likert Scale Response elements for the actual values
    - Range Scale for the actual values.

3. QuestionnaireSubmission: This tracks the Submission made by the same patient for the same questionnaire over a period of time (Submission date field)


Page display:
The page will be called PRO Review
**Template**: `templates/promapp/prom_review.html`

## Filtering 

Global filters will be provided which allow users to filter the list by the following 
1. Date of submission which will allow the users to select a date upto which the responses will be shown. Responses upto the date or before it will be shown after selection.
2. Questionnaire name (related to the questionnaires assigned to the patient)
3. Item names (These are reflective of the items available in questionnaires for the patient)

4. Addtionally, the user can choose to display results of a configurable number of responses in the plots. 

Note that the default display will show responses related to all questionnaires focussed on the last submission by default. 
## Time Analysis

The system allows users to designate a date from which the plots data display will be done. Default is the date of Registration. However, other dates related to diagnosis and treatment initiation are also available. 

For each date the user can configure the time interval to be shown (i.e. time between the selected date and the date of the last submission). 

This setting is also used to calculate the aggregation setting. 

## Patient information 

This shows the patient name, id, age, gender and date of registration. Additionally all available diagnoses and their treatments are shown in an hierarchical list. 

## Questionnaire Overview 

This shows the questionnaires available for the patient, number of responses to each questionnaire and the date of last response for each questionnaire.

## Topline results


This shows the key construct scores which need attention. The rules used to determine placement in the Topline results section are as follows:

1. If the construct score has a threshold score designated (clinical threshold score) and the direction which indicates a better / desirable score then the construct will appear in the topline section if the score is higher than the threshold (when a lower score is better) or vice-versa. 
2. If the threshold score is not specified but the normative score is specified with the standard deviation then anything above 1/2 the standard deviation above or below the normative score as per the direction.  
3. If the threshold score is not specified but the normative score is specified with the standard deviation then anything above 1/2 the standard deviation above or below the normative score as per the direction.
4. If both threshold & normative scores are available then threshold scores will be given importance. 

If these scores are not available then the construct score will not appear in the topline results. Note that as the system computes these rules dynamically, if threshold or normative score data is made available at a later stage then the displays will be modified automatically. 

The change in the direction of the score w.r.t to the previous assessment is shown with an arrow. This color is marked with red if the change is deterimental (determined by the relationship above) or green if the change is beneficial. 

A line plot is shown with the last 5 values by default. X axis shows the time in weeks from the start date (can be defined by the observer) Y axis shows the score value. Addtionally we indicate the threshold and normative score values if available (orange and blue color). If standard deviation of the normative score is available then it will be shown as a band with light blue color around the normative score. 

# Other construct scores

This section shows the construct scores for the patient which are not shown in the Topline results. The display indicates the actual score, the direction of change w.r.t to the previous score (if available) and the type of change (deterimental indicated with a red color and improvment indicated with a green color). Additionally it shows the number of items answered for the construct score and if the construct score is withing the the threshold. Finally a arrow indicator is provided with indicates if a higher score is better or vice versa. 

## Composite Construct score

If defined then composite construct scores are shown here. Unlike construct scores, composite scores do not have clinical thresholds and normative values defined. However the number of constructs involved in the composite is shown. 

## Item wise results. 

This section shows the results for each item. 
The display for the item will be different based on the type of response:

| Response Type | Display |
| ----- | ----- |
| Text | For this the entire text needs to be shown inside a wide card element. A paginator at the bottom will allow users to navigate to the previous text|
| Numeric | For this the actual numeric value needs to be presented. As per the display we have adopted for the topline results where the construct scale. See details below |
| Likert | The actual option text value will need to be presented. A color visualation will be done based on the direction and number of items |
| Range | For this the actual numeric value will be presented. Display will be as per the Numeric items |

## Text Option
For text items we do not need any specific visualization as noted above. However we may want to get the important concepts from the text later on. This will be implemented later.


## Numeric and Range options
For Numeric and Range options which are numeric the display will be similiar to the construct scale


 
The scores will be shown in a card component where the score of the latest submission shall be shown prominently on the left (1/2 of the space). Each item in the construct will be represented in a card of its own and two items will be shown in the same row for wide displays. Below this score the change with respect to the previous score will be shown with an arrow indicating increase or decrease (orange arrow up for increase or decrease based on the direction, green arrow down for decrease or increase based on the direction, orange horizontal bar for no change) if a prior score is available. orange arrow will indicate worsening and green arrow will indicate improvement. Note that if the direction is not specified then only the previous score will be shown. 


If the previous submission had a missing score for the item same will be shown as -NA-.

The remaining half of the space will be occupied by interactive line plots for each item arranged in the same order as the cards. Again 2 plots for each row in wide displays. Plots will have Y axis as the value and x axis as the submission date. To save space the submission date will be common for all plots here. Number of submissions for visualization will be controlled by the widget noted in the topline results section for all plots. Threshold scores and normatives scores will be depicted using the orange and blue lines respectively. If standard deviation of the normaitve score is present for the item then a semi-transparent lighter hue of blue will be used to depict this.



## Likert Response

For likert responses, the display will include a card component on the left occupying half of the space. Inside this two items will be displayed side by side in the same row in wider displays. For each item the response text will be shown coloorange with a color based on the value. The color will correpsond to the option_value. To ensure consistency a seqauential color palette will be used. Depending on the direction for the item higher option values will have darker or lighter hues. The number of hues will correspond to the number of options for the Likert range. Thus the hue and the text both will be shown together. 

**Component**: `LikertItemCard`
**Template**: `templates/promapp/components/likert_item_card.html`
**Layout**: Two items per row on wide displays, left half (1/2) for response text with color coding, right half (1/2) for plot
**Color Coding**: Sequential palette based on option_value, direction-aware hue intensity

The right half will be occupied by interactive line plots. Line plots will have the Y axis values as the values for the likert response (option_text). The same control for submission date will apply. The background of the plot will be coloorange with a transparent version of the hue corresponding to the option value as used in the card component. 

**Plotting**: Bokeh line plots with Y-axis showing option_text, transparent viridis palette background, controlled by `SubmissionControlWidget`

If threshold and normative values are provided for the item then they will be displayed with orange and blue lines. Standard deviation will be ignoorange. 


# Plot guidelines
All line plots will have similiar color convention 
1. Light gray grid (`#e5e7eb`)
2. Bright orange color indicating threshold score (`#f97316`)
3. Navy Blue color indicating normative value (`#1e3a8a`)
4. semitransparent navy blue band indicating 1 standard deviation (excpet when likert scale plots are being shown)
5. Black bold line for the plot (`#000000`)
6. White background (`#ffffff`)
7. For likert scale plots the background hues will be built using the viridis palette but will have a transaprecy such that the line is visible at all times.  

**Shared Components**:
- `PlotContainer` (wrapper for all Bokeh plots with consistent styling)
- `ChangeIndicator` (reusable arrow logic for all score changes)

**Standard Bokeh plot Features**:
- Responsive design
- Print-friendly rendering
- Hover tooltips with exact values
- Zoom/Pan capabilities
- Missing data shown as gaps with 'X' markers

Interactivity:
1. Show values when hovered over the line. 

**HTMX Integration Points**:
- Submission date changes update all plots and scores
- Submission count widget adjusts plot data range  
- Fieldset toggles show/hide item groups
- Text pagination navigates historical responses

**File Structure**:
- Main template: `templates/promapp/hcp_result_ui.html`
- Components: `templates/promapp/components/[component_name].html`
- HTMX partials: `templates/promapp/partials/[partial_name].html`

Finally the page can be printed out without loosing any information

In mobile screens the arrangement will be responsive. 

# Display ordering

Item & construct ordering in item wise results section to ensure items for the worst performing constructs are displayed first

1. Items will be ordered based on the item number in their construct
2. Constructs will be ordered based on the scale_better_score_direction and value as follows:
  - If the direction choice is Higher is Better then the constructs with lowest score will be displayed first. 
  - If the direction choice is Lower is Better then the constructs with the highest score will be displayed first.
  - If the direction is No Direction or not specifieid or Middle is better then the constructs will be ordered according to the score value from lowest to highest score



# Aggregation features

The system will be able to show the aggregated data in the plots as well as the cards. 

How aggregation will be done:
1. Aggregation will be done for the construct scores, as well as items with Likert, Range and Numeric response types. 
2. For each of the construct scores, and item responses (of the types mentioned) the system will get the data of all patients in the system who have provided one or more responses for these.
3. Before the aggregation the system will take into account the time period from which the responses are to be evaluated. For example the default start period is date of registration. However other dates can be selected as in the UI. Based on the type of date that has been selected (note that it is not the actual date value but the type of date) the aggregation will be done. 
4. The end date upto which the submissions are to be shown will be selected by the users in the Submissions Upto field. The interval between the start and end date is used to calculate the duration or interval over which the responses are to be obtained. For example if the duration is 3 months then we need all responses given by other patients in the three month period from the start date chosen. 
5. By default all patients responses will be shown. However we will have the potential to filter the list by matching gender, diagnosis, treatment etc. A combination of these factors will also be possible. If none of these are specified all patients are to be returned. 
6. After this the system evaluate the time interval units desired. For example if it is Days then the aggregation is to be done at a days level else weeks and so on. Default is weeks. 
7. The user will be able to choose the type of aggregation in the UI:
   - Median with interquartile range (25th - 75th quartile)
   - Mean with 95% confidence intervals of mean
   - Mean +/- 0.5 SD
   - Mean +/- 1 SD
   - Mean +/- 0.5 SD
   - Mean +/- 2 SD
   - Mean +/- 2.5 SD
8. The values of the patient whose data is being reviewed is to be discarded from the dataset. For the remaining patients, the median and IQR values of the construct scale score or the item responses will be computed at each of the time intervals desired. For example if the user wishes to review the responses over a period of 3 months from the date of registration at weekly intervals and has provided responses at 0 weeks, 1 week, 2 week, 3 week, 6 weeks, 9 weeks and 12 weeks then the system will first group the responses of the other patients into these week categories and then compute the median for each week. This implies that for the median aggregation, patients who have provided responses at 4, 5 and 6 weeks will all be grouped into the 6 week response group. 
8. Once this aggregation is performed then the median and IQRs scores at each week will be displayed on the line plots using the following convention:
   - Dotted gray line for the median or mean
   - Error bars on the points to represent the dispersion parameter (IQR, SD or 95% CI as the case may be)

Missing values for the given construct score / item response will be discarded for the computation. However if the patient response is such that one construct score is missing or one item value is missing while others are avaialble then all available values will be used for computation. 

It is important to remember that we would want the index patients responses to be always removed. 




# Score Interpretation

Interpretation will be provided for the construct scores : 

The focus of the interpretation will be on two aspects -
1. The current score
2. Change with respect to the previous score


Clinical importance of the current score for the construct scores will be determined according to the following rules:

## Direction: Higher is better

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

## Direction Lower is better

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


## Direction Middle is better 

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

## Direction Higher is Better

If MID is available then check the difference between the current score and the previous score. If the current score is lower than the previous score by a value greater than the MID then it is clinical important. 
If SD of Normative score is available then check the difference between the current score and the previous score. If the current score is lower than the previous score by a value more than 1 SD then it is clinically important
If both of these are available the MID takes precedence. If none are available then the score change exceeding 10% (that is if current score is lower than the previous score by 10% or more) will be considered clinically important. 

## Direction Lower is Better

If MID is available then check the difference between the current score and the previous score. If the current score is higher than the previous score by a value greater than the MID then it is clinical important. 
If SD of Normative score is available then check the difference between the current score and the previous score. If the current score is higher than the previous score by a value more than 1 SD then it is clinically important
If both of these are available the MID takes precedence. If none are available then the score change exceeding 10% (that is if current score is higher than the previous score by 10% or more) will be considered clinically important. 

## Direction Middle is Better

If MID is available then check the difference between the current score and the previous score. If the current score is higher or lower than the previous score by a value greater than the MID then it is clinical important. 
If SD of Normative score is available then check the difference between the current score and the previous score. If the current score is higher or lower than the previous score by a value more than 1 SD then it is clinically important
If both of these are available the MID takes precedence. If none are available then the score change exceeding 10% (that is if current score is higher or lower than the previous score by 10% or more) will be considered clinically important. 

All construct scores which meet either the criteria for clinical importance based on current score or change from previous score or both will be grouped. Note that if a score meets both criteria it takes precedence in the order. Remaining ordering will be done alphabetically.



