from django.contrib import admin
from .models import *
from parler.admin import TranslatableAdmin, TranslatableStackedInline
# Import export section
from import_export import resources
from import_export.admin import ImportExportActionModelAdmin, ImportExportModelAdmin
from import_export import fields
from import_export.widgets import ForeignKeyWidget
from .resources import ItemResource
from allauth.account.decorators import secure_admin_login



#from modeltranslation.admin import TranslationAdmin, TranslationStackedInline
# Register your models here.



admin.autodiscover()
admin.site.login = secure_admin_login(admin.site.login)

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


class LikertScaleResponseOptionImportResource(resources.ModelResource):
    class Meta:
        model = LikertScaleResponseOption
        import_id_fields = ['id']  # Use UUID as the import identifier
        fields = ('id', 'likert_scale', 'option_order', 'option_value', 'option_text')
        export_order = fields

    def before_import_row(self, row, **kwargs):
        """
        Handle UUID generation for new records during import
        """
        if not row.get('id'):
            row['id'] = str(uuid.uuid4())
    
    def get_instance(self, instance_loader, row):
        """
        Override to handle UUID lookup
        """
        try:
            return self.get_queryset().get(id=row['id'])
        except (self.Meta.model.DoesNotExist, KeyError):
            return None


@admin.register(LikertScaleResponseOption)
class LikertScaleResponseOptionAdmin(TranslatableAdmin, ImportExportActionModelAdmin):
    resource_classes = [LikertScaleResponseOptionImportResource]
    list_display = ('likert_scale', 'option_order', 'get_option_text', 'option_value', 'option_emoji')
    search_fields = ('likert_scale', 'option_order', 'translations__option_text', 'option_value', 'option_emoji')
    list_filter = ('likert_scale',)
    ordering = ('-created_date',)
    readonly_fields = ('created_date', 'modified_date')
    
    # Parler translation settings
    fieldsets = (
        (None, {
            'fields': ('likert_scale', 'option_order', 'option_value', 'option_emoji')
        }),
        ('Translations', {
            'fields': ('option_text', 'option_media'),
            'classes': ('parler-translatable',)
        }),
    )

    def get_option_text(self, obj):
        """Get the translated option text for the current language"""
        return obj.safe_translation_getter('option_text', any_language=True)
    get_option_text.short_description = 'Option Text'


class QuestionnaireItemInline(admin.StackedInline):
    model = QuestionnaireItem
    extra = 1

class LikertScaleImportResource(resources.ModelResource):
    class Meta:
        model = LikertScale
        import_id_fields = ['id']  # Use UUID as the import identifier
        fields = ('id', 'likert_scale_name')
        export_order = fields

    def before_import_row(self, row, **kwargs):
        """
        Handle UUID generation for new records during import
        """
        if not row.get('id'):
            row['id'] = str(uuid.uuid4())

    def get_instance(self, instance_loader, row):
        """
        Override to handle UUID lookup
        """
        try:
            return self.get_queryset().get(id=row['id'])
        except (self.Meta.model.DoesNotExist, KeyError):
            return None        

@admin.register(LikertScale)
class LikertScaleAdmin(ImportExportActionModelAdmin):
    inlines = [LikertScaleResponseOptionInline]
    list_display = ('likert_scale_name',)
    search_fields = ('likert_scale_name',)
    list_filter = ('likert_scale_name',)
    ordering = ('-created_date',)
    readonly_fields = ('created_date', 'modified_date')
    group_fieldsets = True
    resource_classes = [LikertScaleImportResource]

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
        import_id_fields = ['id']  # Use UUID as the import identifier
        fields = ('id', 'name', 'instrument_name', 'instrument_version', 'scale_equation',
                 'minimum_number_of_items', 'scale_better_score_direction', 'scale_threshold_score',
                 'scale_minimum_clinical_important_difference', 'scale_normative_score_mean',
                 'scale_normative_score_standard_deviation')
        export_order = fields

    def before_import_row(self, row, **kwargs):
        """
        Handle UUID generation for new records during import
        """
        if not row.get('id'):
            row['id'] = str(uuid.uuid4())

    def get_instance(self, instance_loader, row):
        """
        Override to handle UUID lookup
        """
        try:
            return self.get_queryset().get(id=row['id'])
        except (self.Meta.model.DoesNotExist, KeyError):
            return None

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
class ItemAdmin(ImportExportModelAdmin):
    resource_class = ItemResource
    list_display = ('name', 'item_number', 'response_type', 'get_related_constructs')
    list_filter = ('response_type', 'construct_scale')
    search_fields = ('translations__name', 'item_number')


@admin.register(QuestionnaireSubmission)
class QuestionnaireSubmissionAdmin(admin.ModelAdmin):
    list_display = ('patient', 'patient_questionnaire', 'user_submitting_questionnaire', 'submission_date')
    search_fields = ('patient__name', 'patient_questionnaire__questionnaire__name', 'user_submitting_questionnaire__username')
    list_filter = ('patient', 'patient_questionnaire', 'user_submitting_questionnaire', 'submission_date')
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