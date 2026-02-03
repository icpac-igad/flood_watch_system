from wagtail_modeladmin.options import ModelAdmin, ModelAdminGroup, modeladmin_register
from wagtail.admin.panels import FieldPanel
from wagtail import hooks
from django.urls import reverse
from django.utils.html import format_html

from .models import SiteTheme, MultimodalDataUpload, CategoryDescription


class CategoryDescriptionAdmin(ModelAdmin):
    model = CategoryDescription
    menu_label = "Category Descriptions"
    menu_icon = "list-ul"
    menu_order = 150
    list_display = ("category_id", "description")
    search_fields = ("description",)


class SiteThemeAdmin(ModelAdmin):
    model = SiteTheme
    menu_label = "Site Theme"
    menu_icon = "palette"
    menu_order = 300
    list_display = ("name", "primary_color", "secondary_color", "accent_color", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name",)


class MultimodalDataUploadAdmin(ModelAdmin):
    model = MultimodalDataUpload
    menu_label = "Multimodal Upload"
    menu_icon = "upload"
    menu_order = 200
    list_display = ("title", "data_date", "source", "status", "feature_count", "matched_count", "created_at")
    list_filter = ("status", "source", "data_date")
    search_fields = ("title",)
    ordering = ["-data_date", "-created_at"]

    def get_extra_attrs_for_row(self, obj, context):
        """Add color highlighting based on status."""
        if obj.status == "completed":
            return {"style": "background-color: #d4edda;"}
        elif obj.status == "failed":
            return {"style": "background-color: #f8d7da;"}
        elif obj.status == "processing":
            return {"style": "background-color: #fff3cd;"}
        return {}


class DataManagementGroup(ModelAdminGroup):
    menu_label = "Data Management"
    menu_icon = "doc-full-inverse"
    menu_order = 250
    items = (MultimodalDataUploadAdmin,)


modeladmin_register(CategoryDescriptionAdmin)
modeladmin_register(SiteThemeAdmin)
modeladmin_register(DataManagementGroup)


# Add a button to process uploads
@hooks.register('register_admin_urls')
def register_process_upload_url():
    from django.urls import path
    from django.http import HttpResponseRedirect
    from django.contrib import messages

    def process_upload_view(request, upload_id):
        try:
            upload = MultimodalDataUpload.objects.get(id=upload_id)
            if upload.process_upload():
                messages.success(request, f"Successfully processed: {upload.title}")
            else:
                messages.error(request, f"Failed to process: {upload.title}. Check logs.")
        except MultimodalDataUpload.DoesNotExist:
            messages.error(request, "Upload not found")

        return HttpResponseRedirect(reverse('multimodaldataupload_modeladmin_index'))

    return [
        path('multimodal/process/<int:upload_id>/', process_upload_view, name='process_multimodal_upload'),
    ]
