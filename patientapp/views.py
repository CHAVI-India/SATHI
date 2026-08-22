from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.utils.translation import gettext_lazy as _, gettext, get_language
from django.utils import timezone
from django.db import transaction, IntegrityError
from django.db.models import Q, Count, Max
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.http import JsonResponse
from .models import (
    Patient, Diagnosis, DiagnosisList, Treatment, Institution, GenderChoices,
    TreatmentType, TreatmentIntentChoices, Project, PatientProject,
    ProjectRedcapMapping, RedcapFormToQuestionnaireMapping,
    RedcapFieldToItemMapping, RedcapStudyIDtoPatientIDMap,
    RedcapDataExportLog, ExportTypeChoices, ExportStatusChoices,
    RedcapInstanceToSubmissionMapping,
)
from .redcap_utils import (
    fetch_project_metadata,
    fetch_patient_id_records,
    fetch_form_instances,
    fetch_field_values_for_record,
    import_records as redcap_import_records,
)
from .forms import (
    PatientForm, TreatmentForm, DiagnosisForm, PatientRestrictedUpdateForm,
    DiagnosisListForm, ProjectForm, PatientProjectForm,
    ProjectRedcapMappingForm, RedcapIDFieldsForm, RedcapFormToQuestionnaireMappingForm,
    RedcapFieldToItemMappingForm, RedcapStudyIDMapForm, DiagnosisTreatmentBlockForm,
)
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
import csv
from django.http import HttpResponse
from bokeh.resources import Resources  # Serve Bokeh from local static files
from patientapp.utils import get_filtered_patients_for_aggregation
from django.core.cache import cache
import hashlib
import json


logger = logging.getLogger(__name__)
cache_logger = logging.getLogger('cache_performance')

# Configure Bokeh to use local static files
bokeh_resources = Resources(mode='server', root_url='/static/bokeh/')

# Create your views here.


