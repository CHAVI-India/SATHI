Reviewing Results
==================

.. contents:: Table of Contents
   :local:
   :depth: 2


The PRO Review page is your central dashboard for viewing and analyzing patient questionnaire responses over time. This page helps you track patient outcomes, identify concerning trends, and compare individual patient scores against population data.

Accessing the PRO Review Page
------------------------------

1. Navigate to the **Patient List** from the main menu
2. Click on a patient's name to view their details
3. Click the **"PRO Review"** button to access their results dashboard

Understanding the Page Layout
------------------------------

The PRO Review page is organized into several key sections:

**Help Card (Collapsible)**
   Click the blue information banner at the top to expand a comprehensive guide explaining all plot elements, change indicators, and status symbols used throughout the page.

**Filters Section (Collapsible)**
   Control which data is displayed and how it's analyzed. Click to expand the filters panel.

**Patient Information Card**
   Shows patient demographics, diagnoses, treatments, and allows you to mark important dates on plots.

**Questionnaire Overview**
   Displays all questionnaires the patient has completed with submission counts and dates.

**Results Sections**
   - **Topline Results**: Constructs requiring attention (worsened scores or below threshold)
   - **Other Construct Scores**: All other construct measurements
   - **Composite Construct Scores**: Combined scores from multiple related constructs

Using Filters
-------------

The filters section allows you to customize your view of the patient's data. Click the **"Filters"** header to expand the panel.

Time Analysis Filters
~~~~~~~~~~~~~~~~~~~~~

**Start Date Reference**
   Choose which date to use as the starting point for time calculations:
   
   - Date of Registration
   - Date of Diagnosis
   - Date of Treatment Start
   - Other clinical milestones
   
   This helps align data to clinically meaningful timepoints.

**Up to [X] [weeks/months/years] after start date**
   Limit data to a specific time window from the start date. Leave empty to show all data.

**Time Range**
   Select how many recent submissions to display:
   
   - 3, 5, 10, or 15 submissions
   - All submissions
   
   Default is 5 submissions.

**Time Interval**
   Choose the unit for time calculations:
   
   - Days
   - Weeks (default)
   - Months
   - Years

Population Comparison Filters
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

These filters control which other patients are included when calculating population comparison data (the gray dashed lines and error bars on plots).

**Aggregation Type**
   Choose how population data is summarized:
   
   - **Median with IQR**: Shows the middle value with 25th-75th percentile range (default, most robust)
   - **Mean with 95% Confidence Interval**: Shows average with statistical confidence range
   - **Mean ± 0.5/1/2 Standard Deviations**: Shows average with spread indicators

**Gender Filter**
   - All Genders
   - Match Patient (compare only to same gender)
   - Specific gender (Male, Female, Other)

**Diagnosis Filter**
   - All Diagnoses
   - Match Patient (compare only to patients with same diagnosis)
   - Specific diagnosis

**Treatment Filter**
   - All Treatments
   - Match Patient (compare only to patients with same treatment)
   - Specific treatment type

**Age Range**
   Set minimum and maximum age to narrow the comparison population.

Applying Filters
~~~~~~~~~~~~~~~~

1. Adjust the filter settings as needed
2. Click the blue **"Apply Filters"** button at the bottom of the filters section
3. The page will reload with a loading indicator while recalculating
4. Click **"Reset Filters"** to return to default settings

Patient Information Card
------------------------

This card displays:

- **Patient Name and ID**: At the top with an avatar
- **Demographics**: Age, gender, and registration date
- **Clinical Information**: Diagnoses and associated treatments

Marking Important Dates on Plots
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can add vertical lines to plots to mark important clinical events:

1. Find the diagnosis or treatment in the patient information card
2. Check the box next to dates you want to display:
   
   - Diagnosis dates (checkbox next to diagnosis name)
   - Treatment start dates (green checkbox)
   - Treatment end dates (red checkbox)

3. Click the blue **"Apply Plot Indicators"** button at the bottom of the card
4. Vertical dashed lines will appear on all plots at those dates

Questionnaire Overview
----------------------

This section shows cards for each questionnaire the patient has completed:

- **Badge number**: Shows how many times the questionnaire was submitted
- **Questionnaire name**: The name of the questionnaire
- **Latest submission date**: When it was last completed

**Filtering by Questionnaire**

Click on any questionnaire card to filter the entire page to show only results from that questionnaire. A blue highlight indicates the active filter. Click **"Clear Filter"** to show all questionnaires again.

Understanding the Results Sections
-----------------------------------

Results are organized into three sections with vertical tabs for easy navigation:

Topline Results (Red Section)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This section highlights constructs that require clinical attention because:

- The score has significantly worsened compared to the previous assessment
- The score is below the clinical threshold
- The score is worse than the normative (population average) value

**When to check Topline Results**: Review this section first during patient consultations to identify areas needing intervention.

Other Construct Scores (Green Section)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Shows all other construct measurements that don't meet the criteria for Topline Results. These are generally stable or improving scores.

