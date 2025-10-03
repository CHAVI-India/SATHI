from django.utils import translation
from django.conf import settings
from django.shortcuts import redirect
from .models import Patient
import logging

logger = logging.getLogger(__name__)

# Django's session key for language preference
LANGUAGE_SESSION_KEY = '_language'


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
                        session_language = request.session.get(LANGUAGE_SESSION_KEY)
                        
                        # Check if user is accessing a language-prefixed URL
                        # If they are, it means they're manually choosing that language
                        current_path = request.path
                        user_chosen_language = None
                        for lang_code, lang_name in settings.LANGUAGES:
                            if current_path.startswith(f'/{lang_code}/'):
                                user_chosen_language = lang_code
                                break
                        
                        # If user is accessing a language-prefixed URL that differs from their preferred language,
                        # update the session to remember their choice
                        if user_chosen_language and user_chosen_language != preferred_language:
                            request.session[LANGUAGE_SESSION_KEY] = user_chosen_language
                            logger.info(f"Patient {patient.name} manually chose language {user_chosen_language}")
                        
                        # Only auto-switch if:
                        # 1. Current language doesn't match preferred language
                        # 2. AND user hasn't manually chosen a different language (not in URL and not in session)
                        should_auto_switch = (
                            current_language != preferred_language and
                            user_chosen_language is None and
                            (session_language is None or session_language == preferred_language)
                        )
                        
                        if should_auto_switch:
                            # Activate the preferred language
                            translation.activate(preferred_language)
                            request.LANGUAGE_CODE = preferred_language
                            
                            # Set the language in the session for persistence
                            request.session[LANGUAGE_SESSION_KEY] = preferred_language
                            
                            logger.info(f"Language auto-switched to {preferred_language} for patient {patient.name} (ID: {patient.id})")
                            
                            # Skip redirects for special paths that shouldn't be language-prefixed
                            skip_paths = ['/i18n/', '/media/', '/static/', '/__debug__/', '/admin/']
                            if any(current_path.startswith(path) for path in skip_paths):
                                # Don't redirect these special URLs
                                pass
                            # Skip favicon and other common non-page requests
                            elif current_path.endswith('.ico') or current_path.endswith('.txt') or current_path.endswith('.xml'):
                                # Don't redirect static file requests
                                pass
                            else:
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
