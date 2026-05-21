from calendar import c
from django.db import models
from django.db.models import CheckConstraint, Q
from django.utils import timezone
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
import secured_fields
import uuid
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
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

class Project(models.Model):
    '''
    This model will store information about the project to which the patient will be assigned to. Patient may be assigned to one or multiple projects.
    '''
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project_name = models.CharField(max_length= 512,null=True, blank=True)
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_date']
        verbose_name = "Project"
        verbose_name_plural = "Projects"

    def __str__(self):
        return self.project_name



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
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE, db_index=True,help_text="Please select the Institution from the List")
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    name = secured_fields.EncryptedCharField(max_length=255, searchable=True, null=True, blank=True,help_text="Please enter the Full Name of the Patient")
    patient_id = secured_fields.EncryptedCharField(max_length=255, searchable=True, null=True, blank=True,help_text="Please enter the Patient ID")
    date_of_registration = secured_fields.EncryptedDateField(verbose_name="Date of Registration",null=True, blank=True, searchable=True,help_text="Please select the Date of Registration from the Calendar")
    age = models.PositiveIntegerField(null=True, blank=True, db_index=True,help_text="Please enter the Age of the Patient")
    gender = models.CharField(max_length=255, choices=GenderChoices.choices, null=True, blank=True, db_index=True,help_text="Please select the Gender of the Patient")
    preferred_language = models.CharField(
        max_length=10, 
        choices=settings.LANGUAGES, 
        default=settings.LANGUAGE_CODE,
        null=True, 
        blank=True, 
        db_index=True,
        help_text=_("Please select the Preferred Language of the Patient")
    )
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_date']
        verbose_name = 'Patient'
        verbose_name_plural = 'Patients'
        indexes = [
            models.Index(fields=['institution', 'gender'], name='patient_inst_gender_idx'),
            models.Index(fields=['institution', 'age'], name='patient_inst_age_idx'),
            models.Index(fields=['institution', 'created_date'], name='patient_inst_created_idx'),
        ]

    def __str__(self):
        return f"{self.name} ({self.patient_id})" if self.patient_id else f"{self.name}"

    def save(self, *args, **kwargs):
        # Ensure the preferred_language is one of the supported languages
        if self.preferred_language not in dict(settings.LANGUAGES).keys():
            self.preferred_language = settings.LANGUAGE_CODE
        super().save(*args, **kwargs)


@receiver(post_save, sender=Patient)
def update_user_language(sender, instance, **kwargs):
    """
    Signal to update the user's session language when their preferred language changes
    """
    from django.utils import translation
    from django.conf import settings
    
    if hasattr(instance, 'user'):
        # Update the language in the user's session
        if hasattr(instance.user, 'session'):
            session = instance.user.session
            session[translation.LANGUAGE_SESSION_KEY] = instance.preferred_language or settings.LANGUAGE_CODE
            session.save()

class PatientProject(models.Model):
    '''
    PatientProject model to link patients to project using a many to many relationship. The table also stores the date the patient was assigned to the project as that will be used later on with questionnaire export to allow users to export the questionnaires which were answered by the patient during the period the patient was a part of the project.
    '''
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(Patient, on_delete=models.SET_NULL, null=True, blank=True, db_index=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, db_index=True)
    date_patient_enrolled_in_project= models.DateField(null=True,blank=True)
    date_patient_exited_from_project= models.DateField(null=True,blank=True)
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_date']
        verbose_name = 'Patient Project'
        verbose_name_plural = 'Patient Projects'
        indexes = [
            models.Index(fields=['patient', 'project'], name='patient_project_idx'),
        ]
        constraints = [
            models.UniqueConstraint(fields=['patient', 'project'], name='unique_patient_project')
        ]

    def __str__(self):
        return f"{self.patient} - {self.project}"


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
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, db_index=True)
    diagnosis = models.ForeignKey(DiagnosisList,on_delete=models.CASCADE,null=True, blank=True,help_text="Select the Diagnosis from the list",related_name="diagnosis_list", db_index=True)
    date_of_diagnosis = secured_fields.EncryptedDateField(verbose_name="Date of Diagnosis",null=True,blank=True,searchable=True, help_text="Select the Date of Diagnosis from the calendar")
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_date']
        verbose_name = 'Diagnosis'
        verbose_name_plural = 'Diagnoses'
        indexes = [
            models.Index(fields=['patient', 'date_of_diagnosis'], name='diag_patient_date_idx'),
            models.Index(fields=['diagnosis', 'date_of_diagnosis'], name='diag_type_date_idx'),
        ]

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
    

