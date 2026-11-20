"""
Utility functions for REDCap / PyCap API interactions.

All functions accept a `ProjectRedcapMapping` instance (or explicit url/token)
and return plain Python dicts/lists so callers stay decoupled from PyCap internals.
"""

import math
import re

import redcap as pycap
from dateutil import parser as _date_parser
from datetime import datetime as _datetime


# ---------------------------------------------------------------------------
# Low-level: project connection
# ---------------------------------------------------------------------------

def get_redcap_project(mapping) -> pycap.Project:
    """Return a PyCap Project instance from a ProjectRedcapMapping."""
    return pycap.Project(mapping.redcap_project_url, mapping.redcap_project_token)


# ---------------------------------------------------------------------------
# Project-level
# ---------------------------------------------------------------------------

def fetch_project_metadata(mapping) -> dict:
    """
    Fetch full project metadata from REDCap and return a dict ready to be
    stored in ProjectRedcapMapping.redcap_project_info.

    Keys: project_info, instruments, metadata, dags, events, repeating.
    Also returns record_count as a top-level key.

    Raises: any PyCap / requests exception on failure.
    """
    rc = get_redcap_project(mapping)

    project_info = rc.export_project_info()
    instruments = rc.export_instruments()
    metadata = rc.export_metadata()
    record_count = len(rc.export_records(fields=[rc.def_field]))

    try:
        dags = rc.export_dags()
    except Exception:
        dags = []

    try:
        events = rc.export_events() if project_info.get('is_longitudinal') else []
    except Exception:
        events = []

    try:
        repeating = rc.export_repeating_instruments_events()
    except Exception:
        repeating = []

    info_payload = {
        'project_info': project_info,
        'instruments': instruments,
        'metadata': metadata,
        'dags': dags,
        'events': events,
        'repeating': repeating,
    }
    return info_payload, record_count


# ---------------------------------------------------------------------------
# Patient ID-level
# ---------------------------------------------------------------------------

def fetch_patient_id_records(mapping) -> list:
    """
    Fetch all records from REDCap returning only the primary (and optional
    secondary) ID fields. Deduplicates by primary field.

    Returns a list of dicts: [{'primary': str, 'secondary': str}, ...]

    Raises: any PyCap / requests exception on failure.
    """
    rc = get_redcap_project(mapping)
    primary_field = mapping.redcap_study_id_field or 'record_id'
    secondary_field = mapping.redcap_secondary_id_field or ''

    fields_to_fetch = [primary_field]
    if secondary_field:
        fields_to_fetch.append(secondary_field)

    raw_records = rc.export_records(fields=fields_to_fetch)

    seen_ids = set()
    records = []
    for rec in raw_records:
        rid = rec.get(primary_field, '').strip()
        if rid and rid not in seen_ids:
            seen_ids.add(rid)
            records.append({
                'primary': rid,
                'secondary': rec.get(secondary_field, '').strip() if secondary_field else '',
            })
    return records


# ---------------------------------------------------------------------------
# Form / instance-level
# ---------------------------------------------------------------------------

def fetch_form_instances(mapping, record_id: str, form_name: str,
                         extra_fields: list = None,
                         events_filter: list = None) -> list:
    """
    Fetch all records for a specific patient (record_id) and form from REDCap.

    Returns raw list of record dicts from PyCap (unprocessed).

    Args:
        mapping: ProjectRedcapMapping instance (provides url + token + primary field).
        record_id: The REDCap study ID string for the patient.
        form_name: The REDCap instrument/form name.
        extra_fields: Additional field names to include alongside the primary field.
        events_filter: Optional list of event names to restrict the export to.

    Raises: any PyCap / requests exception on failure.
    """
    rc = get_redcap_project(mapping)
    primary_field = mapping.redcap_study_id_field or 'record_id'

    fields = [primary_field] + (extra_fields or [])
    kwargs = {
        'records': [record_id],
        'fields': fields,
        'forms': [form_name],
    }
    if events_filter:
        kwargs['events'] = events_filter

    return rc.export_records(**kwargs)


