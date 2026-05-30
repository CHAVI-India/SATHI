Exporting Data to REDCap
========================

This guide explains how to configure and export Patient-Reported Outcome Measures (PROM) data from SATHI to REDCap for a specific project.

Overview
--------

SATHI supports seamless integration with REDCap for exporting e-PROM results. There are two export methods available:

1. **Manual CSV Export** - Download a formatted CSV file that you upload manually to REDCap
2. **Direct API Export** - Push data directly to REDCap via API (requires import privileges)

The export method is configured at the project level by an administrator.

Prerequisites
-------------

Before you can export data, the following must be in place:

* A REDCap project with an API token configured in SATHI
* Form mappings created linking SATHI questionnaires to REDCap forms
* Field mappings linking questionnaire items to REDCap fields
* Patient study ID mappings linking SATHI patients to REDCap records

Step-by-Step Configuration
--------------------------

Step 1: Configure REDCap API Connection
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The REDCap API connection is typically configured by a system administrator. This includes:

* REDCap project URL
* API token with appropriate privileges
* Data Access Group settings (if applicable)

Once configured, the system will automatically fetch REDCap metadata including:

* Available forms (instruments)
* Field definitions
* Events (for longitudinal projects)
* Repeating instrument and event settings

.. mermaid::

   flowchart TB
       A[REDCap Server] -->|API Token| B[SATHI System]
       B --> C[Fetch Forms]
       B --> D[Fetch Fields]
       B --> E[Fetch Events]

Step 2: Map Forms to Questionnaires
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For each questionnaire in SATHI that needs to be exported to REDCap:

1. Navigate to the REDCap Configuration page for your project
2. Under "Form Mappings", click "Add Form Mapping"
3. Select the REDCap form from the dropdown
4. Select the corresponding SATHI questionnaire
5. Configure the following settings:

   * **Event Name** (for longitudinal projects): The REDCap event where data will be stored
   * **Date Mapping Field** (optional): A date field in REDCap used for matching submissions to instances
   * **Submission Date Field**: The REDCap field that will receive the questionnaire submission date

6. Save the mapping

.. mermaid::

   flowchart TB
       A[REDCap Form] --> B{SATHI Questionnaire}
       B --> C[Set Event]
       B --> D[Set Date Field]
       B --> E[Save Mapping]

**Important notes:**

* The date mapping field helps the system match questionnaire submissions to the correct REDCap event/instance by comparing dates
* If the form is repeating or part of a repeating event, you will need to match submissions individually (see Step 5)

Step 3: Map Fields (Items to REDCap Fields)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

After creating a form mapping, you must map individual questionnaire items to REDCap fields:

1. Go to the Form Mappings list
2. Click "Field Mappings" next to the form mapping you want to configure
3. For each questionnaire item that needs to be exported:

   * Click "Add Field Mapping"
   * Select the REDCap field from the dropdown
   * Select the corresponding questionnaire item
   * Choose a response transform if needed (e.g., convert to integer, strip trailing zeros)
   * Save the mapping

4. Continue until all required items are mapped

.. mermaid::

   flowchart TB
       A[Questionnaire Item] --> B{REDCap Field}
       B --> C[Select Transform]
       C --> D[To Integer]
       C --> E[To Float]
       C --> F[Strip Zeros]
       C --> G[No Transform]
       D --> H[Save]
       E --> H
       F --> H
       G --> H

**Response Transforms:**

Response transforms ensure data is formatted correctly for REDCap:

* **None** - Export as-is
* **To Integer** - Convert to whole number (for radio/dropdown codes)
* **To Float** - Convert to decimal number
* **To Float (2 decimals)** - Convert to decimal with 2 decimal places
* **Round to Integer** - Round to nearest whole number
* **Strip Trailing Zeros** - Remove unnecessary decimal places (e.g., 1.00 → 1)

Step 4: Map Patient Study IDs
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Before exporting, each SATHI patient must be linked to a REDCap study ID:

1. Navigate to "Patient IDs" in the REDCap section
2. The system will attempt to auto-match patients based on ID similarities
3. For unmatched patients:

   * Click "Assign" next to the patient
   * Select the corresponding REDCap study ID from the list
   * Or type the study ID manually if not shown
   * Save the mapping

4. Review auto-matched patients to confirm accuracy

A patient must have a study ID mapping before their data can be exported.

.. mermaid::

   flowchart TB
       A[Patient in SATHI] --> B[Find Match]
       B --> C{REDCap Study ID}
       C -->|Found| D[Auto-Match]
       C -->|Not Found| E[Manual Assign]
       D --> F[Save Mapping]
       E --> F

Step 5: Match Submissions to REDCap Instances (for Repeating Forms/Events)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If your REDCap project uses repeating forms or events, you must specify which REDCap instance each questionnaire submission maps to:

1. From the Patient IDs page, click "Match" next to a patient with a study ID
2. Review the submissions for each questionnaire:

   * The system suggests the closest match based on date proximity (if a date mapping field is configured)
   * The suggested event and instance number are shown

3. For each submission:

   * Verify the suggested event name is correct
   * Verify or adjust the instance number
   * Check the checkbox to include the submission in the match

4. Click "Save Selected Matches"

