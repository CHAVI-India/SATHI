# Django imports
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponse, Http404
from django.views.generic import DetailView, TemplateView
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required, permission_required
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from django.db.models import Q, Count, Max, Min, Avg, Prefetch
from django.core.paginator import Paginator
from django.utils import timezone
from django.core.exceptions import PermissionDenied
from datetime import datetime, timedelta
import json
from decimal import Decimal
import logging

# Setup logger
logger = logging.getLogger(__name__)

# Local imports
from .models import (
    QuestionnaireSubmission, 
    QuestionnaireConstructScore, 
    QuestionnaireItemResponse,
    ConstructScale,
    Item,
    Questionnaire,
    QuestionnaireItem,
    PatientQuestionnaire,
    LikertScaleResponseOption,
    DirectionChoices,
    ResponseTypeChoices
)
from patientapp.models import Patient, Diagnosis, Treatment


def check_patient_access(user, patient):
    """
    Check if the user has permission to access this patient's data.
    This should be customized based on your authorization model.
    """
    # Basic checks - customize based on your requirements
    if not user.is_authenticated:
        return False
    
    # Superusers can access all patients
    if user.is_superuser:
        return True
    
    # Check if user has general permission to view patient data
    if not user.has_perm('patientapp.view_patient'):
        return False
    
    # Add your specific business logic here, for example:
    # - Check if user is assigned to this patient
    # - Check if user belongs to the same organization/clinic
    # - Check if user has role-based access
    
    # For now, we'll allow access if user has the basic permission
    # You should replace this with your actual authorization logic
    return True


def validate_submission_count(submission_count):
    """Validate and sanitize submission count parameter."""
    try:
        count = int(submission_count)
        # Limit to reasonable range to prevent performance issues
        if count < 1:
            return 5  # Default
        elif count > 50:  # Maximum limit
            return 50
        return count
    except (ValueError, TypeError):
        return 5  # Default


