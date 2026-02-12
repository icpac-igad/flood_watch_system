import base64
import json
from urllib.parse import urlencode

from wagtail_modeladmin.options import ModelAdmin, ModelAdminGroup, modeladmin_register
from wagtail_modeladmin.helpers import PermissionHelper
from wagtail.admin.panels import FieldPanel
from wagtail import hooks
from django.urls import reverse, path
from django.utils.html import format_html
from django.http import HttpResponseRedirect
from django.contrib import messages
from django.db import connection

from .models import (
    SiteTheme, MultimodalDataUpload, CategoryDescription,
    ExpertAssessment, DistrictRiskLevel,
)


COUNTRY_NAME_TO_CODE = {
    "burundi": "BI",
    "djibouti": "DJ",
    "eritrea": "ER",
    "ethiopia": "ET",
    "kenya": "KE",
    "rwanda": "RW",
    "somalia": "SO",
    "south sudan": "SS",
    "sudan": "SD",
    "tanzania": "TZ",
    "uganda": "UG",
    "zanzibar": "TZ",
}


def _country_code_from_name(country):
    text = (country or "").strip()
    if not text:
        return ""
    if len(text) == 2 and text.isalpha():
        return text.upper()
    return COUNTRY_NAME_TO_CODE.get(text.lower(), "")


