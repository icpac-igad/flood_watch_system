from .base import *
import os
import logging.config

WAGTAIL_ENABLE_UPDATE_CHECK = False

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env("SECRET_KEY")

# SECURITY WARNING: define the correct hosts in production!
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=[])

DEBUG = env("DEBUG", False)

CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", cast=None, default=[])
SECURE_CROSS_ORIGIN_OPENER_POLICY = env.str("SECURE_CROSS_ORIGIN_OPENER_POLICY", None)

CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", cast=None, default=[])

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.memcached.PyMemcacheCache",
        "LOCATION": env("MEMCACHED_URI", default=""),
        "KEY_PREFIX": "cms_cache",
        "TIMEOUT": 14400,  # 4 hours (in seconds)
    },
}
# see https://docs.djangoproject.com/en/4.2/ref/middleware/#http-strict-transport-security
SECURE_HSTS_SECONDS = 7776000  # 3 months
SECURE_HSTS_PRELOAD = True
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "True").lower() != "false"
CSRF_COOKIE_SECURE = os.environ.get("CSRF_COOKIE_SECURE", "True").lower() != "false"
SECURE_SSL_REDIRECT = False
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"

# Disable Django's default logging setup
LOGGING_CONFIG = None

LOGLEVEL = os.environ.get("LOGLEVEL", "info").upper()

logging.config.dictConfig(
    {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(asctime)s %(name)-12s %(levelname)-8s %(message)s",
            }
        },
        "handlers": {
            "stdout": {
                "class": "logging.StreamHandler",
                "level": "INFO",
                "formatter": "default",
                "stream": "ext://sys.stdout",
            },
            "stderr": {
                "class": "logging.StreamHandler",
                "level": "ERROR",
                "formatter": "default",
                "stream": "ext://sys.stderr",
            },
            "file": {
                "level": "INFO",
                "class": "logging.FileHandler",
                "filename": os.environ.get("CMS_LOG_FILE", "/tmp/cms-web-app.log"),
                "formatter": "default",
            },
        },
        "loggers": {
            # Default logger
            "": {
                "level": "WARNING",
                "handlers": ["stdout", "stderr", "file"],
            },
            # application logger
            "app": {
                "level": LOGLEVEL,
                "handlers": ["stdout", "stderr", "file"],
                "propagate": False,
            },
        },
    }
)
