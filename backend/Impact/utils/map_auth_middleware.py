from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
import re


class MapAuthMiddleware(MiddlewareMixin):
    """Middleware to protect map-related API endpoints"""
    
    # Define patterns that require authentication
    MAP_PROTECTED_PATTERNS = [
        r'^/api/.*geojson.*',
        r'^/api/.*deterministic.*',
        r'^/api/.*flood-hazard.*',
        r'^/api/.*hazards.*',
        r'^/api/.*wms.*',
        r'^/api/.*layers.*',
        r'^/api/admin-boundaries.*',
        r'^/api/affectedPop.*',
        r'^/api/impactedGDP.*',
        r'^/api/affectedCrops.*',
        r'^/api/affectedRoads.*',
        r'^/api/displacedPop.*',
        r'^/api/affectedLivestock.*',
        r'^/api/affectedGrazing.*',
        r'^/api/admin1.*',
        r'^/api/admin2.*',
        r'^/api/lakes.*',
    ]
    
    # Public endpoints that don't require auth
    PUBLIC_PATTERNS = [
        r'^/api/auth/.*',
        r'^/admin/.*',
        r'^/static/.*',
        r'^/media/.*',
        r'^/health.*',
        r'^/$',
    ]
    
    def process_request(self, request):
        # AUTHENTICATION COMPLETELY DISABLED FOR TESTING
        # Just return None to allow all requests through
        print(f"MapAuthMiddleware: DISABLED - allowing request to {request.path}")
        return None

        # Original code commented out:
        # path = request.path
        #
        # # Check if this is a public endpoint
        # for pattern in self.PUBLIC_PATTERNS:
        #     if re.match(pattern, path):
        #         return None
        #
        # # Check if this is a protected map endpoint
        # is_protected = any(re.match(pattern, path) for pattern in self.MAP_PROTECTED_PATTERNS)
        #
        # if is_protected:
        #     # Try to authenticate using JWT
        #     jwt_auth = JWTAuthentication()
        #     try:
        #         auth_result = jwt_auth.authenticate(request)
        #         if auth_result is None:
        #             return JsonResponse({
        #                 'error': 'Authentication required',
        #                 'message': 'You need to login to access map features',
        #                 'code': 'AUTH_REQUIRED'
        #             }, status=401)
        #
        #         user, token = auth_result
        #         request.user = user
        #         request.auth = token
        #
        #     except (InvalidToken, TokenError):
        #         return JsonResponse({
        #             'error': 'Invalid token',
        #             'message': 'Your session has expired. Please login again.',
        #             'code': 'TOKEN_INVALID'
        #         }, status=401)
        #
        # return None