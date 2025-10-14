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
    path('patients/<uuid:pk>/prom-review/item-search/', views.prom_review_item_search, name='prom_review_item_search'),
    
    # Patient Portal URL
    path('my-portal/', views.patient_portal, name='patient_portal'),
]