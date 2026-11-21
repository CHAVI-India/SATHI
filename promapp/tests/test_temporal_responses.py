"""
Tests for the Date / Time / DateTime response types.

Covers the parts of docs/DATE_TIME_QUESTION_TYPES_PLAN.md that are verifiable
without a browser:

* Part 1/2 - canonical storage formats and Item validation.
* Part 4   - server-side assembly of component boxes (day/month/year,
             hour/minute/second), including the "no JavaScript" path.
* Part 6   - rule-engine comparisons on temporal answers.
* Part 7   - date answers never enter construct scores or equation operands.
* Part 10  - CSV exports include date/time/datetime answers.
* Part 11  - not tested here (owned separately with the REDCap exporter).
* Part 3   - bulk-import spelling variants of the new type names.
"""

import csv
import datetime

from django.conf import settings as django_settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import override_settings
from django.urls import reverse

from promapp.forms import (
    QuestionnaireResponseForm,
    assemble_temporal_from_parts,
    coerce_rule_operands,
    parse_rule_temporal_value,
    serialize_response_value,
)
from promapp.models import (
    ConstructScale,
    Item,
    LikertScale,
    LikertScaleResponseOption,
    PatientQuestionnaire,
    Questionnaire,
    QuestionnaireConstructScore,
    QuestionnaireItem,
    QuestionnaireItemResponse,
    QuestionnaireSubmission,
    ResponseTypeChoices,
)
from promapp.resources import ResponseTypeWidget
from patientapp.models import Institution, Patient
from django.test import TestCase

# A dummy 32-byte key so secured_fields (encrypted patient fields) work in tests.
TEST_ENCRYPTION_KEY = 'MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY='


def make_patient(institution, tag):
    user = get_user_model().objects.create_user(
        username=f'user_{tag}', email=f'{tag}@example.com', password='pw'
    )
    return Patient.objects.create(
        institution=institution, user=user, name=f'Test {tag}',
        patient_id=f'PID-{tag}', age=42, gender='Male',
    )


class ItemTemporalValidationTests(TestCase):
    """Part 2: Item.clean() consistency rules for the new types."""

    def test_date_item_rejects_likert_scale(self):
        scale = LikertScale.objects.create(likert_scale_name='S')
        LikertScaleResponseOption.objects.create(
            likert_scale=scale, option_text='Agree', option_value=1, option_order=1
        )
        item = Item(
            name='Vaccination date',
            response_type=ResponseTypeChoices.DATE,
            likert_response=scale,
        )
        with self.assertRaises(ValidationError):
            item.clean()

    def test_time_item_rejects_range_scale(self):
        from promapp.models import RangeScale
        scale = RangeScale.objects.create(range_scale_name='R')
        item = Item(
            name='Sleep time',
            response_type=ResponseTypeChoices.TIME,
            range_response=scale,
        )
        with self.assertRaises(ValidationError):
            item.clean()

    def test_time_item_without_scale_is_valid(self):
        item = Item(name='Sleep time', response_type=ResponseTypeChoices.TIME)
        item.clean()  # must not raise

    def test_number_item_validation_unchanged(self):
        item = Item(name='Pain', response_type=ResponseTypeChoices.NUMBER)
        item.clean()  # must not raise


