from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
import secured_fields
import uuid

# Create your models here.

class Institution(models.Model):
    '''
    Institution model.
    '''
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255,null=True, blank=True)
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_date']
        verbose_name = 'Institution'
        verbose_name_plural = 'Institutions'

    def __str__(self):
        return self.name

class GenderChoices(models.TextChoices):
    MALE = 'Male'
    FEMALE = 'Female'
    TRANSGENDER = 'Transgender'
    NON_BINARY = 'Non-binary'
    PREFER_NOT_TO_SAY = 'Prefer not to say'
    OTHER = 'Other'

class Patient(models.Model):
    '''
    Patient model.
    '''
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE)
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    name = secured_fields.EncryptedCharField(max_length=255, searchable=True, null=True, blank=True)
    patient_id = secured_fields.EncryptedCharField(max_length=255, searchable=True, null=True, blank=True)
    date_of_registration = secured_fields.EncryptedDateField(verbose_name="Date of Registration",null=True, blank=True, searchable=True)
    age = models.PositiveIntegerField(null=True, blank=True)
    gender = models.CharField(max_length=255, choices=GenderChoices.choices, null=True, blank=True)
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_date']
        verbose_name = 'Patient'
        verbose_name_plural = 'Patients'

    def __str__(self):
        return self.name

class DiagnosisList(models.Model):
    '''
    List of diagnosis for the system. This list will be referenced in the model for the Diagnosis. 
    '''
    id = models.UUIDField(primary_key=True, default=uuid.uuid4,editable=False)
    diagnosis = models.CharField(null=True,blank=True,max_length = 255)
    icd_11_code = models.CharField(null=True, blank=True,max_length=255, verbose_name= "ICD 11 Code")
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)

    class Meta: 
        ordering = ['-created_date']
        verbose_name = 'List of Diagnosis'
        verbose_name_plural = 'List of Diagnoses'

    def __str__(self):
        return f"{self.icd_11_code}: {self.diagnosis}"



class Diagnosis(models.Model):
    '''
    Diagnosis model.
    '''
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    diagnosis = models.ForeignKey(DiagnosisList,on_delete=models.CASCADE,null=True, blank=True,help_text="Select the Diagnosis from the list",related_name="diagnosis_list")
    date_of_diagnosis = secured_fields.EncryptedDateField(verbose_name="Date of Diagnosis",null=True,blank=True,searchable=True, help_text="Select the Date of Diagnosis from the calendar")
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_date']
        verbose_name = 'Diagnosis'
        verbose_name_plural = 'Diagnoses'

    def __str__(self):
        return self.patient.patient_id


class TreatmentIntentChoices(models.TextChoices):
    PREVENTIVE = 'Preventive'
    CURATIVE = 'Curative'
    PALLIATIVE = 'Palliative'
    OTHER = 'Other'

class TreatmentType(models.Model):
    '''
    Treatment types model.
    '''
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    treatment_type = models.CharField(max_length=255,null=True, blank=True)
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_date']
        verbose_name = 'Treatment Type'
        verbose_name_plural = 'Treatment Types'

    def __str__(self):  
        return self.treatment_type

class Treatment(models.Model):
    '''
    Treatment model. Use this to specify the treatments delivered to the specific diagnosis. As patients may have multiple treatments over a period of time, this form allows us to capture treatments delivered synchronously. If treatments are delivered sequentially, then add another entry of the form for the diagnosis. This also allows for data to be updated longitudinally.
    '''
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    diagnosis = models.ForeignKey(Diagnosis, on_delete=models.CASCADE)
    treatment_type = models.ManyToManyField(TreatmentType, blank=True,help_text="Select the Treatment Type(s) from the list. Please select treatments that have been delivered synchronously.Please add another treatment entry form if there were sequential treatments delivered.")
    treatment_intent = models.CharField(max_length=255, choices=TreatmentIntentChoices.choices, null=True, blank=True)
    date_of_start_of_treatment = secured_fields.EncryptedDateField(null=True, blank=True,help_text="Select the Date of Start of Treatment from the calendar",searchable=True)
    currently_ongoing_treatment = models.BooleanField(default=False,help_text="Select this if the treatment is currently ongoing. This will be used to indicate that the treatment is ongoing and not yet completed.")
    date_of_end_of_treatment = secured_fields.EncryptedDateField(null=True, blank=True,help_text="Select the Date of End of Treatment from the calendar",searchable=True)
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_date']
        verbose_name = 'Treatment'
        verbose_name_plural = 'Treatments'

    def clean(self):
        """
        Custom validation for Treatment model.
        """
        super().clean()
        errors = {}
        
        # Get today's date for future date validation
        today = timezone.now().date()
        
        # Validate start date is not in the future
        if self.date_of_start_of_treatment and self.date_of_start_of_treatment > today:
            errors['date_of_start_of_treatment'] = _('Start date cannot be in the future.')
        
        # Validate end date is not in the future
        if self.date_of_end_of_treatment and self.date_of_end_of_treatment > today:
            errors['date_of_end_of_treatment'] = _('End date cannot be in the future.')
        
        # Validate end date is not before start date
        if (self.date_of_start_of_treatment and self.date_of_end_of_treatment and 
            self.date_of_end_of_treatment < self.date_of_start_of_treatment):
            errors['date_of_end_of_treatment'] = _('End date cannot be before the start date.')
        
        # Validate that if currently_ongoing_treatment is True, end date should be empty
        if self.currently_ongoing_treatment and self.date_of_end_of_treatment:
            errors['date_of_end_of_treatment'] = _('End date should not be specified for ongoing treatments.')
        
        # Validate that if currently_ongoing_treatment is False and we have a start date, we should have an end date
        if (not self.currently_ongoing_treatment and self.date_of_start_of_treatment and 
            not self.date_of_end_of_treatment):
            errors['date_of_end_of_treatment'] = _('End date is required when treatment is not ongoing.')
        
        if errors:
            raise ValidationError(errors)
    