def fetch_field_values_for_record(mapping, record_id: str, field_name: str,
                                   form_name: str,
                                   events_filter: list = None) -> dict:
    """
    Fetch a single date/value field across all events (and instances) for a patient.

    Returns: {(event_name, instance_int_or_None): field_value_str}
    For non-repeating events instance_int_or_None is None.
    For repeating events/forms each instance gets its own entry, preventing
    last-write-wins overwrite when multiple instances share an event name.

    Raises: any PyCap / requests exception on failure.
    """
    raw = fetch_form_instances(
        mapping,
        record_id=record_id,
        form_name=form_name,
        extra_fields=[field_name],
        events_filter=events_filter,
    )
    result = {}
    for rec in raw:
        ev = rec.get('redcap_event_name', '')
        raw_inst = rec.get('redcap_repeat_instance', '')
        inst = int(raw_inst) if str(raw_inst).isdigit() else None
        val = rec.get(field_name, '').strip()
        if val:
            result[(ev, inst)] = val
    return result


# ---------------------------------------------------------------------------
# Import
# ---------------------------------------------------------------------------

def import_records(mapping, rows: list):
    """
    Import a list of record dicts into REDCap via PyCap.

    Returns the PyCap response.
    Raises: any PyCap / requests exception on failure.
    """
    rc = get_redcap_project(mapping)
    return rc.import_records(rows)


# ---------------------------------------------------------------------------
# Field-type validation & formatting for exports
# ---------------------------------------------------------------------------

# Field types for which auto-validation/formatting takes precedence over the
# manual `response_transform` on RedcapFieldToItemMapping.
_AUTO_VALIDATED_FIELD_TYPES = {
    'radio', 'dropdown', 'checkbox',
    'yesno', 'truefalse',
    'slider', 'calc',
    'descriptive', 'sql', 'file',
}

# text_validation_type values that trigger auto-validation for `text` fields.
_AUTO_VALIDATED_TEXT_VALIDATIONS = {
    'integer', 'number', 'number_1dp', 'number_2dp', 'number_3dp', 'number_4dp',
    'email', 'phone', 'zipcode', 'alpha_only', 'alpha_only_uppercase',
    'time', 'time_hhmmss',
}

# Regex patterns for text validation types.
_TEXT_VALIDATION_PATTERNS = {
    'email': re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$'),
    'phone': re.compile(r'^[+()\d][\d\s()\-]+$'),
    'zipcode': re.compile(r'^[A-Za-z0-9 \-]{3,10}$'),
    'alpha_only': re.compile(r'^[A-Za-z]+$'),
    'alpha_only_uppercase': re.compile(r'^[A-Z]+$'),
}

# REDCap date/datetime/time validation types → expected output format and
# input formats to try (in order). The validation type from REDCap metadata
# drives both parsing and reformatting.
_REDCAP_FORMATS = {
    'date_ymd': {
        'output': '%Y-%m-%d',
        'input_formats': ['%Y-%m-%d', '%Y/%m/%d', '%Y%m%d'],
    },
    'date_mdy': {
        'output': '%Y-%m-%d',
        'input_formats': ['%m/%d/%Y', '%m-%d-%Y', '%m/%d/%y'],
    },
    'date_dmy': {
        'output': '%Y-%m-%d',
        'input_formats': ['%d/%m/%Y', '%d-%m-%Y', '%d/%m/%y'],
    },
    'datetime_ymd': {
        'output': '%Y-%m-%d %H:%M',
        'input_formats': ['%Y-%m-%d %H:%M', '%Y/%m/%d %H:%M', '%Y-%m-%dT%H:%M'],
    },
    'datetime_mdy': {
        'output': '%Y-%m-%d %H:%M',
        'input_formats': ['%m/%d/%Y %H:%M', '%m-%d-%Y %H:%M'],
    },
    'datetime_dmy': {
        'output': '%Y-%m-%d %H:%M',
        'input_formats': ['%d/%m/%Y %H:%M', '%d-%m-%Y %H:%M'],
    },
    'datetime_seconds_ymd': {
        'output': '%Y-%m-%d %H:%M:%S',
        'input_formats': ['%Y-%m-%d %H:%M:%S', '%Y/%m/%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S'],
    },
    'datetime_seconds_mdy': {
        'output': '%Y-%m-%d %H:%M:%S',
        'input_formats': ['%m/%d/%Y %H:%M:%S', '%m-%d-%Y %H:%M:%S'],
    },
    'datetime_seconds_dmy': {
        'output': '%Y-%m-%d %H:%M:%S',
        'input_formats': ['%d/%m/%Y %H:%M:%S', '%d-%m-%Y %H:%M:%S'],
    },
    'time': {
        'output': '%H:%M',
        'input_formats': ['%H:%M:%S', '%H:%M'],
    },
    'time_hhmmss': {
        'output': '%H:%M:%S',
        'input_formats': ['%H:%M:%S', '%H:%M'],
    },
}

