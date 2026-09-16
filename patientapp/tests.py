from django.test import SimpleTestCase

from patientapp.redcap_utils import (
    validate_and_format_response_value,
    parse_redcap_choices,
    has_auto_validation,
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

    def test_slider_number_validation(self):
        val, err = validate_and_format_response_value('5', 'slider', 'number', [])
        self.assertEqual((val, err), ('5.0', None))

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