Composite Construct Scores (Blue Section)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Displays combined scores calculated from multiple related constructs. These provide a broader view of patient functioning in specific domains.

Reading Construct Score Cards
------------------------------

Each construct is displayed in a card showing:

**Score Display**
   - Large number showing the current score
   - Change indicator (arrow or equal sign):
     
     - Green up arrow: Beneficial improvement
     - Orange up arrow: Detrimental increase
     - Green down arrow: Beneficial decrease
     - Orange down arrow: Detrimental decrease
     - Blue equal sign: No change

**Direction Badge**
   - **Green "Higher is Better"**: Higher scores indicate better outcomes (e.g., quality of life)
   - **Blue "Lower is Better"**: Lower scores indicate better outcomes (e.g., symptom severity)
   - **Purple "Middle is Better"**: Mid-range scores are optimal

**Status Indicators**
   - Green checkmark (✓): Score meets clinical threshold
   - Red warning (⚠): Score below threshold, needs attention
   - Blue circle (◯): Population mean score value

**Completion Information**
   Shows "X/Y items answered" - how many questions were completed out of the total.

Understanding the Plots
------------------------

Each construct card includes an interactive plot showing scores over time.

Plot Elements
~~~~~~~~~~~~~

**Black Line and Circles**
   - The patient's actual scores over time
   - Hover over circles to see exact values and dates

**Orange Horizontal Line**
   - Clinical significance threshold
   - Scores above/below this line (depending on direction) indicate clinical concern

**Gray Horizontal Line**
   - Normative score (population average)
   - Reference point for typical scores

**Gray Shaded Bands**
   - Standard deviation bands around the normative score
   - Shows typical population variation

**Gray Dashed Line with Error Bars**
   - Aggregated scores from similar patients
   - Error bars show population spread (IQR, confidence interval, or standard deviation)
   - Helps you see if this patient's trajectory is typical

**Colored Vertical Dashed Lines**
   - Important clinical dates you marked (diagnosis, treatment start/end)
   - Color matches the checkbox color in the patient information card

Interpreting Trends
~~~~~~~~~~~~~~~~~~~~

**Improving Trend**
   - For "Higher is Better" constructs: Line moving upward
   - For "Lower is Better" constructs: Line moving downward
   - Patient is responding well to treatment

**Worsening Trend**
   - For "Higher is Better" constructs: Line moving downward
   - For "Lower is Better" constructs: Line moving upward
   - May indicate need for intervention or treatment adjustment

**Stable Trend**
   - Line remains relatively flat
   - Patient maintaining current status

**Comparison to Population**
   - Patient line above gray dashed line: Doing better than similar patients
   - Patient line below gray dashed line: Doing worse than similar patients
   - Patient line within error bars: Typical for this population

Viewing Individual Item Responses
----------------------------------

Below each construct plot, you'll find detailed responses to individual questionnaire items.

**For Likert Scale Items** (e.g., "Not at all" to "Very much")
   - Shows the selected response option
   - Displays the submission date

**For Range Scale Items** (e.g., 0-10 scale)
   - Shows the numeric value selected
   - Displays the submission date

**For Text Responses**
   - Shows the patient's written response
   - Long responses are truncated with a "Show more" button

**For Image/Media Responses**
   - Displays uploaded images
   - Click to view full size

Practical Workflow Tips
-----------------------

**During Patient Consultations**

1. Start with **Topline Results** to identify urgent concerns
2. Review the **plots** to understand trends over time
3. Use **population comparison** to contextualize the patient's scores
4. Check **individual item responses** for specific symptoms or concerns
5. Mark **treatment dates** on plots to correlate interventions with outcomes

**For Longitudinal Monitoring**

1. Set **Time Range** to "All submissions" to see the complete history
2. Use **Start Date Reference** to align data to treatment start
3. Apply **Population Filters** to compare against similar patients
4. Look for patterns around treatment changes

**For Research or Quality Improvement**

1. Use **Aggregation Type** filters to analyze population-level data
2. Apply **demographic filters** to study specific patient subgroups
3. Filter by **specific questionnaires** to focus on particular outcomes
4. Export or document trends for reporting

Troubleshooting Common Issues
------------------------------

**No data appears after applying filters**
   - Check if your time interval filter is too restrictive
   - Verify the patient has submissions within the selected timeframe
   - Try clicking "Reset Filters" to start over

**Plots are loading slowly**
   - The system is calculating population comparisons
   - Wait for the loading indicator to complete
   - Consider narrowing your filters to reduce calculation time

**Can't see all constructs**
   - Some constructs may be in different sections (Topline vs. Other)
   - Check if a questionnaire filter is active (clear it to see all)
   - Scroll down to see all vertical tabs

**Population comparison line is missing**
   - There may not be enough similar patients in the system
   - Try broadening your population filters
   - Check the aggregation metadata card for patient count

Next Steps
----------

- Review :doc:`getting_started` for general navigation tips
- Explore the patient list to view multiple patients' results
- Use the filters to compare different patient populations
