"""Tests for the one-off fix of legacy free-text clock answers.

Covers ``promapp/time_normalization.py`` (the conversion rules, including the
exact examples from the data-fix request) and the ``fix_time_responses``
management command (dry run by default, --commit, --backup/--restore).
"""

import io
import json
import os
import tempfile

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from promapp.models import (
    Item,
    PatientQuestionnaire,
    Questionnaire,
    QuestionnaireItem,
    QuestionnaireItemResponse,
    QuestionnaireSubmission,
    ResponseTypeChoices,
)
from promapp.time_normalization import (
    MERIDIAN_AM,
    MERIDIAN_AUTO,
    MERIDIAN_CHOICES,
    MERIDIAN_PM,
    normalize_clock_value,
)
from patientapp.models import Institution
from promapp.tests.test_temporal_responses import TEST_ENCRYPTION_KEY, make_patient

from django.test import override_settings


def normalize(raw, meridian=MERIDIAN_AM):
    return normalize_clock_value(raw, meridian=meridian).value


class ClockConversionRuleTests(TestCase):
    """The rules promised to the data fix, both meridians."""

    # ── the examples given for the two production items ───────────────────
    def test_am_item_examples(self):
        for raw in ('0800', '800', '8', '08', '8.0', '930', '9.5'):
            expected = {'930': '09:30:00', '9.5': '09:30:00'}.get(raw, '08:00:00')
            with self.subTest(raw=raw):
                self.assertEqual(normalize(raw, MERIDIAN_AM), expected)

    def test_pm_item_examples(self):
        cases = {
            '8': '20:00:00',
            '800': '20:00:00',
            '0800': '20:00:00',
            '9': '21:00:00',
            '9.5': '21:30:00',   # 9.5 read as half past nine, p.m.
            '9,5': '21:30:00',   # Spanish decimal comma
            '2230': '22:30:00',  # already 24-hour: left alone
            '21:30': '21:30:00',  # already a time: seconds padded
        }
        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(normalize(raw, MERIDIAN_PM), expected)

    # ── shapes we should also survive ────────────────────────────────────
    def test_four_digit_is_read_as_hhmm_not_hmm(self):
        self.assertEqual(normalize('1230', MERIDIAN_AUTO), '12:30:00')
        self.assertEqual(normalize('0030', MERIDIAN_AUTO), '00:30:00')

    def test_two_digit_is_hours_only(self):
        self.assertEqual(normalize('11', MERIDIAN_AUTO), '11:00:00')

    def test_half_hour_and_quarter_variants(self):
        # One decimal digit is a fraction of an hour (9.5 = half past), two
        # digits are read as minutes the way people type "9.45", and only
        # when they cannot be minutes does the fraction reading kick in.
        self.assertEqual(normalize('9.5', MERIDIAN_AUTO), '09:30:00')
        self.assertEqual(normalize('9.75', MERIDIAN_AUTO), '09:45:00')
        self.assertEqual(normalize('9.45', MERIDIAN_AUTO), '09:45:00')
        self.assertEqual(normalize('9.25', MERIDIAN_AUTO), '09:25:00')
        self.assertIn('decimal', normalize_clock_value(
            '9.25', MERIDIAN_AUTO).reason)

    def test_midnight_and_noon(self):
        self.assertEqual(normalize('0', MERIDIAN_PM), '00:00:00')
        self.assertEqual(normalize('0000', MERIDIAN_PM), '00:00:00')
        self.assertEqual(normalize('12', MERIDIAN_PM), '12:00:00')

    def test_explicit_marker_beats_the_item_meridian(self):
        self.assertEqual(normalize('2:30 pm', MERIDIAN_AM), '14:30:00')
        self.assertEqual(normalize('2:30 PM', MERIDIAN_PM), '14:30:00')
        self.assertEqual(normalize('9 a.m.', MERIDIAN_PM), '09:00:00')
        self.assertEqual(normalize('12 pm', MERIDIAN_AUTO), '12:00:00')
        self.assertEqual(normalize('12 am', MERIDIAN_AUTO), '00:00:00')

    def test_spanish_wording(self):
        self.assertEqual(normalize('10 de la noche', MERIDIAN_AUTO), '22:00:00')
        self.assertEqual(normalize('9 de la mañana', MERIDIAN_AUTO), '09:00:00')

    def test_hours_notation(self):
        self.assertEqual(normalize('9h30', MERIDIAN_AUTO), '09:30:00')
        self.assertEqual(normalize('9 h', MERIDIAN_AUTO), '09:00:00')

    # ── safety rails ─────────────────────────────────────────────────────
    def test_idempotent_on_canonical_values(self):
        for raw in ('08:00:00', '00:00:00', '23:59:59'):
            result = normalize_clock_value(raw, MERIDIAN_PM)
            self.assertEqual(result.value, raw)
            self.assertEqual(result.action, 'unchanged')

    def test_colon_values_keep_their_hour_unless_asked_otherwise(self):
        # A typed colon means the writer used the time convention already.
        self.assertEqual(normalize('8:00', MERIDIAN_PM), '08:00:00')
        shifted = normalize_clock_value('8:00', MERIDIAN_PM, shift_colon=True)
        self.assertEqual(shifted.value, '20:00:00')

    def test_impossible_and_unreadable_values_are_left_alone(self):
        for raw in ('99', '9325', '12345', 'ayer', 'no recuerdo', None, ''):
            result = normalize_clock_value(raw, MERIDIAN_PM)
            with self.subTest(raw=raw):
                self.assertIn(result.action, ('review', 'skip'))
                self.assertIsNone(result.value if result.action == 'review'
                                  else None)

    def test_never_produces_something_the_exporter_rejects(self):
        """Whatever we write must pass the REDCap time validator."""
        from patientapp.redcap_utils import validate_and_format_response_value

        for raw in ('0800', '800', '8', '9.5', '9,5', '2230', '930', '12',
                    '0', '9.75', '8:00', '2:30 pm', '10 de la noche', '9h30'):
            for meridian in MERIDIAN_CHOICES:
                value = normalize_clock_value(raw, meridian=meridian).value
                if value is None:
                    continue
                with self.subTest(raw=raw, meridian=meridian):
                    formatted, error = validate_and_format_response_value(
                        value, 'text', 'time_hhmmss', [])
                    self.assertIsNone(error, f'{raw} -> {value}: {error}')
                    self.assertEqual(formatted, value)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_ENCRYPTION_KEY)