@method_decorator(login_required, name='dispatch')
@method_decorator(permission_required('patientapp.view_patient', raise_exception=True), name='dispatch')
class HCPResultView(DetailView):
    """
    Main view for Healthcare Provider Result UI.
    Displays comprehensive patient reported outcome results.
    """
    model = Patient
    template_name = 'promapp/hcp_result_ui.html'
    context_object_name = 'patient'
    pk_url_kwarg = 'patient_id'
    
    def get_object(self, queryset=None):
        """Override to add authorization check."""
        patient = super().get_object(queryset)
        
        # Check if user has access to this patient
        if not check_patient_access(self.request.user, patient):
            logger.warning(f"Unauthorized access attempt to patient {patient.id} by user {self.request.user.id}")
            raise PermissionDenied("You don't have permission to access this patient's data.")
        
        return patient
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        patient = self.get_object()
        
        # Get selected submission date from query params (default to latest)
        selected_submission_date = self.request.GET.get('submission_date')
        selected_questionnaire_id = self.request.GET.get('questionnaire_id')
        submission_count = validate_submission_count(self.request.GET.get('submission_count', 5))
        
        # Get patient questionnaires and submissions
        patient_questionnaires = PatientQuestionnaire.objects.filter(
            patient=patient,
            display_questionnaire=True
        ).select_related('questionnaire')
        
        # Get all submissions for this patient
        submissions = QuestionnaireSubmission.objects.filter(
            patient=patient
        ).select_related('patient_questionnaire__questionnaire').order_by('-submission_date')
        
        # Filter by questionnaire if specified
        if selected_questionnaire_id:
            submissions = submissions.filter(
                patient_questionnaire__questionnaire_id=selected_questionnaire_id
            )
        
        # Get the selected submission or default to latest
        if selected_submission_date:
            try:
                selected_submission = submissions.filter(
                    submission_date__date=datetime.strptime(selected_submission_date, '%Y-%m-%d').date()
                ).first()
            except ValueError:
                selected_submission = submissions.first()
        else:
            selected_submission = submissions.first()
        
        # Get patient diagnoses and treatments
        diagnoses = Diagnosis.objects.filter(patient=patient)
        treatments = Treatment.objects.filter(diagnosis__patient=patient).order_by('-date_of_start_of_treatment')
        
        # Get questionnaire overview data
        questionnaire_overview = self._get_questionnaire_overview(patient, patient_questionnaires, submissions)
        
        # Get construct scores and important constructs for selected submission
        important_constructs = []
        construct_scores = []
        if selected_submission:
            construct_scores = self._get_construct_scores(selected_submission, submission_count)
            important_constructs = self._get_important_constructs(selected_submission, submission_count)
        
        # Get item-wise results grouped by construct
        item_results = self._get_item_results(selected_submission, submission_count) if selected_submission else []
        
        context.update({
            'diagnoses': diagnoses,
            'treatments': treatments,
            'patient_questionnaires': patient_questionnaires,
            'questionnaire_overview': questionnaire_overview,
            'submissions': submissions[:10],  # Limit for dropdown
            'selected_submission': selected_submission,
            'selected_submission_date': selected_submission_date,
            'selected_questionnaire_id': selected_questionnaire_id,
            'submission_count': submission_count,
            'important_constructs': important_constructs,
            'construct_scores': construct_scores,
            'item_results': item_results,
        })
        
        return context
    
    def _get_questionnaire_overview(self, patient, patient_questionnaires, submissions):
        """Get overview data for each questionnaire available to the patient."""
        overview_data = []
        
        for pq in patient_questionnaires:
            questionnaire_submissions = submissions.filter(
                patient_questionnaire=pq
            )
            
            submission_count = questionnaire_submissions.count()
            last_submission = questionnaire_submissions.first()
            
            overview_data.append({
                'questionnaire': pq.questionnaire,
                'patient_questionnaire': pq,
                'submission_count': submission_count,
                'last_submission_date': last_submission.submission_date if last_submission else None,
                'last_submission': last_submission,
            })
        
        return overview_data
    
    def _get_construct_scores(self, submission, submission_count):
        """Get construct scores for the submission with historical data."""
        construct_scores = QuestionnaireConstructScore.objects.filter(
            questionnaire_submission=submission
        ).select_related('construct')
        
        # Add historical data for each construct
        for score in construct_scores:
            score.historical_data = self._get_construct_historical_data(
                submission.patient,
                score.construct,
                submission_count
            )
            score.previous_score = self._get_previous_construct_score(
                submission.patient,
                score.construct,
                submission.submission_date
            )
        
        return construct_scores
    
    def _get_important_constructs(self, submission, submission_count):
        """
        Identify important constructs based on threshold and normative scores.
        Returns constructs that need clinical attention.
        """
        construct_scores = QuestionnaireConstructScore.objects.filter(
            questionnaire_submission=submission,
            score__isnull=False
        ).select_related('construct')
        
        logger.debug(f"Found {construct_scores.count()} construct scores for submission {submission.id}")
        
        important_constructs = []
        
        for score in construct_scores:
            construct = score.construct
            current_score = score.score
            is_important = False
            importance_reason = ""
            
            logger.debug(f"Evaluating construct '{construct.name}': score={current_score}, "
                        f"threshold={construct.scale_threshold_score}, "
                        f"normative_mean={construct.scale_normative_score_mean}, "
                        f"normative_sd={construct.scale_normative_score_standard_deviation}, "
                        f"direction={construct.scale_better_score_direction}")
            
            # Check threshold score criteria
            if construct.scale_threshold_score is not None:
                if construct.scale_better_score_direction == DirectionChoices.HIGHER_IS_BETTER:
                    if current_score <= construct.scale_threshold_score:
                        is_important = True
                        if current_score == construct.scale_threshold_score:
                            importance_reason = f"At threshold ({construct.scale_threshold_score})"
                        else:
                            importance_reason = f"Below threshold ({construct.scale_threshold_score})"
                elif construct.scale_better_score_direction == DirectionChoices.LOWER_IS_BETTER:
                    if current_score >= construct.scale_threshold_score:
                        is_important = True
                        if current_score == construct.scale_threshold_score:
                            importance_reason = f"At threshold ({construct.scale_threshold_score})"
                        else:
                            importance_reason = f"Above threshold ({construct.scale_threshold_score})"
                
                logger.debug(f"Threshold check for '{construct.name}': is_important={is_important}, reason='{importance_reason}'")
            
            # Check normative score criteria if no threshold or as additional check
            elif construct.scale_normative_score_mean is not None:
                normative_mean = construct.scale_normative_score_mean
                normative_sd = construct.scale_normative_score_standard_deviation
                
                if normative_sd is not None:
                    # Use 0.5 SD as criteria
                    threshold_value = normative_sd * Decimal('0.5')
                    if construct.scale_better_score_direction == DirectionChoices.HIGHER_IS_BETTER:
                        if current_score <= (normative_mean - threshold_value):
                            is_important = True
                            importance_reason = f"Below normative range"
                    elif construct.scale_better_score_direction == DirectionChoices.LOWER_IS_BETTER:
                        if current_score >= (normative_mean + threshold_value):
                            is_important = True
                            importance_reason = f"Above normative range"
                else:
                    # Just use normative mean
                    if construct.scale_better_score_direction == DirectionChoices.HIGHER_IS_BETTER:
                        if current_score <= normative_mean:
                            is_important = True
                            importance_reason = f"Below normative mean ({normative_mean})"
                    elif construct.scale_better_score_direction == DirectionChoices.LOWER_IS_BETTER:
                        if current_score >= normative_mean:
                            is_important = True
                            importance_reason = f"Above normative mean ({normative_mean})"
                
                logger.debug(f"Normative check for '{construct.name}': is_important={is_important}, reason='{importance_reason}'")
            else:
                logger.debug(f"No threshold or normative criteria configured for '{construct.name}'")
            
            if is_important:
                # Add historical data and previous score
                score.historical_data = self._get_construct_historical_data(
                    submission.patient,
                    construct,
                    submission_count
                )
                score.previous_score = self._get_previous_construct_score(
                    submission.patient,
                    construct,
                    submission.submission_date
                )
                score.importance_reason = importance_reason
                important_constructs.append(score)
                logger.debug(f"Added '{construct.name}' to important constructs")
        
        logger.debug(f"Total important constructs: {len(important_constructs)}")
        return important_constructs
    
    def _get_construct_historical_data(self, patient, construct, submission_count):
        """Get historical construct scores for plotting."""
        historical_scores = QuestionnaireConstructScore.objects.filter(
            questionnaire_submission__patient=patient,
            construct=construct,
            score__isnull=False
        ).select_related('questionnaire_submission').order_by('-questionnaire_submission__submission_date')[:submission_count]
        
        return list(reversed(historical_scores))  # Reverse to show oldest first for plotting
    
    def _get_previous_construct_score(self, patient, construct, current_submission_date):
        """Get the previous construct score for comparison."""
        previous_score = QuestionnaireConstructScore.objects.filter(
            questionnaire_submission__patient=patient,
            construct=construct,
            questionnaire_submission__submission_date__lt=current_submission_date,
            score__isnull=False
        ).select_related('questionnaire_submission').order_by('-questionnaire_submission__submission_date').first()
        
        return previous_score
    
    def _get_item_results(self, submission, submission_count):
        """Get item-wise results grouped by construct scales."""
        if not submission:
            return []
        
        # Get all responses for this submission
        responses = QuestionnaireItemResponse.objects.filter(
            questionnaire_submission=submission
        ).select_related(
            'questionnaire_item__item__construct_scale',
            'questionnaire_item__item__likert_response',
            'questionnaire_item__item__range_response'
        ).order_by('questionnaire_item__question_number')
        
        # Group responses by construct scale
        construct_groups = {}
        
        for response in responses:
            item = response.questionnaire_item.item
            construct = item.construct_scale
            
            if construct not in construct_groups:
                construct_groups[construct] = {
                    'construct': construct,
                    'items': [],
                    'construct_score': self._get_construct_score_for_submission(submission, construct),
                    'construct_historical_data': self._get_construct_historical_data(
                        submission.patient, construct, submission_count
                    ) if construct else []
                }
            
            # Add historical data for this item
            item_historical_data = self._get_item_historical_data(
                submission.patient,
                response.questionnaire_item,
                submission_count
            )
            
            # Get previous response for comparison
            previous_response = self._get_previous_item_response(
                submission.patient,
                response.questionnaire_item,
                submission.submission_date
            )
            
            # Add response type specific data
            response_data = {
                'response': response,
                'item': item,
                'questionnaire_item': response.questionnaire_item,
                'historical_data': item_historical_data,
                'previous_response': previous_response,
            }
            
            # Add type-specific data
            if item.response_type == ResponseTypeChoices.LIKERT:
                response_data['likert_options'] = self._get_likert_options(item)
                response_data['selected_option'] = self._get_selected_likert_option(response, item)
            
            construct_groups[construct]['items'].append(response_data)
        
        return list(construct_groups.values())
    
    def _get_construct_score_for_submission(self, submission, construct):
        """Get construct score for a specific submission and construct."""
        if not construct:
            return None
        
        return QuestionnaireConstructScore.objects.filter(
            questionnaire_submission=submission,
            construct=construct
        ).first()
    
    def _get_item_historical_data(self, patient, questionnaire_item, submission_count):
        """Get historical responses for a specific item."""
        historical_responses = QuestionnaireItemResponse.objects.filter(
            questionnaire_submission__patient=patient,
            questionnaire_item=questionnaire_item
        ).select_related('questionnaire_submission').order_by('-questionnaire_submission__submission_date')[:submission_count]
        
        return list(reversed(historical_responses))  # Reverse for chronological order
    
    def _get_previous_item_response(self, patient, questionnaire_item, current_submission_date):
        """Get the previous response for an item for comparison."""
        previous_response = QuestionnaireItemResponse.objects.filter(
            questionnaire_submission__patient=patient,
            questionnaire_item=questionnaire_item,
            questionnaire_submission__submission_date__lt=current_submission_date
        ).select_related('questionnaire_submission').order_by('-questionnaire_submission__submission_date').first()
        
        return previous_response
    
    def _get_likert_options(self, item):
        """Get all Likert scale options for an item."""
        if item.response_type != ResponseTypeChoices.LIKERT or not item.likert_response:
            return []
        
        return LikertScaleResponseOption.objects.filter(
            likert_scale=item.likert_response
        ).order_by('option_order')
    
    def _get_selected_likert_option(self, response, item):
        """Get the selected Likert option for a response."""
        if item.response_type != ResponseTypeChoices.LIKERT or not response.response_value:
            return None
        
        try:
            option_value = Decimal(response.response_value)
            return LikertScaleResponseOption.objects.filter(
                likert_scale=item.likert_response,
                option_value=option_value
            ).first()
        except (ValueError, TypeError):
            return None