class SerializeFormatTests(TestCase):
    """Part 1: canonical string formats, including the midnight trap."""

    def test_date(self):
        self.assertEqual(serialize_response_value(datetime.date(2025, 3, 14)), '2025-03-14')

    def test_time_formats(self):
        self.assertEqual(serialize_response_value(datetime.time(14, 30, 5)), '14:30:05')
        self.assertEqual(serialize_response_value(datetime.time(14, 30)), '14:30:00')

    def test_midnight_is_padded(self):
        # Storage must always use two-digit hours; explicit strftime recipes
        # guarantee it regardless of Python version or tz-awareness quirks.
        self.assertEqual(serialize_response_value(datetime.time(0, 0, 0)), '00:00:00')

    def test_aware_datetime_serializes_without_timezone_noise(self):
        # Django's DateTimeField localizes to the active timezone (USE_TZ),
        # and str() of an aware datetime carries the offset/microseconds —
        # the canonical recipe strips it to the stored wall-clock value.
        from django.utils import timezone
        aware = timezone.make_aware(datetime.datetime(2025, 3, 14, 14, 30, 0))
        self.assertEqual(serialize_response_value(aware), '2025-03-14 14:30:00')
        self.assertNotEqual(serialize_response_value(aware), str(aware))

    def test_datetime(self):
        dt = datetime.datetime(2025, 3, 14, 9, 5, 2)
        self.assertEqual(serialize_response_value(dt), '2025-03-14 09:05:02')

    def test_datetime_microseconds_dropped(self):
        dt = datetime.datetime(2025, 3, 14, 9, 5, 2, 123456)
        self.assertEqual(serialize_response_value(dt), '2025-03-14 09:05:02')

    def test_non_temporal_untouched(self):
        self.assertEqual(serialize_response_value('5.50'), '5.50')
        self.assertEqual(serialize_response_value(3), '3')
        self.assertIsNone(serialize_response_value(None))


class TemporalAssemblyTests(TestCase):
    """Part 4: component-box assembly used by the form (and the no-JS path)."""

    def _assemble(self, rtype, base='response_1', **parts):
        data = {f'{base}_{k}': v for k, v in parts.items()}
        return assemble_temporal_from_parts(data, base, rtype)

    def test_date_parts(self):
        value, error = self._assemble(
            ResponseTypeChoices.DATE, day='14', month='3', year='2025'
        )
        self.assertIsNone(error)
        self.assertEqual(value, datetime.date(2025, 3, 14))

    def test_time_seconds_blank_is_zero_seconds(self):
        value, error = self._assemble(
            ResponseTypeChoices.TIME, hour='0', minute='0', second=''
        )
        self.assertIsNone(error)
        self.assertEqual(value, datetime.time(0, 0, 0))
        self.assertEqual(serialize_response_value(value), '00:00:00')

    def test_time_partial_is_error(self):
        value, error = self._assemble(ResponseTypeChoices.TIME, hour='9')
        self.assertIsNone(value)
        self.assertIsNotNone(error)

    def test_impossible_date_is_error(self):
        value, error = self._assemble(
            ResponseTypeChoices.DATE, day='30', month='2', year='2025'
        )
        self.assertIsNone(value)
        self.assertIsNotNone(error)

    def test_out_of_range_time_is_error(self):
        value, error = self._assemble(
            ResponseTypeChoices.TIME, hour='25', minute='0', second=''
        )
        self.assertIsNone(value)
        self.assertIsNotNone(error)

    def test_datetime_parts(self):
        value, error = self._assemble(
            ResponseTypeChoices.DATETIME,
            day='14', month='3', year='2025',
            hour='14', minute='30', second='',
        )
        self.assertIsNone(error)
        self.assertEqual(value, datetime.datetime(2025, 3, 14, 14, 30, 0))

    def test_datetime_date_only_is_error(self):
        # A datetime answer needs both halves (or neither).
        value, error = self._assemble(
            ResponseTypeChoices.DATETIME, day='14', month='3', year='2025'
        )
        self.assertIsNone(value)
        self.assertIsNotNone(error)

    def test_all_blank_is_none_without_error(self):
        value, error = self._assemble(
            ResponseTypeChoices.DATE, day='', month='', year=''
        )
        self.assertIsNone(value)
        self.assertIsNone(error)
        value, error = self._assemble(
            ResponseTypeChoices.DATETIME,
            day='', month='', year='', hour='', minute='', second='',
        )
        self.assertIsNone(value)
        self.assertIsNone(error)


