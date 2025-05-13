from modeltranslation.translator import translator, TranslationOptions, register
from .models import LikertScaleResponseOption, RangeScaleResponseOption, Item, Questionnaire


@register(LikertScaleResponseOption)
class LikertScaleResponseOptionTranslationOptions(TranslationOptions):
    fields = ('option_text','option_media',)

@register(RangeScaleResponseOption)
class RangeScaleResponseOptionTranslationOptions(TranslationOptions):
    fields = ('min_value_text','max_value_text',)

@register(Item)
class ItemTranslationOptions(TranslationOptions):
    fields = ('name',)

@register(Questionnaire)
class QuestionnaireTranslationOptions(TranslationOptions):
    fields = ('name','description',)