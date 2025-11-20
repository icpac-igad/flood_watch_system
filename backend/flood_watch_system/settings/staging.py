# Staging settings - inherits from production but disables HTTPS redirect
from .production import *

# Disable HTTPS redirect for staging testing
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# Allow both HTTP and HTTPS
SECURE_PROXY_SSL_HEADER = None

# Debug info for staging
DEBUG = config('DEBUG', default=False, cast=bool)

# Staging-specific allowed hosts
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1,197.254.1.10').split(',')

# Use localhost Redis for staging
CACHES['default']['LOCATION'] = config('REDIS_CACHE_URL', default='redis://redis:6379/1')

# COMPREHENSIVE CORS settings for staging - SOLVE CORS ISSUES ONCE AND FOR ALL
CORS_ALLOW_ALL_ORIGINS = True  # Allow all origins for staging
CORS_ALLOW_CREDENTIALS = True

# Backup specific origins if needed
CORS_ALLOWED_ORIGINS = [
    'http://localhost:8094',
    'http://127.0.0.1:8094',
    'http://localhost:9006',
    'http://127.0.0.1:9006',
    'http://197.254.1.10:9006',
    'http://197.254.1.10:8094',
    'http://localhost:3000',
    'http://localhost:5173',
    'http://localhost:8080',
    'http://localhost:80',
    'http://0.0.0.0:8094',
]

# Allow all common headers
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
    'cache-control',
    'x-forwarded-for',
    'x-forwarded-proto',
    'x-real-ip',
    'referer',
    'sec-fetch-dest',
    'sec-fetch-mode',
    'sec-fetch-site',
]

# Allow all HTTP methods
CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'HEAD',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]

# Additional CORS settings
CORS_PREFLIGHT_MAX_AGE = 86400
CORS_EXPOSE_HEADERS = []
CORS_ALLOWED_ORIGIN_REGEXES = []