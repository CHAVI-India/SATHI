# from modeltranslation.translator import translator, TranslationOptions
# from .models import LikertScaleResponseOption, RangeScaleResponseOption, Item, Questionnaire



# class LikertScaleResponseOptionTranslationOptions(TranslationOptions):
#     fields = ('option_text','option_media',)


# class RangeScaleResponseOptionTranslationOptions(TranslationOptions):
#     fields = ('min_value_text','max_value_text',)


# class ItemTranslationOptions(TranslationOptions):
#     fields = ('name',)


# class QuestionnaireTranslationOptions(TranslationOptions):
#     fields = ('name','description',)

# translator.register(LikertScaleResponseOption, LikertScaleResponseOptionTranslationOptions)
# translator.register(RangeScaleResponseOption, RangeScaleResponseOptionTranslationOptions)
# translator.register(Item, ItemTranslationOptions)
# translator.register(Questionnaire, QuestionnaireTranslationOptions)