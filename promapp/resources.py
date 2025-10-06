"""
This module provides import/export functionality for the Item model and its translations.
It uses django-import-export to handle CSV/Excel imports and exports, and django-parler
for handling translations.
"""

from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget, CharWidget
from .models import Item, ConstructScale, LikertScale, RangeScale, ResponseTypeChoices
from parler.models import TranslatableModel
from django.utils.translation import get_language
from django.conf import settings


class ResponseTypeWidget(CharWidget):
    """
    Custom widget to handle response_type field imports.
    Accepts both the choice value (e.g., 'Likert') and the display name (e.g., 'Likert Scale').
    """
    def clean(self, value, row=None, *args, **kwargs):
        """
        Clean the response_type value from CSV.
        Handles both choice values and display names.
        """
        if not value:
            return value
        
        # Convert to string and strip whitespace
        value = str(value).strip()
        
        # Create a mapping of both values and labels to choice values
        choice_mapping = {
            # Direct values (case-insensitive)
            'text': ResponseTypeChoices.TEXT,
            'number': ResponseTypeChoices.NUMBER,
            'likert': ResponseTypeChoices.LIKERT,
            'range': ResponseTypeChoices.RANGE,
            'media': ResponseTypeChoices.MEDIA,
            # Display names (case-insensitive)
            'text response': ResponseTypeChoices.TEXT,
            'numeric response': ResponseTypeChoices.NUMBER,
            'likert scale': ResponseTypeChoices.LIKERT,
            'range response': ResponseTypeChoices.RANGE,
            'media response': ResponseTypeChoices.MEDIA,
        }
        
        # Try to find a match (case-insensitive)
        value_lower = value.lower()
        if value_lower in choice_mapping:
            return choice_mapping[value_lower]
        
        # If exact match found in valid choices, return as-is
        valid_choices = [choice[0] for choice in ResponseTypeChoices.choices]
        if value in valid_choices:
            return value
        
        # If no match found, return the original value
        # This will trigger a validation error if it's invalid
        return value


class ItemTranslationResource(resources.ModelResource):
    """
    Resource for importing/exporting Item translations
    """
    master = fields.Field(
        column_name='master_id',
        attribute='master',
        widget=ForeignKeyWidget(Item, 'id')
    )
    language_code = fields.Field(column_name='language_code')
    name = fields.Field(column_name='name')

    class Meta:
        model = Item._parler_meta.root_model
        fields = ('id', 'master', 'language_code', 'name')
        import_id_fields = ('id',)
        skip_unchanged = True
        report_skipped = True

class ItemResource(resources.ModelResource):
    """
    Resource for importing/exporting Item model and its translations.
    
    This resource handles:
    1. Main Item model fields
    2. Foreign key relationships (construct_scale, likert_response, range_response)
    3. Translations through the before_import_row and after_save_instance methods
    
    The import process:
    1. Reads the CSV/Excel file
    2. For each row:
       a. Creates/updates the main Item record
       b. Stores translation data temporarily
       c. After saving the Item, creates/updates the translation
    """

    # Foreign key fields with their widgets
    # These fields handle the relationships between Item and other models
    # The ForeignKeyWidget converts the ID from the CSV into the actual model instance
    construct_scale = fields.Field(
        column_name='construct_scale',  # Name in the CSV/Excel file
        attribute='construct_scale',    # Field name in the Item model
        widget=ForeignKeyWidget(ConstructScale, 'id')  # Widget to handle the foreign key relationship
    )
    
    # Response type field with custom widget
    # This widget handles both choice values ('Likert') and display names ('Likert Scale')
    response_type = fields.Field(
        column_name='response_type',
        attribute='response_type',
        widget=ResponseTypeWidget()
    )
    
    likert_response = fields.Field(
        column_name='likert_response',
        attribute='likert_response',
        widget=ForeignKeyWidget(LikertScale, 'id')
    )
    range_response = fields.Field(
        column_name='range_response',
        attribute='range_response',
        widget=ForeignKeyWidget(RangeScale, 'id')
    )

    class Meta:
        """
        Meta configuration for the ItemResource.
        
        Attributes:
            model: The Django model to import/export
            fields: List of fields to include in import/export
            import_id_fields: Fields used to identify existing records
            skip_unchanged: Skip records that haven't changed
            report_skipped: Report which records were skipped
        """
        model = Item
        fields = (
            'id', 'construct_scale', 'abbreviated_item_id', 'item_number', 'response_type',
            'likert_response', 'range_response', 'is_required',
            'item_missing_value', 'item_better_score_direction',
            'item_threshold_score', 'item_minimum_clinical_important_difference',
            'item_normative_score_mean', 'item_normative_score_standard_deviation',
            'discrimination_parameter', 'difficulty_parameter',
            'pseudo_guessing_parameter'
        )
        import_id_fields = ('id',)  # Use UUID as the identifier for existing records
        skip_unchanged = True       # Skip records that haven't changed
        report_skipped = True       # Report which records were skipped

    def before_import_row(self, row, **kwargs):
        """
        Process each row before importing.
        
        This method is called for each row in the CSV/Excel file before the main
        Item record is created/updated. It extracts the translation data and stores
        it temporarily for use in after_save_instance.
        
        The method:
        1. Takes the row data from the CSV/Excel file
        2. Extracts the language_code and name values
        3. Stores them in self.translation_data for later use
        
        Args:
            row: Dictionary containing the row data from the CSV/Excel file
            **kwargs: Additional arguments passed by django-import-export
        
        The row should contain:
        - All Item model fields
        - language_code: The language code for the translation (e.g., 'en', 'es')
        - name: The translated name for the item
        """
        # Store translation data temporarily for use in after_save_instance
        # This data will be used after the main Item record is saved
        self.translation_data = {
            'language_code': row.get('language_code'),  # Get the language code from the row
            'name': row.get('name')                     # Get the translated name from the row
        }

    def after_save_instance(self, instance, row, **kwargs):
        """
        Process each row after the main Item record is saved.
        
        This method is called after the main Item record is created/updated.
        It handles saving the translation using django-parler's translation system.
        
        The method:
        1. Checks if we're not in dry_run mode (preview)
        2. Verifies we have both language_code and name
        3. Uses django-parler's set_current_language to set the language
        4. Sets the translated name
        5. Saves the translation to the item_translation table
        
        Args:
            instance: The Item instance that was just saved
            row: Dictionary containing the row data from the CSV/Excel file
            **kwargs: Additional arguments passed by django-import-export
                     (includes 'dry_run' for preview mode)
        
        Example CSV row:
        id,construct_scale,item_number,response_type,language_code,name
        550e8400-e29b-41d4-a716-446655440000,123e4567-e89b-12d3-a456-426614174000,1,Likert,en,"How are you feeling?"
        """
        # Only save translation if:
        # 1. Not in dry_run mode (preview)
        # 2. We have a language code
        # 3. We have a name to translate
        if not kwargs.get('dry_run') and self.translation_data.get('language_code') and self.translation_data.get('name'):
            # Set the current language for the translation
            # This tells django-parler which language we're setting
            instance.set_current_language(self.translation_data['language_code'])
            
            # Set the translated name
            # This will be saved in the item_translation table
            instance.name = self.translation_data['name']
            
            # Save the translation
            # This creates/updates the record in the item_translation table
            # with the language_code and name
            instance.save() 