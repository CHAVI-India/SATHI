from django.urls import path
from . import views

urlpatterns = [
    path('patients/', views.patient_list, name='patient_list'),
    path('patients/<uuid:pk>/', views.patient_detail, name='patient_detail'),
    path('patients/create/', views.PatientCreateView.as_view(), name='patient_create'),
    path('diagnoses/', views.diagnosis_list, name='diagnosis_list'),
    path('diagnoses/<uuid:pk>/', views.diagnosis_detail, name='diagnosis_detail'),
    path('treatments/', views.treatment_list, name='treatment_list'),
    path('treatments/<uuid:pk>/', views.treatment_detail, name='treatment_detail'),
] 