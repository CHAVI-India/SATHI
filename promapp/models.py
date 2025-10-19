from django.db import models
from django.utils import timezone
import uuid
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from patientapp.models import Patient,Diagnosis,Treatment
from django.contrib.auth.models import User
from parler.models import TranslatableModel, TranslatedFields
from django.db.models import Q
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.utils.safestring import mark_safe
import re
import statistics
from decimal import Decimal
from .equation_parser import EquationValidator, EquationTransformer
import logging
import numpy as np
import magic
import mimetypes

# Allowed extensions and their MIME types fore the media field.
allowed_types = {
    'audio': {
        'extensions': ['.mp3', '.wav', '.m4a', '.ogg', '.flac', '.aac'],
        'mimetypes': [
            'audio/mpeg', 'audio/wav', 'audio/x-wav', 'audio/mp4', 'audio/x-m4a',
            'audio/ogg', 'audio/x-flac', 'audio/flac', 'audio/aac', 'audio/x-aac'
        ],
    },
    'video': {
        'extensions': ['.mp4', '.mov', '.avi', '.wmv', '.flv', '.mkv'],
        'mimetypes': [
            'video/mp4', 'video/quicktime', 'video/x-msvideo', 'video/x-ms-wmv',
            'video/x-flv', 'video/x-matroska', 'video/mkv'
        ],
    },
    'image': {
        'extensions': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'],
        'mimetypes': [
            'image/jpeg', 'image/png', 'image/gif', 'image/bmp', 'image/tiff', 'image/webp'
        ],
    },
}
all_exts = sum([v['extensions'] for v in allowed_types.values()], [])
all_mimes = sum([v['mimetypes'] for v in allowed_types.values()], [])


# Create your models here.

# Setup logger for construct score calculations
logger = logging.getLogger('promapp.construct_scores')


class DirectionChoices(models.TextChoices):
    HIGHER_IS_BETTER = 'Higher is Better', 'Higher is Better'
    LOWER_IS_BETTER = 'Lower is Better', 'Lower is Better'
    MIDDLE_IS_BETTER = 'Middle is Better', 'Middle is Better'
    NO_DIRECTION = 'No Direction', 'No Direction'

class ConstructScale(models.Model):
    '''
    Construct Scale model. Construct Scale refers to the collection of items that are used to measure a construct.
    '''
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255,null=True, blank=True,help_text = "Enter the name of the construct scale like physical functioning, pain etc.",verbose_name="Name of the Construct Scale")
    instrument_name = models.CharField(max_length=255,null=True, blank=True,help_text = "The name of the patient reported outcome measurement instrument (Questionnaire) that the construct scale belongs to. For example EORTC QLQ C30", verbose_name="Name of the Instrument (Questionnaire)")
    instrument_version = models.CharField(max_length=255,null=True, blank=True,help_text = "The version of the instrument that the construct scale belongs to", verbose_name="Version of the Instrument (Questionnaire)")
    scale_equation = models.CharField(max_length=1025,null=True,blank=True,help_text = "The equation to calculate the score for the construct scale from the items in the scale", verbose_name="Equation")
    minimum_number_of_items = models.IntegerField(default=0,help_text = "The minimum number of items that must be answered to calculate the score for the construct scale", verbose_name="Minimum Number of Items")
    scale_better_score_direction = models.CharField(max_length=255, choices=DirectionChoices.choices, null=True, blank=True, verbose_name="Construct Score Direction", help_text = "Indicates whether higher or lower scores are better for this construct")
    scale_threshold_score = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,  help_text = "The score which is considered clinically important. Scores above or below this threshold (depending on direction) will be considered clinically actionable.", verbose_name="Construct Threshold Score")
    scale_minimum_clinical_important_difference = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,  help_text = "The minimum difference between two scores that would be considered clinically important. Changes exceeding this magnitude will result in clinically significant.",verbose_name="Minimum Important Difference Score (MID)")
    scale_normative_score_mean = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,  help_text = "The mean of the normative score for the construct scale. Used to display the normative score reference.", verbose_name="Construct Normative Score Mean")
    scale_normative_score_standard_deviation = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text = "The standard deviation of the normative score for the construct scale. Used to display the normative score reference.", verbose_name="Construct Normative Score Standard Deviation")
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

class ScoringTypeChoices(models.TextChoices):
    AVERAGE = 'Average', 'Average'
    SUM = 'Sum', 'Sum'
    MEDIAN = 'Median', 'Median'
    MODE = 'Mode', 'Mode'
    MIN = 'Min', 'Minimum'
    MAX = 'Max', 'Maximum'



class CompositeConstructScaleScoring(models.Model):
    '''
    Composite Construct Scale Scoring model. This is used when construct scales are combined to form a score.
    '''
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    composite_construct_scale_name = models.CharField(max_length=255, null=True, blank=True, help_text = "The name of the composite construct scale")
    construct_scales = models.ManyToManyField(ConstructScale, help_text = "The construct scales which will be used to calculate the composite construct scale")
    scoring_type = models.CharField(max_length=255, choices=ScoringTypeChoices.choices, help_text = "The type of scoring to use for the composite construct scale")
    composite_construct_score_direction = models.CharField(max_length=255, choices=DirectionChoices.choices, null=True, blank=True, verbose_name="Composite Construct Score Direction", help_text = "Indicates whether higher or lower scores are better for this composite construct")
    composite_construct_scale_threshold_score = models.CharField(max_length=255, null=True, blank=True, help_text = "The threshold score for the composite construct scale")
    composite_construct_scale_minimum_clinical_important_difference = models.CharField(max_length=255, null=True, blank=True, help_text = "The minimum important difference for the composite construct scale")
    composite_construct_scale_normative_score_mean = models.CharField(max_length=255, null=True, blank=True, help_text = "The normative score mean for the composite construct scale")
    composite_construct_scale_normative_score_standard_deviation = models.CharField(max_length=255, null=True, blank=True, help_text = "The normative score standard deviation for the composite construct scale")
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_date']
        verbose_name = 'Composite Construct Scale Scoring'
        verbose_name_plural = 'Composite Construct Scale Scorings'

    def __str__(self):
        return self.composite_construct_scale_name or f"Composite Scale {self.id}"


