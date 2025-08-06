"""
Enhanced Django signals for comprehensive Two-Factor Authentication security logging.

This module extends the existing signals.py with additional security monitoring
and audit logging for OTP-related events, including suspicious activity detection.
"""

from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.core.cache import cache
from django.utils import timezone
import logging
import hashlib
import json

# Import the device models for all 2FA types
from django_otp.plugins.otp_email.models import EmailDevice
from django_otp.plugins.otp_totp.models import TOTPDevice
from django_otp.plugins.otp_static.models import StaticDevice, StaticToken

logger = logging.getLogger('two_factor.security')
audit_logger = logging.getLogger('two_factor.audit')


def log_security_event(event_type, user, details=None, ip_address=None, user_agent=None):
    """
    Log security events with comprehensive details for audit purposes.
    
    Args:
        event_type (str): Type of security event
        user: User instance
        details (dict): Additional event details
        ip_address (str): Client IP address
        user_agent (str): Client user agent
    """
    event_data = {
        'event_type': event_type,
        'user_id': getattr(user, 'id', None),
        'username': getattr(user, 'username', 'Unknown'),
        'timestamp': timezone.now().isoformat(),
        'ip_address': ip_address,
        'user_agent_hash': hashlib.sha256(user_agent.encode()).hexdigest() if user_agent else None,
        'details': details or {}
    }
    
    audit_logger.info(f"SECURITY_EVENT: {json.dumps(event_data)}")


# Enhanced Email 2FA Device Signals
@receiver(post_save, sender=EmailDevice)
def log_email_2fa_enabled_enhanced(sender, instance, created, **kwargs):
    """Enhanced logging when a user enables email-based 2FA."""
    if created:
        user = getattr(instance, 'user', None)
        details = {
            'device_id': instance.id,
            'device_name': getattr(instance, 'name', 'Unnamed'),
            'email': instance.email if hasattr(instance, 'email') else 'Unknown',
            'confirmed': getattr(instance, 'confirmed', False)
        }
        
        log_security_event('EMAIL_2FA_ENABLED', user, details)
        logger.info(f"2FA ENABLED (email): Device {instance.id} for user {user.username if user else 'Unknown'}")


@receiver(post_delete, sender=EmailDevice)
def log_email_2fa_disabled_enhanced(sender, instance, **kwargs):
    """Enhanced logging when a user disables email-based 2FA."""
    user = getattr(instance, 'user', None)
    details = {
        'device_id': instance.id,
        'device_name': getattr(instance, 'name', 'Unnamed'),
        'email': instance.email if hasattr(instance, 'email') else 'Unknown'
    }
    
    log_security_event('EMAIL_2FA_DISABLED', user, details)
    logger.warning(f"2FA DISABLED (email): Device {instance.id} for user {user.username if user else 'Unknown'}")


# Enhanced TOTP Device Signals
@receiver(post_save, sender=TOTPDevice)
def log_totp_2fa_enabled_enhanced(sender, instance, created, **kwargs):
    """Enhanced logging when a user enables TOTP-based 2FA."""
    if created:
        user = getattr(instance, 'user', None)
        details = {
            'device_id': instance.id,
            'device_name': getattr(instance, 'name', 'Unnamed'),
            'confirmed': getattr(instance, 'confirmed', False),
            'drift': getattr(instance, 'drift', 0),
            'digits': getattr(instance, 'digits', 6),
            'tolerance': getattr(instance, 'tolerance', 1)
        }
        
        log_security_event('TOTP_2FA_ENABLED', user, details)
        logger.info(f"2FA ENABLED (TOTP): Device {instance.id} for user {user.username if user else 'Unknown'}")


@receiver(post_delete, sender=TOTPDevice)
def log_totp_2fa_disabled_enhanced(sender, instance, **kwargs):
    """Enhanced logging when a user disables TOTP-based 2FA."""
    user = getattr(instance, 'user', None)
    details = {
        'device_id': instance.id,
        'device_name': getattr(instance, 'name', 'Unnamed')
    }
    
    log_security_event('TOTP_2FA_DISABLED', user, details)
    logger.warning(f"2FA DISABLED (TOTP): Device {instance.id} for user {user.username if user else 'Unknown'}")