class QuestionnaireResponseFormTemporalTests(TestCase):
    """Part 4: the patient/staff form accepts boxes or a combined value."""

    def setUp(self):
        self.q = Questionnaire.objects.create(name='Temporal Q')
        self.items = {}
        for tag, rtype in [
            ('date', ResponseTypeChoices.DATE),
            ('time', ResponseTypeChoices.TIME),
            ('dt', ResponseTypeChoices.DATETIME),
        ]:
            item = Item(name=f'{tag} item', response_type=rtype)
            item.save()
            qi = QuestionnaireItem.objects.create(
                questionnaire=self.q, item=item, question_number=1
            )
            self.items[tag] = qi

    def _form(self, tag, data):
        qi = self.items[tag]
        return QuestionnaireResponseForm(data=data, questionnaire_items=[qi])

    def test_boxes_only_assembles_date(self):
        qi = self.items['date']
        form = self._form('date', {
            f'response_{qi.id}': '',
            f'response_{qi.id}_day': '14',
            f'response_{qi.id}_month': '3',
            f'response_{qi.id}_year': '2025',
        })
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data[f'response_{qi.id}'], datetime.date(2025, 3, 14))
        self.assertEqual(
            serialize_response_value(form.cleaned_data[f'response_{qi.id}']),
            '2025-03-14',
        )

    def test_partial_boxes_rejected(self):
        qi = self.items['date']
        form = self._form('date', {
            f'response_{qi.id}': '',
            f'response_{qi.id}_day': '14',
            f'response_{qi.id}_month': '',
            f'response_{qi.id}_year': '',
        })
        self.assertFalse(form.is_valid())
        self.assertIn(f'response_{qi.id}', form.errors)

    def test_impossible_date_rejected(self):
        qi = self.items['date']
        form = self._form('date', {
            f'response_{qi.id}': '',
            f'response_{qi.id}_day': '31',
            f'response_{qi.id}_month': '4',
            f'response_{qi.id}_year': '2025',
        })
        self.assertFalse(form.is_valid())

    def test_combined_value_used_when_js_filled_it(self):
        qi = self.items['dt']
        form = self._form('dt', {f'response_{qi.id}': '2025-03-14 14:30:00'})
        self.assertTrue(form.is_valid(), form.errors)
        # The form localizes datetimes to the active timezone (USE_TZ);
        # what matters for the database is the canonical serialized text.
        self.assertEqual(
            serialize_response_value(form.cleaned_data[f'response_{qi.id}']),
            '2025-03-14 14:30:00',
        )

    def test_blank_optional_answer_valid(self):
        qi = self.items['time']
        form = self._form('time', {f'response_{qi.id}': ''})
        self.assertTrue(form.is_valid(), form.errors)
        self.assertIsNone(form.cleaned_data[f'response_{qi.id}'])

    def test_time_seconds_optional(self):
        qi = self.items['time']
        form = self._form('time', {
            f'response_{qi.id}': '',
            f'response_{qi.id}_hour': '2',
            f'response_{qi.id}_minute': '5',
            f'response_{qi.id}_second': '',
        })
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data[f'response_{qi.id}'], datetime.time(2, 5, 0))
        self.assertEqual(
            serialize_response_value(form.cleaned_data[f'response_{qi.id}']),
            '02:05:00',
        )


