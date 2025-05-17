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


class QuestionnaireResponseForm(forms.Form):
    """
    Form for handling questionnaire responses.
    This is a dynamic form that will be populated with fields based on the questionnaire items.
    """
    def __init__(self, *args, **kwargs):
        self.questionnaire_items = kwargs.pop('questionnaire_items', [])
        super().__init__(*args, **kwargs)
        
        # Dynamically add fields based on questionnaire items
        for qi in self.questionnaire_items:
            field_name = f'response_{qi.id}'
            
            if qi.item.response_type == 'Text':
                self.fields[field_name] = forms.CharField(
                    required=False,
                    widget=forms.Textarea(attrs={
                        'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
                        'rows': 3,
                        'placeholder': _('Enter your response here...')
                    })
                )
            elif qi.item.response_type == 'Number':
                self.fields[field_name] = forms.DecimalField(
                    required=False,
                    widget=forms.NumberInput(attrs={
                        'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
                        'placeholder': _('Enter a number...')
                    })
                )
            elif qi.item.response_type == 'Likert':
                choices = [(option.option_value, option.option_text) 
                          for option in qi.item.likert_response.likertscaleresponseoption_set.all()]
                self.fields[field_name] = forms.ChoiceField(
                    required=False,
                    choices=choices,
                    widget=forms.RadioSelect(attrs={
                        'class': 'peer sr-only'
                    })
                )
            elif qi.item.response_type == 'Range':
                self.fields[field_name] = forms.DecimalField(
                    required=False,
                    min_value=qi.item.range_response.min_value,
                    max_value=qi.item.range_response.max_value,
                    widget=forms.NumberInput(attrs={
                        'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
                        'type': 'range',
                        'min': qi.item.range_response.min_value,
                        'max': qi.item.range_response.max_value,
                        'step': qi.item.range_response.increment
                    })
                )

    def clean(self):
        cleaned_data = super().clean()
        return cleaned_data

