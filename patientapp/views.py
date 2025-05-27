from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.models import User
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.utils.translation import gettext_lazy as _, get_language
from django.db import transaction
from django.db.models import Q, Count, Max
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.http import JsonResponse
from .models import Patient, Diagnosis, Treatment, Institution, GenderChoices, TreatmentType, TreatmentIntentChoices
from .forms import PatientForm, TreatmentForm
from promapp.models import *
from .utils import ConstructScoreData, calculate_percentage
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
        submissions = submissions.filter(submission_date=submission_date)
    
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
    
    # Calculate percentages and add option text for item responses
    for response in item_responses:
        if response.questionnaire_item.item.response_type == 'Numeric' and response.questionnaire_item.item.range_response:
            try:
                numeric_value = float(response.response_value) if response.response_value else None
                response.numeric_response = numeric_value
                response.percentage = calculate_percentage(numeric_value, response.questionnaire_item.item.range_response.max_value)
            except (ValueError, TypeError):
                response.numeric_response = None
                response.percentage = 0
        elif response.questionnaire_item.item.response_type == 'Likert' and response.questionnaire_item.item.likert_response:
            try:
                likert_value = float(response.response_value) if response.response_value else None
                response.likert_response = likert_value
                # Get max value from LikertScaleResponseOption
                max_value = response.questionnaire_item.item.likert_response.likertscaleresponseoption_set.aggregate(
                    max_value=Max('option_value')
                )['max_value']
                response.percentage = calculate_percentage(likert_value, max_value)
                
                # Add the option text and color to the response
                likert_scale = response.questionnaire_item.item.likert_response
                better_direction = response.questionnaire_item.item.item_better_score_direction or 'Higher is Better'
                color_map = likert_scale.get_option_colors(better_direction)
                
                for option in likert_scale.likertscaleresponseoption_set.all():
                    if str(option.option_value) == response.response_value:
                        response.option_text = option.option_text
                        response.option_color = color_map.get(str(option.option_value), '#ffffff')
                        response.text_color = likert_scale.get_text_color(response.option_color)
                        break

                # Get previous response for change calculation
                previous_response = QuestionnaireItemResponse.objects.filter(
                    questionnaire_item=response.questionnaire_item,
                    questionnaire_submission__patient=patient,
                    questionnaire_submission__submission_date__lt=response.questionnaire_submission.submission_date
                ).order_by('-questionnaire_submission__submission_date').first()

                if previous_response and previous_response.response_value:
                    try:
                        previous_value = float(previous_response.response_value)
                        response.previous_value = previous_value
                        response.value_change = likert_value - previous_value if likert_value is not None else None
                    except (ValueError, TypeError):
                        response.previous_value = None
                        response.value_change = None
                else:
                    response.previous_value = None
                    response.value_change = None

            except (ValueError, TypeError):
                response.likert_response = None
                response.percentage = 0
                response.previous_value = None
                response.value_change = None
    
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

    # Get submission count from time range or default to 5
    if time_range == 'all':
        submission_count = submissions.count()
    else:
        submission_count = int(time_range)
    
    logger.info(f"Using submission count: {submission_count}")

    # Get important construct scores
    important_construct_scores = []
    logger.info("Processing construct scores to find important ones...")
    
    for construct_score in construct_scores:
        construct = construct_score.construct
        logger.info(f"Processing construct: {construct.name}")
        
        # Get historical scores for this construct
        historical_scores = QuestionnaireConstructScore.objects.filter(
            questionnaire_submission__patient=patient,
            construct=construct
        ).select_related(
            'questionnaire_submission'
        ).order_by('-questionnaire_submission__submission_date')[:submission_count]

        logger.debug(f"Found {historical_scores.count()} historical scores for {construct.name}")

        # Get previous score for change calculation
        previous_score = None
        if historical_scores.count() > 1:
            previous_score = historical_scores[1].score
            logger.debug(f"Previous score for {construct.name}: {previous_score}")

        # Create construct score data object
        score_data = ConstructScoreData(
            construct=construct,
            current_score=construct_score.score,
            previous_score=previous_score,
            historical_scores=historical_scores
        )

        # Only include if it's an important construct
        if ConstructScoreData.is_important_construct(construct, construct_score.score):
            logger.info(f"Adding {construct.name} to important constructs")
            important_construct_scores.append(score_data)
        else:
            logger.info(f"{construct.name} not marked as important")
    
    logger.info(f"Found {len(important_construct_scores)} important construct scores")
    
    # Get Bokeh resources
    bokeh_css = CDN.render_css()
    bokeh_js = CDN.render_js()
    
    context = {
        'patient': patient,
        'submissions': submissions,
        'latest_submissions': latest_submissions,
        'assigned_questionnaires': assigned_questionnaires,
        'item_responses': item_responses,
        'construct_scores': construct_scores,
        'questionnaire_submission_counts': questionnaire_submission_counts,
        'important_construct_scores': important_construct_scores,
        'bokeh_css': bokeh_css,
        'bokeh_js': bokeh_js,
    }
    
    # If this is an HTMX request, only return the main content section
    if request.headers.get('HX-Request'):
        return render(request, 'promapp/components/main_content.html', context)
    
    return render(request, 'promapp/prom_review.html', context)