class TemporalBoundaryValidationTests(TestCase):
    """Part 4 validation: illogical dates/times are impossible, using the
    real calendar (Python's datetime), not hand-written range rules alone.

    Ranges enforced: hour 0-23 (24-hour clock; the UI echoes the 12-hour
    am/pm reading), minute 0-59, second 0-59, month 1-12, and day 1 to the
    real length of that month - which makes 29 Feb valid only in leap years.
    """

    def _assemble(self, rtype, **parts):
        base = 'response_1'
        data = {f'{base}_{k}': v for k, v in parts.items()}
        return assemble_temporal_from_parts(data, base, rtype)

    # -- dates -----------------------------------------------------------
    def test_29_feb_in_non_leap_year_rejected(self):
        value, error = self._assemble(
            ResponseTypeChoices.DATE, day='29', month='2', year='2025'
        )
        self.assertIsNone(value)
        self.assertIsNotNone(error)

    def test_29_feb_in_leap_year_accepted(self):
        value, error = self._assemble(
            ResponseTypeChoices.DATE, day='29', month='2', year='2024'
        )
        self.assertIsNone(error)
        self.assertEqual(value, datetime.date(2024, 2, 29))

    def test_31_april_rejected_30_days_in_month(self):
        value, error = self._assemble(
            ResponseTypeChoices.DATE, day='31', month='4', year='2025'
        )
        self.assertIsNone(value)
        self.assertIsNotNone(error)

    def test_day_zero_and_month_zero_rejected(self):
        for parts in [
            dict(day='0', month='3', year='2025'),
            dict(day='1', month='0', year='2025'),
            dict(day='1', month='13', year='2025'),
            dict(day='32', month='1', year='2025'),
        ]:
            value, error = self._assemble(ResponseTypeChoices.DATE, **parts)
            self.assertIsNone(value, parts)
            self.assertIsNotNone(error, parts)

    def test_day_31_of_31_day_month_and_month_12_accepted(self):
        value, error = self._assemble(
            ResponseTypeChoices.DATE, day='31', month='12', year='2025'
        )
        self.assertIsNone(error)
        self.assertEqual(value, datetime.date(2025, 12, 31))

    # -- times -----------------------------------------------------------
    def test_hour_24_rejected(self):
        # 24-hour clock: valid hours are 00-23 (midnight is 00, shown to
        # the patient as 12:xx AM).
        value, error = self._assemble(
            ResponseTypeChoices.TIME, hour='24', minute='0', second=''
        )
        self.assertIsNone(value)
        self.assertIsNotNone(error)

    def test_minute_60_and_second_60_rejected(self):
        value, error = self._assemble(
            ResponseTypeChoices.TIME, hour='10', minute='60', second=''
        )
        self.assertIsNone(value)
        self.assertIsNotNone(error)
        value, error = self._assemble(
            ResponseTypeChoices.TIME, hour='10', minute='0', second='60'
        )
        self.assertIsNone(value)
        self.assertIsNotNone(error)

    def test_last_seconds_of_day_accepted(self):
        value, error = self._assemble(
            ResponseTypeChoices.TIME, hour='23', minute='59', second='59'
        )
        self.assertIsNone(error)
        self.assertEqual(value, datetime.time(23, 59, 59))

    # -- datetime: both halves validated ----------------------------------
    def test_datetime_bad_date_good_time_rejected(self):
        value, error = self._assemble(
            ResponseTypeChoices.DATETIME,
            day='29', month='2', year='2025', hour='10', minute='30', second='',
        )
        self.assertIsNone(value)
        self.assertIsNotNone(error)

    def test_datetime_good_date_bad_time_rejected(self):
        value, error = self._assemble(
            ResponseTypeChoices.DATETIME,
            day='14', month='3', year='2025', hour='10', minute='70', second='',
        )
        self.assertIsNone(value)
        self.assertIsNotNone(error)

    def test_datetime_leap_day_valid(self):
        value, error = self._assemble(
            ResponseTypeChoices.DATETIME,
            day='29', month='2', year='2024', hour='23', minute='59', second='59',
        )
        self.assertIsNone(error)
        self.assertEqual(value, datetime.datetime(2024, 2, 29, 23, 59, 59))


