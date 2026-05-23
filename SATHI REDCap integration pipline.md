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
- `redcap_patient_ids` view fetches REDCap records via PyCap using `redcap_study_id_field` (primary) and `redcap_secondary_id_field` (optional secondary), deduplicates by primary ID, and auto-matches SATHI `patient_id` against both primary and secondary REDCap IDs (case-insensitive).
- POST handling supports two actions:
  - `action=save` + `modal_single=1`: saves a single patient's mapping from the modal dialog (fields: `modal_patient_pk`, `modal_study_id`).
  - `action=clear` + `patient_pk`: deletes the mapping for a single patient.
- Context passed to template: `rows` (list of dicts with `patient`, `redcap_study_id`, `auto_matched`), `mapped_count`, `redcap_records` (list of `{primary, secondary}` dicts), `primary_field`, `secondary_field`, `redcap_fetch_error`.

**UI (`redcap_patient_ids.html`):**
- Summary stat cards: Total patients enrolled, Mapped count (server-rendered), REDCap records count.
- Legend: Auto-matched (green), Saved (blue), Unmatched (grey).
- Read-only table: patient name, SATHI ID, current mapped REDCap ID, status badge, actions.
  - Auto-matched rows highlighted green; saved (manual) rows highlighted blue.
  - **Edit / Assign** button per row opens a modal dialog for that patient.
  - **Clear** button (with confirmation) posts `action=clear` for mapped rows only.
- **Modal dialog** (single patient at a time):
  - Header shows patient name; read-only patient info block shows name + SATHI ID.
  - Search input (`#modal-search`) filters the listbox in real-time.
  - Scrollable div-based listbox (`#modal-listbox`, `max-height: 160px`) — no native `<select>` dropdown popup, no z-index/positioning issues.
  - Hidden input (`#modal-hidden-val`) carries the selected value on submit.
  - Falls back to a plain text input when `redcap_fetch_error` is set.
  - Closes on Cancel, backdrop click, or Escape key.
- Mapped count displayed as `X / Y patients mapped` below the table (server-rendered, no JS dependency).

#### Steps 9–11 — Export (initial implementation)
- `redcap_export` view and `redcap_export.html` template: UI to select form mappings and trigger export.
- `ExportTypeChoices`: `MANUAL` (CSV download) and `AUTOMATIC` (API).
- **CSV export** (`_build_csv_export`): wide-format CSV with `record_id`, `redcap_event_name`, `redcap_repeat_instrument`, `redcap_repeat_instance`, and one column per mapped REDCap field. All submissions for all patients with a study ID mapping are included.
- **API export** (`_run_api_export`): imports rows via PyCap `import_records()`.
- **Transaction logging** (`RedcapDataExportLog`): records patient, user, form mapping, export type, start/end time, status (`pending/completed/incomplete/failed`), and raw response log. Last 50 logs shown on export page.
- `submission_date_field` / `submission_date_format` written to model and now used in `_collect_export_rows` to populate the submission date column.

#### Submission date column in export
- `_collect_export_rows` reads `fm.submission_date_field` and `fm.submission_date_format` and writes the formatted `QuestionnaireSubmission.submission_date` into the row.
- Format mapping via `_SUBMISSION_DATE_FORMATS` dict: `date_ymd` → `%Y-%m-%d`, `datetime_ymd` → `%Y-%m-%d %H:%M`, `datetime_seconds_ymd` → `%Y-%m-%d %H:%M:%S`.
- Field is only written if `submission_date_field`, a resolved format, and a non-null `submission_date` are all present.

#### Cleanup — `RedcapFieldToItemMapping` legacy submission date fields removed
- `submission_date_field` and `submission_date_format` removed from `RedcapFieldToItemMapping` model (migration `0022`).
- `is_submission_date_field` extra field, `clean()` logic, and `save()` override removed from `RedcapFieldToItemMappingForm`.

