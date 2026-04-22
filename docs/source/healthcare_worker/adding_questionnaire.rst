Adding Questionnaires
======================
.. contents:: Table of Contents
   :local:
   :depth: 2


This guide explains how to create Patient Reported Outcome Measures (PROMs) questionnaires in SATHI. Creating questionnaires involves a structured four-step process that must be followed in order.

Accessing the Questionnaire Creation Guide
-------------------------------------------

1. Navigate to the main menu
2. Click on **"Questionnaires"** or **"PROM Management"**
3. Select **"Questionnaire Creation Guide"** to access the comprehensive creation workflow

Understanding the Creation Process
-----------------------------------

Creating a questionnaire requires completing four key steps in the correct order:

**Step 1: Create Construct Scale** (Foundation)
   Define the latent trait you want to measure. This is the theoretical foundation of your questionnaire.

**Step 2: Create Response Scales** (Optional, if needed)
   Set up Likert or Range scales if your questions will use these response types.

**Step 3: Create Items (Questions)** (Building blocks)
   Create individual questions that will measure your construct.

**Step 4: Add to Questionnaire** (Final assembly)
   Combine your items into a complete questionnaire and arrange them in order.

.. important::
   These steps must be completed in order. You cannot create items without first creating the construct scale, and you cannot create a questionnaire without first creating items.

Understanding Latent Traits
----------------------------

Before creating questionnaires, it's important to understand what you're measuring.

What are Latent Traits?
~~~~~~~~~~~~~~~~~~~~~~~~

Latent traits are characteristics that **cannot be measured directly** and require patient-reported outcome measures to quantify them. These are subjective in nature, and PROMs help obtain a quantitative value that can be measured and compared.

**Key Characteristics:**

- Cannot be measured with physical instruments
- Subjective in nature
- Require multiple questions to capture fully
- Need patient self-reporting

**Examples of Latent Traits:**

- **Pain**: Intensity, quality, and impact of pain experiences
- **Quality of Life**: Overall well-being and life satisfaction
- **Depression**: Mood, emotional state, and psychological well-being
- **Anxiety**: Worry, fear, and stress levels
- **Physical Function**: Ability to perform daily activities
- **Fatigue**: Energy levels and tiredness

**Comparison:**

- **Objective Measurement**: Blood pressure can be measured using a sphygmomanometer (direct, quantitative)
- **Latent Trait Measurement**: Pain is measured using the Visual Analog Scale (indirect, patient-reported)

Step 1: Creating Construct Scales
----------------------------------

A construct scale is designed to measure a specific latent trait using a set of questions (items).

What is a Construct Scale?
~~~~~~~~~~~~~~~~~~~~~~~~~~~

A construct scale defines:

- What latent trait is being measured
- How to calculate a score from individual item responses
- Clinical thresholds and reference values
- Scoring direction (higher/lower is better)

Creating a New Construct Scale
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. Click **"Create Construct Scale"** from the creation guide
2. Fill in the required information:

**Basic Information:**

- **Name**: The name of the construct (e.g., "Physical Function", "Pain Intensity")
- **Instrument Name**: The PROM instrument this belongs to (e.g., "EORTC QLQ-C30")
- **Instrument Version**: Version number of the instrument
- **Scale Equation**: Mathematical formula to calculate the score from items (e.g., ``(Q1 + Q2 + Q3) / 3``)
- **Minimum Items**: Minimum number of questions that must be answered to calculate a valid score

**Clinical Parameters:**

- **Score Direction**: Whether higher or lower scores indicate better outcomes
  
  - Higher is Better (e.g., quality of life)
  - Lower is Better (e.g., symptom severity)
  - Middle is Better (e.g., some psychological measures)

- **Threshold Score**: The clinical significance threshold (scores beyond this indicate clinical concern)
- **Minimum Clinical Important Difference (MCID)**: The smallest change in score that is clinically meaningful
- **Normative Score Mean**: Average score in a healthy population
- **Normative Score Standard Deviation**: Variation in the healthy population

