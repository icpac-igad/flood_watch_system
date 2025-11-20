"""
Local development settings for flood_watch_system project.
"""
from .base import *

# Debug mode
DEBUG = True

# Allowed hosts for local development - use environment variable
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1,0.0.0.0,10.10.1.13,197.254.1.10,floodwatch_nginx_proxy').split(',')

# CORS settings for local development - use environment variable
CORS_ALLOWED_ORIGINS = config('CORS_ALLOWED_ORIGINS', default='http://localhost:9006,http://127.0.0.1:9006').split(',')
CORS_ALLOW_ALL_ORIGINS = True  # Only for development
CORS_ALLOW_CREDENTIALS = True

# CSRF Trusted Origins - allow POST requests from frontend container
CSRF_TRUSTED_ORIGINS = [
    'http://localhost:8094',
    'http://127.0.0.1:8094',
    'http://localhost:8090',
    'http://127.0.0.1:8090',
    'http://localhost:9006',
    'http://127.0.0.1:9006',
]

# Force relative URLs instead of absolute URLs
USE_ABSOLUTE_URI = False
FORCE_SCRIPT_NAME = ''

# Database - use environment variables or defaults for local development
# No additional options needed for PostgreSQL in local development

# Static and media files for development
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]

# Email backend for development
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Cache configuration for development - using Redis for realistic testing
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': config('REDIS_URL', default='redis://redis:6379/1'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'SOCKET_CONNECT_TIMEOUT': 5,
            'SOCKET_TIMEOUT': 5,
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 50,
                'retry_on_timeout': True,
            },
            'IGNORE_EXCEPTIONS': True,  # Gracefully handle Redis failures in dev
        },
        'KEY_PREFIX': 'floodwatch_dev',
        'TIMEOUT': 300,  # Default timeout 5 minutes
    }
}

# Development-specific logging
LOGGING['handlers']['console']['level'] = 'DEBUG'
LOGGING['loggers']['django']['level'] = 'DEBUG'
LOGGING['loggers']['Impact']['level'] = 'DEBUG'

# Django Debug Toolbar (if installed)
try:
    import debug_toolbar
    INSTALLED_APPS.append('debug_toolbar')
    MIDDLEWARE.insert(0, 'debug_toolbar.middleware.DebugToolbarMiddleware')
    INTERNAL_IPS = ['127.0.0.1', 'localhost', '10.10.1.13', '197.254.1.10']
except ImportError:
    pass

# Disable some security features for local development
SECURE_SSL_REDIRECT = False
SECURE_HSTS_SECONDS = 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False

# Disable authentication for local development
REST_FRAMEWORK['DEFAULT_PERMISSION_CLASSES'] = [
    'rest_framework.permissions.AllowAny',
]

# Remove authentication middleware and add relative URL middleware
MIDDLEWARE = [m for m in MIDDLEWARE if 'MapAuthMiddleware' not in m]
# Exempt all /api/ endpoints from CSRF checks (development only)
MIDDLEWARE.insert(0, 'Impact.middleware_csrf_exempt.APICSRFExemptMiddleware')
MIDDLEWARE.append('Impact.middleware.RelativeURLMiddleware')