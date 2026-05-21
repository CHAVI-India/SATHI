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
- `submission_date_field` (CharField, nullable) — the REDCap field within the mapped form that will receive the questionnaire submission date/time on export.
- `submission_date_format` (CharField, nullable, choices from `SubmissionDateFormatChoices`) — the canonical export format derived automatically from the REDCap field's validation type (see format normalisation below). Stored as one of `date_ymd`, `datetime_ymd`, or `datetime_seconds_ymd`.
- `SubmissionDateFormatChoices` — TextChoices class defining the supported export formats: `date_dmy/mdy/ymd`, `datetime_dmy/mdy/ymd`, `datetime_seconds_dmy/mdy/ymd`.
- DB constraints: event cannot be repeating unless form is in an event; date mapping field required when form is in an event.
- `redcap_data_access_group_used` boolean field on `ProjectRedcapMapping`, auto-populated on metadata fetch.

#### Submission Date Mapping (form-level)
Implemented at the `RedcapFormToQuestionnaireMapping` level (not the individual field mapping level) so that one submission date field is configured per questionnaire/form pair.

**Form (`RedcapFormToQuestionnaireMappingForm`):**
- `submission_date_field` ChoiceField dynamically populated from all date/datetime fields across all REDCap instruments (detected via `text_validation_type_or_show_slider_number` starting with `date_` or `datetime_`).
- `_date_fields_by_form` dict built in `__init__` and passed to templates as `date_fields_by_form_json` for JS-driven filtering.
- `_normalise_date_format(validation)` static method maps any REDCap validation type to its canonical ymd export format:
  - `date_dmy / date_mdy / date_ymd` → `date_ymd`
  - `datetime_dmy / datetime_mdy / datetime_ymd` → `datetime_ymd`
  - `datetime_seconds_*` → `datetime_seconds_ymd`
- `clean()` validates that the selected field belongs to the chosen REDCap form and resolves the normalised format into `_resolved_submission_date_format`.
- `save()` writes `submission_date_field` and `submission_date_format` to the model instance.

**Views:**
- `redcap_form_mapping_create` and `redcap_form_mapping_edit` both pass `date_fields_by_form_json` to the template.
- Wizard step 3 (`redcap_setup_wizard`, step `'3'`) also passes `date_fields_by_form_json` to `step3_form_mapping.html`.

**Templates — UI behaviour (both wizard step 3 and standalone form mapping edit):**
- Submission Date Mapping section rendered as a separate card below the main form details.
- Dropdown (`<select name="submission_date_field">`) is JS-populated on page load — shows all date fields if no REDCap form is selected yet, filtered to the selected form's fields once a form is chosen.
- If exactly one date field is available, it is auto-selected.
- Format preview badge appears immediately showing the normalised export format (e.g. `date_ymd`).
- Dropdown option labels show both the raw REDCap validation type and the normalised export format, e.g. `fieldname (date_dmy → date_ymd)`.
- Existing form mappings list shows a 📅 amber badge with the configured `submission_date_field` name when set.

---

### ✅ Also Completed

#### Step 4 — Item-level field mapping
- `RedcapFieldToItemMapping` model links a `QuestionnaireItem` to a REDCap field name, scoped to a `RedcapFormToQuestionnaireMapping`.
- DB constraints: unique REDCap field per form mapping; unique questionnaire item per form mapping (one-to-one).
- `RedcapFieldToItemMappingForm` — dropdown populated from REDCap metadata fields for the selected form; date/datetime fields highlighted with a 📅 badge.
- `redcap_field_mappings` view handles add and delete of field mappings via POST `action` parameter.
- Template (`redcap_field_mappings.html`) shows existing mappings and an inline add form.

#### Steps 6 & 7 — Patient selection and study ID mapping
- `RedcapStudyIDtoPatientIDMap` model maps a SATHI `Patient` to a REDCap `redcap_study_id` per `ProjectRedcapMapping`.
- `redcap_patient_ids` view shows all patients linked to the project and allows bulk saving of REDCap study IDs via a single form POST.
- Template (`redcap_patient_ids.html`) renders an editable table with one text input per patient.

