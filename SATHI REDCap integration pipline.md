What we need ?  
Seamless integration between a remote REDCap instance and the SATHI site for exporting results of e-PROM obtained on SATHI. 

What type of export is needed ?

1. Formatted CSV files for manual export  
2. Direct API mediated export

What is the workflow plan ?

1. Step 1: User obtained API key from REDCap. This API key may have import / export privileges.   
2. Stores the following information in SATHI database (using encrypted fields):  
   1. REDCap API token (this is a project specific token so it is unique for each project). Will need to linked to Project table (one project can have multiple API keys)  
   2. REDCap API URL \- again this can be different for different projects  
   3. Checks if data import and export rights have been assigned to the API key  
3. First the system will go to the project and obtain the following details. Errors need to be raised in case the API endpoint is unavailable, or API key is not correct or user does not have appropriate privileges for reading project information:  
   1. Forms available in the database  
   2. Fields for each instrument including field name and field label  
   3. If a form is a part of repeating instance  
   4. If a form is a part of events  
   5. If the events are repeating or the form is repeating in a non-repeating event.   
   6. Total number of records  
4. We then need to provide the users with an UI where they will be able to map the items linked to a questionnaire in SATHI to the instrument field names in REDCap. This mapping needs to be saved. Here the UI should allow mapping of multiple questionnaires and their items to the respective REDcap form fields (and thereby the forms themselves). This mapping has to be one to one i.e. one item in the questionnaire should be mapped to one form field in REDCap. It is noteworthy here that the same item can theoretically be used in multiple questionnaires for the same patient but this mapping needs to be done for the specific form in REDcap as REDCap does not have the same relational structure.   
5. SATHI lacks the designation for the event / form, making it difficult to match which questionnaire submission data is to be matched to which form in REDCap. Blind import may result in spurious / incorrect data. Typically the data available in SATHI for each questionnaire submission is the date and time and therefore this needs to be matched with date and time in REDCap. Here the implicit assumption is that the data from SATHI will be exported to a REDcap where the visit date for the patient has been noted in a specific form. The user will therefore need to explicitly pick the visit date field in REDCapwhich will be matched against the date of the questionnaire submission for the respective questionnaire. In order to ensure that the import is done without error we will require that the field type in REDCap must be a date field. Note that the field may be a date time field also. NOTE : this assumption will break in case of the situation where repeating forms have not been used.   
6. After this the user will select the patient whose data is to be exported from SATHI. They should be able filter the patient list based on the Project to which the patient is linked. If the patient is not linked to a specific project then data of that patient cannot be exported from CHAVI to the REDCap. We will currently allow mapping step by step as otherwise there can be data import errors.   
7. The first step will involve matching the SATHI patient ID to the REDCap study ID. This may be straightforward if the REDCap study id (the primary identifier field name) is mapped directly to the SATHI patient ID (note that in SATHI there is a username and a patient ID we are looking at the patient ID). If not matched then it has to be manually matched and the mapping has to be saved.   
8. For REDCap import to work we need to map the data in SATHI to the relevant redcap form.   
   1. If there is a single observation only for a given questionnaire on REDcap then the export process is relatively straightforward. The date (or date time) field date in the REDCap will be matched against the date of questionnaire submission date (or date time). The user interface will show the closest matching by the time difference between the REDCap visit date and the questionnaire submission date. Once the submission has been marked this choice will be saved for future reference.   
   2. If there are multiple observations for a given questionnaire then there are two possibilities:  
      1. Nonrepeating forms: People can design the REDcap form with one instrument for the different time points. For example if the PROM is take 5 times they can design 5 of the same forms in REDCap where the data is collected (labelled as say qol1, qol2, qol3 and so on). In such situations the date of PROM. Here usually it would be sufficient to map the questionnaire submissions by the date of response and map them sequentially to the forms.   
      2. Repeating Forms and or Events: The most common way of handling this issue will be with a visit date field which is matching with the repeating form or the event. Note that in REDCap it is possible to have repeating events where all forms in the event are repeated, and alternatively there can repeating forms where specific forms in the event are repeated. The date field for mapping will be selected by the user to allow users to identify the repeating instance of an event which is to be mapped. This mapping has to be saved. The user should be presented with the closest match based on the difference between the SATHI date/time (for questionnaire submission) and the date / time in the REDCap visit data field. All matches should be cross verified by the user and modifiable. The results of the matching need to be saved in the database (that is which questionnaire submission matched to which redcap event and repeating instance).   
9. Once the import mapping is done the user should be able to specify API wise direct export to REDCap (in this case the verification of privileges is essential before the export) or csv file which can be imported manually into REDCap by the user.   
10. If API based export is used then appropriate logging is required for each transaction mde.   
11. If CSV export is used then the csv needs to have the study\_id of the REDCap project, redcap\_repeating\_instance, redcap\_event\_name, redcap\_repeating\_event\_name data in addition to the questionnaire response data. This needs to be provided in a wide format. 

---

## Implementation Progress

### ✅ Completed

#### Step 2 — REDCap Configuration Storage (`ProjectRedcapMapping` model)
- `ProjectRedcapMapping` model linked to `Project` (one project, multiple mappings).
- Encrypted storage of `redcap_project_token` (using `secured_fields.EncryptedTextField`).
- `redcap_project_url` stored per mapping.
- Boolean flags `redcap_project_token_allows_import` and `redcap_project_token_allows_export`.
- On the edit form, leaving the token blank retains the existing encrypted token (no accidental overwrite).
- CSRF token sent globally via `htmx:configRequest` header.