class FixTimeResponsesCommandTests(TestCase):
    """The management command end to end, on real rows."""

    def setUp(self):
        self.institution = Institution.objects.create(name='Fix Inst')
        self.patient = make_patient(self.institution, 'fixtime')
        self.user = get_user_model().objects.create_user(
            username='fixtime', email='f@e.com', password='pw')
        self.q = Questionnaire.objects.create(name='Sleep Q')
        self.pq = PatientQuestionnaire.objects.create(
            patient=self.patient, questionnaire=self.q)

        # Two items, mirroring the production pair: wake time (a.m.) and
        # bed time (p.m.), still configured as free-text items.
        self.wake_item = Item(name='What time did you wake up?',
                              response_type=ResponseTypeChoices.TEXT,
                              abbreviated_item_id='wake_time')
        self.wake_item.save()
        self.bed_item = Item(name='What time did you go to bed?',
                             response_type=ResponseTypeChoices.TEXT,
                             abbreviated_item_id='bed_time')
        self.bed_item.save()
        self.wake_qi = QuestionnaireItem.objects.create(
            questionnaire=self.q, item=self.wake_item, question_number=1)
        self.bed_qi = QuestionnaireItem.objects.create(
            questionnaire=self.q, item=self.bed_item, question_number=2)

        self.submission = QuestionnaireSubmission.objects.create(
            patient=self.patient, patient_questionnaire=self.pq)

    def respond(self, qi, value):
        return QuestionnaireItemResponse.objects.create(
            questionnaire_submission=self.submission,
            questionnaire_item=qi, response_value=value)

    def run_command(self, **opts):
        out = io.StringIO()
        opts.setdefault('item', [f'{self.wake_qi.pk}:am', f'{self.bed_qi.pk}:pm'])
        call_command('fix_time_responses', stdout=out, stderr=out, **opts)
        return out.getvalue()

    def test_dry_run_writes_nothing(self):
        resp = self.respond(self.wake_qi, '800')
        text = self.run_command()
        resp.refresh_from_db()
        self.assertEqual(resp.response_value, '800')
        self.assertIn('Dry run', text)
        self.assertIn("'800'", text)  # the proposed mapping is shown

    def test_commit_rewrites_both_items_with_their_meridian(self):
        wake = self.respond(self.wake_qi, '8')
        bed = self.respond(self.bed_qi, '9.5')
        self.run_command(commit=True)
        wake.refresh_from_db()
        bed.refresh_from_db()
        self.assertEqual(wake.response_value, '08:00:00')
        self.assertEqual(bed.response_value, '21:30:00')

    def test_accepts_the_item_id_as_well_as_the_questionnaire_item_id(self):
        resp = self.respond(self.wake_qi, '0800')
        self.run_command(item=[f'{self.wake_item.pk}:am'], commit=True)
        resp.refresh_from_db()
        self.assertEqual(resp.response_value, '08:00:00')

    def test_leaves_blank_and_unreadable_answers_alone(self):
        blank = self.respond(self.wake_qi, '')
        junk = self.respond(self.wake_qi, 'no recuerdo')
        text = self.run_command(commit=True)
        blank.refresh_from_db()
        junk.refresh_from_db()
        self.assertEqual(blank.response_value, '')
        self.assertEqual(junk.response_value, 'no recuerdo')
        self.assertIn('needs review      1', text)

    def test_is_idempotent(self):
        resp = self.respond(self.wake_qi, '800')
        self.run_command(commit=True)
        resp.refresh_from_db()
        first = resp.response_value
        second_run = self.run_command(commit=True)
        resp.refresh_from_db()
        self.assertEqual(first, '08:00:00')
        self.assertEqual(resp.response_value, first)
        self.assertIn('Nothing to rewrite', second_run)

    def test_modified_date_moves_and_other_items_are_untouched(self):
        target = self.respond(self.wake_qi, '930')
        other_qi = QuestionnaireItem.objects.create(
            questionnaire=self.q,
            item=Item.objects.create(name='Pain',
                                     response_type=ResponseTypeChoices.NUMBER,
                                     abbreviated_item_id='pain'),
            question_number=3)
        untouched = QuestionnaireItemResponse.objects.create(
            questionnaire_submission=self.submission,
            questionnaire_item=other_qi, response_value='7')
        before = target.modified_date
        self.run_command(commit=True)
        target.refresh_from_db()
        untouched.refresh_from_db()
        self.assertEqual(target.response_value, '09:30:00')
        self.assertGreater(target.modified_date, before)
        self.assertEqual(untouched.response_value, '7')

    def test_backup_and_restore_round_trip(self):
        resp = self.respond(self.bed_qi, '800')
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, 'backup.json')
            self.run_command(commit=True, backup=path)
            resp.refresh_from_db()
            self.assertEqual(resp.response_value, '20:00:00')

            with open(path, encoding='utf-8') as fh:
                payload = json.load(fh)
            self.assertEqual(payload['rows'][0]['old'], '800')
            self.assertEqual(payload['rows'][0]['new'], '20:00:00')

            self.run_command(restore=path)
            resp.refresh_from_db()
            self.assertEqual(resp.response_value, '800')

    def test_limit_spots_checks_a_prefix_only(self):
        first = self.respond(self.wake_qi, '800')
        second = self.respond(self.wake_qi, '930')
        self.run_command(commit=True, limit=1)
        first.refresh_from_db()
        second.refresh_from_db()
        rewritten = {first.response_value, second.response_value} & {
            '08:00:00', '09:30:00'}
        self.assertEqual(len(rewritten), 1, 'exactly one of the two answers')

    def test_unknown_id_fails_loudly(self):
        with self.assertRaises(CommandError):
            self.run_command(item=['11111111-1111-1111-1111-111111111111:am'])

    def test_bad_meridian_fails_loudly(self):
        with self.assertRaises(CommandError):
            self.run_command(item=[f'{self.wake_qi.pk}:afternoon'])
