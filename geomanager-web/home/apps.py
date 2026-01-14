from django.apps import AppConfig


class HomeConfig(AppConfig):
    name = "home"

    def ready(self):
        import home.signals  # noqa

        # Wagtail API endpoints are registered in geomanagerweb/api.py
        # No need to register them here to avoid conflicts
