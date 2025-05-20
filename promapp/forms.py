from django import forms
from .models import Questionnaire, Item, QuestionnaireItem, LikertScale, RangeScale, LikertScaleResponseOption, ConstructScale, QuestionnaireItemRule, QuestionnaireItemRuleGroup
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
    questionnaire_answer_interval = forms.IntegerField(
        required=False,
        min_value=0,
        help_text="Time interval between questionnaire attempts",
        widget=forms.NumberInput(attrs={'class': 'interval-value'})
    )
    interval_unit = forms.ChoiceField(
        required=False,
        choices=[
            ('seconds', 'Seconds'),
            ('minutes', 'Minutes'),
            ('hours', 'Hours'),
            ('days', 'Days'),
        ],
        initial='seconds',
        widget=forms.Select(attrs={'class': 'interval-unit'})
    )
    questionnaire_order = forms.IntegerField(
        required=False,
        min_value=0,
        help_text="Order in which this questionnaire should be displayed"
    )
    questionnaire_redirect = forms.ModelChoiceField(
        required=False,
        queryset=Questionnaire.objects.all(),
        help_text="Questionnaire to redirect to after completion",
        empty_label="No redirect"
    )

    class Meta:
        model = Questionnaire
        fields = ['name', 'description', 'questionnaire_answer_interval', 'questionnaire_order', 'questionnaire_redirect']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Field('name', css_class='w-full px-3 py-2 border rounded'),
            Field('description', css_class='w-full px-3 py-2 border rounded'),
        )
        # Exclude current questionnaire from redirect choices if editing
        if self.instance and self.instance.pk:
            self.fields['questionnaire_redirect'].queryset = Questionnaire.objects.exclude(pk=self.instance.pk)
        
        # Set initial values for interval fields if editing
        if self.instance and self.instance.pk:
            interval = self.instance.questionnaire_answer_interval
            if interval:
                if interval < 60:
                    self.initial['interval_unit'] = 'seconds'
                    self.initial['questionnaire_answer_interval'] = interval
                elif interval < 3600:
                    self.initial['interval_unit'] = 'minutes'
                    self.initial['questionnaire_answer_interval'] = interval // 60
                elif interval < 86400:
                    self.initial['interval_unit'] = 'hours'
                    self.initial['questionnaire_answer_interval'] = interval // 3600
                else:
                    self.initial['interval_unit'] = 'days'
                    self.initial['questionnaire_answer_interval'] = interval // 86400

    def clean(self):
        cleaned_data = super().clean()
        interval_value = cleaned_data.get('questionnaire_answer_interval')
        interval_unit = cleaned_data.get('interval_unit')
        
        if interval_value is not None and interval_unit:
            # Convert to seconds based on unit
            if interval_unit == 'minutes':
                cleaned_data['questionnaire_answer_interval'] = interval_value * 60
            elif interval_unit == 'hours':
                cleaned_data['questionnaire_answer_interval'] = interval_value * 3600
            elif interval_unit == 'days':
                cleaned_data['questionnaire_answer_interval'] = interval_value * 86400
        
        return cleaned_data


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
            'likert_response': forms.Select(attrs={'class': 'w-full px-3 py-2 border rounded'}),
            'range_response': forms.Select(attrs={'class': 'w-full px-3 py-2 border rounded'}),
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
        
        # Set the querysets for the response fields
        self.fields['likert_response'].queryset = LikertScale.objects.all()
        self.fields['range_response'].queryset = RangeScale.objects.all()
        
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


