from django.urls import path
from . import views

urlpatterns = [
    # Questionnaire URLs
    path('questionnaires/', views.QuestionnaireListView.as_view(), name='questionnaire_list'),
    path('questionnaires/create/', views.QuestionnaireCreateView.as_view(), name='questionnaire_create'),
    path('questionnaires/<uuid:pk>/', views.QuestionnaireDetailView.as_view(), name='questionnaire_detail'),
    path('questionnaires/<uuid:pk>/update/', views.QuestionnaireUpdateView.as_view(), name='questionnaire_update'),
    path('questionnaire/<uuid:pk>/respond/', views.QuestionnaireResponseView.as_view(), name='questionnaire_response'),
    
    # Item URLs
    path('items/', views.ItemListView.as_view(), name='item_list'),
    path('items/create/', views.ItemCreateView.as_view(), name='item_create'),
    path('items/<uuid:pk>/update/', views.ItemUpdateView.as_view(), name='item_update'),
    
    # Construct Scale URLs
    path('construct-scales/', views.ConstructScaleListView.as_view(), name='construct_scale_list'),
    
    # Likert Scale URLs
    path('likert-scales/', views.LikertScaleListView.as_view(), name='likert_scale_list'),
    
    # Range Scale URLs
    path('range-scales/', views.RangeScaleListView.as_view(), name='range_scale_list'),
    path('create-range-scale/', views.create_range_scale, name='create_range_scale'),
    
    # AJAX URLs for dynamic forms
    path('get-response-fields/', views.get_response_fields, name='get_response_fields'),
    path('create-likert-scale/', views.create_likert_scale, name='create_likert_scale'),
    path('create-construct-scale/', views.create_construct_scale, name='create_construct_scale'),
    
    # HTMX URLs
    path('add-likert-option/', views.add_likert_option, name='add_likert_option'),
    path('remove-likert-option/', views.remove_likert_option, name='remove_likert_option'),
    path('patients/<uuid:pk>/questionnaires/', views.PatientQuestionnaireManagementView.as_view(), name='patient_questionnaire_management'),
    path('patient-questionnaires/', views.PatientQuestionnaireListView.as_view(), name='patient_questionnaire_list'),
] 