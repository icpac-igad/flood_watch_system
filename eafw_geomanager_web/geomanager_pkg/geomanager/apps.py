import sys
from django.apps import AppConfig
from django.conf import settings

# Management commands that should NOT start background watcher threads.
# Anything not in this list (gunicorn, daphne, runserver, uvicorn) will start the scheduler.
_SKIP_COMMANDS = frozenset(
    [
        "migrate",
        "makemigrations",
        "collectstatic",
        "shell",
        "shell_plus",
        "test",
        "check",
        "inspectdb",
        "dumpdata",
        "loaddata",
        "createsuperuser",
        "trigger_watchers",
        "showmigrations",
        "sqlmigrate",
        "dbshell",
    ]
)


class GeomanagerConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "geomanager"

    def ready(self):
        # Register signal handlers
        import geomanager.signals  # noqa: F401

        if self._should_start_watchers():
            self._start_periodic_watchers()

    def _should_start_watchers(self) -> bool:
        if not getattr(settings, "ENABLE_PERIODIC_WATCHERS", False):
            return False

        # Don't start background threads during management commands
        if len(sys.argv) >= 2 and sys.argv[1] in _SKIP_COMMANDS:
            return False

        return True

    def _start_periodic_watchers(self):
        try:
            from geomanager.tasks.periodic import start_periodic_watchers

            start_periodic_watchers()
        except Exception as e:
            print(f"Warning: Could not start periodic watchers: {e}")
