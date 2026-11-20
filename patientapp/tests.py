from django.test import SimpleTestCase

from types import SimpleNamespace

from patientapp.redcap_utils import (
    validate_and_format_response_value,
    safe_validate_and_format_response_value,
    parse_redcap_choices,
    has_auto_validation,
)
from patientapp.views import (
    _apply_field_mappings,
    _expected_csv_columns,
    _safe_zip_stem,
    _unique_zip_name,
)


class ParseRedcapChoicesTests(SimpleTestCase):
    def test_basic(self):
        self.assertEqual(
            parse_redcap_choices('1, Poor | 2, Fair | 3, Good'),
            [
                {'code': '1', 'label': 'Poor'},
                {'code': '2', 'label': 'Fair'},
                {'code': '3', 'label': 'Good'},
            ],
        )

    def test_empty(self):
        self.assertEqual(parse_redcap_choices(''), [])
        self.assertEqual(parse_redcap_choices(None), [])

    def test_strips_whitespace(self):
        self.assertEqual(
            parse_redcap_choices(' 1 , Poor | 2 , Fair '),
            [
                {'code': '1', 'label': 'Poor'},
                {'code': '2', 'label': 'Fair'},
            ],
        )

    def test_skips_parts_without_comma(self):
        self.assertEqual(
            parse_redcap_choices('1, Poor | bad | 2, Fair'),
            [
                {'code': '1', 'label': 'Poor'},
                {'code': '2', 'label': 'Fair'},
            ],
        )


class HasAutoValidationTests(SimpleTestCase):
    def test_choice_types_always_auto_validated(self):
        self.assertTrue(has_auto_validation('radio', ''))
        self.assertTrue(has_auto_validation('dropdown', ''))
        self.assertTrue(has_auto_validation('checkbox', ''))

    def test_yesno_truefalse(self):
        self.assertTrue(has_auto_validation('yesno', ''))
        self.assertTrue(has_auto_validation('truefalse', ''))

    def test_slider_calc(self):
        self.assertTrue(has_auto_validation('slider', ''))
        self.assertTrue(has_auto_validation('slider', 'number'))
        self.assertTrue(has_auto_validation('calc', ''))

    def test_text_with_known_validation(self):
        self.assertTrue(has_auto_validation('text', 'integer'))
        self.assertTrue(has_auto_validation('text', 'number'))
        self.assertTrue(has_auto_validation('text', 'number_2dp'))
        self.assertTrue(has_auto_validation('text', 'date_ymd'))
        self.assertTrue(has_auto_validation('text', 'datetime_seconds_mdy'))
        self.assertTrue(has_auto_validation('text', 'time'))
        self.assertTrue(has_auto_validation('text', 'email'))

    def test_text_without_validation_falls_back(self):
        self.assertFalse(has_auto_validation('text', ''))
        self.assertFalse(has_auto_validation('text', None))

    def test_notes_falls_back(self):
        self.assertFalse(has_auto_validation('notes', ''))
        self.assertFalse(has_auto_validation('notes', 'anything'))

    def test_descriptive_sql_file(self):
        self.assertTrue(has_auto_validation('descriptive', ''))
        self.assertTrue(has_auto_validation('sql', ''))
        self.assertTrue(has_auto_validation('file', ''))


class ValidateDateTests(SimpleTestCase):
    def test_date_ymd_iso(self):
        val, err = validate_and_format_response_value('2026-09-16', 'text', 'date_ymd', [])
        self.assertEqual((val, err), ('2026-09-16', None))

    def test_date_ymd_yearfirst_hint(self):
        # yearfirst=True should interpret 2026/09/16 unambiguously
        val, err = validate_and_format_response_value('2026/09/16', 'text', 'date_ymd', [])
        self.assertEqual((val, err), ('2026-09-16', None))

    def test_date_dmy_dayfirst_hint(self):
        val, err = validate_and_format_response_value('16/09/2026', 'text', 'date_dmy', [])
        self.assertEqual((val, err), ('2026-09-16', None))

    def test_date_mdy_default(self):
        # dateutil default is month-first
        val, err = validate_and_format_response_value('09/16/2026', 'text', 'date_mdy', [])
        self.assertEqual((val, err), ('2026-09-16', None))

    def test_invalid_date(self):
        val, err = validate_and_format_response_value('not a date', 'text', 'date_ymd', [])
        self.assertIsNone(val)
        self.assertIn('could not be parsed', err)


