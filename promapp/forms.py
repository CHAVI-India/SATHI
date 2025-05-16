from django import forms
from .models import Questionnaire, Item, QuestionnaireItem, LikertScale, RangeScale, LikertScaleResponseOption, ConstructScale
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Field, Div, HTML, Submit, Button
from django.forms import inlineformset_factory
from django.utils.translation import gettext_lazy as _
from parler.forms import TranslatableModelForm
from parler.forms import TranslatedField
from django.utils.translation import get_language


class QuestionnaireForm(TranslatableModelForm):
    name = TranslatedField()
    description = TranslatedField(form_class=forms.CharField, widget=forms.Textarea(attrs={'rows': 4}))
    
    class Meta:
        model = Questionnaire
        fields = ['name', 'description']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Field('name', css_class='w-full px-3 py-2 border rounded'),
            Field('description', css_class='w-full px-3 py-2 border rounded'),
        )


class ItemSelectionForm(forms.Form):
    items = forms.ModelMultipleChoiceField(
        queryset=Item.objects.none(),  # Will be set in __init__
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label=_("Select Items for Questionnaire")
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Get properly translated items in the current language
        current_language = get_language()
        self.fields['items'].queryset = Item.objects.language(current_language).all()
        
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Field('items', css_class='space-y-2'),
        )


class ItemForm(TranslatableModelForm):
    name = TranslatedField()
    media = TranslatedField(required=False)
    
    class Meta:
        model = Item
        fields = ['construct_scale', 'name', 'response_type', 'likert_response', 'range_response']
        widgets = {
            'response_type': forms.Select(attrs={'hx-get': '/promapp/get-response-fields/', 
                                               'hx-target': '#response-fields',
                                               'hx-trigger': 'change'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Field('construct_scale'),
            Field('name'),
            Field('media'),
            Field('response_type'),
            Div(
                Field('likert_response', css_class='w-full'),
                Field('range_response', css_class='w-full'),
                id='response-fields',
                css_class='mt-3'
            )
        )
        
        # Hide the appropriate fields based on the response type
        if self.instance.pk:
            if self.instance.response_type != 'Likert':
                self.fields['likert_response'].widget = forms.HiddenInput()
            if self.instance.response_type != 'Range':
                self.fields['range_response'].widget = forms.HiddenInput()
        else:
            self.fields['likert_response'].widget = forms.HiddenInput()
            self.fields['range_response'].widget = forms.HiddenInput()


class ConstructScaleForm(forms.ModelForm):
    class Meta:
        model = ConstructScale
        fields = ['name', 'instrument_name', 'instrument_version']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Field('name', css_class='w-full px-3 py-2 border rounded'),
            Field('instrument_name', css_class='w-full px-3 py-2 border rounded'),
            Field('instrument_version', css_class='w-full px-3 py-2 border rounded'),
        )


class LikertScaleForm(forms.ModelForm):
    class Meta:
        model = LikertScale
        fields = ['likert_scale_name']


class LikertScaleResponseOptionForm(TranslatableModelForm):
    option_text = TranslatedField()
    option_media = TranslatedField(required=False)
    
    class Meta:
        model = LikertScaleResponseOption
        fields = ['option_order', 'option_text', 'option_value', 'option_media']



# Update the LikertScaleResponseOptionFormSet to use the custom TranslatableModelForm
LikertScaleResponseOptionFormSet = inlineformset_factory(
    LikertScale, 
    LikertScaleResponseOption, 
    form=LikertScaleResponseOptionForm,
    fields=('option_order', 'option_value', 'option_text', 'option_media'),
    extra=1,
    can_delete=True
)



class QuestionnaireItemForm(forms.ModelForm):
    class Meta:
        model = QuestionnaireItem
        fields = ['questionnaire', 'item']
        # Excluding response fields as they will be filled when patient responds


class RangeScaleForm(TranslatableModelForm):
    min_value_text = TranslatedField()
    max_value_text = TranslatedField()
    
    class Meta:
        model = RangeScale
        fields = ['range_scale_name', 'min_value', 'max_value', 'increment', 'min_value_text', 'max_value_text']
        widgets = {
            'min_value': forms.NumberInput(attrs={'step': '0.01'}),
            'max_value': forms.NumberInput(attrs={'step': '0.01'}),
            'increment': forms.NumberInput(attrs={'step': '0.01'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Field('range_scale_name', css_class='w-full px-3 py-2 border rounded'),
            Field('min_value', css_class='w-full px-3 py-2 border rounded'),
            Field('max_value', css_class='w-full px-3 py-2 border rounded'),
            Field('increment', css_class='w-full px-3 py-2 border rounded'),
            Field('min_value_text', css_class='w-full px-3 py-2 border rounded'),
            Field('max_value_text', css_class='w-full px-3 py-2 border rounded'),
        )

