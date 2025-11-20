from django.contrib import admin
from leaflet.admin import LeafletGeoAdmin
from django.utils.html import format_html
from django.utils import timezone
from Impact.models import (
    Admin1, Admin2, WaterBodies, HydroRivers, MonitoringStation,
    MergedDeterministicGeoJSON, EnsembleControlPoint
)
from Impact.models_reports import (
    StationReportApproval, StationAssessment, SavedReport
)

class BaseImpactAdmin(LeafletGeoAdmin):
    settings_overrides = {
        'DEFAULT_CENTER': (0.0, 36.0),
        'DEFAULT_ZOOM': 4,
        'MIN_ZOOM': 3,
        'MAX_ZOOM': 18,
    }

# Essential Geographic Models

@admin.register(Admin1)
class Admin1Admin(BaseImpactAdmin):
    list_display = ['country', 'objectid', 'shape_area']
    search_fields = ['country']
    list_filter = ['country']

@admin.register(Admin2)
class Admin2Admin(BaseImpactAdmin):
    list_display = ['country', 'adm1_name', 'adm2_name', 'shape_area']
    search_fields = ['country', 'adm1_name', 'adm2_name']
    list_filter = ['country']

@admin.register(WaterBodies)
class WaterBodiesAdmin(BaseImpactAdmin):
    list_display = ['name_of_wa', 'type_of_wa', 'sqkm']
    search_fields = ['name_of_wa', 'type_of_wa']
    list_filter = ['type_of_wa']

@admin.register(HydroRivers)
class HydroRiversAdmin(BaseImpactAdmin):
    list_display = ['hyriv_id', 'ord_stra', 'length_km', 'dis_av_cms', 'get_coordinates']
    search_fields = ['hyriv_id']
    list_filter = ['ord_stra', 'endorheic']

    def get_coordinates(self, obj):
        if obj.geometry:
            centroid = obj.geometry.centroid
            return f"{centroid.y:.4f}, {centroid.x:.4f}"
        return "N/A"
    get_coordinates.short_description = 'Lat, Lon'

@admin.register(MonitoringStation)
class MonitoringStationAdmin(BaseImpactAdmin):
    list_display = ['sec_name', 'sec_code', 'basin', 'domain', 'station_type', 'get_latitude', 'get_longitude', 'latest_data_date']
    search_fields = ['sec_name', 'basin', 'domain']
    list_filter = ['basin', 'domain', 'station_type']
    date_hierarchy = 'latest_data_date'

    def get_latitude(self, obj):
        if obj.geometry:
            return f"{obj.geometry.y:.6f}"
        return "N/A"
    get_latitude.short_description = 'Latitude'

    def get_longitude(self, obj):
        if obj.geometry:
            return f"{obj.geometry.x:.6f}"
        return "N/A"
    get_longitude.short_description = 'Longitude'


# Report Management Admin