@login_required
@permission_required('patientapp.view_patient', raise_exception=True)
@require_http_methods(["GET"])
def update_submission_data(request, patient_id):
    """
    HTMX view to update results when submission date or questionnaire changes.
    Returns updated results container.
    """
    patient = get_object_or_404(Patient, id=patient_id)
    
    # Check patient access
    if not check_patient_access(request.user, patient):
        logger.warning(f"Unauthorized HTMX access attempt to patient {patient_id} by user {request.user.id}")
        raise PermissionDenied("You don't have permission to access this patient's data.")
    
    # Get and validate parameters
    selected_submission_date = request.GET.get('submission_date')
    selected_questionnaire_id = request.GET.get('questionnaire_id')
    submission_count = validate_submission_count(request.GET.get('submission_count', 5))
    
    # Validate questionnaire_id if provided
    if selected_questionnaire_id:
        try:
            # Ensure the questionnaire exists and belongs to this patient
            PatientQuestionnaire.objects.get(
                patient=patient,
                questionnaire_id=selected_questionnaire_id,
                display_questionnaire=True
            )
        except PatientQuestionnaire.DoesNotExist:
            logger.warning(f"Invalid questionnaire {selected_questionnaire_id} for patient {patient_id}")
            return JsonResponse({'error': 'Invalid questionnaire'}, status=400)
    
    # Get submissions
    submissions = QuestionnaireSubmission.objects.filter(
        patient=patient
    ).select_related('patient_questionnaire__questionnaire').order_by('-submission_date')
    
    # Filter by questionnaire if specified
    if selected_questionnaire_id:
        submissions = submissions.filter(
            patient_questionnaire__questionnaire_id=selected_questionnaire_id
        )
    
    # Get the selected submission
    if selected_submission_date:
        try:
            selected_submission = submissions.filter(
                submission_date__date=datetime.strptime(selected_submission_date, '%Y-%m-%d').date()
            ).first()
        except ValueError:
            selected_submission = submissions.first()
    else:
        selected_submission = submissions.first()
    
    # Get updated data
    view_instance = HCPResultView()
    view_instance.request = request
    
    important_constructs = []
    construct_scores = []
    item_results = []
    
    if selected_submission:
        important_constructs = view_instance._get_important_constructs(selected_submission, submission_count)
        construct_scores = view_instance._get_construct_scores(selected_submission, submission_count)
        item_results = view_instance._get_item_results(selected_submission, submission_count)
    
    context = {
        'patient': patient,
        'selected_submission': selected_submission,
        'important_constructs': important_constructs,
        'construct_scores': construct_scores,
        'item_results': item_results,
        'submission_count': submission_count,
    }
    
    return render(request, 'promapp/partials/results_container.html', context)