class ValidateDatetimeTests(SimpleTestCase):
    def test_datetime_ymd(self):
        val, err = validate_and_format_response_value('2026-09-16 14:30', 'text', 'datetime_ymd', [])
        self.assertEqual((val, err), ('2026-09-16 14:30', None))

    def test_datetime_seconds_ymd(self):
        val, err = validate_and_format_response_value(
            '2026-09-16 14:30:45', 'text', 'datetime_seconds_ymd', []
        )
        self.assertEqual((val, err), ('2026-09-16 14:30:45', None))

    def test_datetime_dmy(self):
        val, err = validate_and_format_response_value('16/09/2026 14:30', 'text', 'datetime_dmy', [])
        self.assertEqual((val, err), ('2026-09-16 14:30', None))


class ValidateTimeTests(SimpleTestCase):
    def test_time_hhmm(self):
        val, err = validate_and_format_response_value('14:30', 'text', 'time', [])
        self.assertEqual((val, err), ('14:30', None))

    def test_time_with_seconds_strips_to_hhmm(self):
        # REDCap's `time` validation expects HH:MM; seconds are dropped.
        val, err = validate_and_format_response_value('14:30:45', 'text', 'time', [])
        self.assertEqual((val, err), ('14:30', None))

    def test_time_am_pm(self):
        val, err = validate_and_format_response_value('2:30 PM', 'text', 'time', [])
        self.assertEqual((val, err), ('14:30', None))

    def test_time_digit_4digit(self):
        # "2230" → 22:30 (colon-less entry)
        val, err = validate_and_format_response_value('2230', 'text', 'time', [])
        self.assertEqual((val, err), ('22:30', None))

    def test_time_digit_leading_zero(self):
        val, err = validate_and_format_response_value('0930', 'text', 'time', [])
        self.assertEqual((val, err), ('09:30', None))

    def test_time_digit_invalid_hour(self):
        # "2500" → hour 25 is invalid
        val, err = validate_and_format_response_value('2500', 'text', 'time', [])
        self.assertIsNone(val)
        self.assertIn('could not be parsed as a time', err)

    def test_time_single_digit_invalid(self):
        # "7" is not a valid HH:MM time
        val, err = validate_and_format_response_value('7', 'text', 'time', [])
        self.assertIsNone(val)
        self.assertIn('could not be parsed as a time', err)

    def test_invalid_time(self):
        val, err = validate_and_format_response_value('not a time', 'text', 'time', [])
        self.assertIsNone(val)
        self.assertIn('could not be parsed', err)


class ValidateIntegerTests(SimpleTestCase):
    def test_integer_from_int(self):
        val, err = validate_and_format_response_value('4', 'text', 'integer', [])
        self.assertEqual((val, err), ('4', None))

    def test_integer_from_float_string(self):
        val, err = validate_and_format_response_value('4.00', 'text', 'integer', [])
        self.assertEqual((val, err), ('4', None))

    def test_integer_truncates(self):
        # Confirmed behavior: truncate, not round (matches existing TO_INT)
        val, err = validate_and_format_response_value('1.99', 'text', 'integer', [])
        self.assertEqual((val, err), ('1', None))

    def test_integer_invalid(self):
        val, err = validate_and_format_response_value('abc', 'text', 'integer', [])
        self.assertIsNone(val)
        self.assertIn('not a valid number', err)