class LikertScale(models.Model):
    '''
    Likert scale type model. This is used to store the type of Likert Scale.
    '''
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    likert_scale_name = models.CharField(max_length=255, null=True, blank=True, help_text = "The name of the Likert Scale")
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)

    # Viridis color palette (from dark to light)
    VIRIDIS_COLORS = [
        '#440154',  # Dark purple
        '#3b528b',  # Dark blue
        '#21918c',  # Teal
        '#5ec962',  # Green
        '#fde725',  # Yellow
    ]

    class Meta:
        ordering = ['-created_date']
        verbose_name = 'Likert Scale'
        verbose_name_plural = 'Likert Scales'

    def __str__(self):
        return self.likert_scale_name

    def get_viridis_colors(self, n_colors):
        """
        Generate n colors from the viridis color palette.
        Returns a list of hex color codes.
        """
        if n_colors <= 0:
            return []
        
        # If we need more colors than we have in our palette,
        # we'll interpolate between the existing colors
        if n_colors <= len(self.VIRIDIS_COLORS):
            return self.VIRIDIS_COLORS[:n_colors]
        
        # For more colors, we'll interpolate between the base colors
        colors = []
        for i in range(n_colors):
            # Calculate position in the color range
            pos = i / (n_colors - 1)
            # Get the two colors to interpolate between
            idx = int(pos * (len(self.VIRIDIS_COLORS) - 1))
            next_idx = min(idx + 1, len(self.VIRIDIS_COLORS) - 1)
            # Linear interpolation between colors
            t = (pos * (len(self.VIRIDIS_COLORS) - 1)) - idx
            color = self.interpolate_color(
                self.VIRIDIS_COLORS[idx],
                self.VIRIDIS_COLORS[next_idx],
                t
            )
            colors.append(color)
        
        return colors

    def interpolate_color(self, color1, color2, t):
        """
        Interpolate between two hex colors.
        t is a float between 0 and 1.
        """
        # Convert hex to RGB
        def hex_to_rgb(hex_color):
            hex_color = hex_color.lstrip('#')
            return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        
        # Convert RGB to hex
        def rgb_to_hex(rgb):
            return '#{:02x}{:02x}{:02x}'.format(
                int(rgb[0]),
                int(rgb[1]),
                int(rgb[2])
            )
        
        # Get RGB values
        rgb1 = hex_to_rgb(color1)
        rgb2 = hex_to_rgb(color2)
        
        # Interpolate
        rgb = tuple(
            rgb1[i] + (rgb2[i] - rgb1[i]) * t
            for i in range(3)
        )
        
        return rgb_to_hex(rgb)

    def get_text_color(self, bg_color):
        """
        Determine if text should be light or dark based on background color brightness.
        Returns '#ffffff' for dark backgrounds and '#000000' for light backgrounds.
        """
        # Convert hex to RGB
        hex_color = bg_color.lstrip('#')
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        
        # Calculate relative luminance using the formula from WCAG 2.0
        # https://www.w3.org/TR/WCAG20/#relativeluminancedef
        r = r / 255
        g = g / 255
        b = b / 255
        
        r = r if r <= 0.03928 else ((r + 0.055) / 1.055) ** 2.4
        g = g if g <= 0.03928 else ((g + 0.055) / 1.055) ** 2.4
        b = b if b <= 0.03928 else ((b + 0.055) / 1.055) ** 2.4
        
        luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b
        
        # Return white text for dark backgrounds, black text for light backgrounds
        return '#ffffff' if luminance < 0.5 else '#000000'

    def get_option_colors(self, better_direction='Higher is Better'):
        """
        Get colors for each option in the scale.
        Colors are assigned based on the better_direction:
        - For 'Higher is Better': lighter colors for higher values
        - For 'Lower is Better': lighter colors for lower values
        """
        options = self.likertscaleresponseoption_set.all().order_by('option_value')
        n_options = options.count()
        
        if n_options == 0:
            return {}
        
        # Get colors from viridis palette
        colors = self.get_viridis_colors(n_options)
        
        # Create mapping of option values to colors
        color_map = {}
        for i, option in enumerate(options):
            if better_direction == 'Higher is Better':
                # Higher values get lighter colors
                color_map[str(option.option_value)] = colors[i]
            else:
                # Lower values get lighter colors
                color_map[str(option.option_value)] = colors[-(i+1)]
        
        return color_map

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
    option_emoji = models.CharField(max_length=255, null=True, blank=True, help_text = "The emoji to display for the option. This will be a string of the emoji.")
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

    def get_media_type(self, media_file=None):
        """
        Determine the media type based on file extension.
        
        Args:
            media_file: Optional media file object. If not provided, uses self.option_media
        
        Returns:
            str: 'audio', 'video', 'image', or 'other'
        """
        media = media_file or self.option_media
        if not media:
            return None
            
        try:
            file_name = str(media.name).lower()
            
            # Audio file extensions
            audio_extensions = ['.mp3', '.wav', '.ogg', '.m4a', '.aac', '.flac']
            if any(file_name.endswith(ext) for ext in audio_extensions):
                return 'audio'
            
            # Video file extensions (excluding .ogg which is handled by audio)
            video_extensions = ['.mp4', '.webm', '.avi', '.mov', '.wmv', '.mkv']
            if any(file_name.endswith(ext) for ext in video_extensions):
                return 'video'
            
            # Image file extensions
            image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp', '.tiff', '.ico']
            if any(file_name.endswith(ext) for ext in image_extensions):
                return 'image'
            
            # If no match found, return 'other'
            return 'other'
            
        except (AttributeError, TypeError):
            return None

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


    def validate_increment(self):
        if self.min_value and self.max_value and self.increment:
            if self.min_value > self.max_value:
                raise ValueError("Minimum value cannot be greater than maximum value")
            if self.increment <= 0:
                raise ValueError("Increment must be greater than 0")
            if (self.max_value - self.min_value) % self.increment != 0:
                raise ValueError("Maximum value minus minimum value must be divisible by increment")

    def get_available_languages(self):
        """Return a list of language codes for which translations exist."""
        return list(self.translations.values_list('language_code', flat=True))

class ResponseTypeChoices(models.TextChoices):
    TEXT = 'Text', 'Text Response'
    NUMBER = 'Number', 'Numeric Response'
    LIKERT = 'Likert', 'Likert Scale'
    RANGE = 'Range', 'Range Response'
    MEDIA = 'Media', 'Media Response'


