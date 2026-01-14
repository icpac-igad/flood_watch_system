from .base import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "django-insecure-v%m=de1@h_(n$$m!=h_v$egike=!!plq3=53(e3xlnk6qsu=fv"

# SECURITY WARNING: define the correct hosts in production!
ALLOWED_HOSTS = ["*"]

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

CORS_ALLOW_ALL_ORIGINS = True

INSTALLED_APPS += ["wagtail.contrib.styleguide"]

# used in dev with Mac OS
GDAL_LIBRARY_PATH = env.str("GDAL_LIBRARY_PATH", None)
GEOS_LIBRARY_PATH = env.str("GEOS_LIBRARY_PATH", None)

# grab proxy headers
USE_X_FORWARDED_HOST = True
