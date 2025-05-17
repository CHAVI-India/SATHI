from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.models import User
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.utils.translation import gettext_lazy as _
from django.db import transaction
from django.db.models import Q
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.http import JsonResponse
from .models import Patient, Diagnosis, Treatment, Institution, GenderChoices, TreatmentType, TreatmentIntentChoices
from .forms import PatientForm, TreatmentForm

# Create your views here.

def patient_list(request):
    # Get filter parameters
    search_query = request.GET.get('search', '')
    institution_id = request.GET.get('institution', '')
    gender = request.GET.get('gender', '')
    
    # Start with base queryset
    patients = Patient.objects.all()
    
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
    
    # Get all institutions for the filter dropdown
    institutions = Institution.objects.all()
    
    # Get gender choices for the filter dropdown
    gender_choices = GenderChoices.choices
    
    # Pagination
    page = request.GET.get('page', 1)
    paginator = Paginator(patients, 10)  # Show 10 patients per page
    
    try:
        patients = paginator.page(page)
    except PageNotAnInteger:
        patients = paginator.page(1)
    except EmptyPage:
        patients = paginator.page(paginator.num_pages)
    
    context = {
        'patients': patients,
        'institutions': institutions,
        'gender_choices': gender_choices,
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






