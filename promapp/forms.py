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
        # Use initial for create, instance for update
        questionnaire_item = self.initial.get('questionnaire_item')
        if self.instance.pk:
            questionnaire_item = getattr(self.instance, 'questionnaire_item', questionnaire_item)
        print('[DEBUG] clean: instance.questionnaire_item =', getattr(self.instance, 'questionnaire_item', None))
        print('[DEBUG] clean: initial[questionnaire_item] =', self.initial.get('questionnaire_item'))
        if dependent_item and questionnaire_item:
            # Ensure dependent item is from the same questionnaire
            if dependent_item.questionnaire != questionnaire_item.questionnaire:
                raise forms.ValidationError(_("Dependent item must be from the same questionnaire."))

            # Validate comparison value based on the dependent item's response type
            if dependent_item.item.response_type == 'Number':
                try:
                    float(comparison_value)
                except (ValueError, TypeError):
                    raise forms.ValidationError(_("Comparison value must be a number for numeric questions."))
            elif dependent_item.item.response_type == 'Likert':
                try:
                    float(comparison_value)
                except (ValueError, TypeError):
                    raise forms.ValidationError(_("Comparison value must be a number for Likert scale questions."))
                # Validate against Likert scale values
                likert_options = dependent_item.item.likert_response.likertscaleresponseoption_set.all()
                valid_values = [option.option_value for option in likert_options]
                if float(comparison_value) not in valid_values:
                    raise forms.ValidationError(_("Comparison value must be a valid Likert scale value."))
            elif dependent_item.item.response_type == 'Range':
                try:
                    value = float(comparison_value)
                    range_scale = dependent_item.item.range_response
                    if not (range_scale.min_value <= value <= range_scale.max_value):
                        raise forms.ValidationError(_("Comparison value must be within the range scale limits."))
                except (ValueError, TypeError):
                    raise forms.ValidationError(_("Comparison value must be a number for range scale questions."))

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

