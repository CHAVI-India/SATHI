"""
Celery tasks for parallel plot generation.

This module contains Celery tasks that generate Bokeh plots for the PRO Review page.
Tasks are designed to run in parallel to speed up page loading.
"""

import logging
import json
from celery import shared_task
from celery_progress.backend import ProgressRecorder
from django.template.loader import render_to_string
from django.core.cache import cache

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def generate_plots_batch_task(self, patient_id, plots, filters, user_id):
    """
    Generate multiple plots in a single task with progress tracking.
    
    Args:
        patient_id: UUID string of the patient
        plots: List of {'type': 'construct'|'composite'|'item', 'id': uuid_string}
        filters: Dict of filter parameters
        user_id: ID of the requesting user (for permission checks)
    
    Returns:
        List of {'plot_id': str, 'plot_type': str, 'html': str, 'metadata': dict}
    """
    progress_recorder = ProgressRecorder(self)
    results = []
    
    logger.info(f"Starting batch plot generation for patient {patient_id}, {len(plots)} plots")
    
    for i, plot in enumerate(plots):
        plot_type = plot['type']
        plot_id = plot['id']
        
        # Update progress
        progress_recorder.set_progress(
            i + 1, 
            len(plots), 
            description=f"Generating {plot_type} plot {i + 1}/{len(plots)}"
        )
        
        try:
            # Generate plot based on type
            if plot_type == 'construct':
                html, metadata = generate_construct_plot(patient_id, plot_id, filters)
            elif plot_type == 'composite':
                html, metadata = generate_composite_plot(patient_id, plot_id, filters)
            elif plot_type == 'item':
                html, metadata = generate_item_plot(patient_id, plot_id, filters)
            else:
                logger.warning(f"Unknown plot type: {plot_type}")
                html = f'<div class="text-red-500">Unknown plot type: {plot_type}</div>'
                metadata = {}
            
            results.append({
                'plot_id': str(plot_id),
                'plot_type': plot_type,
                'html': html,
                'metadata': metadata
            })
            
        except Exception as e:
            logger.error(f"Error generating {plot_type} plot {plot_id}: {e}", exc_info=True)
            results.append({
                'plot_id': str(plot_id),
                'plot_type': plot_type,
                'html': f'<div class="text-red-500 text-center py-4">Error loading plot</div>',
                'metadata': {'error': str(e)}
            })
    
    logger.info(f"Completed batch plot generation for patient {patient_id}, {len(results)} plots")
    return results