# Human-readable form of each REDCap output format, for error messages.
_OUTPUT_LABELS = {
    '%Y-%m-%d': 'YYYY-MM-DD',
    '%Y-%m-%d %H:%M': 'YYYY-MM-DD HH:MM',
    '%Y-%m-%d %H:%M:%S': 'YYYY-MM-DD HH:MM:SS',
    '%H:%M': 'HH:MM',
    '%H:%M:%S': 'HH:MM:SS',
}

# Digit-only date/datetime strings are decoded by exact length. strptime's
# numeric directives are variable-width, so '2024071' would otherwise parse as
# 2024-07-01 through '%Y%m%d' — silently wrong data in a clinical export.
_COMPACT_DIGIT_DATE_LENGTHS = {8: '%Y%m%d', 12: '%Y%m%d%H%M', 14: '%Y%m%d%H%M%S'}

# A trailing all-zero fraction, left behind when a date/time was captured
# through a Number-type answer ('20240715' stored as '20240715.00').
_ZERO_FRACTION_NUMBER_RE = re.compile(r'^(\d{4,14})[.,]0+$')
_ZERO_FRACTION_DATETIME_RE = re.compile(
    r'^(\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}(?::\d{2})?)[.,]0+$'
)


def parse_redcap_choices(raw_choices):
    """Parse REDCap 'code, label | code, label | ...' into a list of dicts.

    Returns: [{'code': str, 'label': str}, ...]
    """
    if not raw_choices:
        return []
    choices = []
    for part in raw_choices.split('|'):
        part = part.strip()
        if ',' in part:
            code, _, label = part.partition(',')
            choices.append({'code': code.strip(), 'label': label.strip()})
    return choices


def has_auto_validation(field_type, validation):
    """Return True if this REDCap field should use auto-validation/formatting
    instead of the manual `response_transform`.

    - Choice/yesno/truefalse/slider/calc/descriptive/sql/file field types always
      use auto-validation (regardless of `validation`).
    - `text` fields use auto-validation only when `validation` is a known
      text_validation_type (date_*, datetime_*, time, integer, number*, email,
      phone, zipcode, alpha_only*).
    - `notes` and plain `text` (no/unknown validation) fall back to the manual
      transform.
    """
    if field_type in _AUTO_VALIDATED_FIELD_TYPES:
        return True
    if field_type == 'text':
        if not validation:
            return False
        if validation.startswith(('date_', 'datetime_')):
            return True
        return validation in _AUTO_VALIDATED_TEXT_VALIDATIONS
    return False


def _match_choice_code(raw, valid_codes):
    """Match a raw value against a set of valid REDCap choice codes.

    Does strict string matching first, then falls back to numeric
    normalization: if both the raw value and a code parse as floats and are
    equal, they match (e.g. '3.00' matches code '3'). This protects against
    stored decimal-formatted values even when no manual transform is configured.

    Returns the matching code string (in the code's canonical form) or None.
    """
    s = str(raw)
    if s in valid_codes:
        return s
    # Numeric fallback: try to coerce both sides to float.
    try:
        raw_num = float(s)
    except (ValueError, TypeError):
        return None
    for code in valid_codes:
        try:
            if float(code) == raw_num:
                return code
        except (ValueError, TypeError):
            continue
    return None


