from django.contrib import admin
from .models import *
# Register your models here.


class LikertScaleResponseOptionInline(admin.StackedInline):
    model = LikertScaleResponseOption
    extra = 1

class RangeScaleResponseOptionInline(admin.StackedInline):
    model = RangeScaleResponseOption
    extra = 1


class QuestionnaireItemResponseInline(admin.StackedInline):
    model = QuestionnaireItemResponse
    extra = 1

@admin.register(LikertScale)
class LikertScaleAdmin(admin.ModelAdmin):
    inlines = [LikertScaleResponseOptionInline]
    list_display = ('likert_scale_name',)
    search_fields = ('likert_scale_name',)
    list_filter = ('likert_scale_name',)
    ordering = ('-created_date',)
    readonly_fields = ('created_date', 'modified_date')

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

@admin.register(QuestionnaireItemResponse)
class QuestionnaireItemResponseAdmin(admin.ModelAdmin):
    list_display = ('questionnaire', 'patient', 'item', 'item_response_text', 'item_response_number', 'item_response_likert_value', 'item_response_range_min_value', 'item_response_range_max_value', 'response_date_time')
    search_fields = ('questionnaire', 'patient', 'item', 'item_response_text', 'item_response_number', 'item_response_likert_value', 'item_response_range_min_value', 'item_response_range_max_value', 'response_date_time')
    list_filter = ('questionnaire', 'patient', 'item', 'item_response_text', 'item_response_number', 'item_response_likert_value', 'item_response_range_min_value', 'item_response_range_max_value', 'response_date_time')
    ordering = ('-response_date_time',)
    readonly_fields = ('created_date', 'modified_date')

