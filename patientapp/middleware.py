from django.utils import translation
from django.conf import settings
from django.shortcuts import redirect
from django.urls import resolve, reverse
from .models import Patient
import logging

logger = logging.getLogger(__name__)


class PatientLanguageMiddleware:
    """
    Middleware to automatically switch the website language based on the patient's preferred language.
    This middleware checks if the logged-in user is a patient and if they have a preferred language set.
    If so, it activates that language and redirects to the appropriate language URL if necessary.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Only process for authenticated users
        if request.user.is_authenticated:
            try:
                # Check if the user has an associated patient profile
                if hasattr(request.user, 'patient'):
                    patient = request.user.patient
                    preferred_language = patient.preferred_language
                    
                    # If patient has a preferred language set
                    if preferred_language:
                        current_language = translation.get_language()
                        
                        # If the current language doesn't match the preferred language
                        if current_language != preferred_language:
                            # Activate the preferred language
                            translation.activate(preferred_language)
                            request.LANGUAGE_CODE = preferred_language
                            
                            # Set the language in the session for persistence
                            request.session[translation.LANGUAGE_SESSION_KEY] = preferred_language
                            
                            logger.info(f"Language switched to {preferred_language} for patient {patient.name} (ID: {patient.id})")
                            
                            # Get the current URL path without the language prefix
                            current_path = request.path
                            resolved = resolve(request.path_info)
                            
                            # Check if we're already on a language-prefixed URL
                            # If the current path starts with a language code, we need to redirect
                            for lang_code, lang_name in settings.LANGUAGES:
                                if current_path.startswith(f'/{lang_code}/'):
                                    # Extract the path without language prefix
                                    path_without_lang = current_path[len(f'/{lang_code}/'):]
                                    # Build new URL with preferred language
                                    new_path = f'/{preferred_language}/{path_without_lang}'
                                    
                                    # Preserve query string
                                    query_string = request.META.get('QUERY_STRING', '')
                                    if query_string:
                                        new_path = f'{new_path}?{query_string}'
                                    
                                    logger.info(f"Redirecting from {current_path} to {new_path}")
                                    return redirect(new_path)
                            
                            # If no language prefix found, check if we're on a non-prefixed URL
                            # and redirect to the language-prefixed version
                            if not any(current_path.startswith(f'/{lang_code}/') for lang_code, _ in settings.LANGUAGES):
                                # This is a non-i18n URL (like /i18n/ or /media/)
                                # Don't redirect these
                                if not current_path.startswith('/i18n/') and not current_path.startswith('/media/') and not current_path.startswith('/static/'):
                                    new_path = f'/{preferred_language}{current_path}'
                                    query_string = request.META.get('QUERY_STRING', '')
                                    if query_string:
                                        new_path = f'{new_path}?{query_string}'
                                    logger.info(f"Redirecting from {current_path} to {new_path}")
                                    return redirect(new_path)
                        
            except Patient.DoesNotExist:
                # User is not a patient, continue normally
                pass
            except Exception as e:
                # Log any unexpected errors but don't break the request
                logger.error(f"Error in PatientLanguageMiddleware: {e}", exc_info=True)
        
        response = self.get_response(request)
        return response
