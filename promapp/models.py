from django.db import models
from django.utils import timezone
import uuid
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from patientapp.models import Patient,Diagnosis,Treatment
from parler.models import TranslatableModel, TranslatedFields
# Create your models here.

class ConstructScale(models.Model):
    '''
    Construct Scale model. Construct Scale refers to the collection of items that are used to measure a construct.
    '''
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255,null=True, blank=True)
    instrument_name = models.CharField(max_length=255,null=True, blank=True,help_text = "The name of the instrument that the construct scale belongs to")
    instrument_version = models.CharField(max_length=255,null=True, blank=True,help_text = "The version of the instrument that the construct scale belongs to")
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_date']
        verbose_name = 'Construct Scale'
        verbose_name_plural = 'Construct Scales'

    def __str__(self):
        return self.name


class LikertScale(models.Model):
    '''
    Likert scale type model. This is used to store the type of Likert Scale.
    '''
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    likert_scale_name = models.CharField(max_length=255, null=True, blank=True, help_text = "The name of the Likert Scale")
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_date']
        verbose_name = 'Likert Scale Response'
        verbose_name_plural = 'Likert Scale Responses'

    def __str__(self):
        return self.likert_scale_name

class LikertScaleResponseOption(TranslatableModel):
    '''
    Likert scale response options model. This is used to store the options for Likert Scale Responses.
    In this the translatable fields are option_text, and option_media.
    '''
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    likert_scale = models.ForeignKey(LikertScale, on_delete=models.CASCADE)
    option_order = models.IntegerField(null=True, blank=True, help_text = "The order of the option. This will be a number.")
    translations = TranslatedFields(
        option_text = models.CharField(max_length=255, null=True, blank=True, help_text = "The text to display for the option"),
        option_media = models.FileField(upload_to='likert_scale_response_options/', null=True, blank=True, help_text = "The media to display for the option. This will be an audio, video or image.")
    )
    option_value = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text = "The value to store for the option. This will be a number with upto 2 decimal places.")
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['option_order']
        verbose_name = 'Likert Scale Response Option'
        verbose_name_plural = 'Likert Scale Response Options'
        # Each option_order and option_value combination must be unique within a likert_scale
        # This ensures we can't have duplicate values in the same scale
        unique_together = ['likert_scale', 'option_order', 'option_value']

    def __str__(self):
        return self.option_text

class RangeScale(TranslatableModel):
    '''
    Range scale model. This is used to store the range of values for a range scale.
    '''
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    range_scale_name = models.CharField(max_length=255, null=True, blank=True, help_text = "The name of the Range Scale")
    max_value = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text = "The maximum value for the range scale")
    min_value = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text = "The minimum value for the range scale")
    increment = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text = "The increment for the range scale. Must be more than 0")
    translations = TranslatedFields(
        min_value_text = models.CharField(max_length=255, null=True, blank=True, help_text = "The text to display for the minimum value"),  
        max_value_text = models.CharField(max_length=255, null=True, blank=True, help_text = "The text to display for the maximum value")
    )
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_date']
        verbose_name = 'Range Scale'
        verbose_name_plural = 'Range Scales'

    def __str__(self):
        return self.range_scale_name
    def validate_increment(self):
        if self.min_value and self.max_value and self.increment:
            if self.min_value > self.max_value:
                raise ValueError("Minimum value cannot be greater than maximum value")
            if self.increment <= 0:
                raise ValueError("Increment must be greater than 0")
            if (self.max_value - self.min_value) % self.increment != 0:
                raise ValueError("Maximum value minus minimum value must be divisible by increment")



class ResponseTypeChoices(models.TextChoices):
    TEXT = 'Text', 'Text Response'
    NUMBER = 'Number', 'Numeric Response'
    LIKERT = 'Likert', 'Likert Scale'
    RANGE = 'Range', 'Range Response'