def generate_construct_plot(patient_id, construct_id, filters):
    """
    Generate a single construct plot and return (HTML, metadata).
    
    This extracts the core logic from prom_review_construct_plot view.
    """
    from django.shortcuts import get_object_or_404
    from patientapp.models import Patient
    from promapp.models import ConstructScale, QuestionnaireConstructScore, QuestionnaireSubmission
    from patientapp.utils import (
        ConstructScoreData, get_patient_start_date, calculate_time_interval_value,
        filter_positive_intervals_construct, get_filtered_patients_for_aggregation,
        aggregate_construct_scores_by_time_interval, calculate_aggregation_statistics
    )
    import time as time_module
    
    # Get patient
    patient = get_object_or_404(Patient, id=patient_id)
    
    # Extract filter parameters
    questionnaire_filter = filters.get('questionnaire_filter')
    max_time_interval = filters.get('max_time_interval')
    time_range = filters.get('time_range', '5')
    start_date_reference = filters.get('start_date_reference', 'date_of_registration')
    time_interval = filters.get('time_interval', 'weeks')
    aggregation_type = filters.get('aggregation_type', 'median_iqr')
    patient_filter_gender = filters.get('patient_filter_gender')
    patient_filter_diagnosis = filters.get('patient_filter_diagnosis')
    patient_filter_treatment = filters.get('patient_filter_treatment')
    patient_filter_min_age = filters.get('patient_filter_min_age')
    patient_filter_max_age = filters.get('patient_filter_max_age')
    
    # Get selected indicators
    selected_indicators = filters.get('selected_indicators', [])
    if isinstance(selected_indicators, str):
        try:
            selected_indicators = json.loads(selected_indicators)
        except (json.JSONDecodeError, TypeError):
            selected_indicators = []
    
    # Convert filters to proper types
    max_time_interval_value = None
    if max_time_interval:
        try:
            max_time_interval_value = float(max_time_interval)
        except (ValueError, TypeError):
            pass
    
    min_age_value = None
    max_age_value = None
    if patient_filter_min_age:
        try:
            min_age_value = int(patient_filter_min_age)
        except (ValueError, TypeError):
            pass
    if patient_filter_max_age:
        try:
            max_age_value = int(patient_filter_max_age)
        except (ValueError, TypeError):
            pass
    
    # Get construct
    construct = get_object_or_404(ConstructScale, id=construct_id)
    
    # Get patient start date
    patient_start_date = get_patient_start_date(patient, start_date_reference)
    
    # Get submission count
    submission_count_base_query = QuestionnaireSubmission.objects.filter(patient=patient)
    
    if max_time_interval_value is not None and patient_start_date:
        filtered_submission_ids = []
        for submission in submission_count_base_query.select_related():
            interval_value = calculate_time_interval_value(
                submission.submission_date,
                patient_start_date,
                time_interval
            )
            if interval_value <= max_time_interval_value:
                filtered_submission_ids.append(submission.id)
        submission_count_base_query = submission_count_base_query.filter(id__in=filtered_submission_ids)
    
    if time_range == 'all':
        submission_count = submission_count_base_query.count()
    else:
        submission_count = int(time_range)
        actual_available_count = submission_count_base_query.count()
        submission_count = min(submission_count, actual_available_count)
    
    # Get construct scores with caching
    scores_cache_key = (
        f"scores_{str(patient_id)}_{str(construct_id)}"
        f"_{questionnaire_filter or 'all'}"
        f"_{time_range}"
        f"_{str(max_time_interval_value) if max_time_interval_value else 'none'}"
        f"_{start_date_reference}"
        f"_{time_interval}"
    )
    
    historical_scores = cache.get(scores_cache_key)
    if not historical_scores:
        construct_scores = QuestionnaireConstructScore.objects.filter(
            construct=construct,
            questionnaire_submission__patient=patient
        ).select_related(
            'questionnaire_submission',
            'construct'
        ).order_by('-questionnaire_submission__submission_date')
        
        if questionnaire_filter:
            construct_scores = construct_scores.filter(
                questionnaire_submission__patient_questionnaire__questionnaire_id=questionnaire_filter
            )
        
        if max_time_interval_value is not None and patient_start_date:
            filtered_score_ids = []
            for score in construct_scores:
                interval_value = calculate_time_interval_value(
                    score.questionnaire_submission.submission_date,
                    patient_start_date,
                    time_interval
                )
                if interval_value <= max_time_interval_value:
                    filtered_score_ids.append(score.id)
            construct_scores = construct_scores.filter(id__in=filtered_score_ids)
        
        historical_scores = list(construct_scores[:submission_count])
        
        if patient_start_date:
            historical_scores = filter_positive_intervals_construct(
                historical_scores, patient_start_date, time_interval
            )
        
        cache.set(scores_cache_key, historical_scores, 300)
    
    # Get aggregated patients
    aggregated_patients = get_filtered_patients_for_aggregation(
        exclude_patient=patient,
        patient_filter_gender=patient_filter_gender,
        patient_filter_diagnosis=patient_filter_diagnosis,
        patient_filter_treatment=patient_filter_treatment,
        patient_filter_min_age=min_age_value,
        patient_filter_max_age=max_age_value
    )
    
    t_agg_start = time_module.perf_counter()
    
    # Calculate aggregated statistics
    aggregated_statistics = None
    aggregation_metadata = None
    if aggregated_patients and historical_scores:
        try:
            reference_intervals = []
            for score_obj in historical_scores:
                interval_value = calculate_time_interval_value(
                    score_obj.questionnaire_submission.submission_date,
                    patient_start_date,
                    time_interval
                )
                if interval_value not in reference_intervals:
                    reference_intervals.append(interval_value)
            reference_intervals.sort()
            
            aggregated_data, aggregation_metadata = aggregate_construct_scores_by_time_interval(
                construct=construct,
                patients_queryset=aggregated_patients,
                start_date_reference=start_date_reference,
                time_interval=time_interval,
                max_time_interval_filter=max_time_interval_value,
                reference_time_intervals=reference_intervals
            )
            
            if aggregated_data:
                aggregated_statistics = calculate_aggregation_statistics(
                    aggregated_data, aggregation_type
                )
        except Exception as e:
            logger.error(f"Error calculating aggregated data for construct {construct.name}: {e}")
    
    t_agg_ms = round((time_module.perf_counter() - t_agg_start) * 1000)
    
    # Get current and previous scores
    current_score = historical_scores[0].score if historical_scores else None
    previous_score = historical_scores[1].score if len(historical_scores) > 1 else None
    
    t_plot_start = time_module.perf_counter()
    
    # Create construct score data object (this generates the plot)
    score_data = ConstructScoreData(
        construct=construct,
        current_score=current_score,
        previous_score=previous_score,
        historical_scores=historical_scores,
        patient=patient,
        start_date_reference=start_date_reference,
        time_interval=time_interval,
        aggregated_statistics=aggregated_statistics,
        aggregation_metadata=aggregation_metadata,
        aggregation_type=aggregation_type,
        selected_indicators=selected_indicators
    )
    
    t_plot_ms = round((time_module.perf_counter() - t_plot_start) * 1000)
    
    # Render template
    html = render_to_string('promapp/partials/construct_plot.html', {'score_data': score_data})
    
    # Build metadata
    metadata = {
        'timing_aggregation_ms': t_agg_ms,
        'timing_plot_ms': t_plot_ms,
    }
    if aggregation_metadata:
        metadata['contributing_patients'] = aggregation_metadata.get('contributing_patients', 0)
        metadata['total_responses'] = aggregation_metadata.get('total_responses', 0)
        metadata['time_range'] = aggregation_metadata.get('time_range', 'N/A')
        metadata['time_interval_unit'] = aggregation_metadata.get('time_interval_unit', 'weeks')
    
    return html, metadata


