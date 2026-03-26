from wagtail_modeladmin.options import ModelAdmin, modeladmin_register
from .models import SiteTheme


class SiteThemeAdmin(ModelAdmin):
    model = SiteTheme
    menu_label = "Site Theme"
    menu_icon = "palette"
    menu_order = 300
    list_display = ("name", "primary_color", "secondary_color", "accent_color", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name",)


modeladmin_register(SiteThemeAdmin)