# Enhanced Static/Backup Token Device Signals
@receiver(post_save, sender=StaticDevice)
def log_static_2fa_enabled_enhanced(sender, instance, created, **kwargs):
    """Enhanced logging when a user enables static/backup token 2FA."""
    if created:
        user = getattr(instance, 'user', None)
        details = {
            'device_id': instance.id,
            'device_name': getattr(instance, 'name', 'Unnamed'),
            'confirmed': getattr(instance, 'confirmed', False)
        }
        
        log_security_event('STATIC_2FA_ENABLED', user, details)
        logger.info(f"2FA ENABLED (static/backup): Device {instance.id} for user {user.username if user else 'Unknown'}")


@receiver(post_delete, sender=StaticDevice)
def log_static_2fa_disabled_enhanced(sender, instance, **kwargs):
    """Enhanced logging when a user disables static/backup token 2FA."""
    user = getattr(instance, 'user', None)
    details = {
        'device_id': instance.id,
        'device_name': getattr(instance, 'name', 'Unnamed')
    }
    
    log_security_event('STATIC_2FA_DISABLED', user, details)
    logger.warning(f"2FA DISABLED (static/backup): Device {instance.id} for user {user.username if user else 'Unknown'}")


# Static Token Usage Tracking
@receiver(post_save, sender=StaticToken)
def log_static_token_usage(sender, instance, created, **kwargs):
    """Log when static tokens are used (they get deleted after use)."""
    if not created:  # Token was modified, likely used
        device = getattr(instance, 'device', None)
        user = getattr(device, 'user', None) if device else None
        
        details = {
            'device_id': device.id if device else None,
            'token_id': instance.id,
            'token_consumed': not hasattr(instance, 'token') or instance.token is None
        }
        
        log_security_event('STATIC_TOKEN_USED', user, details)
        logger.info(f"Static token used for user {user.username if user else 'Unknown'}")


@receiver(post_delete, sender=StaticToken)
def log_static_token_consumed(sender, instance, **kwargs):
    """Log when static tokens are consumed (deleted after use)."""
    device = getattr(instance, 'device', None)
    user = getattr(device, 'user', None) if device else None
    
    details = {
        'device_id': device.id if device else None,
        'token_id': instance.id
    }
    
    log_security_event('STATIC_TOKEN_CONSUMED', user, details)
    logger.info(f"Static token consumed for user {user.username if user else 'Unknown'}")


# Enhanced Login/Logout Signals
@receiver(user_logged_in)
def log_enhanced_login(sender, request, user, **kwargs):
    """Enhanced logging for user login events."""
    ip_address = get_client_ip(request)
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    
    # Check if this is a 2FA login
    is_2fa_login = hasattr(user, 'is_verified') and user.is_verified()
    
    details = {
        'login_method': '2FA' if is_2fa_login else 'PASSWORD_ONLY',
        'session_key': request.session.session_key,
        'is_2fa_verified': is_2fa_login
    }
    
    log_security_event('USER_LOGIN', user, details, ip_address, user_agent)
    
    # Track login patterns for anomaly detection
    track_login_pattern(user, ip_address, user_agent)
    
    if is_2fa_login:
        logger.info(f"Secure 2FA login successful for user {user.username} from {ip_address}")
    else:
        logger.warning(f"Password-only login for user {user.username} from {ip_address} - 2FA not verified")


@receiver(user_logged_out)
def log_enhanced_logout(sender, request, user, **kwargs):
    """Enhanced logging for user logout events."""
    if user:
        ip_address = get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        details = {
            'session_key': request.session.session_key if request.session else None
        }
        
        log_security_event('USER_LOGOUT', user, details, ip_address, user_agent)
        logger.info(f"User logout: {user.username} from {ip_address}")


@receiver(user_login_failed)
def log_enhanced_login_failure(sender, credentials, request, **kwargs):
    """Enhanced logging for failed login attempts."""
    ip_address = get_client_ip(request)
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    username = credentials.get('username', 'Unknown')
    
    details = {
        'attempted_username': username,
        'failure_reason': 'INVALID_CREDENTIALS'
    }
    
    # Create a dummy user object for logging
    class DummyUser:
        def __init__(self, username):
            self.username = username
            self.id = None
    
    dummy_user = DummyUser(username)
    log_security_event('LOGIN_FAILED', dummy_user, details, ip_address, user_agent)
    
    # Track failed login attempts for brute force detection
    track_failed_login(username, ip_address)
    
    logger.warning(f"Login failed for username '{username}' from {ip_address}")