@login_required
@permission_required('patientapp.view_patient', raise_exception=True)
@require_http_methods(["GET"])
def update_plot_data(request, patient_id):
    """
    HTMX view to update plot data when submission count changes.
    Returns JSON data for plot updates.
    """
    patient = get_object_or_404(Patient, id=patient_id)
    
    # Check patient access
    if not check_patient_access(request.user, patient):
        logger.warning(f"Unauthorized plot data access attempt to patient {patient_id} by user {request.user.id}")
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    # Get and validate parameters
    selected_submission_date = request.GET.get('submission_date')
    selected_questionnaire_id = request.GET.get('questionnaire_id')
    submission_count = validate_submission_count(request.GET.get('submission_count', 5))
    construct_id = request.GET.get('construct_id')
    
    if not construct_id:
        return JsonResponse({'error': 'construct_id is required'}, status=400)
    
    # Get submissions
    submissions = QuestionnaireSubmission.objects.filter(
        patient=patient
    ).select_related('patient_questionnaire__questionnaire').order_by('-submission_date')
    
    # Filter by questionnaire if specified
    if selected_questionnaire_id:
        submissions = submissions.filter(
            patient_questionnaire__questionnaire_id=selected_questionnaire_id
        )
    
    # Get the selected submission
    if selected_submission_date:
        try:
            selected_submission = submissions.filter(
                submission_date__date=datetime.strptime(selected_submission_date, '%Y-%m-%d').date()
            ).first()
        except ValueError:
            selected_submission = submissions.first()
    else:
        selected_submission = submissions.first()
    
    if not selected_submission or not construct_id:
        return JsonResponse({'error': 'Invalid parameters'}, status=400)
    
    # Get construct
    try:
        construct = ConstructScale.objects.get(id=construct_id)
    except ConstructScale.DoesNotExist:
        return JsonResponse({'error': 'Construct not found'}, status=404)
    
    # Get historical data
    view_instance = HCPResultView()
    historical_data = view_instance._get_construct_historical_data(patient, construct, submission_count)
    
    # Prepare plot data
    plot_data = {
        'dates': [score.questionnaire_submission.submission_date.strftime('%Y-%m-%d') for score in historical_data],
        'scores': [float(score.score) if score.score else None for score in historical_data],
        'threshold_score': float(construct.scale_threshold_score) if construct.scale_threshold_score else None,
        'normative_mean': float(construct.scale_normative_score_mean) if construct.scale_normative_score_mean else None,
        'normative_sd': float(construct.scale_normative_score_standard_deviation) if construct.scale_normative_score_standard_deviation else None,
    }
    
    return JsonResponse(plot_data)