**How matching works:**

* The system fetches existing REDCap instances with their dates
* It calculates the time difference between questionnaire submission dates and REDCap dates
* Submissions are matched to the closest date within a 30-day threshold
* Instance numbers are auto-incremented starting from existing REDCap instance counts

**Important:** Only matched submissions will be exported. Unmatched submissions for repeating/event forms are automatically excluded from export to prevent data errors.

.. mermaid::

   flowchart TB
       A[Patient Submissions] --> B{Repeating?}
       B -->|Yes| C[Date Matching]
       B -->|No| D[Export All]
       C --> E[Suggest Instance]
       E --> F[Review & Confirm]
       F --> G[Save Matches]
       D --> H[Export]
       G --> H

Exporting Data
--------------

Once all mappings and matches are complete:

1. Navigate to the "Export" page
2. Select the form mappings you want to export (checkboxes on the left)
3. Select specific patients to export (optional - leave all unchecked to export all)
4. The export method (Manual CSV or Direct API) is shown based on project configuration
5. Click "Run Export"

Manual CSV Export
~~~~~~~~~~~~~~~~~

For manual export:

1. Click "Run Export"
2. A CSV file will download automatically
3. Log into REDCap
4. Navigate to Data Import Tool
5. Upload the downloaded CSV file
6. Review and import the data

.. mermaid::

   flowchart TB
       A[Run Export] --> B[Select Mappings]
       B --> C[Select Patients]
       C --> D[Click Run]
       D --> E[Download CSV]
       E --> F[Import to REDCap]

Direct API Export
~~~~~~~~~~~~~~~~~

For API export:

1. Click "Run Export"
2. The system will push data directly to REDCap
3. Wait for the operation to complete
4. Review the export log for results:

   * Green "Completed" status = successful export
   * Red "Failed" status = error occurred (check the log for details)

.. mermaid::

   flowchart TB
       A[Run Export] --> B[Select Mappings]
       B --> C[Select Patients]
       C --> D[Click Run]
       D --> E[Push via API]
       E --> F{Success?}
       F -->|Yes| G[Completed]
       F -->|No| H[Check Log]

Checking Export Status
----------------------

The Export page shows a "Recent Export Log" table with:

* Date and time of export
* Form exported
* Patient exported (if applicable)
* Export type (Manual or Automatic)
* Status (Completed, Failed, Pending)
* User who performed the export

Click "Match →" in the Actions column to go directly to the matching page for a specific patient.

Troubleshooting
---------------

Form Mappings Not Showing
~~~~~~~~~~~~~~~~~~~~~~~~~

* Ensure form mappings have been created in the REDCap configuration
* Verify at least one field mapping exists for each form you want to export

"No Patients Selected" Error
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* Ensure patients have study ID mappings (Step 4)
* If selecting specific patients, ensure at least one checkbox is checked

"No Data Found" Warning
~~~~~~~~~~~~~~~~~~~~~~~

* Verify the patient has questionnaire submissions for the selected form
* Check that submissions are properly matched to REDCap instances (Step 5) for repeating forms
* For repeating/event forms, unmatched submissions are excluded from export

Export Log Shows "Failed"
~~~~~~~~~~~~~~~~~~~~~~~~~

* Check that the API token has import privileges (for API export)
* Verify the REDCap project URL is correct
* Review the error message in the export log
* Ensure REDCap is accessible and the project is not in maintenance mode

Date Matching Issues
~~~~~~~~~~~~~~~~~~~~

* If dates are not matching correctly:

  * Verify the date mapping field is configured in the form mapping
  * Check that the REDCap field contains valid dates
  * Ensure questionnaire submission dates are within 30 days of REDCap dates

Data Appears in Wrong REDCap Instance
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* Review the submission matches for the patient (Step 5)
* Verify the event name and instance number are correct
* Adjust and save the matches, then re-export

Tips for Successful Export
--------------------------

1. **Complete matching before exporting** - Ensure all submissions for repeating forms are matched to avoid missing data

2. **Review auto-matches** - While the system suggests matches based on date proximity, always review them for accuracy

3. **Export incrementally** - For large projects, export in smaller batches (by form or by patient subset)

4. **Check the export log** - Review the Recent Export Log after each export to confirm success

5. **Verify in REDCap** - After importing, spot-check data in REDCap to ensure it appears in the correct events and instances

6. **Use the Matching UI** - The "Match →" links in the export log provide quick access to fix mapping issues

Data Security Notes
-------------------

* REDCap API tokens are stored encrypted in SATHI
* Patient study IDs are stored encrypted
* All export transactions are logged with user identification
* Data Access Groups are respected during export (if configured)

Related Documentation
---------------------

* :doc:`adding_questionnaire` - Creating and managing questionnaires
* :doc:`patient_management` - Managing patient records
* :doc:`../developer/data_integration` - Project-level configuration and data integration

See Also
--------

* `REDCap Project <https://projectredcap.org>`_ - Official REDCap documentation
* `REDCap API Documentation <https://redcap.vanderbilt.edu/api/help/>`_ - API reference

For technical details about the REDCap integration implementation, refer to the internal ``SATHI REDCap integration pipline.md`` document.