class ValidateNumberTests(SimpleTestCase):
    def test_number_general(self):
        val, err = validate_and_format_response_value('1', 'text', 'number', [])
        self.assertEqual((val, err), ('1.0', None))

    def test_number_2dp_from_int(self):
        val, err = validate_and_format_response_value('1', 'text', 'number_2dp', [])
        self.assertEqual((val, err), ('1.00', None))

    def test_number_2dp_from_decimal(self):
        val, err = validate_and_format_response_value('1.5', 'text', 'number_2dp', [])
        self.assertEqual((val, err), ('1.50', None))

    def test_number_1dp_rounds(self):
        val, err = validate_and_format_response_value('1.567', 'text', 'number_1dp', [])
        self.assertEqual((val, err), ('1.6', None))

    def test_number_3dp(self):
        val, err = validate_and_format_response_value('1.2345', 'text', 'number_3dp', [])
        self.assertEqual((val, err), ('1.234', None))

    def test_number_4dp(self):
        val, err = validate_and_format_response_value('1.23456', 'text', 'number_4dp', [])
        self.assertEqual((val, err), ('1.2346', None))

    def test_number_invalid(self):
        val, err = validate_and_format_response_value('abc', 'text', 'number_2dp', [])
        self.assertIsNone(val)
        self.assertIn('not a valid number', err)


class ValidateChoiceTests(SimpleTestCase):
    CHOICES = [
        {'code': '1', 'label': 'Poor'},
        {'code': '2', 'label': 'Fair'},
        {'code': '3', 'label': 'Good'},
    ]

    def test_radio_valid(self):
        val, err = validate_and_format_response_value('3', 'radio', '', self.CHOICES)
        self.assertEqual((val, err), ('3', None))

    def test_radio_invalid_code(self):
        val, err = validate_and_format_response_value('5', 'radio', '', self.CHOICES)
        self.assertIsNone(val)
        self.assertIn('not a valid choice code', err)

    def test_dropdown_valid(self):
        val, err = validate_and_format_response_value('1', 'dropdown', '', self.CHOICES)
        self.assertEqual((val, err), ('1', None))

    def test_dropdown_invalid(self):
        val, err = validate_and_format_response_value('x', 'dropdown', '', self.CHOICES)
        self.assertIsNone(val)
        self.assertIn('not a valid choice code', err)


class ValidateCheckboxTests(SimpleTestCase):
    CHOICES = [
        {'code': '1', 'label': 'A'},
        {'code': '2', 'label': 'B'},
        {'code': '3', 'label': 'C'},
    ]

    def test_single_valid(self):
        val, err = validate_and_format_response_value('1', 'checkbox', '', self.CHOICES)
        self.assertEqual((val, err), ('1', None))

    def test_multiple_valid(self):
        val, err = validate_and_format_response_value('1,2', 'checkbox', '', self.CHOICES)
        self.assertEqual((val, err), ('1,2', None))

    def test_multiple_with_spaces(self):
        val, err = validate_and_format_response_value('1, 2 , 3', 'checkbox', '', self.CHOICES)
        self.assertEqual((val, err), ('1,2,3', None))

    def test_invalid_code(self):
        val, err = validate_and_format_response_value('1,9', 'checkbox', '', self.CHOICES)
        self.assertIsNone(val)
        self.assertIn("'9' is not a valid checkbox code", err)

    def test_empty_string(self):
        val, err = validate_and_format_response_value('', 'checkbox', '', self.CHOICES)
        self.assertEqual((val, err), ('', None))


