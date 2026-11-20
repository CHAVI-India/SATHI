# Plan: Adding Date, Time, and Date-Time Question Types

**Status:** v2 — reviewed with owner answers; concrete code changes added for review. Still no code changed.
**Goal:** Let patients answer some questions with a proper calendar date (like a birthday), a clock time (like medication time), or both together, instead of typing them as plain text or numbers.

**Decisions confirmed in review:**
1. Standard storage formats approved (Part 1).
2. Patient input must be **component-based** (day / month / year boxes), not a calendar popup — see the Part 4 design spec.
3. Date/time answers do not feed into numeric scores.
4. Both pre-existing problems (Part 14) will be fixed in this work.
5. Date answers in trend charts are handled the same way as text answers (Part 9).

---

## Part 1 — Storage format decision (CONFIRMED)

All date/time answers are stored as text in the standard international format:

- Date answer → `2025-03-14`
- Time answer → `14:30:00` (2:30 PM, always 8 characters with colons)
- Date and time answer → `2025-03-14 14:30:00`

> **Answer:** This is fine.

### Planned code changes
No code in this part — this decision governs Parts 4, 5, 6, 10, 11. One rule for the whole implementation: whenever the system turns a picked date/time into stored text, it uses an explicit format recipe (never Python's default text conversion, which produces awkward text like `0:00:00` for midnight).

---

## Part 2 — The question editor (staff defining new questions) (CONFIRMED)

> **Answer:** This is fine.

### Planned code changes
| File | Change |
|---|---|
| `promapp/models.py` — `Item.clean()` | Add Date/Time/DateTime to the same check that today forbids picking a Likert/Range scale for Text/Number questions, and fix the error wording to name all affected types. |
| `promapp/models.py` — `Item.clean()` (missing value check) | No change needed — it already rejects a missing-value number for non-numeric types. Add an automated check to lock that behavior in. |
| `promapp/forms.py` — `ItemForm` | No functional change; the Likert/Range boxes are already hidden for anything that isn't Likert/Range. Verify only. |
| `promapp/migrations/` (new file) | Run the housekeeping ("migration") step so the database's record of allowed answer types includes the three new ones. Data-safe, no rows touched. |
| `templates/promapp/response_fields.html` | Already renders nothing for unknown types, so the editor will correctly show no scale picker. Verify only. |

---

## Part 3 — Bulk-importing questions from a spreadsheet

> **Answer:** This is fine. Ensure Datetime and time formats are also handled.

### Planned code changes
| File | Change |
|---|---|
| `promapp/resources.py` — `ResponseTypeWidget.clean` | The name→type lookup table is hard-coded with only the old five types. Add entries for the new three, in both short and full-label spellings (case-insensitive): `date`, `date response`, `time`, `time response`, `datetime`, `datetime response`, plus tolerant spellings `date time` / `date time response`. The exact match path already accepts `Date`/`Time`/`DateTime`, but full labels currently fall through and fail the import — this fixes that. |
| Import test data | Add a small CSV fixture importing one item of each new type in short, full-label, and mixed-case spellings. |

---

## Part 4 — The patient answering flow (design spec, per your review)

> **Answer:** This is fine but the design needs some thought. Many patients may find a standard calendar based date picker difficult to handle. It would be better to split the date and date time into components and ask for these specifically. This will also be important in a mobile screen where a calendar is difficult to handle often. We need carefully balance accessibility and usability for people with less familiarity with computers. Theming is to be done and also we need to ensure that after patient enters the answer the question moves to the next question as in other questions.

### Proposed input design — "component boxes, no calendar"

**Date question — three small boxes side by side:**
- `Day` (accepts 1–31), `Month` (accepts 1–12, with the month name echoed under the box as the patient types, in the current language — catches the 03-vs-March confusion), `Year` (4 digits).
- Boxes are large (finger-sized on mobile), use a big readable font matching today's question style, and pop up the **number keypad** on phones (numeric keyboard hint, no letters).
- A small **"Today"** link fills all three boxes for questions like "today's symptom date".
- Order Day–Month–Year (unambiguous when labelled; labels remove the US/international confusion entirely).

**Time question — two required boxes + one optional:**
- `Hour` (0–23) and `Minute` (0–59) required; `Second` optional (blank means :00). Shown as `Hour : Minute : Second` with colon separators printed between boxes. 24-hour numbers with the equivalent am/pm hint echoed under the boxes (translated).

**Date & time question — both groups stacked:** the three date boxes on one row, the time boxes below.

**Behavior (must match today's feel):**
- When the last required box gets a valid value, the page assembles the standard-format answer (Part 1) into the question's hidden answer field **and triggers the existing "answer given → move to next question" behavior** — same as Likert/radio today.
- Back-navigation re-fills the boxes from what was entered, including after a skipped-and-returned answer.
- Per-box gentle errors ("Day should be between 1 and 31", "There is no 30 February") shown under the box; auto-advance pauses until fixed.
- **Works without JavaScript:** the boxes themselves are submitted (as separate day/month/year parts) and the server assembles the answer too, so patients with JavaScript off, broken scripts, or text-only browsers are never blocked. Server-side assembly is the official value of record; the in-page assembly only drives auto-advance.

**Accessibility:**
- Each group is a labelled fieldset whose legend is the question text; each box has its own visible label (translated: Day/Month/Year/Hour/Minute/Second) — screen readers read "Question… Day edit text" cleanly.
- Errors are linked to the box (aria-describedby) and announced; no keyboard traps; tab order Day→Month→Year→(Hour→Minute→Second)→next.
- Meets contrast and touch-target sizes from the existing design system.

**Theming:** uses the current Tailwind look (same border radius, focus ring, large text as existing answer inputs), so the boxes feel native to the questionnaire; no new visual language.

### Planned code changes
| File | Change |
|---|---|
| `promapp/forms.py` — `QuestionnaireResponseForm.__init__` | Add fields for Date/Time/Date-time questions (standard date/time form fields). In `clean()`, when the separate day/month/year/hour/minute/second parts arrive instead of a single value, assemble and validate them server-side into the Part 1 formats. |
| `promapp/views.py` — `QuestionnaireResponseView.post` (~line 1839) | Save using the explicit format recipes (Part 1) instead of Python's default text conversion. |
| `templates/promapp/questionnaire_response.html` — rendering (~lines 201–560) | New display branches for the three types: the component-box layouts above, plus a hidden standard-format answer field per question. |
| Same file — script (~lines 785–940) | Extend the existing change/auto-advance and submit-collection scripts: listen on component boxes, assemble the hidden answer when complete and valid, hand it to the **existing** rule-evaluation and next-question flow unchanged. |
| `locale/` (all languages) | New on-screen strings (Day, Month, Year, Hour, Minute, Second, Today, per-box error messages) added for translation. |

---

## Part 5 — Staff entering answers on behalf of patients (CONFIRMED)

> **Answer:** This is fine. Here a simple date picker can be used or the same widget for the patient answering used.

**Recommendation:** staff screens use the browser's **simple built-in pickers** (single date box, single time box, combined date-time box) — fast for trained users; storage format identical to the patient flow. One shared code path for saving, so the two flows can never disagree.

### Planned code changes
| File | Change |
|---|---|
| `promapp/forms.py` — `StaffQuestionnaireResponseForm.__init__` (~line 1276) | Add the three new question types with simple built-in picker inputs (date, time, date-time). |
| `templates/promapp/staff_questionnaire_response.html` (~lines 181–260) | Add display branches rendering the simple pickers. |
| `promapp/views.py` — `StaffQuestionnaireResponseView.post` (~line 5225) | Same explicit format recipes as the patient view. |
| `promapp/views.py` — the staff view's translated-items helper (~line 5105) | Verify only: date types need no translation handling (no scales involved). |

---

## Part 6 — Questions that appear or hide based on earlier answers (CONFIRMED)

> **Answer:** This is fine.

### Planned code changes
| File | Change |
|---|---|
| `promapp/forms.py` — `QuestionnaireItemRuleForm.clean` (~line 746) | New validation branches: when the earlier question is Date/Time/Date-time, the comparison value must be a well-formed date/time written in the standard format (helpful example shown in the message, e.g. `2025-03-14`). |
| `promapp/views.py` — `validate_rule_operator` (~line 3344) | The instant-feedback text distinguishes only "numeric" vs "text"; add a "date/time comparison" message for the new types. |
| `promapp/views.py` — `validate_comparison_value` (~line 3368) | Add the live-check branches for date/time/date-time values (mirrors the form rule above). |
| `promapp/views.py` — `evaluate_question_rules` (~lines 3699 and 3744, both the single-rule and rule-group copies) | Before comparing, convert both the stored answer and the comparison value into real dates/times (accepting the standard format, plus a few tolerant variants) and compare properly, so "after / before / on" mean calendar reality — not letter-order of text. Unparseable values keep today's safe fallback (rule skipped, question shown). |

---

## Part 7 — Scores and formulas (CONFIRMED — dates never affect scores)

> **Answer:** This is fine.

### Planned code changes
| File | Change |
|---|---|
| `promapp/models.py` | **No functional change**: scoring already only reads Number/Likert/Range items, and equation builders list the new types as unusable (correct, per decision). Automated checks added to lock this in. |
| Same file — `calculate_scores_for_submission` log | Cosmetic only: the per-response debug log already prints the type, so date items are visibly ignored. Verify only. |
| `promapp/views.py` — `ConstructEquationView` (~line 4731) | No change; verify date items land in the editor's "not usable" list without errors. |
| Completion counting (`promapp/views.py` `StatisticsView`) | No change: "answered" = any stored text, which dates satisfy. Automated check added. |

---

## Part 8 — Viewing results: staff dashboards and patient portal

*(No comment on this part — proceeding as originally proposed.)*

### Planned code changes
| File | Change |
|---|---|
| `templates/promapp/components/date_item_card.html` (new) | A small answer card for date/time answers, modeled on the existing text card: question, the formatted answer in readable style (e.g. "14 March 2025", "2:30 PM"), no numeric bar. |
| `templates/promapp/components/item_results_section.html` (lines 18–45), `topline_vertical_tabs.html` and `other_constructs_vertical_tabs.html` (~lines 320–327) | Add a Date/Time/Date-time branch pointing at the new card (today these answer types render **nothing** in all three views). |
| `templates/cotton/hcp_results/construct_fieldset.html` (lines 63–81) | Add the same branch for the HCP review construct view. |
| `templates/patientapp/partials/patient_portal_plots.html` | Show date answers as clean text in the history cards (also fixes the "Numeric" spelling here — see Part 14). |
| `patientapp/views.py` — `prom_review` and `patient_portal` response processing (~lines 380–460 and ~1810–1910) | Treat Date/Time/Date-time like Text answers: shown as-is, no percentage bar, no numeric conversion attempted. Format nicely (day month year / 12-hour hint) at display time only — storage stays standard. |
| `templates/promapp/partials/item_list_table.html` (lines 61–66) | Badge colors for the three new types (distinct hues from the existing set). |

---

## Part 9 — Trend charts over time

> **Answer:** This is fine. Handle these like text responses.

### Planned code changes
| File | Change |
|---|---|
| `patientapp/utils.py` — `create_item_response_plot` (~line 1350) | Explicit branch: Date/Time/Date-time items follow the **same path as Text answers** instead of falling into the numeric plot (which today would silently produce no usable points). No crashes, no fake zeros. |
| `patientapp/views.py` — `patient_portal` (~line 1908 onward, where chart vs media cards are decided) | Route date-type items with the text items so the history card shows the answer as text (Part 8), not a chart placeholder. |

---

## Part 10 — Spreadsheet (CSV) export (CONFIRMED)

> **Answer:** This is fine.

### Planned code changes
| File | Change |
|---|---|
| `promapp/views.py` — `export_questionnaire_responses` | Add the three new types to **both** hard-coded type lists (column headers ~line 3251 and data cells ~line 3312) so their columns appear with the stored standard-format text. Column naming rules unchanged (short code if defined, else "N. question text"). |

---

## Part 11 — REDCap export (CONFIRMED — metadata-driven)

> **Answer:** This is fine. We have the redcap metadata which is used to determine the export format which should help in this regard.

### Planned code changes
| File | Change |
|---|---|
| `patientapp/redcap_utils.py` — `_REDCAP_FORMATS` / `_AUTO_VALIDATED_TEXT_VALIDATIONS` / `validate_and_format_response_value` | The metadata-driven flow already converts our standard stored text to whatever style the mapped REDCap field expects (`date_ymd/mdy/dmy`, `datetime_*`, `time`). Two additions: (a) accept the seconds style time (`HH:MM:SS` → REDCap `time_hhmmss` validation type where a project uses it) and the six-digit style `HHMMSS` as an accepted input for plain time fields; (b) an automated check that a Date, a Time, and a Date-time answer each export cleanly against representative date/time field styles. No change to how metadata drives the conversion. |
| `patientapp/views.py` — export row builder | No change needed: date-type answers flow through the existing transform-and-validate path; clear per-cell error messages already surface on mismatches. |

---

## Part 12 — Statistics and housekeeping (CONFIRMED)

> **Answer:** This is fine.

### Planned code changes
| File | Change |
|---|---|
| `locale/*/LC_MESSAGES/django.po` (all languages) | Extract and add the new strings from Parts 4, 6, 8 (box labels, error texts, card labels) and translate where possible; mark untranslated for review. |
| `promapp/admin.py` | Verify only: answer-type filter/list pick up the new types automatically. |
| `promapp/views.py` — `StatisticsView` | Verify only (see Part 7). |

---

## Part 13 — Safety net (testing) (CONFIRMED)

### Planned code changes — automated checks to add
1. `promapp/tests/`: create/edit items of each new type; editor hides scale pickers; missing-value rejected.
2. Patient flow: submit each new type → stored text exactly matches Part 1 formats (including midnight `00:00:00` and single-digit days); server-side assembly works when only component parts are posted (no-JS path).
3. Staff flow: same round-trip checks with the simple pickers.
4. Rules: after/before/on comparisons across a date answer; tolerant input variants; unparseable comparison keeps question visible.
5. Scoring: a construct with a date member gets the date excluded; answered/missing counts and completion stats unaffected.
6. CSV export: columns present with exact values.
7. REDCap: export of Date/Time/Date-time answers against `date_ymd`, `date_dmy`, `datetime_seconds_ymd`, `time`, `time_hhmmss` field styles, including the six-digit input acceptance.
8. Display smoke checks: the new answer card renders in the three dashboards; charts skip date items like text items.
9. Bulk import fixture per Part 3.

---

## Part 14 — Two pre-existing problems

> **Answer:** Please fix this.

### Planned code changes
| File | Change |
|---|---|
| `patientapp/views.py` (~lines 386 and 1816) and `templates/patientapp/partials/patient_portal_plots.html` (~line 61) | Fix the answer-type spelling from `Numeric` to the system's actual value `Number`, so Number answers get their percentage bars again in the portal and review screens. Use the shared choice constant, not a typed word, so this class of bug can't recur. |
| `promapp/views.py` — `add_item_form` (~line 752) | Remove this dead helper: it points at a template that no longer exists and no page links to it (confirmed absent from the URL table). |

---

## Part 15 — Build order (unchanged)

1. Part 1 (done — decision) + Part 2 (editor + migration)
2. Part 4 + Part 5 (patients and staff can answer) ← biggest user-visible win
3. Part 10 + Part 11 (CSV and REDCap exports correct)
4. Part 8 + Part 9 (all views display and chart sanely)
5. Part 6 (smart hide/show with dates)
6. Part 7 + Part 12 + Part 14 (locks, translations, approved fixes)
7. Part 13 checks accompany every step

---

## Remaining open questions before coding starts

| # | Question | Context |
|---|----------|---------|
| 1 | Seconds box on the patient time input: **optional with blank = :00** (proposed), always hidden (minutes only), or always required? | Part 4; storage is always `HH:MM:SS` either way. |
| 2 | Month-name echo under the Month box and am/pm hint under the time boxes: OK as proposed, or show the raw numbers only? | Part 4 usability aids; both are translated. |
| 3 | "Today" quick-fill link shown on all date questions, or only where staff can flag it per question? | Part 4; per-question flag would need one extra checkbox in the question editor. |


Answers: Seconds optional is ok. If not filled 00 default. Month name echo is ok. Today link would be useful for dates as will some additional defaults for date and date time (not too many to overwhelm)