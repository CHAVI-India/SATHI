"""
Django signals for logging Two-Factor Authentication events.

This module provides signal handlers to log when users enable or disable
2FA devices (email, TOTP, and static/backup tokens).
"""

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
import logging

# Import the device models for all 2FA types
from django_otp.plugins.otp_email.models import EmailDevice
from django_otp.plugins.otp_totp.models import TOTPDevice
from django_otp.plugins.otp_static.models import StaticDevice

logger = logging.getLogger('two_factor')


def log_device_event(action, instance):
    """
    Log a 2FA device event with consistent formatting.
    
    Args:
        action (str): The action being performed (e.g., "ENABLED", "DISABLED")
        instance: The device instance that triggered the event
    """
    user = getattr(instance, 'user', None)
    device_type = type(instance).__name__
    user_id = getattr(user, 'id', None)
    username = getattr(user, 'username', 'Unknown')
    
    logger.info(
        f"2FA {action}: {device_type} for user {username} (id={user_id})"
    )


# Email 2FA Device Signals
@receiver(post_save, sender=EmailDevice)
def log_email_2fa_enabled(sender, instance, created, **kwargs):
    """Log when a user enables email-based 2FA."""
    if created:
        log_device_event("ENABLED (email)", instance)


@receiver(post_delete, sender=EmailDevice)
def log_email_2fa_disabled(sender, instance, **kwargs):
    """Log when a user disables email-based 2FA."""
    log_device_event("DISABLED (email)", instance)


# TOTP (Time-based One-Time Password) Device Signals
@receiver(post_save, sender=TOTPDevice)
def log_totp_2fa_enabled(sender, instance, created, **kwargs):
    """Log when a user enables TOTP-based 2FA (e.g., Google Authenticator)."""
    if created:
        log_device_event("ENABLED (TOTP)", instance)


@receiver(post_delete, sender=TOTPDevice)
def log_totp_2fa_disabled(sender, instance, **kwargs):
    """Log when a user disables TOTP-based 2FA."""
    log_device_event("DISABLED (TOTP)", instance)


# Static/Backup Token Device Signals
@receiver(post_save, sender=StaticDevice)
def log_static_2fa_enabled(sender, instance, created, **kwargs):
    """Log when a user enables static/backup token 2FA."""
    if created:
        log_device_event("ENABLED (static/backup)", instance)


@receiver(post_delete, sender=StaticDevice)
def log_static_2fa_disabled(sender, instance, **kwargs):
    """Log when a user disables static/backup token 2FA."""
    log_device_event("DISABLED (static/backup)", instance) 