class ValidateChoiceNumericNormalizationTests(SimpleTestCase):
    """Regression tests for decimal-formatted values matching integer choice codes.

    Stored response_value strings are often decimal-formatted (e.g. '3.00')
    while REDCap radio/dropdown choice codes are integers ('3'). The validator
    must normalize these so they match.
    """

    CHOICES = [
        {'code': '0', 'label': 'Not at all'},
        {'code': '1', 'label': 'A little'},
        {'code': '2', 'label': 'Quite a bit'},
        {'code': '3', 'label': 'Very much'},
        {'code': '4', 'label': 'Extremely'},
    ]

    def test_radio_decimal_matches_int_code(self):
        val, err = validate_and_format_response_value('3.00', 'radio', '', self.CHOICES)
        self.assertEqual((val, err), ('3', None))

    def test_radio_decimal_zero_matches(self):
        val, err = validate_and_format_response_value('0.00', 'radio', '', self.CHOICES)
        self.assertEqual((val, err), ('0', None))

    def test_radio_int_still_matches(self):
        val, err = validate_and_format_response_value('3', 'radio', '', self.CHOICES)
        self.assertEqual((val, err), ('3', None))

    def test_radio_decimal_non_matching_still_fails(self):
        val, err = validate_and_format_response_value('5.00', 'radio', '', self.CHOICES)
        self.assertIsNone(val)
        self.assertIn('not a valid choice code', err)

    def test_dropdown_decimal_matches(self):
        val, err = validate_and_format_response_value('2.00', 'dropdown', '', self.CHOICES)
        self.assertEqual((val, err), ('2', None))

    def test_radio_non_numeric_code_not_corrupted(self):
        # Codes like 'a', 'b' must not be coerced numerically.
        choices = [{'code': 'a', 'label': 'X'}, {'code': 'b', 'label': 'Y'}]
        val, err = validate_and_format_response_value('a', 'radio', '', choices)
        self.assertEqual((val, err), ('a', None))
        val, err = validate_and_format_response_value('b', 'radio', '', choices)
        self.assertEqual((val, err), ('b', None))
        val, err = validate_and_format_response_value('c', 'radio', '', choices)
        self.assertIsNone(val)

    def test_checkbox_decimal_matches(self):
        val, err = validate_and_format_response_value('1.00,2.00', 'checkbox', '', self.CHOICES)
        self.assertEqual((val, err), ('1,2', None))

    def test_checkbox_mixed_decimal_and_int(self):
        val, err = validate_and_format_response_value('1,2.00', 'checkbox', '', self.CHOICES)
        self.assertEqual((val, err), ('1,2', None))


class ValidateBooleanTests(SimpleTestCase):
    def test_yesno_yes(self):
        val, err = validate_and_format_response_value('yes', 'yesno', '', [])
        self.assertEqual((val, err), ('1', None))

    def test_yesno_no(self):
        val, err = validate_and_format_response_value('no', 'yesno', '', [])
        self.assertEqual((val, err), ('0', None))

    def test_yesno_numeric(self):
        val, err = validate_and_format_response_value('1', 'yesno', '', [])
        self.assertEqual((val, err), ('1', None))
        val, err = validate_and_format_response_value('0', 'yesno', '', [])
        self.assertEqual((val, err), ('0', None))

    def test_yesno_invalid(self):
        val, err = validate_and_format_response_value('2', 'yesno', '', [])
        self.assertIsNone(val)
        self.assertIn('not a valid yes/no', err)

    def test_truefalse_true(self):
        val, err = validate_and_format_response_value('true', 'truefalse', '', [])
        self.assertEqual((val, err), ('1', None))

    def test_truefalse_false(self):
        val, err = validate_and_format_response_value('false', 'truefalse', '', [])
        self.assertEqual((val, err), ('0', None))

    def test_yesno_decimal_one(self):
        # Decimal-stored '1.00' should normalize to '1' (defense-in-depth).
        val, err = validate_and_format_response_value('1.00', 'yesno', '', [])
        self.assertEqual((val, err), ('1', None))

    def test_yesno_decimal_zero(self):
        val, err = validate_and_format_response_value('0.00', 'yesno', '', [])
        self.assertEqual((val, err), ('0', None))

    def test_yesno_decimal_invalid(self):
        # A decimal value other than 0 or 1 is still invalid.
        val, err = validate_and_format_response_value('2.00', 'yesno', '', [])
        self.assertIsNone(val)
        self.assertIn('not a valid yes/no', err)

    def test_truefalse_decimal_one(self):
        val, err = validate_and_format_response_value('1.00', 'truefalse', '', [])
        self.assertEqual((val, err), ('1', None))


