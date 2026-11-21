"""One-off data fix: rewrite legacy free-text clock answers as HH:MM:SS.

Two questionnaire items collected a clock time while the response type was
still free text, so the database holds answers such as ``8``, ``800``, ``0800``
and ``9.5``. The REDCap exporter cannot validate those against a ``time`` field,
and the REDCap column cannot be switched to a time validation type until the
stored strings are canonical.

This command rewrites ``QuestionnaireItemResponse.response_value`` for the
affected items into the canonical ``HH:MM:SS`` storage format used by the Time
response type (see ``promapp.forms.serialize_response_value``), interpreting
hours according to what the question asks (a.m. for wake-up times, p.m. for
bedtime times). See ``promapp/time_normalization.py`` for the conversion rules.

It is a dry run by default and prints every distinct stored value with its
proposed replacement, so the mapping can be reviewed before writing:

    # 1. inspect (writes nothing)
    python manage.py fix_time_responses

    # 2. apply, keeping a rollback file next to the run log
    python manage.py fix_time_responses --commit \
        --backup backups/time_responses_$(date +%Y%m%d_%H%M%S).json

    # 3. undo if anything looks wrong
    python manage.py fix_time_responses --restore \
        backups/time_responses_20260212_153000.json

Other options: ``--item UUID:am|pm|auto`` (repeatable, replaces the built-in
list when given), ``--shift-colon`` (also apply the p.m. shift to values that
already contain a colon), ``--limit N`` (process at most N answers per item),
``--show N`` (size of the change sample, default 40) and ``--force`` (restore
even when the stored value no longer matches the backup).
"""

from __future__ import annotations

import json
import os
import uuid
from collections import Counter, defaultdict

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from promapp.time_normalization import (
    MERIDIAN_CHOICES,
    normalize_clock_value,
)

# Items whose stored answers need rewriting, and how their hours must be read.
# 'am': 8 means 08:00. 'pm': 8 means 20:00, 9.5 means 21:30.
LEGACY_TIME_ITEMS = (
    ('9c16d1e1-f7e5-4ee7-905e-a778250dad87', 'am'),
    ('df5988ce-dcc2-4624-9389-c22d28657948', 'pm'),
)

BACKUP_FORMAT = 'sathi-time-response-backup/1'