@login_required
@permission_required('patientapp.view_patient', raise_exception=True)
@require_http_methods(["GET"])
def get_text_response_history(request, patient_id):
    """
    HTMX view to get historical text responses for pagination.
    """
    patient = get_object_or_404(Patient, id=patient_id)
    
    # Check patient access
    if not check_patient_access(request.user, patient):
        logger.warning(f"Unauthorized text history access attempt to patient {patient_id} by user {request.user.id}")
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    questionnaire_item_id = request.GET.get('questionnaire_item_id')
    try:
        page = int(request.GET.get('page', 1))
        if page < 1:
            page = 1
    except (ValueError, TypeError):
        page = 1
    
    if not questionnaire_item_id:
        return JsonResponse({'error': 'Missing questionnaire_item_id'}, status=400)
    
    try:
        questionnaire_item = QuestionnaireItem.objects.get(id=questionnaire_item_id)
    except QuestionnaireItem.DoesNotExist:
        return JsonResponse({'error': 'Questionnaire item not found'}, status=404)
    
    # Get all text responses for this item
    responses = QuestionnaireItemResponse.objects.filter(
        questionnaire_submission__patient=patient,
        questionnaire_item=questionnaire_item,
        response_value__isnull=False
    ).exclude(response_value='').select_related('questionnaire_submission').order_by('-questionnaire_submission__submission_date')
    
    # Paginate responses
    paginator = Paginator(responses, 1)  # One response per page for text
    page_obj = paginator.get_page(page)
    
    context = {
        'page_obj': page_obj,
        'questionnaire_item': questionnaire_item,
        'patient': patient,
    }
    
    return render(request, 'promapp/partials/text_response_paginator.html', context)


