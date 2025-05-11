from django.db import models
from django.utils import timezone
import uuid

# Create your models here.

class Instrument(models.Model):
    '''
    Instrument model.
    '''
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255,null=True, blank=True)
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_date']
        verbose_name = 'Instrument'
        verbose_name_plural = 'Instruments'

    def __str__(self):
        return self.name


class Scale(models.Model):
    '''
    Scale model.
    '''
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    instrument = models.ForeignKey(Instrument, on_delete=models.CASCADE)
    name = models.CharField(max_length=255,null=True, blank=True)
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_date']
        verbose_name = 'Scale'
        verbose_name_plural = 'Scales'

    def __str__(self):
        return self.name

class ResponseTypeChoices(models.TextChoices):
    TEXT = 'Text', 'Text Response'
    NUMBER = 'Number', 'Numeric Response'
    BOOLEAN = 'Boolean', 'Yes/No Response'
    LIKERT = 'Likert', 'Likert Scale'
    RANKING = 'Ranking', 'Ranking Response'
    RANGE = 'Range', 'Range Response'

class ResponseOption(models.Model):
    '''
    ResponseOption model to store possible options for each response type.
    '''
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    item = models.ForeignKey('Item', on_delete=models.CASCADE, related_name='response_options')
    option_text = models.CharField(max_length=255)
    option_value = models.CharField(max_length=255, null=True, blank=True)
    order = models.IntegerField(default=0)
    # Range specific fields
    min_value = models.IntegerField(null=True, blank=True)  # For Range type
    max_value = models.IntegerField(null=True, blank=True)  # For Range type
    increment_value = models.IntegerField(null=True, blank=True)  # For Range type
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'created_date']
        verbose_name = 'Response Option'
        verbose_name_plural = 'Response Options'

    def __str__(self):
        return f"{self.item.name} - {self.option_text}"

    def clean(self):
        """
        Validate that range-specific fields are only set for range type responses
        """
        from django.core.exceptions import ValidationError
        if self.item.response_type == ResponseTypeChoices.RANGE:
            if self.min_value is None or self.max_value is None or self.increment_value is None:
                raise ValidationError("Range type responses require min_value, max_value, and increment_value")
            if self.min_value >= self.max_value:
                raise ValidationError("min_value must be less than max_value")
            if self.increment_value <= 0:
                raise ValidationError("increment_value must be greater than 0")
        else:
            if self.min_value is not None or self.max_value is not None or self.increment_value is not None:
                raise ValidationError("min_value, max_value, and increment_value are only for range type responses")

class Item(models.Model):
    '''
    Item model.
    '''
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    scale = models.ForeignKey(Scale, on_delete=models.CASCADE)
    name = models.CharField(max_length=255,null=True, blank=True)
    response_type = models.CharField(max_length=255, choices=ResponseTypeChoices.choices)
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_date']
        verbose_name = 'Item'
        verbose_name_plural = 'Items'

    def __str__(self):
        return self.name

    def get_response_options(self):
        """
        Returns the response options for this item based on its response type.
        """
        if self.response_type == ResponseTypeChoices.TEXT:
            return self.response_options.filter(option_text__isnull=False)
        elif self.response_type == ResponseTypeChoices.NUMBER:
            return self.response_options.filter(option_text__isnull=False)
        elif self.response_type == ResponseTypeChoices.BOOLEAN:
            return self.response_options.filter(option_text__in=['Yes', 'No'])
        elif self.response_type == ResponseTypeChoices.LIKERT:
            return self.response_options.filter(option_text__isnull=False).order_by('order')
        elif self.response_type == ResponseTypeChoices.RANKING:
            return self.response_options.filter(option_text__isnull=False).order_by('order')
        elif self.response_type == ResponseTypeChoices.RANGE:
            return self.response_options.filter(option_text__isnull=False).order_by('order')
        return self.response_options.none()
    