class ValidateSliderCalcTests(SimpleTestCase):
    def test_slider_int(self):
        val, err = validate_and_format_response_value('5', 'slider', '', [])
        self.assertEqual((val, err), ('5', None))

    def test_slider_number_flag(self):
        # 'number' is the "show slider number" display toggle, not a
        # validation — slider values are always integers.
        val, err = validate_and_format_response_value('5', 'slider', 'number', [])
        self.assertEqual((val, err), ('5', None))

    def test_slider_decimal_stored_value(self):
        val, err = validate_and_format_response_value('5.00', 'slider', 'number', [])
        self.assertEqual((val, err), ('5', None))

    def test_slider_invalid(self):
        val, err = validate_and_format_response_value('abc', 'slider', '', [])
        self.assertIsNone(val)
        self.assertIn('not a valid number', err)

    def test_calc_valid(self):
        val, err = validate_and_format_response_value('42', 'calc', '', [])
        self.assertEqual((val, err), ('42.0', None))

    def test_calc_invalid(self):
        val, err = validate_and_format_response_value('abc', 'calc', '', [])
        self.assertIsNone(val)
        self.assertIn('not a valid number', err)


class ValidateTextFormatTests(SimpleTestCase):
    def test_email_valid(self):
        val, err = validate_and_format_response_value('a@b.com', 'text', 'email', [])
        self.assertEqual((val, err), ('a@b.com', None))

    def test_email_invalid(self):
        val, err = validate_and_format_response_value('abc', 'text', 'email', [])
        self.assertIsNone(val)
        self.assertIn('does not match email format', err)

    def test_phone_valid(self):
        val, err = validate_and_format_response_value('+91 98765 43210', 'text', 'phone', [])
        self.assertEqual((val, err), ('+91 98765 43210', None))

    def test_phone_invalid(self):
        val, err = validate_and_format_response_value('abc', 'text', 'phone', [])
        self.assertIsNone(val)
        self.assertIn('does not match phone format', err)

    def test_alpha_only_valid(self):
        val, err = validate_and_format_response_value('Hello', 'text', 'alpha_only', [])
        self.assertEqual((val, err), ('Hello', None))

    def test_alpha_only_invalid(self):
        val, err = validate_and_format_response_value('Hello123', 'text', 'alpha_only', [])
        self.assertIsNone(val)
        self.assertIn('does not match alpha_only format', err)

    def test_alpha_only_uppercase_valid(self):
        val, err = validate_and_format_response_value('HELLO', 'text', 'alpha_only_uppercase', [])
        self.assertEqual((val, err), ('HELLO', None))

    def test_alpha_only_uppercase_invalid(self):
        val, err = validate_and_format_response_value('hello', 'text', 'alpha_only_uppercase', [])
        self.assertIsNone(val)
        self.assertIn('does not match alpha_only_uppercase format', err)


class ValidateNonExportableTests(SimpleTestCase):
    def test_descriptive(self):
        val, err = validate_and_format_response_value('anything', 'descriptive', '', [])
        self.assertIsNone(val)
        self.assertIn('not exportable', err)

    def test_sql(self):
        val, err = validate_and_format_response_value('SELECT 1', 'sql', '', [])
        self.assertIsNone(val)
        self.assertIn('not exportable', err)

    def test_file(self):
        val, err = validate_and_format_response_value('file.dat', 'file', '', [])
        self.assertIsNone(val)
        self.assertIn('not exportable', err)


class ValidatePassthroughTests(SimpleTestCase):
    def test_text_no_validation_passthrough(self):
        val, err = validate_and_format_response_value('anything', 'text', '', [])
        self.assertEqual((val, err), ('anything', None))

    def test_notes_passthrough(self):
        val, err = validate_and_format_response_value('some notes', 'notes', '', [])
        self.assertEqual((val, err), ('some notes', None))

    def test_text_unknown_validation_passthrough(self):
        val, err = validate_and_format_response_value('xyz', 'text', 'unknown_validation', [])
        self.assertEqual((val, err), ('xyz', None))


