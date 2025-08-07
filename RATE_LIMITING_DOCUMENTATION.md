# User-Based Rate Limiting Implementation

## Overview

This document describes the implementation of user account-based rate limiting for authentication endpoints in the CHAVI-PROM system. The rate limiting is designed to work behind reverse proxies by focusing on user identifiers (username, email) rather than IP addresses.

## Features

- ✅ **User Account-Based**: Rate limits based on username/email, not IP addresses
- ✅ **Reverse Proxy Compatible**: Works correctly behind load balancers and reverse proxies
- ✅ **Multiple Endpoint Support**: Covers login, password reset, and OTP operations
- ✅ **Configurable Limits**: Easy to adjust rate limits per environment
- ✅ **Case-Insensitive**: Treats "User", "user", and "USER" as the same account
- ✅ **Graceful Degradation**: Falls back to session-based limiting when user info unavailable
- ✅ **Comprehensive Logging**: Tracks all rate limiting events for monitoring

## Rate Limiting Configuration

### Default Limits

- **Login Attempts**: 6 attempts per minute per username
- **Password Reset**: 6 attempts per minute per email address
- **OTP Operations**: 3 attempts per minute per user

### Environment-Specific Settings

The system automatically adjusts rate limits based on the environment:

#### Production Settings (DEBUG=False)
```python
AUTH_RATE_LIMIT_COUNT = 5        # Stricter limits
OTP_RATE_LIMIT_COUNT = 2         # Very strict for OTP
SUSPICIOUS_ACTIVITY_THRESHOLD = 5 # Lower threshold
```

#### Development Settings (DEBUG=True)
```python
AUTH_RATE_LIMIT_COUNT = 10       # More lenient
OTP_RATE_LIMIT_COUNT = 5         # Allows more testing
SUSPICIOUS_ACTIVITY_THRESHOLD = 20 # Higher threshold
```

## Implementation Details

### Key Generation Strategy

The rate limiting uses intelligent key generation based on available user identifiers:

#### Login Endpoint
1. **Primary**: `login:{username}` (from `auth-username` or `username` field)
2. **Fallback**: `login_session:{session_key}` (when no username provided)
3. **Last Resort**: `login_anon:{user_agent}` (truncated to 50 chars)

#### Password Reset Endpoint
1. **Primary**: `reset:{email}` (from `email` field)
2. **Fallback**: `reset_session:{session_key}` (when no email provided)
3. **Last Resort**: `reset_anon:{user_agent}` (truncated to 50 chars)

#### OTP Endpoints
1. **Primary**: `otp_user:{user_id}` (for authenticated users)
2. **Secondary**: `otp_setup:{username}` (during setup flow)
3. **Fallback**: `otp_session:{session_key}` (session-based)
4. **Last Resort**: `otp_anon:{user_agent}` (truncated to 50 chars)

### Rate Limited Views

The following views have been implemented with user-based rate limiting:

1. **`RateLimitedLoginView`**: Handles login attempts with username-based limiting
2. **`RateLimitedPasswordResetView`**: Handles password reset with email-based limiting
3. **`RateLimitedOTPSetupView`**: Handles OTP setup with user-based limiting
4. **`RateLimitedOTPView`**: Generic OTP view for API endpoints

## Files Modified/Created

### New Files
- `chaviprom/rate_limited_auth_views.py` - Main rate limiting implementation
- `chaviprom/rate_limiting_config.py` - Configuration settings
- `test_user_rate_limiting.py` - Test script for validation
- `RATE_LIMITING_DOCUMENTATION.md` - This documentation

### Modified Files
- `chaviprom/urls.py` - Updated to use new rate-limited views
- `chaviprom/settings.py` - Added rate limiting configuration
- `requirements.txt` - Already contained `django-ratelimit==4.1.0`

## Testing

### Automated Tests

Run the comprehensive test suite:

```bash
cd /home/santam/chavi-prom
python test_user_rate_limiting.py
```

The test script validates:
- ✅ Same user rate limiting works correctly
- ✅ Different users are not rate limited together
- ✅ Password reset email-based rate limiting
- ✅ Different emails are not rate limited together
- ✅ Case-insensitive username handling

### Manual Testing