def generate_composite_plot(patient_id, composite_id, filters):
    """
    Generate a single composite construct plot and return (HTML, metadata).
    """
    from django.shortcuts import get_object_or_404
    from patientapp.models import Patient
    from promapp.models import CompositeConstructScaleScoring, QuestionnaireConstructScoreComposite, QuestionnaireSubmission
    from patientapp.utils import (
        CompositeConstructScoreData, get_patient_start_date, calculate_time_interval_value,
        filter_positive_intervals_composite
    )
    import json
    
    # Get patient
    patient = get_object_or_404(Patient, id=patient_id)
    
    # Extract filter parameters
    max_time_interval = filters.get('max_time_interval')
    time_range = filters.get('time_range', '5')
    start_date_reference = filters.get('start_date_reference', 'date_of_registration')
    time_interval = filters.get('time_interval', 'weeks')
    
    # Get selected indicators
    selected_indicators = filters.get('selected_indicators', [])
    if isinstance(selected_indicators, str):
        try:
            selected_indicators = json.loads(selected_indicators)
        except (json.JSONDecodeError, TypeError):
            selected_indicators = []
    
    # Convert filters
    max_time_interval_value = None
    if max_time_interval:
        try:
            max_time_interval_value = float(max_time_interval)
        except (ValueError, TypeError):
            pass
    
    # Get composite construct scale
    composite_scale = get_object_or_404(CompositeConstructScaleScoring, id=composite_id)
    
    # Get patient start date
    patient_start_date = get_patient_start_date(patient, start_date_reference)
    
    # Get submission count
    submission_count_base_query = QuestionnaireSubmission.objects.filter(patient=patient)
    
    if max_time_interval_value is not None and patient_start_date:
        filtered_submission_ids = []
        for submission in submission_count_base_query.select_related():
            interval_value = calculate_time_interval_value(
                submission.submission_date,
                patient_start_date,
                time_interval
            )
            if interval_value <= max_time_interval_value:
                filtered_submission_ids.append(submission.id)
        submission_count_base_query = submission_count_base_query.filter(id__in=filtered_submission_ids)
    
    if time_range == 'all':
        submission_count = submission_count_base_query.count()
    else:
        submission_count = int(time_range)
        actual_available_count = submission_count_base_query.count()
        submission_count = min(submission_count, actual_available_count)
    
    # Get composite scores with caching
    comp_cache_key = (
        f"comp_scores_{str(patient_id)}_{str(composite_id)}"
        f"_{time_range}"
        f"_{str(max_time_interval_value) if max_time_interval_value else 'none'}"
        f"_{start_date_reference}"
        f"_{time_interval}"
    )
    
    historical_scores = cache.get(comp_cache_key)
    if not historical_scores:
        composite_scores = QuestionnaireConstructScoreComposite.objects.filter(
            composite_construct_scale=composite_scale,
            questionnaire_submission__patient=patient
        ).select_related(
            'questionnaire_submission',
            'composite_construct_scale'
        ).order_by('-questionnaire_submission__submission_date')
        
        if max_time_interval_value is not None and patient_start_date:
            filtered_score_ids = []
            for score in composite_scores:
                interval_value = calculate_time_interval_value(
                    score.questionnaire_submission.submission_date,
                    patient_start_date,
                    time_interval
                )
                if interval_value <= max_time_interval_value:
                    filtered_score_ids.append(score.id)
            composite_scores = composite_scores.filter(id__in=filtered_score_ids)
        
        historical_scores = list(composite_scores[:submission_count])
        
        if patient_start_date:
            historical_scores = filter_positive_intervals_composite(
                historical_scores, patient_start_date, time_interval
            )
        
        cache.set(comp_cache_key, historical_scores, 300)
    
    # Get current and previous scores
    current_score = historical_scores[0].score if historical_scores else None
    previous_score = historical_scores[1].score if len(historical_scores) > 1 else None
    
    # Create composite score data object
    score_data = CompositeConstructScoreData(
        composite_construct_scale=composite_scale,
        current_score=current_score,
        previous_score=previous_score,
        historical_scores=historical_scores,
        patient=patient,
        start_date_reference=start_date_reference,
        time_interval=time_interval,
        selected_indicators=selected_indicators
    )
    
    # Render template
    html = render_to_string('promapp/partials/construct_plot.html', {'score_data': score_data})
    
    return html, {}


