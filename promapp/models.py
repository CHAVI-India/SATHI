from django.db import models
from django.utils import timezone
import uuid
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from patientapp.models import Patient,Diagnosis,Treatment
from parler.models import TranslatableModel, TranslatedFields
from django.db.models import Q
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils.safestring import mark_safe
import re
from .equation_parser import EquationValidator, EquationTransformer

# Create your models here.

class ConstructScale(models.Model):
    '''
    Construct Scale model. Construct Scale refers to the collection of items that are used to measure a construct.
    '''
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255,null=True, blank=True)
    instrument_name = models.CharField(max_length=255,null=True, blank=True,help_text = "The name of the instrument that the construct scale belongs to")
    instrument_version = models.CharField(max_length=255,null=True, blank=True,help_text = "The version of the instrument that the construct scale belongs to")
    scale_equation = models.CharField(max_length=255,null=True,blank=True,help_text = "The equation to calculate the score for the construct scale from the items in the scale")
    minimum_number_of_items = models.IntegerField(default=0,help_text = "The minimum number of items that must be answered to calculate the score for the construct scale")
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_date']
        verbose_name = 'Construct Scale'
        verbose_name_plural = 'Construct Scales'

    def __str__(self):
        return self.name
    
    def get_valid_items_with_numbers(self):
        """
        Returns a list of valid items (Number, Likert, or Range) with their stored item numbers.
        """
        valid_items = []
        
        for item in self.item_set.all():
            if item.response_type in ['Number', 'Likert', 'Range']:
                valid_items.append({
                    'item': item,
                    'question_number': item.item_number
                })
                
        return valid_items
    
    def validate_scale_equation(self):
        """
        Validates the scale equation using Lark grammar. Validation rules are in the file called equation_validation_rules.lark
        """
        if not self.scale_equation:
            return

        # Get all valid question numbers for this scale
        valid_question_numbers = set()
        for item_data in self.get_valid_items_with_numbers():
            valid_question_numbers.add(item_data['question_number'])

        # Check for valid question references
        question_refs = re.findall(r'\{q(\d+)\}', self.scale_equation)
        if not question_refs:
            raise ValidationError("Equation must contain at least one question reference in the form {qN} (e.g., {q1}, {q2})")
        
        invalid_refs = []
        for ref in question_refs:
            question_number = int(ref)
            if question_number not in valid_question_numbers:
                invalid_refs.append(f"{{q{question_number}}}")
        if invalid_refs:
            raise ValidationError(f"Invalid question references: {', '.join(invalid_refs)}. Only questions {', '.join(f'{{q{n}}}' for n in sorted(valid_question_numbers))} are available for this scale.")

        # Validate equation syntax using Lark
        validator = EquationValidator()
        validator.validate(self.scale_equation)

        # Test the equation with sample data to ensure it works with minimum required items
        sample_data = {num: 1 for num in valid_question_numbers}  # Use 1 as a sample value
        transformer = EquationTransformer(sample_data, self.minimum_number_of_items)
        try:
            tree = validator.parser.parse(self.scale_equation)
            transformer.transform(tree)
        except ValidationError as e:
            raise ValidationError(f"Equation validation failed: {str(e)}")

    def clean(self):
        """
        This method is called by Django's form validation and model validation.
        It ensures the scale_equation is validated before saving.
        """
        super().clean()
        self.validate_scale_equation()

    def save(self, *args, **kwargs):
        """
        Override save to ensure validation is always performed
        """
        self.full_clean()  # This will call clean() and validate all fields
        super().save(*args, **kwargs)


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
        # Use Parler's safe_translation_getter to get the translated name
        range_scale_name = self.safe_translation_getter('range_scale_name', any_language=True) if hasattr(self, 'safe_translation_getter') else None
        if range_scale_name is None:
            # Fallback to a default string representation if no translation is found
            return f"Range Scale {self.id}"
        return range_scale_name

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
    item_number = models.IntegerField(null=True, blank=True, help_text = "The number of the item in the construct scale")
    response_type = models.CharField(max_length=255, choices=ResponseTypeChoices.choices, db_index=True, help_text = "The type of response for the item")
    likert_response = models.ForeignKey(LikertScale, on_delete=models.CASCADE, null=True, blank=True)
    range_response = models.ForeignKey(RangeScale, on_delete=models.CASCADE, null=True, blank=True)
    created_date = models.DateTimeField(auto_now_add=True, db_index=True)
    modified_date = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_date']
        verbose_name = 'Item'
        verbose_name_plural = 'Items'

    def save(self, *args, **kwargs):
        if not self.item_number and self.construct_scale:
            # Get the highest item number for this construct scale
            last_item = Item.objects.filter(construct_scale=self.construct_scale).order_by('-item_number').first()
            self.item_number = (last_item.item_number + 1) if last_item and last_item.item_number else 1
        super().save(*args, **kwargs)

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
    def __str__(self):
        # Use Parler's safe_translation_getter to get the translated name
        item_name = self.safe_translation_getter('name', any_language=True) if hasattr(self, 'safe_translation_getter') else None
        if item_name is None:
            # Fallback to a default string representation if no translation is found
            return f"Item {self.id}"
        return item_name

    def get_available_languages(self):
        """Return a list of language codes for which translations exist."""
        return list(self.translations.values_list('language_code', flat=True))

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
    questionnaire_answer_interval = models.IntegerField(default=0, help_text = "The interval in seconds between answering the same questionnaire by the same patient")
    questionnaire_order = models.IntegerField(default=0, help_text = "The order of the questionnaire in the list of questionnaires for the patient")
    questionnaire_redirect = models.ForeignKey('self', null=True, blank= True, on_delete=models.CASCADE, help_text = "The questionnaire to redirect to after the current questionnaire is answered",related_name="redirect_questionnaire")
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_date']
        verbose_name = 'Questionnaire'
        verbose_name_plural = 'Questionnaires'
    def __str__(self):
        # Use Parler's safe_translation_getter to get the translated name
        questionnaire_name = self.safe_translation_getter('name', any_language=True) if hasattr(self, 'safe_translation_getter') else None
        if questionnaire_name is None:
            # Fallback to a default string representation if no translation is found
            return f"Questionnaire {self.id}"
        return questionnaire_name

    def get_available_languages(self):
        """Return a list of language codes for which translations exist."""
        return list(self.translations.values_list('language_code', flat=True))





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

    def __str__(self):
        # Use Parler's safe_translation_getter to get the translated name
        item_name = self.item.safe_translation_getter('name', any_language=True) if hasattr(self.item, 'safe_translation_getter') else str(self.item)
        return f"Q{self.question_number}: {item_name}"





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
    def __str__(self):
        return f"{self.patient.name} - {self.questionnaire.name}"


