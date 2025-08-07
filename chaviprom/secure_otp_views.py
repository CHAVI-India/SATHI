"""
Secure OTP Utility Functions and API Views

This module provides utility functions and API views to enhance
the security of django-two-factor-auth against OTP bypass attacks.

This version is designed to work with existing django-two-factor-auth
views through middleware rather than overriding them directly.
"""

import hashlib
import hmac
import time
import logging
import os
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import render, redirect
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.cache import never_cache
from django.views.generic import View
from django_otp import match_token
from django_otp.decorators import otp_required
from django import forms
from django_ratelimit.decorators import ratelimit

from two_factor.views import LoginView
from two_factor.views.core import SetupView as BaseSetupView
from django.contrib.auth import views as auth_views

# Rate-limited Login View
from django.utils.decorators import method_decorator

class RateLimitedLoginView(LoginView):
    template_name = 'two_factor/core/login.html'

    @method_decorator(ratelimit(key='ip', rate='5/m', block=True))
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

# Rate-limited Password Reset View
class RateLimitedPasswordResetView(auth_views.PasswordResetView):
    template_name = 'registration/password_reset_form.html'
    email_template_name = 'registration/password_reset_email.html'
    subject_template_name = 'registration/password_reset_subject.txt'

    @method_decorator(ratelimit(key='ip', rate='5/m', block=True))
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


logger = logging.getLogger('two_factor.security')


# Simplified secure OTP utility functions that work with existing views
# These functions are called by the middleware to enhance security

def generate_challenge_id(request):
    """Generate a unique challenge ID for OTP attempts."""
    import os
    challenge_data = f"{request.session.session_key}:{time.time()}:{os.urandom(16).hex()}"
    return hashlib.sha256(challenge_data.encode()).hexdigest()
    
    def form_valid(self, form):
        """Enhanced form validation with anti-replay protection."""
        # Validate challenge ID hasn't been tampered with
        if not self._validate_challenge_integrity(self.request):
            logger.warning(
                f"Challenge integrity violation during login for user "
                f"{getattr(self.request.user, 'username', 'unknown')}"
            )
            return HttpResponseForbidden("Security validation failed.")
        
        # Check for replay attacks
        if self._is_replay_attempt(self.request):
            logger.warning(
                f"Potential replay attack detected for user "
                f"{getattr(self.request.user, 'username', 'unknown')}"
            )
            return HttpResponseForbidden("Invalid verification attempt.")
        
        # Perform secure OTP validation
        if not self._secure_otp_validation(self.request, form):
            logger.warning(
                f"OTP validation failed for user "
                f"{getattr(self.request.user, 'username', 'unknown')}"
            )
            form.add_error(None, "Invalid token. Please try again.")
            return self.form_invalid(form)
        
        # Mark this challenge as used to prevent replay
        self._mark_challenge_used(self.request)
        
        # Bind session to user context
        self._bind_session_to_user(self.request)
        
        return super().form_valid(form)
    
    def _generate_challenge_id(self, request):
        """Generate a unique challenge ID for this OTP attempt."""
        challenge_data = f"{request.session.session_key}:{time.time()}:{random_hex()}"
        return hashlib.sha256(challenge_data.encode()).hexdigest()
    
    def _validate_challenge_integrity(self, request):
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
    
    def _is_replay_attempt(self, request):
        """Check if this is a replay attempt."""
        challenge_id = request.session.get('_otp_challenge_id')
        if not challenge_id:
            return True
        
        # Check if this challenge has already been used
        cache_key = f"used_challenge_{challenge_id}"
        if cache.get(cache_key):
            return True
        
        return False
    
    def _secure_otp_validation(self, request, form):
        """Perform secure OTP validation with additional checks."""
        token = form.cleaned_data.get('otp_token')
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
    
    def _mark_challenge_used(self, request):
        """Mark the current challenge as used to prevent replay."""
        challenge_id = request.session.get('_otp_challenge_id')
        if challenge_id:
            cache_key = f"used_challenge_{challenge_id}"
            cache.set(cache_key, True, timeout=3600)  # 1 hour
    
    def _bind_session_to_user(self, request):
        """Bind the session to the user context for security."""
        if request.user.is_authenticated:
            # Store user binding information
            request.session['_otp_user_id'] = request.user.id
            request.session['_otp_login_timestamp'] = time.time()
            request.session['_otp_client_ip'] = self._get_client_ip(request)
            request.session['_otp_user_agent_hash'] = hashlib.sha256(
                request.META.get('HTTP_USER_AGENT', '').encode()
            ).hexdigest()
            
            # Generate session integrity token
            session_token = self._generate_session_token(request)
            request.session['_otp_session_token'] = session_token
            
            logger.info(
                f"Secure OTP login successful for user {request.user.username} "
                f"from IP {self._get_client_ip(request)}"
            )
    
    def _generate_session_token(self, request):
        """Generate a session integrity token."""
        session_data = (
            f"{request.user.id}:"
            f"{request.session.session_key}:"
            f"{self._get_client_ip(request)}:"
            f"{time.time()}"
        )
        return hmac.new(
            settings.SECRET_KEY.encode(),
            session_data.encode(),
            hashlib.sha256
        ).hexdigest()
    
    def _get_client_ip(self, request):
        """Get the client's IP address."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class SecureSetupView(BaseSetupView):
    """
    Enhanced setup view for 2FA device configuration with security measures.
    """
    
    def dispatch(self, request, *args, **kwargs):
        """Enhanced dispatch with security validation."""
        # Ensure user is properly authenticated
        if not request.user.is_authenticated:
            return redirect('two_factor:login')
        
        # Validate session integrity
        if not self._validate_session_integrity(request):
            logger.warning(
                f"Session integrity violation during 2FA setup for user "
                f"{request.user.username}"
            )
            return HttpResponseForbidden("Session validation failed.")
        
        return super().dispatch(request, *args, **kwargs)
    
    def _validate_session_integrity(self, request):
        """Validate session integrity for 2FA setup."""
        # Check if session is bound to the correct user
        session_user_id = request.session.get('_otp_user_id')
        if session_user_id != request.user.id:
            return False
        
        # Check session token
        stored_token = request.session.get('_otp_session_token')
        if not stored_token:
            return False
        
        # Validate session hasn't been hijacked
        current_ip = self._get_client_ip(request)
        stored_ip = request.session.get('_otp_client_ip')
        
        if getattr(settings, 'OTP_BIND_SESSION_TO_IP', True) and stored_ip != current_ip:
            logger.warning(
                f"IP mismatch during 2FA setup for user {request.user.username}: "
                f"stored={stored_ip}, current={current_ip}"
            )
            return False
        
        return True
    
    def _get_client_ip(self, request):
        """Get the client's IP address."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


@login_required
@otp_required
def secure_profile_view(request):
    """
    Secure profile view that validates OTP session integrity.
    """
    # Additional security check for OTP-protected views
    if not _validate_otp_session(request):
        logger.warning(
            f"OTP session validation failed for user {request.user.username}"
        )
        return redirect('two_factor:login')
    
    return render(request, 'two_factor/profile/profile.html')


def _validate_otp_session(request):
    """Validate that the OTP session is still valid and secure."""
    if not request.user.is_authenticated:
        return False
    
    # Check if user has completed OTP verification
    if not request.user.is_verified():
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
        current_ip = _get_client_ip(request)
        if stored_ip != current_ip:
            return False
    
    return True


def _get_client_ip(request):
    """Get the client's IP address."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip
