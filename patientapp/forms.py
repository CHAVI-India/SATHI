from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User, Group
from .models import (
    Patient, Institution, Treatment, Diagnosis, DiagnosisList, Project, PatientProject,
    ProjectRedcapMapping, RedcapFormToQuestionnaireMapping,
    RedcapFieldToItemMapping, RedcapStudyIDtoPatientIDMap,
)
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Field, Div, Submit, HTML
from django.utils.translation import gettext_lazy as _

INPUT_CLASS = 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500'
SELECT_CLASS = 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white'
CHECKBOX_CLASS = 'h-4 w-4 text-blue-600 border-gray-300 rounded'

class PatientForm(forms.ModelForm):
    # User fields
    username = forms.CharField(max_length=150, required=True)
    email = forms.EmailField(required=True)
    password1 = forms.CharField(
        widget=forms.PasswordInput(),
        required=True,
        label=_('Password')
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput(),
        required=True,
        label=_('Repeat Password')
    )
    groups = forms.ModelMultipleChoiceField(
        queryset=Group.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label=_('Groups')
    )
    
    class Meta:
        model = Patient
        fields = ['patient_id', 'name', 'age', 'gender', 'institution','date_of_registration', 'preferred_language', 'username', 'email', 'password1', 'password2', 'groups']
        widgets = {
            'age': forms.NumberInput(attrs={'min': 0, 'max': 150}),
            'password1': forms.PasswordInput(),
            'password2': forms.PasswordInput(),
            'date_of_registration': forms.DateInput(attrs={'type': 'date'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            # User Account Information
            HTML('<h3 class="text-lg font-medium text-gray-900 mb-4">{% translate "User Account Information" %}</h3>'),
            Div(
                Field('username', css_class='w-full px-3 py-2 border rounded'),
                Field('email', css_class='w-full px-3 py-2 border rounded'),
                css_class='space-y-4'
            ),
            
            # Password Section
            HTML('<h3 class="text-lg font-medium text-gray-900 mt-6 mb-4">{% translate "Password" %}</h3>'),
            Div(
                Field('password1', css_class='w-full px-3 py-2 border rounded'),
                Field('password2', css_class='w-full px-3 py-2 border rounded'),
                css_class='space-y-4'
            ),
            
            # Patient Information
            HTML('<h3 class="text-lg font-medium text-gray-900 mt-6 mb-4">{% translate "Patient Information" %}</h3>'),
            Div(
                Field('name', css_class='w-full px-3 py-2 border rounded'),
                Field('patient_id', css_class='w-full px-3 py-2 border rounded'),
                Field('age', css_class='w-full px-3 py-2 border rounded'),
                Field('gender', css_class='w-full px-3 py-2 border rounded'),
                Field('institution', css_class='w-full px-3 py-2 border rounded'),
                Field('date_of_registration',css_class='w-full px-3 py-2 border rounded'),
                Field('preferred_language', css_class='w-full px-3 py-2 border rounded'),
                css_class='space-y-4'
            ),
            
            # Groups Section
            HTML('<h3 class="text-lg font-medium text-gray-900 mt-6 mb-4">{% translate "User Groups" %}</h3>'),
            Div(
                Field('groups', css_class='space-y-2'),
                css_class='mt-2'
            )
        )
    
    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError(_("Passwords don't match"))
        return password2
    
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError(_("A user with that username already exists."))
        return username
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError(_("A user with that email already exists."))
        return email

class DiagnosisListForm(forms.ModelForm):
    class Meta:
        model = DiagnosisList
        fields = ['diagnosis', 'icd_11_code']
        labels = {
            'diagnosis': _('Diagnosis Name'),
            'icd_11_code': _('ICD-11 Code'),
        }

class DiagnosisForm(forms.ModelForm):
    class Meta:
        model = Diagnosis
        fields = ['diagnosis', 'date_of_diagnosis']
        widgets = {
            'date_of_diagnosis': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.date_of_diagnosis:
            self.initial['date_of_diagnosis'] = self.instance.date_of_diagnosis.strftime('%Y-%m-%d')

class PatientRestrictedUpdateForm(forms.ModelForm):
    class Meta:
        model = Patient
        fields = ['age', 'gender', 'institution', 'date_of_registration', 'preferred_language']
        widgets = {
            'age': forms.NumberInput(attrs={'min': 0, 'max': 150}),
            'date_of_registration': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.date_of_registration:
            self.initial['date_of_registration'] = self.instance.date_of_registration.strftime('%Y-%m-%d')
        
        # If you want to use crispy forms helper for this new form:
        # self.helper = FormHelper()
        # self.helper.form_tag = False # To prevent crispy from rendering the <form> tag
        # self.helper.layout = Layout(
        #     Field('age', css_class='w-full px-3 py-2 border rounded'),
        #     Field('gender', css_class='w-full px-3 py-2 border rounded'),
        #     Field('institution', css_class='w-full px-3 py-2 border rounded'),
        #     Field('date_of_registration', css_class='w-full px-3 py-2 border rounded'),
        # )
class TreatmentForm(forms.ModelForm):
    class Meta:
        model = Treatment
        fields = ['treatment_type', 'treatment_intent', 'date_of_start_of_treatment', 'currently_ongoing_treatment', 'date_of_end_of_treatment']
        widgets = {
            'date_of_start_of_treatment': forms.DateInput(attrs={'type': 'date'}),
            'date_of_end_of_treatment': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            if self.instance.date_of_start_of_treatment:
                self.initial['date_of_start_of_treatment'] = self.instance.date_of_start_of_treatment.strftime('%Y-%m-%d')
            if self.instance.date_of_end_of_treatment:
                self.initial['date_of_end_of_treatment'] = self.instance.date_of_end_of_treatment.strftime('%Y-%m-%d')

class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ['project_name']
        labels = {
            'project_name': _('Project Name'),
        }
        widgets = {
            'project_name': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'placeholder': _('Enter project name')
            }),
        }

class PatientProjectForm(forms.ModelForm):
    class Meta:
        model = PatientProject
        fields = ['project', 'date_patient_enrolled_in_project', 'date_patient_exited_from_project']
        labels = {
            'project': _('Project'),
            'date_patient_enrolled_in_project': _('Date Enrolled'),
            'date_patient_exited_from_project': _('Date Exited'),
        }
        widgets = {
            'project': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
            }),
            'date_patient_enrolled_in_project': forms.DateInput(attrs={
                'type': 'date',
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
            }),
            'date_patient_exited_from_project': forms.DateInput(attrs={
                'type': 'date',
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
            }),
        }

    def __init__(self, *args, **kwargs):
        patient = kwargs.pop('patient', None)
        super().__init__(*args, **kwargs)
        
        # Filter projects to exclude ones already assigned to this patient (for new assignments)
        if patient and not self.instance.pk:
            existing_project_ids = PatientProject.objects.filter(patient=patient).values_list('project_id', flat=True)
            self.fields['project'].queryset = Project.objects.exclude(id__in=existing_project_ids)
        
        # Set initial values for date fields if instance exists
        if self.instance and self.instance.pk:
            if self.instance.date_patient_enrolled_in_project:
                self.initial['date_patient_enrolled_in_project'] = self.instance.date_patient_enrolled_in_project.strftime('%Y-%m-%d')
            if self.instance.date_patient_exited_from_project:
                self.initial['date_patient_exited_from_project'] = self.instance.date_patient_exited_from_project.strftime('%Y-%m-%d')

    def clean(self):
        cleaned_data = super().clean()
        project = cleaned_data.get('project')
        enrollment_date = cleaned_data.get('date_patient_enrolled_in_project')
        exit_date = cleaned_data.get('date_patient_exited_from_project')
        
        # Check for duplicate patient-project assignment (for new assignments only)
        if project and not self.instance.pk and hasattr(self, 'patient') and self.patient:
            if PatientProject.objects.filter(patient=self.patient, project=project).exists():
                raise forms.ValidationError(_('This patient is already assigned to this project.'))
        
        # Validate that exit date is after enrollment date
        if enrollment_date and exit_date and exit_date < enrollment_date:
            raise forms.ValidationError(_('Exit date cannot be before enrollment date.'))
        
        return cleaned_data


class ProjectRedcapMappingForm(forms.ModelForm):
    redcap_project_token = forms.CharField(
        widget=forms.PasswordInput(render_value=False, attrs={'class': INPUT_CLASS, 'autocomplete': 'new-password'}),
        label=_('REDCap API Token'),
        help_text=_('Enter the API token. Leave blank on edit to keep the existing token.'),
        required=False,
    )

    class Meta:
        model = ProjectRedcapMapping
        fields = [
            'redcap_project_url', 'redcap_project_token',
            'redcap_project_token_allows_import', 'redcap_project_token_allows_export',
            'export_type',
        ]
        labels = {
            'redcap_project_url': _('REDCap Project URL'),
            'redcap_project_token_allows_import': _('Token allows import into REDCap'),
            'redcap_project_token_allows_export': _('Token allows export from REDCap'),
            'export_type': _('Export Type'),
        }
        widgets = {
            'redcap_project_url': forms.URLInput(attrs={'class': INPUT_CLASS}),
            'export_type': forms.Select(attrs={'class': SELECT_CLASS}),
            'redcap_project_token_allows_import': forms.CheckboxInput(attrs={'class': CHECKBOX_CLASS}),
            'redcap_project_token_allows_export': forms.CheckboxInput(attrs={'class': CHECKBOX_CLASS}),
        }

    def clean_redcap_project_token(self):
        token = self.cleaned_data.get('redcap_project_token', '').strip()
        if not token:
            if self.instance and self.instance.pk:
                return self.instance.redcap_project_token
            raise forms.ValidationError(_('API token is required when creating a new configuration.'))
        return token


class RedcapIDFieldsForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        field_choices = [('', _('--- Select Field ---'))]
        instance = kwargs.get('instance')
        if instance and instance.redcap_project_info:
            for field in instance.redcap_project_info.get('metadata', []):
                fname = field.get('field_name', '')
                flabel = field.get('field_label', fname)
                if fname:
                    field_choices.append((fname, f"{flabel} ({fname})"))
        self.fields['redcap_study_id_field'] = forms.ChoiceField(
            choices=field_choices,
            label=_('Study ID Field'),
            help_text=_('The REDCap field used as the primary record/study identifier.'),
            widget=forms.Select(attrs={'class': SELECT_CLASS}),
        )
        self.fields['redcap_secondary_id_field'] = forms.ChoiceField(
            choices=[('', _('--- None ---'))] + field_choices[1:],
            required=False,
            label=_('Secondary ID Field'),
            help_text=_('Optional secondary identifier (e.g. when auto-numbering is used in REDCap).'),
            widget=forms.Select(attrs={'class': SELECT_CLASS}),
        )

    class Meta:
        model = ProjectRedcapMapping
        fields = ['redcap_study_id_field', 'redcap_secondary_id_field']


class RedcapFormToQuestionnaireMappingForm(forms.ModelForm):
    def __init__(self, *args, project_redcap_mapping=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._project_redcap_mapping = project_redcap_mapping

        redcap_form_choices = [('', _('--- Select REDCap Form ---'))]
        redcap_field_choices = [('', _('--- Select REDCap Field ---'))]
        self._date_fields_by_form = {}

        if project_redcap_mapping and project_redcap_mapping.redcap_project_info:
            info = project_redcap_mapping.redcap_project_info
            forms_seen = set()
            for instrument in info.get('instruments', []):
                name = instrument.get('instrument_name', '')
                label = instrument.get('instrument_label', name)
                if name and name not in forms_seen:
                    redcap_form_choices.append((name, f"{label} ({name})"))
                    forms_seen.add(name)
            for field in info.get('metadata', []):
                fname = field.get('field_name', '')
                flabel = field.get('field_label', fname)
                fform = field.get('form_name', '')
                validation = field.get('text_validation_type_or_show_slider_number', '')
                if fname:
                    redcap_field_choices.append((fname, f"{flabel} ({fname})"))
                    if validation and validation.startswith(('date_', 'datetime_')):
                        self._date_fields_by_form.setdefault(fform, {})[fname] = validation

        self.fields['redcap_form_name'] = forms.ChoiceField(
            choices=redcap_form_choices,
            label=_('REDCap Form'),
            widget=forms.Select(attrs={'class': SELECT_CLASS, 'id': 'id_redcap_form_name'}),
        )
        self.fields['redcap_date_mapping_field'] = forms.ChoiceField(
            choices=[('', _('--- None ---'))] + redcap_field_choices[1:],
            required=False,
            label=_('Date Mapping Field in REDCap'),
            widget=forms.Select(attrs={'class': SELECT_CLASS}),
        )

        # Build choices from ALL date/datetime fields across all forms so that any
        # submitted value passes ChoiceField's built-in validation. The clean() method
        # enforces that the chosen field actually belongs to the selected form.
        date_field_choices = [('', _('--- None (no submission date export) ---'))]
        seen = set()
        for form_fields in self._date_fields_by_form.values():
            for fname, ftype in form_fields.items():
                if fname not in seen:
                    date_field_choices.append((fname, f"{fname} ({ftype})"))
                    seen.add(fname)

        self.fields['submission_date_field'] = forms.ChoiceField(
            choices=date_field_choices,
            required=False,
            label=_('Submission Date Field'),
            help_text=_('Select a date or datetime field in this REDCap form to receive the questionnaire submission date on export. The format is determined automatically from the REDCap field validation.'),
            widget=forms.Select(attrs={'class': SELECT_CLASS, 'id': 'id_submission_date_field'}),
        )

    @staticmethod
    def _normalise_date_format(validation):
        """Map any REDCap date validation type to its canonical ymd export format."""
        if validation.startswith('datetime_seconds_'):
            return 'datetime_seconds_ymd'
        if validation.startswith('datetime_'):
            return 'datetime_ymd'
        if validation.startswith('date_'):
            return 'date_ymd'
        return None

    def clean(self):
        cleaned_data = super().clean()
        submission_date_field = cleaned_data.get('submission_date_field') or None
        redcap_form_name = cleaned_data.get('redcap_form_name', '')

        if submission_date_field:
            form_date_fields = self._date_fields_by_form.get(redcap_form_name, {})
            validation = form_date_fields.get(submission_date_field)
            if not validation:
                self.add_error('submission_date_field', _(
                    '"%(field)s" is not a recognised date/datetime field for the selected form.'
                ) % {'field': submission_date_field})
            else:
                resolved = self._normalise_date_format(validation)
                if not resolved:
                    self.add_error('submission_date_field', _(
                        'The REDCap validation type "%(fmt)s" could not be mapped to an export format.'
                    ) % {'fmt': validation})
                else:
                    cleaned_data['_resolved_submission_date_format'] = resolved
        else:
            cleaned_data['submission_date_field'] = None
            cleaned_data['_resolved_submission_date_format'] = None

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.submission_date_field = self.cleaned_data.get('submission_date_field') or None
        instance.submission_date_format = self.cleaned_data.get('_resolved_submission_date_format') or None
        if commit:
            instance.save()
        return instance

    class Meta:
        model = RedcapFormToQuestionnaireMapping
        fields = [
            'redcap_form_name', 'redcap_event_name',
            'redcap_form_is_repeating', 'redcap_form_is_in_event', 'redcap_event_is_repeating',
            'redcap_date_mapping_field', 'questionnaire', 'submission_date_field',
        ]
        labels = {
            'redcap_event_name': _('REDCap Event Name'),
            'redcap_form_is_repeating': _('Form is a repeating form'),
            'redcap_form_is_in_event': _('Form is part of an event'),
            'redcap_event_is_repeating': _('Event is repeating'),
            'questionnaire': _('CHAVI PROM Questionnaire'),
        }
        widgets = {
            'redcap_event_name': forms.TextInput(attrs={'class': INPUT_CLASS}),
            'redcap_form_is_repeating': forms.CheckboxInput(attrs={'class': CHECKBOX_CLASS}),
            'redcap_form_is_in_event': forms.CheckboxInput(attrs={'class': CHECKBOX_CLASS}),
            'redcap_event_is_repeating': forms.CheckboxInput(attrs={'class': CHECKBOX_CLASS}),
            'questionnaire': forms.Select(attrs={'class': SELECT_CLASS}),
        }


DATE_VALIDATION_PREFIXES = ('date_', 'datetime_')


class RedcapFieldToItemMappingForm(forms.ModelForm):

    def __init__(self, *args, project_redcap_mapping=None, form_mapping=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._date_field_validation_map = {}
        self._form_mapping = form_mapping

        redcap_field_choices = [('', _('--- Select Field ---'))]
        if project_redcap_mapping and project_redcap_mapping.redcap_project_info:
            form_name = form_mapping.redcap_form_name if form_mapping else None
            for field in project_redcap_mapping.redcap_project_info.get('metadata', []):
                if form_name and field.get('form_name') != form_name:
                    continue
                fname = field.get('field_name', '')
                flabel = field.get('field_label', fname)
                validation = field.get('text_validation_type_or_show_slider_number', '')
                if fname:
                    if validation and validation.startswith(DATE_VALIDATION_PREFIXES):
                        self._date_field_validation_map[fname] = validation
                        redcap_field_choices.append((fname, f"{flabel} ({fname}) \u2014 \U0001f4c5 {validation}"))
                    else:
                        redcap_field_choices.append((fname, f"{flabel} ({fname})"))

        self.fields['redcap_field_name'] = forms.ChoiceField(
            choices=redcap_field_choices,
            label=_('REDCap Field'),
            widget=forms.Select(attrs={'class': SELECT_CLASS}),
        )

        if form_mapping:
            from promapp.models import QuestionnaireItem
            self.fields['questionnaire_item'].queryset = QuestionnaireItem.objects.filter(
                questionnaire=form_mapping.questionnaire
            ).select_related('item')

    class Meta:
        model = RedcapFieldToItemMapping
        fields = ['redcap_field_name', 'questionnaire_item']
        labels = {
            'questionnaire_item': _('Questionnaire Item'),
        }
        widgets = {
            'questionnaire_item': forms.Select(attrs={'class': SELECT_CLASS}),
        }


RedcapFieldToItemMappingFormSet = forms.modelformset_factory(
    RedcapFieldToItemMapping,
    form=RedcapFieldToItemMappingForm,
    extra=1,
    can_delete=True,
)


class RedcapStudyIDMapForm(forms.ModelForm):
    class Meta:
        model = RedcapStudyIDtoPatientIDMap
        fields = ['redcap_study_id']
        labels = {
            'redcap_study_id': _('REDCap Study ID'),
        }
        widgets = {
            'redcap_study_id': forms.TextInput(attrs={'class': INPUT_CLASS}),
        }