from django.shortcuts import render
from .models import Patient, Diagnosis, Treatment
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






