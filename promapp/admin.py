from django.contrib import admin
from .models import *
from parler.admin import TranslatableAdmin, TranslatableStackedInline
# Import export section
from import_export import resources
from import_export.admin import ImportExportActionModelAdmin
from import_export import fields
from import_export.widgets import ForeignKeyWidget
#from modeltranslation.admin import TranslationAdmin, TranslationStackedInline
# Register your models here.


class LikertScaleResponseOptionInline(TranslatableStackedInline):
    model = LikertScaleResponseOption
    fieldsets = (
        (None, {
            'fields': ( 'option_order', 'option_value')
        }),
        ('Emoji', {
            'fields': ('option_emoji',)
        }),
        ('Translations', {
            'fields': ('option_text', 'option_media')
        }),
    )
    extra = 1




class QuestionnaireItemInline(admin.StackedInline):
    model = QuestionnaireItem
    extra = 1



@admin.register(LikertScale)
class LikertScaleAdmin(admin.ModelAdmin):
    inlines = [LikertScaleResponseOptionInline]
    list_display = ('likert_scale_name',)
    search_fields = ('likert_scale_name',)
    list_filter = ('likert_scale_name',)
    ordering = ('-created_date',)
    readonly_fields = ('created_date', 'modified_date')
    group_fieldsets = True

@admin.register(RangeScale)
class RangeScaleAdmin(admin.ModelAdmin):
    list_display = ('range_scale_name', 'min_value', 'max_value', 'increment')
    search_fields = ('range_scale_name', 'min_value', 'max_value', 'increment')
    list_filter = ('range_scale_name', 'min_value', 'max_value', 'increment')
    ordering = ('-created_date',)
    readonly_fields = ('created_date', 'modified_date')
    group_fieldsets = True


@admin.register(Questionnaire)
class QuestionnaireAdmin(TranslatableAdmin):
    list_display = ('name',)
    search_fields = ('name',)
    ordering = ('-created_date',)
    readonly_fields = ('created_date', 'modified_date')

@admin.register(QuestionnaireItem)
class QuestionnaireItemAdmin(admin.ModelAdmin):
    list_display = ('questionnaire', 'item', 'question_number')
    search_fields = ('questionnaire', 'item', 'question_number')
    list_filter = ('questionnaire', 'item', 'question_number')
    ordering = ('-created_date',)
    readonly_fields = ('created_date', 'modified_date')


class ConstructScaleImportResource(resources.ModelResource):
    class Meta:
        model = ConstructScale

@admin.register(ConstructScale)
class ConstructScaleAdmin(ImportExportActionModelAdmin):
    resource_classes = [ConstructScaleImportResource]
    list_display = ('name','instrument_name','instrument_version')
    exclude = ('created_date', 'modified_date')
    search_fields = ('name','instrument_name','instrument_version')
    list_filter = ('instrument_name','instrument_version')
    ordering = ('-created_date',)
    readonly_fields = ('created_date', 'modified_date')


@admin.register(Item)
class ItemAdmin(TranslatableAdmin):
    list_display = ('construct_scale', 'name', 'response_type')
    search_fields = ('construct_scale', 'name', 'response_type')
    list_filter = ('response_type',)
    ordering = ('-created_date',)
    readonly_fields = ('created_date', 'modified_date')


@admin.register(QuestionnaireSubmission)
class QuestionnaireSubmissionAdmin(admin.ModelAdmin):
    list_display = ('patient', 'patient_questionnaire', 'submission_date')
    search_fields = ('patient', 'patient_questionnaire', 'submission_date')
    list_filter = ('patient', 'patient_questionnaire', 'submission_date')
    ordering = ('-submission_date',)
    readonly_fields = ('created_date', 'modified_date')

@admin.register(QuestionnaireConstructScore)
class QuestionnaireConstructScoreAdmin(admin.ModelAdmin):
    list_display = ('questionnaire_submission', 'construct', 'items_answered', 'items_not_answered', 'score')
    search_fields = ('questionnaire_submission', 'construct', 'score')
    list_filter = ('questionnaire_submission', 'construct', 'score')
    ordering = ('-created_date',)
    readonly_fields = ('created_date', 'modified_date')

@admin.register(QuestionnaireItemResponse)
class QuestionnaireItemResponseAdmin(admin.ModelAdmin):
    list_display = ('questionnaire_item', 'questionnaire_submission', 'response_date', 'response_value')
    search_fields = ('questionnaire_item', 'questionnaire_submission', 'response_date', 'response_value')
    list_filter = ('questionnaire_item',  'response_date', 'response_value')
    ordering = ('-created_date',)
    readonly_fields = ('created_date', 'modified_date')


@admin.register(CompositeConstructScaleScoring)
class CompositeConstructScaleScoringAdmin(admin.ModelAdmin):
    list_display = ('composite_construct_scale_name', 'scoring_type')
    search_fields = ('composite_construct_scale_name', 'scoring_type')
    list_filter = ('scoring_type',)
    ordering = ('-created_date',)
    readonly_fields = ('created_date', 'modified_date')

@admin.register(QuestionnaireItemRule)
class QuestionnaireItemRuleAdmin(admin.ModelAdmin):
    pass

@admin.register(QuestionnaireItemRuleGroup)
class QuestionnaireItemRuleGroupAdmin(admin.ModelAdmin):
    pass

@admin.register(QuestionnaireConstructScoreComposite)
class QuestionnaireConstructScoreCompositeAdmin(admin.ModelAdmin):
    list_display = ('questionnaire_submission', 'composite_construct_scale', 'score')
    search_fields = ('questionnaire_submission', 'composite_construct_scale', 'score')
    list_filter = ('questionnaire_submission', 'composite_construct_scale', 'score')
    ordering = ('-created_date',)