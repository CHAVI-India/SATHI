from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.utils.translation import gettext_lazy as _, gettext, get_language
from django.utils import timezone
from django.db import transaction
from django.db.models import Q, Count, Max
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.http import JsonResponse
from .models import Patient, Diagnosis, DiagnosisList, Treatment, Institution, GenderChoices, TreatmentType, TreatmentIntentChoices
from .forms import PatientForm, TreatmentForm, DiagnosisForm, PatientRestrictedUpdateForm, DiagnosisListForm
from promapp.models import *
from .utils import (
    ConstructScoreData, calculate_percentage, create_item_response_plot, get_patient_start_date, 
    get_patient_available_start_dates, filter_positive_intervals, filter_positive_intervals_construct, 
    get_interval_label, calculate_time_interval_value,
    # Institution filtering utilities
    get_user_institution, is_provider_user, filter_patients_by_institution, 
    check_patient_access, get_accessible_patient_or_404, InstitutionFilterMixin
)
import logging
from bokeh.resources import CDN
from patientapp.utils import get_filtered_patients_for_aggregation


logger = logging.getLogger(__name__)

# Create your views here.


@login_required
@permission_required('patientapp.view_patient', raise_exception=True)
def prom_review(request, pk):
    """View for the PRO Review page that shows patient questionnaire responses.
    Supports global filtering for all sections of the page.
    """
    logger.info(f"PRO Review view called for patient ID: {pk}")
    
    # Get patient with institution access check
    patient = get_accessible_patient_or_404(request.user, pk)
    logger.info(f"Found patient: {patient.name} (ID: {patient.id})")
    
    # Get filter parameters
    questionnaire_filter = request.GET.get('questionnaire_filter')
    max_time_interval = request.GET.get('max_time_interval')
    time_range = request.GET.get('time_range', '5')
    item_filter = request.GET.getlist('item_filter')  # Get list of selected item IDs
    start_date_reference = request.GET.get('start_date_reference', 'date_of_registration')
    time_interval = request.GET.get('time_interval', 'weeks')
    
    # Get selected indicators for plot display
    selected_indicators_param = request.GET.get('selected_indicators')
    selected_indicators = []
    if selected_indicators_param:
        try:
            import json
            selected_indicators = json.loads(selected_indicators_param)
            logger.info(f"Selected indicators: {len(selected_indicators)} indicators")
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning(f"Failed to parse selected_indicators parameter: {e}")
            selected_indicators = []
    
    # Convert max_time_interval to float if provided
    max_time_interval_value = None
    if max_time_interval:
        try:
            max_time_interval_value = float(max_time_interval)
            logger.info(f"Max time interval filter: {max_time_interval_value} {time_interval}")
        except (ValueError, TypeError):
            logger.warning(f"Invalid max_time_interval value: {max_time_interval}")
    
    logger.info(f"Item filter received: {item_filter}")
    
    # Get aggregation parameters - aggregation is now always enabled
    show_aggregated = True  # Always show aggregated data
    aggregation_type = request.GET.get('aggregation_type', 'median_iqr')
    patient_filter_gender = request.GET.get('patient_filter_gender')
    patient_filter_diagnosis = request.GET.get('patient_filter_diagnosis')
    patient_filter_treatment = request.GET.get('patient_filter_treatment')
    patient_filter_min_age = request.GET.get('patient_filter_min_age')
    patient_filter_max_age = request.GET.get('patient_filter_max_age')
    
    # Convert age filters to integers if provided
    min_age_value = None
    max_age_value = None
    if patient_filter_min_age:
        try:
            min_age_value = int(patient_filter_min_age)
        except (ValueError, TypeError):
            logger.warning(f"Invalid min age value: {patient_filter_min_age}")
    
    if patient_filter_max_age:
        try:
            max_age_value = int(patient_filter_max_age)
        except (ValueError, TypeError):
            logger.warning(f"Invalid max age value: {patient_filter_max_age}")
    
    logger.info(f"Aggregation settings: show_aggregated={show_aggregated}, type={aggregation_type}, gender={patient_filter_gender}, diagnosis={patient_filter_diagnosis}, treatment={patient_filter_treatment}, min_age={min_age_value}, max_age={max_age_value}")
    
    # Always get aggregated patients to show patient counts, regardless of whether aggregation is enabled
    aggregated_patients = get_filtered_patients_for_aggregation(
        exclude_patient=patient,
        patient_filter_gender=patient_filter_gender,
        patient_filter_diagnosis=patient_filter_diagnosis,
        patient_filter_treatment=patient_filter_treatment,
        patient_filter_min_age=min_age_value,
        patient_filter_max_age=max_age_value
    )
    logger.info(f"Found {aggregated_patients.count()} patients for aggregation (aggregation enabled: {show_aggregated})")
    
    # Get start date for this patient for relative time calculations
    patient_start_date = get_patient_start_date(patient, start_date_reference)
    
    # Get submission count from time range or default to 5
    # This count needs to respect the max_time_interval filter if active.
    
    # Base query for counting submissions, respecting patient and potentially time interval filter
    submission_count_base_query = QuestionnaireSubmission.objects.filter(patient=patient)
    
    # Apply max time interval filter if specified
    if max_time_interval_value is not None and patient_start_date:
        # Filter submissions to only include those within the specified time interval from start date
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
        logger.info(f"Applied max time interval filter: {len(filtered_submission_ids)} submissions within {max_time_interval_value} {time_interval}")

    if time_range == 'all':
        submission_count = submission_count_base_query.count()
        # If count is 0 (e.g. no submissions up to filter time interval, or no submissions at all), plot will be empty.
    else:
        submission_count = int(time_range)
        # Ensure submission_count doesn't exceed available submissions after time interval filter
        # (or total submissions if no time interval filter)
        actual_available_count = submission_count_base_query.count()
        submission_count = min(submission_count, actual_available_count)
    
    logger.info(f"Using submission count for plots: {submission_count}")
    
    # Get all questionnaire submissions for this patient
    submissions = QuestionnaireSubmission.objects.filter(
        patient=patient
    ).select_related(
        'patient_questionnaire',
        'patient_questionnaire__questionnaire'
    ).prefetch_related(
        'patient_questionnaire__questionnaire__translations'
    )
    
    # Apply questionnaire filter if specified
    if questionnaire_filter:
        submissions = submissions.filter(
            patient_questionnaire__questionnaire_id=questionnaire_filter
        )
    
    # Apply max time interval filter if specified
    if max_time_interval_value is not None and patient_start_date:
        # Filter submissions based on relative time intervals
        filtered_submission_ids = []
        for submission in submissions.select_related():
            interval_value = calculate_time_interval_value(
                submission.submission_date,
                patient_start_date,
                time_interval
            )
            if interval_value <= max_time_interval_value:
                filtered_submission_ids.append(submission.id)
        
        submissions = submissions.filter(id__in=filtered_submission_ids)
    
    # Order by submission date
    submissions = submissions.order_by('-submission_date')
    
    logger.info(f"Found {submissions.count()} total submissions")
    
    # Get submission counts per questionnaire
    questionnaire_submission_counts = {}
    for submission in submissions:
        q_id = submission.patient_questionnaire.questionnaire_id
        questionnaire_submission_counts[q_id] = questionnaire_submission_counts.get(q_id, 0) + 1
    
    # Get the latest submission for each questionnaire, respecting filters
    latest_submissions = {}
    for submission in submissions:
        q_id = submission.patient_questionnaire.questionnaire_id
        # Only add if we haven't seen this questionnaire yet or if this submission is more recent
        if q_id not in latest_submissions or submission.submission_date > latest_submissions[q_id].submission_date:
            latest_submissions[q_id] = submission
            logger.info(f"Latest submission for questionnaire {q_id}: {submission.submission_date}")
    
    # Get all assigned questionnaires
    all_assigned_questionnaires = PatientQuestionnaire.objects.filter(
        patient=patient
    ).select_related(
        'questionnaire'
    ).prefetch_related(
        'questionnaire__translations'
    )
    
    # Keep a reference to all questionnaires for dropdown options
    assigned_questionnaires = all_assigned_questionnaires
    
    # Apply questionnaire filter to assigned questionnaires if specified for data filtering
    if questionnaire_filter:
        assigned_questionnaires = assigned_questionnaires.filter(
            questionnaire_id=questionnaire_filter
        )
    
    logger.info(f"Found {assigned_questionnaires.count()} assigned questionnaires")
    
    # Get item responses for the latest submissions
    item_responses = QuestionnaireItemResponse.objects.filter(
        questionnaire_submission__in=latest_submissions.values()
    ).select_related(
        'questionnaire_item',
        'questionnaire_item__item',
        'questionnaire_item__item__likert_response',
        'questionnaire_item__item__range_response',
        'questionnaire_submission'  # Add this for submission date access
    ).prefetch_related(
        'questionnaire_item__item__likert_response__likertscaleresponseoption_set',
        'questionnaire_item__item__likert_response__likertscaleresponseoption_set__translations'
    )
    
    # Apply questionnaire filter to item responses if specified
    if questionnaire_filter:
        item_responses = item_responses.filter(
            questionnaire_item__questionnaire_id=questionnaire_filter
        )
    
    # Apply item filter if specified
    if item_filter:
        item_responses = item_responses.filter(
            questionnaire_item__item_id__in=item_filter
        )
        logger.info(f"After applying item filter {item_filter}, found {item_responses.count()} item responses")
    else:
        logger.info(f"No item filter applied, found {item_responses.count()} total item responses")
    
    # === OPTIMIZATION: Bulk fetch previous responses for all items ===
    item_response_list = list(item_responses)
    previous_responses_map = {}
    historical_responses_map = {}
    
    # === OPTIMIZATION: Bulk fetch all Likert scale options to avoid N+1 queries ===
    likert_options_map = {}
    if item_response_list:
        # Get all unique Likert scale IDs from the items
        likert_scale_ids = set()
        for response in item_response_list:
            if (response.questionnaire_item.item.response_type == 'Likert' and 
                response.questionnaire_item.item.likert_response_id):
                likert_scale_ids.add(response.questionnaire_item.item.likert_response_id)
        
        if likert_scale_ids:
            # Bulk fetch all Likert scale options for these scales
            from promapp.models import LikertScaleResponseOption
            all_likert_options = LikertScaleResponseOption.objects.filter(
                likert_scale_id__in=likert_scale_ids
            ).select_related('likert_scale').prefetch_related('translations').order_by('likert_scale_id', 'option_value')
            
            # Group options by likert_scale_id
            for option in all_likert_options:
                scale_id = option.likert_scale_id
                if scale_id not in likert_options_map:
                    likert_options_map[scale_id] = []
                likert_options_map[scale_id].append(option)
    
    if item_response_list:
        # Get all questionnaire items that have responses
        questionnaire_item_ids = [resp.questionnaire_item.id for resp in item_response_list]
        
        # Bulk fetch all previous responses for these items
        all_previous_responses = QuestionnaireItemResponse.objects.filter(
            questionnaire_item__id__in=questionnaire_item_ids,
            questionnaire_submission__patient=patient
        ).select_related(
            'questionnaire_submission',
            'questionnaire_item'
        ).order_by('questionnaire_item', '-questionnaire_submission__submission_date')
        
        # Group previous responses by questionnaire item
        responses_by_item = {}
        for response in all_previous_responses:
            item_id = response.questionnaire_item.id
            if item_id not in responses_by_item:
                responses_by_item[item_id] = []
            responses_by_item[item_id].append(response)
        
        # Find previous response for each current response
        for current_response in item_response_list:
            item_id = current_response.questionnaire_item.id
            item_responses_list = responses_by_item.get(item_id, [])
            
            # Find the response that comes before the current one
            for response in item_responses_list:
                if response.questionnaire_submission.submission_date < current_response.questionnaire_submission.submission_date:
                    previous_responses_map[current_response.id] = response
                    break
            
            # Store historical responses for plotting (apply filters)
            historical_responses_for_item = item_responses_list.copy()
            
            # Apply max time interval filter if specified
            if max_time_interval_value is not None and patient_start_date:
                filtered_historical = []
                for hist_response in historical_responses_for_item:
                    interval_value = calculate_time_interval_value(
                        hist_response.questionnaire_submission.submission_date,
                        patient_start_date,
                        time_interval
                    )
                    if interval_value <= max_time_interval_value:
                        filtered_historical.append(hist_response)
                historical_responses_for_item = filtered_historical
            
            # Take only the submission_count most recent
            historical_responses_for_item = historical_responses_for_item[:submission_count]
            
            # Filter out responses with negative time intervals
            if patient_start_date:
                historical_responses_for_item = filter_positive_intervals(
                    historical_responses_for_item, patient_start_date, time_interval
                )
            
            historical_responses_map[current_response.id] = historical_responses_for_item
    
    # Calculate percentages and add option text for item responses
    for response in item_response_list:
        current_value_for_change_calc = None
        response.bokeh_plot = None # Initialize bokeh_plot for all responses

        # Type-specific processing
        if response.questionnaire_item.item.response_type == 'Numeric' and response.questionnaire_item.item.range_response:
            try:
                numeric_value = float(response.response_value) if response.response_value else None
                response.numeric_response = numeric_value
                current_value_for_change_calc = numeric_value
                response.percentage = calculate_percentage(numeric_value, response.questionnaire_item.item.range_response.max_value)
            except (ValueError, TypeError):
                response.numeric_response = None
                response.percentage = 0
        elif response.questionnaire_item.item.response_type == 'Likert' and response.questionnaire_item.item.likert_response:
            try:
                likert_value = float(response.response_value) if response.response_value else None
                response.likert_response = likert_value
                current_value_for_change_calc = likert_value
                
                # Use bulk-fetched options to calculate max value
                likert_scale_id = response.questionnaire_item.item.likert_response_id
                options_list = likert_options_map.get(likert_scale_id, [])
                max_value = max(option.option_value for option in options_list) if options_list else None
                response.percentage = calculate_percentage(likert_value, max_value)
                
                likert_scale = response.questionnaire_item.item.likert_response
                better_direction = response.questionnaire_item.item.item_better_score_direction or 'Higher is Better'
                
                # Calculate color map directly using bulk-fetched options
                if options_list:
                    sorted_options = sorted(options_list, key=lambda x: x.option_value)
                    n_options = len(sorted_options)
                    colors = likert_scale.get_viridis_colors(n_options)
                    color_map = {}
                    for i, option in enumerate(sorted_options):
                        if better_direction == 'Higher is Better':
                            color_map[str(option.option_value)] = colors[i]
                        else:
                            color_map[str(option.option_value)] = colors[-(i+1)]
                else:
                    color_map = {}
                
                # Use the bulk-fetched options_list
                for option in options_list:
                    if str(option.option_value) == response.response_value:
                        response.option_text = option.option_text
                        response.option_color = color_map.get(str(option.option_value), '#ffffff')
                        response.text_color = likert_scale.get_text_color(response.option_color)
                        break
            except (ValueError, TypeError) as e_likert_proc:
                logger.error(f"Error processing Likert item {response.questionnaire_item.item.id} (Response ID {response.id}): {e_likert_proc}", exc_info=True)
                response.likert_response = None
                response.percentage = 0
        elif response.questionnaire_item.item.response_type == 'Media':
            # Handle media responses
            try:
                if response.response_media:
                    # Determine media type using the existing get_media_type method
                    media_type = None
                    if hasattr(response.response_media, 'name') and response.response_media.name:
                        file_name = str(response.response_media.name).lower()
                        
                        # Audio file extensions
                        audio_extensions = ['.mp3', '.wav', '.ogg', '.m4a', '.aac', '.flac']
                        if any(file_name.endswith(ext) for ext in audio_extensions):
                            media_type = 'audio'
                        # Video file extensions
                        elif any(file_name.endswith(ext) for ext in ['.mp4', '.webm', '.avi', '.mov', '.wmv', '.mkv']):
                            media_type = 'video'
                        # Image file extensions
                        elif any(file_name.endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp', '.tiff', '.ico']):
                            media_type = 'image'
                        # Default to 'other' if no match
                        else:
                            media_type = 'other'
                    
                    response.media_type = media_type or 'other'
                else:
                    response.media_type = None
            except Exception as e_media_proc:
                logger.error(f"Error processing Media item {response.questionnaire_item.item.id} (Response ID {response.id}): {e_media_proc}", exc_info=True)
                response.media_type = None
        
        # Get previous response for change calculation using the bulk-fetched data
        response.previous_value = None
        response.value_change = None
        if current_value_for_change_calc is not None:
            previous_response_obj = previous_responses_map.get(response.id)
            if previous_response_obj and previous_response_obj.response_value:
                try:
                    previous_value_float = float(previous_response_obj.response_value)
                    response.previous_value = previous_value_float
                    response.value_change = current_value_for_change_calc - previous_value_float
                except (ValueError, TypeError):
                    logger.warning(f"Could not parse previous value for item {response.questionnaire_item.item.id} (Response ID {response.id})")

        # Get historical responses for plotting using the bulk-fetched data
        try:
            historical_responses_for_plot = historical_responses_map.get(response.id, [])
            
            logger.debug(f"Item {response.questionnaire_item.item.id} (Response ID {response.id}): Found {len(historical_responses_for_plot)} historical responses for plot after filtering (submission_count: {submission_count}, max_time_interval: {max_time_interval_value}).")

            if historical_responses_for_plot:
                response.bokeh_plot = create_item_response_plot(
                    historical_responses_for_plot, # Pass the filtered and sliced list
                    response.questionnaire_item.item,
                    patient,
                    start_date_reference,
                    time_interval,
                    selected_indicators
                )
                if not response.bokeh_plot:
                    logger.warning(f"Item {response.questionnaire_item.item.id} (Response ID {response.id}): create_item_response_plot returned None or empty string.")
            else:
                logger.info(f"Item {response.questionnaire_item.item.id} (Response ID {response.id}): No historical responses to plot after filtering, setting bokeh_plot to None.")
        except Exception as e_plot_gen:
            logger.error(f"Error generating plot for item {response.questionnaire_item.item.id} (Response ID {response.id}): {e_plot_gen}", exc_info=True)
    
    logger.info(f"Found {len(item_response_list)} item responses")
    
    # Get construct scores for the latest submissions
    construct_scores = QuestionnaireConstructScore.objects.filter(
        questionnaire_submission__in=latest_submissions.values()
    ).select_related(
        'construct',
        'questionnaire_submission'  # Add this for submission date access
    )
    
    # Apply questionnaire filter to construct scores if specified
    if questionnaire_filter:
        construct_scores = construct_scores.filter(
            questionnaire_submission__patient_questionnaire__questionnaire_id=questionnaire_filter
        )
    
    logger.info(f"Found {construct_scores.count()} construct scores")
    
    # Get composite construct scores for the latest submissions
    composite_construct_scores = QuestionnaireConstructScoreComposite.objects.filter(
        questionnaire_submission__in=latest_submissions.values()
    ).select_related(
        'composite_construct_scale',
        'questionnaire_submission'  # Add this for submission date access
    )
    
    # Apply questionnaire filter to composite construct scores if specified
    if questionnaire_filter:
        composite_construct_scores = composite_construct_scores.filter(
            questionnaire_submission__patient_questionnaire__questionnaire_id=questionnaire_filter
        )
    
    logger.info(f"Found {composite_construct_scores.count()} composite construct scores")

    # === OPTIMIZATION: Bulk fetch previous construct scores ===
    construct_scores_list = list(construct_scores)
    previous_construct_scores_map = {}
    historical_construct_scores_map = {}
    
    if construct_scores_list:
        # Get all constructs that have scores
        construct_ids = [cs.construct.id for cs in construct_scores_list]
        
        # Bulk fetch all construct scores for these constructs
        all_construct_scores = QuestionnaireConstructScore.objects.filter(
            construct__id__in=construct_ids,
            questionnaire_submission__patient=patient
        ).select_related(
            'questionnaire_submission',
            'construct'
        ).order_by('construct', '-questionnaire_submission__submission_date')
        
        # Group construct scores by construct
        scores_by_construct = {}
        for score in all_construct_scores:
            construct_id = score.construct.id
            if construct_id not in scores_by_construct:
                scores_by_construct[construct_id] = []
            scores_by_construct[construct_id].append(score)
        
        # Find previous score for each current score
        for current_score in construct_scores_list:
            construct_id = current_score.construct.id
            construct_scores_list_for_construct = scores_by_construct.get(construct_id, [])
            
            # Find the score that comes before the current one
            for score in construct_scores_list_for_construct:
                if score.questionnaire_submission.submission_date < current_score.questionnaire_submission.submission_date:
                    previous_construct_scores_map[current_score.id] = score
                    break
            
            # Store historical scores for plotting (apply filters)
            historical_scores_for_construct = construct_scores_list_for_construct.copy()
            
            # Apply max time interval filter if specified
            if max_time_interval_value is not None and patient_start_date:
                filtered_historical = []
                for hist_score in historical_scores_for_construct:
                    interval_value = calculate_time_interval_value(
                        hist_score.questionnaire_submission.submission_date,
                        patient_start_date,
                        time_interval
                    )
                    if interval_value <= max_time_interval_value:
                        filtered_historical.append(hist_score)
                historical_scores_for_construct = filtered_historical
            
            # Take only the submission_count most recent
            historical_scores_for_construct = historical_scores_for_construct[:submission_count]
            
            # Filter out scores with negative time intervals
            if patient_start_date:
                historical_scores_for_construct = filter_positive_intervals_construct(
                    historical_scores_for_construct, patient_start_date, time_interval
                )
            
            historical_construct_scores_map[current_score.id] = historical_scores_for_construct

    # Add historical data to construct scores using bulk-fetched data
    for construct_score in construct_scores_list:
        # Get previous score for change calculation using bulk-fetched data
        previous_score_obj = previous_construct_scores_map.get(construct_score.id)
        construct_score.previous_score = previous_score_obj.score if previous_score_obj else None
        construct_score.score_change = None
        if construct_score.score is not None and construct_score.previous_score is not None:
            construct_score.score_change = construct_score.score - construct_score.previous_score

    # === OPTIMIZATION: Bulk fetch previous composite construct scores ===
    composite_construct_scores_list = list(composite_construct_scores)
    previous_composite_scores_map = {}
    
    if composite_construct_scores_list:
        # Get all composite constructs that have scores
        composite_construct_ids = [cs.composite_construct_scale.id for cs in composite_construct_scores_list]
        
        # Bulk fetch all composite construct scores for these constructs
        all_composite_scores = QuestionnaireConstructScoreComposite.objects.filter(
            composite_construct_scale__id__in=composite_construct_ids,
            questionnaire_submission__patient=patient
        ).select_related(
            'questionnaire_submission',
            'composite_construct_scale'
        ).order_by('composite_construct_scale', '-questionnaire_submission__submission_date')
        
        # Group composite scores by composite construct
        composite_scores_by_construct = {}
        for score in all_composite_scores:
            construct_id = score.composite_construct_scale.id
            if construct_id not in composite_scores_by_construct:
                composite_scores_by_construct[construct_id] = []
            composite_scores_by_construct[construct_id].append(score)
        
        # Find previous score for each current score
        for current_score in composite_construct_scores_list:
            construct_id = current_score.composite_construct_scale.id
            composite_scores_list_for_construct = composite_scores_by_construct.get(construct_id, [])
            
            # Find the score that comes before the current one
            for score in composite_scores_list_for_construct:
                if score.questionnaire_submission.submission_date < current_score.questionnaire_submission.submission_date:
                    previous_composite_scores_map[current_score.id] = score
                    break

    # Add historical data to composite construct scores using bulk-fetched data
    for composite_score in composite_construct_scores_list:
        # Get previous composite score for change calculation using bulk-fetched data
        previous_composite_obj = previous_composite_scores_map.get(composite_score.id)
        composite_score.previous_score = previous_composite_obj.score if previous_composite_obj else None
        composite_score.score_change = None
        if composite_score.score is not None and composite_score.previous_score is not None:
            composite_score.score_change = composite_score.score - composite_score.previous_score

    # Get all construct scores with plots (both important and other)
    important_construct_scores = []
    other_construct_scores_with_plots = []
    logger.info("Processing construct scores to create plot data...")
    
    # Log plotting session start
    from patientapp.utils import log_plotting_session_start
    log_plotting_session_start(patient.name, len(construct_scores_list))
    
    for construct_score in construct_scores_list:
        construct = construct_score.construct
        logger.info(f"Processing construct: {construct.name}")
        
        # Get historical scores for this construct's plot using bulk-fetched data
        historical_scores_for_plot = historical_construct_scores_map.get(construct_score.id, [])
        
        logger.debug(f"Found {len(historical_scores_for_plot)} historical scores for {construct.name} plot after filtering (submission_count: {submission_count}, max_time_interval: {max_time_interval_value}).")

        # Determine the 'previous_score' for ConstructScoreData based on this plot-specific historical data.
        # This 'previous_score' is for the context of the plot and the ConstructScoreData object.
        # The main card display uses construct_score.previous_score which is already correctly calculated.
        previous_score_for_plot_context = None
        if len(historical_scores_for_plot) > 1:
            # historical_scores_for_plot is latest first, so [1] is the second latest.
            previous_score_for_plot_context = historical_scores_for_plot[1].score
            logger.debug(f"Previous score for {construct.name} (plot context): {previous_score_for_plot_context}")

        # Calculate aggregated statistics - now always enabled
        aggregated_statistics = None
        aggregation_metadata = None
        if aggregated_patients and historical_scores_for_plot:
            try:
                from patientapp.utils import (
                    aggregate_construct_scores_by_time_interval,
                    calculate_aggregation_statistics
                )
                
                # Get reference time intervals from the index patient's data
                reference_intervals = []
                for score_obj in historical_scores_for_plot:
                    interval_value = calculate_time_interval_value(
                        score_obj.questionnaire_submission.submission_date,
                        patient_start_date,
                        time_interval
                    )
                    if interval_value not in reference_intervals:
                        reference_intervals.append(interval_value)
                
                # Sort reference intervals
                reference_intervals.sort()
                
                # Check how many patients in the aggregation pool have the requested start date type
                patients_with_requested_start_date = 0
                for agg_patient in aggregated_patients:
                    # Use aggregation-friendly start date logic
                    from patientapp.utils import get_patient_start_date_for_aggregation
                    patient_start_date_agg = get_patient_start_date_for_aggregation(agg_patient, start_date_reference)
                    if patient_start_date_agg:
                        patients_with_requested_start_date += 1
                
                total_agg_patients = aggregated_patients.count()
                
                # Proceed with aggregation if we have patients with the requested start date type
                if patients_with_requested_start_date > 0:
                    logger.info(f"Proceeding with aggregation using '{start_date_reference}': {patients_with_requested_start_date}/{total_agg_patients} patients have this start date type.")
                    
                    # Aggregate data from other patients using the requested start date reference
                    aggregated_data, aggregation_metadata = aggregate_construct_scores_by_time_interval(
                        construct=construct,
                        patients_queryset=aggregated_patients,
                        start_date_reference=start_date_reference,
                        time_interval=time_interval,
                        max_time_interval_filter=max_time_interval_value,
                        reference_time_intervals=reference_intervals
                    )
                    
                    # Calculate statistics only if we have meaningful data
                    if aggregated_data:
                        aggregated_statistics = calculate_aggregation_statistics(
                            aggregated_data, aggregation_type
                        )
                        
                        logger.debug(f"Construct {construct.name}: Generated aggregated statistics for {len(aggregated_statistics)} intervals using start_date_reference '{start_date_reference}'")
                    else:
                        logger.info(f"No aggregated data available for construct {construct.name} with start_date_reference '{start_date_reference}' - patients may not have construct scores in the time range")
                        
                        # Create metadata to show why no data is available
                        aggregation_metadata = {
                            'total_eligible_patients': total_agg_patients,
                            'contributing_patients': 0,
                            'total_responses': 0,
                            'time_intervals_count': 0,
                            'time_range': 'N/A',
                            'time_interval_unit': get_interval_label(time_interval).lower(),
                            'no_data_reason': f"{patients_with_requested_start_date} patients have the selected start date type '{start_date_reference}', but no construct scores are available in the specified time range.",
                            'patients_with_start_date': patients_with_requested_start_date,
                            'patient_details': {'contributing': [], 'non_contributing': []}
                        }
                    
                else:
                    logger.info(f"No patients available for aggregation with '{start_date_reference}': {patients_with_requested_start_date}/{total_agg_patients} patients have this start date type.")
                    
                    # Create metadata to show why aggregation is not available
                    aggregation_metadata = {
                        'total_eligible_patients': total_agg_patients,
                        'contributing_patients': 0,
                        'total_responses': 0,
                        'time_intervals_count': 0,
                        'time_range': 'N/A',
                        'time_interval_unit': get_interval_label(time_interval).lower(),
                        'insufficient_patients_reason': f"No patients in the selected population have the start date type '{start_date_reference}'. Try selecting a different start date reference or adjusting the population filters.",
                        'patients_with_start_date': patients_with_requested_start_date,
                        'patient_details': {'contributing': [], 'non_contributing': []}
                    }
                
            except Exception as e:
                logger.error(f"Error calculating aggregated data for construct {construct.name}: {e}")

        # Create construct score data object
        score_data = ConstructScoreData(
            construct=construct, # construct_score.construct
            current_score=construct_score.score, # This is from the main construct_scores list, respecting filters for card display
            previous_score=construct_score.previous_score, # Use the actual previous score for change calculations
            historical_scores=historical_scores_for_plot, # Filtered and sliced list for the plot
            patient=patient,
            start_date_reference=start_date_reference,
            time_interval=time_interval,
            aggregated_statistics=aggregated_statistics,  # Pass aggregated statistics
            aggregation_metadata=aggregation_metadata,  # Pass aggregation metadata
            aggregation_type=aggregation_type,  # Pass aggregation type for tooltips
            selected_indicators=selected_indicators  # Pass selected indicators for plot display
        )

        # Categorize as important or other construct
        if ConstructScoreData.is_important_construct(construct, construct_score.score):
            logger.info(f"Adding {construct.name} to important constructs")
            important_construct_scores.append(score_data)
        else:
            logger.info(f"Adding {construct.name} to other constructs")
            other_construct_scores_with_plots.append(score_data)
    
    logger.info(f"Found {len(important_construct_scores)} important construct scores")
    logger.info(f"Found {len(other_construct_scores_with_plots)} other construct scores with plots")
    
    # Get Bokeh resources
    bokeh_css = CDN.render_css()
    bokeh_js = CDN.render_js()
    
    # =========================
    # Group items by construct
    # =========================
    # Create construct ordering: important (topline) constructs first, then others,
    # and finally any constructs present in item responses but missing from scores lists.
    important_construct_order = [cs.construct.id for cs in important_construct_scores]
    other_construct_order = [cs.construct.id for cs in other_construct_scores_with_plots]
    construct_order = []
    for cid in important_construct_order + other_construct_order:
        if cid not in construct_order:
            construct_order.append(cid)

    # Add any constructs that appear in item responses but aren't in the above order
    # Handle ManyToMany relationship - an item can belong to multiple construct scales
    item_construct_ids = []
    construct_obj_by_id = {}
    for resp in item_response_list:
        # Get all construct scales for this item (ManyToMany)
        item_constructs = resp.questionnaire_item.item.construct_scale.all()
        for construct in item_constructs:
            cid = construct.id
            if cid not in item_construct_ids:
                item_construct_ids.append(cid)
            # Cache construct object for template header use
            construct_obj_by_id[cid] = construct
    
    for cid in item_construct_ids:
        if cid not in construct_order:
            construct_order.append(cid)

    # Build grouped structure in the specified order
    # Map responses by construct id first for efficiency
    # An item can belong to multiple constructs, so a response may appear in multiple groups
    responses_by_construct = {}
    for resp in item_response_list:
        # Get all construct scales for this item (ManyToMany)
        item_constructs = resp.questionnaire_item.item.construct_scale.all()
        for construct in item_constructs:
            cid = construct.id
            responses_by_construct.setdefault(cid, []).append(resp)

    item_responses_grouped = []
    for cid in construct_order:
        items = responses_by_construct.get(cid, [])
        if not items:
            continue
        construct_obj = construct_obj_by_id.get(cid)
        # Fallback: try to obtain construct object from scores if not cached
        if not construct_obj:
            for cs in important_construct_scores + other_construct_scores_with_plots:
                if cs.construct.id == cid:
                    construct_obj = cs.construct
                    break
        if construct_obj:
            # Identify worsened items for this construct
            worsened_items = []
            improved_items = []
            stable_items = []
            
            for item_resp in items:
                # Only consider items with numeric/likert responses that have change data
                if item_resp.value_change is not None:
                    item_better_direction = item_resp.questionnaire_item.item.item_better_score_direction or 'Higher is Better'
                    
                    # Determine if item has worsened based on direction
                    if item_better_direction == 'Higher is Better':
                        if item_resp.value_change < 0:  # Score decreased = worsened
                            worsened_items.append(item_resp)
                        elif item_resp.value_change > 0:  # Score increased = improved
                            improved_items.append(item_resp)
                        else:
                            stable_items.append(item_resp)
                    elif item_better_direction == 'Lower is Better':
                        if item_resp.value_change > 0:  # Score increased = worsened
                            worsened_items.append(item_resp)
                        elif item_resp.value_change < 0:  # Score decreased = improved
                            improved_items.append(item_resp)
                        else:
                            stable_items.append(item_resp)
            
            # Sort worsened items by magnitude of worsening (largest first)
            worsened_items.sort(key=lambda x: abs(x.value_change), reverse=True)
            improved_items.sort(key=lambda x: abs(x.value_change), reverse=True)
            
            item_responses_grouped.append({
                'construct': construct_obj,
                'items': items,
                'worsened_items': worsened_items,
                'improved_items': improved_items,
                'stable_items': stable_items,
            })
    # Provide important construct ids list for template badges/ordering if needed
    important_construct_ids_list = [str(cid) for cid in important_construct_order]

    # Get available items for the filter (based on current questionnaire filter)
    # Use prefetch_related for ManyToMany construct_scale relationship
    available_items_query = Item.objects.prefetch_related('construct_scale', 'translations')
    
    if questionnaire_filter:
        # Get items from the selected questionnaire
        available_items_query = available_items_query.filter(
            questionnaireitem__questionnaire_id=questionnaire_filter
        ).distinct()
    else:
        # Get items from all assigned questionnaires
        questionnaire_ids = all_assigned_questionnaires.values_list('questionnaire_id', flat=True)
        available_items_query = available_items_query.filter(
            questionnaireitem__questionnaire_id__in=questionnaire_ids
        ).distinct()
    
    # Can't order by ManyToMany field directly, so order by item_number only
    available_items = available_items_query.order_by('item_number')
    
    # Get selected item details for proper initialization
    selected_items_data = []
    if item_filter:
        selected_items = Item.objects.filter(id__in=item_filter).prefetch_related('translations')
        selected_items_data = [{'id': str(item.id), 'name': item.name} for item in selected_items]

    # Prepare options for Cotton dropdowns
    questionnaire_options_for_cotton = [
        {'id': str(pq.questionnaire.id), 'name': pq.questionnaire.name}
        for pq in all_assigned_questionnaires  # Use the unfiltered list for dropdown options
    ]

    time_range_options_for_cotton = [
        ("3", gettext("3 submissions")),
        ("5", gettext("5 submissions")),
        ("10", gettext("10 submissions")),
        ("15", gettext("15 submissions")),
        ("all", gettext("All submissions")),
    ]
    selected_time_range_for_cotton = request.GET.get('time_range', '5')

    # Get available start dates for this patient
    available_start_dates = get_patient_available_start_dates(patient)
    
    # Ensure we have at least the registration date as fallback
    if not available_start_dates:
        available_start_dates = [('date_of_registration', 'Date of Registration', patient.created_date.date())]
    
    # Set default start_date_reference if not provided
    if not start_date_reference:
        start_date_reference = available_start_dates[0][0] if available_start_dates else 'date_of_registration'

    # Get available diagnoses and treatment types for aggregation filters
    from patientapp.models import DiagnosisList, TreatmentType
    
    # Get unique diagnoses that are actually assigned to patients
    available_diagnoses = DiagnosisList.objects.filter(
        diagnosis_list__patient__isnull=False
    ).distinct().order_by('diagnosis')
    
    # Get unique treatment types that are actually assigned to patients
    available_treatment_types = TreatmentType.objects.filter(
        treatment__diagnosis__patient__isnull=False
    ).distinct().order_by('treatment_type')

    # Get patient's current age for potential display
    from patientapp.utils import calculate_patient_age
    patient_current_age = calculate_patient_age(patient)

    # Calculate aggregation metadata - now always available since aggregation is always enabled
    aggregation_metadata = None
    if aggregated_patients:
        try:
            # Collect metadata from all the construct aggregations that were already calculated
            total_eligible_patients = aggregated_patients.count()
            total_responses = 0
            time_intervals_count = 0
            time_ranges = []
            all_patient_details = {'contributing': [], 'non_contributing': []}
            
            # Get patient details from the first construct that has aggregation data
            found_patient_details = False
            
            # Aggregate metadata from important construct calculations (which have aggregated_statistics)
            for score_data in important_construct_scores:
                if hasattr(score_data, 'aggregated_statistics') and score_data.aggregated_statistics:
                    # Count unique time intervals across all constructs
                    construct_intervals = list(score_data.aggregated_statistics.keys())
                    if construct_intervals:
                        time_intervals_count = max(time_intervals_count, len(construct_intervals))
                        time_ranges.extend([min(construct_intervals), max(construct_intervals)])
                    
                    # Count responses from this construct's aggregation
                    for interval_stats in score_data.aggregated_statistics.values():
                        if 'n' in interval_stats:
                            total_responses += interval_stats['n']
                    
                    # Get patient details from the construct's metadata (if available)
                    if not found_patient_details and hasattr(score_data, 'aggregation_metadata'):
                        if 'patient_details' in score_data.aggregation_metadata:
                            all_patient_details = score_data.aggregation_metadata['patient_details']
                            found_patient_details = True
            
            # If we don't have patient details yet, try to get them from a fresh calculation
            if not found_patient_details and important_construct_scores:
                try:
                    first_construct = important_construct_scores[0]
                    if hasattr(first_construct, 'construct'):
                        from patientapp.utils import aggregate_construct_scores_by_time_interval
                        
                        # Check if we have sufficient patients with the requested start date type
                        patients_with_requested_start_date = 0
                        for agg_patient in aggregated_patients:
                            # Use aggregation-friendly start date logic
                            from patientapp.utils import get_patient_start_date_for_aggregation
                            patient_start_date_agg = get_patient_start_date_for_aggregation(agg_patient, start_date_reference)
                            if patient_start_date_agg:
                                patients_with_requested_start_date += 1
                        
                        # Proceed if we have patients with the requested start date type (consistent with main aggregation logic)
                        if patients_with_requested_start_date > 0 and patient_start_date and hasattr(first_construct, 'aggregated_statistics') and first_construct.aggregated_statistics:
                            # Get reference intervals from this construct
                            reference_intervals = sorted(list(first_construct.aggregated_statistics.keys()))
                            if reference_intervals:
                                # Get fresh metadata with patient details using the requested start date reference
                                _, metadata_with_details = aggregate_construct_scores_by_time_interval(
                                    construct=first_construct.construct,
                                    patients_queryset=aggregated_patients,
                                    start_date_reference=start_date_reference,
                                    time_interval=time_interval,
                                    max_time_interval_filter=max_time_interval_value,
                                    reference_time_intervals=reference_intervals
                                )
                                if 'patient_details' in metadata_with_details:
                                    all_patient_details = metadata_with_details['patient_details']
                                    found_patient_details = True
                                    
                                    logger.info(f"Successfully retrieved patient details using start_date_reference '{start_date_reference}': {len(all_patient_details['contributing'])} contributing, {len(all_patient_details['non_contributing'])} non-contributing")
                        else:
                            logger.info(f"Cannot retrieve patient details: no patients ({patients_with_requested_start_date}) with start_date_reference '{start_date_reference}' or no aggregated statistics available")
                except Exception as e:
                    logger.error(f"Error getting patient details: {e}")
            
            # Calculate overall time range
            time_range = None
            if time_ranges:
                min_time = min(time_ranges)
                max_time = max(time_ranges)
                if min_time == max_time:
                    time_range = f"{min_time:.1f}"
                else:
                    time_range = f"{min_time:.1f} - {max_time:.1f}"
            
            # Estimate contributing patients (this is approximate since we aggregate across constructs)
            # Use a reasonable estimate based on total responses and intervals
            if time_intervals_count > 0 and total_responses > 0:
                estimated_contributing_patients = min(
                    total_responses // max(1, time_intervals_count),
                    total_eligible_patients
                )
            else:
                estimated_contributing_patients = 0
            
            # If we have actual patient details, use the real count
            if found_patient_details:
                estimated_contributing_patients = len(all_patient_details['contributing'])
            
            aggregation_metadata = {
                'total_eligible_patients': total_eligible_patients,
                'contributing_patients': estimated_contributing_patients,
                'total_responses': total_responses,
                'time_intervals_count': time_intervals_count,
                'time_range': time_range or 'N/A',
                'time_interval_unit': get_interval_label(time_interval).lower(),
                'patient_details': all_patient_details,
            }
            
            logger.info(f"Calculated aggregation metadata: {estimated_contributing_patients} contributing patients, {total_responses} responses, {time_intervals_count} intervals, patient_details_found: {found_patient_details}")
                
        except Exception as e:
            logger.error(f"Error calculating aggregation metadata: {e}")
            aggregation_metadata = {
                'total_eligible_patients': aggregated_patients.count() if aggregated_patients else 0,
                'contributing_patients': 0,
                'total_responses': 0,
                'time_intervals_count': 0,
                'time_range': 'N/A',
                'time_interval_unit': get_interval_label(time_interval).lower(),
                'patient_details': {'contributing': [], 'non_contributing': []},
            }

    context = {
        'patient': patient,
        'submissions': submissions,
        'latest_submissions': latest_submissions,
        'assigned_questionnaires': assigned_questionnaires, # Filtered questionnaires for data display
        'all_assigned_questionnaires': all_assigned_questionnaires, # Unfiltered questionnaires for other template needs
        'available_questionnaires': [pq.questionnaire for pq in all_assigned_questionnaires], # For the questionnaire filter dropdown
        'item_responses': item_response_list,  # Use the list instead of queryset
        'construct_scores': construct_scores_list,  # Use the list instead of queryset
        'other_construct_scores': other_construct_scores_with_plots,  # ConstructScoreData objects with plots
        'composite_construct_scores': composite_construct_scores_list,  # Use the list instead of queryset
        'questionnaire_submission_counts': questionnaire_submission_counts,
        'important_construct_scores': important_construct_scores,  # ConstructScoreData objects with plots
        'available_items': available_items,
        'selected_items_data': selected_items_data,
        'item_filter': item_filter,
        'bokeh_css': bokeh_css,
        'bokeh_js': bokeh_js,
        'questionnaire_options_for_cotton': questionnaire_options_for_cotton,
        'time_range_options_for_cotton': time_range_options_for_cotton,
        'selected_time_range_for_cotton': selected_time_range_for_cotton,
        'available_start_dates': available_start_dates,
        'available_diagnoses': available_diagnoses,
        'available_treatment_types': available_treatment_types,
        'aggregation_metadata': aggregation_metadata,
        'patient_current_age': patient_current_age,
        'item_responses_grouped': item_responses_grouped,
        'important_construct_ids': important_construct_ids_list,
    }
    
    # If this is an HTMX request, only return the main content section
    if request.headers.get('HX-Request'):
        return render(request, 'promapp/components/main_content.html', context)
    
    return render(request, 'promapp/prom_review.html', context)


@login_required
@permission_required('patientapp.view_patient', raise_exception=True)
def prom_review_item_search(request, pk):
    """HTMX endpoint for searching items in the item filter autocomplete."""
    patient = get_accessible_patient_or_404(request.user, pk)
    search_query = request.GET.get('item-filter-search', '').strip()
    questionnaire_filter = request.GET.get('questionnaire_filter')
    
    # Get available items based on questionnaire filter
    # Use prefetch_related for ManyToMany construct_scale relationship
    items_query = Item.objects.prefetch_related('construct_scale', 'translations')
    
    if questionnaire_filter:
        # Get items from the selected questionnaire
        items_query = items_query.filter(
            questionnaireitem__questionnaire_id=questionnaire_filter
        ).distinct()
    else:
        # Get items from all assigned questionnaires for this patient
        assigned_questionnaires = PatientQuestionnaire.objects.filter(patient=patient)
        questionnaire_ids = assigned_questionnaires.values_list('questionnaire_id', flat=True)
        items_query = items_query.filter(
            questionnaireitem__questionnaire_id__in=questionnaire_ids
        ).distinct()
    
    # Apply search filter if provided
    if search_query:
        items_query = items_query.filter(
            Q(translations__name__icontains=search_query) |
            Q(construct_scale__name__icontains=search_query)
        ).distinct()
    
    # Limit results to prevent too many options
    # Can't order by ManyToMany field directly
    items = items_query.order_by('item_number')[:20]
    
    context = {
        'items': items,
        'search_query': search_query,
    }
    
    return render(request, 'promapp/partials/item_search_results.html', context)


def patient_portal(request):
    """
    Patient portal view for patients to see their own data and questionnaire responses.
    
    Note: This view does NOT require 'patientapp.view_patient' permission because:
    - Patients should not be given permission to view other patients
    - This view is restricted to the authenticated user's own patient data only
    - Security is enforced by checking request.user.patient exists and matches
    """
    if not request.user.is_authenticated:
        return redirect('login')
    
    # Ensure the user is a patient
    try:
        patient = request.user.patient
        # Additional security: ensure the patient can access their own data
        check_patient_access(request.user, patient)
    except AttributeError:
        messages.error(request, _('You do not have patient access.'))
        return redirect('/')
    
    logger.info(f"Patient portal accessed by: {patient.name} (ID: {patient.id})")
    
    # Get item filter parameters for item selection
    item_filter = request.GET.getlist('item_filter')
    
    # Get selected indicators for plot display
    selected_indicators_param = request.GET.get('selected_indicators')
    selected_indicators = []
    if selected_indicators_param:
        try:
            import json
            selected_indicators = json.loads(selected_indicators_param)
            logger.info(f"Selected indicators: {len(selected_indicators)} indicators")
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning(f"Failed to parse selected_indicators parameter: {e}")
            selected_indicators = []
    
    # Get all questionnaire submissions for this patient
    submissions = QuestionnaireSubmission.objects.filter(
        patient=patient
    ).select_related(
        'patient_questionnaire',
        'patient_questionnaire__questionnaire'
    ).prefetch_related(
        'patient_questionnaire__questionnaire__translations'
    ).order_by('-submission_date')
    
    logger.info(f"Found {submissions.count()} total submissions for patient")
    
    # Get submission counts per questionnaire
    questionnaire_submission_counts = {}
    for submission in submissions:
        q_id = submission.patient_questionnaire.questionnaire_id
        questionnaire_submission_counts[q_id] = questionnaire_submission_counts.get(q_id, 0) + 1
    
    # Get all assigned questionnaires (available questionnaires)
    assigned_questionnaires = PatientQuestionnaire.objects.filter(
        patient=patient,
        display_questionnaire=True  # Only show questionnaires that are supposed to be displayed
    ).select_related(
        'questionnaire'
    ).prefetch_related(
        'questionnaire__translations'
    ).order_by('questionnaire__questionnaire_order')
    
    logger.info(f"Found {assigned_questionnaires.count()} assigned questionnaires")
    
    # Add submission information to each assigned questionnaire
    for pq in assigned_questionnaires:
        # Get the last submission for this questionnaire
        last_submission = QuestionnaireSubmission.objects.filter(
            patient_questionnaire=pq
        ).order_by('-submission_date').first()
        
        pq.last_submission = last_submission
        pq.submission_count = questionnaire_submission_counts.get(pq.questionnaire_id, 0)
        
        if last_submission:
            # Calculate when the questionnaire can be answered next
            interval_seconds = pq.questionnaire.questionnaire_answer_interval
            
            if interval_seconds == 0:
                pq.next_available = last_submission.submission_date
                pq.can_answer = True
            elif interval_seconds < 0:
                pq.next_available = last_submission.submission_date
                pq.can_answer = True
            else:
                next_available = last_submission.submission_date + timezone.timedelta(seconds=interval_seconds)
                pq.next_available = next_available
                pq.can_answer = timezone.now() >= next_available
        else:
            pq.next_available = None
            pq.can_answer = True
    
    # Get item responses for plotting - all responses from all submissions
    item_responses = QuestionnaireItemResponse.objects.filter(
        questionnaire_submission__patient=patient
    ).select_related(
        'questionnaire_item',
        'questionnaire_item__item',
        'questionnaire_item__item__likert_response',
        'questionnaire_item__item__range_response',
        'questionnaire_submission'
    ).prefetch_related(
        'questionnaire_item__item__likert_response__likertscaleresponseoption_set',
        'questionnaire_item__item__likert_response__likertscaleresponseoption_set__translations'
    )
    
    # Apply item filter if specified
    if item_filter:
        item_responses = item_responses.filter(
            questionnaire_item__item_id__in=item_filter
        )
        logger.info(f"After applying item filter {item_filter}, found {item_responses.count()} item responses")
    else:
        logger.info(f"No item filter applied, found {item_responses.count()} total item responses")
    
    # === OPTIMIZATION: Bulk fetch all Likert scale options to avoid N+1 queries ===
    likert_options_map = {}
    if item_responses:
        # Get all unique Likert scale IDs from the items
        likert_scale_ids = set()
        for response in item_responses:
            if (response.questionnaire_item.item.response_type == 'Likert' and 
                response.questionnaire_item.item.likert_response_id):
                likert_scale_ids.add(response.questionnaire_item.item.likert_response_id)
        
        if likert_scale_ids:
            # Bulk fetch all Likert scale options for these scales
            from promapp.models import LikertScaleResponseOption
            all_likert_options = LikertScaleResponseOption.objects.filter(
                likert_scale_id__in=likert_scale_ids
            ).select_related('likert_scale').prefetch_related('translations').order_by('likert_scale_id', 'option_value')
            
            # Group options by likert_scale_id
            for option in all_likert_options:
                scale_id = option.likert_scale_id
                if scale_id not in likert_options_map:
                    likert_options_map[scale_id] = []
                likert_options_map[scale_id].append(option)

    # Group responses by item for plotting
    item_responses_by_item = {}
    for response in item_responses:
        item_id = response.questionnaire_item.item.id
        if item_id not in item_responses_by_item:
            item_responses_by_item[item_id] = {
                'item': response.questionnaire_item.item,
                'responses': []
            }
        item_responses_by_item[item_id]['responses'].append(response)
    
    # Process each item's responses and create plots
    item_plots = []
    media_items = []
    
    for item_id, item_data in item_responses_by_item.items():
        item = item_data['item']
        responses = item_data['responses']
        
        # Sort responses by submission date (oldest first for plotting)
        responses.sort(key=lambda r: r.questionnaire_submission.submission_date)
        
        # Calculate percentages and add option text for item responses
        for response in responses:
            current_value_for_change_calc = None
            
            # Type-specific processing
            if response.questionnaire_item.item.response_type == 'Numeric' and response.questionnaire_item.item.range_response:
                try:
                    numeric_value = float(response.response_value) if response.response_value else None
                    response.numeric_response = numeric_value
                    current_value_for_change_calc = numeric_value
                    response.percentage = calculate_percentage(numeric_value, response.questionnaire_item.item.range_response.max_value)
                except (ValueError, TypeError):
                    response.numeric_response = None
                    response.percentage = 0
            elif response.questionnaire_item.item.response_type == 'Likert' and response.questionnaire_item.item.likert_response:
                try:
                    likert_value = float(response.response_value) if response.response_value else None
                    response.likert_response = likert_value
                    current_value_for_change_calc = likert_value
                    
                    # Use bulk-fetched options to calculate max value
                    likert_scale_id = response.questionnaire_item.item.likert_response_id
                    options_list = likert_options_map.get(likert_scale_id, [])
                    max_value = max(option.option_value for option in options_list) if options_list else None
                    response.percentage = calculate_percentage(likert_value, max_value)
                    
                    likert_scale = response.questionnaire_item.item.likert_response
                    better_direction = response.questionnaire_item.item.item_better_score_direction or 'Higher is Better'
                    
                    # === OPTIMIZATION: Calculate colors in Python using bulk-fetched options ===
                    # Avoid additional database query by calculating colors directly
                    n_options = len(options_list)
                    if n_options > 0:
                        # Sort options for consistent color mapping
                        sorted_options = sorted(options_list, key=lambda x: x.option_value)
                        # Get colors from viridis palette
                        colors = likert_scale.get_viridis_colors(n_options)
                        
                        # Create mapping of option values to colors
                        color_map = {}
                        for i, option in enumerate(sorted_options):
                            if better_direction == 'Higher is Better':
                                # Higher values get lighter colors
                                color_map[str(option.option_value)] = colors[i]
                            else:
                                # Lower values get lighter colors
                                color_map[str(option.option_value)] = colors[-(i+1)]
                    else:
                        color_map = {}
                    
                    # Use the bulk-fetched options_list
                    for option in options_list:
                        if str(option.option_value) == response.response_value:
                            response.option_text = option.option_text
                            response.option_color = color_map.get(str(option.option_value), '#ffffff')
                            response.text_color = likert_scale.get_text_color(response.option_color)
                            break
                except (ValueError, TypeError) as e_likert_proc:
                    logger.error(f"Error processing Likert item {response.questionnaire_item.item.id}: {e_likert_proc}", exc_info=True)
                    response.likert_response = None
                    response.percentage = 0
            elif response.questionnaire_item.item.response_type == 'Media':
                # Handle media responses
                try:
                    if response.response_media:
                        # Determine media type
                        media_type = None
                        if hasattr(response.response_media, 'name') and response.response_media.name:
                            file_name = str(response.response_media.name).lower()
                            
                            # Audio file extensions
                            audio_extensions = ['.mp3', '.wav', '.ogg', '.m4a', '.aac', '.flac']
                            if any(file_name.endswith(ext) for ext in audio_extensions):
                                media_type = 'audio'
                            # Video file extensions
                            elif any(file_name.endswith(ext) for ext in ['.mp4', '.webm', '.avi', '.mov', '.wmv', '.mkv']):
                                media_type = 'video'
                            # Image file extensions
                            elif any(file_name.endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp', '.tiff', '.ico']):
                                media_type = 'image'
                            # Default to 'other' if no match
                            else:
                                media_type = 'other'
                        
                        response.media_type = media_type or 'other'
                    else:
                        response.media_type = None
                except Exception as e_media_proc:
                    logger.error(f"Error processing Media item {response.questionnaire_item.item.id}: {e_media_proc}", exc_info=True)
                    response.media_type = None
        
        # Get the most recent response for display
        most_recent_response = responses[-1] if responses else None
        
        # Handle media items separately (don't create plots for them)
        if item.response_type == 'Media':
            media_items.append({
                'item': item,
                'responses': responses,
                'most_recent_response': most_recent_response,
                'response_count': len(responses)
            })
        else:
            # Create plot for this item using all historical responses
            try:
                plot_html = create_item_response_plot(
                    responses,
                    item,
                    patient,
                    'date_of_registration',  # Use registration date as reference
                    'weeks',  # Use weeks as time interval
                    selected_indicators
                )
                
                item_plots.append({
                    'item': item,
                    'plot_html': plot_html,
                    'responses': responses,
                    'most_recent_response': most_recent_response,
                    'response_count': len(responses)
                })
            except Exception as e_plot_gen:
                logger.error(f"Error generating plot for item {item.id}: {e_plot_gen}", exc_info=True)
    
    # Get available items for the filter
    # Use prefetch_related for ManyToMany construct_scale relationship
    available_items_query = Item.objects.prefetch_related('construct_scale', 'translations')
    
    # Get items from all assigned questionnaires
    questionnaire_ids = assigned_questionnaires.values_list('questionnaire_id', flat=True)
    available_items_query = available_items_query.filter(
        questionnaireitem__questionnaire_id__in=questionnaire_ids
    ).distinct()
    
    # Can't order by ManyToMany field directly
    available_items = available_items_query.order_by('item_number')
    
    # Get selected item details for proper initialization
    selected_items_data = []
    if item_filter:
        selected_items = Item.objects.filter(id__in=item_filter).prefetch_related('translations')
        selected_items_data = [{'id': str(item.id), 'name': item.name} for item in selected_items]

    # Get Bokeh resources
    bokeh_css = CDN.render_css()
    bokeh_js = CDN.render_js()
    
    # Get patient's diagnoses and treatments for display (chronological order - earliest first)
    diagnoses = patient.diagnosis_set.all().order_by('date_of_diagnosis')
    
    context = {
        'patient': patient,
        'submissions': submissions,
        'assigned_questionnaires': assigned_questionnaires,
        'questionnaire_submission_counts': questionnaire_submission_counts,
        'item_plots': item_plots,
        'media_items': media_items,
        'available_items': available_items,
        'selected_items_data': selected_items_data,
        'item_filter': item_filter,
        'bokeh_css': bokeh_css,
        'bokeh_js': bokeh_js,
        'diagnoses': diagnoses,
    }
    
    # If this is an HTMX request for item filter update, only return the plots section
    if request.headers.get('HX-Request'):
        return render(request, 'patientapp/partials/patient_portal_plots.html', context)
    
    return render(request, 'patientapp/patient_portal.html', context)


@login_required
def patient_search_api(request):
    """
    API endpoint for Select2 widget to search patients by name or ID.
    Returns decrypted patient data in Select2 format with pagination support.
    Accessible to users with Provider profile or view_patient permission.
    Optionally filters by questionnaire assignment if questionnaire_id is provided.
    """
    # Check if user has Provider profile or view_patient permission
    from providerapp.models import Provider
    has_provider_profile = hasattr(request.user, 'provider') and Provider.objects.filter(user=request.user).exists()
    has_permission = request.user.has_perm('patientapp.view_patient')
    
    if not (has_provider_profile or has_permission):
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    search_term = request.GET.get('q', '').strip()
    page = int(request.GET.get('page', 1))
    page_size = 50
    questionnaire_id = request.GET.get('questionnaire_id', '').strip()
    
    # Start with base queryset and apply institution filtering
    patients = Patient.objects.select_related('institution').all()
    patients = filter_patients_by_institution(patients, request.user)
    
    # Filter by questionnaire assignment if questionnaire_id is provided
    if questionnaire_id:
        from promapp.models import PatientQuestionnaire
        # Only show patients who have this questionnaire assigned
        patients = patients.filter(
            patientquestionnaire__questionnaire_id=questionnaire_id
        ).distinct()
    
    # Get all patients and decrypt their data for searching
    all_results = []
    for patient in patients:
        # Decrypt the name and patient_id for comparison
        patient_name = patient.name or ''
        patient_id = patient.patient_id or ''
        
        # If there's a search term, filter by it
        if search_term:
            # Case-insensitive search in both name and ID
            if (search_term.lower() in patient_name.lower() or 
                search_term.lower() in patient_id.lower()):
                all_results.append({
                    'id': str(patient.id),
                    'text': f"{patient_name} (ID: {patient_id})",
                    'name': patient_name,
                    'patient_id': patient_id
                })
        else:
            # No search term, return all patients with pagination
            all_results.append({
                'id': str(patient.id),
                'text': f"{patient_name} (ID: {patient_id})",
                'name': patient_name,
                'patient_id': patient_id
            })
    
    # Sort results by name
    all_results.sort(key=lambda x: x['name'].lower() if x['name'] else '')
    
    # Calculate pagination
    start_index = (page - 1) * page_size
    end_index = start_index + page_size
    results = all_results[start_index:end_index]
    has_more = end_index < len(all_results)
    
    return JsonResponse({
        'results': results,
        'pagination': {
            'more': has_more
        }
    })


@login_required
@permission_required('patientapp.view_patient', raise_exception=True)
def patient_list(request):
    # Get filter parameters
    patient_select = request.GET.get('patient_select', '')  # Select2 patient selection
    institution_id = request.GET.get('institution', '')
    gender = request.GET.get('gender', '')
    diagnosis = request.GET.get('diagnosis', '')
    treatment_type = request.GET.get('treatment_type', '')
    questionnaire_count = request.GET.get('questionnaire_count', '')
    sort_by = request.GET.get('sort', 'name')
    
    # Start with base queryset and apply institution filtering
    patients = Patient.objects.select_related('user', 'institution').all()
    patients = filter_patients_by_institution(patients, request.user)
    
    # Apply patient selection filter (from Select2)
    if patient_select:
        # Filter by the specific patient UUID selected from Select2
        patients = patients.filter(id=patient_select)
    
    if institution_id:
        patients = patients.filter(institution_id=institution_id)
    
    if gender:
        patients = patients.filter(gender=gender)
    
    if diagnosis:
        patients = patients.filter(diagnosis__diagnosis__diagnosis__icontains=diagnosis).distinct()
    
    if treatment_type:
        patients = patients.filter(diagnosis__treatment__treatment_type__treatment_type__icontains=treatment_type).distinct()
    
    # Apply questionnaire count filter
    if questionnaire_count:
        if questionnaire_count == '0':
            patients = patients.annotate(
                q_count=Count('patientquestionnaire', distinct=True)
            ).filter(q_count=0)
        elif questionnaire_count == '1-5':
            patients = patients.annotate(
                q_count=Count('patientquestionnaire', distinct=True)
            ).filter(q_count__gte=1, q_count__lte=5)
        elif questionnaire_count == '6-10':
            patients = patients.annotate(
                q_count=Count('patientquestionnaire', distinct=True)
            ).filter(q_count__gte=6, q_count__lte=10)
        elif questionnaire_count == '10+':
            patients = patients.annotate(
                q_count=Count('patientquestionnaire', distinct=True)
            ).filter(q_count__gt=10)
    
    # Apply sorting
    if sort_by == 'name':
        patients = patients.order_by('name')
    elif sort_by == '-name':
        patients = patients.order_by('-name')
    elif sort_by == 'questionnaire_count':
        patients = patients.annotate(
            q_count=Count('patientquestionnaire', distinct=True)
        ).order_by('q_count')
    elif sort_by == '-questionnaire_count':
        patients = patients.annotate(
            q_count=Count('patientquestionnaire', distinct=True)
        ).order_by('-q_count')
    else:
        patients = patients.order_by('name')
    
    # Get institutions for the filter dropdown (filtered by user's institution for providers)
    institutions = Institution.objects.all()
    user_institution = get_user_institution(request.user)
    if user_institution:
        institutions = institutions.filter(id=user_institution.id)
    
    # Get gender choices for the filter dropdown
    gender_choices = GenderChoices.choices
    
    # Get unique diagnoses for the filter dropdown (only from accessible patients)
    diagnoses = list(DiagnosisList.objects.values_list('diagnosis', flat=True).distinct().exclude(diagnosis__isnull=True).exclude(diagnosis=''))
    
    # Get unique treatment types for the filter dropdown (only from accessible patients)
    treatment_types = list(TreatmentType.objects.values_list('treatment_type', flat=True).distinct().exclude(treatment_type__isnull=True).exclude(treatment_type=''))
    
    # Pagination
    page = request.GET.get('page', 1)
    paginator = Paginator(patients, 25)  # Show 25 patients per page to match questionnaire list
    
    try:
        patients = paginator.page(page)
    except PageNotAnInteger:
        patients = paginator.page(1)
    except EmptyPage:
        patients = paginator.page(paginator.num_pages)
    
    # Add questionnaire data to each patient
    current_language = get_language()
    for patient in patients:
        # Import here to avoid circular imports
        from promapp.models import PatientQuestionnaire, Questionnaire
        
        # Count only unique questionnaire assignments
        patient.questionnaire_count = PatientQuestionnaire.objects.filter(
            patient=patient
        ).values('questionnaire').distinct().count()
        
        # Get unique questionnaire names in current language using a subquery
        questionnaire_ids = PatientQuestionnaire.objects.filter(
            patient=patient
        ).values_list('questionnaire_id', flat=True).distinct()
        
        patient.questionnaire_names = list(
            Questionnaire.objects.filter(
                id__in=questionnaire_ids,
                translations__language_code=current_language
            ).values_list('translations__name', flat=True)
        )
    
    # Add dropdown options for filter components
    questionnaire_count_choices = [
        ('0', _('None')),
        ('1-5', _('1-5')),
        ('6-10', _('6-10')),
        ('10+', _('10+')),
    ]
    
    sort_choices = [
        ('name', _('Name')),
        ('-name', _('Name (Z-A)')),
        ('questionnaire_count', _('Questionnaire Count')),
        ('-questionnaire_count', _('Questionnaire Count (High-Low)')),
    ]
    
    context = {
        'patients': patients,
        'institutions': institutions,
        'gender_choices': gender_choices,
        'diagnoses': diagnoses,
        'treatment_types': treatment_types,
        'questionnaire_count_choices': questionnaire_count_choices,
        'sort_choices': sort_choices,
        'is_paginated': patients.has_other_pages(),
        'page_obj': patients,
    }
    
    # If this is an HTMX request, only return the table part
    if request.headers.get('HX-Request'):
        return render(request, 'patientapp/partials/patient_table.html', context)
    
    return render(request, 'patientapp/patient_list.html', context)

@login_required
@permission_required('patientapp.view_patient', raise_exception=True)
def patient_detail(request, pk):
    patient = get_accessible_patient_or_404(request.user, pk)
    diagnoses = patient.diagnosis_set.all().order_by('-created_date')
    context = {
        'patient': patient,
        'diagnoses': diagnoses,
    }
    return render(request, 'patientapp/patient_detail.html', context)

def diagnosis_list(request):
    diagnoses = Diagnosis.objects.all()
    return render(request, 'patientapp/diagnosis_list.html', {'diagnoses': diagnoses})

def diagnosis_detail(request, pk):
    diagnosis = Diagnosis.objects.get(pk=pk)
    return render(request, 'patientapp/diagnosis_detail.html', {'diagnosis': diagnosis})

def treatment_list(request):
    treatments = Treatment.objects.all()
    return render(request, 'patientapp/treatment_list.html', {'treatments': treatments})

def treatment_detail(request, pk):
    treatment = Treatment.objects.get(pk=pk)
    return render(request, 'patientapp/treatment_detail.html', {'treatment': treatment})

class PatientCreateView(InstitutionFilterMixin, LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Patient
    form_class = PatientForm
    template_name = 'patientapp/patient_form.html'
    success_url = reverse_lazy('patient_list')
    permission_required = 'patientapp.add_patient'

    def get_form(self, form_class=None):
        """Customize the form to limit institution choices for providers."""
        form = super().get_form(form_class)
        
        # If user is a provider, limit institution choices to their institution
        user_institution = get_user_institution(self.request.user)
        if user_institution:
            form.fields['institution'].queryset = Institution.objects.filter(id=user_institution.id)
            form.fields['institution'].initial = user_institution
        
        return form

    def form_valid(self, form):
        try:
            with transaction.atomic():
                # Create the User object first
                user = User.objects.create_user(
                    username=form.cleaned_data['username'],
                    email=form.cleaned_data['email'],
                    password=form.cleaned_data['password1']
                )
                
                # Assign groups to the user
                if 'groups' in form.cleaned_data:
                    user.groups.set(form.cleaned_data['groups'])
                
                # Create the Patient object
                patient = form.save(commit=False)
                patient.user = user
                
                # For providers, ensure the patient is created in their institution
                user_institution = get_user_institution(self.request.user)
                if user_institution:
                    patient.institution = user_institution
                
                patient.save()
                
                messages.success(self.request, _('Patient created successfully.'))
                return redirect(self.success_url)
                
        except Exception as e:
            messages.error(self.request, _('An error occurred while creating the patient.'))
            return self.form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('Add New Patient')
        return context

class PatientRestrictedUpdateView(InstitutionFilterMixin, LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Patient
    form_class = PatientRestrictedUpdateForm
    template_name = 'patientapp/patient_restricted_update_form.html'
    permission_required = 'patientapp.change_patient' # Or a more specific permission

    def get_form(self, form_class=None):
        """Customize the form to limit institution choices for providers."""
        form = super().get_form(form_class)
        
        # If user is a provider, limit institution choices to their institution
        user_institution = get_user_institution(self.request.user)
        if user_institution:
            form.fields['institution'].queryset = Institution.objects.filter(id=user_institution.id)
        
        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('Edit Patient Details')
        return context

    def form_valid(self, form):
        try:
            with transaction.atomic():
                # For providers, ensure the patient stays in their institution
                user_institution = get_user_institution(self.request.user)
                if user_institution:
                    form.instance.institution = user_institution
                
                self.object = form.save()
                messages.success(self.request, _('Patient basic details updated successfully.'))
                return redirect(self.get_success_url())
        except Exception as e:
            logger.error(f"Error updating patient basic details {self.object.id}: {e}", exc_info=True)
            messages.error(self.request, _('An error occurred while updating the patient basic details.'))
            return self.form_invalid(form)

    def get_success_url(self):
        return reverse('patient_detail', kwargs={'pk': self.object.pk})

# Diagnosis Views
class DiagnosisCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Diagnosis
    form_class = DiagnosisForm
    template_name = 'patientapp/diagnosis_form.html'
    permission_required = 'patientapp.add_diagnosis'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Check patient access before showing the form
        patient = get_accessible_patient_or_404(self.request.user, self.kwargs['patient_pk'])
        context['patient'] = patient
        context['title'] = _('Add Diagnosis')
        return context

    def form_valid(self, form):
        # Check patient access before saving
        patient = get_accessible_patient_or_404(self.request.user, self.kwargs['patient_pk'])
        form.instance.patient = patient
        messages.success(self.request, _('Diagnosis added successfully.'))
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('patient_detail', kwargs={'pk': self.kwargs['patient_pk']})

class DiagnosisUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Diagnosis
    form_class = DiagnosisForm
    template_name = 'patientapp/diagnosis_form.html'
    permission_required = 'patientapp.change_diagnosis'

    def get_object(self, queryset=None):
        """Get the diagnosis and check patient access."""
        obj = super().get_object(queryset)
        # Check that the user can access this patient
        check_patient_access(self.request.user, obj.patient)
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('Edit Diagnosis')
        context['patient'] = self.object.patient # Pass patient to context for the cancel button
        return context

    def get_success_url(self):
        return reverse('patient_detail', kwargs={'pk': self.object.patient.pk})

# DiagnosisDeleteView removed as per request to restrict delete to admin only.

class DiagnosisListCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """View for adding new diagnosis types to the DiagnosisList."""
    model = DiagnosisList
    form_class = DiagnosisListForm
    template_name = 'patientapp/diagnosislist_form.html'
    permission_required = 'patientapp.add_diagnosislist'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('Add New Diagnosis Type')
        # Get the return URL from query parameter if provided
        context['return_url'] = self.request.GET.get('return_url', '')
        return context
    
    def form_valid(self, form):
        messages.success(self.request, _('Diagnosis type added successfully.'))
        response = super().form_valid(form)
        
        # If this was opened from a diagnosis form, redirect back with the new diagnosis selected
        return_url = self.request.GET.get('return_url', '')
        if return_url:
            # Add the newly created diagnosis ID as a query parameter
            from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
            parsed = urlparse(return_url)
            query_params = parse_qs(parsed.query)
            query_params['new_diagnosis_id'] = [str(self.object.id)]
            new_query = urlencode(query_params, doseq=True)
            new_url = urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment))
            return redirect(new_url)
        
        return response
    
    def get_success_url(self):
        # Default success URL if no return_url is provided
        return reverse('diagnosislist_create')

# Treatment Views
class TreatmentCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Treatment
    form_class = TreatmentForm
    template_name = 'patientapp/treatment_form.html'
    permission_required = 'patientapp.add_treatment'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Check patient access through diagnosis
        diagnosis = get_object_or_404(Diagnosis, pk=self.kwargs['diagnosis_pk'])
        check_patient_access(self.request.user, diagnosis.patient)
        context['diagnosis'] = diagnosis
        context['treatment_types'] = TreatmentType.objects.all()
        context['treatment_intents'] = TreatmentIntentChoices.choices
        context['title'] = _('Add Treatment')
        return context

    def form_valid(self, form):
        # Check patient access before saving
        diagnosis = get_object_or_404(Diagnosis, pk=self.kwargs['diagnosis_pk'])
        check_patient_access(self.request.user, diagnosis.patient)
        form.instance.diagnosis = diagnosis
        messages.success(self.request, _('Treatment added successfully.'))
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('patient_detail', kwargs={'pk': self.object.diagnosis.patient.pk})

class TreatmentUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Treatment
    form_class = TreatmentForm
    template_name = 'patientapp/treatment_form.html'
    permission_required = 'patientapp.change_treatment'

    def get_object(self, queryset=None):
        """Get the treatment and check patient access."""
        obj = super().get_object(queryset)
        # Check that the user can access this patient through the diagnosis
        check_patient_access(self.request.user, obj.diagnosis.patient)
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['treatment_types'] = TreatmentType.objects.all()
        context['treatment_intents'] = TreatmentIntentChoices.choices
        context['title'] = _('Edit Treatment')
        # Ensure diagnosis is in context for the cancel button URL
        context['diagnosis'] = self.object.diagnosis
        return context

    def get_success_url(self):
        return reverse('patient_detail', kwargs={'pk': self.object.diagnosis.patient.pk})

# TreatmentDeleteView removed as per request to restrict delete to admin only.

# Treatment Type Views
from django.http import HttpResponse

class TreatmentTypeCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = TreatmentType
    fields = ['treatment_type']
    template_name = 'patientapp/treatment_type_form.html' # Full page template
    permission_required = 'patientapp.add_treatmenttype'

    def get_template_names(self):
        if self.request.htmx:
            return ['patientapp/partials/treatment_type_form_modal.html']
        return [self.template_name]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('Add Treatment Type')
        return context

    def form_valid(self, form):
        super().form_valid(form) # Save the object
        if self.request.htmx:
            # Send back an empty response for the modal content, effectively clearing it.
            # And trigger an event to tell the parent page to refresh the dropdown and hide the modal container.
            response = HttpResponse(status=200) # OK
            # This will replace the modal content with nothing.
            response.content = ""
            # This header tells the client to hide the modal container and refresh the treatment type field.
            # We'll need corresponding JS on the client to handle 'closeModalAndRefreshTreatmentTypes'.
            response['HX-Trigger'] = 'closeModalAndRefreshTreatmentTypes'
            return response
        return redirect(self.get_success_url())


    def get_success_url(self):
        # This is for non-HTMX requests or if form_valid doesn't return an HttpResponse
        return reverse('treatment_type_list') # Or redirect back to the treatment form?

class TreatmentTypeUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = TreatmentType
    fields = ['treatment_type']
    template_name = 'patientapp/treatment_type_form.html'
    permission_required = 'patientapp.change_treatmenttype'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('Edit Treatment Type')
        return context

    def get_success_url(self):
        return reverse('treatment_type_list')

# TreatmentTypeDeleteView removed as per request to restrict delete to admin only.

def treatment_type_list(request):
    treatment_types = TreatmentType.objects.all()
    return render(request, 'patientapp/treatment_type_list.html', {
        'treatment_types': treatment_types,
        'title': _('Treatment Types')
    })


def get_patient_count():
    """
    Get the total count of patients in the system.
    Returns an integer count.
    """
    return Patient.objects.count()



