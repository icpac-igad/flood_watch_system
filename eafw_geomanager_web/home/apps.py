from django.apps import AppConfig


class HomeConfig(AppConfig):
    name = "home"

    def ready(self):
        import home.signals  # noqa
        from home.patches import apply_all as apply_patches
        apply_patches()