class QuestionnaireItemRuleForm(forms.ModelForm):
    """
    Form for creating and editing questionnaire item rules.
    """
    class Meta:
        model = QuestionnaireItemRule
        fields = ['dependent_item', 'operator', 'comparison_value', 'logical_operator', 'rule_order']
        widgets = {
            'operator': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border rounded',
                'hx-get': '/promapp/validate-rule-operator/',
                'hx-trigger': 'change',
                'hx-target': '#comparison-value-container',
                'hx-swap': 'innerHTML'
            }),
            'comparison_value': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border rounded',
                'hx-get': '/promapp/validate-comparison-value/',
                'hx-trigger': 'change',
                'hx-target': '#comparison-value-feedback',
                'hx-swap': 'innerHTML'
            }),
            'logical_operator': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border rounded',
                'hx-get': '/promapp/validate-logical-operator/',
                'hx-trigger': 'change',
                'hx-target': '#logical-operator-feedback',
                'hx-swap': 'innerHTML'
            }),
            'rule_order': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border rounded',
                'min': '1',
                'hx-get': '/promapp/validate-rule-order/',
                'hx-trigger': 'change',
                'hx-target': '#rule-order-feedback',
                'hx-swap': 'innerHTML'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        questionnaire_item = getattr(self.instance, 'questionnaire_item', None) or kwargs.get('initial', {}).get('questionnaire_item')
        print('[DEBUG] __init__: instance.questionnaire_item =', getattr(self.instance, 'questionnaire_item', None))
        print('[DEBUG] __init__: initial[questionnaire_item] =', kwargs.get('initial', {}).get('questionnaire_item'))
        
        if questionnaire_item:
            # Get all items from the same questionnaire
            base_queryset = QuestionnaireItem.objects.filter(
                questionnaire=questionnaire_item.questionnaire
            )
            
            # If we have a question number, filter for items that come before this one
            if questionnaire_item.question_number is not None:
                base_queryset = base_queryset.filter(
                    question_number__lt=questionnaire_item.question_number
                )
            
            self.fields['dependent_item'].queryset = base_queryset
        else:
            self.fields['dependent_item'].queryset = QuestionnaireItem.objects.none()
            
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Div(
                Field('dependent_item', 
                      css_class='w-full px-3 py-2 border rounded',
                      hx_get='/promapp/validate-dependent-item/',
                      hx_trigger='change',
                      hx_target='#dependent-item-feedback',
                      hx_swap='innerHTML'),
                Div(id='dependent-item-feedback'),
                css_class='mb-4'
            ),
            Div(
                Field('operator'),
                Div(id='comparison-value-container'),
                css_class='mb-4'
            ),
            Div(
                Field('comparison_value'),
                Div(id='comparison-value-feedback'),
                css_class='mb-4'
            ),
            Div(
                Field('logical_operator'),
                Div(id='logical-operator-feedback'),
                css_class='mb-4'
            ),
            Div(
                Field('rule_order'),
                Div(id='rule-order-feedback'),
                css_class='mb-4'
            ),
        )

        # Add HTMX attributes to dependent_item field
        self.fields['dependent_item'].widget.attrs.update({
            'hx-get': '/promapp/validate-dependent-item/',
            'hx-trigger': 'change',
            'hx-target': '#dependent-item-feedback',
            'hx-swap': 'innerHTML'
        })

    def clean(self):
        cleaned_data = super().clean()
        dependent_item = cleaned_data.get('dependent_item')
        operator = cleaned_data.get('operator')
        comparison_value = cleaned_data.get('comparison_value')
        questionnaire_item = self.initial.get('questionnaire_item')
        if self.instance.pk:
            questionnaire_item = getattr(self.instance, 'questionnaire_item', questionnaire_item)

        if dependent_item and questionnaire_item:
            # Ensure dependent item is from the same questionnaire
            if dependent_item.questionnaire != questionnaire_item.questionnaire:
                raise forms.ValidationError(
                    f'Rule validation failed: The dependent question "{dependent_item.item.name}" belongs to a different questionnaire than the current question "{questionnaire_item.item.name}". Please select a question from the same questionnaire.'
                )

            # Validate comparison value based on the dependent item's response type
            if dependent_item.item.response_type == 'Number':
                try:
                    float(comparison_value)
                except (ValueError, TypeError):
                    raise forms.ValidationError(
                        f'Rule validation failed: The comparison value "{comparison_value}" must be a valid number for the numeric question "{dependent_item.item.name}".'
                    )
            elif dependent_item.item.response_type == 'Likert':
                try:
                    float_value = float(comparison_value)
                    likert_options = dependent_item.item.likert_response.likertscaleresponseoption_set.all()
                    valid_values = [option.option_value for option in likert_options]
                    if float_value not in valid_values:
                        valid_values_str = ', '.join(map(str, valid_values))
                        raise forms.ValidationError(
                            f'Rule validation failed: The comparison value "{comparison_value}" is not a valid option for the Likert scale question "{dependent_item.item.name}". Valid values are: {valid_values_str}'
                        )
                except (ValueError, TypeError):
                    raise forms.ValidationError(
                        f'Rule validation failed: The comparison value "{comparison_value}" must be a valid number for the Likert scale question "{dependent_item.item.name}".'
                    )
            elif dependent_item.item.response_type == 'Range':
                try:
                    value = float(comparison_value)
                    range_scale = dependent_item.item.range_response
                    if not (range_scale.min_value <= value <= range_scale.max_value):
                        raise forms.ValidationError(
                            f'Rule validation failed: The comparison value "{comparison_value}" must be between {range_scale.min_value} and {range_scale.max_value} for the range scale question "{dependent_item.item.name}".'
                        )
                except (ValueError, TypeError):
                    raise forms.ValidationError(
                        f'Rule validation failed: The comparison value "{comparison_value}" must be a valid number for the range scale question "{dependent_item.item.name}".'
                    )

        return cleaned_data