class ValidateEmptyTests(SimpleTestCase):
    def test_none_returns_empty(self):
        val, err = validate_and_format_response_value(None, 'text', 'integer', [])
        self.assertEqual((val, err), ('', None))

    def test_empty_string_returns_empty(self):
        val, err = validate_and_format_response_value('', 'text', 'date_ymd', [])
        self.assertEqual((val, err), ('', None))

    def test_empty_for_radio(self):
        val, err = validate_and_format_response_value('', 'radio', '', [{'code': '1'}])
        self.assertEqual((val, err), ('', None))

    def test_empty_for_yesno(self):
        val, err = validate_and_format_response_value('', 'yesno', '', [])
        self.assertEqual((val, err), ('', None))


class SafeValidateTests(SimpleTestCase):
    """The export must never die because one value or one piece of metadata is
    malformed — it must degrade to a single-cell error."""

    def test_unexpected_internal_error_becomes_cell_error(self):
        # Malformed choice metadata (ints instead of {'code','label'} dicts)
        val, err = safe_validate_and_format_response_value('1', 'radio', '', [1, 2])
        self.assertIsNone(val)
        self.assertIn('could not be validated', err)

    def test_valid_value_unaffected_by_wrapper(self):
        val, err = safe_validate_and_format_response_value(
            '1', 'radio', '', [{'code': '1', 'label': 'Yes'}]
        )
        self.assertEqual((val, err), ('1', None))

    def test_non_finite_number_does_not_raise(self):
        # int(float('nan')) and int(float('inf')) used to raise out of
        # _validate_number and abort the whole export with a 500.
        for raw in ('nan', 'inf', '-inf', '1e999'):
            with self.subTest(raw=raw):
                val, err = safe_validate_and_format_response_value(raw, 'text', 'integer', [])
                self.assertIsNone(val)
                self.assertIn('finite number', err)

    def test_non_finite_number_never_written_as_literal(self):
        # 'number'/'calc' would previously emit the literal text 'inf' or 'nan'.
        for raw in ('nan', 'inf'):
            with self.subTest(raw=raw):
                val, err = safe_validate_and_format_response_value(raw, 'calc', '', [])
                self.assertIsNone(val)
                self.assertIn('finite number', err)


class NumericStorageDateCoercionTests(SimpleTestCase):
    """Dates captured through a Number-type answer arrive as decimal text."""

    def test_integral_float_fraction_is_stripped(self):
        val, err = validate_and_format_response_value('20240715.00', 'text', 'date_ymd', [])
        self.assertEqual((val, err), ('2024-07-15', None))

    def test_single_zero_fraction(self):
        val, err = validate_and_format_response_value('19700101.0', 'text', 'date_ymd', [])
        self.assertEqual((val, err), ('1970-01-01', None))

    def test_datetime_fraction_is_stripped(self):
        val, err = validate_and_format_response_value(
            '2025-03-14 14:30:00.000', 'text', 'datetime_seconds_ymd', []
        )
        self.assertEqual((val, err), ('2025-03-14 14:30:00', None))

    def test_non_zero_fraction_is_not_truncated_silently(self):
        val, err = validate_and_format_response_value('20240715.5', 'text', 'date_ymd', [])
        self.assertIsNone(val)
        self.assertIn('could not be parsed', err)

    def test_compact_datetime_for_datetime_field(self):
        val, err = validate_and_format_response_value('20240715143000', 'text', 'datetime_ymd', [])
        self.assertEqual((val, err), ('2024-07-15 14:30', None))

    def test_compact_datetime_for_seconds_field(self):
        val, err = validate_and_format_response_value(
            '20240715143000', 'text', 'datetime_seconds_ymd', []
        )
        self.assertEqual((val, err), ('2024-07-15 14:30:00', None))

    def test_compact_datetime_truncated_for_date_field(self):
        val, err = validate_and_format_response_value('20240715143000', 'text', 'date_ymd', [])
        self.assertEqual((val, err), ('2024-07-15', None))

    def test_wrong_length_digits_rejected_not_misread(self):
        # '%Y%m%d' alone reads '2024071' as 2024-07-01; exact lengths only.
        val, err = validate_and_format_response_value('2024071', 'text', 'date_ymd', [])
        self.assertIsNone(val)
        self.assertIn('could not be parsed', err)

    def test_ordinal_like_number_rejected(self):
        val, err = validate_and_format_response_value('45123', 'text', 'date_ymd', [])
        self.assertIsNone(val)
        self.assertIn('could not be parsed', err)

    def test_year_below_1000_zero_padded(self):
        val, err = validate_and_format_response_value('0001-01-01', 'text', 'date_ymd', [])
        self.assertEqual((val, err), ('0001-01-01', None))


