from django.contrib import admin
from .models import *
from allauth.account.decorators import secure_admin_login
from import_export import resources
from import_export.admin import ImportExportActionModelAdmin, ImportExportModelAdmin
from import_export import fields
from import_export.widgets import ForeignKeyWidget

admin.autodiscover()
admin.site.login = secure_admin_login(admin.site.login)

# Register your models here.
@admin.register(Institution)
class InstitutionAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_date', 'modified_date']

@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ['name', 'patient_id', 'age', 'gender', 'institution','date_of_registration', 'created_date', 'modified_date']


class DiagnosisListResource(resources.ModelResource):
    class Meta:
        model = DiagnosisList
        fields = ('id', 'diagnosis', 'icd_11_code')
    
    def before_import_row(self, row, **kwargs):
        """
        Automatically generate UUID for 'id' field if not provided in the import data.
        """
        if not row.get('id'):
            import uuid
            row['id'] = str(uuid.uuid4())



@admin.register(DiagnosisList)
class DiagnosisListAdmin(ImportExportModelAdmin):
    resource_class = DiagnosisListResource
    list_display = ['diagnosis','icd_11_code']

@admin.register(Diagnosis)
class DiagnosisAdmin(admin.ModelAdmin):
    list_display = ['patient', 'diagnosis','date_of_diagnosis', 'created_date', 'modified_date']

class TreatmentTypeResource(resources.ModelResource):
    class Meta:
        model = TreatmentType
        fields = ('id', 'treatment_type')
    
    def before_import_row(self, row, **kwargs):
        """
        Automatically generate UUID for 'id' field if not provided in the import data.
        """
        if not row.get('id'):
            import uuid
            row['id'] = str(uuid.uuid4())


@admin.register(TreatmentType)
class TreatmentTypeAdmin(admin.ModelAdmin):
    list_display = ['treatment_type', 'created_date', 'modified_date']

@admin.register(Treatment)
class TreatmentAdmin(admin.ModelAdmin):
    list_display = ['diagnosis', 'treatment_intent', 'date_of_start_of_treatment','currently_ongoing_treatment','date_of_end_of_treatment', 'created_date', 'modified_date']