class Item(TranslatableModel):
    '''
    Item model for storing questions in an instrument. Ensure full_clean() is called before saving in views and forms.
    Translatable field is name.
    '''
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    construct_scale = models.ManyToManyField(ConstructScale, help_text = "Each item can belong to a construct scale which is designed to measure a construct or domain related to the Patient Reported Outcome.")
    translations = TranslatedFields(
        name = models.CharField(max_length=255,null=True, blank=True, help_text = "The name of the item which will be displayed to the patient", db_index=True, verbose_name= "Item (Question) Text"),
        media = models.FileField(upload_to='item_media/', 
        null=True, 
        blank=True, 
        verbose_name = "Item (Question) Media File",
        help_text = "The media to display for the item. This will be an audio, video or image. Allowed files are <br> <ul> <li>Audio: .mp3, .wav, .m4a, .ogg, .flac, .aac</li> <li>Video: .mp4, .mov, .avi, .wmv, .flv, .mkv</li> <li>Image: .jpg, .jpeg, .png, .gif, .bmp, .tiff, .webp</li> </ul> ")
    )
    abbreviated_item_id = models.CharField(max_length=255, unique =True, null=True, blank=True, help_text = "The unique abbreviation of the item which will be used for exports. Allowed lower case characters, numbers and underscores. This is not displayed to the patient. For example question of EORTC QLQ C30 may be qlqc30_q1", verbose_name= "Item (Question) Abbreviation To be used")
    item_number = models.IntegerField(null=True, blank=True, help_text = "The number of the item in the construct scale")
    response_type = models.CharField(max_length=255, choices=ResponseTypeChoices.choices, db_index=True, help_text = "The type of response for the item")
    likert_response = models.ForeignKey(LikertScale, on_delete=models.CASCADE, null=True, blank=True)
    range_response = models.ForeignKey(RangeScale, on_delete=models.CASCADE, null=True, blank=True)
    is_required = models.BooleanField(default=False, help_text = "If True, the item is required to be answered for the construct score to be calculated")
    item_missing_value = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text = "The value to store for the item when it is not answered. This will be a number with upto 2 decimal places. If left blank then the item value will be a Null when missing. This is usually the correct practice so do not set the value unless the scoring document specifies this explicity.")
    item_better_score_direction = models.CharField(max_length=255, choices=DirectionChoices.choices, null=True, blank=True, verbose_name="Score Direction", help_text = "Indicates whether higher or lower scores are better for this item")
    item_threshold_score = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Threshold Score", help_text = "The score which is considered clinically important. Scores above or below this threshold (depending on direction) will be considered clinically actionable.")
    item_minimum_clinical_important_difference = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Minimum Clinical Important Difference", help_text = "The minimum difference between two scores that would be considered clinically important. Changes exceeding this magnitude will result in clinically significant impact on patient lives.")
    item_normative_score_mean = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Normative Score Mean", help_text = "The mean of the normative score for the item. Used to display the normative score reference.")
    item_normative_score_standard_deviation = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Normative Score Standard Deviation", help_text = "The standard deviation of the normative score for the item. Used to display the normative score reference.")
    discrimination_parameter = models.FloatField(null=True, blank=True, help_text = "Also known as a index. The discrimination parameter for the item. This value will be obtained from a IRT model like a GPCM model")
    difficulty_parameter = models.FloatField(null=True, blank=True, help_text = "Also known as b index. The difficulty parameter for the item. This value will be obtained from a IRT model like a GPCM model")
    pseudo_guessing_parameter = models.FloatField(null=True, blank=True, help_text = "Also known as c index. The pseudo-guessing parameter for the item. This value will be obtained from a IRT model like a GPCM model")
    created_date = models.DateTimeField(auto_now_add=True, db_index=True)
    modified_date = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_date']
        verbose_name = 'Item'
        verbose_name_plural = 'Items'
        indexes = [
            models.Index(fields=['response_type'], name='item_resptype_idx'),
            models.Index(fields=['item_number'], name='item_number_idx'),
        ]

    def get_related_constructs(self):
        return "\n".join([construct.name for construct in self.construct_scale.all()])

    def save(self, *args, **kwargs):
        # Check if we're updating an existing item 
        if self.pk:
            try:
                old_item = Item.objects.get(pk=self.pk)
                
                # Check if the item_number is changing
                if (old_item.item_number != self.item_number and 
                    old_item.item_number):
                    # Check if the old item number is referenced in equations
                    ref_check = old_item.is_referenced_in_equation()
                    if ref_check['is_referenced']:
                        raise ValidationError(
                            f'Cannot change item number for "{old_item.name}" as it is referenced in construct scale equations: '
                            f'{ref_check["construct_names"]}. '
                            f'Please update the equations first.'
                        )
                
                # Check if the construct_scale is changing (compare sets of IDs)
                old_construct_ids = set(old_item.construct_scale.values_list('id', flat=True))
                new_construct_ids = set(self.construct_scale.values_list('id', flat=True))
                
                if old_construct_ids != new_construct_ids and old_item.item_number:
                    # Check if this item is referenced in the OLD construct scale's equations
                    ref_check = old_item.is_referenced_in_equation()
                    if ref_check['is_referenced']:
                        raise ValidationError(
                            f'Cannot change construct scales for item "{old_item.name}" as it is referenced in equations '
                            f'for scales: {ref_check["construct_names"]}. '
                            f'Please update the equations first or remove the reference to {{q{old_item.item_number}}}.'
                        )
            except Item.DoesNotExist:
                pass
        
        super().save(*args, **kwargs)
        
        # Auto-assign item_number if not set and construct scales exist
        # This happens after save because ManyToMany relationships require the object to exist first
        if not self.item_number and self.construct_scale.exists():
            # Get the highest item number across all items in any of the construct scales this item belongs to
            max_item_number = 0
            for construct in self.construct_scale.all():
                last_item = construct.item_set.order_by('-item_number').first()
                if last_item and last_item.item_number:
                    max_item_number = max(max_item_number, last_item.item_number)
            
            self.item_number = max_item_number + 1 if max_item_number > 0 else 1
            # Use update to avoid triggering save() again and causing recursion
            Item.objects.filter(pk=self.pk).update(item_number=self.item_number)

    def clean(self):
        # Check if media validation should be skipped (for clearing invalid files)
        if getattr(self, '_skip_media_validation', False):
            # Skip media validation - this allows clearing invalid files
            pass
        else:
            # Validate Media file type
            for translation in self.translations.all():
                media_file = translation.media
                if not media_file:
                    continue
                name = getattr(media_file, 'name', None)
                if not name:
                    continue
                ext = name[name.rfind('.'):].lower()
                if ext not in all_exts:
                    raise ValidationError({'media': f"Invalid file extension '{ext}' for media. Allowed: {', '.join(all_exts)}"})

                # Guess type by extension
                expected_type = None
                for t, v in allowed_types.items():
                    if ext in v['extensions']:
                        expected_type = t
                        break

                # Get MIME type
                mime_type = None
                try:
                    mime = magic.Magic(mime=True)
                    file_obj = None
                    if hasattr(media_file, 'file'):
                        file_obj = media_file.file
                        file_obj.seek(0)
                        mime_type = mime.from_buffer(file_obj.read(2048))
                        file_obj.seek(0)
                    else:
                        file_path = media_file.path
                        with open(file_path, 'rb') as f:
                            mime_type = mime.from_buffer(f.read(2048))

                except Exception:
                    mime_type, _ = mimetypes.guess_type(name)
                if not mime_type:
                    raise ValidationError({'media': f"Could not determine MIME type for file '{name}'."})
                # Check MIME type is allowed for the extension
                valid_mimes = allowed_types[expected_type]['mimetypes'] if expected_type else all_mimes
                if mime_type not in valid_mimes:
                    raise ValidationError({'media': f"File MIME type '{mime_type}' does not match allowed types for extension '{ext}'. Allowed: {', '.join(valid_mimes)}"})        


        # Validate response type for the item and ensure correct type is selected.
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
        
        # Validate item_missing_value can only be set for numeric response types
        if self.item_missing_value is not None:
            if self.response_type not in [ResponseTypeChoices.LIKERT, ResponseTypeChoices.NUMBER, ResponseTypeChoices.RANGE]:
                raise ValidationError({
                    'item_missing_value': 'Missing value can only be specified for Likert, Number, or Range response types. '
                                        f'Current response type is {self.get_response_type_display()}.'
                })
        
        # Validate abbreviated_item_id format
        if self.abbreviated_item_id:
            import re
            if not re.match(r'^[a-z0-9_]+$', self.abbreviated_item_id):
                raise ValidationError({
                    'abbreviated_item_id': 'Only lowercase letters, numbers, and underscores are allowed.'
                })
    
    def delete(self, *args, **kwargs):
        """
        Override delete to check if this item is referenced in any construct scale equations.
        """
        ref_check = self.is_referenced_in_equation()
        if ref_check['is_referenced']:
            raise ValidationError(
                f'Cannot delete item "{self.name}" as it is referenced in construct scale equations '
                f'for scales: {ref_check["construct_names"]}. '
                f'Please update the equations first.'
            )
        super().delete(*args, **kwargs)

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
    
    def is_referenced_in_equation(self, check_item_number=None):
        """
        Check if this item (or a specific item number) is referenced in any of its construct scale equations.
        
        Args:
            check_item_number: If provided, check this specific item number instead of self.item_number
        
        Returns:
            dict with 'is_referenced': bool, 'equations': list of equations, and 'construct_names': str
        """
        item_number_to_check = check_item_number if check_item_number is not None else self.item_number
        if not item_number_to_check:
            return {'is_referenced': False, 'equations': [], 'construct_names': ''}
        
        # Check all construct scales this item belongs to
        referenced_constructs = []
        referenced_equations = []
        
        for construct in self.construct_scale.all():
            if construct.scale_equation:
                # Extract question references from the equation
                question_refs = re.findall(r'\{q(\d+)\}', construct.scale_equation)
                if str(item_number_to_check) in question_refs:
                    referenced_constructs.append(construct.name)
                    referenced_equations.append(construct.scale_equation)
        
        is_referenced = len(referenced_constructs) > 0
        
        return {
            'is_referenced': is_referenced,
            'equations': referenced_equations,
            'construct_names': ', '.join(referenced_constructs) if is_referenced else ''
        }
    
    def get_media_type(self, media_file=None):
        """
        Determine the media type based on file extension.
        
        Args:
            media_file: Optional media file object. If not provided, uses self.media
        
        Returns:
            str: 'audio', 'video', 'image', or 'other'
        """
        media = media_file or self.media
        if not media:
            return None
            
        try:
            file_name = str(media.name).lower()
            
            # Audio file extensions
            audio_extensions = ['.mp3', '.wav', '.ogg', '.m4a', '.aac', '.flac']
            if any(file_name.endswith(ext) for ext in audio_extensions):
                return 'audio'
            
            # Video file extensions (excluding .ogg which is handled by audio)
            video_extensions = ['.mp4', '.webm', '.avi', '.mov', '.wmv', '.mkv']
            if any(file_name.endswith(ext) for ext in video_extensions):
                return 'video'
            
            # Image file extensions
            image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp', '.tiff', '.ico']
            if any(file_name.endswith(ext) for ext in image_extensions):
                return 'image'
            
            # If no match found, return 'other'
            return 'other'
            
        except (AttributeError, TypeError):
            return None
    
    def get_media_info(self):
        """
        Get comprehensive media information for template use.
        Handles translatable media fields with proper fallback.
        
        Returns:
            dict: Contains media_type, url, name, and has_media
        """
        # Simple approach: check if media exists using the same logic as template
        if self.media:
            try:
                return {
                    'has_media': True,
                    'media_type': self.get_media_type(),
                    'url': self.media.url,
                    'name': self.media.name
                }
            except (AttributeError, ValueError):
                pass
        
        # Fallback: try to find media in any translation
        for translation in self.translations.all():
            if translation.media:
                try:
                    return {
                        'has_media': True,
                        'media_type': self.get_media_type(translation.media),
                        'url': translation.media.url,
                        'name': translation.media.name
                    }
                except (AttributeError, ValueError):
                    continue
        
        # No media found
        return {
            'has_media': False,
            'media_type': None,
            'url': None,
            'name': None
        }

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
    questionnaire_answer_interval = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text = "The interval in seconds between answering the same questionnaire by the same patient. Set to 0 to allow immediate re-answering."
    )
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
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, help_text = "The patient to which the questionnaire belongs", db_index=True)
    questionnaire = models.ForeignKey(Questionnaire, on_delete=models.CASCADE, help_text = "The questionnaire to which the patient belongs", db_index=True)
    display_questionnaire = models.BooleanField(default=False, help_text = "If True, the questionnaire is currently will be displayed for the patient", db_index=True)
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_date']
        verbose_name = 'Patient Questionnaire'
        verbose_name_plural = 'Patient Questionnaires'
        indexes = [
            models.Index(fields=['patient', 'display_questionnaire'], name='pq_patient_display_idx'),
            models.Index(fields=['patient', 'questionnaire'], name='pq_patient_quest_idx'),
        ]
        
    def __str__(self):
        return f"{self.patient.name} - {self.questionnaire.name}"