#### Test Login Rate Limiting
1. Navigate to the login page
2. Enter the same username with wrong password 6 times
3. On the 7th attempt, you should see a rate limit error
4. Try with a different username - it should work normally

#### Test Password Reset Rate Limiting
1. Navigate to password reset page
2. Enter the same email address 6 times
3. On the 7th attempt, you should see a rate limit error
4. Try with a different email - it should work normally

## Monitoring and Logging

### Log Messages

The system logs the following events:

```python
# Successful events
logger.info(f"Successful login for user: {username}")
logger.info(f"Password reset requested for email: {email}")
logger.info(f"Successful OTP setup for user: {username}")

# Failed attempts
logger.warning(f"Failed login attempt for user: {username}")
logger.warning(f"Failed password reset attempt for email: {email}")
logger.warning(f"Failed OTP setup attempt for user: {username}")

# Rate limiting events
logger.warning(f"Rate limit exceeded for {endpoint_type} on {request.path}")
```

### Monitoring Recommendations

1. **Set up alerts** for excessive rate limiting events
2. **Monitor logs** for patterns of abuse
3. **Track success/failure ratios** for authentication endpoints
4. **Review rate limit settings** periodically based on usage patterns

## Security Benefits

### Protection Against Attacks

1. **Brute Force Protection**: Limits password guessing attempts per account
2. **Account Enumeration**: Prevents rapid testing of username/email existence
3. **OTP Abuse Prevention**: Limits OTP generation and validation attempts
4. **Resource Protection**: Prevents overwhelming authentication services

### Advantages Over IP-Based Limiting

1. **Reverse Proxy Compatible**: Works correctly behind load balancers
2. **Targeted Protection**: Directly protects user accounts, not just IPs
3. **Bypass Resistant**: Cannot be easily circumvented by changing IP addresses
4. **Accurate Limiting**: Focuses on the actual target of attacks (user accounts)

## Configuration Customization

### Adjusting Rate Limits

Edit `chaviprom/rate_limiting_config.py`:

```python
AUTH_RATE_LIMITING_SETTINGS = {
    'AUTH_RATE_LIMIT_COUNT': 6,  # Change this value
    'OTP_RATE_LIMIT_COUNT': 3,   # Change this value
    # ... other settings
}
```

### Adding New Endpoints

To add rate limiting to new endpoints:

1. Create a custom key function:
```python
def my_endpoint_key(group, request):
    identifier = request.POST.get('my_field')
    return f"my_endpoint:{identifier.lower()}" if identifier else f"my_endpoint_session:{request.session.session_key}"
```

2. Apply the decorator:
```python
@method_decorator(ratelimit(key=my_endpoint_key, rate='5/60s', method='POST', block=True), name='dispatch')
class MyRateLimitedView(View):
    def dispatch(self, request, *args, **kwargs):
        try:
            return super().dispatch(request, *args, **kwargs)
        except Ratelimited as e:
            return handle_rate_limit_exceeded(request, e)
```

## Troubleshooting

### Common Issues

#### Rate Limiting Not Working
- Check that `django-ratelimit` is installed: `pip show django-ratelimit`
- Verify Django cache is configured properly
- Check that the views are being used in URLs

#### Users Getting Rate Limited Too Quickly
- Review rate limit settings in `rate_limiting_config.py`
- Check if the environment detection is working correctly
- Verify the key generation functions are working as expected

#### Rate Limits Not Resetting
- Check Django cache configuration
- Verify cache backend is working: `python manage.py shell` → `from django.core.cache import cache; cache.set('test', 'value'); cache.get('test')`

### Debug Mode

To debug rate limiting issues, add this to your Django settings:

```python
LOGGING = {
    # ... existing config
    'loggers': {
        'chaviprom.rate_limiting': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
    }
}
```

## Production Deployment Checklist

- [ ] Rate limiting configuration reviewed and approved
- [ ] Test script executed successfully
- [ ] Logging configured for monitoring
- [ ] Cache backend configured and tested
- [ ] Rate limit settings appropriate for production load
- [ ] Monitoring alerts configured for rate limiting events
- [ ] Documentation shared with operations team

## Support

For issues or questions regarding the rate limiting implementation:

1. Check the logs for rate limiting events
2. Run the test script to validate functionality
3. Review this documentation for configuration options
4. Check Django cache configuration if limits aren't working