#### Step 5 / Step 8 — `RedcapInstanceToSubmissionMapping` model ✅
- Model `RedcapInstanceToSubmissionMapping` created and migrated.
- **Fields:**
  - `questionnaire_submission` FK → `promapp.QuestionnaireSubmission` (CASCADE): the specific SATHI submission. Links to user → patient, so patient is implicit via this chain.
  - `redcap_form` FK → `RedcapFormToQuestionnaireMapping` (CASCADE): provides `redcap_form_name`, event flags, and `redcap_date_mapping_field`.
  - `data_access_group` CharField (nullable): DAG for the submission.
  - `redcap_patient_id` `EncryptedCharField` (nullable): resolved REDCap study ID, stored encrypted.
  - `redcap_event_name` CharField (nullable): specific REDCap event this submission maps to.
  - `redcap_repeat_instance` PositiveIntegerField (nullable): repeat instance number.
  - `redcap_repeat_event` PositiveIntegerField (nullable): repeating event ID if applicable.
  - `created_at` / `modified_at` auto timestamps.

#### Security changes to existing models
- `RedcapStudyIDtoPatientIDMap.redcap_study_id` changed to `secured_fields.EncryptedCharField` — decrypts transparently in Python; no view/form changes needed as it is never used in an ORM filter lookup.
- `RedcapInstanceToSubmissionMapping.redcap_patient_id` stored as `EncryptedCharField` from the start.
- `redcap_project_info` remains a plain `models.JSONField` (encryption attempt reverted due to migration complexity with existing data).

---

#### Step 5 / Step 8 — Matching UI and algorithm ✅

**URL**: `projects/<pk>/redcap/<mapping_pk>/patient-ids/<patient_pk>/match/` → `redcap_match_submissions`

**Entry point**: Patient IDs page — mapped rows now show **Edit | Match | Clear**. "Match" is only shown when a study ID is already assigned.

**View logic (`redcap_match_submissions`):**
- Guards: patient must be enrolled in project and have a study ID mapped; redirects with error message otherwise.
- Builds `_metadata_field_to_form` lookup from `redcap_project_info['metadata']` — resolves which REDCap form actually owns `redcap_date_mapping_field` (it may differ from the questionnaire form).
- For each `RedcapFormToQuestionnaireMapping` under this project, skips forms with no submissions for this patient.
- **Two PyCap calls per form mapping:**
  1. Fetch questionnaire form (`fm.redcap_form_name`) records for this patient → build `event_to_instances = {event_name: [instance_ints]}` (all existing instances across all events).
  2. Fetch date-field form (`date_field_form_name`) records for this patient → build `event_to_date = {event_name: date_str}` (one date per event).
  3. Combine → `rc_instances` list of `{event, instance, date_str}`.
- **Two-pass suggestion for unconfirmed rows (submissions ordered by date ascending):**
  - Pass 1: for each submission, find the event whose date is closest to `submission_date` (absolute delta in seconds); default to `fm.redcap_event_name` or first available event if no date data.
  - Pass 2: within each event, auto-increment instance counter (earliest submission for that event = 1, next = 2, etc.).
- Existing `RedcapInstanceToSubmissionMapping` rows loaded as "Saved" and pre-populate event/instance; these are still editable.
- **Available events** for dropdown built from `redcap_project_info['events']` (preferred, authoritative order); fallback to events seen in `rc_instances`, then `fm.redcap_event_name`.
- POST: `get_or_create` + `save` per (submission, form_mapping) pair — idempotent, supports re-editing.

**Template (`redcap_match_submissions.html`):**
- One card per form mapping showing questionnaire name, REDCap form, event, repeating flags, and date field.
- Table columns: Submission date | Event name (dropdown) | Repeat instance (number input) | Status.
- Event column: `<select>` populated from `available_events` — prevents typos, constrained to valid event names.
- Instance column: editable number input, auto-filled by server-side suggestion; user can override.
- Status badge: "✓ Saved" (green) for previously confirmed rows, "⚡ Suggested" (amber) for new auto-suggestions.
- Collapsible reference table showing all available REDCap instances with their event name and date field value — column header shows `field_name (form_name)` resolved from metadata.
- **JS (`recalcInstances`)**: on any event dropdown change, recalculates all instance numbers for that form card sequentially in DOM order (= submission date order), grouped by event name. Applies to all rows including previously saved ones.

#### REDCap API utility layer ✅