class RuleTemporalComparisonTests(TestCase):
    """Part 6: rules compare dates as dates, not as text."""

    def test_date_greater_than(self):
        left, right = coerce_rule_operands(
            '2025-03-14', '2025-03-01', ResponseTypeChoices.DATE
        )
        self.assertIsInstance(left, datetime.date)
        self.assertTrue(left > right)
        # As plain text, '2025-03-14' > '2025-03-01' happens to work, but
        # the important property is real calendar comparison:
        left, right = coerce_rule_operands(
            '2025-01-09', '2024-12-31', ResponseTypeChoices.DATE
        )
        self.assertTrue(left > right)

    def test_lenient_date_input_accepted(self):
        # Staff often type the local format into the rule builder.
        self.assertEqual(
            parse_rule_temporal_value('2025-03-14', ResponseTypeChoices.DATE),
            datetime.date(2025, 3, 14),
        )
        self.assertEqual(
            parse_rule_temporal_value('14/03/2025', ResponseTypeChoices.DATE),
            datetime.date(2025, 3, 14),
        )

    def test_time_lenient_input(self):
        self.assertEqual(
            parse_rule_temporal_value('2:30 PM', ResponseTypeChoices.TIME),
            datetime.time(14, 30),
        )

    def test_equal_on_same_instant(self):
        left, right = coerce_rule_operands(
            '14:30', '14:30:00', ResponseTypeChoices.TIME
        )
        self.assertEqual(left, right)

    def test_invalid_comparison_value_rejected(self):
        with self.assertRaises(ValueError):
            parse_rule_temporal_value('last tuesday', ResponseTypeChoices.DATE)

    def test_datetime_comparable(self):
        left, right = coerce_rule_operands(
            '2025-03-14 09:00:00', '2025-03-14 14:30:00',
            ResponseTypeChoices.DATETIME,
        )
        self.assertTrue(left < right)

    def test_numeric_types_coerced_to_float(self):
        left, right = coerce_rule_operands('5.50', '5.5', ResponseTypeChoices.NUMBER)
        self.assertEqual((left, right), (5.5, 5.5))

    def test_text_types_compare_as_text(self):
        left, right = coerce_rule_operands('yes', 'no', ResponseTypeChoices.TEXT)
        self.assertEqual((left, right), ('yes', 'no'))


@override_settings(FIELD_ENCRYPTION_KEY=TEST_ENCRYPTION_KEY)
class ConstructScoreExclusionTests(TestCase):
    """Part 7: temporal items never feed construct scores."""

    def setUp(self):
        self.institution = Institution.objects.create(name='Test Inst')
        self.patient = make_patient(self.institution, 'score')
        self.q = Questionnaire.objects.create(name='Score Q')

        self.numeric_item = Item(name='Pain score', response_type=ResponseTypeChoices.NUMBER)
        self.numeric_item.save()
        self.date_item = Item(name='Date of vaccination', response_type=ResponseTypeChoices.DATE)
        self.date_item.save()

        self.construct = ConstructScale.objects.create(
            name='Pain', minimum_number_of_items=1,
        )
        self.numeric_item.construct_scale.add(self.construct)
        self.numeric_item.item_number = 1
        self.numeric_item.save()
        self.date_item.construct_scale.add(self.construct)
        self.date_item.item_number = 2
        self.date_item.save()
        # Equation is set only after the numeric item it references exists
        # (the scale equation is validated on ConstructScale.save).
        self.construct.scale_equation = '{q1}'
        self.construct.save()

        self.pq = PatientQuestionnaire.objects.create(
            patient=self.patient, questionnaire=self.q
        )
        self.qi_num = QuestionnaireItem.objects.create(
            questionnaire=self.q, item=self.numeric_item, question_number=1
        )
        self.qi_date = QuestionnaireItem.objects.create(
            questionnaire=self.q, item=self.date_item, question_number=2
        )

    def test_date_answer_ignored_by_scoring(self):
        submission = QuestionnaireSubmission.objects.create(
            patient=self.patient, patient_questionnaire=self.pq
        )
        QuestionnaireItemResponse.objects.create(
            questionnaire_submission=submission,
            questionnaire_item=self.qi_num,
            response_value='5.00',
        )
        QuestionnaireItemResponse.objects.create(
            questionnaire_submission=submission,
            questionnaire_item=self.qi_date,
            response_value='2025-03-14',
        )
        # The last response triggers the post_save scoring signal, which
        # calculates scores automatically.
        scores = QuestionnaireConstructScore.objects.filter(
            questionnaire_submission=submission, construct=self.construct
        )
        self.assertEqual(scores.count(), 1)
        score = scores.first()
        # The score comes from the numeric item alone (equation {q1}).
        self.assertAlmostEqual(float(score.score), 5.0)
        self.assertEqual(score.items_answered, 1)
        self.assertEqual(score.items_not_answered, 0)
        self.assertNotIn('2025-03-14', str(score.score))

    def test_temporal_items_not_offered_to_equation_builder(self):
        valid = self.construct.get_valid_items_with_numbers()
        numbers = [entry['question_number'] for entry in valid]
        self.assertIn(1, numbers)
        self.assertNotIn(2, numbers)