@admin.register(StationReportApproval)
class StationReportApprovalAdmin(admin.ModelAdmin):
    list_display = ['station_id', 'final_status_badge', 'member_state_status_badge', 'icpac_status_badge', 'updated_at']
    list_filter = ['final_status', 'member_state_status', 'icpac_status', 'created_at', 'updated_at']
    search_fields = ['station_id', 'member_state_poc_name', 'member_state_poc_email', 'icpac_reviewer_name']
    readonly_fields = ['created_at', 'updated_at', 'member_state_approved_at', 'icpac_approved_at']
    date_hierarchy = 'updated_at'

    fieldsets = (
        ('Station Information', {
            'fields': ('station_id', 'summary_text')
        }),
        ('Member State Approval (Stage 1)', {
            'fields': (
                'member_state_poc_name',
                'member_state_poc_title',
                'member_state_poc_organization',
                'member_state_poc_email',
                'member_state_status',
                'member_state_comments',
                'member_state_approved_at'
            )
        }),
        ('ICPAC/RTMWA Approval (Stage 2)', {
            'fields': (
                'icpac_reviewer_name',
                'icpac_reviewer_title',
                'icpac_status',
                'icpac_comments',
                'icpac_approved_at'
            )
        }),
        ('Final Status', {
            'fields': ('final_status',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def final_status_badge(self, obj):
        colors = {
            'approved': 'green',
            'pending': 'orange',
            'changes_requested': 'red',
            'rejected': 'darkred'
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            colors.get(obj.final_status, 'gray'),
            obj.final_status.replace('_', ' ').title()
        )
    final_status_badge.short_description = 'Final Status'

    def member_state_status_badge(self, obj):
        colors = {'approved': 'green', 'pending': 'orange', 'changes_requested': 'red', 'rejected': 'darkred'}
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            colors.get(obj.member_state_status, 'gray'),
            obj.member_state_status.replace('_', ' ').title()
        )
    member_state_status_badge.short_description = 'Member State'

    def icpac_status_badge(self, obj):
        colors = {'approved': 'green', 'pending': 'orange', 'changes_requested': 'red', 'rejected': 'darkred'}
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            colors.get(obj.icpac_status, 'gray'),
            obj.icpac_status.replace('_', ' ').title()
        )
    icpac_status_badge.short_description = 'ICPAC/RTMWA'


@admin.register(SavedReport)
class SavedReportAdmin(admin.ModelAdmin):
    list_display = ['report_title', 'station_id', 'country', 'basin', 'final_status_badge', 'created_at']
    list_filter = ['final_status', 'country', 'basin', 'created_at']
    search_fields = ['report_title', 'station_id', 'country', 'basin']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Report Information', {
            'fields': ('report_title', 'country', 'basin', 'station_id')
        }),
        ('Statistics', {
            'fields': ('total_stations', 'emergency_count', 'alarm_count', 'warning_count', 'normal_count')
        }),
        ('Member State Approval', {
            'fields': ('member_state_approver', 'member_state_organization', 'member_state_status', 'member_state_comments', 'member_state_approved_at')
        }),
        ('ICPAC Approval', {
            'fields': ('icpac_approver', 'icpac_status', 'icpac_comments', 'icpac_approved_at')
        }),
        ('Final Status', {
            'fields': ('final_status',)
        }),
        ('File Exports', {
            'fields': ('pdf_path', 'csv_path', 'png_path'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('generated_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def final_status_badge(self, obj):
        colors = {
            'approved': 'green',
            'pending': 'orange',
            'changes_requested': 'red',
            'rejected': 'darkred'
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            colors.get(obj.final_status, 'gray'),
            obj.final_status.replace('_', ' ').title()
        )
    final_status_badge.short_description = 'Final Status'


@admin.register(MergedDeterministicGeoJSON)
class MergedDeterministicGeoJSONAdmin(admin.ModelAdmin):
    list_display = ['data_date', 'feature_count', 'file_count', 'created_at']
    list_filter = ['created_at', 'updated_at']
    search_fields = ['date_string']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'data_date'
    ordering = ['-data_date']

    fieldsets = (
        ('Date Information', {
            'fields': ('data_date', 'date_string')
        }),
        ('Data Statistics', {
            'fields': ('feature_count', 'file_count', 'file_path')
        }),
        ('Processing Info', {
            'fields': ('processed_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    # Don't show the massive geojson_data field in the admin list
    def get_exclude(self, request, obj=None):
        return ['geojson_data'] if not obj else []


@admin.register(EnsembleControlPoint)
class EnsembleControlPointAdmin(BaseImpactAdmin):
    """Admin interface for ensemble control points used in forecast merging."""
    list_display = ['point_id', 'gridcode', 'admin_name', 'zone', 'x', 'y', 'is_node', 'created_at']
    list_filter = ['zone', 'is_node']
    search_fields = ['point_id', 'gridcode', 'admin_name']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['point_id']

    fieldsets = (
        ('Identification', {
            'fields': ('point_id', 'gridcode')
        }),
        ('Location', {
            'fields': ('admin_name', 'x', 'y', 'zone')
        }),
        ('Properties', {
            'fields': ('is_node', 'geom')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
