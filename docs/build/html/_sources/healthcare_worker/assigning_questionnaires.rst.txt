Assigning Questionnaires
=========================

This page explains how to assign questionnaires to a patient, control their visibility, and schedule them for specific dates and times. All of these actions are done from the **Manage Questionnaires** page for a patient.

.. note::
   You need the appropriate permissions to manage questionnaires. If you do not see the **Manage Questionnaires** button, please contact your system administrator.

---

Opening the Manage Questionnaires Page
---------------------------------------

There are two ways to reach the Manage Questionnaires page:

1. **From the Patient List** — Find the patient in the patient list and click the green **Manage Questionnaires** button next to their name.
2. **From the Patient Details page** — Open a patient's record and click the **Manage Questionnaires** button at the top of the page.

Both options take you to the same page, which is titled **"Manage Questionnaires for [Patient Name]"**.

To return to the patient list at any time, click the **Back to Patient List** button in the top-right corner of the page.

---

Understanding the Questionnaire Status Table
---------------------------------------------

The lower section of the page shows a table of all questionnaires available in the system. Each row includes:

- **Questionnaire** — The name and a short description of the questionnaire.
- **Status** — Shows one of three states:

  - **Not Assigned** (grey) — The questionnaire has not been given to this patient.
  - **Hidden** (yellow) — The questionnaire is assigned to the patient, but the patient cannot currently see it.
  - **Displayed** (green) — The questionnaire is assigned and visible to the patient in their account.

- **Assigned Date** — The date the questionnaire was first assigned to this patient.
- **Actions** — Buttons to assign, unassign, or change the visibility of the questionnaire.

---

Assigning a Questionnaire to a Patient
----------------------------------------

1. Find the questionnaire you want to assign in the table.
2. If its status shows **Not Assigned**, click the green **Assign** button in the Actions column.
3. The page will refresh and the questionnaire status will change to **Hidden**.

.. note::
   A newly assigned questionnaire is set to **Hidden** by default. The patient will not see it in their account until you set it to **Displayed** (see below).

---

Making a Questionnaire Visible to the Patient
----------------------------------------------

Once a questionnaire is assigned, you can control whether the patient sees it.

- If the status is **Hidden**, click the **Show** button to make it visible. The status will change to **Displayed**.
- If the status is **Displayed**, click the **Hide** button to hide it from the patient. The status will change to **Hidden**.

This is useful when you want to temporarily stop a patient from seeing a questionnaire without fully removing the assignment.

---

Unassigning a Questionnaire
-----------------------------

1. Find the assigned questionnaire in the table (it will show a **Hidden** or **Displayed** status).
2. Click the red **Unassign** button.
3. A confirmation prompt will appear asking: *"Are you sure you want to unassign this questionnaire?"*
4. Click **OK** to confirm. The questionnaire will be removed from the patient's account and its status will return to **Not Assigned**.

.. warning::
   Unassigning a questionnaire removes it from the patient's account. Any previously created schedules for that questionnaire will also be removed. This action cannot be undone from this page.

---

Scheduling Questionnaires
--------------------------

The **Schedule Questionnaires** section at the top of the page lets you set specific dates and times when a questionnaire should be made available to the patient.

.. note::
   You can only schedule questionnaires that have already been **assigned** to the patient. If no questionnaires appear in the scheduling section, assign at least one questionnaire first (see above).

**Step 1: Select Questionnaires to Schedule**

Tick the checkbox next to one or more questionnaires you want to schedule. Each questionnaire label also shows its **interval restriction** — the minimum required time between two scheduled dates for that questionnaire (e.g., *"Interval: 7 day(s)"*). If there is no restriction, it will say *"No interval restriction"*.

**Step 2: Select Dates and Times**

Click the **"Click to select dates"** field to open the calendar picker. You can:

- Select **multiple dates** by clicking each date you want.
- Set a **time** for each date using the time selector within the calendar.

Selected dates will appear as blue tags below the calendar. To remove a date, click the **✕** button on its tag.

**Step 3: Check for Interval Warnings**

If you select multiple dates for a questionnaire that has an interval restriction, the system will automatically warn you if any two consecutive dates are too close together. A yellow warning box will appear listing the problematic questionnaires and the required minimum gap.

You must resolve all interval warnings before the schedule can be saved.

**Step 4: Create the Schedule**

Click the **Create Schedule** button. The system will create one schedule entry for each combination of selected questionnaire and selected date. If a schedule for an exact questionnaire-and-datetime combination already exists, it will not be duplicated.

A green success message will appear confirming how many schedule entries were created.

---

Viewing and Deleting Existing Schedules
-----------------------------------------

If any schedules have already been set up for the patient, an **Existing Schedules** table will appear between the scheduling form and the questionnaire status table. This table shows:

- **Questionnaire** — The name of the scheduled questionnaire.
- **Scheduled Date** — The date and time the questionnaire is scheduled.
- **Actions** — A **Delete** button to remove that specific schedule entry.

To delete a schedule:

1. Click the red **Delete** button next to the schedule entry you want to remove.
2. A confirmation prompt will appear asking: *"Are you sure you want to delete this schedule?"*
3. Click **OK** to confirm. The schedule entry will be permanently removed.

.. note::
   Deleting a schedule only removes the specific date-and-time entry. The questionnaire remains assigned to the patient and can be rescheduled at any time.