@login_required
@permission_required('patientapp.view_patient', raise_exception=True)
@csrf_protect
@require_http_methods(["POST"])
def toggle_fieldset(request, patient_id):
    """
    HTMX view to toggle fieldset visibility.
    Returns updated fieldset content.
    """
    patient = get_object_or_404(Patient, id=patient_id)
    
    # Check patient access
    if not check_patient_access(request.user, patient):
        logger.warning(f"Unauthorized fieldset toggle attempt for patient {patient_id} by user {request.user.id}")
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    construct_id = request.POST.get('construct_id')
    is_expanded = request.POST.get('is_expanded') == 'true'
    
    # Validate construct_id if provided
    if construct_id:
        try:
            ConstructScale.objects.get(id=construct_id)
        except ConstructScale.DoesNotExist:
            return JsonResponse({'error': 'Invalid construct'}, status=400)
    
    # This is mainly for client-side state management
    # Return success response
    return JsonResponse({'success': True, 'is_expanded': is_expanded})


@login_required
@permission_required('patientapp.view_patient', raise_exception=True)
@csrf_protect
@require_http_methods(["POST"])
def toggle_all_fieldsets(request, patient_id):
    """
    HTMX view to toggle all fieldsets visibility.
    """
    patient = get_object_or_404(Patient, id=patient_id)
    
    # Check patient access
    if not check_patient_access(request.user, patient):
        logger.warning(f"Unauthorized fieldset toggle all attempt for patient {patient_id} by user {request.user.id}")
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    expand_all = request.POST.get('expand_all') == 'true'
    
    # This is mainly for client-side state management
    return JsonResponse({'success': True, 'expand_all': expand_all})