def safe_validate_and_format_response_value(raw, field_type, validation, choices):
    """Never-throwing wrapper around :func:`validate_and_format_response_value`.

    The export must not die because one value (or one piece of REDCap metadata)
    is malformed: any unexpected exception is reported as a validation error for
    that single cell instead of aborting the whole export.
    """
    try:
        return validate_and_format_response_value(raw, field_type, validation, choices)
    except Exception as exc:  # noqa: BLE001 — export must degrade to a per-cell error
        return (None, f"value '{raw}' could not be validated ({type(exc).__name__}: {exc})")


def validate_and_format_response_value(raw, field_type, validation, choices):
    """Validate and format a raw response_value string for a REDCap field.

    Args:
        raw: the raw string from QuestionnaireItemResponse.response_value.
        field_type: REDCap `field_type` (e.g. 'text', 'radio', 'yesno').
        validation: REDCap `text_validation_type_or_show_slider_number`.
        choices: list of {'code', 'label'} dicts (for radio/dropdown/checkbox).

    Returns:
        (formatted_value, error_message_or_None):
        - formatted_value: string to write to the export row, or None on error.
        - error_message: None on success, human-readable string on failure.
    """
    if raw is None or raw == '':
        return ('', None)

    # ── date / datetime / time ────────────────────────────────────────────
    if field_type == 'text' and validation and (
        validation.startswith('date_') or validation.startswith('datetime_')
    ):
        return _validate_date_like(raw, validation)
    if field_type == 'text' and validation in ('time', 'time_hhmmss'):
        return _validate_time(raw, validation)

    # ── numeric (text + integer/number*) ──────────────────────────────────
    if field_type == 'text' and validation in ('integer', 'number',
                                                'number_1dp', 'number_2dp',
                                                'number_3dp', 'number_4dp'):
        return _validate_number(raw, validation)

    # ── text format validations (email/phone/zipcode/alpha) ────────────────
    if field_type == 'text' and validation in _TEXT_VALIDATION_PATTERNS:
        pattern = _TEXT_VALIDATION_PATTERNS[validation]
        if pattern.match(str(raw)):
            return (str(raw), None)
        return (None, f"value '{raw}' does not match {validation} format")

    # ── choice fields (radio / dropdown) ─────────────────────────────────
    if field_type in ('radio', 'dropdown'):
        valid_codes = {str(c['code']) for c in (choices or [])}
        matched = _match_choice_code(raw, valid_codes)
        if matched is not None:
            return (matched, None)
        return (None, f"value '{raw}' is not a valid choice code "
                      f"(expected one of {sorted(valid_codes) or '[]'})")

    # ── checkbox (comma-separated codes) ──────────────────────────────────
    if field_type == 'checkbox':
        valid_codes = {str(c['code']) for c in (choices or [])}
        parts = [p.strip() for p in str(raw).split(',') if p.strip()]
        if not parts:
            return ('', None)
        matched_parts = []
        for p in parts:
            matched = _match_choice_code(p, valid_codes)
            if matched is None:
                return (None, f"value '{p}' is not a valid checkbox code "
                              f"(expected one of {sorted(valid_codes) or '[]'})")
            matched_parts.append(matched)
        return (','.join(matched_parts), None)

    # ── yesno / truefalse ────────────────────────────────────────────────
    if field_type in ('yesno', 'truefalse'):
        return _validate_boolean(raw)

    # ── slider ───────────────────────────────────────────────────────────
    if field_type == 'slider':
        # For sliders, 'number' in the validation column is only the
        # "show slider number" display toggle — not a real validation.
        # Slider values are always stored as integers (min–max, step 1).
        return _validate_number(raw, 'integer')

    # ── calc ─────────────────────────────────────────────────────────────
    if field_type == 'calc':
        return _validate_number(raw, 'number')

    # ── non-exportable field types ───────────────────────────────────────
    if field_type in ('descriptive', 'sql', 'file'):
        return (None, f"field type '{field_type}' is not exportable")

    # ── fallback: plain text/notes or unknown validation → passthrough ────
    return (str(raw), None)


