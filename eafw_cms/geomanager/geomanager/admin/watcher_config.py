from geomanager.admin.base import BaseModelAdmin, ModelAdminCanHide
from geomanager.models import WatcherConfig


class WatcherConfigModelAdmin(BaseModelAdmin, ModelAdminCanHide):
    model = WatcherConfig
    exclude_from_explorer = True
    menu_icon = "rotate"

    # Add JavaScript for conditional field display based on parser_type
    form_view_extra_js = ["geomanager/js/watcher-config-conditional.js"]

    list_display = ["title", "parser_type", "period_type", "auto_update_frequency"]
    list_filter = ["parser_type", "period_type"]
    search_fields = ["title", "description", "api_url"]
