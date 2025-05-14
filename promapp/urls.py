from django.urls import path
from . import views

urlpatterns = [
    # Questionnaire URLs
    path('questionnaires/', views.QuestionnaireListView.as_view(), name='questionnaire_list'),
    path('questionnaires/create/', views.QuestionnaireCreateView.as_view(), name='questionnaire_create'),
    path('questionnaires/<uuid:pk>/', views.QuestionnaireDetailView.as_view(), name='questionnaire_detail'),
    path('questionnaires/<uuid:pk>/update/', views.QuestionnaireUpdateView.as_view(), name='questionnaire_update'),
    
    # Item URLs
    path('items/', views.ItemListView.as_view(), name='item_list'),
    path('items/create/', views.ItemCreateView.as_view(), name='item_create'),
    path('items/<uuid:pk>/update/', views.ItemUpdateView.as_view(), name='item_update'),
    
    # AJAX URLs for dynamic forms
    path('get-response-fields/', views.get_response_fields, name='get_response_fields'),
    path('create-likert-scale/', views.create_likert_scale, name='create_likert_scale'),
    path('create-range-scale/', views.create_range_scale, name='create_range_scale'),
    path('create-construct-scale/', views.create_construct_scale, name='create_construct_scale'),
    
    # HTMX URLs
    path('add-likert-option/', views.add_likert_option, name='add_likert_option'),
    path('remove-likert-option/', views.remove_likert_option, name='remove_likert_option'),
] 