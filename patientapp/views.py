from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.models import User
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.utils.translation import gettext_lazy as _, gettext, get_language
from django.db import transaction
from django.db.models import Q, Count, Max
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.http import JsonResponse
from .models import Patient, Diagnosis, DiagnosisList, Treatment, Institution, GenderChoices, TreatmentType, TreatmentIntentChoices
from .forms import PatientForm, TreatmentForm, DiagnosisForm, PatientRestrictedUpdateForm
from promapp.models import *
from .utils import ConstructScoreData, calculate_percentage, create_item_response_plot, get_patient_start_date, get_patient_available_start_dates, filter_positive_intervals, filter_positive_intervals_construct, get_interval_label, calculate_time_interval_value
import logging
from bokeh.resources import CDN

logger = logging.getLogger(__name__)

# Create your views here.


def prom_review(request, pk):
    """View for the PRO Review page that shows patient questionnaire responses.
    Supports global filtering for all sections of the page.
    """
    logger.info(f"PRO Review view called for patient ID: {pk}")
    
    patient = get_object_or_404(Patient, pk=pk)
    logger.info(f"Found patient: {patient.name} (ID: {patient.id})")
    
    # Get filter parameters
    questionnaire_filter = request.GET.get('questionnaire_filter')
    submission_date = request.GET.get('submission_date')
    time_range = request.GET.get('time_range', '5')
    item_filter = request.GET.getlist('item_filter')  # Get list of selected item IDs
    start_date_reference = request.GET.get('start_date_reference', 'date_of_registration')
    time_interval = request.GET.get('time_interval', 'weeks')
    
    # Get aggregation parameters - aggregation is now always enabled
    show_aggregated = True  # Always show aggregated data
    aggregation_type = request.GET.get('aggregation_type', 'median_iqr')
    patient_filter_gender = request.GET.get('patient_filter_gender')
    patient_filter_diagnosis = request.GET.get('patient_filter_diagnosis')
    patient_filter_treatment = request.GET.get('patient_filter_treatment')
    
    logger.info(f"Aggregation settings: show_aggregated={show_aggregated}, type={aggregation_type}, gender={patient_filter_gender}, diagnosis={patient_filter_diagnosis}, treatment={patient_filter_treatment}")
    
    # Always get aggregated patients to show patient counts, regardless of whether aggregation is enabled
    from patientapp.utils import get_filtered_patients_for_aggregation
    aggregated_patients = get_filtered_patients_for_aggregation(
        exclude_patient=patient,
        patient_filter_gender=patient_filter_gender,
        patient_filter_diagnosis=patient_filter_diagnosis,
        patient_filter_treatment=patient_filter_treatment
    )
    logger.info(f"Found {aggregated_patients.count()} patients for aggregation (aggregation enabled: {show_aggregated})")
    
    # Get submission count from time range or default to 5
    # This count needs to respect the submission_date filter if active.
    
    # Base query for counting submissions, respecting patient and potentially date filter
    submission_count_base_query = QuestionnaireSubmission.objects.filter(patient=patient)
    if submission_date: # The global submission_date filter from request.GET
        submission_count_base_query = submission_count_base_query.filter(submission_date__date__lte=submission_date)

    if time_range == 'all':
        submission_count = submission_count_base_query.count()
        # If count is 0 (e.g. no submissions up to filter date, or no submissions at all), plot will be empty.
    else:
        submission_count = int(time_range)
        # Ensure submission_count doesn't exceed available submissions after date filter
        # (or total submissions if no date filter)
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
    
    # Apply submission date filter if specified
    if submission_date:
        submissions = submissions.filter(submission_date__date__lte=submission_date)
    
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
    assigned_questionnaires = PatientQuestionnaire.objects.filter(
        patient=patient
    ).select_related(
        'questionnaire'
    ).prefetch_related(
        'questionnaire__translations'
    )
    
    # Apply questionnaire filter to assigned questionnaires if specified
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
        'questionnaire_item__item__range_response'
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
    
    # Calculate percentages and add option text for item responses
    for response in item_responses:
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
                max_value = response.questionnaire_item.item.likert_response.likertscaleresponseoption_set.aggregate(
                    max_value=Max('option_value')
                )['max_value']
                response.percentage = calculate_percentage(likert_value, max_value)
                
                likert_scale = response.questionnaire_item.item.likert_response
                better_direction = response.questionnaire_item.item.item_better_score_direction or 'Higher is Better'
                color_map = likert_scale.get_option_colors(better_direction)
                for option in likert_scale.likertscaleresponseoption_set.all():
                    if str(option.option_value) == response.response_value:
                        response.option_text = option.option_text
                        response.option_color = color_map.get(str(option.option_value), '#ffffff')
                        response.text_color = likert_scale.get_text_color(response.option_color)
                        break
            except (ValueError, TypeError) as e_likert_proc:
                logger.error(f"Error processing Likert item {response.questionnaire_item.item.id} (Response ID {response.id}): {e_likert_proc}", exc_info=True)
                response.likert_response = None
                response.percentage = 0
        
        # Common: Get previous response for change calculation (for both Numeric and Likert)
        response.previous_value = None
        response.value_change = None
        if current_value_for_change_calc is not None:
            previous_response_obj = QuestionnaireItemResponse.objects.filter(
                questionnaire_item=response.questionnaire_item,
                questionnaire_submission__patient=patient,
                questionnaire_submission__submission_date__lt=response.questionnaire_submission.submission_date
            ).order_by('-questionnaire_submission__submission_date').first()

            if previous_response_obj and previous_response_obj.response_value:
                try:
                    previous_value_float = float(previous_response_obj.response_value)
                    response.previous_value = previous_value_float
                    response.value_change = current_value_for_change_calc - previous_value_float
                except (ValueError, TypeError):
                    logger.warning(f"Could not parse previous value for item {response.questionnaire_item.item.id} (Response ID {response.id})")

        # Common: Get historical responses for plotting (for both Numeric and Likert)
        try:
            # Fetch historical responses for the plot, respecting submission_date filter
            base_item_historical_qs = QuestionnaireItemResponse.objects.filter(
                questionnaire_item=response.questionnaire_item,
                questionnaire_submission__patient=patient
            )

            if submission_date: # Apply the global submission_date filter
                base_item_historical_qs = base_item_historical_qs.filter(
                    questionnaire_submission__submission_date__date__lte=submission_date
                )
            
            # Get the 'submission_count' most recent responses within the (optional) date filter.
            # Bokeh plotting functions in utils.py use reversed(historical_responses),
            # so historical_responses should be in descending order (latest first) here.
            historical_responses_for_plot = list(
                base_item_historical_qs.select_related(
                    'questionnaire_submission'
                ).order_by('-questionnaire_submission__submission_date')[:submission_count]
            )
            
            # Filter out responses with negative time intervals
            start_date = get_patient_start_date(patient, start_date_reference)
            if start_date:
                historical_responses_for_plot = filter_positive_intervals(
                    historical_responses_for_plot, start_date, time_interval
                )
            
            logger.debug(f"Item {response.questionnaire_item.item.id} (Response ID {response.id}): Found {len(historical_responses_for_plot)} historical responses for plot after filtering (submission_count: {submission_count}, submission_date_filter: {submission_date}).")

            if historical_responses_for_plot:
                response.bokeh_plot = create_item_response_plot(
                    historical_responses_for_plot, # Pass the filtered and sliced list
                    response.questionnaire_item.item,
                    patient,
                    start_date_reference,
                    time_interval
                )
                if not response.bokeh_plot:
                    logger.warning(f"Item {response.questionnaire_item.item.id} (Response ID {response.id}): create_item_response_plot returned None or empty string.")
            else:
                logger.info(f"Item {response.questionnaire_item.item.id} (Response ID {response.id}): No historical responses to plot after filtering, setting bokeh_plot to None.")
        except Exception as e_plot_gen:
            logger.error(f"Error generating plot for item {response.questionnaire_item.item.id} (Response ID {response.id}): {e_plot_gen}", exc_info=True)
    
    logger.info(f"Found {item_responses.count()} item responses")
    
    # Get construct scores for the latest submissions
    construct_scores = QuestionnaireConstructScore.objects.filter(
        questionnaire_submission__in=latest_submissions.values()
    ).select_related(
        'construct'
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
        'composite_construct_scale'
    )
    
    # Apply questionnaire filter to composite construct scores if specified
    if questionnaire_filter:
        composite_construct_scores = composite_construct_scores.filter(
            questionnaire_submission__patient_questionnaire__questionnaire_id=questionnaire_filter
        )
    
    logger.info(f"Found {composite_construct_scores.count()} composite construct scores")

    # Add historical data to construct scores
    for construct_score in construct_scores:
        # Get previous score for change calculation
        previous_score_obj = QuestionnaireConstructScore.objects.filter(
            questionnaire_submission__patient=patient,
            construct=construct_score.construct,
            questionnaire_submission__submission_date__lt=construct_score.questionnaire_submission.submission_date
        ).order_by('-questionnaire_submission__submission_date').first()
        
        construct_score.previous_score = previous_score_obj.score if previous_score_obj else None
        construct_score.score_change = None
        if construct_score.score is not None and construct_score.previous_score is not None:
            construct_score.score_change = construct_score.score - construct_score.previous_score

    # Add historical data to composite construct scores
    for composite_score in composite_construct_scores:
        # Get previous composite score for change calculation
        previous_composite_obj = QuestionnaireConstructScoreComposite.objects.filter(
            questionnaire_submission__patient=patient,
            composite_construct_scale=composite_score.composite_construct_scale,
            questionnaire_submission__submission_date__lt=composite_score.questionnaire_submission.submission_date
        ).order_by('-questionnaire_submission__submission_date').first()
        
        composite_score.previous_score = previous_composite_obj.score if previous_composite_obj else None
        composite_score.score_change = None
        if composite_score.score is not None and composite_score.previous_score is not None:
            composite_score.score_change = composite_score.score - composite_score.previous_score

    # Get important construct scores
    important_construct_scores = []
    logger.info("Processing construct scores to find important ones...")
    
    # Log plotting session start
    from patientapp.utils import log_plotting_session_start
    log_plotting_session_start(patient.name, construct_scores.count())
    
    for construct_score in construct_scores:
        construct = construct_score.construct
        logger.info(f"Processing construct: {construct.name}")
        
        # Get historical scores for this construct's plot, respecting submission_date filter
        base_construct_historical_qs = QuestionnaireConstructScore.objects.filter(
            questionnaire_submission__patient=patient,
            construct=construct
        )

        if submission_date: # Apply the global submission_date filter
            base_construct_historical_qs = base_construct_historical_qs.filter(
                questionnaire_submission__submission_date__date__lte=submission_date
            )

        # Get the 'submission_count' most recent scores within the (optional) date filter.
        # ConstructScoreData._create_bokeh_plot in utils.py also uses reversed(historical_scores).
        historical_scores_for_plot = list(
            base_construct_historical_qs.select_related(
                'questionnaire_submission'
            ).order_by('-questionnaire_submission__submission_date')[:submission_count]
        )
        
        # Filter out scores with negative time intervals
        start_date = get_patient_start_date(patient, start_date_reference)
        if start_date:
            historical_scores_for_plot = filter_positive_intervals_construct(
                historical_scores_for_plot, start_date, time_interval
            )
        
        logger.debug(f"Found {len(historical_scores_for_plot)} historical scores for {construct.name} plot after filtering (submission_count: {submission_count}, submission_date_filter: {submission_date}).")

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
                        start_date,
                        time_interval
                    )
                    if interval_value not in reference_intervals:
                        reference_intervals.append(interval_value)
                
                # Sort reference intervals
                reference_intervals.sort()
                
                # Aggregate data from other patients using index patient's time intervals as reference
                aggregated_data, aggregation_metadata = aggregate_construct_scores_by_time_interval(
                    construct=construct,
                    patients_queryset=aggregated_patients,
                    start_date_reference=start_date_reference,
                    time_interval=time_interval,
                    submission_date_filter=submission_date,
                    reference_time_intervals=reference_intervals
                )
                
                # Calculate statistics
                aggregated_statistics = calculate_aggregation_statistics(
                    aggregated_data, aggregation_type
                )
                
                logger.debug(f"Construct {construct.name}: Generated aggregated statistics for {len(aggregated_statistics)} intervals")
                
            except Exception as e:
                logger.error(f"Error calculating aggregated data for construct {construct.name}: {e}")

        # Create construct score data object
        score_data = ConstructScoreData(
            construct=construct, # construct_score.construct
            current_score=construct_score.score, # This is from the main construct_scores list, respecting filters for card display
            previous_score=previous_score_for_plot_context, # Previous score in the context of the plot data
            historical_scores=historical_scores_for_plot, # Filtered and sliced list for the plot
            patient=patient,
            start_date_reference=start_date_reference,
            time_interval=time_interval,
            aggregated_statistics=aggregated_statistics,  # Pass aggregated statistics
            aggregation_metadata=aggregation_metadata  # Pass aggregation metadata
        )

        # Only include if it's an important construct
        if ConstructScoreData.is_important_construct(construct, construct_score.score):
            logger.info(f"Adding {construct.name} to important constructs")
            important_construct_scores.append(score_data)
        else:
            logger.info(f"{construct.name} not marked as important")
    
    logger.info(f"Found {len(important_construct_scores)} important construct scores")
    
    # Filter out important construct scores from the main construct_scores list
    # to avoid duplication between topline results and construct scores section
    important_construct_ids = {score_data.construct.id for score_data in important_construct_scores}
    other_construct_scores = [cs for cs in construct_scores if cs.construct.id not in important_construct_ids]
    
    logger.info(f"Found {len(other_construct_scores)} other construct scores (excluding important ones)")
    
    # Get Bokeh resources
    bokeh_css = CDN.render_css()
    bokeh_js = CDN.render_js()
    
    # Get available items for the filter (based on current questionnaire filter)
    available_items_query = Item.objects.select_related('construct_scale').prefetch_related('translations')
    
    if questionnaire_filter:
        # Get items from the selected questionnaire
        available_items_query = available_items_query.filter(
            questionnaireitem__questionnaire_id=questionnaire_filter
        ).distinct()
    else:
        # Get items from all assigned questionnaires
        questionnaire_ids = assigned_questionnaires.values_list('questionnaire_id', flat=True)
        available_items_query = available_items_query.filter(
            questionnaireitem__questionnaire_id__in=questionnaire_ids
        ).distinct()
    
    available_items = available_items_query.order_by('construct_scale__name', 'item_number')
    
    # Get selected item details for proper initialization
    selected_items_data = []
    if item_filter:
        selected_items = Item.objects.filter(id__in=item_filter).prefetch_related('translations')
        selected_items_data = [{'id': str(item.id), 'name': item.name} for item in selected_items]

    # Prepare options for Cotton dropdowns
    questionnaire_options_for_cotton = [
        {'id': str(pq.questionnaire.id), 'name': pq.questionnaire.name}
        for pq in assigned_questionnaires  # Use the already filtered or full list
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
                        start_date = get_patient_start_date(patient, start_date_reference)
                        
                        if start_date and hasattr(first_construct, 'aggregated_statistics') and first_construct.aggregated_statistics:
                            # Get reference intervals from this construct
                            reference_intervals = sorted(list(first_construct.aggregated_statistics.keys()))
                            if reference_intervals:
                                # Get fresh metadata with patient details
                                _, metadata_with_details = aggregate_construct_scores_by_time_interval(
                                    construct=first_construct.construct,
                                    patients_queryset=aggregated_patients,
                                    start_date_reference=start_date_reference,
                                    time_interval=time_interval,
                                    submission_date_filter=submission_date,
                                    reference_time_intervals=reference_intervals
                                )
                                if 'patient_details' in metadata_with_details:
                                    all_patient_details = metadata_with_details['patient_details']
                                    found_patient_details = True
                                    
                                    logger.info(f"Successfully retrieved patient details: {len(all_patient_details['contributing'])} contributing, {len(all_patient_details['non_contributing'])} non-contributing")
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
        'assigned_questionnaires': assigned_questionnaires, # Still needed for other parts of the template
        'item_responses': item_responses,
        'construct_scores': construct_scores,
        'other_construct_scores': other_construct_scores,
        'composite_construct_scores': composite_construct_scores,
        'questionnaire_submission_counts': questionnaire_submission_counts,
        'important_construct_scores': important_construct_scores,
        'available_items': available_items,
        'selected_items_data': selected_items_data,
        'bokeh_css': bokeh_css,
        'bokeh_js': bokeh_js,
        'questionnaire_options_for_cotton': questionnaire_options_for_cotton,
        'time_range_options_for_cotton': time_range_options_for_cotton,
        'selected_time_range_for_cotton': selected_time_range_for_cotton,
        'available_start_dates': available_start_dates,
        'available_diagnoses': available_diagnoses,
        'available_treatment_types': available_treatment_types,
        'aggregation_metadata': aggregation_metadata,
    }
    
    # If this is an HTMX request, only return the main content section
    if request.headers.get('HX-Request'):
        return render(request, 'promapp/components/main_content.html', context)
    
    return render(request, 'promapp/prom_review.html', context)


