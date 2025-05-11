from django.contrib import admin
from .models import *


# Register your models here.
@admin.register(Institution)
class InstitutionAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_date', 'modified_date']

@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ['name', 'patient_id', 'age', 'gender', 'created_date', 'modified_date']

@admin.register(Diagnosis)
class DiagnosisAdmin(admin.ModelAdmin):
    list_display = ['patient', 'diagnosis', 'created_date', 'modified_date']

@admin.register(TreatmentType)
class TreatmentTypeAdmin(admin.ModelAdmin):
    list_display = ['treatment_type', 'created_date', 'modified_date']

@admin.register(Treatment)
class TreatmentAdmin(admin.ModelAdmin):
    list_display = ['diagnosis', 'treatment_intent', 'date_of_start_of_treatment', 'created_date', 'modified_date']