class Command(BaseCommand):
    help = ('Rewrite legacy numeric answers for selected questionnaire items '
            'into canonical HH:MM:SS time strings (dry run by default).')

    def add_arguments(self, parser):
        parser.add_argument(
            '--item', action='append', metavar='UUID[:am|pm|auto]',
            help='Item to fix, with the meridian its hours use. Repeatable. '
                 'UUID may be an Item id or a QuestionnaireItem id. Replaces '
                 'the built-in list of two items when supplied.')
        parser.add_argument(
            '--commit', action='store_true',
            help='Write the changes. Without this flag nothing is saved.')
        parser.add_argument(
            '--backup', metavar='FILE',
            help='Write a JSON undo file (id, old value, new value) before '
                 'committing.')
        parser.add_argument(
            '--restore', metavar='FILE',
            help='Restore the old values recorded in a --backup file and exit.')
        parser.add_argument(
            '--force', action='store_true',
            help='With --restore, also write back rows whose current value is '
                 'not the value the backup wrote.')
        parser.add_argument(
            '--shift-colon', action='store_true',
            help='Apply the p.m. shift to answers that already contain a '
                 'colon (e.g. 8:00 becomes 20:00:00 on a p.m. item). '
                 'By default such answers only get their seconds padded.')
        parser.add_argument(
            '--limit', type=int, default=0,
            help='Process at most N answers per item (spot checks).')
        parser.add_argument(
            '--show', type=int, default=40,
            help='How many distinct values / changed rows to print. Default 40.')

    # ── entry point ───────────────────────────────────────────────────────
    def handle(self, *args, **opts):
        from promapp.models import QuestionnaireItemResponse

        if opts['restore']:
            self._restore(opts)
            return

        targets = self._resolve_targets(opts)
        if not targets:
            raise CommandError('No questionnaire item matched the given ids.')

        planned = []          # (response_id, old, new, reason)
        need_review = []      # (response_id, old, reason)
        raw_counts = defaultdict(Counter)   # qi_id -> Counter of stored values
        outcome = defaultdict(dict)         # qi_id -> {stored value: result}
        totals = Counter()

        for qi_id, label, meridian in targets:
            qs = QuestionnaireItemResponse.objects.filter(
                questionnaire_item_id=qi_id).order_by('pk')
            if opts['limit']:
                qs = qs[:opts['limit']]

            self.stdout.write('')
            self.stdout.write(self.style.MIGRATE_HEADING(
                f'{label}  [questionnaire_item {qi_id}] meridian={meridian}'))

            for resp in qs.iterator(chunk_size=1000):
                raw = resp.response_value
                result = normalize_clock_value(
                    raw, meridian=meridian, shift_colon=opts['shift_colon'])
                totals[result.action] += 1
                # NULL and '' must stay visible in the report, so the histogram
                # is keyed by the printable form of the stored value.
                if raw is None:
                    shown = '<NULL>'
                elif raw == '':
                    shown = '<BLANK>'
                else:
                    shown = str(raw)
                raw_counts[qi_id][shown] += 1
                outcome[qi_id].setdefault(shown, result)
                if result.changed:
                    if result.value != (raw or ''):
                        planned.append(
                            (resp.pk, raw, result.value, result.reason))
                elif result.action == 'review':
                    need_review.append((resp.pk, raw, result.reason))

            self._report_values(qi_id, outcome, raw_counts[qi_id], opts['show'])

        self._summary(totals, planned, need_review, opts['show'])

        if not planned:
            self.stdout.write(self.style.SUCCESS(
                'Nothing to rewrite.'))
            if need_review:
                self.stdout.write(self.style.WARNING(
                    f'{len(need_review)} answer(s) still need a human decision; '
                    'fix them in the admin or with a targeted ORM update.'))
            return

        if not opts['commit']:
            self.stdout.write(self.style.WARNING(
                '\nDry run - nothing was written. Re-run with --commit'
                + (' and --backup FILE' if not opts['backup'] else '')
                + ' to apply.'))
            return

        self._write_backup(opts['backup'], planned)
        with transaction.atomic():
            self._apply(planned)
        self.stdout.write(self.style.SUCCESS(
            f'\nRewrote {len(planned)} response(s).'))
        self._warn_equations(targets)

    # ── reporting ─────────────────────────────────────────────────────────
    def _report_values(self, qi_id, outcome, counts, show):
        """Print each distinct stored value once, with what it becomes."""
        rows = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
        if not rows:
            self.stdout.write('  (no answers stored for this item)')
            return
        self.stdout.write(f'  {"stored value":<22} {"n":>6}  ->  new value')
        for stored, n in rows[:show]:
            result = outcome[qi_id].get(stored)
            new = result.value if (result and result.value) else '-'
            note = result.reason if result else ''
            if result and result.action == 'review':
                new = self.style.ERROR('LEAVE AS IS')
            elif result and result.action == 'unchanged':
                new = self.style.SUCCESS(new)
            self.stdout.write(f'  {stored:<22} {n:>6}  ->  {new}   {note}')
        if len(rows) > show:
            self.stdout.write(f'  ... {len(rows) - show} more distinct value(s)'
                              f' (--show {len(rows)} to list them all)')

    def _summary(self, totals, planned, need_review, show):
        self.stdout.write('')
        self.stdout.write(self.style.MIGRATE_HEADING('Summary'))
        self.stdout.write(f'  to rewrite        {totals["rewrite"]}')
        self.stdout.write(f'  already HH:MM:SS  {totals["unchanged"]}')
        self.stdout.write(f'  blank / no answer {totals["skip"]}')
        self.stdout.write(f'  needs review      {totals["review"]}')
        if planned:
            self.stdout.write(f'\n  sample of changes (first {min(show, len(planned))}):')
            for _pk, old, new, reason in planned[:show]:
                self.stdout.write(f'    {str(old)!r:>12}  ->  {new}   ({reason})')
        if need_review:
            self.stdout.write(self.style.WARNING(
                f'\n  {len(need_review)} answer(s) could not be interpreted and '
                'will be left untouched:'))
            for pk, old, reason in need_review[:show]:
                self.stdout.write(f'    {pk}  {str(old)!r}  ({reason})')

    # ── applying ──────────────────────────────────────────────────────────
    def _apply(self, planned):
        """Update the rows. Runs inside the caller's transaction."""
        from promapp.models import QuestionnaireItemResponse

        by_value = defaultdict(list)
        for pk, _old, new, _reason in planned:
            by_value[new].append(pk)

        now = _now()
        done = 0
        for new, pks in by_value.items():
            # One UPDATE per distinct target value (queryset.update() skips the
            # auto_now field, so modified_date is set explicitly to leave an
            # audit trail of the fix).
            for start in range(0, len(pks), 500):
                done += QuestionnaireItemResponse.objects.filter(
                    pk__in=pks[start:start + 500]).update(
                        response_value=new, modified_date=now)
        self.stdout.write(f'  {done} row(s) updated in the database.')

    def _write_backup(self, path, planned):
        if not path:
            self.stdout.write(self.style.WARNING(
                '  No --backup file given: old values are not recoverable '
                'from this command.'))
            return
        parent = os.path.dirname(os.path.abspath(path))
        os.makedirs(parent, exist_ok=True)
        payload = {
            'format': BACKUP_FORMAT,
            'generated_at': _now().isoformat(),
            'rows': [{'id': str(pk), 'old': old, 'new': new}
                     for pk, old, new, _reason in planned],
        }
        # Written before the transaction commits: the file is the rollback plan,
        # and an unused file is harmless while a lost one is not.
        with open(path, 'w', encoding='utf-8') as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=1)
        self.stdout.write(f'  Backup of {len(planned)} old value(s) -> {path}')

    def _restore(self, opts):
        from promapp.models import QuestionnaireItemResponse

        try:
            with open(opts['restore'], encoding='utf-8') as fh:
                payload = json.load(fh)
        except (OSError, ValueError) as exc:
            raise CommandError(f'Cannot read backup file: {exc}')
        if payload.get('format') != BACKUP_FORMAT:
            raise CommandError(f'{opts["restore"]} is not a backup written '
                               f'by this command.')

        rows = payload.get('rows', [])
        restored = skipped = 0
        with transaction.atomic():
            for row in rows:
                try:
                    resp = QuestionnaireItemResponse.objects.filter(
                        pk=row['id']).first()
                except (ValueError, ValidationError):
                    self.stdout.write(self.style.WARNING(
                        f'  {row.get("id")!r} is not a response id; skipped.'))
                    skipped += 1
                    continue
                if resp is None:
                    skipped += 1
                    continue
                if resp.response_value != row['new'] and not opts['force']:
                    self.stdout.write(self.style.WARNING(
                        f'  {resp.pk}: stored {resp.response_value!r} is not '
                        f'what the backup wrote ({row["new"]!r}); use --force.'))
                    skipped += 1
                    continue
                if resp.response_value == row['old']:
                    continue
                resp.response_value = row['old']
                resp.save(update_fields=['response_value', 'modified_date'])
                restored += 1
        self.stdout.write(self.style.SUCCESS(
            f'Restored {restored} value(s), skipped {skipped}.'))

    # ── target resolution ─────────────────────────────────────────────────
    def _resolve_targets(self, opts):
        """Map the requested ids to QuestionnaireItem rows.

        The response model points at QuestionnaireItem, but the ids handed to
        this command may come from either table (or from a REDCap metadata
        dump), so both are tried and the answer is printed.
        """
        from promapp.models import QuestionnaireItem

        specs = self._parse_items(opts['item'])
        targets = []
        for value, meridian in specs:
            try:
                key = uuid.UUID(str(value))
            except (ValueError, AttributeError):
                raise CommandError(f'{value!r} is not a UUID.')

            direct = list(QuestionnaireItem.objects.filter(
                pk=key).values_list('id', flat=True))
            via_item = list(QuestionnaireItem.objects.filter(
                item_id=key).values_list('id', flat=True))
            qi_ids = direct or via_item
            if not qi_ids:
                raise CommandError(
                    f'{key}: no QuestionnaireItem and no Item with this id. '
                    'Check the id (and remember Items are per-questionnaire '
                    'through QuestionnaireItem).')
            if direct and via_item:
                self.stdout.write(self.style.WARNING(
                    f'{key} matched a QuestionnaireItem and the Item of the '
                    'same id; using the QuestionnaireItem.'))
            for qi_id in qi_ids:
                targets.append((qi_id, _item_label(qi_id), meridian))
            if len(qi_ids) > 1:
                self.stdout.write(self.style.WARNING(
                    f'{key} is used by {len(qi_ids)} questionnaire items; all '
                    'will be rewritten with meridian=' + meridian + '.'))
        return targets

    def _parse_items(self, supplied):
        if not supplied:
            return list(LEGACY_TIME_ITEMS)
        specs = []
        for entry in supplied:
            value, _, meridian = entry.partition(':')
            meridian = (meridian or 'auto').lower()
            if meridian not in MERIDIAN_CHOICES:
                raise CommandError(
                    f'{entry}: meridian must be one of '
                    f'{", ".join(MERIDIAN_CHOICES)}.')
            specs.append((value.strip(), meridian))
        return specs

    def _warn_equations(self, targets):
        """Time answers are not score operands; shout if they are used anyway."""
        from promapp.models import QuestionnaireItem

        for qi_id, _label, _meridian in targets:
            qi = QuestionnaireItem.objects.select_related('item').filter(
                pk=qi_id).first()
            if qi is None or qi.item_id is None:
                continue
            try:
                check = qi.item.is_referenced_in_equation()
            except Exception:  # noqa: BLE001 - a warning must never break a run
                continue
            if check.get('is_referenced'):
                self.stdout.write(self.style.WARNING(
                    f'  NOTE: {_label} is referenced in construct scale '
                    f'equation(s) {check["equations"]} - scores that were '
                    'calculated from the old numeric text will have to be '
                    'recalculated.'))


def _item_label(qi_id):
    """'Q7: item text' for reports; never raises on missing translations."""
    from promapp.models import QuestionnaireItem

    qi = QuestionnaireItem.objects.select_related('item').filter(
        pk=qi_id).first()
    if qi is None:
        return f'QuestionnaireItem {qi_id}'
    name = ''
    item = getattr(qi, 'item', None)
    if item is not None:
        try:
            name = item.safe_translation_getter('name', any_language=True) or ''
        except Exception:  # noqa: BLE001 - a report label must not break a run
            name = ''
    return f'Q{qi.question_number}: {name}' if name else \
        f'QuestionnaireItem {qi_id} (Q{qi.question_number})'


def _now():
    from django.utils import timezone
    return timezone.now()