def track_login_pattern(user, ip_address, user_agent):
    """Track login patterns for anomaly detection."""
    cache_key = f"login_pattern_{user.id}"
    pattern_data = cache.get(cache_key, {})
    
    # Track IP addresses
    ips = pattern_data.get('ips', set())
    ips.add(ip_address)
    
    # Track user agents
    user_agents = pattern_data.get('user_agents', set())
    user_agent_hash = hashlib.sha256(user_agent.encode()).hexdigest()
    user_agents.add(user_agent_hash)
    
    # Check for suspicious patterns
    if len(ips) > 5:  # More than 5 different IPs
        logger.warning(f"Multiple IP addresses detected for user {user.username}: {len(ips)} IPs")
    
    if len(user_agents) > 3:  # More than 3 different user agents
        logger.warning(f"Multiple user agents detected for user {user.username}: {len(user_agents)} agents")
    
    # Update pattern data
    pattern_data.update({
        'ips': ips,
        'user_agents': user_agents,
        'last_login': timezone.now().isoformat()
    })
    
    cache.set(cache_key, pattern_data, timeout=86400)  # 24 hours


def track_failed_login(username, ip_address):
    """Track failed login attempts for brute force detection."""
    # Track by username
    username_key = f"failed_login_user_{username}"
    username_attempts = cache.get(username_key, 0) + 1
    cache.set(username_key, username_attempts, timeout=3600)  # 1 hour
    
    # Track by IP
    ip_key = f"failed_login_ip_{ip_address}"
    ip_attempts = cache.get(ip_key, 0) + 1
    cache.set(ip_key, ip_attempts, timeout=3600)  # 1 hour
    
    # Alert on suspicious activity
    if username_attempts >= 5:
        logger.error(f"BRUTE_FORCE_ALERT: {username_attempts} failed login attempts for username '{username}'")
    
    if ip_attempts >= 10:
        logger.error(f"BRUTE_FORCE_ALERT: {ip_attempts} failed login attempts from IP {ip_address}")


def get_client_ip(request):
    """Get the client's IP address, handling proxies."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


# Device Confirmation Signals
@receiver(pre_save, sender=EmailDevice)
def log_email_device_confirmation(sender, instance, **kwargs):
    """Log when email devices are confirmed."""
    if instance.pk:  # Existing device being updated
        try:
            old_instance = EmailDevice.objects.get(pk=instance.pk)
            if not old_instance.confirmed and instance.confirmed:
                user = getattr(instance, 'user', None)
                details = {
                    'device_id': instance.id,
                    'device_name': getattr(instance, 'name', 'Unnamed'),
                    'email': instance.email if hasattr(instance, 'email') else 'Unknown'
                }
                log_security_event('EMAIL_2FA_CONFIRMED', user, details)
                logger.info(f"Email 2FA device confirmed for user {user.username if user else 'Unknown'}")
        except EmailDevice.DoesNotExist:
            pass


@receiver(pre_save, sender=TOTPDevice)
def log_totp_device_confirmation(sender, instance, **kwargs):
    """Log when TOTP devices are confirmed."""
    if instance.pk:  # Existing device being updated
        try:
            old_instance = TOTPDevice.objects.get(pk=instance.pk)
            if not old_instance.confirmed and instance.confirmed:
                user = getattr(instance, 'user', None)
                details = {
                    'device_id': instance.id,
                    'device_name': getattr(instance, 'name', 'Unnamed')
                }
                log_security_event('TOTP_2FA_CONFIRMED', user, details)
                logger.info(f"TOTP 2FA device confirmed for user {user.username if user else 'Unknown'}")
        except TOTPDevice.DoesNotExist:
            pass


@receiver(pre_save, sender=StaticDevice)
def log_static_device_confirmation(sender, instance, **kwargs):
    """Log when static devices are confirmed."""
    if instance.pk:  # Existing device being updated
        try:
            old_instance = StaticDevice.objects.get(pk=instance.pk)
            if not old_instance.confirmed and instance.confirmed:
                user = getattr(instance, 'user', None)
                details = {
                    'device_id': instance.id,
                    'device_name': getattr(instance, 'name', 'Unnamed')
                }
                log_security_event('STATIC_2FA_CONFIRMED', user, details)
                logger.info(f"Static 2FA device confirmed for user {user.username if user else 'Unknown'}")
        except StaticDevice.DoesNotExist:
            pass