#### Step 3 — Metadata Fetch (PyCap integration)
All fetched via PyCap and stored in `redcap_project_info` (JSONField):
- `project_info` — project title, language, longitudinal flag, production status, etc.
- `instruments` — list of all forms with `instrument_name` and `instrument_label`.
- `metadata` — all fields with `field_name`, `field_label`, `field_type`, `form_name`, etc.
- `events` — all events with `event_name`, `unique_event_name`, `arm_num` (longitudinal projects only).
- `dags` — all Data Access Groups.
- `repeating` — output of `export_repeating_instruments_and_events()` distinguishing repeating forms from repeating events.
- `redcap_record_count` — total number of records stored separately as an integer field.
- `date_redcap_project_info_updated` — date of last fetch stored.
- `redcap_data_access_group_used` — boolean auto-set from whether DAGs were returned.
- Error handling: API unavailability, bad token, and insufficient privileges are caught and shown to the user.

#### Setup Wizard UI (full-page, new tab)
- "Setup Wizard" / "Setup / Fetch" button on the REDCap dashboard opens the wizard in a new browser tab (`target="_blank"`).
- Wizard is a full-page view (`/projects/<pk>/redcap/<mapping_pk>/wizard/`) rendered by `redcap_wizard_page`.
- Step-by-step HTMX navigation inside `#wizard-body` without full page reloads.
- Page header has a persistent **Re-fetch Metadata** button (indigo, with spinner) visible at all times.
- After every HTMX swap the page scrolls smoothly to `#wizard-body`.

**Step 1 — Metadata Fetch & Review:**
- Summary stat cards: Records, Forms, Fields, Events.
- Project info table: title, language, production status, longitudinal, DAG status (auto-detected).
- Scrollable list of instruments and events.
- Scrollable list of Data Access Groups (or "No DAGs configured" message).
- Inline **Re-fetch Metadata** button next to "View raw JSON payload" toggle (same row, compact text style).
- Collapsible raw JSON payload viewer (dark background, green monospace text, inline style to override CSS resets).

**Step 2 — ID Fields:**
- Select `redcap_study_id_field` (primary record ID field) and `redcap_secondary_id_field` from dropdown populated from fetched metadata.

**Step 3 — Form → Questionnaire Mapping:**
- REDCap form dropdown populated from fetched instruments.
- Date mapping field dropdown populated from fetched metadata fields.
- **Auto-fill on form selection**: when the user picks a REDCap form, JavaScript immediately sets:
  - `redcap_form_is_repeating` — from `repeating` payload (non-empty `form_name` entries).
  - `redcap_form_is_in_event` — true if project is longitudinal with events.
  - `redcap_event_is_repeating` — true if any repeating entry has an empty `form_name` (whole event repeats).
  - `redcap_event_name` — pre-filled with the first event's `unique_event_name`.
- Same auto-fill JS applied to the standalone create/edit form mapping pages.
- Existing mappings shown in a scrollable list above the add-mapping form.

#### Models
- `RedcapFormToQuestionnaireMapping` — links a REDCap form to a CHAVI PROM questionnaire per project mapping, stores `redcap_event_name`, `redcap_form_is_repeating`, `redcap_form_is_in_event`, `redcap_event_is_repeating`, `redcap_date_mapping_field`.
- DB constraints: event cannot be repeating unless form is in an event; date mapping field required when form is in an event.
- `redcap_data_access_group_used` boolean field on `ProjectRedcapMapping`, auto-populated on metadata fetch.

---

### 🔄 In Progress / Partially Done

#### Step 4 — Item-level field mapping
- `RedcapFieldToItemMapping` model exists linking a PROM item to a REDCap field name within a form mapping.
- Field mapping UI (`redcap_field_mappings` view) exists.
- Status: basic structure in place; needs review for completeness.

---

### ⏳ Pending

#### Step 5 — Date matching logic
- Logic to match questionnaire submission date/time to REDCap visit date field not yet implemented.
- UI for presenting closest date matches to the user not yet built.
- Saving the matched instance (submission ↔ REDCap event/repeating instance) not yet implemented.

#### Step 6 & 7 — Patient selection and study ID mapping
- `RedcapStudyIDtoPatientIDMap` model exists for mapping SATHI patient IDs to REDCap study IDs.
- `redcap_patient_ids` view and template exist for manual ID mapping.
- Status: basic structure in place; automated matching logic not yet implemented.

#### Step 8 — Submission-to-REDCap instance matching
- Matching algorithm (closest date difference) not yet implemented.
- UI for cross-verification and modification of matches not yet built.
- Saving match results to the database not yet implemented.

#### Step 9–11 — Export
- Export type choice (API vs CSV) exists as `export_type` field (`ExportTypeChoices.MANUAL` default).
- `redcap_export` view stub exists.
- CSV generation with `redcap_repeating_instance`, `redcap_event_name`, wide format: **not yet implemented**.
- API-based direct import to REDCap: **not yet implemented**.
- Transaction logging for API exports: **not yet implemented**.