class ExportTypeChoices(models.TextChoices):
    MANUAL = 'manual', 'Manual'
    AUTOMATIC = 'automatic', 'Automatic'

class ProjectRedcapMapping (models.Model):
    '''
    This table will map a REDCap project to the a specific CHAVI PROM Project allowing data of patients in CHAVI PROM to be exported to REDCap. Users can configure this mapping in the admin panel. Using PyCap, the project information will be stored as a JSON mapping in the database table. The project information may be updated also at a later date. 
    '''
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    redcap_project_url = models.URLField()
    redcap_project_token = secured_fields.EncryptedTextField()
    redcap_project_token_allows_import = models.BooleanField(default=False, help_text="Select if the token allows data to be imported into REDCap. Most default API tokens do not allow this so please check your API key settings in REDCap.")
    redcap_project_token_allows_export = models.BooleanField(default=True, help_text="Select if the token allows data to be exported from REDCap. Most default API tokens allow export so this is enabled by default.")
    redcap_project_info = models.JSONField(null=True, blank=True, help_text="This is the project information that will be automatically extracted from REDCap after the project settings are filled.")
    date_redcap_project_info_updated = models.DateField(null=True, blank=True)
    redcap_record_count = models.IntegerField(null=True, blank=True, help_text="This is the record count that will be automatically extracted from REDCap after the project settings are filled.")
    export_type = models.CharField(max_length=12, choices=ExportTypeChoices.choices, default=ExportTypeChoices.MANUAL)
    redcap_study_id_field = models.CharField(max_length=1024, blank=True, null=True, help_text="This is the name of the field in the project that denotes the study ID.")
    redcap_data_access_group_used = models.BooleanField(default=False, help_text="Select if a data access group is used in the project.")
    redcap_secondary_id_field = models.CharField(max_length=1024, null=True, blank=True, help_text="This is a secondary unique ID field that is often used when we are using automatic numbering of records in REDCap. Note that this is not going to be used for the import but will be helpful when deciding the study ID to which the data should be imported in REDCap.")
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Project Redcap Mapping'
        verbose_name_plural = 'Project Redcap Mappings'
        constraints = [
            models.UniqueConstraint(fields=['project', 'redcap_project_url'], name='unique_project_redcap_url'),
        ]

    def __str__(self):
        return f"{self.project.project_name} - {self.redcap_project_url}"


class RedcapStudyIDtoPatientIDMap(models.Model):
    '''
    This model will store the mapping for the patient ID in REDCap to the patient ID in CHAVI PROM.
    Note that the patient ID field is different from username and refers to the patient_id field in the Patient model. Note that the patient will be linked to a specific study not to a questionnaire. 
    '''
    project_redcap_mapping = models.ForeignKey(ProjectRedcapMapping, null=True, blank=True, on_delete=models.CASCADE)
    patient = models.ForeignKey(Patient, null=True, blank=True, on_delete=models.CASCADE)
    redcap_study_id = models.CharField(max_length=1024, null=True, blank=True, help_text="Mapped Study ID from REDCap")
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "REDCap Study ID to Patient ID Map"
        verbose_name_plural = "REDCap Study ID to Patient ID Maps"
        constraints = [
            models.UniqueConstraint(fields=['project_redcap_mapping', 'patient'], name='unique_redcap_patient_mapping'),
        ]

    def __str__(self):
        return f"{self.patient} - {self.redcap_study_id}"


