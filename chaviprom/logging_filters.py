import re
import logging

# Matches a full UUID (8-4-4-4-12 hex). Used to redact patient UUIDs.
_UUID_RE = re.compile(
    r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"
)

# Redact the value following these PHI introducers. Covers the call sites
# found in the audit (promapp/models.py, patientapp/views.py, middleware.py,
# utils.py plotting_logger, tasks.py).
_PHRASE_PATTERNS = [
    re.compile(r"(from patient )(.+?)(?=\s*$|\s*,|\s*\.\s|\s*\))", re.IGNORECASE),
    re.compile(r"(\bPatient:\s)(\S+)", re.IGNORECASE),
    re.compile(r"(patient ID:\s)([0-9a-fA-F-]+)", re.IGNORECASE),
    re.compile(r"(accessed by:\s)(.+?)(?=\s*\()", re.IGNORECASE),
]

_DICT_KEY_PATTERNS = re.compile(
    r"(patient_name|patient_id|name)", re.IGNORECASE
)


def _mask_uuid(text):
    return _UUID_RE.sub(lambda m: m.group(0)[:8] + "***", text)


def _mask_phrases(text):
    for pat in _PHRASE_PATTERNS:
        text = pat.sub(
            lambda m: m.group(1) + "[REDACTED]" + (m.group(3) if m.lastindex == 3 else ""),
            text,
        )
    return text


def _mask_value(value):
    if isinstance(value, str):
        s = _mask_uuid(value)
        s = _mask_phrases(s)
        return s
    if isinstance(value, dict):
        return {
            k: ("[REDACTED]" if _DICT_KEY_PATTERNS.fullmatch(str(k)) else _mask_value(v))
            for k, v in value.items()
        }
    if isinstance(value, (list, tuple)):
        return type(value)(_mask_value(v) for v in value)
    return value


class PHIMaskingFilter(logging.Filter):
    """Redact patient PHI (UUIDs, names, IDs) from log records.

    Attached to file handlers in settings.LOGGING so every persisted log
    line is sanitized. Console output is left unfiltered for dev debugging.
    """

    def filter(self, record):
        try:
            record.msg = _mask_value(record.msg if isinstance(record.msg, str) else str(record.msg))
            if record.args:
                record.args = _mask_value(record.args)
        except Exception:
            pass  # never let masking break logging
        return True