@login_required
@permission_required('patientapp.view_patient', raise_exception=True)
@require_http_methods(["GET"])
def get_item_plot_data(request, patient_id):
    """
    HTMX view to get plot data for individual items.
    Returns JSON data for item-specific plots.
    """
    patient = get_object_or_404(Patient, id=patient_id)
    
    # Check patient access
    if not check_patient_access(request.user, patient):
        logger.warning(f"Unauthorized item plot data access attempt to patient {patient_id} by user {request.user.id}")
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    # Get and validate parameters
    questionnaire_item_id = request.GET.get('questionnaire_item_id')
    submission_count = validate_submission_count(request.GET.get('submission_count', 5))
    
    if not questionnaire_item_id:
        return JsonResponse({'error': 'questionnaire_item_id is required'}, status=400)
    
    try:
        questionnaire_item = QuestionnaireItem.objects.get(id=questionnaire_item_id)
    except QuestionnaireItem.DoesNotExist:
        return JsonResponse({'error': 'Questionnaire item not found'}, status=404)
    
    # Get historical data for this item
    view_instance = HCPResultView()
    historical_data = view_instance._get_item_historical_data(patient, questionnaire_item, submission_count)
    
    # Prepare plot data based on response type
    item = questionnaire_item.item
    plot_data = {
        'dates': [response.questionnaire_submission.submission_date.strftime('%Y-%m-%d') for response in historical_data],
        'response_type': item.response_type,
        'item_name': item.name,
        'threshold_score': float(item.item_threshold_score) if item.item_threshold_score else None,
        'normative_mean': float(item.item_normative_score_mean) if item.item_normative_score_mean else None,
        'normative_sd': float(item.item_normative_score_standard_deviation) if item.item_normative_score_standard_deviation else None,
    }
    
    if item.response_type in [ResponseTypeChoices.NUMBER, ResponseTypeChoices.RANGE]:
        # Numeric data
        plot_data['values'] = [float(response.response_value) if response.response_value else None for response in historical_data]
    
    elif item.response_type == ResponseTypeChoices.LIKERT:
        # Likert data - need option text and values
        plot_data['values'] = []
        plot_data['option_texts'] = []
        
        for response in historical_data:
            if response.response_value:
                try:
                    option_value = Decimal(response.response_value)
                    option = LikertScaleResponseOption.objects.filter(
                        likert_scale=item.likert_response,
                        option_value=option_value
                    ).first()
                    
                    plot_data['values'].append(float(option_value))
                    plot_data['option_texts'].append(option.option_text if option else str(option_value))
                except (ValueError, TypeError):
                    plot_data['values'].append(None)
                    plot_data['option_texts'].append(None)
            else:
                plot_data['values'].append(None)
                plot_data['option_texts'].append(None)
        
        # Get all available options for the scale
        if item.likert_response:
            options = LikertScaleResponseOption.objects.filter(
                likert_scale=item.likert_response
            ).order_by('option_order')
            plot_data['all_options'] = [
                {'value': float(opt.option_value), 'text': opt.option_text} 
                for opt in options if opt.option_value is not None
            ]
    
    elif item.response_type == ResponseTypeChoices.TEXT:
        # Text data - just return the text values
        plot_data['text_values'] = [response.response_value for response in historical_data]
    
    return JsonResponse(plot_data)


@login_required
@permission_required('patientapp.view_patient', raise_exception=True)
@require_http_methods(["GET"])
def get_construct_sparkline_data(request, patient_id):
    """
    HTMX view to get sparkline data for construct scores in fieldsets.
    Returns JSON data for mini sparkline plots.
    """
    patient = get_object_or_404(Patient, id=patient_id)
    
    # Check patient access
    if not check_patient_access(request.user, patient):
        logger.warning(f"Unauthorized sparkline data access attempt to patient {patient_id} by user {request.user.id}")
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    construct_id = request.GET.get('construct_id')
    
    if not construct_id:
        return JsonResponse({'error': 'construct_id is required'}, status=400)
    
    try:
        construct = ConstructScale.objects.get(id=construct_id)
    except ConstructScale.DoesNotExist:
        return JsonResponse({'error': 'Construct not found'}, status=404)
    
    # Get last 10 submissions for sparkline (fixed number for consistency)
    view_instance = HCPResultView()
    historical_data = view_instance._get_construct_historical_data(patient, construct, 10)
    
    # Prepare sparkline data
    sparkline_data = {
        'dates': [score.questionnaire_submission.submission_date.strftime('%Y-%m-%d') for score in historical_data],
        'scores': [float(score.score) if score.score else None for score in historical_data],
        'construct_name': construct.name,
    }
    
    return JsonResponse(sparkline_data)


