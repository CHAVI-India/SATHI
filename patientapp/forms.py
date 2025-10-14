from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User, Group
from .models import Patient, Institution, Treatment, Diagnosis, DiagnosisList
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Field, Div, Submit, HTML
from django.utils.translation import gettext_lazy as _

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