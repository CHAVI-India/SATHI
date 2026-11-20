def _build_csv_export(request, mapping, selected_fms, id_map,
                      on_invalid=ON_INVALID_SKIP_ROW):
    """Return a ZIP HttpResponse containing one CSV per form mapping and log the export.

    Every selected form mapping contributes a CSV — headers only when none of its
    rows passed validation — and anything that was skipped or blanked is listed in
    `validation_errors.csv` inside the archive. A handful of badly entered answers
    therefore costs the export those cells or rows, never the whole file.
    """
    grouped = _collect_export_rows_per_fm(
        mapping, selected_fms, id_map, on_invalid=on_invalid
    )
    results = list(grouped.values())
    all_warnings = [w for result in results for w in result.warnings]
    all_issues = [issue for result in results for issue in result.issues]
    rows_exported = sum(len(result.rows) for result in results)
    skipped_rows = sum(result.skipped_rows for result in results)
    blanked_cells = sum(result.blanked_cells for result in results)

    if not rows_exported and not all_issues:
        messages.warning(request, _('No data found for the selected form mappings.'))
        return redirect(request.path)

    # Build ZIP in memory with one CSV per form mapping
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        used_names = set()
        for result in results:
            # Column order REDCap expects, plus anything a row added on top.
            all_keys = list(result.columns)
            seen = set(all_keys)
            for row in result.rows:
                for k in row:
                    if k not in seen:
                        all_keys.append(k)
                        seen.add(k)
            csv_buf = io.StringIO()
            writer = csv.DictWriter(csv_buf, fieldnames=all_keys, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(result.rows)
            # Distinct name per form mapping: two mappings may share a REDCap
            # form name, which used to overwrite one form's whole CSV.
            member = _unique_zip_name(used_names, _safe_zip_stem(result.fm.redcap_form_name))
            zf.writestr(member, csv_buf.getvalue())

        if all_issues:
            report_buf = io.StringIO()
            writer = csv.DictWriter(
                report_buf, fieldnames=VALIDATION_ERROR_COLUMNS, extrasaction='ignore'
            )
            writer.writeheader()
            writer.writerows(all_issues)
            zf.writestr(_unique_zip_name(used_names, 'validation_errors'),
                        report_buf.getvalue())
    buf.seek(0)

    filename = f'redcap_export_{mapping.project.project_name}.zip'

    # Log one entry per patient per fm
    from promapp.models import QuestionnaireSubmission as _QS
    patient_map = {p.pk: p for p in Patient.objects.filter(pk__in=id_map.keys())}
    now = timezone.now()
    log_entries = []
    for result in results:
        fm = result.fm
        # Only log for patients who actually have submissions for this fm
        patient_ids_with_subs = set(
            _QS.objects.filter(
                patient_questionnaire__questionnaire=fm.questionnaire,
                patient__in=id_map.keys(),
            ).values_list('patient_id', flat=True)
        )
        log_note = f'CSV export: {filename}'
        if result.issues:
            log_note += (f' — {result.skipped_rows} row(s) skipped, '
                         f'{result.blanked_cells} cell(s) left blank')
        for patient_id in patient_ids_with_subs:
            log_entries.append(RedcapDataExportLog(
                redcap_form_to_questionnaire_mapping=fm,
                patient=patient_map.get(patient_id),
                user_exporting_data=request.user,
                export_type=ExportTypeChoices.MANUAL,
                datetime_export_start=now,
                datetime_export_completed=now,
                # A run that had to drop or blank data is not a clean export.
                export_status=(ExportStatusChoices.INCOMPLETE if result.issues
                               else ExportStatusChoices.COMPLETED),
                export_log=log_note,
            ))
    RedcapDataExportLog.objects.bulk_create(log_entries)

    if not all_warnings:
        response = HttpResponse(buf.getvalue(), content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    # Store the ZIP in a temp file so we can redirect (showing warnings)
    # while still offering the file for download afterwards.
    token = uuid.uuid4().hex
    fd, tmp_path = tempfile.mkstemp(suffix='.zip', prefix='redcap_export_')
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(buf.getvalue())
    except Exception:
        os.close(fd)
        raise
    request.session['redcap_export_warnings'] = all_warnings
    request.session['redcap_export_download'] = {
        'token': token,
        'path': tmp_path,
        'filename': filename,
    }
    if rows_exported:
        messages.warning(request, _(
            'Exported %(rows)s row(s); %(skipped)s row(s) skipped and %(blanked)s cell(s) '
            'left blank because their stored answers do not fit the REDCap field format. '
            'See the warnings below and validation_errors.csv inside the archive. '
            'Your export file is ready for download.'
        ) % {'rows': rows_exported, 'skipped': skipped_rows, 'blanked': blanked_cells})
    else:
        messages.error(request, _(
            'Nothing could be exported: every row failed validation '
            '(%(skipped)s row(s) skipped). The archive contains the column headers and '
            'validation_errors.csv, so you can fix the answers or the field mappings and '
            'run the export again.'
        ) % {'skipped': skipped_rows})
    return redirect(request.path)


def _run_api_export(request, pk, mapping_pk, mapping, selected_fms, id_map,
                    on_invalid=ON_INVALID_SKIP_ROW):
    """Export via REDCap API using PyCap and log results.

    Uses the same validation policy as the CSV export: rows whose answers fail
    validation are skipped (or blanked when opted in) and reported, and a form
    mapping whose rows all failed is left out of the API call instead of failing
    the whole run.
    """
    grouped = _collect_export_rows_per_fm(
        mapping, selected_fms, id_map, on_invalid=on_invalid
    )
    results = list(grouped.values())
    exportable = [result for result in results if result.rows]
    all_warnings = [w for result in results for w in result.warnings]
    all_issues = [issue for result in results for issue in result.issues]
    skipped_rows = sum(result.skipped_rows for result in results)
    blanked_cells = sum(result.blanked_cells for result in results)

    if all_warnings:
        request.session['redcap_export_warnings'] = all_warnings

    if not exportable:
        if all_issues:
            messages.error(request, _(
                'Nothing was sent to REDCap: every row failed validation '
                '(%(skipped)s row(s) skipped). See the warnings below for the fields '
                'and values to fix.'
            ) % {'skipped': skipped_rows})
        else:
            messages.warning(request, _('No data found for the selected form mappings.'))
        return redirect('redcap_export', pk=pk, mapping_pk=mapping_pk)

    if all_warnings:
        messages.warning(request, _(
            '%(skipped)s row(s) were skipped and %(blanked)s cell(s) left blank before the '
            'API push because their stored answers do not fit the REDCap field format. '
            'See the warnings below.'
        ) % {'skipped': skipped_rows, 'blanked': blanked_cells})

    from promapp.models import QuestionnaireSubmission as _QS
    patient_map = {p.pk: p for p in Patient.objects.filter(pk__in=id_map.keys())}
    for result in exportable:
        fm = result.fm
        rows = result.rows
        patient_ids_with_subs = set(
            _QS.objects.filter(
                patient_questionnaire__questionnaire=fm.questionnaire,
                patient__in=id_map.keys(),
            ).values_list('patient_id', flat=True)
        )
        patients_for_fm = [patient_map.get(pid) for pid in patient_ids_with_subs] or [None]
        # Create one pending log per patient before the API call
        logs = [
            RedcapDataExportLog.objects.create(
                redcap_form_to_questionnaire_mapping=fm,
                patient=patient,
                user_exporting_data=request.user,
                export_type=ExportTypeChoices.AUTOMATIC,
                datetime_export_start=timezone.now(),
                export_status=ExportStatusChoices.PENDING,
            )
            for patient in patients_for_fm
        ]
        try:
            response_data = redcap_import_records(mapping, rows)
            # A run that had to drop or blank data is not a clean export.
            final_status = (ExportStatusChoices.INCOMPLETE if result.issues
                            else ExportStatusChoices.COMPLETED)
            log_text = str(response_data)
            if result.issues:
                log_text += (f' | {result.skipped_rows} row(s) skipped, '
                             f'{result.blanked_cells} cell(s) left blank by validation')
        except Exception as e:
            final_status = ExportStatusChoices.FAILED
            log_text = str(e)
        completed_at = timezone.now()
        for log in logs:
            log.export_status = final_status
            log.export_log = log_text
            log.datetime_export_completed = completed_at
            log.save(update_fields=['export_status', 'export_log', 'datetime_export_completed', 'modified_at'])

    messages.success(request, _('API export completed. Check the log below for details.'))
    return redirect('redcap_export', pk=pk, mapping_pk=mapping_pk)