class QuestionnaireSubmission(models.Model):
    '''
    Questionnaire Submission model. This is used to store the submission of the questionnaire.
    '''
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, help_text = "The patient to which the submission belongs")
    patient_questionnaire = models.ForeignKey(PatientQuestionnaire, on_delete=models.CASCADE, help_text = "The patient questionnaire to which the submission belongs")
    submission_date = models.DateTimeField(help_text = "The date and time of the submission",auto_now_add=True)
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)
    class Meta:
        ordering = ['-submission_date']
        verbose_name = 'Questionnaire Submission'
        verbose_name_plural = 'Questionnaire Submissions'
    def __str__(self):
        return f"{self.patient.name} - {self.patient_questionnaire.questionnaire.name}"

class QuestionnaireConstructScore(models.Model):
    '''
    Questionnaire Construct Score model. This is used to store the score for the construct.
    '''
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    questionnaire_submission = models.ForeignKey(QuestionnaireSubmission, on_delete=models.CASCADE, help_text = "The submission to which the score belongs")
    construct = models.ForeignKey(ConstructScale, on_delete=models.CASCADE, help_text = "The construct to which the score belongs")
    score = models.DecimalField(max_digits=10, decimal_places=2, help_text = "The score for the construct")
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)
    class Meta:
        ordering = ['-created_date']
        verbose_name = 'Questionnaire Construct Score'
        verbose_name_plural = 'Questionnaire Construct Scores'


class QuestionnaireItemResponse(models.Model):
    '''
    Questionnaire Item Response model. This is used to store the responses for the questionnaire item.
    '''
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    questionnaire_submission = models.ForeignKey(QuestionnaireSubmission, on_delete=models.CASCADE, help_text = "The submission to which the response belongs")
    questionnaire_item = models.ForeignKey(QuestionnaireItem, on_delete=models.CASCADE, help_text = "The item to which the response belongs")
    response_date = models.DateTimeField(help_text = "The date and time of the response",auto_now_add=True)
    response_value = models.CharField(max_length=255, help_text = "The response value",null=True, blank=True)
    created_date = models.DateTimeField(auto_now_add=True,editable=False)
    modified_date = models.DateTimeField(auto_now=True,editable=False)

    class Meta:
        ordering = ['-response_date']
        verbose_name = 'Questionnaire Response'
        verbose_name_plural = 'Questionnaire Responses'

    def __str__(self):
        return f"{self.questionnaire_submission.patient.name} - {self.questionnaire_item.item.name}"