class QuestionnaireSubmission(models.Model):
    '''
    Questionnaire Submission model. This is used to store the submission of the questionnaire.
    '''
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, help_text = "The patient to which the submission belongs")
    user_submitting_questionnaire = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, help_text = "The user submitting the questionnaire")
    patient_questionnaire = models.ForeignKey(PatientQuestionnaire, on_delete=models.CASCADE, help_text = "The patient questionnaire to which the submission belongs")
    submission_date = models.DateTimeField(help_text = "The date and time of the submission",default=timezone.now)
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-submission_date']
        verbose_name = 'Questionnaire Submission'
        verbose_name_plural = 'Questionnaire Submissions'
        indexes = [
            models.Index(fields=['patient', 'submission_date'], name='qsub_patient_date_idx'),
            models.Index(fields=['patient_questionnaire', 'submission_date'], name='qsub_pq_date_idx'),
            models.Index(fields=['submission_date'], name='qsub_date_idx'),
        ]
    
    def __str__(self):
        return f"{self.patient.name} - {self.patient_questionnaire.questionnaire.name}"

class QuestionnaireConstructScore(models.Model):
    '''
    Questionnaire Construct Score model. This is used to store the score for the construct.
    '''
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    questionnaire_submission = models.ForeignKey(QuestionnaireSubmission, on_delete=models.CASCADE, help_text = "The submission to which the score belongs")
    construct = models.ForeignKey(ConstructScale, on_delete=models.CASCADE, help_text = "The construct to which the score belongs")
    score = models.DecimalField(max_digits=10, decimal_places=2, help_text = "The score for the construct", null=True, blank=True)
    items_answered = models.IntegerField(help_text = "The number of items answered for the construct", null=True, blank=True)
    items_not_answered = models.IntegerField(help_text = "The number of items not answered for the construct", null=True, blank=True)
    calculation_log = models.TextField(help_text = "The log of the equation processing", null=True, blank=True)
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_date']
        verbose_name = 'Questionnaire Construct Score'
        verbose_name_plural = 'Questionnaire Construct Scores'
        indexes = [
            models.Index(fields=['questionnaire_submission', 'construct'], name='qcs_submission_construct_idx'),
            models.Index(fields=['construct', 'questionnaire_submission'], name='qcs_construct_submission_idx'),
        ]

