"""
Middleware to exempt API endpoints from CSRF validation.
For development/testing only - in production, use proper CSRF tokens.
"""
from django.utils.deprecation import MiddlewareMixin


class APICSRFExemptMiddleware(MiddlewareMixin):
    """
    Exempts all /api/ endpoints from CSRF validation.
    This is acceptable for REST APIs that use other security mechanisms (CORS, JWT, etc.)
    """
    def process_request(self, request):
        if request.path.startswith('/api/'):
            setattr(request, '_dont_enforce_csrf_checks', True)
        return None