class QuestionnaireItemRule(models.Model):
    '''
    Questionnaire Item Rule model. This is used to store rules that determine when a questionnaire item should be visible.
    '''
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    questionnaire_item = models.ForeignKey(QuestionnaireItem, on_delete=models.CASCADE, 
        related_name='visibility_rules',
        help_text="The item whose visibility is controlled by this rule")
    dependent_item = models.ForeignKey(QuestionnaireItem, on_delete=models.CASCADE,
        related_name='dependent_rules',
        help_text="The previous item whose response determines visibility")
    
    # Operator choices for comparison
    OPERATOR_CHOICES = [
        ('EQUALS', 'Equals'),
        ('NOT_EQUALS', 'Not Equals'),
        ('GREATER_THAN', 'Greater Than'),
        ('LESS_THAN', 'Less Than'),
        ('GREATER_THAN_EQUALS', 'Greater Than or Equals'),
        ('LESS_THAN_EQUALS', 'Less Than or Equals'),
        ('CONTAINS', 'Contains'),
        ('NOT_CONTAINS', 'Does Not Contain'),
    ]
    
    operator = models.CharField(max_length=40, choices=OPERATOR_CHOICES,help_text="The operator to use for the comparison")
    comparison_value = models.CharField(max_length=255, 
        help_text="The value to compare against")
    
    # Logical operator to combine multiple rules
    LOGICAL_OPERATOR_CHOICES = [
        ('AND', 'And'),
        ('OR', 'Or'),
    ]
    logical_operator = models.CharField(max_length=3, choices=LOGICAL_OPERATOR_CHOICES, 
        default='AND',
        help_text="How this rule combines with other rules")
    
    rule_order = models.IntegerField(default=0,
        help_text="Order in which rules should be evaluated")
    
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['rule_order']
        unique_together = ['questionnaire_item', 'dependent_item', 'operator', 'comparison_value']
        verbose_name = 'Questionnaire Item Rule'
        verbose_name_plural = 'Questionnaire Item Rules'

    def clean(self):
        # Ensure dependent_item comes before the questionnaire_item
        if self.dependent_item.question_number >= self.questionnaire_item.question_number:
            raise ValidationError({
                'dependent_item': f'Rule validation failed: The dependent question (Q{self.dependent_item.question_number}) must come before the current question (Q{self.questionnaire_item.question_number}) in the questionnaire. Please reorder the questions or choose a different dependent question.'
            })
        
        # Ensure both items belong to the same questionnaire
        if self.dependent_item.questionnaire != self.questionnaire_item.questionnaire:
            raise ValidationError({
                'dependent_item': f'Rule validation failed: The dependent question "{self.dependent_item.item.name}" belongs to a different questionnaire than the current question "{self.questionnaire_item.item.name}". Please select a question from the same questionnaire.'
            })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        qitem = getattr(self, 'questionnaire_item', None)
        ditem = getattr(self, 'dependent_item', None)
        return f"Rule for {qitem or '[unsaved]'} based on {ditem or '[unsaved]'}"

class QuestionnaireItemRuleGroup(models.Model):
    '''
    Questionnaire Item Rule Group model. This is used to group related rules together.
    '''
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    questionnaire_item = models.ForeignKey(QuestionnaireItem, on_delete=models.CASCADE,
        related_name='rule_groups')
    rules = models.ManyToManyField(QuestionnaireItemRule, related_name='rule_groups')
    group_order = models.IntegerField(default=0)
    
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['group_order']
        verbose_name = 'Questionnaire Item Rule Group'
        verbose_name_plural = 'Questionnaire Item Rule Groups'

    def __str__(self):
        return f"Rule group for {self.questionnaire_item}"

# Add signal to handle question number changes
@receiver(pre_save, sender=QuestionnaireItem)
def validate_question_number_change(sender, instance, **kwargs):
    if not instance.pk:
        return  # Only validate on update, not create
    try:
        old_instance = QuestionnaireItem.objects.get(pk=instance.pk)
    except QuestionnaireItem.DoesNotExist:
        return
    if old_instance.question_number != instance.question_number:
        # Check if this change would invalidate any rules
        affected_rules = QuestionnaireItemRule.objects.filter(
            # Case 1: This question has rules that depend on questions that would come after it
            models.Q(
                questionnaire_item=instance,
                dependent_item__question_number__gt=instance.question_number
            ) |
            # Case 2: This question is a dependent item for rules of questions that would come before it
            models.Q(
                dependent_item=instance,
                questionnaire_item__question_number__lt=instance.question_number
            )
        )
        if affected_rules.exists():
            rule_details = []
            dependent_rules = []
            dependent_item_rules = []
            
            for rule in affected_rules:
                if rule.questionnaire_item == instance:
                    dependent_rules.append(
                        f"- Rule for question '{rule.questionnaire_item.item.name}' "
                        f"based on question '{rule.dependent_item.item.name}'"
                    )
                else:
                    dependent_item_rules.append(
                        f"- Question '{rule.questionnaire_item.item.name}' "
                        f"depends on this question"
                    )
            
            if dependent_rules:
                rule_details.append("This question has rules that depend on later questions:")
                rule_details.extend(dependent_rules)
            
            if dependent_item_rules:
                if rule_details:
                    rule_details.append("")
                rule_details.append("Other questions have rules that depend on this question:")
                rule_details.extend(dependent_item_rules)
            
            rule_details.append("")
            rule_details.append("To move this question, you must first:")
            rule_details.append("1. Update or remove the affected rules")
            rule_details.append("2. Ensure all dependent questions come before the questions that depend on them")
            
            # Join with HTML line breaks and mark as safe
            error_message = mark_safe('<br>'.join(rule_details))
            raise ValidationError(error_message)