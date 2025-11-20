"""
Django settings initialization based on environment.
"""
import os
from decouple import config

# Determine which settings to use based on environment
ENVIRONMENT = config('ENVIRONMENT', default='local')

if ENVIRONMENT == 'production':
    from .production import *
elif ENVIRONMENT == 'staging':
    try:
        from .staging import *
    except ImportError:
        from .production import *
        DEBUG = True  # Enable debug for staging if no staging.py exists
else:
    from .local import *

# Override with environment-specific DEBUG setting if provided
DEBUG = config('DEBUG', default=DEBUG, cast=bool)