#### Steps 9–11 — Export (initial implementation)
- `redcap_export` view and `redcap_export.html` template: UI to select form mappings and trigger export.
- `ExportTypeChoices`: `MANUAL` (CSV download) and `AUTOMATIC` (API).
- **CSV export** (`_build_csv_export`): wide-format CSV with `record_id`, `redcap_event_name`, `redcap_repeat_instrument`, `redcap_repeat_instance`, and one column per mapped REDCap field. All submissions for all patients with a study ID mapping are included.
- **API export** (`_run_api_export`): imports rows via PyCap `import_records()`.
- **Transaction logging** (`RedcapDataExportLog`): records patient, user, form mapping, export type, start/end time, status (`pending/completed/incomplete/failed`), and raw response log. Last 50 logs shown on export page.
- `submission_date_field` / `submission_date_format` written to model but **not yet used** in `_collect_export_rows` to populate the submission date column in the export.

---

### 🔄 In Progress / Partially Done

#### Submission date population in export rows ✅
- `_collect_export_rows` now reads `fm.submission_date_field` and `fm.submission_date_format` and writes the formatted `QuestionnaireSubmission.submission_date` into the row.
- Format mapping: `date_ymd` → `%Y-%m-%d`, `datetime_ymd` → `%Y-%m-%d %H:%M`, `datetime_seconds_ymd` → `%Y-%m-%d %H:%M:%S` (via `_SUBMISSION_DATE_FORMATS` dict in `views.py`).
- Field is only written if `submission_date_field`, a resolved format, and a non-null `submission_date` are all present.

#### `RedcapFieldToItemMapping` — old submission date fields ✅
- `submission_date_field` and `submission_date_format` removed from `RedcapFieldToItemMapping` model (migration `0022`).
- `is_submission_date_field` extra field, `clean()` logic, and `save()` override removed from `RedcapFieldToItemMappingForm`.

---

### ⏳ Pending

#### Step 5 / Step 8 — Date-based submission-to-REDCap instance matching
- **Purpose**: for repeating forms/events, determine which REDCap repeating instance corresponds to each SATHI questionnaire submission, based on the closest date match between the SATHI `submission_date` and the REDCap `redcap_date_mapping_field` value.
- **Model needed**: a new model (e.g. `RedcapSubmissionInstanceMap`) to persist which submission maps to which `(redcap_event_name, redcap_repeat_instance)` pair, so the mapping is not recomputed on every export.
- **Algorithm**: fetch existing REDCap records via PyCap for the relevant form; compute absolute time difference between each record's date field value and the submission date; present top matches to the user sorted by closeness.
- **UI**: per-patient, per-questionnaire matching review screen where the user can confirm or override the automatically suggested instance.
- **Non-repeating forms**: sequential assignment (first submission → first non-repeating form variant, etc.) as a simpler fallback.
- This step is **prerequisite** for `redcap_repeat_instance` being correctly populated in the CSV/API export.

#### Export — `redcap_repeat_instance` population
- Currently `redcap_repeat_instance` is written as an empty string in `_collect_export_rows`.
- Once Step 5/8 matching is implemented, this should be filled from `RedcapSubmissionInstanceMap`.

#### Export — per-patient export workflow
- The original plan (step 6) calls for patient-level export selection.
- Currently `_collect_export_rows` exports all patients with a study ID at once.
- A patient-selector UI (similar to the patient list page, with Select2 or checkboxes) should be added to `redcap_export.html`.

#### Export — submission date column population
- In `_collect_export_rows`, when `fm.submission_date_field` is set, write `sub.submission_date` formatted according to `fm.submission_date_format` into `row[fm.submission_date_field]`.
- Format mapping: `date_ymd` → `%Y-%m-%d`, `datetime_ymd` → `%Y-%m-%d %H:%M`, `datetime_seconds_ymd` → `%Y-%m-%d %H:%M:%S`.

#### Cleanup — remove legacy submission date fields from `RedcapFieldToItemMapping`
- Create and apply a migration to drop `submission_date_field` and `submission_date_format` from `RedcapFieldToItemMapping`.
- Remove the `is_submission_date_field` logic from `RedcapFieldToItemMappingForm` (this is now handled at the form-mapping level).