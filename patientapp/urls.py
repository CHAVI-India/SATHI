from django.urls import path
from . import views

urlpatterns = [
    path('patients/', views.patient_list, name='patient_list'),
    path('patients/search-api/', views.patient_search_api, name='patient_search_api'),
    path('patients/<uuid:pk>/', views.patient_detail, name='patient_detail'),
    path('patients/create/', views.PatientCreateView.as_view(), name='patient_create'),
    path('patients/<uuid:pk>/update-basic/', views.PatientRestrictedUpdateView.as_view(), name='patient_restricted_update'),
    path('patients/<uuid:pk>/prom-review/', views.prom_review, name='prom_review'),
    
    # Diagnosis URLs
    path('patients/<uuid:patient_pk>/diagnoses/create/', views.DiagnosisCreateView.as_view(), name='diagnosis_create'),
    path('diagnoses/<uuid:pk>/update/', views.DiagnosisUpdateView.as_view(), name='diagnosis_update'),
    # path('diagnoses/<uuid:pk>/delete/', views.DiagnosisDeleteView.as_view(), name='diagnosis_delete'), # Removed as per request
    path('diagnosislist/create/', views.DiagnosisListCreateView.as_view(), name='diagnosislist_create'),
    
    # Treatment URLs
    path('diagnoses/<uuid:diagnosis_pk>/treatments/create/', views.TreatmentCreateView.as_view(), name='treatment_create'),
    path('treatments/<uuid:pk>/update/', views.TreatmentUpdateView.as_view(), name='treatment_update'),
    # path('treatments/<uuid:pk>/delete/', views.TreatmentDeleteView.as_view(), name='treatment_delete'), # Removed as per request
    
    # Treatment Type URLs
    path('treatment-types/', views.treatment_type_list, name='treatment_type_list'),
    path('treatment-types/create/', views.TreatmentTypeCreateView.as_view(), name='treatment_type_create'),
    path('treatment-types/<uuid:pk>/update/', views.TreatmentTypeUpdateView.as_view(), name='treatment_type_update'),
    # path('treatment-types/<uuid:pk>/delete/', views.TreatmentTypeDeleteView.as_view(), name='treatment_type_delete'), # Removed as per request

    # PRO Review URLs
    path('patients/<uuid:pk>/prom-review/', views.prom_review, name='prom_review'),
    path('patients/<uuid:pk>/prom-review/print/', views.prom_review_print, name='prom_review_print'),
    path('patients/<uuid:pk>/prom-review/item-search/', views.prom_review_item_search, name='prom_review_item_search'),
    path('patients/<uuid:pk>/prom-review/construct-plot/<uuid:construct_id>/', views.prom_review_construct_plot, name='prom_review_construct_plot'),
    path('patients/<uuid:pk>/prom-review/composite-plot/<uuid:composite_id>/', views.prom_review_composite_plot, name='prom_review_composite_plot'),
    path('patients/<uuid:pk>/prom-review/item-plot/<uuid:item_id>/', views.prom_review_item_plot, name='prom_review_item_plot'),
    
    # Patient Portal URL
    path('my-portal/', views.patient_portal, name='patient_portal'),
    
    # Project Management URLs
    path('patients/<uuid:patient_pk>/projects/create/', views.patient_project_create, name='patient_project_create'),
    path('patient-projects/<uuid:pk>/update/', views.patient_project_update, name='patient_project_update'),
    path('patient-projects/<uuid:pk>/delete/', views.patient_project_delete, name='patient_project_delete'),
    path('projects/', views.project_list, name='project_list'),
    path('projects/create/', views.project_create, name='project_create'),
    path('projects/<uuid:pk>/update/', views.project_update, name='project_update'),

    # REDCap Integration URLs
    path('projects/<uuid:pk>/redcap/', views.redcap_project_dashboard, name='redcap_project_dashboard'),
    path('projects/<uuid:pk>/redcap/create/', views.redcap_mapping_create, name='redcap_mapping_create'),
    path('projects/<uuid:pk>/redcap/<int:mapping_pk>/edit/', views.redcap_mapping_edit, name='redcap_mapping_edit'),
    path('projects/<uuid:pk>/redcap/<int:mapping_pk>/fetch-metadata/', views.redcap_fetch_metadata, name='redcap_fetch_metadata'),
    path('projects/<uuid:pk>/redcap/<int:mapping_pk>/wizard/', views.redcap_wizard_page, name='redcap_wizard_page'),
    path('projects/<uuid:pk>/redcap/<int:mapping_pk>/setup-wizard/', views.redcap_setup_wizard, name='redcap_setup_wizard'),
    path('projects/<uuid:pk>/redcap/<int:mapping_pk>/id-fields/', views.redcap_id_fields, name='redcap_id_fields'),
    path('projects/<uuid:pk>/redcap/<int:mapping_pk>/form-mappings/', views.redcap_form_mappings, name='redcap_form_mappings'),
    path('projects/<uuid:pk>/redcap/<int:mapping_pk>/form-mappings/create/', views.redcap_form_mapping_create, name='redcap_form_mapping_create'),
    path('projects/<uuid:pk>/redcap/<int:mapping_pk>/form-mappings/<int:fm_pk>/edit/', views.redcap_form_mapping_edit, name='redcap_form_mapping_edit'),
    path('projects/<uuid:pk>/redcap/<int:mapping_pk>/form-mappings/<int:fm_pk>/field-mappings/', views.redcap_field_mappings, name='redcap_field_mappings'),
    path('projects/<uuid:pk>/redcap/<int:mapping_pk>/patient-ids/', views.redcap_patient_ids, name='redcap_patient_ids'),
    path('projects/<uuid:pk>/redcap/<int:mapping_pk>/export/', views.redcap_export, name='redcap_export'),
]