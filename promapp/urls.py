from django.urls import path
from . import views
from .views import MyQuestionnaireListView

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
    path('my-questionnaires/', MyQuestionnaireListView.as_view(), name='my_questionnaire_list'),

    # Questionnaire Item Rule URLs
    path('questionnaire-items/<uuid:questionnaire_item_id>/rules/', 
         views.QuestionnaireItemRuleListView.as_view(), 
         name='questionnaire_item_rules_list'),
    path('questionnaire-items/<uuid:questionnaire_item_id>/rules/create/', 
         views.QuestionnaireItemRuleCreateView.as_view(), 
         name='questionnaire_item_rule_create'),
    path('questionnaire-item-rules/<uuid:pk>/update/', 
         views.QuestionnaireItemRuleUpdateView.as_view(), 
         name='questionnaire_item_rule_update'),
    path('questionnaire-item-rules/<uuid:pk>/delete/', 
         views.QuestionnaireItemRuleDeleteView.as_view(), 
         name='questionnaire_item_rule_delete'),

    # Questionnaire Item Rule Group URLs
    path('questionnaire-items/<uuid:questionnaire_item_id>/rule-groups/', 
         views.QuestionnaireItemRuleGroupListView.as_view(), 
         name='questionnaire_item_rule_groups_list'),
    path('questionnaire-items/<uuid:questionnaire_item_id>/rule-groups/create/', 
         views.QuestionnaireItemRuleGroupCreateView.as_view(), 
         name='questionnaire_item_rule_group_create'),
    path('questionnaire-item-rule-groups/<uuid:pk>/update/', 
         views.QuestionnaireItemRuleGroupUpdateView.as_view(), 
         name='questionnaire_item_rule_group_update'),
    path('questionnaire-item-rule-groups/<uuid:pk>/delete/', 
         views.QuestionnaireItemRuleGroupDeleteView.as_view(), 
         name='questionnaire_item_rule_group_delete'),

    # HTMX URLs for Rule Forms
    path('validate-dependent-item/', views.validate_dependent_item, name='validate_dependent_item'),
    path('validate-rule-operator/', views.validate_rule_operator, name='validate_rule_operator'),
    path('validate-comparison-value/', views.validate_comparison_value, name='validate_comparison_value'),
    path('validate-logical-operator/', views.validate_logical_operator, name='validate_logical_operator'),
    path('validate-rule-order/', views.validate_rule_order, name='validate_rule_order'),
    path('validate-group-order/', views.validate_group_order, name='validate_group_order'),
    path('validate-rule-selection/', views.validate_rule_selection, name='validate_rule_selection'),
    
    # Rule Summary URLs
    path('questionnaire-items/<uuid:questionnaire_item_id>/rules/summary/', 
         views.rule_summary, 
         name='rule_summary'),
    path('questionnaire-items/<uuid:questionnaire_item_id>/rule-groups/summary/', 
         views.rule_group_summary, 
         name='rule_group_summary'),
] 