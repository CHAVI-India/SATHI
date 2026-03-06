from allauth.account.adapter import DefaultAccountAdapter
import logging

logger = logging.getLogger(__name__)


class CustomAccountAdapter(DefaultAccountAdapter):
    """
    Custom adapter to handle IP detection for Django Allauth 65.14.2+
    
    In version 65.14.2, Allauth changed IP detection to distrust X-Forwarded-For
    by default for security. This adapter ensures proper IP detection in both
    development (localhost) and production (behind reverse proxy) environments.
    
    Production: Uses ALLAUTH_TRUSTED_CLIENT_IP_HEADER and ALLAUTH_TRUSTED_PROXY_COUNT
    Development: Falls back to REMOTE_ADDR when no proxy is configured
    """
    
    def get_client_ip(self, request):
        """
        Override IP detection to handle both local development and production.
        
        For production with reverse proxy: Parent implementation uses ALLAUTH_TRUSTED_* settings
        For local development: Falls back to REMOTE_ADDR when parent returns None
        """
        # Log all available IP-related headers for debugging
        logger.info(f"IP Detection Debug - REMOTE_ADDR: {request.META.get('REMOTE_ADDR')}")
        logger.info(f"IP Detection Debug - HTTP_X_REAL_IP: {request.META.get('HTTP_X_REAL_IP')}")
        logger.info(f"IP Detection Debug - HTTP_X_FORWARDED_FOR: {request.META.get('HTTP_X_FORWARDED_FOR')}")
        
        # Try the parent implementation which respects ALLAUTH_TRUSTED_* settings
        ip = super().get_client_ip(request)
        logger.info(f"IP Detection Debug - Parent returned: {ip}")
        
        # Only use fallback if parent returns None (no trusted proxy configured)
        # This happens in local development without a reverse proxy
        if ip is None:
            ip = request.META.get('REMOTE_ADDR')
            logger.info(f"IP Detection Debug - Using fallback REMOTE_ADDR: {ip}")
        
        logger.info(f"IP Detection Debug - Final IP: {ip}")
        return ip