class Item(TranslatableModel):
    '''
    Item model. Ensure full_clean() is called before saving in views and forms.
    Translatable field is name.
    '''
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    construct_scale = models.ForeignKey(ConstructScale, on_delete=models.CASCADE, db_index=True, help_text = "Each item can belong to a construct scale which is designed to measure a construct or domain related to the Patient Reported Outcome.")
    translations = TranslatedFields(
        name = models.CharField(max_length=255,null=True, blank=True, help_text = "The name of the item which will be displayed to the patient", db_index=True),
        media = models.FileField(upload_to='item_media/', null=True, blank=True, help_text = "The media to display for the item. This will be an audio, video or image.")
    )
    response_type = models.CharField(max_length=255, choices=ResponseTypeChoices.choices, db_index=True, help_text = "The type of response for the item")
    likert_response = models.ForeignKey(LikertScale, on_delete=models.CASCADE, null=True, blank=True)
    range_response = models.ForeignKey(RangeScale, on_delete=models.CASCADE, null=True, blank=True)
    created_date = models.DateTimeField(auto_now_add=True, db_index=True)
    modified_date = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_date']
        verbose_name = 'Item'
        verbose_name_plural = 'Items'


    def clean(self):
        if self.likert_response and self.range_response:
            raise ValidationError('Only one of Likert Scale or Range Scale can be selected, not both.')
                
        if self.response_type == ResponseTypeChoices.LIKERT:
            if not self.likert_response:
                raise ValidationError({'likert_response': 'Likert Scale must be selected when response type is Likert'})
            if self.range_response:
                raise ValidationError({'range_response': 'Range Scale should not be selected when response type is Likert'})
        
        elif self.response_type == ResponseTypeChoices.RANGE:
            if not self.range_response:
                raise ValidationError({'range_response': 'Range Scale must be selected when response type is Range'})
            if self.likert_response:
                raise ValidationError({'likert_response': 'Likert Scale should not be selected when response type is Range'})
        
        elif self.response_type in [ResponseTypeChoices.TEXT, ResponseTypeChoices.NUMBER]:
            if self.likert_response:
                raise ValidationError({'likert_response': 'Likert Scale should not be selected for Text or Number response types'})
            if self.range_response:
                raise ValidationError({'range_response': 'Range Scale should not be selected for Text or Number response types'})


class Questionnaire(TranslatableModel):
    '''
    Questionnaire model. This is used to store the questionnaire.
    Translatable field are name and description.
    '''
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    translations = TranslatedFields(
        name = models.CharField(max_length=255, null=True, blank=True, help_text = "The name of the questionnaire"),
        description = models.TextField(null=True, blank=True, help_text = "The description of the questionnaire")
    )
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_date']
        verbose_name = 'Questionnaire'
        verbose_name_plural = 'Questionnaires'

class QuestionnaireItem(models.Model):
    '''
    Questionnaire Item model. This is used to store the items for the questionnaire. There is a many to many relationship between Questionnaire and Item.
    '''
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    questionnaire = models.ForeignKey(Questionnaire, on_delete=models.CASCADE, help_text = "The questionnaire to which the response belongs")
    question_number = models.IntegerField(help_text = "The number of the question in the questionnaire")
    item = models.ForeignKey(Item, on_delete=models.CASCADE, help_text = "The item to which the response belongs")
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_date']
        verbose_name = 'Questionnaire Item'
        verbose_name_plural = 'Questionnaire Items'

class PatientQuestionnaire(models.Model):
    '''
    Patient Questionnaire model. This is used to store the questionnaire available for a patient.
    '''
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, help_text = "The patient to which the questionnaire belongs")
    questionnaire = models.ForeignKey(Questionnaire, on_delete=models.CASCADE, help_text = "The questionnaire to which the patient belongs")
    display_questionnaire = models.BooleanField(default=False, help_text = "If True, the questionnaire is currently will be displayed for the patient")
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_date']
        verbose_name = 'Patient Questionnaire'
        verbose_name_plural = 'Patient Questionnaires'  

class QuestionnaireItemResponse(models.Model):
    '''
    Questionnaire Item Response model. This is used to store the responses for the questionnaire item.
    '''
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient_questionnaire = models.ForeignKey(PatientQuestionnaire, on_delete=models.CASCADE, help_text = "The patient questionnaire to which the response belongs")
    questionnaire_item = models.ForeignKey(QuestionnaireItem, on_delete=models.CASCADE, help_text = "The item to which the response belongs")
    response_date = models.DateTimeField(help_text = "The date and time of the response",auto_now_add=True)
    response_date = models.DateTimeField(help_text = "The date and time of the response",auto_now_add=True)
    response_value = models.CharField(max_length=255, help_text = "The response value",null=True, blank=True)
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-response_date']
        verbose_name = 'Questionnaire Response'
        verbose_name_plural = 'Questionnaire Responses'