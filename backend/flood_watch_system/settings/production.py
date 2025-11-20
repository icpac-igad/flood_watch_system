"""
Production settings for flood_watch_system project.
"""
from .base import *

# Debug mode - MUST be False in production
DEBUG = False

# Security settings for production
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='').split(',')

# CORS settings for production
CORS_ALLOWED_ORIGINS = config('CORS_ALLOWED_ORIGINS', default='').split(',')
CORS_ALLOW_CREDENTIALS = True

# Security middleware and settings
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_SECONDS = config('SECURE_HSTS_SECONDS', default=31536000, cast=int)
SECURE_HSTS_INCLUDE_SUBDOMAINS = config('SECURE_HSTS_INCLUDE_SUBDOMAINS', default=True, cast=bool)
SECURE_HSTS_PRELOAD = config('SECURE_HSTS_PRELOAD', default=True, cast=bool)
SECURE_SSL_REDIRECT = config('SECURE_SSL_REDIRECT', default=True, cast=bool)
SESSION_COOKIE_SECURE = config('SESSION_COOKIE_SECURE', default=True, cast=bool)
CSRF_COOKIE_SECURE = config('CSRF_COOKIE_SECURE', default=True, cast=bool)
X_FRAME_OPTIONS = 'DENY'

# Database connection pooling for production
DATABASES['default'].update({
    'CONN_MAX_AGE': 60,
})

# Cache configuration for production (Redis)
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': config('REDIS_CACHE_URL', default='redis://redis:6379/1'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'COMPRESSOR': 'django_redis.compressors.zlib.ZlibCompressor',
        },
        'TIMEOUT': 300,
    }
}

# Session configuration
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'

# Email configuration for production
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = config('EMAIL_HOST', default='')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='noreply@floodwatch.org')

# Static files configuration for production
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.ManifestStaticFilesStorage'

# Production logging configuration
os.makedirs(os.path.join(BASE_DIR, 'logs'), exist_ok=True)

LOGGING['handlers']['file']['filename'] = os.path.join(BASE_DIR, 'logs', 'production.log')
LOGGING['handlers']['error_file'] = {
    'class': 'logging.handlers.RotatingFileHandler',
    'filename': os.path.join(BASE_DIR, 'logs', 'errors.log'),
    'maxBytes': 1024*1024*10,  # 10MB
    'backupCount': 10,
    'formatter': 'verbose',
    'level': 'ERROR',
}

LOGGING['handlers']['security_file'] = {
    'class': 'logging.handlers.RotatingFileHandler',
    'filename': os.path.join(BASE_DIR, 'logs', 'security.log'),
    'maxBytes': 1024*1024*5,  # 5MB
    'backupCount': 5,
    'formatter': 'verbose',
    'level': 'WARNING',
}

LOGGING['loggers']['django.security'] = {
    'handlers': ['security_file', 'console'],
    'level': 'WARNING',
    'propagate': False,
}

LOGGING['root']['handlers'].extend(['file', 'error_file'])

# Admin security
ADMINS = [
    ('FloodWatch Admin', config('ADMIN_EMAIL', default='admin@floodwatch.org')),
]
MANAGERS = ADMINS

# Performance optimizations
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB
