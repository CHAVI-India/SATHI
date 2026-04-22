Patient Management
==================

.. contents:: Table of Contents
   :local:
   :depth: 2

This page explains how to find patients, add new patients, view and update their details, and manage diagnoses and treatments.

.. note::
   The actions available to you depend on your permissions. If a button described here is not visible, contact your administrator.

---

The Patient List
-----------------

The **Patients** page is your main starting point. Click **Patients** in the navigation menu to open it.

Searching and Filtering
~~~~~~~~~~~~~~~~~~~~~~~~

Use the **Search Patient by Name or ID** box to find a specific patient — start typing and select from the dropdown. The list updates immediately.

You can also narrow the list using these filters:

- **Institution** — Show only patients from a specific institution.
- **Gender** — Filter by gender.
- **Questionnaires** — Filter by how many questionnaires a patient has assigned (None, 1–5, 6–10, 10+).
- **Diagnosis** — Filter by a diagnosis name.
- **Treatment Type** — Filter by a type of treatment.
- **Sort By** — Sort the list by name (A–Z or Z–A) or by number of questionnaires assigned.

Any combination of filters can be applied at once. The list shows 25 patients per page with pagination controls at the bottom.

Actions from the Patient List
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Each row in the patient table has two action buttons:

- **View Patient** — Opens the patient's detail page.
- **Manage Questionnaires** — Opens the questionnaire management page for that patient directly (only shown if you have the required permission).

The top of the page also has:

- **Schedule Calendar** — A calendar view showing all scheduled questionnaire dates across all patients.
- **Add Patient** — Opens the form to register a new patient (requires permission).

---

Adding a New Patient
---------------------

Click the **Add Patient** button on the Patients page. You will need to fill in:

**User Account Information**

- **Username** — A unique login username for the patient. Must not already exist in the system.
- **Email** — The patient's email address. Must not already be registered.
- **Password / Repeat Password** — Set the patient's initial login password.

**Patient Information**

- **Name** — Full name of the patient.
- **Patient ID** — Your institution's internal identifier for the patient.
- **Age** — Patient's age (0–150).
- **Gender** — Select from: Male, Female, Transgender, Non-binary, Prefer not to say, Other.
- **Institution** — The institution this patient belongs to. If you are a provider, this will be pre-set to your institution.
- **Date of Registration** — Select from the date picker.
- **Preferred Language** — The language the patient's questionnaires will be displayed in.

**User Groups**

Tick the appropriate groups to control what the patient can access in the system.

Once all fields are filled in correctly, submit the form. You will be returned to the patient list with a success message.

.. note::
   The patient's **name** and **patient ID** cannot be changed after creation. Only age, gender, institution, registration date, and preferred language can be updated later.

---

Viewing a Patient's Details
-----------------------------

Click **View Patient** on any row in the patient list, or click a patient's name, to open their detail page.

The detail page shows:

- **Patient Information** card — Patient ID, name, age, gender, institution, date of registration, and preferred language.
- **Diagnoses** section — All diagnoses recorded for the patient, each with its associated treatments.

From the top of the detail page you can also:

- Click **Manage Questionnaires** to assign or schedule questionnaires.
- Click **View PRO Review** to see the patient's questionnaire responses and outcome scores.
- Click **Edit Patient Details** to update basic demographic information.

---

Editing Patient Details
------------------------

Click **Edit Patient Details** on the patient detail page. You can update:

- Age
- Gender
- Institution
- Date of Registration
- Preferred Language

Click **Save** to confirm. You will be returned to the patient detail page with a confirmation message.

.. note::
   The patient's name and patient ID are not editable from this screen. Contact your administrator if these need to be corrected.

---

Managing Diagnoses
-------------------

Diagnoses are shown on the patient detail page. Each diagnosis card displays the diagnosis name, date of diagnosis, and any treatments linked to it.

**Adding a Diagnosis**

1. On the patient detail page, click the **Add Diagnosis** button (opens in a new tab).
2. Select the diagnosis from the **Diagnosis** dropdown (this is a list of pre-configured diagnoses in the system).
3. Enter the **Date of Diagnosis** using the date picker.
4. Click **Save**. The diagnosis will appear on the patient detail page.

.. note::
   If the diagnosis you need is not in the dropdown, ask your administrator to add it to the diagnosis list.

**Editing a Diagnosis**

Click the **Edit Diagnosis** button on the relevant diagnosis card. Update the fields and save. You will be returned to the patient detail page.

.. note::
   Diagnoses cannot be deleted from this interface. Contact your administrator if a diagnosis needs to be removed.

---

Managing Treatments
--------------------

Treatments are linked to individual diagnoses and appear inside each diagnosis card on the patient detail page.

**Adding a Treatment**

1. On the diagnosis card, click **Add Treatment** (opens in a new tab).
2. Fill in the treatment details:

   - **Treatment Type** — Select one or more treatment types from the list (e.g. Surgery, Chemotherapy). You can select multiple types if treatments were delivered at the same time.
   - **Treatment Intent** — Select Preventive, Curative, Palliative, or Other.
   - **Date of Start of Treatment** — Use the date picker. Cannot be a future date.
   - **Currently Ongoing Treatment** — Tick this if the treatment is still in progress. If ticked, do not enter an end date.
   - **Date of End of Treatment** — Required if the treatment is not ongoing. Cannot be before the start date or in the future.

3. Click **Save**. The treatment will appear inside the diagnosis card.

**Editing a Treatment**

Click the **Edit** button on the treatment entry. Update the fields and save. You will be returned to the patient detail page.

.. note::
   Treatments cannot be deleted from this interface. Contact your administrator if a treatment entry needs to be removed.

---

Managing Treatment Types
-------------------------

Treatment types are the options available in the **Treatment Type** dropdown when adding a treatment. This list is managed separately.

To view all treatment types, navigate to the **Treatment Types** page from the admin or navigation menu.

**Adding a Treatment Type**

Click **Add Treatment Type** on the Treatment Types page. Enter the treatment type name and save. The new type will immediately be available in treatment forms.

**Editing a Treatment Type**

Click the **Edit** button next to a treatment type, update the name, and save.

.. note::
   Treatment types cannot be deleted from this interface. Contact your administrator if a type needs to be removed.
