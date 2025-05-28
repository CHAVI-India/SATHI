from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
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
    Treatment model.
    '''
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    diagnosis = models.ForeignKey(Diagnosis, on_delete=models.CASCADE)
    treatment_type = models.ManyToManyField(TreatmentType, blank=True)
    treatment_intent = models.CharField(max_length=255, choices=TreatmentIntentChoices.choices, null=True, blank=True)
    date_of_start_of_treatment = models.DateField(null=True, blank=True)
    date_of_end_of_treatment = models.DateField(null=True, blank=True)
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_date']
        verbose_name = 'Treatment'
        verbose_name_plural = 'Treatments'