def generate_item_plot(patient_id, item_id, filters):
    """
    Generate a single item plot and return (HTML, metadata).
    """
    from django.shortcuts import get_object_or_404
    from patientapp.models import Patient
    from promapp.models import Item, QuestionnaireItemResponse, QuestionnaireSubmission
    from patientapp.utils import (
        get_patient_start_date, calculate_time_interval_value,
        filter_positive_intervals, create_item_response_plot
    )
    import json
    
    # Get patient
    patient = get_object_or_404(Patient, id=patient_id)
    
    # Extract filter parameters
    questionnaire_filter = filters.get('questionnaire_filter')
    max_time_interval = filters.get('max_time_interval')
    time_range = filters.get('time_range', '5')
    start_date_reference = filters.get('start_date_reference', 'date_of_registration')
    time_interval = filters.get('time_interval', 'weeks')
    
    # Get selected indicators
    selected_indicators = filters.get('selected_indicators', [])
    if isinstance(selected_indicators, str):
        try:
            selected_indicators = json.loads(selected_indicators)
        except (json.JSONDecodeError, TypeError):
            selected_indicators = []
    
    # Convert filters
    max_time_interval_value = None
    if max_time_interval:
        try:
            max_time_interval_value = float(max_time_interval)
        except (ValueError, TypeError):
            pass
    
    # Get item
    item = get_object_or_404(Item, id=item_id)
    
    # Get patient start date
    patient_start_date = get_patient_start_date(patient, start_date_reference)
    
    # Get submission count
    submission_count_base_query = QuestionnaireSubmission.objects.filter(patient=patient)
    
    if max_time_interval_value is not None and patient_start_date:
        filtered_submission_ids = []
        for submission in submission_count_base_query.select_related():
            interval_value = calculate_time_interval_value(
                submission.submission_date,
                patient_start_date,
                time_interval
            )
            if interval_value <= max_time_interval_value:
                filtered_submission_ids.append(submission.id)
        submission_count_base_query = submission_count_base_query.filter(id__in=filtered_submission_ids)
    
    if time_range == 'all':
        submission_count = submission_count_base_query.count()
    else:
        submission_count = int(time_range)
        actual_available_count = submission_count_base_query.count()
        submission_count = min(submission_count, actual_available_count)
    
    # Get item responses with caching
    item_cache_key = (
        f"item_resp_{str(patient_id)}_{str(item_id)}"
        f"_{questionnaire_filter or 'all'}"
        f"_{time_range}"
        f"_{str(max_time_interval_value) if max_time_interval_value else 'none'}"
        f"_{start_date_reference}"
        f"_{time_interval}"
    )
    
    historical_responses = cache.get(item_cache_key)
    if not historical_responses:
        item_responses = QuestionnaireItemResponse.objects.filter(
            questionnaire_item__item=item,
            questionnaire_submission__patient=patient
        ).select_related(
            'questionnaire_submission',
            'questionnaire_item'
        ).order_by('-questionnaire_submission__submission_date')
        
        if max_time_interval_value is not None and patient_start_date:
            filtered_response_ids = []
            for response in item_responses:
                interval_value = calculate_time_interval_value(
                    response.questionnaire_submission.submission_date,
                    patient_start_date,
                    time_interval
                )
                if interval_value <= max_time_interval_value:
                    filtered_response_ids.append(response.id)
            item_responses = item_responses.filter(id__in=filtered_response_ids)
        
        historical_responses = list(item_responses[:submission_count])
        
        if patient_start_date:
            historical_responses = filter_positive_intervals(
                historical_responses, patient_start_date, time_interval
            )
        
        cache.set(item_cache_key, historical_responses, 300)
    
    # Generate plot
    bokeh_plot = None
    if historical_responses:
        bokeh_plot = create_item_response_plot(
            historical_responses,
            item,
            patient,
            start_date_reference,
            time_interval,
            selected_indicators
        )
    
    # Render template
    html = render_to_string('promapp/partials/item_plot.html', {
        'bokeh_plot': bokeh_plot,
        'item': item,
    })
    
    return html, {}