class RedcapFormToQuestionnaireMapping(models.Model):
    '''
    This table will store the linkage between a REDCap form in a REDCap project and the questionnaire in CHAVI PROM. This linkage will be specfic to the project and therefore when when  the project is modified this linkage will be revised. 
    '''
    project_redcap_mapping = models.ForeignKey(ProjectRedcapMapping, on_delete=models.CASCADE)
    redcap_form_name = models.CharField(max_length=1024)
    redcap_event_name = models.CharField(max_length=1024, blank=True, null=True, help_text="The REDCap event name for this form. Required when the form is part of a longitudinal event and will be included in CSV exports.")
    redcap_form_is_repeating = models.BooleanField(default=False, help_text="This defines if the REDCap form is a repeating form. Repeating form data has to be handled differently from non-repeating forms.")
    redcap_form_is_in_event = models.BooleanField(default=False, help_text="This defines if the REDCap form is a part of an event in a longitudinal project. For these forms the event name needs to be a part of the export file.")
    redcap_event_is_repeating = models.BooleanField(default=False, help_text="This defines if the REDCap event is repeating. If there is a repeating event then all forms in the event will also repeat.")
    redcap_date_mapping_field = models.CharField(max_length=1024, blank=True, null=True, help_text="This is the field in the REDCap form that will be used to map the date to the questionnaire. Note that this field may exist in another form where the visit date is recorded.")
    questionnaire = models.ForeignKey('promapp.Questionnaire', on_delete=models.CASCADE, help_text="Link to the Questionnaire in the CHAVI PROM application.")
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "REDCap Form To Questionnaire Mapping"
        verbose_name_plural = "REDCap Form To Questionnaire Mappings"
        constraints = [
            CheckConstraint(
                condition=Q(redcap_form_is_in_event=True) | Q(redcap_event_is_repeating=False),
                name='%(app_label)s_%(class)s_event_repeating_requires_in_event',
                violation_error_message="Event cannot be repeating if form is not in an event."
            ),
            CheckConstraint(
                condition=Q(redcap_form_is_in_event=False) | Q(redcap_date_mapping_field__isnull=False, redcap_date_mapping_field__gt=''),
                name='%(app_label)s_%(class)s_date_mapping_required_for_events',
                violation_error_message="Date mapping field is required when form is in an event."
            ),
            models.UniqueConstraint(
                fields=['project_redcap_mapping', 'redcap_form_name', 'questionnaire'],
                name='unique_redcap_form_questionnaire_mapping',
            ),
        ]

    def __str__(self):
        return f"{self.redcap_form_name}-{self.questionnaire}"


    
    


class RedcapFieldToItemMapping(models.Model):
    '''
    This table will store information about the mapping of REDCap fields to the Questionnaire Items in the CHAVI PROM questionnaire. Note that this linkage allows us to specify linkage of the same item to the multiple fields in REDCap. The linkage to the questionnaire item will point to the specific Item through the foreign key Questionnaire -> QuestionnaireItem -> Item (see promapp.models)
    When the export process will run, then the value stored for the specific item in the QuestionnaireSubmission will be used to populate the REDCap field data. The relationship traversal will be Questionnaire -> PatientQuestionnaire -> QuestionnaireSubmission -> QuestionnaireItemResponse where the field called response value stores the actual value that will be stored in the REDCap data export. (See promapp.models)

    '''

    redcap_form_to_questionnaire_mapping = models.ForeignKey(RedcapFormToQuestionnaireMapping, on_delete=models.CASCADE)
    redcap_field_name = models.CharField(max_length=1024)
    questionnaire_item = models.ForeignKey('promapp.QuestionnaireItem', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "REDCap Field To Item Mapping"
        verbose_name_plural = "REDCap Field To Item Mappings"
        constraints = [
            models.UniqueConstraint(
                fields=['redcap_form_to_questionnaire_mapping', 'redcap_field_name'],
                name='unique_redcap_field_per_form_mapping',
            ),
            models.UniqueConstraint(
                fields=['redcap_form_to_questionnaire_mapping', 'questionnaire_item'],
                name='unique_questionnaire_item_per_form_mapping',
            ),
        ]

    def __str__(self):
        return f"{self.redcap_field_name}-{self.questionnaire_item}"



class ExportStatusChoices(models.TextChoices):
    PENDING = 'pending', 'Pending'
    COMPLETED = 'completed', 'Completed'
    INCOMPLETE = 'incomplete', 'Incomplete'
    FAILED = 'failed', 'Failed'


class RedcapDataExportLog(models.Model):
    '''
    This model will store the entries for all transactions for data updating using REDCap API when data export is enabled using automatic method.
    '''
    redcap_form_to_questionnaire_mapping = models.ForeignKey(RedcapFormToQuestionnaireMapping, on_delete=models.CASCADE)
    patient = models.ForeignKey(Patient, null=True, blank=True, on_delete=models.SET_NULL, help_text="The patient whose data was exported.")
    user_exporting_data = models.ForeignKey(User, on_delete=models.CASCADE)
    export_type = models.CharField(max_length=12, choices=ExportTypeChoices.choices, default=ExportTypeChoices.MANUAL, help_text="Whether this was an API-mediated export or a manual CSV export.")
    datetime_export_start = models.DateTimeField(null=True, blank=True)
    datetime_export_completed = models.DateTimeField(null=True, blank=True)
    export_status = models.CharField(max_length=20, null=True, blank=True, choices=ExportStatusChoices.choices)
    export_log = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "REDCap API Data Export Log"
        verbose_name_plural = "REDCap API Data Export Logs"

    def __str__(self):
        return f"{self.patient} - {self.redcap_form_to_questionnaire_mapping} - {self.export_status}"
