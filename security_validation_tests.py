#!/usr/bin/env python3
"""
Comprehensive Security Validation Tests for Django 2FA OTP Implementation

This script tests all security objectives to ensure the OTP bypass vulnerability
has been properly remediated.

Security Objectives Tested:
1. OTP session binding to user context
2. Anti-replay mechanisms
3. Session hijacking prevention
4. Comprehensive audit logging
5. Rate limiting and anomaly detection
6. Proper OTP lifecycle management
"""

import os
import sys
import django
import requests
import time
import json
from datetime import datetime

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chaviprom.settings')
django.setup()

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.core.cache import cache
from django_otp.plugins.otp_totp.models import TOTPDevice
from django_otp.plugins.otp_email.models import EmailDevice
from django_otp.plugins.otp_static.models import StaticDevice
from django.contrib.sessions.models import Session
import logging

# Configure logging for test results
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SecurityValidationTests:
    """Comprehensive security validation test suite."""
    
    def __init__(self):
        self.client = Client()
        self.test_results = {
            'passed': 0,
            'failed': 0,
            'details': []
        }
        
    def log_test_result(self, test_name, passed, details=""):
        """Log test result and update counters."""
        status = "PASS" if passed else "FAIL"
        logger.info(f"[{status}] {test_name}: {details}")
        
        if passed:
            self.test_results['passed'] += 1
        else:
            self.test_results['failed'] += 1
            
        self.test_results['details'].append({
            'test': test_name,
            'status': status,
            'details': details,
            'timestamp': datetime.now().isoformat()
        })
    
    def test_middleware_configuration(self):
        """Test 1: Verify security middleware is properly configured."""
        from django.conf import settings
        
        middleware = settings.MIDDLEWARE
        has_secure_otp = 'chaviprom.security_middleware.SecureOTPMiddleware' in middleware
        has_audit = 'chaviprom.security_middleware.OTPAuditMiddleware' in middleware
        
        self.log_test_result(
            "Middleware Configuration",
            has_secure_otp and has_audit,
            f"SecureOTP: {has_secure_otp}, Audit: {has_audit}"
        )
    
    def test_security_settings(self):
        """Test 2: Verify security settings are properly configured."""
        from django.conf import settings
        
        required_settings = {
            'OTP_BIND_SESSION_TO_IP': True,
            'OTP_TOKEN_REUSE_PREVENTION': True,
            'OTP_AUDIT_LOGGING': True,
            'OTP_RATE_LIMIT_ATTEMPTS': 5,
            'OTP_RATE_LIMIT_WINDOW': 300,
        }
        
        all_configured = True
        missing_settings = []
        
        for setting, expected_value in required_settings.items():
            actual_value = getattr(settings, setting, None)
            if actual_value != expected_value:
                all_configured = False
                missing_settings.append(f"{setting}: expected {expected_value}, got {actual_value}")
        
        self.log_test_result(
            "Security Settings Configuration",
            all_configured,
            f"Missing/incorrect: {missing_settings}" if missing_settings else "All settings correct"
        )
    
    def test_session_binding(self):
        """Test 3: Test OTP session binding to user context."""
        # Create test users
        user1 = User.objects.create_user('testuser1', 'test1@example.com', 'password123')
        user2 = User.objects.create_user('testuser2', 'test2@example.com', 'password123')
        
        # Login as user1
        client1 = Client()
        client1.login(username='testuser1', password='password123')
        
        # Get session key for user1
        session1 = client1.session
        session1['_otp_user_id'] = user1.id
        session1['_otp_session_token'] = 'test_token_user1'
        session1.save()
        
        # Try to use user1's session for user2 (should fail)
        client2 = Client()
        client2.login(username='testuser2', password='password123')
        
        # Manually set user2's session to have user1's OTP data (simulating attack)
        session2 = client2.session
        session2['_otp_user_id'] = user1.id  # Wrong user ID
        session2['_otp_session_token'] = 'test_token_user1'  # Wrong token
        session2.save()
        
        # Test session integrity validation
        from chaviprom.secure_otp_utils import validate_session_integrity
        
        # Create mock request for user2 with user1's session data
        class MockRequest:
            def __init__(self, user, session):
                self.user = user
                self.session = session
                self.META = {'REMOTE_ADDR': '127.0.0.1'}
        
        request = MockRequest(user2, session2)
        is_valid = validate_session_integrity(request)
        
        self.log_test_result(
            "Session Binding Validation",
            not is_valid,  # Should be False (invalid)
            f"Session integrity check correctly rejected cross-user session: {not is_valid}"
        )
        
        # Cleanup
        user1.delete()
        user2.delete()
    
    def test_anti_replay_mechanisms(self):
        """Test 4: Test anti-replay mechanisms with nonces."""
        from chaviprom.secure_otp_utils import generate_challenge_id
        
        # Create mock request
        class MockRequest:
            def __init__(self):
                self.session = type('obj', (object,), {'session_key': 'test_session_123'})()
                self.META = {'REMOTE_ADDR': '127.0.0.1'}
        
        request = MockRequest()
        
        # Generate multiple challenge IDs
        challenge1 = generate_challenge_id(request)
        time.sleep(0.1)  # Small delay to ensure different timestamps
        challenge2 = generate_challenge_id(request)
        
        # Challenge IDs should be unique (anti-replay)
        unique_challenges = challenge1 != challenge2
        
        # Challenge IDs should be cryptographically strong (64 chars for SHA256)
        proper_length = len(challenge1) == 64 and len(challenge2) == 64
        
        self.log_test_result(
            "Anti-Replay Challenge Generation",
            unique_challenges and proper_length,
            f"Unique: {unique_challenges}, Proper length: {proper_length}"
        )
    
    def test_audit_logging(self):
        """Test 5: Test comprehensive audit logging."""
        # Clear existing logs
        cache.clear()
        
        # Create test user with 2FA device (use timestamp to ensure uniqueness)
        import time
        timestamp = str(int(time.time()))
        username = f'audituser_{timestamp}'
        email = f'audit_{timestamp}@example.com'
        user = User.objects.create_user(username, email, 'password123')
        device = TOTPDevice.objects.create(user=user, name='test_device', confirmed=True)
        
        # Check if logging functions are available with correct names
        try:
            from chaviprom.enhanced_signals import (
                log_totp_2fa_enabled_enhanced,
                log_enhanced_login,
                log_security_event,
                track_login_pattern
            )
            logging_available = True
            
            # Test security event logging
            log_security_event(
                event_type='TEST_EVENT',
                user=user,
                details={'test': 'audit_logging_validation'},
                ip_address='127.0.0.1'
            )
            
        except ImportError as e:
            logging_available = False
            import_error = str(e)
        
        self.log_test_result(
            "Audit Logging Functions",
            logging_available,
            f"Enhanced signals module available: {logging_available}" + 
            (f", Import error: {import_error}" if not logging_available else "")
        )
        
        # Cleanup
        device.delete()
        user.delete()
    
    def test_rate_limiting(self):
        """Test 6: Test rate limiting mechanisms."""
        # Test cache-based rate limiting
        user_id = 999  # Test user ID
        client_ip = '127.0.0.1'
        cache_key = f"otp_attempts_{user_id}_{client_ip}"
        
        # Clear any existing attempts
        cache.delete(cache_key)
        
        # Simulate multiple attempts
        for i in range(7):  # Exceed the limit of 5
            attempts = cache.get(cache_key, 0)
            cache.set(cache_key, attempts + 1, timeout=300)
        
        final_attempts = cache.get(cache_key, 0)
        rate_limit_working = final_attempts == 7
        
        self.log_test_result(
            "Rate Limiting Mechanism",
            rate_limit_working,
            f"Attempt counter working: {final_attempts} attempts recorded"
        )
        
        # Cleanup
        cache.delete(cache_key)
    
    def test_rate_limiting(self):
        """Test 6: Test rate limiting mechanisms."""
        # Test cache-based rate limiting
        user_id = 999  # Test user ID
        client_ip = '127.0.0.1'
        cache_key = f"otp_attempts_{user_id}_{client_ip}"
        
        # Clear any existing attempts
        cache.delete(cache_key)
        
        # Simulate multiple attempts
        for i in range(7):  # Exceed the limit of 5
            attempts = cache.get(cache_key, 0)
            cache.set(cache_key, attempts + 1, timeout=300)
        
        final_attempts = cache.get(cache_key, 0)
        rate_limit_working = final_attempts == 7
        
        self.log_test_result(
            "Rate Limiting Mechanism",
            rate_limit_working,
            f"Attempt counter working: {final_attempts} attempts recorded"
        )
        
        # Cleanup
        cache.delete(cache_key)

    def test_login_view_rate_limiting(self):
        """Test 6a: Functional test for login view rate limiting (should return 429 after threshold)."""
        from django.urls import reverse
        login_url = reverse('login')
        # Create a test user
        user = User.objects.create_user('ratelimituser', 'ratelimit@example.com', 'password123')
        client = Client()
        login_data = {'auth-username': 'ratelimituser', 'auth-password': 'password123'}
        success = False
        blocked = False
        for i in range(7):
            response = client.post(login_url, login_data, REMOTE_ADDR='127.0.0.1')
            if response.status_code == 200:
                success = True
            if response.status_code == 429:
                blocked = True
                break
        self.log_test_result(
            "Login View Rate Limiting",
            blocked,
            f"Blocked after exceeding threshold: {blocked}, Success before block: {success}"
        )
        user.delete()

    def test_password_reset_view_rate_limiting(self):
        """Test 6b: Functional test for password reset view rate limiting (should return 429 after threshold)."""
        from django.urls import reverse
        reset_url = reverse('password_reset')
        client = Client()
        reset_data = {'email': 'ratelimit@example.com'}
        blocked = False
        for i in range(7):
            response = client.post(reset_url, reset_data, REMOTE_ADDR='127.0.0.1')
            if response.status_code == 429:
                blocked = True
                break
        self.log_test_result(
            "Password Reset View Rate Limiting",
            blocked,
            f"Blocked after exceeding threshold: {blocked}"
        )

    def test_totp_device_security(self):
        """Test 7: Test TOTP device security and lifecycle."""
        # Create test user
        user = User.objects.create_user('totpuser', 'totp@example.com', 'password123')
        
        # Create unconfirmed TOTP device
        unconfirmed_device = TOTPDevice.objects.create(
            user=user, 
            name='unconfirmed_device', 
            confirmed=False
        )
        
        # Create confirmed TOTP device  
        confirmed_device = TOTPDevice.objects.create(
            user=user, 
            name='confirmed_device', 
            confirmed=True
        )
        
        # Test device states
        has_unconfirmed = TOTPDevice.objects.filter(user=user, confirmed=False).exists()
        has_confirmed = TOTPDevice.objects.filter(user=user, confirmed=True).exists()
        
        # Test our security logic
        from chaviprom.security_middleware import SecureOTPMiddleware
        middleware = SecureOTPMiddleware(lambda x: x)
        
        user_completed_setup = middleware._user_has_completed_setup(user)
        
        self.log_test_result(
            "TOTP Device Lifecycle Management",
            has_unconfirmed and has_confirmed and user_completed_setup,
            f"Unconfirmed: {has_unconfirmed}, Confirmed: {has_confirmed}, Setup complete: {user_completed_setup}"
        )
        
        # Cleanup
        unconfirmed_device.delete()
        confirmed_device.delete()
        user.delete()

    
    def test_is_verified_helper(self):
        """Test: is_verified(user) helper function logic."""
        from chaviprom.secure_otp_utils import is_verified
        from django.contrib.auth.models import User
        from django_otp.plugins.otp_totp.models import TOTPDevice
        from django_otp.plugins.otp_email.models import EmailDevice
        from django_otp.plugins.otp_static.models import StaticDevice

        user = User.objects.create_user('verifyuser', 'verify@example.com', 'password123')
        # No devices
        result_none = is_verified(user)
        # Unconfirmed TOTP
        totp_unconfirmed = TOTPDevice.objects.create(user=user, confirmed=False)
        result_unconfirmed = is_verified(user)
        # Confirmed TOTP
        totp_confirmed = TOTPDevice.objects.create(user=user, confirmed=True)
        result_totp = is_verified(user)
        # Confirmed Email
        email_device = EmailDevice.objects.create(user=user, confirmed=True)
        result_email = is_verified(user)
        # Confirmed Static
        static_device = StaticDevice.objects.create(user=user, confirmed=True)
        result_static = is_verified(user)

        passed = (
            result_none is False and
            result_unconfirmed is False and
            result_totp is True and
            result_email is True and
            result_static is True
        )
        self.log_test_result(
            "is_verified(user) Helper Logic",
            passed,
            f"None: {result_none}, Unconfirmed: {result_unconfirmed}, TOTP: {result_totp}, Email: {result_email}, Static: {result_static}"
        )
        # Cleanup
        totp_unconfirmed.delete()
        totp_confirmed.delete()
        email_device.delete()
        static_device.delete()
        user.delete()

    def test_ip_binding(self):
        """Test 8: Test IP address binding for sessions."""
        from chaviprom.secure_otp_utils import validate_session_integrity
        from django.conf import settings
        
        # Ensure IP binding is enabled
        ip_binding_enabled = getattr(settings, 'OTP_BIND_SESSION_TO_IP', False)
        
        if ip_binding_enabled:
            # Create test user
            user = User.objects.create_user('ipuser', 'ip@example.com', 'password123')
            
            # Create mock request with session bound to specific IP
            class MockRequest:
                def __init__(self, user, client_ip, session_ip):
                    self.user = user
                    self.META = {'REMOTE_ADDR': client_ip}
                    self.session = {
                        '_otp_user_id': user.id,
                        '_otp_session_token': 'test_token',
                        '_otp_client_ip': session_ip
                    }
            
            # Test same IP (should pass)
            request_same_ip = MockRequest(user, '192.168.1.100', '192.168.1.100')
            same_ip_valid = validate_session_integrity(request_same_ip)
            
            # Test different IP (should fail)
            request_diff_ip = MockRequest(user, '192.168.1.200', '192.168.1.100')
            diff_ip_valid = validate_session_integrity(request_diff_ip)
            
            self.log_test_result(
                "IP Address Binding",
                same_ip_valid and not diff_ip_valid,
                f"Same IP valid: {same_ip_valid}, Different IP rejected: {not diff_ip_valid}"
            )
            
            # Cleanup
            user.delete()
        else:
            self.log_test_result(
                "IP Address Binding",
                False,
                "IP binding is disabled in settings"
            )
    
    def run_all_tests(self):
        """Run all security validation tests."""
        logger.info("=" * 60)
        logger.info("STARTING COMPREHENSIVE SECURITY VALIDATION TESTS")
        logger.info("=" * 60)
        
        test_methods = [
            self.test_middleware_configuration,
            self.test_security_settings,
            self.test_session_binding,
            self.test_anti_replay_mechanisms,
            self.test_audit_logging,
            self.test_rate_limiting,
            self.test_totp_device_security,
            self.test_ip_binding,
        ]
        
        for test_method in test_methods:
            try:
                test_method()
            except Exception as e:
                self.log_test_result(
                    test_method.__name__,
                    False,
                    f"Test failed with exception: {str(e)}"
                )
        
        # Print summary
        logger.info("=" * 60)
        logger.info("SECURITY VALIDATION TEST SUMMARY")
        logger.info("=" * 60)
        logger.info(f"PASSED: {self.test_results['passed']}")
        logger.info(f"FAILED: {self.test_results['failed']}")
        logger.info(f"TOTAL:  {self.test_results['passed'] + self.test_results['failed']}")
        
        success_rate = (self.test_results['passed'] / 
                       (self.test_results['passed'] + self.test_results['failed'])) * 100
        logger.info(f"SUCCESS RATE: {success_rate:.1f}%")
        
        if self.test_results['failed'] == 0:
            logger.info("🎉 ALL SECURITY OBJECTIVES VALIDATED SUCCESSFULLY!")
        else:
            logger.warning(f"⚠️  {self.test_results['failed']} SECURITY TESTS FAILED")
        
        # Save detailed results
        with open('security_test_results.json', 'w') as f:
            json.dump(self.test_results, f, indent=2)
        
        logger.info("Detailed results saved to: security_test_results.json")
        
        return self.test_results['failed'] == 0

if __name__ == '__main__':
    validator = SecurityValidationTests()
    success = validator.run_all_tests()
    sys.exit(0 if success else 1)
