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


class ResponseTypeChoices(models.TextChoices):
    TEXT = 'Text'
    NUMBER = 'Number'
    DATE = 'Date'
    BOOLEAN = 'Boolean'
    MULTIPLE_CHOICE = 'Multiple Choice'
    SCALE = 'Scale'

class ResponseType(models.Model):
    '''
    Response type model.
    '''
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255,null=True, blank=True, choices=ResponseTypeChoices.choices)
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_date']
        verbose_name = 'Response Type'    
        verbose_name_plural = 'Response Types'
        


class Scale(models.Model):
    '''
    Scale model.
    '''
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    instrument = models.ForeignKey(Instrument, on_delete=models.CASCADE)
    response_type = models.ForeignKey(ResponseType, on_delete=models.CASCADE)
    name = models.CharField(max_length=255,null=True, blank=True)
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_date']
        verbose_name = 'Scale'
        verbose_name_plural = 'Scales'

    def __str__(self):
        return self.name

class Item(models.Model):
    '''
    Item model.
    '''
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    scale = models.ForeignKey(Scale, on_delete=models.CASCADE)
    name = models.CharField(max_length=255,null=True, blank=True)
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_date']
        verbose_name = 'Item'
        verbose_name_plural = 'Items'

    def __str__(self):
        return self.name