All PyCap calls have been extracted from `views.py` into `patientapp/redcap_utils.py`. `views.py` no longer contains any `import redcap` statements.

**File**: `patientapp/redcap_utils.py`

| Function | Purpose |
|---|---|
| `get_redcap_project(mapping)` | Instantiates and returns a `pycap.Project` from a `ProjectRedcapMapping`. |
| `fetch_project_metadata(mapping)` | Full metadata fetch: `project_info`, `instruments`, `metadata`, `dags`, `events`, `repeating`. Returns `(info_payload, record_count)`. |
| `fetch_patient_id_records(mapping)` | Exports all records with primary/secondary ID fields; deduplicates by primary. Returns `[{primary, secondary}]`. |
| `fetch_form_instances(mapping, record_id, form_name, ...)` | Exports all records for a specific patient and form across all events. Returns raw PyCap record list. |
| `fetch_field_values_for_record(mapping, record_id, field_name, form_name, ...)` | Fetches a single field across all events for a patient. Returns `{event_name: value_str}`. |
| `import_records(mapping, rows)` | Imports a list of record dicts into REDCap via PyCap. Returns PyCap response. |

**Views refactored:**
- `redcap_project_setup` → `fetch_project_metadata`
- `redcap_fetch_metadata` (HTMX) → `fetch_project_metadata`
- `redcap_patient_ids` → `fetch_patient_id_records`
- `redcap_match_submissions` → `fetch_form_instances` + `fetch_field_values_for_record`
- `_run_api_export` → `import_records`

**Bug fix post-refactor:** `redcap_patient_ids` passed `primary_field` and `secondary_field` to the template context. These variables had been defined inside the old inline PyCap block and were silently removed during extraction. Fixed by restoring them directly from `mapping.redcap_study_id_field` and `mapping.redcap_secondary_id_field` before the fetch call.

---

### ⏳ Pending / Next Steps

#### Export — per-submission `redcap_event_name` + `redcap_repeat_instance` from `RedcapInstanceToSubmissionMapping` ✅

`_collect_export_rows` now reads per-submission event and instance values from `RedcapInstanceToSubmissionMapping` instead of using the form-mapping-level defaults.

**Implementation (`patientapp/views.py` → `_collect_export_rows`):**
- For each `fm` (form mapping), pre-fetches all `RedcapInstanceToSubmissionMapping` rows for that `fm` + the current submission queryset in a single DB query → `instance_map = {submission_id: obj}`.
- **`redcap_event_name`**: uses `inst_mapping.redcap_event_name` if present; falls back to `fm.redcap_event_name` (e.g. submissions not yet matched).
- **`redcap_repeat_instance`**: uses `inst_mapping.redcap_repeat_instance` if present and non-null; falls back to `''` for unmatched submissions.
- Fallback behaviour ensures export still produces a row for submissions without a confirmed match (with empty instance), rather than silently dropping them.

#### Export — per-patient export workflow ✅

`redcap_export` now supports explicit patient selection before export.

**View (`patientapp/views.py` → `redcap_export`):**
- Pre-fetches all `RedcapStudyIDtoPatientIDMap` rows with `select_related('patient')` on both GET and POST (single shared queryset).
- Builds `mappable_patients = [{patient, redcap_study_id}]` and passes it to the template on GET.
- On POST: reads `patient_pks` checkbox list. If any are checked, filters `id_map` to only those patients (UUID-safe parsing). If none are checked, falls back to exporting all mapped patients.
- Returns an error message and redirects if the resulting `id_map` is empty (no valid patients).

**Template (`redcap_export.html`):**
- New **"Select Patients to Export"** card inserted between the form mappings card and export method card.
- Scrollable checklist (`max-h-64`) — one row per mapped patient showing name, SATHI ID (monospace), and REDCap study ID.
- **Select All / Deselect All** buttons for convenience.
- Pluralised count hint: *"N patients mapped. Leave all unchecked to export all."*
- Empty state message if no patients have a study ID assigned yet.
- Vanilla JS in `{% block extra_js %}` wires the two toggle buttons.

#### Export — unmatched submission safety warning ✅

Pre-export and at-export detection of submissions belonging to repeating/event forms that have no `RedcapInstanceToSubmissionMapping` row.

**View (`patientapp/views.py` → `redcap_export`):**
- `_get_unmatched_warnings(fms_qs, patient_id_set)` helper: iterates form mappings that have any of `redcap_form_is_in_event`, `redcap_form_is_repeating`, or `redcap_event_is_repeating` set; for each, queries submissions for the given patients, fetches matched submission IDs in one query, and returns a list of `{patient, fm, submission_date, match_url}` dicts for any gaps.
- On **GET**: runs against all form mappings + all mapped patients → `unmatched_warnings` passed to template (shown as a passive advisory table).
- On **POST** (first submit, no `confirm_unmatched`): re-runs scoped to the selected forms + selected patients. If any unmatched found, re-renders with `show_unmatched_confirm=True` and re-injects `form_mapping_ids`, `patient_pks`, `export_type` as hidden inputs so no selections are lost.
- On **POST** (second submit, `confirm_unmatched` checked): skips the gate and proceeds with export.

**Template (`redcap_export.html`):**
- Orange warning card appears above the form cards whenever `unmatched_warnings` is non-empty.
- Table columns: Patient | Form | Submission Date | Action ("Match →" opens match page in new tab).
- When `show_unmatched_confirm` is set (after first submit attempt): confirm checkbox + "Proceed with Export" (danger) + "Cancel" link appear inside the warning card. Hidden inputs preserve prior selections.
- No warning shown when all submissions are matched.

#### Export — pre-flight validation ✅

Guards added to the POST handler in `redcap_export`:
- Hard error (redirect + message) if no `form_mapping_ids` are submitted.
- Non-blocking `messages.warning` if any selected fm has zero field mappings — export proceeds but user is alerted.

#### Export — log table "Match →" link ✅

Added **Actions** column to the Recent Export Log table in `redcap_export.html`. Each row with a `patient` FK set shows a "Match →" link pointing to `redcap_match_submissions` for that patient, opening in the same tab.

#### Export — REDCap dashboard per-fm matching status ✅

`redcap_project_dashboard` view now:
- Pre-fetches `RedcapStudyIDtoPatientIDMap` rows per mapping to determine the patient set.
- For each `RedcapFormToQuestionnaireMapping`, counts total submissions and matched `RedcapInstanceToSubmissionMapping` rows.
- Attaches `m.fm_stats = [{fm, total, matched}]` directly to each mapping object (avoids Django template dict-key-lookup limitation).

Dashboard card now shows a **"Form Mapping Status"** section per mapping:
- 🟢 `✓ X/Y matched` — all matched
- 🟡 `X/Y matched` — partial
- 🔴 `0/Y matched` — none matched
- Grey `No submissions` — no submissions exist yet
- "Match →" link to Patient IDs page per row.

#### Export — method driven by `ProjectRedcapMapping.export_type` ✅

The "Export Method" card in `redcap_export.html` no longer shows interactive radio buttons. The export type is driven entirely by `mapping.export_type`:
- A `<input type="hidden" name="export_type">` carries the configured value.
- Both options rendered as read-only display items — the active one highlighted (blue border + filled dot), the inactive one dimmed (`opacity-50`).
- Extra warning shown if `export_type == AUTOMATIC` but `redcap_project_token_allows_import` is `False`.
- Link to the REDCap configuration edit page so users know where to change it.

#### Export — per-patient log entries ✅

**Bug:** `_build_csv_export` created no log entries at all. `_run_api_export` created one log entry per form mapping with `patient=None` — the `log` variable was overwritten on each iteration of the patient loop, so only the last patient's log was updated with status.

**Fix (`patientapp/views.py`):**
- Both `_build_csv_export` and `_run_api_export` now create **one `RedcapDataExportLog` entry per patient per form mapping**.
- Both functions build `patient_map = {pk: Patient}` from `id_map` keys and query which patients have submissions for each fm.
- **CSV**: log entries built as a list and written via `bulk_create` after the CSV response is constructed. All entries have `export_status=COMPLETED`.
- **API**: log entries created individually (PENDING) before the API call; after success/failure all entries for that fm are updated together with the same status, log text, and completion timestamp — no more single-variable overwrite bug.

---

## 🔧 Corrections & Bug Fixes

#### `redcap_date_mapping_field` — constraint, UX, and help text ✅
**Issue:** The original `CheckConstraint` enforced that `redcap_date_mapping_field` was *required* when `redcap_form_is_in_event=True`. This was too strict — the field is optional and its purpose was not clearly communicated to users. The constraint was removed, but no replacement guidance was in place.

**Fixes applied:**
- **`models.py`**: Replaced the "required when in event" constraint with a softer "only allowed when relevant" constraint:
  - `redcap_date_mapping_field` may only be non-empty when at least one of `redcap_form_is_in_event`, `redcap_form_is_repeating`, or `redcap_event_is_repeating` is `True`.
  - Migration applied.
  - Updated `help_text` to clearly explain the purpose of the field.
- **`forms.py`**: Updated `redcap_date_mapping_field` `help_text` to match — explains the visit-date proximity matching purpose, that the field is optional, and that it may belong to a different REDCap form.
- **`redcap_form_mapping_form.html`**: Wrapped the field in a container (`#date_mapping_field_section`) that is hidden by default. Shown via JS only when `applyMeta` detects any of the three flags is `True`. In edit mode, visibility is restored from saved Django model flags. A blue info box explains the purpose in plain language.
- **`wizard/step3_form_mapping.html`**: Same treatment for both the "Add" (`#add_date_mapping_section`) and "Edit" (`#edit_date_mapping_section`) panels. `toggleDateSection(prefix, show)` helper added to the shared `applyMeta` JS function.

#### Date-proximity matching — algorithm review and fixes ✅

**How matching works (`redcap_match_submissions`):**

When `redcap_date_mapping_field` is configured on a `RedcapFormToQuestionnaireMapping`, the matching page uses a two-pass algorithm to auto-suggest which REDCap event/instance each questionnaire submission belongs to.

**Two REDCap API calls per form mapping:**
1. **Call 1** — fetches all existing `(event_name, repeat_instance)` pairs for the questionnaire form for this patient → `event_to_instances`.
2. **Call 2** — fetches the date field values across all events/instances via `fetch_field_values_for_record` → `event_to_date`.

**Pass 1 — event assignment (per unconfirmed submission):**
- For each unmatched submission, iterates all `rc_instances` entries that have a date string.
- Parses each REDCap date (datetime or date-only) and computes `abs(submission_date - rc_date)` in seconds.
- Picks the event/instance with the **smallest delta**.
- **30-day threshold**: if the closest date is more than 30 days away, no suggestion is made — falls back to `fm.redcap_event_name` or the first available event. The user must manually assign.
- If `redcap_date_mapping_field` is not set at all, all submissions default to the configured event name and the user reviews manually.

**Pass 2 — instance numbering:**
- Only runs if `redcap_form_is_repeating` or `redcap_event_is_repeating` is `True`.
- First builds `existing_max = {event: max_instance}` from the REDCap instances already fetched.
- Starts the per-event counter from `existing_max[event]` (not from 0), so new suggestions start at `max + 1` and never collide with instances already present in REDCap.
- Submissions sorted ascending by `submission_date` — earlier submissions get lower instance numbers within the same event.

**Bugs fixed in this review:**

1. **`fetch_field_values_for_record` repeated-event overwrite (`redcap_utils.py`):**
   - Old: returned `{event_name: date_str}` — for repeating events with multiple instances, each loop iteration overwrote the previous, keeping only the last instance's date.
   - Fix: returns `{(event_name, instance_int_or_None): date_str}` — each `(event, instance)` pair gets its own entry. Non-repeating events use `(event, None)` as key.
   - The combine step in `views.py` looks up `(ev, inst)` first, then falls back to `(ev, None)` for non-repeating contexts.

2. **Pass 2 started instance counter from 1 regardless of existing REDCap data:**
   - Old: `event_counter = {}` → first suggestion always got instance 1, colliding with existing REDCap records.
   - Fix: `event_counter = dict(existing_max)` → counter starts from the highest existing instance per event.

