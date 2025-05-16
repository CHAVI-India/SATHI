from django.shortcuts import render, redirect
from django.views.generic import ListView, DetailView, CreateView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.models import User
from django.contrib import messages
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.db import transaction
from .models import Patient, Diagnosis, Treatment
from .forms import PatientForm

# Create your views here.

def patient_list(request):
    patients = Patient.objects.all()
    return render(request, 'patientapp/patient_list.html', {'patients': patients})

def patient_detail(request, pk):
    patient = Patient.objects.get(pk=pk)
    return render(request, 'patientapp/patient_detail.html', {'patient': patient})

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






