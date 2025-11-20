import base64
from django.conf import settings
from django.http import HttpResponse
from django.utils.deprecation import MiddlewareMixin

class BasicAuthMiddleware(MiddlewareMixin):
    """Basic HTTP authentication for staging environment"""
    
    def process_request(self, request):
        # Skip auth for health checks and admin
        if request.path.startswith('/admin/') or request.path == '/health/':
            return None
            
        # Only apply in staging
        if not getattr(settings, 'STAGING_AUTH_ENABLED', False):
            return None
        
        # Check for authorization header
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        
        if auth_header.startswith('Basic '):
            try:
                # Decode the credentials
                encoded_credentials = auth_header.split(' ')[1]
                decoded_credentials = base64.b64decode(encoded_credentials).decode('utf-8')
                username, password = decoded_credentials.split(':', 1)
                
                # Check credentials
                staging_user = getattr(settings, 'STAGING_AUTH_USER', 'floodwatch')
                staging_pass = getattr(settings, 'STAGING_AUTH_PASS', 'icpac2024')
                
                if username == staging_user and password == staging_pass:
                    return None
            except Exception:
                pass
        
        # Return 401 Unauthorized response
        response = HttpResponse('Unauthorized', status=401)
        response['WWW-Authenticate'] = 'Basic realm="FloodWatch Staging"'
        return response