#!/usr/bin/env python
"""
User-Based Rate Limiting Test Script

This script tests the user account-based rate limiting functionality
for authentication endpoints.
"""

import os
import sys
import time
from datetime import datetime

# Add the project directory to Python path
sys.path.insert(0, '/home/santam/chavi-prom')

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chaviprom.settings')
import django
django.setup()

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.core.cache import cache
from django.conf import settings

class UserRateLimitingTests:
    """Test suite for user-based rate limiting functionality."""
    
    def __init__(self):
        self.client = Client()
        self.test_results = []
        
        # Test configuration
        self.rate_limit_count = getattr(settings, 'AUTH_RATE_LIMIT_COUNT', 6)
        self.otp_rate_limit_count = getattr(settings, 'OTP_RATE_LIMIT_COUNT', 3)
        
        print(f"Testing user-based rate limiting:")
        print(f"- Auth attempts: {self.rate_limit_count} per minute")
        print(f"- OTP attempts: {self.otp_rate_limit_count} per minute")
        print("-" * 50)
    
    def log_test_result(self, test_name, passed, message=""):
        """Log test results."""
        status = "✅ PASS" if passed else "❌ FAIL"
        timestamp = datetime.now().strftime("%H:%M:%S")
        result = {
            'test': test_name,
            'status': status,
            'message': message,
            'timestamp': timestamp
        }
        self.test_results.append(result)
        print(f"[{timestamp}] {test_name}: {status}")
        if message:
            print(f"    └─ {message}")
    
    def clear_cache(self):
        """Clear rate limiting cache."""
        cache.clear()
        print("🧹 Cache cleared")
    
    def test_login_rate_limiting_same_user(self):
        """Test rate limiting on login for the same username."""
        print("\n=== Testing Login Rate Limiting (Same User) ===")
        self.clear_cache()
        
        login_url = reverse('login')
        login_data = {
            'auth-username': 'testuser123',
            'auth-password': 'wrongpassword'
        }
        
        # Test requests within limit
        success_count = 0
        for i in range(self.rate_limit_count):
            response = self.client.post(login_url, login_data)
            if response.status_code != 429:
                success_count += 1
            time.sleep(0.1)  # Small delay
        
        self.log_test_result(
            "Login Within Rate Limit",
            success_count == self.rate_limit_count,
            f"Expected {self.rate_limit_count} successful requests, got {success_count}"
        )
        
        # Test rate limit exceeded
        response = self.client.post(login_url, login_data)
        rate_limited = response.status_code == 429
        
        self.log_test_result(
            "Login Rate Limit Exceeded",
            rate_limited,
            f"Expected 429 status code, got {response.status_code}"
        )
        
        return rate_limited
    
    def test_login_different_users_not_rate_limited(self):
        """Test that different usernames are not rate limited together."""
        print("\n=== Testing Different Users Not Rate Limited ===")
        self.clear_cache()
        
        login_url = reverse('login')
        
        # Exhaust rate limit for first user
        login_data_user1 = {
            'auth-username': 'user1_test',
            'auth-password': 'wrongpassword'
        }
        
        for i in range(self.rate_limit_count + 1):
            self.client.post(login_url, login_data_user1)
            time.sleep(0.05)
        
        # Test that different user is not rate limited
        login_data_user2 = {
            'auth-username': 'user2_test',
            'auth-password': 'wrongpassword'
        }
        
        response = self.client.post(login_url, login_data_user2)
        not_rate_limited = response.status_code != 429
        
        self.log_test_result(
            "Different Users Not Rate Limited",
            not_rate_limited,
            f"Different user should not be rate limited, got status {response.status_code}"
        )
        
        return not_rate_limited
    
    def test_password_reset_rate_limiting(self):
        """Test rate limiting on password reset endpoint."""
        print("\n=== Testing Password Reset Rate Limiting ===")
        self.clear_cache()
        
        reset_url = reverse('password_reset')
        reset_data = {
            'email': 'test@example.com'
        }
        
        # Test requests within limit
        success_count = 0
        for i in range(self.rate_limit_count):
            response = self.client.post(reset_url, reset_data)
            if response.status_code != 429:
                success_count += 1
            time.sleep(0.1)
        
        self.log_test_result(
            "Password Reset Within Limit",
            success_count == self.rate_limit_count,
            f"Expected {self.rate_limit_count} successful requests, got {success_count}"
        )
        
        # Test rate limit exceeded
        response = self.client.post(reset_url, reset_data)
        rate_limited = response.status_code == 429
        
        self.log_test_result(
            "Password Reset Rate Limited",
            rate_limited,
            f"Expected 429 status code, got {response.status_code}"
        )
        
        return rate_limited
    
    def test_password_reset_different_emails(self):
        """Test that different emails are not rate limited together."""
        print("\n=== Testing Different Emails Not Rate Limited ===")
        self.clear_cache()
        
        reset_url = reverse('password_reset')
        
        # Exhaust rate limit for first email
        reset_data_email1 = {'email': 'email1@example.com'}
        for i in range(self.rate_limit_count + 1):
            self.client.post(reset_url, reset_data_email1)
            time.sleep(0.05)
        
        # Test that different email is not rate limited
        reset_data_email2 = {'email': 'email2@example.com'}
        response = self.client.post(reset_url, reset_data_email2)
        not_rate_limited = response.status_code != 429
        
        self.log_test_result(
            "Different Emails Not Rate Limited",
            not_rate_limited,
            f"Different email should not be rate limited, got status {response.status_code}"
        )
        
        return not_rate_limited
    
    def test_case_insensitive_rate_limiting(self):
        """Test that rate limiting is case-insensitive."""
        print("\n=== Testing Case-Insensitive Rate Limiting ===")
        self.clear_cache()
        
        login_url = reverse('login')
        
        # Make requests with different cases of the same username
        usernames = ['TestUser', 'testuser', 'TESTUSER', 'TestUSER']
        
        for i, username in enumerate(usernames):
            login_data = {
                'auth-username': username,
                'auth-password': 'wrongpassword'
            }
            response = self.client.post(login_url, login_data)
            time.sleep(0.1)
        
        # Make additional requests to exceed limit
        for i in range(self.rate_limit_count - len(usernames) + 1):
            login_data = {
                'auth-username': 'testuser',
                'auth-password': 'wrongpassword'
            }
            response = self.client.post(login_url, login_data)
            time.sleep(0.05)
        
        # Final request should be rate limited
        final_response = self.client.post(login_url, {
            'auth-username': 'TESTUSER',
            'auth-password': 'wrongpassword'
        })
        
        rate_limited = final_response.status_code == 429
        
        self.log_test_result(
            "Case-Insensitive Rate Limiting",
            rate_limited,
            f"Expected 429 for case variations, got {final_response.status_code}"
        )
        
        return rate_limited
    
    def run_all_tests(self):
        """Run all rate limiting tests."""
        print("🚀 Starting User-Based Rate Limiting Tests")
        print("=" * 60)
        
        tests = [
            self.test_login_rate_limiting_same_user,
            self.test_login_different_users_not_rate_limited,
            self.test_password_reset_rate_limiting,
            self.test_password_reset_different_emails,
            self.test_case_insensitive_rate_limiting,
        ]
        
        passed_tests = 0
        total_tests = len(tests)
        
        for test in tests:
            try:
                result = test()
                if result:
                    passed_tests += 1
            except Exception as e:
                self.log_test_result(
                    test.__name__,
                    False,
                    f"Test failed with exception: {str(e)}"
                )
        
        # Print summary
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {total_tests - passed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if passed_tests == total_tests:
            print("🎉 All tests passed! User-based rate limiting is working correctly.")
        else:
            print("⚠️  Some tests failed. Please review the implementation.")
        
        return passed_tests == total_tests


if __name__ == '__main__':
    tester = UserRateLimitingTests()
    success = tester.run_all_tests()
    
    if success:
        print("\n✅ Rate limiting implementation is ready for production!")
    else:
        print("\n❌ Rate limiting needs attention before deployment.")
    
    sys.exit(0 if success else 1)
