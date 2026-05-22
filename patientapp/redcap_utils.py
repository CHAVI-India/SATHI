"""
Utility functions for REDCap / PyCap API interactions.

All functions accept a `ProjectRedcapMapping` instance (or explicit url/token)
and return plain Python dicts/lists so callers stay decoupled from PyCap internals.
"""

import redcap as pycap


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
    Fetch a single date/value field across all events for a patient.

    Returns: {event_name: field_value_str} — one entry per event that has a
    non-empty value for field_name.

    Raises: any PyCap / requests exception on failure.
    """
    raw = fetch_form_instances(
        mapping,
        record_id=record_id,
        form_name=form_name,
        extra_fields=[field_name],
        events_filter=events_filter,
    )
    event_to_value = {}
    for rec in raw:
        ev = rec.get('redcap_event_name', '')
        val = rec.get(field_name, '').strip()
        if val:
            event_to_value[ev] = val
    return event_to_value


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
