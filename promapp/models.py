from django.db import models
from django.utils import timezone
import uuid
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from patientapp.models import Patient,Diagnosis,Treatment

# Create your models here.

class ConstructScale(models.Model):
    '''
    Construct Scale model. Construct Scale refers to the collection of items that are used to measure a construct.
    '''
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255,null=True, blank=True)
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

class LikertScaleResponseOption(models.Model):
    '''
    Likert scale response options model. This is used to store the options for Likert Scale Responses.
    '''
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    likert_scale = models.ForeignKey(LikertScale, on_delete=models.CASCADE)
    option_text = models.CharField(max_length=255, null=True, blank=True, help_text = "The text to display for the option")
    option_order = models.IntegerField(null=True, blank=True, help_text = "The order of the option. This will be a number.")
    option_media = models.FileField(upload_to='likert_scale_response_options/', null=True, blank=True, help_text = "The media to display for the option. This will be an audio, video or image.")
    option_value = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text = "The value to store for the option. This will be a number with upto 2 decimal places.")
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['option_order']
        verbose_name = 'Likert Scale Response Option'
        verbose_name_plural = 'Likert Scale Response Options'
        unique_together = ['option_text', 'option_order', 'option_value']

    def __str__(self):
        return self.option_text

class RangeScale(models.Model):
    '''
    Range scale model. This is used to store the range of values for a range scale.
    '''
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    range_scale_name = models.CharField(max_length=255, null=True, blank=True, help_text = "The name of the Range Scale")
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_date']
        verbose_name = 'Range Scale'
        verbose_name_plural = 'Range Scales'

    def __str__(self):
        return self.range_scale_name

class RangeScaleResponseOption(models.Model):
    '''
    Range scale response options model. This is used to store the options for Range Scale Responses.
    '''
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    range_scale = models.ForeignKey(RangeScale, on_delete=models.CASCADE)
    min_value = models.DecimalField(max_digits=10, decimal_places=2, help_text = "The minimum value for the range scale")
    min_value_text = models.CharField(max_length=255, null=True, blank=True, help_text = "The text to display for the minimum value")
    max_value = models.DecimalField(max_digits=10, decimal_places=2, help_text = "The maximum value for the range scale")
    max_value_text = models.CharField(max_length=255, null=True, blank=True, help_text = "The text to display for the maximum value")
    increment = models.DecimalField(max_digits=10, default=1, decimal_places=2, null=True, blank=True, help_text = "The increment for the range scale. Must be more than 0")
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_date']
        verbose_name = 'Range Scale Response Option'
        verbose_name_plural = 'Range Scale Response Options'

    def __str__(self):
        return f"{self.range_scale.range_scale_name} - {self.min_value_text} to {self.max_value_text}"
    
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


class Item(models.Model):
    '''
    Item model. Ensure full_clean() is called before saving in views and forms
    '''
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    construct_scale = models.ForeignKey(ConstructScale, on_delete=models.CASCADE, help_text = "Each item can belong to a construct scale which is designed to measure a construct or domain related to the Patient Reported Outcome.")
    name = models.CharField(max_length=255,null=True, blank=True, help_text = "The name of the item which will be displayed to the patient")
    response_type = models.CharField(max_length=255, choices=ResponseTypeChoices.choices, help_text = "The type of response for the item")
    likert_response = models.ForeignKey(LikertScale, on_delete=models.CASCADE, null=True, blank=True)
    range_response = models.ForeignKey(RangeScale, on_delete=models.CASCADE, null=True, blank=True)
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_date']
        verbose_name = 'Item'
        verbose_name_plural = 'Items'

    def __str__(self):
        return self.name

    def clean(self):
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


class Questionnaire(models.Model):
    '''
    Questionnaire model. This is used to store the questionnaire.
    '''
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, null=True, blank=True, help_text = "The name of the questionnaire")
    description = models.TextField(null=True, blank=True, help_text = "The description of the questionnaire")
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_date']
        verbose_name = 'Questionnaire'
        verbose_name_plural = 'Questionnaires'

class QuestionnaireItemResponse(models.Model):
    '''
    Questionnaire Item Response model. This is used to store the items for the questionnaire. There is a many to many relationship between Questionnaire and Item.
    '''
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    questionnaire = models.ForeignKey(Questionnaire, on_delete=models.CASCADE)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, help_text = "The patient to whom the questionnaire belongs")
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    item_response_text = models.CharField(max_length=255, null=True, blank=True, help_text = "The response value for the item")
    item_response_number = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text = "The response value for the item")
    item_response_likert_value = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text = "The response value for the item")
    item_response_range_min_value = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text = "The minimum value for the item response")
    item_response_range_max_value = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text = "The maximum value for the item response")
    response_date_time = models.DateTimeField(auto_now_add=True, help_text = "The date and time of the response")
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_date']
        verbose_name = 'Questionnaire Item Response'
        verbose_name_plural = 'Questionnaire Item Responses'