**Examples:**

- Physical Function (from EORTC QLQ-C30)
- Pain Intensity (from Brief Pain Inventory)
- Depression Severity (from PHQ-9)

3. Click **"Save"** to create the construct scale

Step 2: Creating Response Scales
---------------------------------

Response scales define how patients will answer questions. There are two main types:

Likert Scales
~~~~~~~~~~~~~

Likert scales are the most common response type, consisting of ordered response options with numerical values and text descriptions.

**When to Use:**

- Structured agreement scales (e.g., Strongly Disagree to Strongly Agree)
- Frequency scales (e.g., Never, Rarely, Sometimes, Often, Always)
- Severity scales (e.g., None, Mild, Moderate, Severe)

**Creating a Likert Scale:**

1. Click **"Create Likert Scale"**
2. Enter a **Scale Name** (descriptive label for identification)
3. Add response options:

   - **Option Order**: Display order (1, 2, 3, etc.)
   - **Option Value**: Numerical value for scoring
   - **Option Text**: Text description shown to patients
   - **Emoji** (optional): Visual indicator (use cautiously as meaning may vary)
   - **Option Media** (optional): Image, audio, or video to explain the option

4. Add multiple options as needed
5. To delete an option, check the "Delete" checkbox and save

**Common Examples:**

- Severity: None (0), Mild (1), Moderate (2), Severe (3)
- Frequency: Never (0), Rarely (1), Sometimes (2), Often (3), Always (4)
- Agreement: Strongly Disagree (1) to Strongly Agree (5)

.. note::
   Likert scales can be reused across multiple items and questionnaires if they share the same response structure.

Range Scales
~~~~~~~~~~~~

Range scales present a numeric ruler, typically used for visual analog scales like pain ratings.

**When to Use:**

- Pain scales (0-10)
- Quality of life ratings (0-100)
- Any continuous numeric measurement

**Creating a Range Scale:**

1. Click **"Create Range Scale"**
2. Enter the scale details:

   - **Scale Name**: Descriptive label
   - **Minimum Value**: Starting number (e.g., 0)
   - **Maximum Value**: Ending number (e.g., 10)
   - **Increment**: Step size between numbers (e.g., 1)
   - **Minimum Value Text**: Label for minimum (e.g., "No Pain")
   - **Maximum Value Text**: Label for maximum (e.g., "Worst Pain")

**Common Examples:**

- Pain Scale: 0 (No Pain) to 10 (Worst Pain), increment 1
- Quality of Life: 0 (Worst) to 100 (Best), increment 10

Step 3: Creating Items (Questions)
-----------------------------------

Items are the individual questions that patients will answer. Each item belongs to a construct scale.

Creating a New Item
~~~~~~~~~~~~~~~~~~~

1. Click **"Create New Item (Question)"**
2. Fill in the item details:

**Basic Information:**

- **Construct Scale**: Select which construct this item measures
- **Abbreviated Item ID**: Short code for data export (e.g., "PF1", "Q1") - use official abbreviations from scoring manuals when available
- **Item Name**: The complete question text
  
  .. important::
     Include any question root text. For example, if the questionnaire has "In the past 7 days:" as a common prefix, include it in each question for accuracy.

- **Item Media** (optional): Upload image, audio, or video to help explain the question or assist patients with limited literacy

**Response Type:**

Choose how patients will answer this question:

- **Likert**: Select from a pre-defined Likert scale (requires Step 2)
- **Range**: Use a numeric slider (requires Step 2)
- **Text**: Free-form text entry
- **Numeric**: Numeric value input
- **Media**: Audio or video recording by the patient

**Clinical Scoring Parameters** (optional but recommended):