3. **No threshold on date proximity (pre-existing):**
   - Old: any submission was always matched to *some* event, even if 6 months away.
   - Fix: `_MATCH_THRESHOLD_SECONDS = 30 * 86400`. If no match within 30 days, falls back to configured default event rather than silently assigning a distant one.

#### PyCap refactor — missing `primary_field` / `secondary_field` variables ✅
**Issue:** After extracting inline PyCap calls into `redcap_utils.py`, `primary_field` and `secondary_field` local variables (previously defined inside the old fetch block) were silently removed from `redcap_patient_ids`. These were still passed in the template context, causing a `NameError`.

**Fix:** Restored both variables directly from `mapping.redcap_study_id_field` and `mapping.redcap_secondary_id_field` before the `fetch_patient_id_records` call.

---

#### Export — mixed-project repeating instrument/event handling ✅

**Issue:** Projects with a mixed structure (some events repeating, others not, or some instruments repeating only in specific events) were not handled correctly during export. `_collect_export_rows` used the `RedcapFormToQuestionnaireMapping` flags (`redcap_form_is_repeating`, `redcap_event_is_repeating`) which are form-level, not per-event. This meant:
- A form marked as repeating would always emit `redcap_repeat_instrument` / `redcap_repeat_instance`, even for events in which it does not repeat.
- REDCap rejects rows where these columns have values for non-repeating events.
- Additionally, when the **entire event** repeats (not just one instrument), `redcap_repeat_instrument` must be **blank** but `redcap_repeat_instance` must still be populated — the old code set `redcap_repeat_instrument` to `fm.redcap_form_name` in both cases.

**Fix (`patientapp/views.py` → `_collect_export_rows`):**
- `event_name` is now resolved per-submission (from `inst_mapping.redcap_event_name` or `fm.redcap_event_name`) before the repeating check, so it is available for lookup.
- The `redcap_project_info['repeating']` list is parsed inline into two sets:
  - `_repeating_instruments`: `{(event_name, form_name)}` — entries that have a non-empty `form_name`.
  - `_repeating_events`: `{event_name}` — entries that have an empty `form_name` (whole event repeats).
- Three distinct cases handled per submission:

| Condition | `redcap_repeat_instrument` | `redcap_repeat_instance` |
|---|---|---|
| `_instrument_repeats` — `(event_name, form_name)` in `_repeating_instruments` | `form_name` | instance number |
| `_event_repeats` — `event_name` in `_repeating_events` | `""` (blank) | instance number |
| Neither (non-repeating event in mixed project) | `""` (blank) | `""` (blank) |

- **Fallback**: if `redcap_project_info['repeating']` is empty or no `event_name` is available, falls back to the original `fm` flag behaviour (`fm.redcap_form_is_repeating` / `fm.redcap_event_is_repeating`) to preserve backwards compatibility with simple single-event projects.

---

#### Matching — Pass 1 discarded matched instance number ✅

**Issue:** In `redcap_match_submissions`, Pass 1 (date-proximity) correctly identified the closest REDCap event **and** instance for each submission, but only stored `best_event` — the matched `inst['instance']` was discarded. Pass 2 then treated the row as having no instance (`suggested_instance is None`) and incremented the per-event counter, producing a suggestion one higher than the actual match.

**Example:** `additional_visits_arm_1` had existing instances 1 (2024-11-14) and 2 (2026-03-18). A submission with date 2026-03-18 correctly matched event instance 2 in Pass 1, but Pass 2 incremented from `existing_max = 2` to `3`.

**Fix (`patientapp/views.py` → `redcap_match_submissions`):**
- Pass 1 now also captures `best_instance = inst['instance']` alongside `best_event` when a date match is found.
- `suggested_instance` is initialised to `None`; if Pass 1 finds a match, it is set to the matched instance integer.
- Pass 2 already guards with `if row['suggested_instance'] is None` — rows where Pass 1 found a direct match are skipped entirely.
- Rows with no date match (e.g. no `redcap_date_mapping_field` configured, or submission beyond the 30-day threshold) still go through Pass 2 and receive an auto-incremented instance starting from `existing_max + 1`.