def patient_list(request):
    # Get filter parameters
    search_query = request.GET.get('search', '')
    institution_id = request.GET.get('institution', '')
    gender = request.GET.get('gender', '')
    diagnosis = request.GET.get('diagnosis', '')
    treatment_type = request.GET.get('treatment_type', '')
    questionnaire_count = request.GET.get('questionnaire_count', '')
    sort_by = request.GET.get('sort', 'name')
    
    # Start with base queryset
    patients = Patient.objects.select_related('user', 'institution').all()
    
    # Apply filters
    if search_query:
        patients = patients.filter(
            Q(name__icontains=search_query) |
            Q(patient_id__icontains=search_query)
        )
    
    if institution_id:
        patients = patients.filter(institution_id=institution_id)
    
    if gender:
        patients = patients.filter(gender=gender)
    
    if diagnosis:
        patients = patients.filter(diagnosis__diagnosis__icontains=diagnosis).distinct()
    
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
    diagnoses = list(Diagnosis.objects.values_list('diagnosis', flat=True).distinct().exclude(diagnosis__isnull=True).exclude(diagnosis=''))
    
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

# Diagnosis Views
class DiagnosisCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Diagnosis
    fields = ['diagnosis']
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
    fields = ['diagnosis']
    template_name = 'patientapp/diagnosis_form.html'
    permission_required = 'patientapp.change_diagnosis'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('Edit Diagnosis')
        return context

    def get_success_url(self):
        return reverse('patient_detail', kwargs={'pk': self.object.patient.pk})

class DiagnosisDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Diagnosis
    template_name = 'patientapp/diagnosis_confirm_delete.html'
    permission_required = 'patientapp.delete_diagnosis'

    def get_success_url(self):
        return reverse('patient_detail', kwargs={'pk': self.object.patient.pk})

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
        return context

    def get_success_url(self):
        return reverse('patient_detail', kwargs={'pk': self.object.diagnosis.patient.pk})

class TreatmentDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Treatment
    template_name = 'patientapp/treatment_confirm_delete.html'
    permission_required = 'patientapp.delete_treatment'

    def get_success_url(self):
        return reverse('patient_detail', kwargs={'pk': self.object.diagnosis.patient.pk})

# Treatment Type Views
class TreatmentTypeCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = TreatmentType
    fields = ['treatment_type']
    template_name = 'patientapp/treatment_type_form.html'
    permission_required = 'patientapp.add_treatmenttype'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('Add Treatment Type')
        return context

    def get_success_url(self):
        return reverse('treatment_type_list')

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

class TreatmentTypeDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = TreatmentType
    template_name = 'patientapp/treatment_type_confirm_delete.html'
    permission_required = 'patientapp.delete_treatmenttype'

    def get_success_url(self):
        return reverse('treatment_type_list')

def treatment_type_list(request):
    treatment_types = TreatmentType.objects.all()
    return render(request, 'patientapp/treatment_type_list.html', {
        'treatment_types': treatment_types,
        'title': _('Treatment Types')
    })