- **Score Direction**: Higher/Lower/Middle is better
- **Threshold Score**: Clinical significance threshold for this specific item
- **Minimum Clinical Important Difference**: Meaningful change for this item
- **Normative Score Mean**: Expected value in healthy population
- **Normative Score Standard Deviation**: Variation in healthy population

3. Click **"Save"** to create the item

.. tip::
   **Multi-Language Support**: After creating an item, you can add translations in different languages. The system maintains scoring consistency across all language versions.

Managing Items
~~~~~~~~~~~~~~

- **View All Items**: Click "Manage Items" to see all created questions
- **Edit Items**: Click on any item to modify it
- **Reuse Items**: Items can be used in multiple questionnaires
- **Question Bank**: Build a library of validated questions for reuse

Step 4: Creating the Questionnaire
-----------------------------------

A questionnaire (also called an instrument) is a collection of items presented to patients in a specific order.

Creating a New Questionnaire
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. Click **"Create Questionnaire"**
2. Enter questionnaire details:

**Basic Settings:**

- **Name**: The questionnaire name (e.g., "EORTC QLQ-C30", "Brief Pain Inventory")
- **Description**: Explain what the questionnaire measures, how long it takes, and why it's being used
  
  .. note::
     This description is visible to patients, so use clear, easy-to-understand language.

- **Questionnaire Answer Interval**: Minimum time between submissions (prevents patients from answering too frequently)
- **Questionnaire Order**: Display order number (controls the sequence patients see questionnaires)
- **Questionnaire Redirect**: Optionally select another questionnaire to automatically redirect to after completion

Adding Items to the Questionnaire
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. **Select Items**: Check the box next to each item you want to include
   
   - Selected items appear in the side panel on the right
   - Use the construct scale filter to narrow down items
   - Use the search box to find specific items by text

2. **Arrange Order**: Drag and drop items in the side panel to change their order
   
   .. important::
      Match the official order from the validated PROM instrument when possible.

3. **Remove Items**: Click the cross (X) icon to deselect an item

4. Click **"Save"** to create the questionnaire

Managing Questionnaires
~~~~~~~~~~~~~~~~~~~~~~~~

- **View All Questionnaires**: Click "Manage Questionnaires"
- **Edit Questionnaires**: Modify items, order, or settings
- **Assign to Patients**: After creation, questionnaires can be assigned to specific patients

Advanced Features
-----------------

Multi-Language Translations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The system supports comprehensive multi-language functionality:

**Translatable Elements:**

- Questionnaire titles and descriptions
- Item text and media
- Likert scale response option text and media
- Range scale minimum and maximum value text

**How to Add Translations:**

1. Navigate to **"Manage Translations"** from the main menu
2. Select the language you want to translate to
3. Enter translations for each element
4. The system maintains scoring consistency across all languages

.. note::
   Available languages are configured by the system administrator.

Equation Editor
~~~~~~~~~~~~~~~

Advanced scoring capabilities using mathematical equations to calculate construct scores.

**Supported Operations:**

- Basic operators: ``+``, ``-``, ``*``, ``/``, ``^``
- Functions: ``sqrt()``, ``abs()``
- Item references: ``Q1``, ``Q2``, ``Q3``, etc.
- Parentheses for order of operations

**Example Equations:**

- Simple sum: ``Q1 + Q2 + Q3``
- Average score: ``(Q1 + Q2 + Q3) / 3``
- Transformed score: ``100 - ((Q1 + Q2) * 25 / 2)``
- EORTC scoring: ``(1 - (Q1 + Q2 + Q3) / 12) * 100``

The equation editor includes real-time validation to ensure your formula is correct.

Conditional Logic
~~~~~~~~~~~~~~~~~

After creating a questionnaire, you can define rules to control question display based on patient responses.

**Use Cases:**

- Show follow-up questions only if a specific answer is given
- Skip irrelevant questions based on previous responses
- Create branching logic for complex questionnaires

**How to Set Up:**

