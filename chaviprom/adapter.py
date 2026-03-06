from allauth.account.adapter import DefaultAccountAdapter


class CustomAccountAdapter(DefaultAccountAdapter):
    """
    Custom adapter to handle IP detection for Django Allauth 65.14.2+
    
    In version 65.14.2, Allauth changed IP detection to distrust X-Forwarded-For
    by default for security. This adapter ensures proper IP detection in both
    development (localhost) and production (behind reverse proxy) environments.
    """
    
    def get_client_ip(self, request):
        """
        Override IP detection to handle both local development and production.
        
        For local development: Use REMOTE_ADDR directly
        For production with reverse proxy: Use configured trusted headers
        """
        # First, try the parent implementation which respects ALLAUTH_TRUSTED_* settings
        ip = super().get_client_ip(request)
        
        # If parent returns None (no trusted headers configured), fall back to REMOTE_ADDR
        # This is safe for local development and will work when no proxy is present
        if ip is None:
            ip = request.META.get('REMOTE_ADDR')
        
        return ip