@login_required
@permission_required('patientapp.view_patient', raise_exception=True)
def prom_review(request, pk, print_mode=False):
    """View for the PRO Review page that shows patient questionnaire responses.
    Supports global filtering for all sections of the page.
    
    Args:
        request: HTTP request
        pk: Patient UUID
        print_mode: If True, renders print-optimized template instead of interactive page
    """
    logger.info(f"PRO Review view called for patient ID: {pk}, print_mode={print_mode}")
    
    # Get patient with institution access check
    patient = get_accessible_patient_or_404(request.user, pk)
    logger.info(f"Found patient UUID: {patient.id}")
    
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
                valid_option_values = [option.option_value for option in options_list if option.option_value is not None]
                max_value = max(valid_option_values) if valid_option_values else None
                response.percentage = calculate_percentage(likert_value, max_value)
                
                likert_scale = response.questionnaire_item.item.likert_response
                better_direction = response.questionnaire_item.item.item_better_score_direction or 'Higher is Better'
                
                # Calculate color map directly using bulk-fetched options
                valid_options_list = [option for option in options_list if option.option_value is not None]
                if valid_options_list:
                    sorted_options = sorted(valid_options_list, key=lambda x: x.option_value)
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
                for option in valid_options_list:
                    if response.response_value and float(option.option_value) == float(response.response_value):
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

        # LAZY LOADING: Skip plot generation in main view - plots will be loaded via HTMX
        # Plots are now generated on-demand by prom_review_item_plot endpoint
        response.bokeh_plot = None  # Set to None, will be lazy-loaded
    
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
    historical_composite_scores_map = {}
    
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
        
        # Find previous score and historical scores for each current score
        for current_score in composite_construct_scores_list:
            construct_id = current_score.composite_construct_scale.id
            composite_scores_list_for_construct = composite_scores_by_construct.get(construct_id, [])
            
            # Find the score that comes before the current one
            for score in composite_scores_list_for_construct:
                if score.questionnaire_submission.submission_date < current_score.questionnaire_submission.submission_date:
                    previous_composite_scores_map[current_score.id] = score
                    break
            
            # Store historical scores for plotting (apply filters)
            historical_scores_for_composite = composite_scores_list_for_construct.copy()
            
            # Apply max time interval filter if specified
            if max_time_interval_value is not None and patient_start_date:
                filtered_historical = []
                for hist_score in historical_scores_for_composite:
                    interval_value = calculate_time_interval_value(
                        hist_score.questionnaire_submission.submission_date,
                        patient_start_date,
                        time_interval
                    )
                    if interval_value <= max_time_interval_value:
                        filtered_historical.append(hist_score)
                historical_scores_for_composite = filtered_historical
            
            # Take only the submission_count most recent
            historical_scores_for_composite = historical_scores_for_composite[:submission_count]
            
            # Filter out scores with negative time intervals
            if patient_start_date:
                from patientapp.utils import filter_positive_intervals_composite
                historical_scores_for_composite = filter_positive_intervals_composite(
                    historical_scores_for_composite, patient_start_date, time_interval
                )
            
            historical_composite_scores_map[current_score.id] = historical_scores_for_composite

    # Create CompositeConstructScoreData objects with plots
    composite_construct_scores_with_plots = []
    logger.info("Processing composite construct scores to create plot data...")
    
    for composite_score in composite_construct_scores_list:
        # Get previous composite score for change calculation using bulk-fetched data
        previous_composite_obj = previous_composite_scores_map.get(composite_score.id)
        previous_score = previous_composite_obj.score if previous_composite_obj else None
        
        # Get historical scores for plotting
        historical_scores_for_plot = historical_composite_scores_map.get(composite_score.id, [])
        
        logger.debug(f"Found {len(historical_scores_for_plot)} historical scores for {composite_score.composite_construct_scale.composite_construct_scale_name} plot")
        
        # Create CompositeConstructScoreData object
        # LAZY LOADING: Skip plot generation in main view
        from patientapp.utils import CompositeConstructScoreData
        composite_score_data = CompositeConstructScoreData(
            composite_construct_scale=composite_score.composite_construct_scale,
            current_score=composite_score.score,
            previous_score=previous_score,
            historical_scores=historical_scores_for_plot,
            patient=patient,
            start_date_reference=start_date_reference,
            time_interval=time_interval,
            selected_indicators=selected_indicators,
            generate_plot=False  # Skip plot generation - will be lazy-loaded via HTMX
        )
        
        composite_construct_scores_with_plots.append(composite_score_data)

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

        # LAZY LOADING: Skip aggregation calculation in main view
        # Aggregation statistics will be calculated on-demand in prom_review_construct_plot endpoint
        # This dramatically improves initial page load time (removes ~250ms × N constructs)

        # Create construct score data object
        # LAZY LOADING: Skip plot generation in main view
        score_data = ConstructScoreData(
            construct=construct, # construct_score.construct
            current_score=construct_score.score, # This is from the main construct_scores list, respecting filters for card display
            previous_score=construct_score.previous_score, # Use the actual previous score for change calculations
            historical_scores=historical_scores_for_plot, # Filtered and sliced list for the plot
            patient=patient,
            start_date_reference=start_date_reference,
            time_interval=time_interval,
            aggregated_statistics=None,  # Lazy-loaded in prom_review_construct_plot
            aggregation_metadata=None,  # Lazy-loaded in prom_review_construct_plot
            aggregation_type=aggregation_type,  # Pass aggregation type for tooltips
            selected_indicators=selected_indicators,  # Pass selected indicators for plot display
            generate_plot=False  # Skip plot generation - will be lazy-loaded via HTMX
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
    
    # Get Bokeh resources (served from local static files)
    bokeh_css = bokeh_resources.render_css()
    bokeh_js = bokeh_resources.render_js()
    
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

    # LAZY LOADING: Simplified aggregation metadata for initial page load
    # Detailed aggregation statistics are now calculated on-demand in prom_review_construct_plot
    # This section only provides basic patient pool information for the aggregation card header
    aggregation_metadata = None
    if aggregated_patients:
        total_eligible_patients = aggregated_patients.count()
        aggregation_metadata = {
            'total_eligible_patients': total_eligible_patients,
            'contributing_patients': None,  # Will be calculated when plots load
            'total_responses': None,  # Will be calculated when plots load
            'time_intervals_count': None,  # Will be calculated when plots load
            'time_range': 'N/A',  # Will be calculated when plots load
            'time_interval_unit': get_interval_label(time_interval).lower(),
            'patient_details': {'contributing': [], 'non_contributing': []},  # Will be populated when plots load
            'lazy_loaded': True,  # Flag to indicate detailed stats are lazy-loaded
        }
        logger.info(f"Aggregation metadata (lazy-load mode): {total_eligible_patients} eligible patients in pool")

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
        'composite_construct_scores': composite_construct_scores_with_plots,  # CompositeConstructScoreData objects with plots
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
    
    # If in print mode, render the print-optimized template
    if print_mode:
        return render(request, 'promapp/prom_review_print.html', context)
    
    return render(request, 'promapp/prom_review.html', context)


@login_required
@permission_required('patientapp.view_patient', raise_exception=True)
def prom_review_print(request, pk):
    """
    Print-friendly view for PRO Review report with simplified summaries.
    Reuses the same data gathering logic as prom_review but renders a 
    print-optimized template with natural language summaries.
    """
    # Reuse the main prom_review logic by calling it and capturing context
    # We'll use the same filtering and data gathering
    logger.info(f"PRO Review Print view called for patient ID: {pk}")
    
    # Get patient with institution access check
    patient = get_accessible_patient_or_404(request.user, pk)
    
    # Get filter parameters (same as prom_review)
    questionnaire_filter = request.GET.get('questionnaire_filter')
    max_time_interval = request.GET.get('max_time_interval')
    time_range = request.GET.get('time_range', '5')
    item_filter = request.GET.getlist('item_filter')
    start_date_reference = request.GET.get('start_date_reference', 'date_of_registration')
    time_interval = request.GET.get('time_interval', 'weeks')
    aggregation_type = request.GET.get('aggregation_type', 'median_iqr')
    patient_filter_gender = request.GET.get('patient_filter_gender')
    patient_filter_diagnosis = request.GET.get('patient_filter_diagnosis')
    patient_filter_treatment = request.GET.get('patient_filter_treatment')
    patient_filter_min_age = request.GET.get('patient_filter_min_age')
    patient_filter_max_age = request.GET.get('patient_filter_max_age')
    
    # Build the filter parameters to pass to prom_review logic
    # We'll reuse the prom_review view's logic by making an internal request
    # or we can redirect with a special parameter
    
    # For simplicity and to avoid code duplication, we'll use the same 
    # context gathering approach - essentially duplicating the logic but 
    # rendering a different template
    
    # Redirect to prom_review with print parameter, which will handle data gathering
    # and render the print template
    return prom_review(request, pk, print_mode=True)


@login_required
@permission_required('patientapp.view_patient', raise_exception=True)
def prom_review_construct_plot(request, pk, construct_id):
    """HTMX endpoint for lazy-loading a single construct plot with current filters."""
    logger.info(f"Lazy-loading construct plot for patient {pk}, construct {construct_id}")
    
    # Get patient with institution access check
    patient = get_accessible_patient_or_404(request.user, pk)
    
    # Get ALL filter parameters (same as main view)
    questionnaire_filter = request.GET.get('questionnaire_filter')
    max_time_interval = request.GET.get('max_time_interval')
    time_range = request.GET.get('time_range', '5')
    start_date_reference = request.GET.get('start_date_reference', 'date_of_registration')
    time_interval = request.GET.get('time_interval', 'weeks')
    aggregation_type = request.GET.get('aggregation_type', 'median_iqr')
    patient_filter_gender = request.GET.get('patient_filter_gender')
    patient_filter_diagnosis = request.GET.get('patient_filter_diagnosis')
    patient_filter_treatment = request.GET.get('patient_filter_treatment')
    patient_filter_min_age = request.GET.get('patient_filter_min_age')
    patient_filter_max_age = request.GET.get('patient_filter_max_age')
    
    # Get selected indicators for plot display
    selected_indicators_param = request.GET.get('selected_indicators')
    selected_indicators = []
    if selected_indicators_param:
        try:
            selected_indicators = json.loads(selected_indicators_param)
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning(f"Failed to parse selected_indicators parameter: {e}")
            selected_indicators = []
    
    # Convert filters to proper types
    max_time_interval_value = None
    if max_time_interval:
        try:
            max_time_interval_value = float(max_time_interval)
        except (ValueError, TypeError):
            logger.warning(f"Invalid max_time_interval value: {max_time_interval}")
    
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
    from promapp.models import ConstructScale
    construct = get_object_or_404(ConstructScale, id=construct_id)
    
    # Get patient start date
    patient_start_date = get_patient_start_date(patient, start_date_reference)
    
    # Get submission count
    from promapp.models import QuestionnaireSubmission
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
    
    # Get construct scores for this construct with caching
    from promapp.models import QuestionnaireConstructScore
    
    # Generate cache key for historical scores - include ALL params that affect the query result
    scores_cache_key = (
        f"scores_{str(pk)}_{str(construct_id)}"
        f"_{questionnaire_filter or 'all'}"
        f"_{time_range}"
        f"_{str(max_time_interval_value) if max_time_interval_value else 'none'}"
        f"_{start_date_reference}"
        f"_{time_interval}"
    )
    
    # Try to get from cache
    historical_scores = cache.get(scores_cache_key)
    if historical_scores:
        cache_logger.info(f"Cache HIT for construct scores: {scores_cache_key}")
    else:
        cache_logger.info(f"Cache MISS for construct scores: {scores_cache_key}")
        
        construct_scores = QuestionnaireConstructScore.objects.filter(
            construct=construct,
            questionnaire_submission__patient=patient
        ).select_related(
            'questionnaire_submission',
            'construct'
        ).order_by('-questionnaire_submission__submission_date')
        
        # Apply questionnaire filter if specified
        if questionnaire_filter:
            construct_scores = construct_scores.filter(
                questionnaire_submission__patient_questionnaire__questionnaire_id=questionnaire_filter
            )
        
        # Apply max time interval filter if specified
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
        
        # Take only submission_count most recent
        historical_scores = list(construct_scores[:submission_count])
        
        # Filter out scores with negative time intervals
        if patient_start_date:
            historical_scores = filter_positive_intervals_construct(
                historical_scores, patient_start_date, time_interval
            )
        
        # Cache the result for 5 minutes (300 seconds)
        cache.set(scores_cache_key, historical_scores, 300)
        cache_logger.info(f"Cached construct scores: {scores_cache_key} (TTL: 5 min)")
    
    # Get aggregated patients
    aggregated_patients = get_filtered_patients_for_aggregation(
        exclude_patient=patient,
        patient_filter_gender=patient_filter_gender,
        patient_filter_diagnosis=patient_filter_diagnosis,
        patient_filter_treatment=patient_filter_treatment,
        patient_filter_min_age=min_age_value,
        patient_filter_max_age=max_age_value
    )
    
    import time as time_module
    t_agg_start = time_module.perf_counter()
    
    # Calculate aggregated statistics (no caching - aggregation intervals are patient-specific)
    aggregated_statistics = None
    aggregation_metadata = None
    if aggregated_patients and historical_scores:
        try:
            from patientapp.utils import (
                aggregate_construct_scores_by_time_interval,
                calculate_aggregation_statistics
            )
            
            # Get reference time intervals from this patient's scores (patient-specific)
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
            
            # Call aggregation directly - it handles the case where no patients
            # have valid start dates by returning empty aggregated_data.
            # The old pre-check loop was removed because:
            # 1. It ran N slow queries using get_patient_start_date_for_aggregation()
            # 2. The aggregation function does the same check with 0 queries
            #    using _get_patient_start_date_bulk() on prefetched data
            # 3. The pre-check couldn't tell if patients had scores for THIS
            #    construct anyway - only if they had valid start dates
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
    
    # Create construct score data object
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
    
    context = {
        'score_data': score_data,
    }
    
    response = render(request, 'promapp/partials/construct_plot.html', context)
    response['X-Timing-Aggregation'] = str(t_agg_ms)
    response['X-Timing-Plot'] = str(t_plot_ms)
    
    # Include aggregation metadata in headers for population stats update
    if aggregation_metadata:
        response['X-Aggregation-Contributing'] = str(aggregation_metadata.get('contributing_patients', 0))
        response['X-Aggregation-Responses'] = str(aggregation_metadata.get('total_responses', 0))
        response['X-Aggregation-TimeRange'] = str(aggregation_metadata.get('time_range', 'N/A'))
        response['X-Aggregation-TimeUnit'] = str(aggregation_metadata.get('time_interval_unit', 'weeks'))
    
    return response


@login_required
@permission_required('patientapp.view_patient', raise_exception=True)
def prom_review_composite_plot(request, pk, composite_id):
    """HTMX endpoint for lazy-loading a single composite construct plot with current filters."""
    logger.info(f"Lazy-loading composite plot for patient {pk}, composite {composite_id}")
    
    # Get patient with institution access check
    patient = get_accessible_patient_or_404(request.user, pk)
    
    # Get filter parameters
    max_time_interval = request.GET.get('max_time_interval')
    time_range = request.GET.get('time_range', '5')
    start_date_reference = request.GET.get('start_date_reference', 'date_of_registration')
    time_interval = request.GET.get('time_interval', 'weeks')
    
    # Get selected indicators for plot display
    selected_indicators_param = request.GET.get('selected_indicators')
    selected_indicators = []
    if selected_indicators_param:
        try:
            selected_indicators = json.loads(selected_indicators_param)
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning(f"Failed to parse selected_indicators parameter: {e}")
            selected_indicators = []
    
    # Convert filters
    max_time_interval_value = None
    if max_time_interval:
        try:
            max_time_interval_value = float(max_time_interval)
        except (ValueError, TypeError):
            pass
    
    # Get composite construct scale
    from promapp.models import CompositeConstructScaleScoring
    composite_scale = get_object_or_404(CompositeConstructScaleScoring, id=composite_id)
    
    # Get patient start date
    patient_start_date = get_patient_start_date(patient, start_date_reference)
    
    # Get submission count
    from promapp.models import QuestionnaireSubmission
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
    
    # Get composite construct scores with caching
    from promapp.models import QuestionnaireConstructScoreComposite
    
    # Generate cache key for composite scores - include ALL params that affect the query result
    comp_cache_key = (
        f"comp_scores_{str(pk)}_{str(composite_id)}"
        f"_{time_range}"
        f"_{str(max_time_interval_value) if max_time_interval_value else 'none'}"
        f"_{start_date_reference}"
        f"_{time_interval}"
    )
    
    # Try to get from cache
    historical_scores = cache.get(comp_cache_key)
    if historical_scores:
        cache_logger.info(f"Cache HIT for composite scores: {comp_cache_key}")
    else:
        cache_logger.info(f"Cache MISS for composite scores: {comp_cache_key}")
        
        composite_scores = QuestionnaireConstructScoreComposite.objects.filter(
            composite_construct_scale=composite_scale,
            questionnaire_submission__patient=patient
        ).select_related(
            'questionnaire_submission',
            'composite_construct_scale'
        ).order_by('-questionnaire_submission__submission_date')
        
        # Apply max time interval filter if specified
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
        
        # Take only submission_count most recent
        historical_scores = list(composite_scores[:submission_count])
        
        # Filter out scores with negative time intervals
        if patient_start_date:
            from patientapp.utils import filter_positive_intervals_composite
            historical_scores = filter_positive_intervals_composite(
                historical_scores, patient_start_date, time_interval
            )
        
        # Cache the result for 5 minutes (300 seconds)
        cache.set(comp_cache_key, historical_scores, 300)
        cache_logger.info(f"Cached composite scores: {comp_cache_key} (TTL: 5 min)")
    
    # Get current and previous scores
    current_score = historical_scores[0].score if historical_scores else None
    previous_score = historical_scores[1].score if len(historical_scores) > 1 else None
    
    # Create composite score data object
    from patientapp.utils import CompositeConstructScoreData
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
    
    context = {
        'score_data': score_data,
    }
    
    return render(request, 'promapp/partials/construct_plot.html', context)


@login_required
@permission_required('patientapp.view_patient', raise_exception=True)
def prom_review_item_plot(request, pk, item_id):
    """HTMX endpoint for lazy-loading a single item plot with current filters."""
    logger.info(f"Lazy-loading item plot for patient {pk}, item {item_id}")
    
    # Get patient with institution access check
    patient = get_accessible_patient_or_404(request.user, pk)
    
    # Get filter parameters
    questionnaire_filter = request.GET.get('questionnaire_filter')
    max_time_interval = request.GET.get('max_time_interval')
    time_range = request.GET.get('time_range', '5')
    start_date_reference = request.GET.get('start_date_reference', 'date_of_registration')
    time_interval = request.GET.get('time_interval', 'weeks')
    
    # Get selected indicators for plot display
    selected_indicators_param = request.GET.get('selected_indicators')
    selected_indicators = []
    if selected_indicators_param:
        try:
            selected_indicators = json.loads(selected_indicators_param)
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning(f"Failed to parse selected_indicators parameter: {e}")
            selected_indicators = []
    
    # Convert filters
    max_time_interval_value = None
    if max_time_interval:
        try:
            max_time_interval_value = float(max_time_interval)
        except (ValueError, TypeError):
            pass
    
    # Get item
    from promapp.models import Item
    item = get_object_or_404(Item, id=item_id)
    
    # Get patient start date
    patient_start_date = get_patient_start_date(patient, start_date_reference)
    
    # Get submission count
    from promapp.models import QuestionnaireSubmission
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
    
    # Get item responses for this item with caching
    from promapp.models import QuestionnaireItemResponse
    
    # Generate cache key for item responses - include ALL params that affect the query result
    item_cache_key = (
        f"item_resp_{str(pk)}_{str(item_id)}"
        f"_{questionnaire_filter or 'all'}"
        f"_{time_range}"
        f"_{str(max_time_interval_value) if max_time_interval_value else 'none'}"
        f"_{start_date_reference}"
        f"_{time_interval}"
    )
    
    # Try to get from cache
    historical_responses = cache.get(item_cache_key)
    if historical_responses:
        cache_logger.info(f"Cache HIT for item responses: {item_cache_key}")
    else:
        cache_logger.info(f"Cache MISS for item responses: {item_cache_key}")
        
        item_responses = QuestionnaireItemResponse.objects.filter(
            questionnaire_item__item=item,
            questionnaire_submission__patient=patient
        ).select_related(
            'questionnaire_submission',
            'questionnaire_item'
        ).order_by('-questionnaire_submission__submission_date')
        
        # Apply max time interval filter if specified
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
        
        # Take only submission_count most recent
        historical_responses = list(item_responses[:submission_count])
        
        # Filter out responses with negative time intervals
        if patient_start_date:
            historical_responses = filter_positive_intervals(
                historical_responses, patient_start_date, time_interval
            )
        
        # Cache the result for 5 minutes (300 seconds)
        cache.set(item_cache_key, historical_responses, 300)
        cache_logger.info(f"Cached item responses: {item_cache_key} (TTL: 5 min)")
    
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
    
    context = {
        'bokeh_plot': bokeh_plot,
        'item': item,
    }
    
    return render(request, 'promapp/partials/item_plot.html', context)


@login_required
@permission_required('patientapp.view_patient', raise_exception=True)
def dispatch_plot_tasks(request, pk):
    """
    API endpoint to dispatch Celery tasks for parallel plot generation.
    
    Accepts POST with JSON body:
    {
        "plots": [
            {"type": "construct", "id": "uuid-string"},
            {"type": "composite", "id": "uuid-string"},
            {"type": "item", "id": "uuid-string"}
        ],
        "filters": {
            "questionnaire_filter": "...",
            "time_range": "5",
            ...
        }
    }
    
    Returns JSON:
    {
        "task_id": "celery-task-id",
        "status": "dispatched"
    }
    """
    import json
    from django.views.decorators.http import require_POST
    from patientapp.tasks import generate_plots_batch_task
    
    # Verify patient access
    patient = get_accessible_patient_or_404(request.user, pk)
    
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    
    plots = data.get('plots', [])
    filters = data.get('filters', {})
    
    if not plots:
        return JsonResponse({'error': 'No plots specified'}, status=400)
    
    # Dispatch the Celery task
    task = generate_plots_batch_task.delay(
        patient_id=str(pk),
        plots=plots,
        filters=filters,
        user_id=request.user.id
    )
    
    logger.info(f"Dispatched plot generation task {task.id} for patient {pk}, {len(plots)} plots")
    
    return JsonResponse({
        'task_id': task.id,
        'status': 'dispatched',
        'plot_count': len(plots)
    })


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
                    valid_option_values = [option.option_value for option in options_list if option.option_value is not None]
                    max_value = max(valid_option_values) if valid_option_values else None
                    response.percentage = calculate_percentage(likert_value, max_value)
                    
                    likert_scale = response.questionnaire_item.item.likert_response
                    better_direction = response.questionnaire_item.item.item_better_score_direction or 'Higher is Better'
                    
                    # === OPTIMIZATION: Calculate colors in Python using bulk-fetched options ===
                    # Avoid additional database query by calculating colors directly
                    valid_options_list = [option for option in options_list if option.option_value is not None]
                    n_options = len(valid_options_list)
                    if n_options > 0:
                        # Sort options for consistent color mapping
                        sorted_options = sorted(valid_options_list, key=lambda x: x.option_value)
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
                    for option in valid_options_list:
                        if response.response_value and float(option.option_value) == float(response.response_value):
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

    # Get Bokeh resources (served from local static files)
    bokeh_css = bokeh_resources.render_css()
    bokeh_js = bokeh_resources.render_js()
    
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
    project_id = request.GET.get('project', '')
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
    
    # Apply project filter
    if project_id:
        patients = patients.filter(patientproject__project_id=project_id).distinct()
    
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
    
    # Get projects for the filter dropdown (only projects with patient assignments)
    projects = Project.objects.filter(
        patientproject__patient__in=patients
    ).distinct().order_by('project_name')
    
    # Pagination
    page = request.GET.get('page', 1)
    paginator = Paginator(patients, 25)  # Show 25 patients per page to match questionnaire list
    
    try:
        patients = paginator.page(page)
    except PageNotAnInteger:
        patients = paginator.page(1)
    except EmptyPage:
        patients = paginator.page(paginator.num_pages)
    
    # Add questionnaire and project data to each patient
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
        
        # Get questionnaires with their response counts
        questionnaires_with_counts = []
        for q_id in questionnaire_ids:
            questionnaire = Questionnaire.objects.filter(
                id=q_id,
                translations__language_code=current_language
            ).first()
            
            if questionnaire:
                # Count submissions for this patient and questionnaire
                submission_count = QuestionnaireSubmission.objects.filter(
                    patient=patient,
                    patient_questionnaire__questionnaire=questionnaire
                ).count()
                
                questionnaires_with_counts.append({
                    'name': questionnaire.translations.filter(
                        language_code=current_language
                    ).first().name,
                    'response_count': submission_count
                })
        
        patient.questionnaires_with_counts = questionnaires_with_counts
        
        # Get patient's projects
        patient.projects = list(
            PatientProject.objects.filter(patient=patient)
            .select_related('project')
            .order_by('project__project_name')
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
        'projects': projects,
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
    patient_projects = patient.patientproject_set.all().order_by('-created_date')
    context = {
        'patient': patient,
        'diagnoses': diagnoses,
        'patient_projects': patient_projects,
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

    def _parse_diagnosis_blocks(self, post_data):
        """Parse POST data to extract multiple diagnosis-treatment blocks.

        Django form prefixes use hyphens, so field names are like:
        'diag_block_0-diagnosis', 'diag_block_0-date_of_diagnosis', etc.
        """
        blocks = []
        # Find all unique block prefixes from the POST data
        # Django uses hyphens for prefixed forms: diag_block_0-diagnosis
        block_keys = [k for k in post_data.keys() if k.startswith('diag_block_') and k.endswith('-diagnosis')]

        logger.debug(f"Found diagnosis block keys: {block_keys}")
        logger.debug(f"All POST keys: {list(post_data.keys())}")

        for key in block_keys:
            # Extract the block index (e.g., 'diag_block_0-diagnosis' -> '0')
            prefix = key.replace('-diagnosis', '')  # e.g., 'diag_block_0'
            block_idx = prefix.replace('diag_block_', '')

            # Django form prefixes use hyphens
            diagnosis_id = post_data.get(f'{prefix}-diagnosis')
            logger.debug(f"Block {block_idx}: diagnosis_id = {diagnosis_id}")

            if diagnosis_id:  # Only process if a diagnosis is selected
                block = {
                    'block_idx': block_idx,
                    'diagnosis': diagnosis_id,
                    'date_of_diagnosis': post_data.get(f'{prefix}-date_of_diagnosis'),
                    'treatment_type': post_data.getlist(f'{prefix}-treatment_type'),
                    'treatment_intent': post_data.get(f'{prefix}-treatment_intent'),
                    'date_of_start_of_treatment': post_data.get(f'{prefix}-date_of_start_of_treatment'),
                    'currently_ongoing_treatment': f'{prefix}-currently_ongoing_treatment' in post_data,
                    'date_of_end_of_treatment': post_data.get(f'{prefix}-date_of_end_of_treatment'),
                }
                logger.debug(f"Block {block_idx} data: {block}")
                blocks.append(block)

        logger.debug(f"Total blocks parsed: {len(blocks)}")
        return blocks

    def _create_diagnosis_and_treatment(self, patient, block_data, can_add_treatment=True):
        """Create a Diagnosis and optional Treatment for a patient.

        Args:
            patient: The patient to associate with
            block_data: Dictionary containing diagnosis and treatment data
            can_add_treatment: Whether the user has add_treatment permission
        """
        from datetime import datetime

        # Parse date
        date_of_diagnosis = None
        if block_data['date_of_diagnosis']:
            try:
                date_of_diagnosis = datetime.strptime(block_data['date_of_diagnosis'], '%Y-%m-%d').date()
            except ValueError:
                pass

        # Create Diagnosis
        diagnosis = Diagnosis.objects.create(
            patient=patient,
            diagnosis_id=block_data['diagnosis'],
            date_of_diagnosis=date_of_diagnosis
        )

        # Only create treatment if user has add_treatment permission
        if can_add_treatment:
            # Check if treatment data is provided
            has_treatment_data = (
                block_data['treatment_type'] or
                block_data['treatment_intent'] or
                block_data['date_of_start_of_treatment']
            )

            if has_treatment_data:
                # Parse dates
                start_date = None
                end_date = None
                if block_data['date_of_start_of_treatment']:
                    try:
                        start_date = datetime.strptime(block_data['date_of_start_of_treatment'], '%Y-%m-%d').date()
                    except ValueError:
                        pass
                if block_data['date_of_end_of_treatment']:
                    try:
                        end_date = datetime.strptime(block_data['date_of_end_of_treatment'], '%Y-%m-%d').date()
                    except ValueError:
                        pass

                treatment = Treatment.objects.create(
                    diagnosis=diagnosis,
                    treatment_intent=block_data['treatment_intent'] or '',
                    date_of_start_of_treatment=start_date,
                    currently_ongoing_treatment=block_data['currently_ongoing_treatment'],
                    date_of_end_of_treatment=end_date
                )
                # Set ManyToMany treatment types
                if block_data['treatment_type']:
                    treatment.treatment_type.set(block_data['treatment_type'])
        else:
            logger.debug(f"User lacks add_treatment permission - skipping treatment creation for diagnosis {diagnosis}")

        return diagnosis

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

                # Only create diagnosis records if user has add_diagnosis permission
                if self.request.user.has_perm('patientapp.add_diagnosis'):
                    # Parse and create all diagnosis-treatment blocks
                    diagnosis_blocks = self._parse_diagnosis_blocks(self.request.POST)
                    for block_data in diagnosis_blocks:
                        # Pass treatment permission to control treatment creation
                        self._create_diagnosis_and_treatment(
                            patient,
                            block_data,
                            can_add_treatment=self.request.user.has_perm('patientapp.add_treatment')
                        )
                else:
                    logger.debug(f"User {self.request.user} lacks add_diagnosis permission - skipping diagnosis creation")

                # Only create PatientProject if user has add_patientproject permission
                if self.request.user.has_perm('patientapp.add_patientproject'):
                    project = form.cleaned_data.get('project')
                    if project:
                        PatientProject.objects.create(
                            patient=patient,
                            project=project,
                            date_patient_enrolled_in_project=form.cleaned_data.get('date_patient_enrolled_in_project'),
                            date_patient_exited_from_project=form.cleaned_data.get('date_patient_exited_from_project')
                        )
                else:
                    logger.debug(f"User {self.request.user} lacks add_patientproject permission - skipping project assignment")

                messages.success(self.request, _('Patient created successfully.'))
                return redirect(self.success_url)

        except Exception as e:
            logger.error(f"Error creating patient: {e}", exc_info=True)
            messages.error(self.request, _('An error occurred while creating the patient.'))
            return self.form_invalid(form)

    def form_invalid(self, form):
        """Handle form invalid - preserve submitted diagnosis blocks."""
        # Parse the submitted diagnosis blocks to repopulate the form
        response = super().form_invalid(form)
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('Add New Patient')

        # Permission flags for conditional form section display
        context['can_add_diagnosis'] = self.request.user.has_perm('patientapp.add_diagnosis')
        context['can_add_treatment'] = self.request.user.has_perm('patientapp.add_treatment')
        context['can_add_project'] = self.request.user.has_perm('patientapp.add_patientproject')

        # Check if we're repopulating after a form error
        if self.request.method == 'POST' and context['can_add_diagnosis']:
            # Parse submitted diagnosis blocks and create forms with submitted data
            diagnosis_blocks = self._parse_diagnosis_blocks(self.request.POST)
            block_forms = []
            for i, block_data in enumerate(diagnosis_blocks):
                prefix = f'diag_block_{i}'
                # Create form with submitted data
                block_form = DiagnosisTreatmentBlockForm(
                    prefix=prefix,
                    data=self.request.POST
                )
                block_forms.append({
                    'form': block_form,
                    'block_idx': str(i),
                    'prefix': prefix,
                })

            # If no blocks were submitted (or first one empty), at least show one empty block
            if not block_forms:
                block_forms = [{
                    'form': DiagnosisTreatmentBlockForm(prefix='diag_block_0'),
                    'block_idx': '0',
                    'prefix': 'diag_block_0',
                }]

            context['diagnosis_blocks'] = block_forms
            context['diagnosis_block_count'] = len(block_forms)
        elif context['can_add_diagnosis']:
            # Fresh form - show one empty block (only if user has permission)
            context['diagnosis_blocks'] = [{
                'form': DiagnosisTreatmentBlockForm(prefix='diag_block_0'),
                'block_idx': '0',
                'prefix': 'diag_block_0',
            }]
            context['diagnosis_block_count'] = 1
        else:
            # No diagnosis permission - hide diagnosis section
            context['diagnosis_blocks'] = []
            context['diagnosis_block_count'] = 0

        # Keep the original for backwards compatibility
        if context['diagnosis_blocks']:
            context['diagnosis_block_form'] = context['diagnosis_blocks'][0]['form']

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


@login_required
@permission_required('patientapp.add_diagnosis', raise_exception=True)
def diagnosis_block_partial(request):
    """
    HTMX endpoint to return a new diagnosis-treatment block for the patient form.
    Requires add_diagnosis permission to add diagnosis blocks.
    Expects a 'block_idx' parameter to set the prefix for the form fields.
    """
    block_idx = request.GET.get('block_idx', '0')
    prefix = f'diag_block_{block_idx}'

    form = DiagnosisTreatmentBlockForm(prefix=prefix)

    return render(request, 'patientapp/partials/diagnosis_block.html', {
        'form': form,
        'block_idx': block_idx,
        'prefix': prefix,
        'can_add_treatment': request.user.has_perm('patientapp.add_treatment'),
    })


def get_patient_count():
    """
    Get the total count of patients in the system.
    Returns an integer count.
    """
    return Patient.objects.count()


# Project Management Views

@login_required
@permission_required('patientapp.add_patientproject', raise_exception=True)
def patient_project_create(request, patient_pk):
    """
    Create a new patient-project assignment.
    """
    patient = get_accessible_patient_or_404(request.user, patient_pk)
    
    if request.method == 'POST':
        form = PatientProjectForm(request.POST, patient=patient)
        if form.is_valid():
            patient_project = form.save(commit=False)
            patient_project.patient = patient
            try:
                patient_project.save()
                messages.success(request, _('Patient successfully assigned to project.'))
                return redirect('patient_detail', pk=patient_pk)
            except IntegrityError:
                form.add_error('project', _('This patient is already assigned to this project.'))
    else:
        form = PatientProjectForm(patient=patient)
    
    return render(request, 'patientapp/patient_project_form.html', {
        'form': form,
        'patient': patient,
        'title': _('Assign Patient to Project'),
        'action': 'create'
    })


@login_required
@permission_required('patientapp.change_patientproject', raise_exception=True)
def patient_project_update(request, pk):
    """
    Update an existing patient-project assignment.
    """
    patient_project = get_object_or_404(PatientProject, pk=pk)
    
    # Check access to the patient
    patient = get_accessible_patient_or_404(request.user, patient_project.patient.id)
    
    if request.method == 'POST':
        form = PatientProjectForm(request.POST, instance=patient_project, patient=patient)
        if form.is_valid():
            form.save()
            messages.success(request, _('Patient project assignment updated successfully.'))
            return redirect('patient_detail', pk=patient_project.patient.id)
    else:
        form = PatientProjectForm(instance=patient_project, patient=patient)
    
    return render(request, 'patientapp/patient_project_form.html', {
        'form': form,
        'patient': patient,
        'patient_project': patient_project,
        'title': _('Update Patient Project Assignment'),
        'action': 'update'
    })


@login_required
@permission_required('patientapp.delete_patientproject', raise_exception=True)
def patient_project_delete(request, pk):
    """
    Delete a patient-project assignment.
    """
    patient_project = get_object_or_404(PatientProject, pk=pk)
    
    # Check access to the patient
    patient = get_accessible_patient_or_404(request.user, patient_project.patient.id)
    patient_id = patient_project.patient.id
    
    if request.method == 'POST':
        project_name = patient_project.project.project_name
        patient_project.delete()
        messages.success(request, _('Patient removed from project: %(project)s.') % {'project': project_name})
        return redirect('patient_detail', pk=patient_id)
    
    return render(request, 'patientapp/patient_project_confirm_delete.html', {
        'patient_project': patient_project,
        'patient': patient,
        'title': _('Remove Patient from Project')
    })


@login_required
def project_list(request):
    """List all projects (staff only)."""
    guard = _staff_required(request)
    if guard:
        return guard
    projects = Project.objects.all().order_by('project_name')
    return render(request, 'patientapp/project_list.html', {
        'projects': projects,
    })


@login_required
def project_create(request):
    """
    Create a new project (staff only).
    """
    if not request.user.is_staff:
        messages.error(request, _('You do not have permission to create projects.'))
        return redirect('index')
    
    if request.method == 'POST':
        form = ProjectForm(request.POST)
        if form.is_valid():
            project = form.save()
            messages.success(request, _('Project created successfully.'))
            return redirect('patient_detail', pk=request.GET.get('patient_pk', ''))
    else:
        form = ProjectForm()
    
    return render(request, 'patientapp/project_form.html', {
        'form': form,
        'title': _('Create New Project'),
        'action': 'create',
        'patient_pk': request.GET.get('patient_pk', '')
    })


@login_required
def project_update(request, pk):
    """
    Update an existing project (staff only).
    """
    if not request.user.is_staff:
        messages.error(request, _('You do not have permission to edit projects.'))
        return redirect('index')
    
    project = get_object_or_404(Project, pk=pk)
    
    if request.method == 'POST':
        form = ProjectForm(request.POST, instance=project)
        if form.is_valid():
            form.save()
            messages.success(request, _('Project updated successfully.'))
            return_url = request.GET.get('return_url', '')
            if return_url:
                return redirect(return_url)
            return redirect('patient_detail', pk=request.GET.get('patient_pk', ''))
    else:
        form = ProjectForm(instance=project)
    
    return render(request, 'patientapp/project_form.html', {
        'form': form,
        'project': project,
        'title': _('Update Project'),
        'action': 'update',
        'patient_pk': request.GET.get('patient_pk', ''),
        'return_url': request.GET.get('return_url', '')
    })


# ---------------------------------------------------------------------------
# REDCap Integration Views
# ---------------------------------------------------------------------------

def _staff_required(request):
    """Return redirect response if user is not staff, else None."""
    if not request.user.is_staff:
        messages.error(request, _('You do not have permission to access REDCap configuration.'))
        return redirect('index')
    return None


def _redcap_permission_required(request, permission_codename):
    """Return redirect response if user lacks permission, else None.
    
    Args:
        request: HttpRequest with user attribute
        permission_codename: String like 'add_redcapformmapping' or 'view_redcappatientidmapping'
    
    Returns:
        HttpResponseRedirect if permission denied, None if allowed
    """
    perm = f'patientapp.{permission_codename}'
    if not request.user.has_perm(perm):
        messages.error(request, _('You do not have permission to perform this action.'))
        return redirect('index')
    return None


@login_required
def redcap_project_dashboard(request, pk):
    """List all ProjectRedcapMappings for a given Project."""
    guard = _staff_required(request)
    if guard:
        return guard
    from promapp.models import QuestionnaireSubmission as _QS
    project = get_object_or_404(Project, pk=pk)
    mappings = ProjectRedcapMapping.objects.filter(project=project).order_by('-created_date')

    # Attach fm_stats directly to each mapping object for easy template access.
    mappings = list(mappings)
    for m in mappings:
        patient_ids = set(
            row.patient_id
            for row in RedcapStudyIDtoPatientIDMap.objects.filter(project_redcap_mapping=m)
            if row.redcap_study_id  # filter in Python — EncryptedCharField can't do SQL lookups
        )
        fms = RedcapFormToQuestionnaireMapping.objects.filter(project_redcap_mapping=m)
        fm_stats = []
        for fm in fms:
            total = _QS.objects.filter(
                patient_questionnaire__questionnaire=fm.questionnaire,
                patient__in=patient_ids,
            ).count() if patient_ids else 0
            matched = RedcapInstanceToSubmissionMapping.objects.filter(
                redcap_form=fm,
                questionnaire_submission__patient__in=patient_ids,
            ).count() if patient_ids else 0
            fm_stats.append({'fm': fm, 'total': total, 'matched': matched})
        m.fm_stats = fm_stats

        # Calculate patient ID mapping statistics
        patient_projects = PatientProject.objects.filter(project=project).count()
        # Filter in Python because redcap_study_id is EncryptedCharField
        id_maps = RedcapStudyIDtoPatientIDMap.objects.filter(project_redcap_mapping=m)
        mapped_patients = sum(1 for im in id_maps if im.redcap_study_id)
        m.patient_stats = {
            'total': patient_projects,
            'mapped': mapped_patients,
            'unmapped': patient_projects - mapped_patients,
        }

    return render(request, 'patientapp/redcap/redcap_dashboard.html', {
        'project': project,
        'mappings': mappings,
    })


@login_required
def redcap_mapping_create(request, pk):
    """Create a new ProjectRedcapMapping for a Project."""
    guard = _staff_required(request)
    if guard:
        return guard
    project = get_object_or_404(Project, pk=pk)
    if request.method == 'POST':
        form = ProjectRedcapMappingForm(request.POST)
        if form.is_valid():
            mapping = form.save(commit=False)
            mapping.project = project
            mapping.save()
            messages.success(request, _('REDCap configuration created. Please fetch project metadata next.'))
            return redirect('redcap_project_dashboard', pk=pk)
    else:
        form = ProjectRedcapMappingForm()
    return render(request, 'patientapp/redcap/redcap_project_config_form.html', {
        'form': form,
        'project': project,
        'title': _('Add REDCap Configuration'),
        'action': 'create',
    })


@login_required
def redcap_mapping_edit(request, pk, mapping_pk):
    """Edit an existing ProjectRedcapMapping."""
    guard = _staff_required(request)
    if guard:
        return guard
    project = get_object_or_404(Project, pk=pk)
    mapping = get_object_or_404(ProjectRedcapMapping, pk=mapping_pk, project=project)
    if request.method == 'POST':
        form = ProjectRedcapMappingForm(request.POST, instance=mapping)
        if form.is_valid():
            form.save()
            messages.success(request, _('REDCap configuration updated.'))
            return redirect('redcap_project_dashboard', pk=pk)
    else:
        form = ProjectRedcapMappingForm(instance=mapping)
    return render(request, 'patientapp/redcap/redcap_project_config_form.html', {
        'form': form,
        'project': project,
        'mapping': mapping,
        'title': _('Edit REDCap Configuration'),
        'action': 'edit',
    })


@login_required
def redcap_mapping_delete(request, pk, mapping_pk):
    """Delete a ProjectRedcapMapping configuration."""
    guard = _staff_required(request)
    if guard:
        return guard
    project = get_object_or_404(Project, pk=pk)
    mapping = get_object_or_404(ProjectRedcapMapping, pk=mapping_pk, project=project)

    if request.method == 'POST':
        config_name = str(mapping)
        mapping.delete()
        messages.success(request, _('REDCap configuration "{name}" deleted.').format(name=config_name))
        return redirect('redcap_project_dashboard', pk=pk)

    return render(request, 'patientapp/redcap/redcap_mapping_confirm_delete.html', {
        'project': project,
        'mapping': mapping,
    })


@login_required
def redcap_id_fields(request, pk, mapping_pk):
    """Select Study ID and Secondary ID fields from fetched REDCap metadata."""
    guard = _staff_required(request)
    if guard:
        return guard
    project = get_object_or_404(Project, pk=pk)
    mapping = get_object_or_404(ProjectRedcapMapping, pk=mapping_pk, project=project)
    if not mapping.redcap_project_info:
        messages.warning(request, _('Please fetch REDCap metadata first before selecting ID fields.'))
        return redirect('redcap_project_dashboard', pk=pk)
    if request.method == 'POST':
        form = RedcapIDFieldsForm(request.POST, instance=mapping)
        if form.is_valid():
            form.save()
            messages.success(request, _('ID field mappings saved.'))
            return redirect('redcap_project_dashboard', pk=pk)
    else:
        form = RedcapIDFieldsForm(instance=mapping)
    return render(request, 'patientapp/redcap/redcap_id_fields_form.html', {
        'form': form,
        'project': project,
        'mapping': mapping,
    })


@login_required
def redcap_wizard_page(request, pk, mapping_pk):
    """Full-page wrapper for the REDCap setup wizard."""
    guard = _staff_required(request)
    if guard:
        return guard
    project = get_object_or_404(Project, pk=pk)
    mapping = get_object_or_404(ProjectRedcapMapping, pk=mapping_pk, project=project)
    return render(request, 'patientapp/redcap/redcap_wizard.html', {
        'project': project,
        'mapping': mapping,
    })


def _build_form_meta(mapping):
    """
    Build a dict keyed by instrument_name with pre-derived flags and event name
    for auto-filling the form mapping form.

    Structure per form:
    {
      "form_is_repeating": bool,   # form appears in repeating list with a form_name
      "form_is_in_event": bool,    # project is longitudinal (has events)
      "event_is_repeating": bool,  # form's event appears in repeating list with empty form_name
      "event_name": str,           # unique_event_name of the first event this form is in
    }
    """
    info = (mapping.redcap_project_info or {})
    instruments = info.get('instruments', [])
    events = info.get('events', [])
    repeating = info.get('repeating', [])
    is_longitudinal = bool(int(info.get('project_info', {}).get('is_longitudinal') or 0))

    # Build set of repeating form names (entry has a non-empty form_name)
    repeating_forms = set()
    repeating_events = set()  # event_names where the whole event repeats (form_name == "")
    for r in repeating:
        fn = r.get('form_name', '')
        en = r.get('event_name', '')
        if fn:
            repeating_forms.add(fn)
        elif en:
            repeating_events.add(en)

    # Build map: form_name → list of event unique_names that include this form
    # REDCap instruments_event_mappings is not directly available via basic PyCap export,
    # so we infer: for longitudinal projects use the first event as default event name.
    # If the project has only one event, that applies to all forms.
    first_event = events[0].get('unique_event_name', '') if events else ''

    result = {}
    for inst in instruments:
        name = inst.get('instrument_name', '')
        if not name:
            continue
        form_is_repeating = name in repeating_forms
        form_is_in_event = is_longitudinal and bool(events)
        event_is_repeating = bool(repeating_events) and form_is_in_event
        # Use first event name as default; user can change if multi-arm
        event_name = first_event if form_is_in_event else ''
        result[name] = {
            'form_is_repeating': form_is_repeating,
            'form_is_in_event': form_is_in_event,
            'event_is_repeating': event_is_repeating,
            'event_name': event_name,
        }
    return result


@login_required
def redcap_setup_wizard(request, pk, mapping_pk):
    """Multi-step modal wizard: fetch metadata → ID fields → form mappings."""
    guard = _staff_required(request)
    if guard:
        return guard
    project = get_object_or_404(Project, pk=pk)
    mapping = get_object_or_404(ProjectRedcapMapping, pk=mapping_pk, project=project)

    step = request.GET.get('step', '1')

    if step == '1':
        # Trigger metadata fetch via POST, show result; or just show step 1 shell on GET
        if request.method == 'POST':
            error = None
            try:
                info_payload, record_count = fetch_project_metadata(mapping)
                mapping.redcap_project_info = info_payload
                mapping.redcap_record_count = record_count
                mapping.date_redcap_project_info_updated = timezone.now().date()
                mapping.redcap_data_access_group_used = bool(info_payload.get('dags'))
                mapping.save(update_fields=[
                    'redcap_project_info', 'redcap_record_count',
                    'date_redcap_project_info_updated', 'redcap_data_access_group_used',
                    'modified_date',
                ])
            except Exception as e:
                error = str(e)
            info_json = json.dumps(mapping.redcap_project_info, indent=2, ensure_ascii=False) if mapping.redcap_project_info else ''
            return render(request, 'patientapp/redcap/wizard/step1_result.html', {
                'mapping': mapping, 'project': project, 'error': error, 'info_json': info_json,
            })
        info_json = json.dumps(mapping.redcap_project_info, indent=2, ensure_ascii=False) if mapping.redcap_project_info else ''
        return render(request, 'patientapp/redcap/wizard/step1_result.html', {
            'mapping': mapping, 'project': project, 'error': None, 'info_json': info_json,
        })

    if step == '2':
        form = RedcapIDFieldsForm(
            request.POST if request.method == 'POST' else None,
            instance=mapping,
        )
        if request.method == 'POST' and form.is_valid():
            form.save()
            # Advance to step 3
            form_mapping_form = RedcapFormToQuestionnaireMappingForm(
                project_redcap_mapping=mapping,
            )
            existing_form_mappings = RedcapFormToQuestionnaireMapping.objects.filter(
                project_redcap_mapping=mapping
            )
            return render(request, 'patientapp/redcap/wizard/step3_form_mapping.html', {
                'mapping': mapping, 'project': project,
                'form': form_mapping_form,
                'existing_form_mappings': existing_form_mappings,
                'form_meta_json': json.dumps(_build_form_meta(mapping)),
                'date_fields_by_form_json': json.dumps(form_mapping_form._date_fields_by_form),
            })
        return render(request, 'patientapp/redcap/wizard/step2_id_fields.html', {
            'mapping': mapping, 'project': project, 'form': form,
        })

    if step == '3':
        edit_pk = request.GET.get('edit') or request.POST.get('edit_fm_pk')
        edit_fm = None
        if edit_pk:
            edit_fm = get_object_or_404(RedcapFormToQuestionnaireMapping, pk=edit_pk, project_redcap_mapping=mapping)

        if edit_fm:
            # Inline edit mode
            edit_form = RedcapFormToQuestionnaireMappingForm(
                request.POST if request.method == 'POST' else None,
                instance=edit_fm,
                project_redcap_mapping=mapping,
                prefix='edit',
            )
            if request.method == 'POST' and edit_form.is_valid():
                edit_form.save()
                edit_fm = None
                edit_form = None
            form_mapping_form = RedcapFormToQuestionnaireMappingForm(project_redcap_mapping=mapping)
        else:
            edit_form = None
            form_mapping_form = RedcapFormToQuestionnaireMappingForm(
                request.POST if request.method == 'POST' else None,
                project_redcap_mapping=mapping,
            )
            if request.method == 'POST' and form_mapping_form.is_valid():
                fm = form_mapping_form.save(commit=False)
                fm.project_redcap_mapping = mapping
                fm.save()
                form_mapping_form = RedcapFormToQuestionnaireMappingForm(project_redcap_mapping=mapping)

        existing_form_mappings = RedcapFormToQuestionnaireMapping.objects.filter(
            project_redcap_mapping=mapping
        )
        form_meta = _build_form_meta(mapping)
        return render(request, 'patientapp/redcap/wizard/step3_form_mapping.html', {
            'mapping': mapping, 'project': project,
            'form': form_mapping_form,
            'edit_form': edit_form,
            'edit_fm': edit_fm,
            'existing_form_mappings': existing_form_mappings,
            'form_meta_json': json.dumps(form_meta),
            'date_fields_by_form_json': json.dumps(form_mapping_form._date_fields_by_form),
        })

    return HttpResponse(status=400)


@login_required
def redcap_fetch_metadata(request, pk, mapping_pk):
    """HTMX POST: call PyCap to fetch project metadata and store in redcap_project_info."""
    guard = _staff_required(request)
    if guard:
        return guard
    project = get_object_or_404(Project, pk=pk)
    mapping = get_object_or_404(ProjectRedcapMapping, pk=mapping_pk, project=project)
    if request.method != 'POST':
        return HttpResponse(status=405)

    error = None
    try:
        info_payload, record_count = fetch_project_metadata(mapping)
        mapping.redcap_project_info = info_payload
        mapping.redcap_record_count = record_count
        mapping.date_redcap_project_info_updated = timezone.now().date()
        mapping.save(update_fields=['redcap_project_info', 'redcap_record_count', 'date_redcap_project_info_updated', 'modified_date'])
    except Exception as e:
        error = str(e)

    return render(request, 'patientapp/redcap/partials/metadata_status.html', {
        'mapping': mapping,
        'error': error,
        'project': project,
    })


@login_required
def redcap_form_mappings(request, pk, mapping_pk):
    """List RedcapFormToQuestionnaireMapping entries for a ProjectRedcapMapping."""
    guard = _redcap_permission_required(request, 'view_redcapformtoquestionnairemapping')
    if guard:
        return guard
    project = get_object_or_404(Project, pk=pk)
    mapping = get_object_or_404(ProjectRedcapMapping, pk=mapping_pk, project=project)
    form_mappings = RedcapFormToQuestionnaireMapping.objects.filter(
        project_redcap_mapping=mapping
    ).select_related('questionnaire').order_by('redcap_form_name')
    return render(request, 'patientapp/redcap/redcap_form_mappings.html', {
        'project': project,
        'mapping': mapping,
        'form_mappings': form_mappings,
    })


@login_required
def redcap_form_mapping_create(request, pk, mapping_pk):
    """Create a RedcapFormToQuestionnaireMapping."""
    guard = _redcap_permission_required(request, 'add_redcapformtoquestionnairemapping')
    if guard:
        return guard
    project = get_object_or_404(Project, pk=pk)
    mapping = get_object_or_404(ProjectRedcapMapping, pk=mapping_pk, project=project)
    if request.method == 'POST':
        form = RedcapFormToQuestionnaireMappingForm(request.POST, project_redcap_mapping=mapping)
        if form.is_valid():
            fm = form.save(commit=False)
            fm.project_redcap_mapping = mapping
            fm.save()
            messages.success(request, _('Form mapping created.'))
            return redirect('redcap_form_mappings', pk=pk, mapping_pk=mapping_pk)
    else:
        form = RedcapFormToQuestionnaireMappingForm(project_redcap_mapping=mapping)
    return render(request, 'patientapp/redcap/redcap_form_mapping_form.html', {
        'form': form,
        'project': project,
        'mapping': mapping,
        'title': _('Add Form Mapping'),
        'action': 'create',
        'form_meta_json': json.dumps(_build_form_meta(mapping)),
        'date_fields_by_form_json': json.dumps(form._date_fields_by_form),
    })


@login_required
def redcap_form_mapping_edit(request, pk, mapping_pk, fm_pk):
    """Edit a RedcapFormToQuestionnaireMapping."""
    guard = _redcap_permission_required(request, 'change_redcapformtoquestionnairemapping')
    if guard:
        return guard
    project = get_object_or_404(Project, pk=pk)
    mapping = get_object_or_404(ProjectRedcapMapping, pk=mapping_pk, project=project)
    fm = get_object_or_404(RedcapFormToQuestionnaireMapping, pk=fm_pk, project_redcap_mapping=mapping)
    if request.method == 'POST':
        form = RedcapFormToQuestionnaireMappingForm(request.POST, instance=fm, project_redcap_mapping=mapping)
        if form.is_valid():
            form.save()
            messages.success(request, _('Form mapping updated.'))
            return redirect('redcap_form_mappings', pk=pk, mapping_pk=mapping_pk)
    else:
        form = RedcapFormToQuestionnaireMappingForm(instance=fm, project_redcap_mapping=mapping)
    return render(request, 'patientapp/redcap/redcap_form_mapping_form.html', {
        'form': form,
        'project': project,
        'mapping': mapping,
        'fm': fm,
        'title': _('Edit Form Mapping'),
        'action': 'edit',
        'form_meta_json': json.dumps(_build_form_meta(mapping)),
        'date_fields_by_form_json': json.dumps(form._date_fields_by_form),
    })


@login_required
def redcap_form_mapping_delete(request, pk, mapping_pk, fm_pk):
    """Delete a RedcapFormToQuestionnaireMapping."""
    guard = _redcap_permission_required(request, 'delete_redcapformtoquestionnairemapping')
    if guard:
        return guard
    project = get_object_or_404(Project, pk=pk)
    mapping = get_object_or_404(ProjectRedcapMapping, pk=mapping_pk, project=project)
    fm = get_object_or_404(RedcapFormToQuestionnaireMapping, pk=fm_pk, project_redcap_mapping=mapping)

    if request.method == 'POST':
        form_name = fm.redcap_form_name
        fm.delete()
        messages.success(request, _('Form mapping "{name}" deleted.').format(name=form_name))
        return redirect('redcap_form_mappings', pk=pk, mapping_pk=mapping_pk)

    return render(request, 'patientapp/redcap/redcap_form_mapping_confirm_delete.html', {
        'project': project,
        'mapping': mapping,
        'fm': fm,
    })


@login_required
def redcap_field_mappings(request, pk, mapping_pk, fm_pk):
    """Create/edit RedcapFieldToItemMapping entries for a form mapping."""
    import difflib, html, re as _re
    # Check appropriate permission based on action
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'delete':
            guard = _redcap_permission_required(request, 'delete_redcapfieldtoitemmapping')
        elif action in ('bulk_save', 'edit_row'):
            guard = _redcap_permission_required(request, 'change_redcapfieldtoitemmapping')
        else:  # bulk_add, auto_map, etc.
            guard = _redcap_permission_required(request, 'add_redcapfieldtoitemmapping')
    else:
        guard = _redcap_permission_required(request, 'view_redcapfieldtoitemmapping')
    if guard:
        return guard
    project = get_object_or_404(Project, pk=pk)
    mapping = get_object_or_404(ProjectRedcapMapping, pk=mapping_pk, project=project)
    fm = get_object_or_404(RedcapFormToQuestionnaireMapping, pk=fm_pk, project_redcap_mapping=mapping)

    def _get_existing():
        return RedcapFieldToItemMapping.objects.filter(
            redcap_form_to_questionnaire_mapping=fm
        ).select_related('questionnaire_item__item')

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'bulk_save':
            from promapp.models import QuestionnaireItem as _QI
            already_mapped_fields = set(
                RedcapFieldToItemMapping.objects.filter(
                    redcap_form_to_questionnaire_mapping=fm
                ).values_list('redcap_field_name', flat=True)
            )
            already_mapped_items = set(
                RedcapFieldToItemMapping.objects.filter(
                    redcap_form_to_questionnaire_mapping=fm
                ).values_list('questionnaire_item_id', flat=True)
            )
            created = 0
            skipped = 0
            from patientapp.models import ResponseTransformChoices as _RTC
            valid_transforms = {v for v, _ in _RTC.choices}
            for key, qi_pk in request.POST.items():
                if not key.startswith('map__') or not qi_pk:
                    continue
                redcap_field = key[5:]  # strip 'map__'
                if redcap_field in already_mapped_fields:
                    skipped += 1
                    continue
                try:
                    qi = _QI.objects.get(pk=qi_pk, questionnaire=fm.questionnaire)
                except _QI.DoesNotExist:
                    continue
                if str(qi.pk) in [str(x) for x in already_mapped_items]:
                    skipped += 1
                    continue
                transform = request.POST.get(f'transform__{redcap_field}', _RTC.NONE)
                if transform not in valid_transforms:
                    transform = _RTC.NONE
                RedcapFieldToItemMapping.objects.create(
                    redcap_form_to_questionnaire_mapping=fm,
                    redcap_field_name=redcap_field,
                    questionnaire_item=qi,
                    response_transform=transform,
                )
                already_mapped_fields.add(redcap_field)
                already_mapped_items.add(str(qi.pk))
                created += 1
            if created:
                messages.success(request, _(f'{created} field mapping(s) saved.'))
            if skipped:
                messages.warning(request, _(f'{skipped} row(s) skipped (already mapped or duplicate).'))

        elif action == 'edit_mapping':
            from promapp.models import QuestionnaireItem as _QI
            from patientapp.models import ResponseTransformChoices as _RTC
            field_map_pk = request.POST.get('field_map_pk')
            new_qi_pk = request.POST.get('new_questionnaire_item')
            new_transform = request.POST.get('response_transform', _RTC.NONE)
            # Validate transform value
            valid_transforms = {v for v, _ in _RTC.choices}
            if new_transform not in valid_transforms:
                new_transform = _RTC.NONE
            try:
                field_map = RedcapFieldToItemMapping.objects.get(
                    pk=field_map_pk, redcap_form_to_questionnaire_mapping=fm
                )
                new_qi = _QI.objects.get(pk=new_qi_pk, questionnaire=fm.questionnaire)
                # Check the new item isn't already mapped to a different field
                conflict = RedcapFieldToItemMapping.objects.filter(
                    redcap_form_to_questionnaire_mapping=fm,
                    questionnaire_item=new_qi,
                ).exclude(pk=field_map_pk).first()
                if conflict:
                    messages.error(request, _(
                        f'"{new_qi}" is already mapped to field "{conflict.redcap_field_name}". '
                        'Remove that mapping first.'
                    ))
                else:
                    field_map.questionnaire_item = new_qi
                    field_map.response_transform = new_transform
                    field_map.save(update_fields=['questionnaire_item', 'response_transform', 'modified_at'])
                    messages.success(request, _('Mapping updated.'))
            except (RedcapFieldToItemMapping.DoesNotExist, _QI.DoesNotExist):
                messages.error(request, _('Invalid mapping or questionnaire item.'))

        elif action == 'delete':
            field_map_pk = request.POST.get('field_map_pk')
            RedcapFieldToItemMapping.objects.filter(
                pk=field_map_pk, redcap_form_to_questionnaire_mapping=fm
            ).delete()
            messages.success(request, _('Field mapping removed.'))

        return redirect('redcap_field_mappings', pk=pk, mapping_pk=mapping_pk, fm_pk=fm_pk)

    # ── Build REDCap field list for this form ────────────────────────────────
    CHOICE_FIELD_TYPES = {'radio', 'dropdown', 'checkbox'}
    from patientapp.models import ResponseTransformChoices as _RTC

    def _parse_choices(raw_choices):
        """Parse 'code, label | code, label | ...' into [{code, label}, ...]."""
        if not raw_choices:
            return []
        choices = []
        for part in raw_choices.split('|'):
            part = part.strip()
            if ',' in part:
                code, _, label = part.partition(',')
                choices.append({'code': code.strip(), 'label': label.strip()})
        return choices

    def _suggest_transform(ftype, validation, choices):
        """Infer the most appropriate ResponseTransformChoice for a REDCap field."""
        if ftype in CHOICE_FIELD_TYPES:
            # Choice codes are almost always integers (1, 2, 3 …); suggest to_int
            # unless any code contains a decimal point
            all_int_codes = all(
                c['code'].lstrip('-').isdigit() for c in choices if c['code']
            )
            return _RTC.TO_INT if all_int_codes else _RTC.STRIP_ZEROS
        if ftype in ('yesno', 'truefalse'):
            return _RTC.TO_INT
        if ftype == 'text':
            if validation in ('integer', 'number'):
                return _RTC.TO_INT
            if validation in ('number_2dp',):
                return _RTC.TO_FLOAT_2
            if validation and validation.startswith('number'):
                return _RTC.STRIP_ZEROS
        if ftype == 'calc':
            return _RTC.STRIP_ZEROS
        if ftype == 'slider':
            # slider validation is either empty or 'number'
            return _RTC.TO_INT if not validation else _RTC.STRIP_ZEROS
        return _RTC.NONE

    redcap_fields = []  # [{name, label_plain, field_type, validation, choices, field_info_summary}]
    if mapping.redcap_project_info:
        for field in mapping.redcap_project_info.get('metadata', []):
            if field.get('form_name') != fm.redcap_form_name:
                continue
            fname = field.get('field_name', '')
            if not fname:
                continue
            raw_label = field.get('field_label', fname)
            label_plain = _re.sub(r'<[^>]+>', '', html.unescape(raw_label)).strip() or fname
            ftype = field.get('field_type', '')
            validation = field.get('text_validation_type_or_show_slider_number', '')
            raw_choices = field.get('select_choices_or_calculations', '')
            choices = _parse_choices(raw_choices) if ftype in CHOICE_FIELD_TYPES else []

            # Build a human-readable summary of what REDCap expects for this field
            if ftype in CHOICE_FIELD_TYPES:
                field_info_summary = 'codes: ' + ', '.join(
                    f'{c["code"]}={c["label"]}' for c in choices[:5]
                ) + (' …' if len(choices) > 5 else '')
            elif ftype == 'text' and validation:
                field_info_summary = f'text / {validation}'
            elif ftype == 'text':
                field_info_summary = 'free text'
            elif ftype == 'yesno':
                field_info_summary = '1=Yes, 0=No'
            elif ftype == 'truefalse':
                field_info_summary = '1=True, 0=False'
            elif ftype == 'slider':
                field_info_summary = f'slider{(" / " + validation) if validation else ""}'
            elif ftype == 'calc':
                field_info_summary = 'calculated field'
            elif ftype == 'notes':
                field_info_summary = 'long text'
            else:
                field_info_summary = ftype or '—'

            redcap_fields.append({
                'name': fname,
                'label': raw_label,
                'label_plain': label_plain,
                'field_type': ftype,
                'validation': validation,
                'choices': choices,
                'field_info_summary': field_info_summary,
                'suggested_transform': _suggest_transform(ftype, validation, choices),
            })

    # ── Build questionnaire items list ──────────────────────────────────────
    from promapp.models import QuestionnaireItem as _QI
    qi_qs = _QI.objects.filter(
        questionnaire=fm.questionnaire
    ).select_related('item').order_by('question_number')

    qi_list = []  # [{pk, number, name}]
    for qi in qi_qs:
        item_name = (
            qi.item.safe_translation_getter('name', any_language=True)
            if hasattr(qi.item, 'safe_translation_getter')
            else str(qi.item)
        ) or str(qi.item)
        qi_list.append({'pk': str(qi.pk), 'number': qi.question_number, 'name': item_name})

    # ── Fuzzy match each REDCap field to best questionnaire item ────────────
    already_mapped_fields = set(
        _get_existing().values_list('redcap_field_name', flat=True)
    )
    qi_names = [q['name'] for q in qi_list]

    def _best_match(field_name, label_plain):
        if not qi_names:
            return None
        # Score against both field_name and label_plain, take best
        scores = []
        for qi in qi_list:
            s1 = difflib.SequenceMatcher(None, field_name.lower(), qi['name'].lower()).ratio()
            s2 = difflib.SequenceMatcher(None, label_plain.lower(), qi['name'].lower()).ratio()
            # Also try word-level overlap
            rc_words = set(field_name.lower().replace('_', ' ').split())
            qi_words = set(qi['name'].lower().split())
            word_overlap = len(rc_words & qi_words) / max(len(rc_words | qi_words), 1)
            scores.append((max(s1, s2, word_overlap), qi['pk']))
        scores.sort(key=lambda x: -x[0])
        best_score, best_pk = scores[0]
        return best_pk if best_score >= 0.25 else None

    # Lookup dict for template use in saved-mappings section
    redcap_field_info = {rf['name']: rf for rf in redcap_fields}

    suggestion_rows = []  # only unmapped fields
    for rf in redcap_fields:
        if rf['name'] in already_mapped_fields:
            continue
        suggested_pk = _best_match(rf['name'], rf['label_plain'])
        suggestion_rows.append({
            'name': rf['name'],
            'label': rf['label'],
            'label_plain': rf['label_plain'],
            'field_type': rf['field_type'],
            'validation': rf['validation'],
            'choices': rf['choices'],
            'field_info_summary': rf['field_info_summary'],
            'suggested_pk': suggested_pk or '',
            'suggested_transform': rf['suggested_transform'],
        })

    from patientapp.models import ResponseTransformChoices as _RTC
    # Enrich existing mappings with REDCap field metadata for display
    existing_qs = _get_existing()
    enriched_existing = []
    for em in existing_qs:
        fi = redcap_field_info.get(em.redcap_field_name, {})
        enriched_existing.append({
            'obj': em,
            'field_type': fi.get('field_type', ''),
            'validation': fi.get('validation', ''),
            'choices': fi.get('choices', []),
            'field_info_summary': fi.get('field_info_summary', ''),
            'response_transform': em.response_transform,
            'response_transform_label': em.get_response_transform_display(),
            'suggested_transform': fi.get('suggested_transform', _RTC.NONE),
        })

    transform_choices = _RTC.choices

    return render(request, 'patientapp/redcap/redcap_field_mappings.html', {
        'project': project,
        'mapping': mapping,
        'fm': fm,
        'existing': existing_qs,
        'enriched_existing': enriched_existing,
        'suggestion_rows': suggestion_rows,
        'qi_list': qi_list,
        'qi_list_json': json.dumps(qi_list),
        'transform_choices': transform_choices,
        'transform_none_value': _RTC.NONE,
    })


@login_required
def redcap_patient_ids(request, pk, mapping_pk):
    """Map patients in the project to their REDCap study IDs."""
    guard = _redcap_permission_required(request, 'change_redcapstudyidtopatientidmap')
    if guard:
        return guard
    project = get_object_or_404(Project, pk=pk)
    mapping = get_object_or_404(ProjectRedcapMapping, pk=mapping_pk, project=project)

    patient_projects = PatientProject.objects.filter(project=project).select_related('patient')

    if request.method == 'POST':
        action = request.POST.get('action', 'save')
        if action == 'clear':
            patient_pk = request.POST.get('patient_pk', '').strip()
            RedcapStudyIDtoPatientIDMap.objects.filter(
                project_redcap_mapping=mapping,
                patient__pk=patient_pk,
            ).delete()
            messages.success(request, _('Patient ID mapping cleared.'))
        elif action == 'save_page_auto':
            # Bulk save all auto-matched patients on the current page
            patient_pks = request.POST.getlist('auto_patient_pks')
            # Fetch REDCap records for auto-matching
            try:
                _redcap_records = fetch_patient_id_records(mapping)
            except Exception:
                _redcap_records = []
            _primary_lookup = {r['primary'].lower(): r['primary'] for r in _redcap_records}
            _secondary_lookup = {r['secondary'].lower(): r['primary'] for r in _redcap_records if r['secondary']}
            saved_count = 0
            for ppk in patient_pks:
                try:
                    patient = Patient.objects.get(pk=ppk)
                except Patient.DoesNotExist:
                    continue
                # Skip if already has a saved mapping
                if RedcapStudyIDtoPatientIDMap.objects.filter(
                    project_redcap_mapping=mapping, patient=patient
                ).exists():
                    continue
                pid = (patient.patient_id or '').strip().lower()
                suggested = ''
                if pid in _primary_lookup:
                    suggested = _primary_lookup[pid]
                elif pid in _secondary_lookup:
                    suggested = _secondary_lookup[pid]
                if suggested:
                    obj, created = RedcapStudyIDtoPatientIDMap.objects.get_or_create(
                        project_redcap_mapping=mapping,
                        patient=patient,
                    )
                    obj.redcap_study_id = suggested
                    obj.save(update_fields=['redcap_study_id', 'modified_at'])
                    saved_count += 1
            if saved_count > 0:
                messages.success(request, _('{count} auto-matched patient ID(s) saved.').format(count=saved_count))
            else:
                messages.info(request, _('No auto-matched patients were saved.'))
        elif action == 'save_single_auto':
            # Save a single auto-matched patient
            patient_pk = request.POST.get('patient_pk', '').strip()
            try:
                _redcap_records = fetch_patient_id_records(mapping)
            except Exception:
                _redcap_records = []
            _primary_lookup = {r['primary'].lower(): r['primary'] for r in _redcap_records}
            _secondary_lookup = {r['secondary'].lower(): r['primary'] for r in _redcap_records if r['secondary']}
            try:
                patient = Patient.objects.get(pk=patient_pk)
            except Patient.DoesNotExist:
                messages.error(request, _('Patient not found.'))
                return redirect('redcap_patient_ids', pk=pk, mapping_pk=mapping_pk)
            pid = (patient.patient_id or '').strip().lower()
            suggested = ''
            if pid in _primary_lookup:
                suggested = _primary_lookup[pid]
            elif pid in _secondary_lookup:
                suggested = _secondary_lookup[pid]
            if suggested:
                obj, created = RedcapStudyIDtoPatientIDMap.objects.get_or_create(
                    project_redcap_mapping=mapping,
                    patient=patient,
                )
                obj.redcap_study_id = suggested
                obj.save(update_fields=['redcap_study_id', 'modified_at'])
                messages.success(request, _('Auto-matched patient ID saved.'))
            else:
                messages.error(request, _('No auto-match found for this patient.'))
        elif request.POST.get('modal_single'):
            # Single-patient save from the modal dialog
            patient_pk = request.POST.get('modal_patient_pk', '').strip()
            study_id_val = request.POST.get('modal_study_id', '').strip()
            from django.shortcuts import get_object_or_404 as _get404
            from .models import Patient as _Patient
            patient = _get404(_Patient, pk=patient_pk)
            obj, created = RedcapStudyIDtoPatientIDMap.objects.get_or_create(
                project_redcap_mapping=mapping,
                patient=patient,
            )
            obj.redcap_study_id = study_id_val or None
            obj.save(update_fields=['redcap_study_id', 'modified_at'])
            messages.success(request, _('Patient ID mapping saved.'))
        return redirect('redcap_patient_ids', pk=pk, mapping_pk=mapping_pk)

    # Field names used for display in the template
    primary_field = mapping.redcap_study_id_field or 'record_id'
    secondary_field = mapping.redcap_secondary_id_field or ''

    # Fetch REDCap records to populate dropdown choices
    redcap_records = []
    redcap_fetch_error = None
    try:
        redcap_records = fetch_patient_id_records(mapping)
    except Exception as e:
        redcap_fetch_error = str(e)

    # Build a lookup set for fast auto-matching (lowercase)
    primary_lookup = {r['primary'].lower(): r['primary'] for r in redcap_records}
    secondary_lookup = {r['secondary'].lower(): r['primary'] for r in redcap_records if r['secondary']}

    id_maps = {
        m.patient_id: m.redcap_study_id
        for m in RedcapStudyIDtoPatientIDMap.objects.filter(project_redcap_mapping=mapping)
    }

    # Get submission matching stats per patient
    from promapp.models import QuestionnaireSubmission as _QS
    form_mappings = RedcapFormToQuestionnaireMapping.objects.filter(project_redcap_mapping=mapping)
    submission_stats = {}
    for pp in patient_projects:
        patient = pp.patient
        total_submissions = 0
        matched_submissions = 0
        for fm in form_mappings:
            patient_subs = _QS.objects.filter(
                patient_questionnaire__questionnaire=fm.questionnaire,
                patient=patient,
            )
            total_submissions += patient_subs.count()
            matched = RedcapInstanceToSubmissionMapping.objects.filter(
                redcap_form=fm,
                questionnaire_submission__in=patient_subs,
            ).count()
            matched_submissions += matched
        submission_stats[patient.pk] = {
            'total': total_submissions,
            'matched': matched_submissions,
        }

    rows = []
    for pp in patient_projects:
        patient = pp.patient
        existing = id_maps.get(patient.pk, '')
        pid = (patient.patient_id or '').strip()
        pid_lower = pid.lower()
        # Auto-suggest: prefer existing saved value, then exact match on primary, then secondary
        if existing:
            suggested = existing
            auto_matched = False
        elif pid_lower in primary_lookup:
            suggested = primary_lookup[pid_lower]
            auto_matched = True
        elif pid_lower in secondary_lookup:
            suggested = secondary_lookup[pid_lower]
            auto_matched = True
        else:
            suggested = ''
            auto_matched = False
        rows.append({
            'patient': patient,
            'redcap_study_id': suggested,
            'auto_matched': auto_matched,
            'submission_stats': submission_stats.get(patient.pk, {'total': 0, 'matched': 0}),
        })

    # Apply filtering
    match_filter = request.GET.get('match_filter', 'all')
    if match_filter == 'mapped':
        rows = [r for r in rows if r['redcap_study_id']]
    elif match_filter == 'unmapped':
        rows = [r for r in rows if not r['redcap_study_id']]
    elif match_filter == 'partial_match':
        rows = [
            r for r in rows
            if r['submission_stats']['total'] > 0
            and r['submission_stats']['matched'] < r['submission_stats']['total']
        ]
    elif match_filter == 'full_match':
        rows = [
            r for r in rows
            if r['submission_stats']['total'] > 0
            and r['submission_stats']['matched'] == r['submission_stats']['total']
        ]

    # Page size selector
    per_page = request.GET.get('per_page', '25')
    if per_page == 'all':
        per_page_num = len(rows)
    else:
        try:
            per_page_num = int(per_page)
        except (ValueError, TypeError):
            per_page_num = 25
        per_page = str(per_page_num)

    # Pagination
    from django.core.paginator import Paginator
    paginator = Paginator(rows, per_page_num)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    mapped_count = sum(1 for r in rows if r['redcap_study_id'])
    auto_match_count = sum(1 for r in page_obj if r.get('auto_matched'))
    return render(request, 'patientapp/redcap/redcap_patient_ids.html', {
        'project': project,
        'mapping': mapping,
        'rows': page_obj,
        'page_obj': page_obj,
        'paginator': paginator,
        'match_filter': match_filter,
        'mapped_count': mapped_count,
        'auto_match_count': auto_match_count,
        'per_page': per_page,
        'redcap_records': redcap_records,
        'primary_field': primary_field,
        'secondary_field': secondary_field,
        'redcap_fetch_error': redcap_fetch_error,
    })


@login_required
def redcap_patient_id_delete(request, pk, mapping_pk, patient_pk):
    """Delete a REDCap study ID mapping for a specific patient."""
    guard = _redcap_permission_required(request, 'delete_redcapstudyidtopatientidmap')
    if guard:
        return guard
    project = get_object_or_404(Project, pk=pk)
    mapping = get_object_or_404(ProjectRedcapMapping, pk=mapping_pk, project=project)
    patient = get_object_or_404(Patient, pk=patient_pk)

    # Get the mapping to display in confirmation
    id_map = RedcapStudyIDtoPatientIDMap.objects.filter(
        project_redcap_mapping=mapping,
        patient=patient
    ).first()

    if request.method == 'POST':
        if id_map:
            study_id = id_map.redcap_study_id
            id_map.delete()
            messages.success(
                request,
                _('Study ID mapping for {patient} cleared.').format(patient=patient.name)
            )
        else:
            messages.info(request, _('No mapping exists for this patient.'))
        return redirect('redcap_patient_ids', pk=pk, mapping_pk=mapping_pk)

    return render(request, 'patientapp/redcap/redcap_patient_id_confirm_delete.html', {
        'project': project,
        'mapping': mapping,
        'patient': patient,
        'id_map': id_map,
    })


@login_required
def redcap_match_submissions(request, pk, mapping_pk, patient_pk):
    """Per-patient submission → REDCap instance matching review and save."""
    guard = _redcap_permission_required(request, 'change_redcapinstancetosubmissionmapping')
    if guard:
        return guard
    project = get_object_or_404(Project, pk=pk)
    mapping = get_object_or_404(ProjectRedcapMapping, pk=mapping_pk, project=project)
    patient = get_object_or_404(Patient, pk=patient_pk)

    # Patient must be enrolled in this project
    if not PatientProject.objects.filter(project=project, patient=patient).exists():
        messages.error(request, _('Patient is not enrolled in this project.'))
        return redirect('redcap_patient_ids', pk=pk, mapping_pk=mapping_pk)

    # Patient must have a study ID mapped
    study_id_map = RedcapStudyIDtoPatientIDMap.objects.filter(
        project_redcap_mapping=mapping, patient=patient
    ).first()
    if not study_id_map or not study_id_map.redcap_study_id:
        messages.error(request, _('Please assign a REDCap study ID to this patient before matching submissions.'))
        return redirect('redcap_patient_ids', pk=pk, mapping_pk=mapping_pk)

    redcap_study_id = study_id_map.redcap_study_id

    from promapp.models import QuestionnaireSubmission

    form_mappings = RedcapFormToQuestionnaireMapping.objects.filter(
        project_redcap_mapping=mapping
    )

    # Build per-form-mapping data: submissions + REDCap instances + existing matches
    fm_data = []
    fetch_errors = {}

    # Build lookups: field_name -> form_name and field_name -> validation type from REDCap metadata
    _metadata_field_to_form = {}
    _metadata_field_validation = {}
    if mapping.redcap_project_info:
        for _f in mapping.redcap_project_info.get('metadata', []):
            _fname = _f.get('field_name', '')
            _fform = _f.get('form_name', '')
            _fval = _f.get('text_validation_type_or_show_slider_number', '')
            if _fname:
                _metadata_field_to_form[_fname] = _fform
                _metadata_field_validation[_fname] = _fval

    for fm in form_mappings:
        submissions = list(
            QuestionnaireSubmission.objects.filter(
                patient=patient,
                patient_questionnaire__questionnaire=fm.questionnaire,
            ).order_by('submission_date')
        )
        if not submissions:
            continue

        # Load existing confirmed matches for this patient + form mapping
        existing_matches = {
            m.questionnaire_submission_id: m
            for m in RedcapInstanceToSubmissionMapping.objects.filter(
                questionnaire_submission__in=submissions,
                redcap_form=fm,
            )
        }

        # Resolve which form actually owns the date mapping field from metadata
        date_field_form_name = _metadata_field_to_form.get(fm.redcap_date_mapping_field or '', '') or fm.redcap_form_name

        # Determine if the date mapping field is a date or datetime field
        _date_field_validation = _metadata_field_validation.get(fm.redcap_date_mapping_field or '', '')
        _is_datetime_field = _date_field_validation.startswith('datetime_')

        # Fetch REDCap instances for this patient — two separate calls:
        #   1. Questionnaire form records → all (event, repeat_instance) pairs
        #   2. Date field form records → (event, date_value) per event
        # Then: match submission → closest date → event → instance from call 1.
        rc_instances = []   # final list: {event, instance, date_str}
        fetch_error = None
        if fm.redcap_date_mapping_field:
            try:
                # --- Call 1: all instances of the questionnaire form ---
                q_raw = fetch_form_instances(
                    mapping,
                    record_id=redcap_study_id,
                    form_name=fm.redcap_form_name,
                )
                event_to_instances = {}
                for rec in q_raw:
                    ev = rec.get('redcap_event_name', '')
                    inst = rec.get('redcap_repeat_instance', '')
                    inst_int = int(inst) if str(inst).isdigit() else None
                    event_to_instances.setdefault(ev, []).append(inst_int)

                # --- Call 2: date field values across all events ---
                event_to_date = fetch_field_values_for_record(
                    mapping,
                    record_id=redcap_study_id,
                    field_name=fm.redcap_date_mapping_field,
                    form_name=date_field_form_name,
                )

                # --- Combine: one entry per (event, instance) with its date ---
                # event_to_date is keyed by (event_name, instance_int_or_None)
                for ev, instances in event_to_instances.items():
                    for inst in instances:
                        date_str = (
                            event_to_date.get((ev, inst), '')  # repeating: per-instance key
                            or event_to_date.get((ev, None), '')  # non-repeating fallback
                        )
                        rc_instances.append({
                            'event': ev,
                            'instance': inst,
                            'date_str': date_str,
                        })

            except Exception as e:
                fetch_error = str(e)
                fetch_errors[fm.pk] = fetch_error

        # Build ordered list of unique event names for the dropdown.
        # Prefer order from project_info events; fall back to rc_instances order.
        from django.utils.dateparse import parse_datetime, parse_date
        _pi_events = (mapping.redcap_project_info or {}).get('events', [])
        if _pi_events:
            available_events = [e.get('unique_event_name', '') for e in _pi_events if e.get('unique_event_name')]
        else:
            seen_evs = []
            for _r in rc_instances:
                if _r['event'] and _r['event'] not in seen_evs:
                    seen_evs.append(_r['event'])
            available_events = seen_evs or ([fm.redcap_event_name] if fm.redcap_event_name else [])

        # Build per-submission suggestion rows.
        # Two-pass approach for auto-increment:
        #   Pass 1 — assign best event to each unconfirmed submission
        #   Pass 2 — within each event, number instances sequentially by submission_date
        sub_rows = []
        for sub in submissions:
            existing = existing_matches.get(sub.pk)
            confirmed = existing is not None
            if existing:
                # For confirmed rows, look up the matched RC instance date
                _confirmed_date_matched = True
                _confirmed_match_delta = None
                if rc_instances and fm.redcap_date_mapping_field:
                    _matched_rc_date = None
                    for rc in rc_instances:
                        if rc['event'] == (existing.redcap_event_name or '') and rc['instance'] == existing.redcap_repeat_instance:
                            if rc['date_str']:
                                try:
                                    _matched_rc_date = parse_datetime(rc['date_str']) or parse_date(rc['date_str'])
                                except Exception:
                                    pass
                            break
                    if _matched_rc_date is not None:
                        if _is_datetime_field:
                            _confirmed_date_matched = sub.submission_date.replace(tzinfo=None) == _matched_rc_date.replace(tzinfo=None)
                        else:
                            _confirmed_date_matched = sub.submission_date.date() == _matched_rc_date.date()
                        _delta_days = (sub.submission_date.date() - _matched_rc_date.date()).days
                        _confirmed_match_delta = {
                            'days': _delta_days,
                            'weeks': round(_delta_days / 7),
                            'months': round(_delta_days / 30),
                        }
                sub_rows.append({
                    'submission': sub,
                    'suggested_event': existing.redcap_event_name or '',
                    'suggested_instance': existing.redcap_repeat_instance,
                    'confirmed': True,
                    'existing': existing,
                    'date_matched': _confirmed_date_matched,
                    'match_delta': _confirmed_match_delta,
                })
            else:
                # Date-proximity: find the rc_instance whose date is closest to submission_date
                _MATCH_THRESHOLD_SECONDS = 30 * 86400  # 30 days — no suggestion beyond this
                best_event = fm.redcap_event_name or (available_events[0] if available_events else '')
                best_instance = None  # if set, skip Pass 2 auto-increment for this row
                best_rc_date = None
                if rc_instances and fm.redcap_date_mapping_field:
                    best_delta = None
                    for inst in rc_instances:
                        if not inst['date_str']:
                            continue
                        try:
                            rc_dt = parse_datetime(inst['date_str']) or parse_date(inst['date_str'])
                            if rc_dt:
                                if hasattr(rc_dt, 'date'):
                                    delta = abs((sub.submission_date.replace(tzinfo=None) - rc_dt.replace(tzinfo=None)).total_seconds())
                                else:
                                    delta = abs((sub.submission_date.date() - rc_dt).days * 86400)
                                if delta <= _MATCH_THRESHOLD_SECONDS and (best_delta is None or delta < best_delta):
                                    best_delta = delta
                                    best_event = inst['event']
                                    best_instance = inst['instance']  # use this instance directly
                                    best_rc_date = rc_dt
                        except Exception:
                            continue
                # Determine if this is an exact match (same day for date fields, exact datetime for datetime fields)
                if best_rc_date is not None:
                    if _is_datetime_field:
                        _date_matched = sub.submission_date.replace(tzinfo=None) == best_rc_date.replace(tzinfo=None)
                    else:
                        _date_matched = sub.submission_date.date() == best_rc_date.date()
                    _delta_days = (sub.submission_date.date() - best_rc_date.date()).days
                    _match_delta = {
                        'days': _delta_days,
                        'weeks': round(_delta_days / 7),
                        'months': round(_delta_days / 30),
                    }
                else:
                    _date_matched = False
                    _match_delta = None
                sub_rows.append({
                    'submission': sub,
                    'suggested_event': best_event,
                    'suggested_instance': best_instance,  # None → filled by Pass 2; int → skip Pass 2
                    'confirmed': False,
                    'existing': None,
                    'date_matched': _date_matched,
                    'match_delta': _match_delta,
                })

        # Pass 2 — auto-increment instance numbers per event for unconfirmed rows,
        # ordering within each event by submission_date (already sorted ascending).
        # Start from max existing REDCap instance for that event + 1 to avoid collisions.
        if fm.redcap_form_is_repeating or fm.redcap_event_is_repeating:
            # Build max existing instance per event from rc_instances
            existing_max = {}
            for rc in rc_instances:
                ev = rc['event']
                inst = rc['instance']
                if inst is not None:
                    existing_max[ev] = max(existing_max.get(ev, 0), inst)
            event_counter = dict(existing_max)  # start counters from existing max
            for row in sub_rows:
                if not row['confirmed'] and row['suggested_instance'] is None:
                    ev = row['suggested_event']
                    event_counter[ev] = event_counter.get(ev, 0) + 1
                    row['suggested_instance'] = event_counter[ev]

        # Build event -> date mapping for display in dropdown
        event_dates = {}
        for rc in rc_instances:
            ev = rc.get('event')
            date_str = rc.get('date_str')
            if ev and date_str and not event_dates.get(ev):
                event_dates[ev] = date_str

        # Calculate time intervals from previous submission and from first submission
        # sub_rows is already sorted by submission_date (ascending)
        from datetime import timedelta
        first_date = sub_rows[0]['submission'].submission_date if sub_rows else None
        for i, row in enumerate(sub_rows):
            curr_date = row['submission'].submission_date
            # Time from previous submission
            if i == 0:
                row['interval_from_prev'] = None
            else:
                prev_date = sub_rows[i-1]['submission'].submission_date
                delta = curr_date - prev_date
                row['interval_from_prev'] = {
                    'days': delta.days,
                    'weeks': round(delta.days / 7),
                    'months': round(delta.days / 30),
                }
            # Time from first submission (cumulative)
            if first_date:
                delta_from_first = curr_date - first_date
                row['interval_from_first'] = {
                    'days': delta_from_first.days,
                    'weeks': round(delta_from_first.days / 7),
                    'months': round(delta_from_first.days / 30),
                }
            else:
                row['interval_from_first'] = None

        fm_data.append({
            'fm': fm,
            'sub_rows': sub_rows,
            'rc_instances': rc_instances,
            'fetch_error': fetch_error,
            'date_field_form_name': date_field_form_name,
            'available_events': available_events,
            'event_dates': event_dates,
        })

    if request.method == 'POST':
        saved_count = 0
        for fm_entry in fm_data:
            fm = fm_entry['fm']
            for row in fm_entry['sub_rows']:
                sub = row['submission']

                # Only process if checkbox is checked
                key_include = f'include_{fm.pk}_{sub.pk}'
                if request.POST.get(key_include) != 'on':
                    continue

                key_event = f'event_{fm.pk}_{sub.pk}'
                key_instance = f'instance_{fm.pk}_{sub.pk}'
                event_val = request.POST.get(key_event, '').strip()
                instance_val = request.POST.get(key_instance, '').strip()
                instance_int = int(instance_val) if instance_val.isdigit() else None

                obj, _created = RedcapInstanceToSubmissionMapping.objects.get_or_create(
                    questionnaire_submission=sub,
                    redcap_form=fm,
                )
                obj.redcap_patient_id = redcap_study_id
                obj.redcap_event_name = event_val or None
                obj.redcap_repeat_instance = instance_int
                obj.data_access_group = mapping.redcap_data_access_group_used and '' or None
                obj.save()
                saved_count += 1

        if saved_count > 0:
            messages.success(request, _('{count} submission match(es) saved.').format(count=saved_count))
        else:
            messages.info(request, _('No submissions were selected to save.'))
        return redirect('redcap_patient_ids', pk=pk, mapping_pk=mapping_pk)

    return render(request, 'patientapp/redcap/redcap_match_submissions.html', {
        'project': project,
        'mapping': mapping,
        'patient': patient,
        'redcap_study_id': redcap_study_id,
        'fm_data': fm_data,
    })


@login_required
def redcap_export(request, pk, mapping_pk):
    """Trigger a CSV download or API export for the selected form mappings."""
    guard = _staff_required(request)
    if guard:
        return guard
    project = get_object_or_404(Project, pk=pk)
    mapping = get_object_or_404(ProjectRedcapMapping, pk=mapping_pk, project=project)
    form_mappings = RedcapFormToQuestionnaireMapping.objects.filter(
        project_redcap_mapping=mapping
    ).prefetch_related('redcapfieldtoitemmapping_set__questionnaire_item__item')
    logs = RedcapDataExportLog.objects.filter(
        redcap_form_to_questionnaire_mapping__project_redcap_mapping=mapping
    ).select_related('patient', 'user_exporting_data').order_by('-created_at')[:50]

    # Build list of patients who have a study ID mapped — used for patient selection UI
    study_id_maps = list(
        RedcapStudyIDtoPatientIDMap.objects.filter(project_redcap_mapping=mapping)
        .select_related('patient')
    )
    mappable_patients = [
        {'patient': m.patient, 'redcap_study_id': m.redcap_study_id}
        for m in study_id_maps
        if m.redcap_study_id
    ]

    from promapp.models import QuestionnaireSubmission as _QS

    if request.method == 'POST':
        selected_fm_ids = request.POST.getlist('form_mapping_ids')
        selected_patient_pks = request.POST.getlist('patient_pks')
        export_type = request.POST.get('export_type', ExportTypeChoices.MANUAL)
        selected_fms = form_mappings.filter(pk__in=selected_fm_ids)

        full_id_map = {
            m.patient_id: m.redcap_study_id
            for m in study_id_maps
            if m.redcap_study_id
        }

        # Filter to only selected patients; if none explicitly chosen, export all mapped
        if selected_patient_pks:
            import uuid as _uuid
            selected_pks = set()
            for raw in selected_patient_pks:
                try:
                    selected_pks.add(_uuid.UUID(str(raw)))
                except (ValueError, AttributeError):
                    pass
            id_map = {pk: sid for pk, sid in full_id_map.items() if pk in selected_pks}
        else:
            id_map = full_id_map

        if not selected_fm_ids:
            messages.error(request, _('Please select at least one form mapping to export.'))
            return redirect(request.path)

        if not id_map:
            messages.error(request, _('No patients selected or no mapped patients found.'))
            return redirect(request.path)

        # Warn if any selected fm has no field mappings (export would produce empty rows)
        empty_fms = [fm for fm in selected_fms if not fm.redcapfieldtoitemmapping_set.exists()]
        if empty_fms:
            names = ', '.join(fm.redcap_form_name for fm in empty_fms)
            messages.warning(request, _(
                'The following form mappings have no field mappings configured and will produce empty rows: %(names)s'
            ) % {'names': names})

        # Note: Unmatched submissions (for repeating/event forms without instance mapping)
        # are automatically excluded from the export in _collect_export_rows()

        if export_type == ExportTypeChoices.MANUAL:
            return _build_csv_export(request, mapping, selected_fms, id_map)
        else:
            return _run_api_export(request, pk, mapping_pk, mapping, selected_fms, id_map)

    return render(request, 'patientapp/redcap/redcap_export.html', {
        'project': project,
        'mapping': mapping,
        'form_mappings': form_mappings,
        'mappable_patients': mappable_patients,
        'logs': logs,
        'ExportTypeChoices': ExportTypeChoices,
    })


_SUBMISSION_DATE_FORMATS = {
    'date_ymd': '%Y-%m-%d',
    'datetime_ymd': '%Y-%m-%d %H:%M',
    'datetime_seconds_ymd': '%Y-%m-%d %H:%M:%S',
}


def _apply_response_transform(raw, transform):
    """Coerce a raw response_value string to the format REDCap expects."""
    from patientapp.models import ResponseTransformChoices as _RT
    if raw is None or raw == '':
        return raw
    t = transform or _RT.NONE
    if t == _RT.NONE:
        return raw
    try:
        if t == _RT.TO_INT:
            return str(int(float(raw)))
        if t == _RT.ROUND_INT:
            return str(int(round(float(raw))))
        if t == _RT.TO_FLOAT:
            return str(float(raw))
        if t == _RT.TO_FLOAT_2:
            return f'{float(raw):.2f}'
        if t == _RT.STRIP_ZEROS:
            f = float(raw)
            # Remove trailing zeros: format to enough precision then strip
            result = f'{f:.10f}'.rstrip('0').rstrip('.')
            return result
    except (ValueError, TypeError):
        pass
    return raw


def _collect_export_rows(mapping, selected_fms, id_map):
    """Build list of dicts for REDCap import (wide format, one row per submission)."""
    from promapp.models import QuestionnaireSubmission, QuestionnaireItemResponse
    rows = []
    for fm in selected_fms:
        field_maps = list(fm.redcapfieldtoitemmapping_set.select_related('questionnaire_item'))
        if not field_maps:
            continue
        submissions = QuestionnaireSubmission.objects.filter(
            patient_questionnaire__questionnaire=fm.questionnaire,
            patient__in=id_map.keys(),
        ).select_related('patient', 'patient_questionnaire').order_by('patient', 'submission_date')

        # Pre-fetch per-submission instance mappings for this form mapping.
        # Key: questionnaire_submission_id → RedcapInstanceToSubmissionMapping obj
        instance_map = {
            obj.questionnaire_submission_id: obj
            for obj in RedcapInstanceToSubmissionMapping.objects.filter(
                redcap_form=fm,
                questionnaire_submission__in=submissions,
            )
        }

        date_fmt = _SUBMISSION_DATE_FORMATS.get(fm.submission_date_format) if fm.submission_date_format else None

        for sub in submissions:
            study_id = id_map.get(sub.patient_id)
            if not study_id:
                continue
            row = {mapping.redcap_study_id_field or 'record_id': study_id}

            inst_mapping = instance_map.get(sub.pk)

            event_name = None
            if fm.redcap_form_is_in_event:
                event_name = (
                    inst_mapping.redcap_event_name
                    if inst_mapping and inst_mapping.redcap_event_name
                    else fm.redcap_event_name
                )
                if event_name:
                    row['redcap_event_name'] = event_name

            if fm.redcap_form_is_repeating or fm.redcap_event_is_repeating:
                # Determine per-submission whether the instrument or the event is repeating,
                # using project_info['repeating'] keyed against this submission's event.
                _repeating_list = (mapping.redcap_project_info or {}).get('repeating', [])
                if _repeating_list and event_name:
                    _repeating_instruments = {
                        (e.get('event_name', '').strip(), e.get('form_name', '').strip())
                        for e in _repeating_list if e.get('form_name', '').strip()
                    }
                    _repeating_events = {
                        e.get('event_name', '').strip()
                        for e in _repeating_list if not e.get('form_name', '').strip()
                    }
                    _instrument_repeats = (event_name, fm.redcap_form_name) in _repeating_instruments
                    _event_repeats = event_name in _repeating_events
                else:
                    # No project-info data or no event context — fall back to fm flags
                    _instrument_repeats = fm.redcap_form_is_repeating
                    _event_repeats = fm.redcap_event_is_repeating

                _instance_val = (
                    inst_mapping.redcap_repeat_instance
                    if inst_mapping and inst_mapping.redcap_repeat_instance is not None
                    else ''
                )

                if _instrument_repeats:
                    # Repeating instrument: both fields populated
                    row['redcap_repeat_instrument'] = fm.redcap_form_name
                    row['redcap_repeat_instance'] = _instance_val
                elif _event_repeats:
                    # Repeating event: instrument field is blank, instance still required
                    row['redcap_repeat_instrument'] = ''
                    row['redcap_repeat_instance'] = _instance_val
                else:
                    # Non-repeating in this event (mixed project): both fields blank
                    row['redcap_repeat_instrument'] = ''
                    row['redcap_repeat_instance'] = ''

            # Skip submissions that require instance mapping but don't have one
            # (This filters out unmatched submissions for repeating/event forms)
            _is_repeating = fm.redcap_form_is_repeating or fm.redcap_event_is_repeating
            _is_in_event = fm.redcap_form_is_in_event
            if (_is_repeating or _is_in_event) and inst_mapping is None:
                continue

            if fm.submission_date_field and date_fmt and sub.submission_date:
                row[fm.submission_date_field] = sub.submission_date.strftime(date_fmt)

            responses = {
                r.questionnaire_item_id: r.response_value
                for r in QuestionnaireItemResponse.objects.filter(questionnaire_submission=sub)
            }
            for fm_field in field_maps:
                raw = responses.get(fm_field.questionnaire_item_id, '')
                row[fm_field.redcap_field_name] = _apply_response_transform(raw, fm_field.response_transform)
            rows.append(row)
    return rows


def _build_csv_export(request, mapping, selected_fms, id_map):
    """Return a CSV HttpResponse and log the export."""
    rows = _collect_export_rows(mapping, selected_fms, id_map)
    if not rows:
        messages.warning(request, _('No data found for the selected form mappings.'))
        return redirect(request.path)

    all_keys = []
    seen = set()
    for row in rows:
        for k in row:
            if k not in seen:
                all_keys.append(k)
                seen.add(k)

    response = HttpResponse(content_type='text/csv')
    filename = f'redcap_export_{mapping.project.project_name}.csv'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    writer = csv.DictWriter(response, fieldnames=all_keys, extrasaction='ignore')
    writer.writeheader()
    writer.writerows(rows)

    # Log one entry per patient per fm
    from promapp.models import QuestionnaireSubmission as _QS
    patient_map = {p.pk: p for p in Patient.objects.filter(pk__in=id_map.keys())}
    now = timezone.now()
    log_entries = []
    for fm in selected_fms:
        if not fm.redcapfieldtoitemmapping_set.exists():
            continue
        # Only log for patients who actually have submissions for this fm
        patient_ids_with_subs = set(
            _QS.objects.filter(
                patient_questionnaire__questionnaire=fm.questionnaire,
                patient__in=id_map.keys(),
            ).values_list('patient_id', flat=True)
        )
        for patient_id in patient_ids_with_subs:
            patient = patient_map.get(patient_id)
            log_entries.append(RedcapDataExportLog(
                redcap_form_to_questionnaire_mapping=fm,
                patient=patient,
                user_exporting_data=request.user,
                export_type=ExportTypeChoices.MANUAL,
                datetime_export_start=now,
                datetime_export_completed=now,
                export_status=ExportStatusChoices.COMPLETED,
                export_log=f'CSV export: {filename}',
            ))
    RedcapDataExportLog.objects.bulk_create(log_entries)

    return response


def _run_api_export(request, pk, mapping_pk, mapping, selected_fms, id_map):
    """Export via REDCap API using PyCap and log results."""
    rows = _collect_export_rows(mapping, selected_fms, id_map)
    if not rows:
        messages.warning(request, _('No data found for the selected form mappings.'))
        return redirect(request.path)

    from promapp.models import QuestionnaireSubmission as _QS
    patient_map = {p.pk: p for p in Patient.objects.filter(pk__in=id_map.keys())}
    for fm in selected_fms:
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
            fm_rows = [r for r in rows if fm.redcap_form_name in r.get('redcap_repeat_instrument', fm.redcap_form_name)]
            response_data = redcap_import_records(mapping, fm_rows)
            final_status = ExportStatusChoices.COMPLETED
            log_text = str(response_data)
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

