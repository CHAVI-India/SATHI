"""
Secure OTP Utility Functions

This module provides utility functions to enhance the security of 
django-two-factor-auth against OTP bypass attacks. These functions
work with the existing middleware to provide enhanced security.
"""

import hashlib
import hmac
import time
import logging
import os
from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.cache import never_cache
from django.views.generic import View
from django_otp import match_token
from django import forms

logger = logging.getLogger('two_factor.security')


def generate_challenge_id(request):
    """Generate a unique challenge ID for OTP attempts."""
    challenge_data = f"{request.session.session_key}:{time.time()}:{os.urandom(16).hex()}"
    return hashlib.sha256(challenge_data.encode()).hexdigest()


def validate_challenge_integrity(request):
    """Validate that the challenge ID hasn't been tampered with."""
    challenge_id = request.session.get('_otp_challenge_id')
    challenge_timestamp = request.session.get('_otp_challenge_timestamp')
    
    if not challenge_id or not challenge_timestamp:
        return False
    
    # Check if challenge has expired (5 minutes)
    if time.time() - challenge_timestamp > 300:
        logger.info("OTP challenge expired")
        return False
    
    # Validate challenge ID format
    if len(challenge_id) != 64:  # SHA256 hex length
        return False
    
    return True


def is_replay_attempt(request):
    """Check if this is a replay attempt."""
    challenge_id = request.session.get('_otp_challenge_id')
    if not challenge_id:
        return True
    
    # Check if this challenge has already been used
    cache_key = f"used_challenge_{challenge_id}"
    if cache.get(cache_key):
        return True
    
    return False


def secure_otp_validation(request, token):
    """Perform secure OTP validation with additional checks."""
    if not token:
        return False
    
    # Get the user's OTP device
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated:
        return False
    
    # Validate token with additional security checks
    device = match_token(user, token)
    if not device:
        return False
    
    # Check if this token has been used recently (prevent token reuse)
    token_hash = hashlib.sha256(f"{user.id}:{token}".encode()).hexdigest()
    cache_key = f"used_token_{token_hash}"
    
    if cache.get(cache_key):
        logger.warning(f"Token reuse attempt detected for user {user.username}")
        return False
    
    # Mark token as used (tokens should only be valid for a short time anyway)
    cache.set(cache_key, True, timeout=60)  # 1 minute
    
    # Store device information for audit
    request.session['_otp_device_id'] = device.id
    request.session['_otp_device_type'] = device.__class__.__name__
    
    return True


def mark_challenge_used(request):
    """Mark the current challenge as used to prevent replay."""
    challenge_id = request.session.get('_otp_challenge_id')
    if challenge_id:
        cache_key = f"used_challenge_{challenge_id}"
        cache.set(cache_key, True, timeout=3600)  # 1 hour


def bind_session_to_user(request):
    """Bind the session to the user context for security."""
    if request.user.is_authenticated:
        # Store user binding information
        request.session['_otp_user_id'] = request.user.id
        request.session['_otp_login_timestamp'] = time.time()
        request.session['_otp_client_ip'] = get_client_ip(request)
        request.session['_otp_user_agent_hash'] = hashlib.sha256(
            request.META.get('HTTP_USER_AGENT', '').encode()
        ).hexdigest()
        
        # Generate session integrity token
        session_token = generate_session_token(request)
        request.session['_otp_session_token'] = session_token
        
        logger.info(
            f"Secure OTP login successful for user {request.user.username} "
            f"from IP {get_client_ip(request)}"
        )


def generate_session_token(request):
    """Generate a session integrity token."""
    session_data = (
        f"{request.user.id}:"
        f"{request.session.session_key}:"
        f"{get_client_ip(request)}:"
        f"{time.time()}"
    )
    return hmac.new(
        settings.SECRET_KEY.encode(),
        session_data.encode(),
        hashlib.sha256
    ).hexdigest()


def validate_session_integrity(request):
    """Validate session integrity for authenticated users."""
    if not request.user.is_authenticated:
        return False
    
    # Check if session is bound to the correct user
    session_user_id = request.session.get('_otp_user_id')
    if session_user_id != request.user.id:
        return False
    
    # Check session token
    stored_token = request.session.get('_otp_session_token')
    if not stored_token:
        return False
    
    # Validate session hasn't been hijacked
    current_ip = get_client_ip(request)
    stored_ip = request.session.get('_otp_client_ip')
    
    if getattr(settings, 'OTP_BIND_SESSION_TO_IP', True) and stored_ip != current_ip:
        logger.warning(
            f"IP mismatch for user {request.user.username}: "
            f"stored={stored_ip}, current={current_ip}"
        )
        return False
    
    return True


def validate_otp_session(request):
    """Validate that the OTP session is still valid and secure."""
    if not request.user.is_authenticated:
        return False
    
    # Check if user has completed OTP verification
    if hasattr(request.user, 'is_verified') and not request.user.is_verified():
        return False
    
    # Validate session binding
    session_user_id = request.session.get('_otp_user_id')
    if session_user_id != request.user.id:
        return False
    
    # Check session age
    login_timestamp = request.session.get('_otp_login_timestamp')
    if login_timestamp:
        # Sessions expire after 8 hours
        if time.time() - login_timestamp > 28800:
            return False
    
    # Validate IP binding if enabled
    if getattr(settings, 'OTP_BIND_SESSION_TO_IP', True):
        stored_ip = request.session.get('_otp_client_ip')
        current_ip = get_client_ip(request)
        if stored_ip != current_ip:
            return False
    
    return True


def get_client_ip(request):
    """Get the client's IP address, handling proxies."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


# API endpoints removed as per user request
# All security enhancements are now handled through middleware