1. Create the questionnaire first
2. Navigate to the questionnaire's rule settings
3. Define conditions (e.g., "If Q1 = 'Yes', show Q2")
4. Test the logic before assigning to patients

Composite Construct Scores
---------------------------

Composite scores combine multiple individual construct scores into a single higher-level measurement.

What is a Composite Construct Score?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A composite construct score is calculated from one or more individual construct scores, providing a broader view of patient functioning.

**Example:**

The FACT TOI (Trial Outcome Index) score is calculated as:
``FACT-G (General) + FACT-B (Breast Cancer) + BCS (Breast Cancer Subscale)``

Creating a Composite Score
~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. Click **"Create Composite Construct Score"**
2. Select the **Scoring Type**:

   - **Sum**: Adds all selected construct scores together
   - **Average**: Calculates the mean of all scores
   - **Median**: Finds the middle value
   - **Mode**: Identifies the most frequent score
   - **Minimum**: Takes the lowest value
   - **Maximum**: Takes the highest value

3. Select which **Construct Scales** to include in the calculation
4. Click **"Save"**

**Common Use Cases:**

- Creating overall quality of life scores from multiple domains
- Combining physical and emotional wellbeing measures
- Generating summary scores for clinical trial endpoints
- Creating simplified reporting metrics from complex questionnaires

.. warning::
   Only create composite scores when there is theoretical and statistical justification. Refer to the original questionnaire validation papers for guidance.

Best Practices
--------------

**When Creating Construct Scales:**

- Use validated constructs from published PROM instruments
- Include all available clinical parameters (thresholds, MCID, normative scores)
- Verify the scoring equation matches the official scoring manual
- Document the source of your construct definition

**When Creating Items:**

- Use exact wording from validated questionnaires
- Include question roots and timeframes in the item text
- Use official abbreviated IDs from scoring manuals
- Add media to assist patients with limited literacy
- Test questions with a small group before full deployment

**When Creating Questionnaires:**

- Match the official item order from validated instruments
- Write clear, patient-friendly descriptions
- Set appropriate answer intervals to prevent survey fatigue
- Use questionnaire redirects to create smooth workflows
- Test the complete questionnaire before assigning to patients

**For Multi-Language Support:**

- Use professionally validated translations when available
- Have translations reviewed by native speakers
- Test questionnaires in each language
- Ensure cultural appropriateness of all content

Troubleshooting Common Issues
------------------------------

**Cannot create items without construct scale**
   You must create the construct scale first (Step 1) before creating items (Step 3).

**Likert/Range scale not appearing in item creation**
   Create the response scale first (Step 2) before creating items that use it.

**Equation validation errors**
   - Check that all item references (Q1, Q2, etc.) are correct
   - Ensure parentheses are balanced
   - Verify mathematical operators are valid
   - Test with sample values

**Items not appearing when creating questionnaire**
   - Verify items were saved successfully
   - Check that items belong to the expected construct
   - Use the search and filter functions to locate items

**Translations not displaying**
   - Ensure translations are saved for the active language
   - Check that the language is enabled in system settings
   - Verify all required fields are translated

Next Steps
----------

- Review :doc:`reviewing_results` to understand how scores are displayed
- Review :doc:`getting_started` for general navigation tips
- Explore the questionnaire guidance page within the system for detailed examples

Additional Resources
--------------------

**Within the System:**

- **Manage Construct Scales**: View and edit all construct scales
- **Manage Likert Scales**: View and edit all Likert response scales
- **Manage Range Scales**: View and edit all range response scales
- **Manage Items**: View and edit all questions
- **Manage Questionnaires**: View and edit all questionnaires
- **Manage Translations**: Add and edit multi-language translations
- **Composite Scoring**: Create and manage composite construct scores

**External Resources:**

- Refer to original PROM validation papers for construct definitions
- Consult official scoring manuals for equation verification
- Review published translations for language accuracy
