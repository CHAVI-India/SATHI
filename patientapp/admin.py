from django.contrib import admin
from patientapp.models import *
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

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ['project_name', 'created_date', 'modified_date']

@admin.register(PatientProject)
class PatientProjectAdmin(admin.ModelAdmin):
    list_display = ['patient', 'project', 'date_patient_enrolled_in_project', 'date_patient_exited_from_project', 'created_date', 'modified_date']

@admin.register(ProjectRedcapMapping)
class ProjectRedcapMappingAdmin(admin.ModelAdmin):
    list_display = ['project', 'redcap_project_url', 'export_type', 'redcap_project_token_allows_import', 'redcap_project_token_allows_export', 'date_redcap_project_info_updated', 'created_date', 'modified_date']
    list_filter = ['export_type', 'redcap_project_token_allows_import', 'redcap_project_token_allows_export']
    readonly_fields = ['created_date', 'modified_date', 'date_redcap_project_info_updated', 'redcap_record_count', 'redcap_project_info']

@admin.register(RedcapStudyIDtoPatientIDMap)
class RedcapStudyIDtoPatientIDMapAdmin(admin.ModelAdmin):
    list_display = ['patient', 'project_redcap_mapping', 'redcap_study_id', 'created_at', 'modified_at']
    list_filter = ['project_redcap_mapping']
    readonly_fields = ['created_at', 'modified_at']

@admin.register(RedcapFormToQuestionnaireMapping)
class RedcapFormToQuestionnaireMappingAdmin(admin.ModelAdmin):
    list_display = ['redcap_form_name', 'project_redcap_mapping', 'questionnaire', 'redcap_form_is_repeating', 'redcap_form_is_in_event', 'redcap_event_is_repeating', 'created_at', 'modified_at']
    list_filter = ['project_redcap_mapping', 'redcap_form_is_repeating', 'redcap_form_is_in_event', 'redcap_event_is_repeating']
    readonly_fields = ['created_at', 'modified_at']

@admin.register(RedcapFieldToItemMapping)
class RedcapFieldToItemMappingAdmin(admin.ModelAdmin):
    list_display = ['redcap_field_name', 'redcap_form_to_questionnaire_mapping', 'questionnaire_item', 'created_at', 'modified_at']
    list_filter = ['redcap_form_to_questionnaire_mapping']
    readonly_fields = ['created_at', 'modified_at']

@admin.register(RedcapDataExportLog)
class RedcapDataExportLogAdmin(admin.ModelAdmin):
    list_display = ['patient', 'redcap_form_to_questionnaire_mapping', 'user_exporting_data', 'export_type', 'export_status', 'datetime_export_start', 'datetime_export_completed']
    list_filter = ['export_type', 'export_status']
    readonly_fields = ['created_at', 'modified_at']