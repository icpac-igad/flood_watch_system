from django.apps import AppConfig
from django.conf import settings


class GeomanagerConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "geomanager"

    def ready(self):
        # Import signals to register handlers
        import geomanager.signals  # noqa: F401

        # Start periodic watchers
        self.start_periodic_watchers()

    def start_periodic_watchers(self):
        # Start the periodic watchers for automatic updates.To disable periodic watchers, set ENABLE_PERIODIC_WATCHERS = False
        # Check if periodic watchers are enabled (default: True)
        enable_periodic = getattr(settings, "ENABLE_PERIODIC_WATCHERS", True)

        if not enable_periodic:
            print("Periodic watchers disabled via settings. Using signal-based triggering only.")
            return

        try:
            from geomanager.tasks.periodic import start_periodic_watchers

            start_periodic_watchers()
            print("Periodic watchers started successfully (background monitoring enabled)")
        except Exception as e:
            print(f"Warning: Could not start periodic watchers: {e}")
