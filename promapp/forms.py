from django import forms
from .models import Questionnaire, Item, QuestionnaireItem, LikertScale, RangeScale, LikertScaleResponseOption, ConstructScale, QuestionnaireItemRule, QuestionnaireItemRuleGroup, CompositeConstructScaleScoring
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Field, Div, HTML, Submit, Button
from django.forms import inlineformset_factory
from django.utils.translation import gettext_lazy as _
from parler.forms import TranslatableModelForm
from parler.forms import TranslatedField
from django.utils.translation import get_language
from django.utils.safestring import mark_safe


class QuestionnaireForm(TranslatableModelForm):
    name = TranslatedField()
    description = TranslatedField(form_class=forms.CharField, widget=forms.Textarea(attrs={'rows': 4}))
    questionnaire_answer_interval = forms.IntegerField(
        required=False,
        min_value=0,
        help_text="Time interval between questionnaire attempts. Leave empty for no restriction.",
        widget=forms.NumberInput(attrs={
            'class': 'interval-value',
            'placeholder': 'Enter number (leave empty for no restriction)'
        })
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
        help_text="Order in which this questionnaire should be displayed. Leave empty to set as 0.",
        widget=forms.NumberInput(attrs={
            'placeholder': 'Enter display order (leave empty for 0)'
        })
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
            if interval and interval > 0:  # Only set if interval is greater than 0
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

    def clean_questionnaire_answer_interval(self):
        """Clean the questionnaire answer interval field."""
        value = self.cleaned_data.get('questionnaire_answer_interval')
        
        # If value is None or empty, that's acceptable - it will be set to 0 in clean()
        if value is not None and value < 0:
            raise forms.ValidationError("Answer interval cannot be negative.")
        
        return value

    def clean_questionnaire_order(self):
        """Clean the questionnaire order field."""
        value = self.cleaned_data.get('questionnaire_order')
        
        # If value is None or empty, that's acceptable - it will be set to 0 in clean()
        if value is not None and value < 0:
            raise forms.ValidationError("Questionnaire order cannot be negative.")
        
        return value

    def clean(self):
        cleaned_data = super().clean()
        interval_value = cleaned_data.get('questionnaire_answer_interval')
        interval_unit = cleaned_data.get('interval_unit')
        questionnaire_order = cleaned_data.get('questionnaire_order')
        
        # Ensure questionnaire_answer_interval is never None
        if interval_value is not None and interval_unit:
            # Convert to seconds based on unit
            if interval_unit == 'minutes':
                cleaned_data['questionnaire_answer_interval'] = interval_value * 60
            elif interval_unit == 'hours':
                cleaned_data['questionnaire_answer_interval'] = interval_value * 3600
            elif interval_unit == 'days':
                cleaned_data['questionnaire_answer_interval'] = interval_value * 86400
            # If interval_unit is 'seconds' or anything else, keep the original value
        else:
            # If no interval is specified, set to 0 (no restriction)
            cleaned_data['questionnaire_answer_interval'] = 0
        
        # Ensure questionnaire_order is never None
        if questionnaire_order is None:
            cleaned_data['questionnaire_order'] = 0
        
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
    
    class Meta:
        model = Item
        fields = [
            'construct_scale', 
            'name', 
            'media',
            'response_type', 
            'likert_response', 
            'range_response', 
            'is_required',
            'item_missing_value',
            'item_better_score_direction',
            'item_threshold_score',
            'item_minimum_clinical_important_difference',
            'item_normative_score_mean',
            'item_normative_score_standard_deviation'
        ]
        widgets = {
            'response_type': forms.Select(attrs={'hx-get': '/promapp/get-response-fields/', 
                                               'hx-target': '#response-fields',
                                               'hx-trigger': 'change'}),
            'likert_response': forms.Select(attrs={'class': 'w-full px-3 py-2 border rounded'}),
            'range_response': forms.Select(attrs={'class': 'w-full px-3 py-2 border rounded'}),
            'is_required': forms.CheckboxInput(attrs={'class': 'w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500 focus:ring-2'}),
            'item_missing_value': forms.NumberInput(attrs={'step': '0.01', 'placeholder': 'Leave blank to use null for missing values'}),
            'item_threshold_score': forms.NumberInput(attrs={'step': '0.01'}),
            'item_minimum_clinical_important_difference': forms.NumberInput(attrs={'step': '0.01'}),
            'item_normative_score_mean': forms.NumberInput(attrs={'step': '0.01'}),
            'item_normative_score_standard_deviation': forms.NumberInput(attrs={'step': '0.01'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.render_unmentioned_fields = False
        self.helper.layout = Layout(
            # Basic Information Section
            Div(
                HTML(f'<h3 class="text-lg font-semibold text-gray-800 mb-4">{_("Item Details")}</h3>'),
                Field('construct_scale'),
                Field('name'),
                Field('media'),
                Field('is_required'),
                Field('response_type'),
                Div(
                    Field('likert_response', css_class='w-full'),
                    Field('range_response', css_class='w-full'),
                    id='response-fields',
                    css_class='mt-3'
                ),
                Field('item_missing_value'),
                css_class='bg-gray-50 p-4 rounded-md mb-6'
            ),
            # Advanced Clinical Settings Section (Collapsible)
            Div(
                HTML(f'''
                    <div class="border border-gray-200 rounded-md">
                        <button type="button" 
                                class="w-full px-4 py-3 text-left bg-gray-100 hover:bg-gray-200 rounded-t-md focus:outline-none focus:ring-2 focus:ring-blue-500 transition-colors duration-200"
                                onclick="toggleAdvancedSettings()"
                                id="advanced-settings-toggle">
                            <div class="flex items-center justify-between">
                                <h3 class="text-lg font-semibold text-gray-800">{_("Advanced Clinical Settings")}</h3>
                                <svg id="chevron-icon" class="w-5 h-5 text-gray-600 transform transition-transform duration-200" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path>
                                </svg>
                            </div>
                            <p class="text-sm text-gray-600 mt-1">{_("Configure scoring direction, thresholds, and normative values for this item")}</p>
                        </button>
                        <div id="advanced-settings-content" class="hidden p-4 space-y-4">
                '''),
                
                # Advanced fields with proper spacing
                Field('item_better_score_direction', css_class='w-full px-3 py-2 border rounded mb-4'),
                Field('item_threshold_score', css_class='w-full px-3 py-2 border rounded mb-4'),
                Field('item_minimum_clinical_important_difference', css_class='w-full px-3 py-2 border rounded mb-4'),
                Field('item_normative_score_mean', css_class='w-full px-3 py-2 border rounded mb-4'),
                Field('item_normative_score_standard_deviation', css_class='w-full px-3 py-2 border rounded mb-4'),
                
                HTML('</div></div>'),
                css_class='mb-6'
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
        fields = [
            'name', 
            'instrument_name', 
            'instrument_version',
            'scale_better_score_direction',
            'scale_threshold_score',
            'scale_minimum_clinical_important_difference',
            'scale_normative_score_mean',
            'scale_normative_score_standard_deviation'
        ]
        widgets = {
            'scale_threshold_score': forms.NumberInput(attrs={'step': '0.01'}),
            'scale_minimum_clinical_important_difference': forms.NumberInput(attrs={'step': '0.01'}),
            'scale_normative_score_mean': forms.NumberInput(attrs={'step': '0.01'}),
            'scale_normative_score_standard_deviation': forms.NumberInput(attrs={'step': '0.01'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            # Basic Information Section
            Div(
                HTML(f'<h3 class="text-lg font-semibold text-gray-800 mb-4">{_("Basic Information")}</h3>'),
                Field('name', css_class='w-full px-3 py-2 border rounded'),
                Field('instrument_name', css_class='w-full px-3 py-2 border rounded'),
                Field('instrument_version', css_class='w-full px-3 py-2 border rounded'),
                css_class='bg-gray-50 p-4 rounded-md mb-6'
            ),
            # Advanced Settings Section (Collapsible)
            Div(
                HTML(f'''
                    <div class="border border-gray-200 rounded-md">
                        <button type="button" 
                                class="w-full px-4 py-3 text-left bg-gray-100 hover:bg-gray-200 rounded-t-md focus:outline-none focus:ring-2 focus:ring-blue-500 transition-colors duration-200"
                                onclick="toggleAdvancedSettings()"
                                id="advanced-settings-toggle">
                            <div class="flex items-center justify-between">
                                <h3 class="text-lg font-semibold text-gray-800">{_("Advanced Clinical Settings")}</h3>
                                <svg id="chevron-icon" class="w-5 h-5 text-gray-600 transform transition-transform duration-200" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path>
                                </svg>
                            </div>
                            <p class="text-sm text-gray-600 mt-1">{_("Configure scoring direction, thresholds, and normative values")}</p>
                        </button>
                        <div id="advanced-settings-content" class="hidden p-4 space-y-4">
                '''),
                
                # Advanced fields with proper spacing
                Field('scale_better_score_direction', css_class='w-full px-3 py-2 border rounded mb-4'),
                Field('scale_threshold_score', css_class='w-full px-3 py-2 border rounded mb-4'),
                Field('scale_minimum_clinical_important_difference', css_class='w-full px-3 py-2 border rounded mb-4'),
                Field('scale_normative_score_mean', css_class='w-full px-3 py-2 border rounded mb-4'),
                Field('scale_normative_score_standard_deviation', css_class='w-full px-3 py-2 border rounded mb-4'),
                
                HTML('</div></div>'),
                css_class='mb-6'
            )
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
        fields = ['option_order', 'option_text', 'option_value', 'option_emoji', 'option_media']
        widgets = {
            'option_emoji': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border rounded emoji-input',
                'placeholder': '😊 Click to select emoji',
                'data-emoji-picker': 'true',
                'maxlength': '10'
            }),
        }



# Update the LikertScaleResponseOptionFormSet to use the custom TranslatableModelForm
LikertScaleResponseOptionFormSet = inlineformset_factory(
    LikertScale, 
    LikertScaleResponseOption, 
    form=LikertScaleResponseOptionForm,
    fields=('option_order', 'option_value', 'option_text', 'option_emoji', 'option_media'),
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
    This form is dynamically created based on the questionnaire items.
    """
    def __init__(self, *args, **kwargs):
        questionnaire_items = kwargs.pop('questionnaire_items', [])
        super().__init__(*args, **kwargs)
        
        # Store questionnaire_items as an instance attribute for use in clean method
        self.questionnaire_items = questionnaire_items
        
        # Get the current language
        current_language = get_language()
        
        for qi in questionnaire_items:
            if qi.item.response_type == 'Text':
                self.fields[f'response_{qi.id}'] = forms.CharField(
                    required=False,
                    widget=forms.Textarea(attrs={
                        'class': 'w-full px-4 py-3 text-lg border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
                        'rows': 3,
                        'placeholder': _('Enter your response here...')
                    })
                )
            elif qi.item.response_type == 'Number':
                self.fields[f'response_{qi.id}'] = forms.IntegerField(
                    required=False,
                    widget=forms.NumberInput(attrs={
                        'class': 'w-full px-4 py-3 text-lg border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
                        'placeholder': _('Enter a number...')
                    })
                )
            elif qi.item.response_type == 'Likert':
                # Get options with fallback to default language
                try:
                    options = qi.item.likert_response.likertscaleresponseoption_set.language(current_language)
                except:
                    # If translation not found, fall back to default language (en-gb)
                    options = qi.item.likert_response.likertscaleresponseoption_set.language('en-gb')
                
                choices = [(option.option_value, option.option_text) for option in options]
                
                self.fields[f'response_{qi.id}'] = forms.ChoiceField(
                    required=False,
                    choices=choices,
                    widget=forms.RadioSelect(attrs={
                        'class': 'likert-options'
                    })
                )
            elif qi.item.response_type == 'Range':
                self.fields[f'response_{qi.id}'] = forms.IntegerField(
                    required=False,
                    min_value=qi.item.range_response.min_value,
                    max_value=qi.item.range_response.max_value,
                    widget=forms.NumberInput(attrs={
                        'class': 'w-full px-4 py-3 text-lg border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
                        'type': 'range',
                        'min': qi.item.range_response.min_value,
                        'max': qi.item.range_response.max_value,
                        'step': qi.item.range_response.increment
                    })
                )
            elif qi.item.response_type == 'Media':
                # For media responses, we'll handle file uploads in the template/JavaScript
                # This field is just for tracking that a media response was provided
                self.fields[f'response_{qi.id}'] = forms.CharField(
                    required=False,
                    widget=forms.HiddenInput()
                )

    def clean(self):
        cleaned_data = super().clean()
        # Convert empty strings to None and ensure all questions have a value (None if unanswered)
        for qi in self.questionnaire_items:
            field_name = f'response_{qi.id}'
            value = cleaned_data.get(field_name)
            if value == '' or value is None:
                cleaned_data[field_name] = None
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
            
            # Order by question number for proper sorting in the dropdown
            self.fields['dependent_item'].queryset = base_queryset.order_by('question_number')
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

        # Check if the questionnaire item being targeted by this rule is required
        if questionnaire_item and questionnaire_item.item.is_required:
            raise forms.ValidationError(
                f'Rule creation not allowed: The question "{questionnaire_item.item.name}" is marked as required for scoring. '
                f'Rules cannot be created for required items as they might prevent the item from being displayed, '
                f'which would make score calculation impossible. Please unmark this item as required first if you want to add visibility rules.'
            )

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

        # Check if the questionnaire item being targeted by rule groups is required
        if questionnaire_item and questionnaire_item.item.is_required:
            raise forms.ValidationError(
                f'Rule group creation not allowed: The question "{questionnaire_item.item.name}" is marked as required for scoring. '
                f'Rule groups cannot be created for required items as they might prevent the item from being displayed, '
                f'which would make score calculation impossible. Please unmark this item as required first if you want to add visibility rule groups.'
            )

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
    
    language_filter = forms.ChoiceField(
        required=False,
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
            'hx-get': '',  # Will be set in the view
            'hx-trigger': 'change',
            'hx-target': '#translation-table',
            'hx-swap': 'innerHTML'
        })
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Create choices for language filter
        from django.conf import settings
        language_choices = [('', _('All Languages'))]
        for lang_code, lang_name in settings.LANGUAGES:
            language_choices.extend([
                (f'{lang_code}_translated', _(f'{lang_name} (Translated)')),
                (f'{lang_code}_untranslated', _(f'{lang_name} (Not Translated)'))
            ])
        
        self.fields['language_filter'].choices = language_choices
        
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Div(
                Div(
                    Field('search'),
                    css_class='w-full md:w-2/3'
                ),
                Div(
                    Field('language_filter'),
                    css_class='w-full md:w-1/3'
                ),
                css_class='flex flex-col md:flex-row gap-4 mb-4'
            )
        )


class ConstructEquationForm(forms.ModelForm):
    """
    Form for managing the equation of a construct scale.
    """
    scale_equation = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'rows': 4,
            'class': 'w-full px-4 py-3 text-base border-2 border-gray-300 rounded-lg shadow-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 font-mono',
            'placeholder': 'Enter equation using {q1}, {q2}, etc. for question references',
            'hx-get': '/promapp/validate-equation/',
            'hx-trigger': 'keyup changed delay:500ms',
            'hx-target': '#equation-validation',
            'hx-include': '[name="scale_id"]'
        })
    )

    class Meta:
        model = ConstructScale
        fields = ['scale_equation']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False

    def clean_scale_equation(self):
        equation = self.cleaned_data.get('scale_equation')
        if equation:
            # Basic validation will be done in the model's validate_scale_equation method
            pass
        return equation


class CompositeConstructScaleScoringForm(forms.ModelForm):
    """
    Form for creating and editing composite construct scale scoring configurations.
    """
    construct_scales = forms.ModelMultipleChoiceField(
        queryset=ConstructScale.objects.all(),
        widget=forms.SelectMultiple(attrs={
            'class': 'form-control',
            'size': '8',
            'multiple': True
        }),
        help_text="Hold Ctrl/Cmd to select multiple construct scales. Type to search within the list."
    )

    class Meta:
        model = CompositeConstructScaleScoring
        fields = ['composite_construct_scale_name', 'construct_scales', 'scoring_type']
        widgets = {
            'composite_construct_scale_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 text-base border-2 border-gray-300 rounded-lg shadow-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500',
                'placeholder': 'Enter composite construct scale name'
            }),
            'scoring_type': forms.Select(attrs={
                'class': 'w-full px-4 py-3 text-base border-2 border-gray-300 rounded-lg shadow-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500'
            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            # Basic Information Section
            Div(
                HTML(f'<h3 class="text-lg font-semibold text-gray-800 mb-4">{_("Basic Information")}</h3>'),
                Field('composite_construct_scale_name', css_class='w-full px-4 py-3 border-2 border-gray-300 rounded-lg'),
                Field('scoring_type', css_class='w-full px-4 py-3 border-2 border-gray-300 rounded-lg'),
                css_class='bg-gray-50 p-4 rounded-md mb-6'
            ),
            # Construct Scales Selection Section
            Div(
                HTML(f'<h3 class="text-lg font-semibold text-gray-800 mb-4">{_("Select Construct Scales")}</h3>'),
                Field('construct_scales', css_class='form-control'),
                HTML('<div class="mt-2 text-sm text-gray-600">'),
                HTML('Hold Ctrl/Cmd and click to select multiple items. At least 2 construct scales are required.'),
                HTML('</div>'),
                css_class='bg-gray-50 p-4 rounded-md mb-6'
            )
        )

        # Update queryset to show construct scales with their details
        self.fields['construct_scales'].queryset = ConstructScale.objects.all().order_by('name')
        
        # Customize the choice labels to include more information
        choices = []
        for construct in self.fields['construct_scales'].queryset:
            label = construct.name
            if construct.instrument_name:
                label += f" ({construct.instrument_name}"
                if construct.instrument_version:
                    label += f" v{construct.instrument_version}"
                label += ")"
            choices.append((construct.id, label))
        
        self.fields['construct_scales'].choices = choices

    def clean_construct_scales(self):
        construct_scales = self.cleaned_data.get('construct_scales')
        if not construct_scales:
            raise forms.ValidationError("Please select at least one construct scale.")
        if len(construct_scales) < 2:
            raise forms.ValidationError("A composite score requires at least two construct scales.")
        return construct_scales

