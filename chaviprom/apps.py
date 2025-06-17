"""
Django app configuration for the main chaviprom project.
"""

from django.apps import AppConfig


class ChavipromConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'chaviprom'

    def ready(self):
        """
        Import signals when Django is ready.
        This ensures the signals are registered after all models are loaded.
        """
        try:
            from . import signals
        except ImportError:
            # Signals module might not exist yet, which is fine
            pass 