from django.urls import path
from . import views
from .views import MyQuestionnaireListView
from . import patient_reponses_view

urlpatterns = [
    # Questionnaire URLs
    path('questionnaires/', views.QuestionnaireListView.as_view(), name='questionnaire_list'),
    path('questionnaires/create/', views.QuestionnaireCreateView.as_view(), name='questionnaire_create'),
    path('questionnaires/<uuid:pk>/', views.QuestionnaireDetailView.as_view(), name='questionnaire_detail'),
    path('questionnaires/<uuid:pk>/update/', views.QuestionnaireUpdateView.as_view(), name='questionnaire_update'),
    path('questionnaires/<uuid:pk>/rules/', views.QuestionnaireRulesView.as_view(), name='questionnaire_rules'),
    path('questionnaire/<uuid:pk>/response/', views.QuestionnaireResponseView.as_view(), name='questionnaire_response'),
    path('questionnaires/<uuid:pk>/save-question-numbers/', views.save_question_numbers, name='save_question_numbers'),
    
    # Item URLs
    path('items/', views.ItemListView.as_view(), name='item_list'),
    path('items/create/', views.ItemCreateView.as_view(), name='item_create'),
    path('items/<uuid:pk>/update/', views.ItemUpdateView.as_view(), name='item_update'),
    
    # Construct Scale URLs
    path('construct-scales/', views.ConstructScaleListView.as_view(), name='construct_scale_list'),
    path('construct-scales/<uuid:pk>/edit/', views.ConstructScaleUpdateView.as_view(), name='construct_scale_edit'),
    path('construct-scales/<uuid:pk>/delete/', views.ConstructScaleDeleteView.as_view(), name='construct_scale_delete'),
    
    # Likert Scale URLs
    path('likert-scales/', views.LikertScaleListView.as_view(), name='likert_scale_list'),
    
    # Range Scale URLs
    path('range-scales/', views.RangeScaleListView.as_view(), name='range_scale_list'),
    path('create-range-scale/', views.create_range_scale, name='create_range_scale'),
    path('range-scale/<uuid:pk>/translate/', views.RangeScaleTranslationView.as_view(), name='range_scale_translate'),
    
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
    path('questionnaire/<uuid:questionnaire_item_id>/evaluate-rules/', views.evaluate_question_rules, name='evaluate_question_rules'),
    path('switch-language/', views.switch_language, name='switch_language'),
    path('translations/', views.TranslationsDashboardView.as_view(), name='translations_dashboard'),

    # Translation URLs
    path('translations/dashboard/', views.TranslationsDashboardView.as_view(), name='translations_dashboard'),
    path('translations/questionnaires/', views.QuestionnaireTranslationListView.as_view(), name='questionnaire_translation_list'),
    path('translations/questionnaire/<uuid:pk>/', views.QuestionnaireTranslationView.as_view(), name='questionnaire_translation'),
    path('translations/switch-language/', views.switch_language, name='switch_language'),

    # Item Translation URLs
    path('translations/items/', views.ItemTranslationListView.as_view(), name='item_translation_list'),
    path('translations/item/<uuid:pk>/', views.ItemTranslationView.as_view(), name='item_translation'),

    # Likert Scale Response Option Translation URLs
    path('translations/likert-options/', views.LikertScaleResponseOptionTranslationListView.as_view(), name='likert_scale_response_option_translation_list'),
    path('translations/likert-option/<uuid:pk>/', views.LikertScaleResponseOptionTranslationView.as_view(), name='likert_scale_response_option_translation'),

    # Range Scale Translation URLs
    path('translations/range-scales/', views.RangeScaleTranslationListView.as_view(), name='range_scale_translation_list'),
    path('translations/range-scale/<uuid:pk>/', views.RangeScaleTranslationView.as_view(), name='range_scale_translation'),

    # Construct Scale Search URLs
    path('search-construct-scales/', views.search_construct_scales, name='search_construct_scales'),

    path('construct-scale/<uuid:pk>/equation/', views.ConstructEquationView.as_view(), name='construct_equation_edit'),
    path('validate-equation/', views.validate_equation, name='validate_equation'),
    path('add-to-equation/', views.add_to_equation, name='add_to_equation'),

 
] 