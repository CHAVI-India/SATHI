from django.conf import settings
from django.utils import translation


def language_fonts(request):
    """
    Context processor that provides language-specific font information
    to all templates.
    """
    current_language = translation.get_language()
    
    # Get the font for the current language, fallback to default
    current_font = settings.LANGUAGE_FONTS.get(
        current_language, 
        settings.DEFAULT_FONT
    )
    
    # Create Google Fonts URL
    # Replace + with spaces for display purposes
    font_display_name = current_font.replace('+', ' ')
    
    # Create the Google Fonts URL - keep + for URL encoding
    google_fonts_url = f"https://fonts.googleapis.com/css2?family={current_font}:wght@300;400;500;600;700&display=swap"
    
    return {
        'CURRENT_FONT': current_font,
        'CURRENT_FONT_DISPLAY': font_display_name,
        'GOOGLE_FONTS_URL': google_fonts_url,
        'LANGUAGE_FONTS': settings.LANGUAGE_FONTS,
    } 