def _validate_date_like(raw, validation):
    """Parse a date/datetime string and reformat to the REDCap-expected format.

    The REDCap validation type (e.g. date_ymd, datetime_seconds_mdy, time)
    determines BOTH the expected output format and the input formats we try
    in order. We try strptime with each expected input format first, then
    fall back to dateutil's flexible parsing with hints (yearfirst/dayfirst)
    derived from the validation type.

    Args:
        raw: the raw string from QuestionnaireItemResponse.response_value.
        validation: one of date_ymd, date_mdy, date_dmy, datetime_ymd,
                    datetime_mdy, datetime_dmy, datetime_seconds_ymd,
                    datetime_seconds_mdy, datetime_seconds_dmy.
    """
    fmt = _REDCAP_FORMATS.get(validation)
    if fmt is None:
        # Unknown validation type — fall back to dateutil with no hints.
        try:
            parsed = _date_parser.parse(str(raw))
        except (ValueError, OverflowError, TypeError) as exc:
            return (None, f"value '{raw}' could not be parsed as a date ({exc})")
        return (_render_parsed(parsed, '%Y-%m-%d %H:%M:%S'), None)

    s = _strip_zero_fraction(re.sub(r'\s+', ' ', str(raw).strip()))

    # Step 1: Digit-only values are decoded by exact length only — see
    # _COMPACT_DIGIT_DATE_LENGTHS.
    if s.isdigit():
        in_fmt = _COMPACT_DIGIT_DATE_LENGTHS.get(len(s))
        if in_fmt is None:
            return (None, f"value '{raw}' could not be parsed as a date "
                          f"(expected {_OUTPUT_LABELS.get(fmt['output'], fmt['output'])} format)")
        try:
            parsed = _datetime.strptime(s, in_fmt)
        except ValueError as exc:
            return (None, f"value '{raw}' could not be parsed as a date ({exc})")
        return (_render_parsed(parsed, fmt['output']), None)

    # Step 2: Try each input format that REDCap's validation type implies.
    for in_fmt in fmt['input_formats']:
        try:
            parsed = _datetime.strptime(s, in_fmt)
            return (_render_parsed(parsed, fmt['output']), None)
        except ValueError:
            continue

    # Step 3: Fall back to dateutil with hints derived from the validation type.
    kwargs = {}
    if validation.endswith('_ymd'):
        kwargs['yearfirst'] = True
    elif validation.endswith('_dmy'):
        kwargs['dayfirst'] = True
    # _mdy → dateutil default (month-first)

    try:
        parsed = _date_parser.parse(s, **kwargs)
    except (ValueError, OverflowError, TypeError) as exc:
        return (None, f"value '{raw}' could not be parsed as a date ({exc})")

    return (_render_parsed(parsed, fmt['output']), None)


def _strip_zero_fraction(s):
    """Drop a trailing all-zero fraction left by numeric/decimal answer storage.

    '20240715.00' → '20240715' and '2025-03-14 14:30:00.000' → '2025-03-14 14:30:00'.
    Only an *all-zero* fraction is removed, so a genuinely different value
    ('20240715.5') still fails validation instead of being silently truncated.
    """
    m = _ZERO_FRACTION_NUMBER_RE.match(s) or _ZERO_FRACTION_DATETIME_RE.match(s)
    return m.group(1) if m else s


def _render_parsed(parsed, output_fmt):
    """Format a parsed date/time for REDCap without relying on strftime.

    The platform strftime rejects years below 1000 and does not zero-pad them,
    so the standard REDCap output shapes are assembled explicitly.
    """
    if output_fmt.startswith('%Y-%m-%d'):
        date = f'{parsed.year:04d}-{parsed.month:02d}-{parsed.day:02d}'
        if output_fmt == '%Y-%m-%d':
            return date
        time_part = f'{parsed.hour:02d}:{parsed.minute:02d}'
        if output_fmt.endswith('%S'):
            time_part += f':{parsed.second:02d}'
        return f'{date} {time_part}'
    if output_fmt.startswith('%H:%M'):
        time_part = f'{parsed.hour:02d}:{parsed.minute:02d}'
        if output_fmt == '%H:%M:%S':
            time_part += f':{parsed.second:02d}'
        return time_part
    return parsed.strftime(output_fmt)