class QuestionnaireConstructScoreComposite(models.Model):
    '''
    Questionnaire Construct Score Composite model. This is used to store the composite score for the construct.
    '''
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    questionnaire_submission = models.ForeignKey(QuestionnaireSubmission, on_delete=models.CASCADE, help_text = "The submission to which the composite score belongs")
    composite_construct_scale = models.ForeignKey(CompositeConstructScaleScoring, on_delete=models.CASCADE, help_text = "The composite construct scale to which the score belongs")
    score = models.DecimalField(max_digits=10, decimal_places=2, help_text = "The score for the composite construct", null=True, blank=True)
    calculation_log = models.TextField(help_text = "The log of the equation processing", null=True, blank=True)
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)
    class Meta:
        ordering = ['-created_date']
        verbose_name = 'Questionnaire Construct Score Composite'

class QuestionnaireItemResponse(models.Model):
    '''
    Questionnaire Item Response model. This is used to store the responses for the questionnaire item.
    '''
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    questionnaire_submission = models.ForeignKey(QuestionnaireSubmission, on_delete=models.CASCADE, help_text = "The submission to which the response belongs")
    questionnaire_item = models.ForeignKey(QuestionnaireItem, on_delete=models.CASCADE, help_text = "The item to which the response belongs")
    response_date = models.DateTimeField(help_text = "The date and time of the response",auto_now_add=True)
    response_value = models.CharField(max_length=255, help_text = "The response value",null=True, blank=True)
    response_media = models.FileField(upload_to='questionnaire_responses/', help_text = "The media response",null=True, blank=True)
    created_date = models.DateTimeField(auto_now_add=True,editable=False)
    modified_date = models.DateTimeField(auto_now=True,editable=False)

    class Meta:
        ordering = ['-response_date']
        verbose_name = 'Questionnaire Response'
        verbose_name_plural = 'Questionnaire Responses'
        indexes = [
            models.Index(fields=['questionnaire_submission', 'questionnaire_item'], name='qir_submission_item_idx'),
            models.Index(fields=['questionnaire_item', 'questionnaire_submission'], name='qir_item_submission_idx'),
            models.Index(fields=['response_date'], name='qir_response_date_idx'),
        ]

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

# Signal handler to calculate construct scores when a questionnaire submission is created
@receiver(post_save, sender=QuestionnaireSubmission)
def calculate_construct_scores(sender, instance, created, **kwargs):
    """
    Signal handler that calculates construct scores when a questionnaire is submitted.
    
    This function only registers the submission for later processing.
    The actual calculation happens after all responses are saved.
    """
    if not created:
        # Only register new submissions
        return

    # We'll log that we received a new submission but won't calculate scores yet
    logger.info(f"New questionnaire submission registered: {instance.id} from patient {instance.patient.name}")
    # The actual calculation will be done after responses are saved

@receiver(post_save, sender=QuestionnaireItemResponse)
def trigger_score_calculation_on_response(sender, instance, created, **kwargs):
    """
    When a response is saved, check if we need to calculate scores.
    We'll do this after a slight delay to allow all responses to be saved.
    """
    if not created:
        # Only trigger on new responses
        return
        
    # Get the submission this response belongs to
    submission = instance.questionnaire_submission
    
    # We'll use a simple approach - check if this appears to be the last response
    # by comparing the current number of responses to the number of questions
    questionnaire = submission.patient_questionnaire.questionnaire
    total_questions = QuestionnaireItem.objects.filter(questionnaire=questionnaire).count()
    current_responses = QuestionnaireItemResponse.objects.filter(questionnaire_submission=submission).count()
    
    logger.debug(f"Response {instance.id} saved for submission {submission.id}: {current_responses}/{total_questions} questions answered")
    
    if current_responses == total_questions:
        # This appears to be the last response, calculate the scores
        logger.info(f"All responses received for submission {submission.id}, calculating scores")
        calculate_scores_for_submission(submission)