class TimeValidationExtendedTests(SimpleTestCase):
    def test_six_digit_time_for_hhmm_field(self):
        val, err = validate_and_format_response_value('143000', 'text', 'time', [])
        self.assertEqual((val, err), ('14:30', None))

    def test_time_hhmmss_is_auto_validated(self):
        self.assertTrue(has_auto_validation('text', 'time_hhmmss'))

    def test_time_hhmmss_output(self):
        val, err = validate_and_format_response_value('14:30', 'text', 'time_hhmmss', [])
        self.assertEqual((val, err), ('14:30:00', None))

    def test_time_hhmmss_keeps_seconds(self):
        val, err = validate_and_format_response_value('14:30:45', 'text', 'time_hhmmss', [])
        self.assertEqual((val, err), ('14:30:45', None))

    def test_time_hhmmss_six_digits(self):
        val, err = validate_and_format_response_value('143045', 'text', 'time_hhmmss', [])
        self.assertEqual((val, err), ('14:30:45', None))


class _QuestionnaireItem:
    """Stand-in for promapp.QuestionnaireItem with a readable str()."""

    def __init__(self, number):
        self.question_number = number

    def __str__(self):
        return f'Q{self.question_number}: item text'


class _BrokenItem:
    """Stand-in whose str() explodes (e.g. a missing translation)."""

    question_number = 7

    def __str__(self):
        raise RuntimeError('translation unavailable')


def _field_map(item_id, field_name, transform=None, question_number=1):
    """Stand-in for RedcapFieldToItemMapping (no database involved)."""
    return SimpleNamespace(
        questionnaire_item_id=item_id,
        redcap_field_name=field_name,
        response_transform=transform,
        questionnaire_item=_QuestionnaireItem(question_number),
    )


class ApplyFieldMappingsTests(SimpleTestCase):
    """Cell-level isolation: every field is reported, good cells still export."""

    META = {
        'dob': ('text', 'date_ymd', []),
        'symptom_time': ('text', 'time', []),
        'note': ('notes', '', []),
        'pain_score': ('text', 'integer', []),
    }

    def _run(self):
        field_maps = [
            _field_map('a', 'dob'),
            _field_map('b', 'symptom_time', question_number=2),
            _field_map('c', 'note'),
            _field_map('d', 'pain_score'),
        ]
        responses = {'a': '20240715.00', 'b': '2500', 'c': 'feeling ok', 'd': 'abc'}
        return _apply_field_mappings(field_maps, responses, self.META)

    def test_good_cells_still_exported(self):
        row, _ = self._run()
        self.assertEqual(row['dob'], '2024-07-15')
        self.assertEqual(row['note'], 'feeling ok')

    def test_failing_cells_written_as_empty(self):
        row, _ = self._run()
        self.assertEqual(row['symptom_time'], '')
        self.assertEqual(row['pain_score'], '')

    def test_every_failing_cell_is_reported_not_just_the_first(self):
        # The old row builder stopped at the first failure, so fixing one field
        # only revealed the next one on the following run.
        _, errors = self._run()
        self.assertEqual([e['field'] for e in errors], ['symptom_time', 'pain_score'])

    def test_error_carries_value_and_item_for_the_report(self):
        _, errors = self._run()
        err = errors[0]
        self.assertEqual(err['raw'], '2500')
        self.assertIn('could not be parsed', err['message'])
        self.assertEqual(err['item_label'], 'Q2: item text')

    def test_item_label_never_raises(self):
        # A broken translation must not break the export of the row.
        field_maps = [_field_map('b', 'symptom_time')]
        field_maps[0].questionnaire_item = _BrokenItem()
        _, errors = _apply_field_mappings(field_maps, {'b': 'nope'}, self.META)
        self.assertEqual(errors[0]['item_label'], '7')

    def test_missing_answer_is_empty_not_none(self):
        field_maps = [_field_map('x', 'dob')]
        row, errors = _apply_field_mappings(field_maps, {}, {'dob': ('text', 'date_ymd', [])})
        self.assertEqual((row, errors), ({'dob': ''}, []))