def _validate_time(raw, validation='time'):
    """Parse a time string and reformat to what REDCap expects (HH:MM or HH:MM:SS).

    REDCap's `time` validation type expects HH:MM, `time_hhmmss` expects
    HH:MM:SS. Digit-only answers are read by exact length (4 digits = HHMM,
    6 digits = HHMMSS) because strptime's time directives are variable-width
    and would read '2500' as 02:50:00. Anything else falls back to dateutil for
    formats like "2:30 PM"; digit strings of an unexpected length are rejected
    rather than handed to dateutil, which would read them as years.
    """
    fmt = _REDCAP_FORMATS.get(validation, _REDCAP_FORMATS['time'])
    s = re.sub(r'\s+', ' ', str(raw).strip())
    digits = s.replace(' ', '')

    # Step 1: Digit-only answers — exact-length interpretation only.
    if digits.isdigit():
        parts = {4: (digits[:2], digits[2:4], '00'),
                 6: (digits[:2], digits[2:4], digits[4:6])}.get(len(digits))
        label = _OUTPUT_LABELS.get(fmt['output'], 'HH:MM')
        if parts is None:
            return (None, f"value '{raw}' could not be parsed as a time "
                          f"(expected {label} format)")
        try:
            parsed = _datetime.strptime(':'.join(parts), '%H:%M:%S')
        except ValueError:
            return (None, f"value '{raw}' could not be parsed as a time "
                          f"(expected {label} format)")
        return (_render_parsed(parsed, fmt['output']), None)

    # Step 2: Try each input format that the validation type implies.
    for in_fmt in fmt['input_formats']:
        try:
            parsed = _datetime.strptime(s, in_fmt)
            return (_render_parsed(parsed, fmt['output']), None)
        except ValueError:
            continue

    # Step 3: Fall back to dateutil for formats like "2:30 PM".
    try:
        parsed = _date_parser.parse(s)
    except (ValueError, OverflowError, TypeError) as exc:
        return (None, f"value '{raw}' could not be parsed as a time ({exc})")

    return (_render_parsed(parsed, fmt['output']), None)


def _validate_number(raw, validation):
    """Validate and format a numeric value.

    validation is one of: integer, number, number_1dp, number_2dp,
                          number_3dp, number_4dp.
    """
    try:
        val = float(raw)
    except (ValueError, TypeError, OverflowError):
        return (None, f"value '{raw}' is not a valid number")
    # inf/nan would otherwise raise from int() or be written to the export as
    # the literal text 'inf' / 'nan'.
    if not math.isfinite(val):
        return (None, f"value '{raw}' is not a finite number")
    if validation == 'integer':
        return (str(int(val)), None)
    if validation == 'number':
        # General float — strip trailing zeros but keep at least one decimal.
        s = f'{val:.10f}'.rstrip('0')
        if s.endswith('.'):
            s += '0'
        return (s, None)
    # number_Ndp
    ndp = int(validation.split('_')[1].replace('dp', ''))
    return (f'{val:.{ndp}f}', None)


def _validate_boolean(raw):
    """Normalize yesno/truefalse values to '0' or '1'.

    Accepts word forms (yes/no/true/false/y/n/t/f) and numeric forms including
    decimal-stored values like '1.00' or '0.00' (defense-in-depth against the
    same decimal-storage pattern that affects radio fields).
    """
    s = str(raw).strip().lower()
    if s in ('1', 'yes', 'true', 'y', 't'):
        return ('1', None)
    if s in ('0', 'no', 'false', 'n', 'f'):
        return ('0', None)
    # Numeric fallback: coerce decimal-stored values (e.g. '1.00' → 1).
    try:
        num = float(s)
    except (ValueError, TypeError):
        return (None, f"value '{raw}' is not a valid yes/no value")
    if num == 1:
        return ('1', None)
    if num == 0:
        return ('0', None)
    return (None, f"value '{raw}' is not a valid yes/no value")