@login_required
@permission_required('patientapp.view_patient', raise_exception=True)
@require_http_methods(["GET"])
def get_questionnaire_submissions(request, patient_id):
    """
    HTMX view to get available submissions for a specific questionnaire.
    Used for submission date selector dropdown.
    """
    patient = get_object_or_404(Patient, id=patient_id)
    
    # Check patient access
    if not check_patient_access(request.user, patient):
        logger.warning(f"Unauthorized submissions access attempt to patient {patient_id} by user {request.user.id}")
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    questionnaire_id = request.GET.get('questionnaire_id')
    
    if questionnaire_id:
        # Validate questionnaire belongs to patient
        try:
            PatientQuestionnaire.objects.get(
                patient=patient,
                questionnaire_id=questionnaire_id,
                display_questionnaire=True
            )
        except PatientQuestionnaire.DoesNotExist:
            return JsonResponse({'error': 'Invalid questionnaire'}, status=400)
        
        # Get submissions for specific questionnaire
        submissions = QuestionnaireSubmission.objects.filter(
            patient=patient,
            patient_questionnaire__questionnaire_id=questionnaire_id
        ).select_related('patient_questionnaire__questionnaire').order_by('-submission_date')[:20]
    else:
        # Get all submissions for patient
        submissions = QuestionnaireSubmission.objects.filter(
            patient=patient
        ).select_related('patient_questionnaire__questionnaire').order_by('-submission_date')[:20]
    
    # Prepare submission data
    submission_data = []
    for submission in submissions:
        submission_data.append({
            'id': str(submission.id),
            'date': submission.submission_date.strftime('%Y-%m-%d'),
            'datetime': submission.submission_date.strftime('%Y-%m-%d %H:%M'),
            'questionnaire_name': submission.patient_questionnaire.questionnaire.name,
        })
    
    context = {
        'submissions': submission_data,
        'patient': patient,
    }
    
    return render(request, 'promapp/partials/submission_selector_options.html', context)


@login_required
@permission_required('patientapp.view_patient', raise_exception=True)
@require_http_methods(["GET"])
def get_color_palette_data(request, patient_id):
    """
    HTMX view to get color palette information for Likert scale items.
    Returns color mapping for consistent visualization.
    """
    patient = get_object_or_404(Patient, id=patient_id)
    
    # Check patient access
    if not check_patient_access(request.user, patient):
        logger.warning(f"Unauthorized color palette access attempt to patient {patient_id} by user {request.user.id}")
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    questionnaire_item_id = request.GET.get('questionnaire_item_id')
    
    if not questionnaire_item_id:
        return JsonResponse({'error': 'questionnaire_item_id is required'}, status=400)
    
    try:
        questionnaire_item = QuestionnaireItem.objects.get(id=questionnaire_item_id)
    except QuestionnaireItem.DoesNotExist:
        return JsonResponse({'error': 'Questionnaire item not found'}, status=404)
    
    item = questionnaire_item.item
    
    if item.response_type != ResponseTypeChoices.LIKERT or not item.likert_response:
        return JsonResponse({'error': 'Item is not a Likert scale'}, status=400)
    
    # Get all options for the Likert scale
    options = LikertScaleResponseOption.objects.filter(
        likert_scale=item.likert_response
    ).order_by('option_order')
    
    # Generate color palette based on direction and number of options
    color_data = []
    num_options = options.count()
    
    for i, option in enumerate(options):
        # Generate color intensity based on direction
        if item.item_better_score_direction == DirectionChoices.HIGHER_IS_BETTER:
            # Higher values get darker colors
            intensity = (i + 1) / num_options
        elif item.item_better_score_direction == DirectionChoices.LOWER_IS_BETTER:
            # Lower values get darker colors
            intensity = (num_options - i) / num_options
        else:
            # No direction - use neutral progression
            intensity = (i + 1) / num_options
        
        # Use viridis-like color scale
        # This is a simplified version - you might want to use a proper color library
        hue = 240 + (intensity * 120)  # Blue to green range
        saturation = 70 + (intensity * 30)  # 70-100%
        lightness = 30 + (intensity * 40)   # 30-70%
        
        color_data.append({
            'option_value': float(option.option_value) if option.option_value else 0,
            'option_text': option.option_text,
            'color': f'hsl({hue}, {saturation}%, {lightness}%)',
            'background_color': f'hsla({hue}, {saturation}%, {lightness}%, 0.3)',  # Transparent version
        })
    
    return JsonResponse({
        'colors': color_data,
        'direction': item.item_better_score_direction,
        'item_name': item.name,
    })
