"""Normalisation of legacy free-text clock answers to canonical ``HH:MM:SS``.

Background
----------
Before the date/time question types were introduced (see
docs/DATE_TIME_QUESTION_TYPES_PLAN.md), items that asked for a clock time were
configured as free-text/numeric items, so patients typed times however they
felt: ``0800``, ``800``, ``8``, ``9.5``, ``9,5``, ``2230``... Those values are
stored verbatim in ``QuestionnaireItemResponse.response_value`` and are rejected
by the REDCap exporter's ``time`` / ``time_hhmmss`` validation.

The canonical storage format for a time answer is ``%H:%M:%S`` (see
``promapp.forms.serialize_response_value``), so the legacy rows have to be
rewritten before the REDCap field can be switched to a time validation type.

Some legacy answers are genuinely ambiguous: ``8`` on a "what time did you wake
up?" item means 08:00, on a "what time did you go to bed?" item it means 20:00.
The caller therefore declares which meridian the item uses:

``am``   hours are taken at face value (wake-up / morning items)
``pm``   an hour ``0 < h < 12`` is read as p.m. and shifted by +12 (bedtime items)
``auto`` no shift at all, purely mechanical reformatting

Every rule reports *why* it produced its answer, so a dry run can be reviewed
before anything is written. Values that cannot be interpreted are left alone and
reported for manual fixing - this module never guesses silently.

Rules implemented, with the two production items as the example
(a.m. = "what time did you wake up", p.m. = "what time did you go to bed"):

============================  ==========================  ==========================
stored                        am item                     pm item
============================  ==========================  ==========================
``0800`` / ``800`` / ``8``    ``08:00:00``                ``20:00:00``
``9`` / ``900``               ``09:00:00``                ``21:00:00``
``9.5`` / ``9,5`` / ``930``   ``09:30:00``                ``21:30:00``
``9.45`` / ``9.75``           ``09:45:00``                ``21:45:00``
``2230``                      ``22:30:00`` (flagged)      ``22:30:00``
``8:00``                      ``08:00:00``                ``08:00:00`` (see note 4)
``2:30 pm``                   ``14:30:00``                ``14:30:00``
``08:00:00``                  unchanged                   unchanged
``no recuerdo``               left alone, reported        left alone, reported
============================  ==========================  ==========================

Notes:
1. One decimal digit is a fraction of an hour (``9.5`` -> 30 min); two digits
   are read as the minutes the way people type them (``9.25`` -> ``09:25``),
   and only when they cannot be minutes does the fraction reading come back
   (``9.75`` -> ``09:45``). Every decimal answer is labelled in the dry-run
   report so the odd ones can be checked by a human first.
2. Digit-only answers are read by exact length, with the same table as
   ``patientapp.redcap_utils._validate_time``: 1-2 digits = hours, 3 = HMM,
   4 = HHMM, 6 = HHMMSS. Anything else is reported, never guessed.
3. An hour > 12 on an a.m. item (or an hour < 12 written in 24-hour form on a
   p.m. item) is kept as typed and flagged in the report.
4. A value that already contains a colon was written by someone using the time
   convention, so only its seconds get padded. Pass ``shift_colon=True``
   (``--shift-colon``) to apply the meridian shift to those as well.
5. An explicit ``am``/``pm``/``de la noche`` marker always beats the item's
   default meridian.

Pure functions only: no ORM, no settings, safe to unit test and to paste into
``manage.py shell``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# ── Outcomes ────────────────────────────────────────────────────────────────
SKIP = 'skip'            # nothing stored (NULL / blank) - nothing to do
UNCHANGED = 'unchanged'  # already canonical HH:MM:SS
REWRITE = 'rewrite'      # value rewritten to a canonical time
REVIEW = 'review'        # could not be interpreted - left untouched

MERIDIAN_AM = 'am'
MERIDIAN_PM = 'pm'
MERIDIAN_AUTO = 'auto'
MERIDIAN_CHOICES = (MERIDIAN_AM, MERIDIAN_PM, MERIDIAN_AUTO)

# English and (this deployment runs in Spanish) meridian markers.
_AM_MARKERS = ('am', 'mañana', 'manana', 'madrugada')
_PM_MARKERS = ('pm', 'tarde', 'noche', 'medianoche')
# Filler words left behind once a marker is removed ("10 de la noche", "at 10").
_TRAILING_FILLER = re.compile(
    r'(?i)\s*(de\s+las|de\s+la|del|de|las|la|el|a|at)\s*$')
_LEADING_FILLER = re.compile(r'(?i)^\s*(las|la|el|at|a\s+las)\s+')

_CANONICAL_RE = re.compile(r'^(\d{1,2}):(\d{2})(?::(\d{2}))?$')
_FULL_CANONICAL_RE = re.compile(r'^(\d{2}):(\d{2}):(\d{2})$')
# 9h30 / 9 h 30 / 9h
_HOURS_RE = re.compile(r'^(\d{1,2})\s*h\s*(\d{1,2})?$', re.IGNORECASE)
# 9.5 / 9,5 / 9.30 / 9 30 - a separator then a one or two digit remainder.
# ':' is handled by _CANONICAL_RE so that "08:00" is never read as a fraction.
_DECIMAL_RE = re.compile(r'^(\d{1,2})\s*[.,]\s*(\d{1,2})$')


@dataclass(frozen=True)
class TimeNormalization:
    """Result of normalising one stored response value.

    Attributes:
        value: canonical ``HH:MM:SS`` string, or None when there is nothing to
            write (``skip``) or the value could not be read (``review``).
        action: one of ``skip``, ``unchanged``, ``rewrite``, ``review``.
        reason: short human-readable note explaining the interpretation, e.g.
            ``'HMM digits (800)'`` or ``'decimal fraction .5 = 30 min'``. Shown
            by the management command so odd rules are visible before committing.
    """
    value: str | None
    action: str
    reason: str = ''

    @property
    def changed(self) -> bool:
        return self.action == REWRITE


def normalize_clock_value(raw, meridian: str = MERIDIAN_AM,
                          shift_colon: bool = False) -> TimeNormalization:
    """Convert one legacy response string to canonical ``HH:MM:SS``.

    Args:
        raw: the value as stored in ``response_value`` (any type; str() is used).
        meridian: how to read hours written on a 12-hour clock, see module doc.
        shift_colon: also apply the meridian shift to values that already
            contain a colon (``8:00`` -> ``20:00:00`` on a pm item). Off by
            default: whoever typed a colon already used the time convention, so
            its hour is taken as written and only the seconds get padded.

    Returns:
        TimeNormalization - never raises.
    """
    if raw is None:
        return TimeNormalization(None, SKIP, 'empty')

    s = re.sub(r'\s+', ' ', str(raw)).strip(' \t.,;:')
    if s == '' or s.lower() in ('none', 'null', '-'):
        return TimeNormalization(None, SKIP, 'empty')

    # "9 a.m." / "9 p. m." -> "9 am" / "9 pm" so one marker test covers them all.
    s = re.sub(r'(?i)([ap])[.\s]*m[.\s]*', r'\1m', s).strip(' \t.,;:-')

    # Already canonical -> nothing to do. This makes a whole run idempotent.
    full = _FULL_CANONICAL_RE.match(s)
    if full:
        h, m, sec = (int(g) for g in full.groups())
        if h <= 23 and m <= 59 and sec <= 59:
            return TimeNormalization(s, UNCHANGED, 'already HH:MM:SS')

    # ── meridian marker: "2:30 pm", "9 a.m.", "10 de la noche" ─────────────
    explicit_pm = None
    lowered = s.lower()
    for marker, is_pm in ([(m, True) for m in _PM_MARKERS]
                          + [(m, False) for m in _AM_MARKERS]):
        if lowered.endswith(marker):
            explicit_pm = is_pm
            s = s[:len(s) - len(marker)].strip(' \t.,;:-')
            lowered = lowered[:len(lowered) - len(marker)].strip(' \t.,;:-')
            break
    if explicit_pm is not None:
        s = _LEADING_FILLER.sub('', _TRAILING_FILLER.sub('', s)).strip(' \t.,;:-')
        if s == '':
            # "noche" / "medianoche" alone: noon-ish vs midnight.
            return _finish(12 if explicit_pm else 0, 0, 0, meridian,
                           'meridian marker only', explicit_pm=explicit_pm)

    # ── 9h30 / 9 h ─────────────────────────────────────────────────────────
    m = _HOURS_RE.match(s)
    if m:
        hour = int(m.group(1))
        minute = int(m.group(2) or 0)
        reason = f'h-notation ({m.group(0)})'
        return _finish(hour, minute, 0, meridian, reason, explicit_pm)

    # ── digit-only answers, read by exact length ───────────────────────────
    # Same length table as patientapp.redcap_utils._validate_time, so anything
    # rewritten here is accepted by the REDCap exporter as well.
    digits = s.replace(' ', '')
    if digits.isdigit():
        n = digits
        if len(n) <= 2:
            hour, minute, second, reason = int(n), 0, 0, f'hours only ({n})'
        elif len(n) == 3:
            hour, minute, second, reason = int(n[0]), int(n[1:]), 0, f'HMM ({n})'
        elif len(n) == 4:
            hour, minute, second, reason = int(n[:2]), int(n[2:]), 0, f'HHMM ({n})'
        elif len(n) == 6:
            hour, minute, second = int(n[:2]), int(n[2:4]), int(n[4:])
            reason = f'HHMMSS ({n})'
        else:
            return TimeNormalization(
                None, REVIEW, f'{len(n)} digits is not a time we recognise')
        return _finish(hour, minute, second, meridian, reason, explicit_pm)

    # ── colon: 8:00, 08:00:30 ──────────────────────────────────────────────
    m = _CANONICAL_RE.match(s)
    if m:
        hour, minute = int(m.group(1)), int(m.group(2))
        second = int(m.group(3) or 0)
        reason = f'HH:MM{"SS" if m.group(3) else ""} ({s})'
        if explicit_pm is None and not shift_colon:
            # Hour was written deliberately: only pad the seconds.
            return _render(hour, minute, second, f'{reason}, seconds padded')
        return _finish(hour, minute, second, meridian, reason, explicit_pm)

    # ── decimal: 9.5, 9,5, 9.45, 9 30 ──────────────────────────────────────
    m = _DECIMAL_RE.match(s)
    if m:
        hour, rest = int(m.group(1)), m.group(2)
        if len(rest) == 1:
            # One decimal digit = fraction of an hour: 9.5 -> 9:30.
            minute = round(int(rest) * 6)
            reason = f'decimal fraction .{rest} = {minute} min'
        elif int(rest) <= 59:
            # Two digits that fit in a minute: 9.45 -> 9:45 (typed, not .75 h).
            minute = int(rest)
            reason = f'decimal minutes .{rest} = {minute} min'
        else:
            minute = round(int(rest) / 100 * 60)
            reason = f'decimal fraction .{rest} = {minute} min'
        return _finish(hour, minute, 0, meridian, reason, explicit_pm)

    return TimeNormalization(None, REVIEW, f'"{raw}" is not a time we recognise')


# ── helpers ─────────────────────────────────────────────────────────────────

def _finish(hour: int, minute: int, second: int, meridian: str,
            reason: str, explicit_pm: bool | None = None) -> TimeNormalization:
    """Apply the meridian rule, range-check, and render HH:MM:SS."""
    note = reason

    if explicit_pm is not None:
        # An explicit am/pm marker always beats the item's default meridian.
        if explicit_pm and hour < 12:
            hour += 12
            note = f'{reason}, p.m. marker'
        elif not explicit_pm and hour == 12:
            hour = 0
            note = f'{reason}, a.m. marker'
    elif meridian == MERIDIAN_PM and 0 < hour < 12:
        hour += 12
        note = f'{reason}, p.m. item (+12)'
    elif meridian == MERIDIAN_AM and hour > 12:
        note = f'{reason}, p.m. hour on an a.m. item (left as typed)'

    return _render(hour, minute, second, note)


def _render(hour: int, minute: int, second: int,
            reason: str) -> TimeNormalization:
    """Range-check and render HH:MM:SS, or flag an impossible time."""
    if not (0 <= hour <= 23 and 0 <= minute <= 59 and 0 <= second <= 59):
        return TimeNormalization(
            None, REVIEW,
            f'{reason} -> impossible time {hour}:{minute:02d}:{second:02d}')
    return TimeNormalization(f'{hour:02d}:{minute:02d}:{second:02d}', REWRITE, reason)