# Debug toolbar is enabled by env var in this developer environment; during
# tests its URLs are not registered, so its response post-processing breaks
# any full request test. Strip it for the request-level tests below.
NO_DEBUG_TOOLBAR = [m for m in django_settings.MIDDLEWARE if 'debug_toolbar' not in m]


@override_settings(
    FIELD_ENCRYPTION_KEY=TEST_ENCRYPTION_KEY,
    MIDDLEWARE=NO_DEBUG_TOOLBAR,
)
class CsvExportTemporalTests(TestCase):
    """Part 10: export CSVs carry date/time/datetime answers."""

    def setUp(self):
        self.institution = Institution.objects.create(name='Export Inst')
        self.patient = make_patient(self.institution, 'export')
        self.admin = get_user_model().objects.create_superuser(
            username='admin_export', email='a@e.com', password='pw'
        )
        self.client.force_login(self.admin)
        self.q = Questionnaire.objects.create(name='Export Q')
        self.pq = PatientQuestionnaire.objects.create(
            patient=self.patient, questionnaire=self.q
        )

        self.answers = [
            (ResponseTypeChoices.DATE, '2025-03-14', 'exp_date'),
            (ResponseTypeChoices.TIME, '14:30:00', 'exp_time'),
            (ResponseTypeChoices.DATETIME, '2025-03-14 14:30:00', 'exp_datetime'),
        ]
        self.qis = []
        for num, (rtype, _answer, abbrev) in enumerate(self.answers, start=1):
            item = Item(
                name=f'{rtype} item', response_type=rtype,
                abbreviated_item_id=abbrev,
            )
            item.save()
            qi = QuestionnaireItem.objects.create(
                questionnaire=self.q, item=item, question_number=num
            )
            self.qis.append(qi)

        self.submission = QuestionnaireSubmission.objects.create(
            patient=self.patient, patient_questionnaire=self.pq
        )
        for qi, (_rtype, answer, _abbrev) in zip(self.qis, self.answers):
            QuestionnaireItemResponse.objects.create(
                questionnaire_submission=self.submission,
                questionnaire_item=qi,
                response_value=answer,
            )

    def test_export_contains_temporal_columns_and_values(self):
        # The app URLs live in i18n_patterns; the language-prefix redirect is
        # followed transparently. (reverse() is avoided here because the
        # dev-only debug toolbar namespace confuses it in some settings.)
        url = f"/promapp/export/questionnaires/{self.q.id}/responses/"
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8-sig')
        rows = list(csv.reader(content.splitlines()))
        header = rows[0]
        for _rtype, _answer, abbrev in self.answers:
            self.assertIn(abbrev, header)
        data_row = rows[1]
        for _rtype, answer, _abbrev in self.answers:
            self.assertIn(answer, data_row)


class ImporterWidgetTests(TestCase):
    """Part 3: tolerant parsing of the new type names in bulk imports."""

    def test_new_types_parsed(self):
        widget = ResponseTypeWidget()
        self.assertEqual(widget.clean('Date Response'), 'Date')
        self.assertEqual(widget.clean('date response'), 'Date')
        self.assertEqual(widget.clean('Time'), 'Time')
        self.assertEqual(widget.clean('DateTime'), 'DateTime')
        self.assertEqual(widget.clean('Datetime'), 'DateTime')
        self.assertEqual(widget.clean('datetime response'), 'DateTime')

    def test_existing_types_still_parse(self):
        widget = ResponseTypeWidget()
        self.assertEqual(widget.clean('Likert Scale'), 'Likert')
        self.assertEqual(widget.clean('Numeric Response'), 'Number')
        self.assertEqual(widget.clean('text'), 'Text')

    def test_unknown_type_passes_through_for_model_validation(self):
        # The widget deliberately returns unknown spellings unchanged; the
        # model's choices validation then rejects the row during import.
        widget = ResponseTypeWidget()
        self.assertEqual(widget.clean('Fibonacci Response'), 'Fibonacci Response')

    def test_blank_passes_through(self):
        widget = ResponseTypeWidget()
        self.assertEqual(widget.clean(''), '')
        self.assertIsNone(widget.clean(None))
