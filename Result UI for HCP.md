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

Access the page will be accessed through a button called "View Responses" placed on the Patient Table component which is used in the Patient List template. Clicking this button will provide the necessary context in form of the patient's primary key. 

**Technology Stack**: Django Templates + Tailwind CSS + HTMX + Bokeh + Django Crispy Forms

Top right card (1/3rd of the width in wide display):
 - Patient Name, Patient ID, 
 - Diagnses
 - Treatments with date
 
**Component**: `PatientInfoCard` 
**Template**: `templates/promapp/components/patient_info_card.html`

Top Left card (2/3rd of the width in wide display):
 - Questionnaires available for the patient, number of submissions for the questionnaire, last date of submission
 - The latest submitted questionnaire(s) will be shown in the page together. That is if the patient submits response to two questionnaires then the responses from the latest submission of both these questionnaires is to be shown by default. The responses will be used in the sections below (Topline results and Item wise reuslts).
 - Option to navigate to a specific submission (by date and submission). Note if a different submission date is selected then the display will change accordingly below.

**Component**: `QuestionnaireOverviewCard`
**Template**: `templates/promapp/components/questionnaire_overview_card.html`
**Widgets**: 
- `SubmissionDateSelector` (dropdown for submission navigation)
- `QuestionnaireFilter` (filter specific questionnaires)
**HTMX**: Updates `#results-container` on submission date change

Topline results
This section which will span the entire width will show the **important** construct scales. Importance will be determined by the following hurestic:
 - Any score that is greater than the threshold score - if the direction is lower is better and lower than the threshold score if the direction is higher is better
 - If the threshold score is not specified but the normative score is specified alone then any score above or below the normative score depending on the direction as above.
 - If the threshold score is not specified but the normative score is specified with the standard deviation then anything above 1/2 the standard deviation above or below the normative score as per the direction. 
 - If both threshold score and normative scores are available scores above or below the threshold score will be given prominence

**Component**: `ToplineResultsSection`
**Template**: `templates/promapp/components/topline_results_section.html`
 
The scores will be shown in a card component where the score of the latest submission shall be shown prominently on the left (1/3rd of the space). Below this score the change with respect to the previous score will be shown with an arrow indicating increase or decrease (orange arrow up for increase or decrease based on the direction, green arrow down for decrease or increase based on the direction, orange horizontal bar for no change) if a prior score is available. orange arrow will indicate worsening and green arrow will indicate improvement. If the direction is not specified the arrows will not be shown. If the previous submission had a missing score for the construct same will be shown as -NA-.

**Component**: `ImportantConstructCard` (multiple instances, 2-4 per row)
**Template**: `templates/promapp/components/important_construct_card.html`
**Widget**: `ChangeIndicator` (arrows: green=improvement, orange=worsening, horizontal=no change, "-NA-"=missing previous)

The remaining 2/3rd of half of the space will be occupied by an interactive line plot showing the threshold score value as a line (orange), normative population score as a blue line (with SD bands 1 standard deviation if available with light semitransparent blue). The Y axis will comprise of the score and the X axis will have the last 5 submissions arranged such that the latest submission value is at the left. However a widget will be provided which allows the user to customize the number of submissions they wish to see. 

**Plotting**: Bokeh line plots with threshold (orange) and normative (navy blue) reference lines
**Widget**: `SubmissionControlWidget` (controls: 3, 5, 10, 15, All submissions - default: 5)
**HTMX**: Updates all plots when submission count changes

Missing scores will be denoted with a cross.

The remaining section will link to clinical advisory which will be added latter for the specific construct scale

Item wise results. 

This will allow users to drill down to the specific item wise responses. Items will be grouped by construct scales inside fieldsets which will be open by default but can be collapsed if desiorange. A toggle will be provided for this. 

**Component**: `ItemWiseResultsSection`
**Template**: `templates/promapp/components/item_wise_results_section.html`

For each fieldset we will have the construct score for the latest submission and a sparkline showing the trend in the construct score.

**Component**: `ConstructFieldset` (collapsible groupings)
**Template**: `templates/promapp/components/construct_fieldset.html`
**Widgets**: 
- `FieldsetToggle` (individual expand/collapse)
- `GlobalFieldsetToggle` (expand/collapse all)
**Plotting**: Mini Bokeh sparklines for construct score trends 

The display for the item will be different based on the type of response:

| Response Type | Display |
| ----- | ----- |
| Text | For this the entire text needs to be shown inside a wide card element. A paginator at the bottom will allow users to navigate to the previous text|
| Numeric | For this the actual numeric value needs to be presented. As per the display we have adopted for the topline results where the construct scale. See details below |
| Likert | The actual option text value will need to be presented. A color visualation will be done based on the direction and number of items |
| Range | For this the actual numeric value will be presented. Display will be as per the Numeric items |

## Text Option
For text items we do not need any specific visualization as noted above. However we may want to get the important concepts from the text later on. This will be implemented later.

**Component**: `TextItemCard`
**Template**: `templates/promapp/components/text_item_card.html`
**Widget**: `TextResponsePaginator` (navigate through historical text responses)
**Layout**: Wide card spanning full width

## Numeric and Range options
For Numeric and Range options which are numeric the display will be similiar to the construct scale

**Components**: 
- `NumericItemCard` 
- `RangeItemCard` (same implementation as NumericItemCard)
**Templates**: 
- `templates/promapp/components/numeric_item_card.html`
- `templates/promapp/components/range_item_card.html`
**Layout**: Two items per row on wide displays, left half (1/2) for value display, right half (1/2) for plot
 
The scores will be shown in a card component where the score of the latest submission shall be shown prominently on the left (1/2 of the space). Each item in the construct will be represented in a card of its own and two items will be shown in the same row for wide displays. Below this score the change with respect to the previous score will be shown with an arrow indicating increase or decrease (orange arrow up for increase or decrease based on the direction, green arrow down for decrease or increase based on the direction, orange horizontal bar for no change) if a prior score is available. orange arrow will indicate worsening and green arrow will indicate improvement. Note that if the direction is not specified then only the previous score will be shown. 

**Widget**: `ChangeIndicator` (same logic as construct cards)

If the previous submission had a missing score for the item same will be shown as -NA-.

The remaining half of the space will be occupied by interactive line plots for each item arranged in the same order as the cards. Again 2 plots for each row in wide displays. Plots will have Y axis as the value and x axis as the submission date. To save space the submission date will be common for all plots here. Number of submissions for visualization will be controlled by the widget noted in the topline results section for all plots. Threshold scores and normatives scores will be depicted using the orange and blue lines respectively. If standard deviation of the normaitve score is present for the item then a semi-transparent lighter hue of blue will be used to depict this.

**Plotting**: Bokeh line plots with threshold/normative reference lines, controlled by `SubmissionControlWidget` 


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