class ExpectedCsvColumnsTests(SimpleTestCase):
    def test_plain_form(self):
        mapping = SimpleNamespace(redcap_study_id_field='record_id')
        fm = SimpleNamespace(
            redcap_form_is_in_event=False, redcap_form_is_repeating=False,
            redcap_event_is_repeating=False, submission_date_field=None,
        )
        cols = _expected_csv_columns(mapping, fm, [_field_map('a', 'f1'), _field_map('b', 'f2')])
        self.assertEqual(cols, ['record_id', 'f1', 'f2'])

    def test_event_repeating_and_date_field_order(self):
        mapping = SimpleNamespace(redcap_study_id_field='patient_id')
        fm = SimpleNamespace(
            redcap_form_is_in_event=True, redcap_form_is_repeating=False,
            redcap_event_is_repeating=True, submission_date_field='visit_date',
        )
        cols = _expected_csv_columns(mapping, fm, [_field_map('a', 'f1')])
        self.assertEqual(cols, [
            'patient_id', 'redcap_event_name', 'redcap_repeat_instrument',
            'redcap_repeat_instance', 'visit_date', 'f1',
        ])

    def test_custom_id_field_default_and_duplicates(self):
        mapping = SimpleNamespace(redcap_study_id_field='')
        fm = SimpleNamespace(
            redcap_form_is_in_event=False, redcap_form_is_repeating=False,
            redcap_event_is_repeating=False, submission_date_field=None,
        )
        cols = _expected_csv_columns(mapping, fm, [_field_map('a', 'record_id'), _field_map('b', 'f2')])
        self.assertEqual(cols, ['record_id', 'f2'])


class ZipMemberNameTests(SimpleTestCase):
    def test_form_name_sanitised(self):
        self.assertEqual(_safe_zip_stem('Adverse Events/2024'), 'Adverse_Events_2024')

    def test_empty_form_name_falls_back(self):
        self.assertEqual(_safe_zip_stem('///'), 'form')

    def test_duplicate_form_names_do_not_overwrite_each_other(self):
        # Two form mappings may share a REDCap form name; the second writestr
        # used to silently replace the first form's entire CSV.
        used = set()
        first = _unique_zip_name(used, _safe_zip_stem('demographics'))
        second = _unique_zip_name(used, _safe_zip_stem('demographics'))
        self.assertEqual((first, second), ('demographics.csv', 'demographics_2.csv'))

    def test_report_name_cannot_be_shadowed_by_a_form(self):
        # A form literally named "validation_errors" must not swallow the report.
        used = set()
        form_member = _unique_zip_name(used, _safe_zip_stem('validation_errors'))
        report_member = _unique_zip_name(used, 'validation_errors')
        self.assertEqual((form_member, report_member),
                         ('validation_errors.csv', 'validation_errors_2.csv'))
