from django.contrib import admin
from .models import *
from modeltranslation.admin import TranslationAdmin, TranslationStackedInline
# Register your models here.


class LikertScaleResponseOptionInline(TranslationStackedInline):
    model = LikertScaleResponseOption
    fieldsets = (
        (None, {
            'fields': ( 'option_order', 'option_value', ('option_text','option_media'))
        }),
    )
    extra = 1

class RangeScaleResponseOptionInline(TranslationStackedInline):
    model = RangeScaleResponseOption
    fieldsets = (
        (None, {
            'fields': ( 'min_value', 'min_value_text', 'max_value', 'max_value_text', 'increment')
        }),
    )
    extra = 1
    group_fieldsets = True


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
    inlines = [RangeScaleResponseOptionInline]
    list_display = ('range_scale_name',)
    search_fields = ('range_scale_name',)
    list_filter = ('range_scale_name',)
    ordering = ('-created_date',)
    readonly_fields = ('created_date', 'modified_date')

@admin.register(Questionnaire)
class QuestionnaireAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
    list_filter = ('name',)
    ordering = ('-created_date',)
    readonly_fields = ('created_date', 'modified_date')

@admin.register(QuestionnaireItem)
class QuestionnaireItemAdmin(admin.ModelAdmin):
    list_display = ('questionnaire', 'item', 'question_number')
    search_fields = ('questionnaire', 'item', 'question_number')
    list_filter = ('questionnaire', 'item', 'question_number')
    ordering = ('-created_date',)
    readonly_fields = ('created_date', 'modified_date')


@admin.register(ConstructScale)
class ConstructScaleAdmin(admin.ModelAdmin):
    list_display = ('name','instrument_name','instrument_version')
    exclude = ('created_date', 'modified_date')
    search_fields = ('name','instrument_name','instrument_version')
    list_filter = ('instrument_name','instrument_version')
    ordering = ('-created_date',)
    readonly_fields = ('created_date', 'modified_date')


@admin.register(Item)
class ItemAdmin(TranslationAdmin):
    list_display = ('construct_scale', 'name', 'response_type')
    search_fields = ('construct_scale', 'name', 'response_type')
    list_filter = ('response_type',)
    ordering = ('-created_date',)
    readonly_fields = ('created_date', 'modified_date')
    group_fieldsets = True