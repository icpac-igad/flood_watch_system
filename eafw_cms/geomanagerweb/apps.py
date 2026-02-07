from django.apps import AppConfig


class GeomanagerwebConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "geomanagerweb"

    def ready(self):
        # Import and register API endpoints after apps are loaded
        from .api import register_api_endpoints
        register_api_endpoints()