def _build_flood_analysis_preview_url(obj):
    country_code = _country_code_from_name(obj.country)
    assessment_date = obj.assessment_date
    if assessment_date and hasattr(assessment_date, "isoformat"):
        assessment_date = assessment_date.isoformat()
    elif assessment_date:
        assessment_date = str(assessment_date)
    else:
        assessment_date = ""

    params = {
        "reporting_unit": "Administrative Boundary",
        "forecast_date": assessment_date,
        "alert_filter": "all",
        "admin_level": "0",
        "unit_id": country_code,
        "placename": obj.country or "East Africa Region",
        "admin0_code": country_code,
        # Keep district context in URL state for future deep-link support.
        "district_country": obj.country or "",
        "district_admin1": obj.admin1 or "",
        "district_admin2": obj.admin2 or "",
    }
    state = {"params": params, "settings": {}}
    encoded = base64.b64encode(
        json.dumps(state, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).decode("ascii")
    return f"{reverse('flood_analysis')}?{urlencode({'qstr': encoded})}"


def _build_mapviewer_preview_url(obj):
    country_code = _country_code_from_name(obj.country)
    if country_code:
        return reverse("mapview_adm0", kwargs={"location_type": "country", "adm0": country_code})
    return reverse("mapview")


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


# =============================================================================
# REPORTS GROUP - Read-only views of expert assessments
# =============================================================================

class ReadOnlyPermissionHelper(PermissionHelper):
    """Denies create, edit, and delete — inspect only."""

    def user_can_create(self, user):
        return False

    def user_can_edit_obj(self, user, obj):
        return False

    def user_can_delete_obj(self, user, obj):
        return False


class ExpertAssessmentAdmin(ModelAdmin):
    model = ExpertAssessment
    permission_helper_class = ReadOnlyPermissionHelper
    inspect_view_enabled = True
    menu_label = "Expert Assessments"
    menu_icon = "doc-full"
    list_display = (
        "assessment_date", "report_key_display", "expert_type", "country_name",
        "risk_level", "completion_state", "publication_state", "created_by", "moderation_actions",
    )
    list_filter = ("expert_type", "risk_level", "is_published", "assessment_date")
    search_fields = ("country_name", "created_by", "assessment_comment")
    ordering = ["-assessment_date", "-created_at"]
    inspect_view_fields = [
        "expert_type", "assessment_date", "valid_from", "valid_to",
        "country_code", "country_name", "risk_level",
        "assessment_comment", "affected_areas", "recommendations",
        "created_by", "is_published", "created_at", "updated_at",
    ]

    def get_extra_attrs_for_row(self, obj, context):
        colors = {
            "emergency": "#f8d7da",
            "alarm": "#fff3cd",
            "warning": "#fff9e6",
            "watch": "#d1ecf1",
        }
        bg = colors.get(obj.risk_level)
        if bg:
            return {"style": f"background-color: {bg};"}
        return {}

    def report_key_display(self, obj):
        country = (obj.country_code or "REGION").upper()
        date_value = obj.assessment_date.isoformat() if obj.assessment_date else "unknown-date"
        expert = (obj.expert_type or "expert").lower()
        return f"{expert}_{country}_{date_value}"

    report_key_display.short_description = "Report Key"

    def completion_state(self, obj):
        if obj.is_published:
            color = "#166534"
            label = "approved"
        elif (obj.assessment_comment or "").strip() or (obj.affected_areas or "").strip() or (obj.recommendations or "").strip():
            color = "#92400e"
            label = "unapproved"
        else:
            color = "#374151"
            label = "unfinished"

        return format_html(
            '<span style="display:inline-block;padding:2px 8px;border-radius:999px;background:#f3f4f6;color:{};font-weight:600;text-transform:uppercase;font-size:11px;">{}</span>',
            color,
            label,
        )

    completion_state.short_description = "Completion"

    def publication_state(self, obj):
        if obj.is_published:
            return format_html(
                '<span style="color:#166534;font-weight:700;">Published</span>'
            )
        return format_html(
            '<span style="color:#92400e;font-weight:700;">Draft / Unapproved</span>'
        )

    publication_state.short_description = "Publication"

    def moderation_actions(self, obj):
        if not obj.id:
            return "-"

        if obj.is_published:
            url = reverse("admin_unpublish_assessment", args=[obj.id])
            label = "Mark Draft"
            bg = "#f3f4f6"
            fg = "#374151"
            border = "#d1d5db"
        else:
            url = reverse("admin_publish_assessment", args=[obj.id])
            label = "Approve & Publish"
            bg = "#dcfce7"
            fg = "#166534"
            border = "#86efac"

        return format_html(
            '<a href="{}" style="display:inline-block;padding:4px 10px;border:1px solid {};border-radius:6px;background:{};color:{};font-weight:600;text-decoration:none;">{}</a>',
            url, border, bg, fg, label
        )

    moderation_actions.short_description = "Moderation"


class DistrictRiskLevelAdmin(ModelAdmin):
    model = DistrictRiskLevel
    permission_helper_class = ReadOnlyPermissionHelper
    inspect_view_enabled = True
    menu_label = "District Risk Levels"
    menu_icon = "warning"
    list_display = (
        "assessment_date", "expert_type", "country",
        "admin1", "admin2", "risk_level", "preview_actions",
    )
    list_filter = ("expert_type", "risk_level", "country", "assessment_date")
    search_fields = ("country", "admin1", "admin2")
    ordering = ["-assessment_date", "country", "admin1"]
    inspect_view_fields = [
        "expert_type", "assessment_date", "country",
        "admin1", "admin2", "gid_2", "risk_level",
        "comment", "created_at", "updated_at",
    ]

    def get_extra_attrs_for_row(self, obj, context):
        colors = {
            "emergency": "#f8d7da",
            "alarm": "#fff3cd",
            "warning": "#fff9e6",
            "watch": "#d1ecf1",
        }
        bg = colors.get(obj.risk_level)
        if bg:
            return {"style": f"background-color: {bg};"}
        return {}

    def preview_actions(self, obj):
        flood_url = _build_flood_analysis_preview_url(obj)
        map_url = _build_mapviewer_preview_url(obj)
        return format_html(
            '<div style="display:flex;gap:6px;align-items:center;">'
            '<a href="{}" target="_blank" rel="noopener" style="display:inline-block;padding:3px 8px;border:1px solid #93c5fd;border-radius:6px;background:#eff6ff;color:#1d4ed8;font-weight:600;text-decoration:none;">Preview</a>'
            '<a href="{}" target="_blank" rel="noopener" style="display:inline-block;padding:3px 8px;border:1px solid #86efac;border-radius:6px;background:#ecfdf5;color:#166534;font-weight:600;text-decoration:none;">Mapviewer</a>'
            '</div>',
            flood_url,
            map_url,
        )

    preview_actions.short_description = "Preview"


class ReportsGroup(ModelAdminGroup):
    menu_label = "Flood Reports"
    menu_icon = "doc-full-inverse"
    menu_order = 260
    items = (ExpertAssessmentAdmin, DistrictRiskLevelAdmin)


modeladmin_register(ReportsGroup)


# Add a button to process uploads
@hooks.register('register_admin_urls')
def register_process_upload_url():
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


def _expert_assessment_index_url():
    candidates = (
        "expertassessment_modeladmin_index",
        "home_expertassessment_modeladmin_index",
        "wagtailadmin_home",
    )
    for name in candidates:
        try:
            return reverse(name)
        except Exception:
            continue
    return "/admin/"


def _update_assessment_publication_state(assessment_id, publish):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            UPDATE gha.expert_assessments
            SET is_published = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            RETURNING id, expert_type, country_name, assessment_date, is_published
            """,
            [publish, assessment_id],
        )
        return cursor.fetchone()


@hooks.register("register_admin_urls")
def register_expert_assessment_moderation_urls():
    def _moderate(request, assessment_id, publish):
        if not request.user.is_authenticated or not request.user.is_staff:
            messages.error(request, "You do not have permission to moderate reports.")
            return HttpResponseRedirect(_expert_assessment_index_url())

        try:
            row = _update_assessment_publication_state(assessment_id, publish)
            if not row:
                messages.error(request, "Assessment not found.")
                return HttpResponseRedirect(_expert_assessment_index_url())

            _, expert_type, country_name, assessment_date, is_published = row
            action = "published" if is_published else "moved to draft"
            messages.success(
                request,
                f"{expert_type.title()} report for {country_name} ({assessment_date}) {action}.",
            )
        except Exception as exc:
            messages.error(request, f"Failed to update assessment: {exc}")

        return HttpResponseRedirect(_expert_assessment_index_url())

    def publish_assessment_view(request, assessment_id):
        return _moderate(request, assessment_id, True)

    def unpublish_assessment_view(request, assessment_id):
        return _moderate(request, assessment_id, False)

    return [
        path(
            "flood-reports/assessments/<int:assessment_id>/publish/",
            publish_assessment_view,
            name="admin_publish_assessment",
        ),
        path(
            "flood-reports/assessments/<int:assessment_id>/unpublish/",
            unpublish_assessment_view,
            name="admin_unpublish_assessment",
        ),
    ]