class QuestionnaireItemRuleGroupForm(forms.ModelForm):
    """
    Form for creating and editing questionnaire item rule groups.
    """
    rules = forms.ModelMultipleChoiceField(
        queryset=QuestionnaireItemRule.objects.none(),
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'space-y-2',
            'hx-get': '/promapp/validate-rule-selection/',
            'hx-trigger': 'change',
            'hx-target': '#rule-selection-feedback',
            'hx-swap': 'innerHTML'
        }),
        required=True,
        label=_("Select Rules")
    )

    class Meta:
        model = QuestionnaireItemRuleGroup
        fields = ['group_order']
        widgets = {
            'group_order': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border rounded',
                'min': '1',
                'hx-get': '/promapp/validate-group-order/',
                'hx-trigger': 'change',
                'hx-target': '#group-order-feedback',
                'hx-swap': 'innerHTML'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Use questionnaire_item from instance or initial
        questionnaire_item = getattr(self.instance, 'questionnaire_item', None) or kwargs.get('initial', {}).get('questionnaire_item')
        if questionnaire_item:
            self.fields['rules'].queryset = QuestionnaireItemRule.objects.filter(
                questionnaire_item=questionnaire_item
            )
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Div(
                Field('group_order'),
                Div(id='group-order-feedback'),
                css_class='mb-4'
            ),
            Div(
                Field('rules'),
                Div(id='rule-selection-feedback'),
                css_class='mb-4'
            ),
        )

    def clean(self):
        cleaned_data = super().clean()
        rules = cleaned_data.get('rules')
        questionnaire_item = self.instance.questionnaire_item if self.instance.pk else self.initial.get('questionnaire_item')

        if rules and questionnaire_item:
            # Ensure all selected rules belong to the same questionnaire item
            for rule in rules:
                if rule.questionnaire_item != questionnaire_item:
                    raise forms.ValidationError(_("All rules must belong to the same questionnaire item."))

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        if commit:
            instance.save()
            # Update the many-to-many relationship
            instance.rules.set(self.cleaned_data['rules'])
        return instance


# Translation Forms
class ItemTranslationForm(TranslatableModelForm):
    """
    Form for translating Item model.
    """
    name = TranslatedField(
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 text-lg border-2 border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            'placeholder': 'Enter item name'
        })
    )
    media = TranslatedField(
        required=False,
        widget=forms.ClearableFileInput(attrs={
            'class': 'w-full px-4 py-2 text-lg border-2 border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent',
        })
    )

    class Meta:
        model = Item
        fields = ['name', 'media']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Div(
                Field('name', wrapper_class='mb-4'),
                Field('media', wrapper_class='mb-4'),
                css_class='space-y-4'
            )
        )

class QuestionnaireTranslationForm(TranslatableModelForm):
    """
    Form for translating Questionnaire model.
    """
    name = TranslatedField(
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 text-lg border-2 border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            'placeholder': 'Enter questionnaire name'
        })
    )
    description = TranslatedField(
        form_class=forms.CharField,
        widget=forms.Textarea(attrs={
            'class': 'w-full px-4 py-2 text-lg border-2 border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            'rows': 4,
            'placeholder': 'Enter questionnaire description'
        })
    )
    
    class Meta:
        model = Questionnaire
        fields = ['name', 'description']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Div(
                Field('name', wrapper_class='mb-4'),
                Field('description', wrapper_class='mb-4'),
                css_class='space-y-4'
            )
        )

class LikertScaleResponseOptionTranslationForm(TranslatableModelForm):
    """
    Form for translating LikertScaleResponseOption model.
    """
    option_text = TranslatedField(
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 text-lg border-2 border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            'placeholder': 'Enter option text'
        })
    )
    option_media = TranslatedField(
        required=False,
        widget=forms.ClearableFileInput(attrs={
            'class': 'w-full px-4 py-2 text-lg border-2 border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent',
        })
    )
    
    class Meta:
        model = LikertScaleResponseOption
        fields = ['option_text', 'option_media']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Div(
                Field('option_text', wrapper_class='mb-4'),
                Field('option_media', wrapper_class='mb-4'),
                css_class='space-y-4'
            )
        )

class RangeScaleTranslationForm(TranslatableModelForm):
    """
    Form for translating RangeScale model.
    """
    min_value_text = TranslatedField(
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 text-lg border-2 border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            'placeholder': 'Enter min value text'
        })
    )
    max_value_text = TranslatedField(
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 text-lg border-2 border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            'placeholder': 'Enter max value text'
        })
    )
    
    class Meta:
        model = RangeScale
        fields = ['min_value_text', 'max_value_text']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Div(
                Field('min_value_text', wrapper_class='mb-4'),
                Field('max_value_text', wrapper_class='mb-4'),
                css_class='space-y-4'
            )
        )

class TranslationSearchForm(forms.Form):
    """
    Form for searching and filtering translation lists.
    """
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
            'placeholder': _('Search...'),
            'hx-get': '',  # Will be set in the view
            'hx-trigger': 'keyup changed delay:500ms',
            'hx-target': '#translation-table',
            'hx-swap': 'innerHTML'
        })
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Div(
                Field('search'),
                css_class='mb-4'
            )
        )