# Move the actual calculation logic to a separate function that can be called
# both automatically by the signal and manually if needed
def calculate_scores_for_submission(submission):
    """
    Calculate construct scores for a completed questionnaire submission.
    
    This function contains the actual calculation logic and can be called
    either automatically by the signal handler or manually.
    """
    logger.info(f"Calculating construct scores for submission {submission.id} from patient {submission.patient.name}")
    
    # Get the questionnaire related to this submission
    questionnaire = submission.patient_questionnaire.questionnaire
    
    # Get all questionnaire items for this questionnaire
    questionnaire_items = QuestionnaireItem.objects.filter(questionnaire=questionnaire)
    logger.debug(f"Found {questionnaire_items.count()} questionnaire items")
    
    # Get responses for this submission - prefetch related questionnaire_item and item
    responses = QuestionnaireItemResponse.objects.filter(
        questionnaire_submission=submission
    ).select_related('questionnaire_item', 'questionnaire_item__item')
    logger.debug(f"Found {responses.count()} responses")
    
    # If no responses are found, we can't calculate any scores
    if not responses.exists():
        logger.warning(f"No responses found for submission {submission.id}, cannot calculate scores")
        return
    
    # Debug: Log all responses with their values and item numbers
    for response in responses:
        qi = response.questionnaire_item
        logger.debug(f"Response found - Q{qi.question_number}: item_number={qi.item.item_number}, "
                    f"value={response.response_value}, type={qi.item.response_type}")
    
    # Find all construct scales used in this questionnaire
    construct_scales = set()
    item_to_constructs_map = {}  # Map of item_id to list of construct_scales
    
    # Map items to their constructs and build set of unique constructs
    # Use prefetch_related for ManyToMany relationship
    for qi in questionnaire_items.select_related('item').prefetch_related('item__construct_scale'):
        item_constructs = qi.item.construct_scale.all()
        if item_constructs:
            for construct in item_constructs:
                construct_scales.add(construct)
                if qi.item.id not in item_to_constructs_map:
                    item_to_constructs_map[qi.item.id] = []
                item_to_constructs_map[qi.item.id].append(construct)
    
    logger.debug(f"Found {len(construct_scales)} construct scales")
    
    # Process each construct scale that has an equation
    for construct in construct_scales:
        if not construct.scale_equation:
            logger.debug(f"Skipping construct {construct.name} - no equation defined")
            continue
        
        logger.info(f"Processing construct {construct.name} with equation: {construct.scale_equation}")
        
        # Initialize calculation log for this construct
        calculation_log = []
        calculation_log.append(f"=== CONSTRUCT SCORE CALCULATION ===")
        calculation_log.append(f"Construct: {construct.name}")
        calculation_log.append(f"Equation: {construct.scale_equation}")
        calculation_log.append(f"Minimum required items: {construct.minimum_number_of_items}")
        calculation_log.append("")
        
        # Create a mapping of item numbers to response values for this construct
        response_values = {}
        valid_response_count = 0
        total_construct_items = 0
        
        # Get all items that belong to this construct scale (regardless of whether they're in the questionnaire)
        all_construct_items = Item.objects.filter(
            construct_scale=construct,
            response_type__in=['Number', 'Likert', 'Range']
        ).prefetch_related('construct_scale')
        
        # Create a mapping of item_id to response for quick lookup
        # An item can belong to multiple constructs, so check if construct is in the item's construct list
        response_map = {}
        for response in responses:
            qi = response.questionnaire_item
            # Check if this item belongs to the current construct
            if qi.item.id in item_to_constructs_map and construct in item_to_constructs_map[qi.item.id]:
                response_map[qi.item.id] = response
        
        # Process all items that belong to this construct
        calculation_log.append("ITEM VALUE PROCESSING:")
        for item in all_construct_items:
            total_construct_items += 1
            item_number = item.item_number
            
            # Check if we have a response for this item
            if item.id in response_map:
                response = response_map[item.id]
                response_value = response.response_value
                
                logger.debug(f"For construct {construct.name}: item {item_number} has response '{response_value}'")
                calculation_log.append(f"Item {item_number} ({item.name}): Response = '{response_value}'")
                
                # Check if response has a valid value
                if response_value and response_value.strip():
                    try:
                        # Convert to float for calculation
                        response_values[item_number] = float(response_value)
                        valid_response_count += 1
                        logger.debug(f"Valid response for item {item_number}: value = {response_value}")
                        calculation_log.append(f"  → Using response value: {response_value}")
                    except (ValueError, TypeError):
                        logger.warning(f"Could not convert response for item {item_number} to float: {response_value}")
                        # Use missing value or None
                        if item.item_missing_value is not None:
                            response_values[item_number] = float(item.item_missing_value)
                            valid_response_count += 1  # Count missing values as valid for minimum count
                            logger.debug(f"Using missing value for item {item_number}: {item.item_missing_value}")
                            calculation_log.append(f"  → Invalid response, using missing value: {item.item_missing_value}")
                        else:
                            response_values[item_number] = None
                            logger.debug(f"Using None for item {item_number} (no missing value specified)")
                            calculation_log.append(f"  → Invalid response, using None (no missing value specified)")
                else:
                    # Empty or missing response - use missing value or None
                    if item.item_missing_value is not None:
                        response_values[item_number] = float(item.item_missing_value)
                        valid_response_count += 1  # Count missing values as valid for minimum count
                        logger.debug(f"Empty response for item {item_number}, using missing value: {item.item_missing_value}")
                        calculation_log.append(f"  → Empty response, using missing value: {item.item_missing_value}")
                    else:
                        response_values[item_number] = None
                        logger.debug(f"Empty response for item {item_number}, using None (no missing value specified)")
                        calculation_log.append(f"  → Empty response, using None (no missing value specified)")
            else:
                # Item is part of construct but not in questionnaire - use missing value or None
                calculation_log.append(f"Item {item_number} ({item.name}): Not in questionnaire")
                if item.item_missing_value is not None:
                    response_values[item_number] = float(item.item_missing_value)
                    valid_response_count += 1  # Count missing values as valid for minimum count
                    logger.debug(f"Item {item_number} not in questionnaire, using missing value: {item.item_missing_value}")
                    calculation_log.append(f"  → Using missing value: {item.item_missing_value}")
                else:
                    response_values[item_number] = None
                    logger.debug(f"Item {item_number} not in questionnaire, using None (no missing value specified)")
                    calculation_log.append(f"  → Using None (no missing value specified)")
        
        # Debug: Log the final response values dictionary
        logger.debug(f"Response values for construct {construct.name}: {response_values}")
        
        calculation_log.append("")
        calculation_log.append("FINAL VALUES FOR CALCULATION:")
        for item_num, value in sorted(response_values.items()):
            calculation_log.append(f"  {{{item_num}}} = {value}")
        
        # Check for required items that are missing valid responses
        required_items_missing = []
        calculation_log.append("")
        calculation_log.append("REQUIRED ITEMS VALIDATION:")
        for item in all_construct_items:
            # Check if this item is required for scoring
            if item.is_required:
                item_number = item.item_number
                # Check if this required item has a valid response or missing value
                if item_number not in response_values or response_values[item_number] is None:
                    required_items_missing.append(item_number)
                    logger.debug(f"Required item {item_number} ({item.name}) is missing a valid response and has no missing value specified")
                    calculation_log.append(f"  Item {item_number} ({item.name}): REQUIRED - MISSING")
                else:
                    calculation_log.append(f"  Item {item_number} ({item.name}): REQUIRED - OK")
        
        # If any required items are missing valid responses, skip score calculation
        if required_items_missing:
            logger.warning(f"Cannot calculate score for construct {construct.name}. " 
                          f"Required items missing valid responses: items {required_items_missing}")
            calculation_log.append("")
            calculation_log.append(f"CALCULATION FAILED: Required items missing: {required_items_missing}")
            calculation_log.append("Score calculation cannot proceed.")
            
            # Create a record but with no score to indicate required items were missing
            QuestionnaireConstructScore.objects.create(
                questionnaire_submission=submission,
                construct=construct,
                score=None,
                items_answered=valid_response_count,
                items_not_answered=total_construct_items - valid_response_count,
                calculation_log="\n".join(calculation_log)
            )
            continue
        
        # Calculate items answered and not answered
        # Count actual responses (not missing values) as answered
        actual_responses_count = 0
        for item in all_construct_items:
            item_number = item.item_number
            if item.id in response_map:
                response = response_map[item.id]
                if response.response_value and response.response_value.strip():
                    try:
                        float(response.response_value)
                        actual_responses_count += 1
                    except (ValueError, TypeError):
                        pass  # Invalid response, don't count
        
        items_answered = actual_responses_count
        items_not_answered = total_construct_items - actual_responses_count
        
        logger.debug(f"For construct {construct.name}: {items_answered} items answered, {items_not_answered} items not answered, {total_construct_items} total items")
        
        calculation_log.append("")
        calculation_log.append("CALCULATION SUMMARY:")
        calculation_log.append(f"  Total items in construct: {total_construct_items}")
        calculation_log.append(f"  Items with actual responses: {items_answered}")
        calculation_log.append(f"  Items not answered: {items_not_answered}")
        calculation_log.append(f"  Valid values for calculation: {valid_response_count}")
        calculation_log.append(f"  Minimum required items: {construct.minimum_number_of_items}")
        
        # Check if we have enough valid responses (minimum_number_of_items logic)
        min_required = construct.minimum_number_of_items
        if valid_response_count < min_required:
            logger.warning(f"Not enough valid responses for construct {construct.name}. " 
                          f"Required: {min_required}, Found: {valid_response_count}")
            calculation_log.append("")
            calculation_log.append(f"CALCULATION FAILED: Insufficient valid responses")
            calculation_log.append(f"Required: {min_required}, Found: {valid_response_count}")
            calculation_log.append("Score calculation cannot proceed.")
            
            # Still create a record but with no score, and include the count data
            QuestionnaireConstructScore.objects.create(
                questionnaire_submission=submission,
                construct=construct,
                score=None,
                items_answered=items_answered,
                items_not_answered=items_not_answered,
                calculation_log="\n".join(calculation_log)
            )
            continue
        
        # Calculate score using equation parser
        try:
            calculation_log.append("")
            calculation_log.append("EQUATION PROCESSING:")
            calculation_log.append(f"  Equation: {construct.scale_equation}")
            
            # Parse the equation
            validator = EquationValidator()
            tree = validator.parser.parse(construct.scale_equation)
            calculation_log.append("  Equation parsing: SUCCESS")
            
            # Transform and evaluate the equation
            transformer = EquationTransformer(
                question_values=response_values,
                minimum_required_items=min_required
            )
            
            score = transformer.transform(tree)
            
            # Store the result with items answered/not answered counts
            logger.info(f"Calculated score for construct {construct.name}: {score}")
            
            calculation_log.append(f"  Equation evaluation: SUCCESS")
            calculation_log.append(f"  Final calculated score: {score}")
            calculation_log.append("")
            calculation_log.append("CALCULATION COMPLETED SUCCESSFULLY")
            
            QuestionnaireConstructScore.objects.create(
                questionnaire_submission=submission,
                construct=construct,
                score=score,
                items_answered=items_answered,
                items_not_answered=items_not_answered,
                calculation_log="\n".join(calculation_log)
            )
        
        except ValidationError as e:
            logger.error(f"Equation validation error for construct {construct.name}: {str(e)}")
            calculation_log.append("")
            calculation_log.append(f"CALCULATION FAILED: Equation validation error")
            calculation_log.append(f"Error: {str(e)}")
            
            QuestionnaireConstructScore.objects.create(
                questionnaire_submission=submission,
                construct=construct,
                score=None,
                items_answered=items_answered,
                items_not_answered=items_not_answered,
                calculation_log="\n".join(calculation_log)
            )
        except Exception as e:
            logger.error(f"Error calculating score for construct {construct.name}: {str(e)}", exc_info=True)
            calculation_log.append("")
            calculation_log.append(f"CALCULATION FAILED: Unexpected error")
            calculation_log.append(f"Error: {str(e)}")
            
            QuestionnaireConstructScore.objects.create(
                questionnaire_submission=submission,
                construct=construct,
                score=None,
                items_answered=items_answered,
                items_not_answered=items_not_answered,
                calculation_log="\n".join(calculation_log)
            )
    
    # After calculating all individual construct scores, calculate composite scores
    calculate_composite_scores_for_submission(submission)