def prom_review_item_search(request, pk):
    """HTMX endpoint for searching items in the item filter autocomplete."""
    patient = get_object_or_404(Patient, pk=pk)
    search_query = request.GET.get('item-filter-search', '').strip()
    questionnaire_filter = request.GET.get('questionnaire_filter')
    
    # Get available items based on questionnaire filter
    items_query = Item.objects.select_related('construct_scale').prefetch_related('translations')
    
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
    items = items_query.order_by('construct_scale__name', 'item_number')[:20]
    
    context = {
        'items': items,
        'search_query': search_query,
    }
    
    return render(request, 'promapp/partials/item_search_results.html', context)


def patient_list(request):
    # Get filter parameters
    name_search = request.GET.get('name_search', '')
    id_search = request.GET.get('id_search', '')
    institution_id = request.GET.get('institution', '')
    gender = request.GET.get('gender', '')
    diagnosis = request.GET.get('diagnosis', '')
    treatment_type = request.GET.get('treatment_type', '')
    questionnaire_count = request.GET.get('questionnaire_count', '')
    sort_by = request.GET.get('sort', 'name')
    
    # Start with base queryset
    patients = Patient.objects.select_related('user', 'institution').all()
    
    # Apply filters
    if name_search:
        patients = patients.filter(name__exact=name_search)
    
    if id_search:
        patients = patients.filter(patient_id__exact=id_search)
    
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
    
    # Get all institutions for the filter dropdown
    institutions = Institution.objects.all()
    
    # Get gender choices for the filter dropdown
    gender_choices = GenderChoices.choices
    
    # Get unique diagnoses for the filter dropdown
    diagnoses = list(DiagnosisList.objects.values_list('diagnosis', flat=True).distinct().exclude(diagnosis__isnull=True).exclude(diagnosis=''))
    
    # Get unique treatment types for the filter dropdown
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

