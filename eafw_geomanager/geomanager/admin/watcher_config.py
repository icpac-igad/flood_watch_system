from django.urls import path, reverse
from django.utils.safestring import mark_safe
from wagtail_modeladmin.views import CreateView, EditView

from geomanager.admin.base import BaseModelAdmin, ModelAdminCanHide
from geomanager.models import WatcherConfig
from geomanager.views.watcher_preview import preview_watcher_config_view, trigger_watcher_update_view


class WatcherConfigCreateView(CreateView):
    """Custom create view with preview button context"""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        preview_url = reverse("geomanager_preview_watcher_config")
        context["preview_url"] = preview_url
        context["show_preview_button"] = True

        # Inject JavaScript variables for preview functionality
        preview_js = mark_safe(
            f'<script>window.watcherConfigPreviewUrl = "{preview_url}"; window.watcherConfigId = "";</script>'
        )
        context["preview_js"] = preview_js

        return context


class WatcherConfigEditView(EditView):
    """Custom edit view with preview button context"""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        preview_url = reverse("geomanager_preview_watcher_config")
        trigger_url = reverse("geomanager_trigger_watcher_update")
        config_id = str(self.instance.id)

        context["preview_url"] = preview_url
        context["show_preview_button"] = True
        context["config_id"] = config_id

        # Inject JavaScript variables for preview and trigger functionality
        preview_js = mark_safe(
            f'<script>window.watcherConfigPreviewUrl = "{preview_url}"; '
            f'window.watcherConfigTriggerUrl = "{trigger_url}"; '
            f'window.watcherConfigId = "{config_id}";</script>'
        )
        context["preview_js"] = preview_js

        return context


class WatcherConfigModelAdmin(BaseModelAdmin, ModelAdminCanHide):
    model = WatcherConfig
    exclude_from_explorer = True
    menu_icon = "information-management"

    # Custom views for preview functionality
    create_view_class = WatcherConfigCreateView
    edit_view_class = WatcherConfigEditView

    # Add JavaScript for conditional field display and preview functionality
    form_view_extra_js = ["geomanager/js/watcher-config-conditional.js", "geomanager/js/watcher-config-preview.js"]

    list_display = ["title", "parser_type", "period_type", "auto_update_frequency"]
    list_filter = ["parser_type", "period_type"]
    search_fields = ["title", "description", "api_url"]


# URL patterns for watcher config preview and trigger
urls = [
    path("preview-watcher-config/", preview_watcher_config_view, name="geomanager_preview_watcher_config"),
    path("trigger-watcher-update/", trigger_watcher_update_view, name="geomanager_trigger_watcher_update"),
]