def calculate_composite_scores_for_submission(submission):
    """
    Calculate composite construct scores for a questionnaire submission.
    
    This function calculates composite scores based on CompositeConstructScaleScoring
    definitions. Only composite scales that have at least one component construct
    present in the current submission will be processed. Missing construct scores 
    are treated as 0 for the computation.
    """
    
    logger.info(f"Calculating composite construct scores for submission {submission.id}")
    
    # Get all construct scores for this submission
    construct_scores = QuestionnaireConstructScore.objects.filter(
        questionnaire_submission=submission
    ).select_related('construct')
    
    # Create a mapping of construct_id to score for quick lookup
    construct_score_map = {}
    calculated_construct_ids = set()
    for cs in construct_scores:
        calculated_construct_ids.add(cs.construct.id)
        # Only include scores that were successfully calculated (not None)
        if cs.score is not None:
            construct_score_map[cs.construct.id] = float(cs.score)
    
    logger.debug(f"Found {len(construct_score_map)} valid construct scores for composite calculation")
    
    # If no construct scores were calculated, skip composite score calculation
    if not calculated_construct_ids:
        logger.debug("No construct scores calculated for this submission, skipping composite score calculation")
        return
    
    # Get only composite construct scale scoring definitions that are relevant to this submission
    # A composite scale is relevant if at least one of its component constructs was calculated
    composite_scales = CompositeConstructScaleScoring.objects.filter(
        construct_scales__id__in=calculated_construct_ids
    ).distinct().prefetch_related('construct_scales')
    
    if not composite_scales.exists():
        logger.debug("No relevant composite construct scale scoring definitions found for this submission")
        return
    
    logger.info(f"Found {composite_scales.count()} relevant composite scales to process")
    
    # Process each composite construct scale
    for composite_scale in composite_scales:
        logger.info(f"Processing composite scale: {composite_scale.composite_construct_scale_name}")
        
        # Initialize calculation log for this composite
        calculation_log = []
        calculation_log.append(f"=== COMPOSITE CONSTRUCT SCORE CALCULATION ===")
        calculation_log.append(f"Composite Scale: {composite_scale.composite_construct_scale_name}")
        calculation_log.append(f"Scoring Type: {composite_scale.scoring_type}")
        calculation_log.append("")
        
        # Get the construct scales that make up this composite
        component_constructs = composite_scale.construct_scales.all()
        
        if not component_constructs.exists():
            logger.warning(f"No component constructs found for composite scale {composite_scale.composite_construct_scale_name}")
            calculation_log.append("CALCULATION FAILED: No component constructs found")
            
            QuestionnaireConstructScoreComposite.objects.create(
                questionnaire_submission=submission,
                composite_construct_scale=composite_scale,
                score=None,
                calculation_log="\n".join(calculation_log)
            )
            continue
        
        # Collect scores for the component constructs
        component_scores = []
        missing_constructs = []
        
        calculation_log.append("COMPONENT CONSTRUCT SCORES:")
        for construct in component_constructs:
            if construct.id in construct_score_map:
                score = construct_score_map[construct.id]
                component_scores.append(score)
                logger.debug(f"Found score {score} for construct {construct.name}")
                calculation_log.append(f"  {construct.name}: {score}")
            else:
                # Missing scores are treated as 0
                component_scores.append(0.0)
                missing_constructs.append(construct.name)
                logger.debug(f"Missing score for construct {construct.name}, using 0")
                calculation_log.append(f"  {construct.name}: MISSING (using 0)")
        
        if missing_constructs:
            logger.info(f"Composite scale {composite_scale.composite_construct_scale_name}: "
                       f"Missing scores for constructs {missing_constructs}, treating as 0")
            calculation_log.append("")
            calculation_log.append(f"Note: Missing scores treated as 0: {', '.join(missing_constructs)}")
        
        # Calculate the composite score based on scoring type
        try:
            composite_score = None
            scoring_type = composite_scale.scoring_type
            
            calculation_log.append("")
            calculation_log.append("COMPOSITE SCORE CALCULATION:")
            calculation_log.append(f"  Input values: {component_scores}")
            calculation_log.append(f"  Scoring method: {scoring_type}")
            
            if scoring_type == ScoringTypeChoices.AVERAGE:
                if component_scores:
                    composite_score = sum(component_scores) / len(component_scores)
                    logger.debug(f"Average calculation: {component_scores} = {composite_score}")
                    calculation_log.append(f"  Calculation: sum({component_scores}) / {len(component_scores)} = {composite_score}")
            
            elif scoring_type == ScoringTypeChoices.SUM:
                composite_score = sum(component_scores)
                logger.debug(f"Sum calculation: {component_scores} = {composite_score}")
                calculation_log.append(f"  Calculation: sum({component_scores}) = {composite_score}")
            
            elif scoring_type == ScoringTypeChoices.MEDIAN:
                if component_scores:
                    composite_score = statistics.median(component_scores)
                    logger.debug(f"Median calculation: {component_scores} = {composite_score}")
                    calculation_log.append(f"  Calculation: median({component_scores}) = {composite_score}")
            
            elif scoring_type == ScoringTypeChoices.MODE:
                if component_scores:
                    try:
                        composite_score = statistics.mode(component_scores)
                        logger.debug(f"Mode calculation: {component_scores} = {composite_score}")
                        calculation_log.append(f"  Calculation: mode({component_scores}) = {composite_score}")
                    except statistics.StatisticsError:
                        # No unique mode found, use the first value as fallback
                        composite_score = component_scores[0] if component_scores else 0
                        logger.warning(f"No unique mode found for {component_scores}, using first value: {composite_score}")
                        calculation_log.append(f"  No unique mode found, using first value: {composite_score}")
            
            elif scoring_type == ScoringTypeChoices.MIN:
                if component_scores:
                    composite_score = min(component_scores)
                    logger.debug(f"Min calculation: {component_scores} = {composite_score}")
                    calculation_log.append(f"  Calculation: min({component_scores}) = {composite_score}")
            
            elif scoring_type == ScoringTypeChoices.MAX:
                if component_scores:
                    composite_score = max(component_scores)
                    logger.debug(f"Max calculation: {component_scores} = {composite_score}")
                    calculation_log.append(f"  Calculation: max({component_scores}) = {composite_score}")
            
            else:
                logger.error(f"Unknown scoring type: {scoring_type}")
                calculation_log.append(f"  ERROR: Unknown scoring type: {scoring_type}")
                
                QuestionnaireConstructScoreComposite.objects.create(
                    questionnaire_submission=submission,
                    composite_construct_scale=composite_scale,
                    score=None,
                    calculation_log="\n".join(calculation_log)
                )
                continue
            
            if composite_score is not None:
                # Convert to Decimal for storage
                composite_score_decimal = Decimal(str(composite_score))
                
                calculation_log.append(f"  Final composite score: {composite_score}")
                calculation_log.append("")
                calculation_log.append("CALCULATION COMPLETED SUCCESSFULLY")
                
                # Store the composite score
                QuestionnaireConstructScoreComposite.objects.create(
                    questionnaire_submission=submission,
                    composite_construct_scale=composite_scale,
                    score=composite_score_decimal,
                    calculation_log="\n".join(calculation_log)
                )
                
                logger.info(f"Calculated composite score for {composite_scale.composite_construct_scale_name}: {composite_score}")
            else:
                logger.warning(f"Could not calculate composite score for {composite_scale.composite_construct_scale_name}")
                calculation_log.append("  CALCULATION FAILED: Could not calculate composite score")
                
                QuestionnaireConstructScoreComposite.objects.create(
                    questionnaire_submission=submission,
                    composite_construct_scale=composite_scale,
                    score=None,
                    calculation_log="\n".join(calculation_log)
                )
        
        except Exception as e:
            logger.error(f"Error calculating composite score for {composite_scale.composite_construct_scale_name}: {str(e)}", exc_info=True)
            calculation_log.append("")
            calculation_log.append(f"CALCULATION FAILED: Unexpected error")
            calculation_log.append(f"Error: {str(e)}")
            
            QuestionnaireConstructScoreComposite.objects.create(
                questionnaire_submission=submission,
                composite_construct_scale=composite_scale,
                score=None,
                calculation_log="\n".join(calculation_log)
            )