def patient_detail(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
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

class PatientCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Patient
    form_class = PatientForm
    template_name = 'patientapp/patient_form.html'
    success_url = reverse_lazy('patient_questionnaire_list')
    permission_required = 'patientapp.add_patient'

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

class PatientRestrictedUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Patient
    form_class = PatientRestrictedUpdateForm
    template_name = 'patientapp/patient_restricted_update_form.html'
    permission_required = 'patientapp.change_patient' # Or a more specific permission

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('Edit Patient Details')
        return context

    def form_valid(self, form):
        try:
            with transaction.atomic():
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
        context['patient'] = get_object_or_404(Patient, pk=self.kwargs['patient_pk'])
        context['title'] = _('Add Diagnosis')
        return context

    def form_valid(self, form):
        form.instance.patient = get_object_or_404(Patient, pk=self.kwargs['patient_pk'])
        messages.success(self.request, _('Diagnosis added successfully.'))
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('patient_detail', kwargs={'pk': self.kwargs['patient_pk']})

class DiagnosisUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Diagnosis
    form_class = DiagnosisForm
    template_name = 'patientapp/diagnosis_form.html'
    permission_required = 'patientapp.change_diagnosis'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('Edit Diagnosis')
        context['patient'] = self.object.patient # Pass patient to context for the cancel button
        return context

    def get_success_url(self):
        return reverse('patient_detail', kwargs={'pk': self.object.patient.pk})

# DiagnosisDeleteView removed as per request to restrict delete to admin only.

# Treatment Views
class TreatmentCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Treatment
    form_class = TreatmentForm
    template_name = 'patientapp/treatment_form.html'
    permission_required = 'patientapp.add_treatment'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['diagnosis'] = get_object_or_404(Diagnosis, pk=self.kwargs['diagnosis_pk'])
        context['treatment_types'] = TreatmentType.objects.all()
        context['treatment_intents'] = TreatmentIntentChoices.choices
        context['title'] = _('Add Treatment')
        return context

    def form_valid(self, form):
        form.instance.diagnosis = get_object_or_404(Diagnosis, pk=self.kwargs['diagnosis_pk'])
        messages.success(self.request, _('Treatment added successfully.'))
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('patient_detail', kwargs={'pk': self.object.diagnosis.patient.pk})

class TreatmentUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Treatment
    form_class = TreatmentForm
    template_name = 'patientapp/treatment_form.html'
    permission_required = 'patientapp.change_treatment'

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






