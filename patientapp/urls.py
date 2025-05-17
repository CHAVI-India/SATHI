from django.urls import path
from . import views

urlpatterns = [
    path('patients/', views.patient_list, name='patient_list'),
    path('patients/<uuid:pk>/', views.patient_detail, name='patient_detail'),
    path('patients/create/', views.PatientCreateView.as_view(), name='patient_create'),
    
    # Diagnosis URLs
    path('patients/<uuid:patient_pk>/diagnoses/create/', views.DiagnosisCreateView.as_view(), name='diagnosis_create'),
    path('diagnoses/<uuid:pk>/update/', views.DiagnosisUpdateView.as_view(), name='diagnosis_update'),
    path('diagnoses/<uuid:pk>/delete/', views.DiagnosisDeleteView.as_view(), name='diagnosis_delete'),
    
    # Treatment URLs
    path('diagnoses/<uuid:diagnosis_pk>/treatments/create/', views.TreatmentCreateView.as_view(), name='treatment_create'),
    path('treatments/<uuid:pk>/update/', views.TreatmentUpdateView.as_view(), name='treatment_update'),
    path('treatments/<uuid:pk>/delete/', views.TreatmentDeleteView.as_view(), name='treatment_delete'),
] 