from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    WaterbodiesViewSet,
    Admin0ViewSet,
    Admin1ViewSet,
    Admin2ViewSet,
    MonitoringStationViewSet,
    HydroRiversViewSet,
    EnsembleControlPointViewSet,
    get_geojson_by_date,
    get_available_dates,
    get_best_available_date,
    MergedDeterministicGeoJSONViewSet,
    get_deterministic_geojson_by_date,
    get_deterministic_available_dates,
    get_deterministic_latest,
    get_geosfm_geojson_by_date,
    get_geosfm_available_dates,
    get_geosfm_latest,
    get_admin_boundaries,
    get_map_layer_config,
    get_merged_forecast_from_file,
    get_merged_forecast_from_db,
)
from .views_titiler import (
    get_raster_files,
    get_raster_info,
    get_raster_statistics,
    get_latest_inundation,
    get_latest_alerts,
    get_raster_dates,
    get_raster_by_date,
)
from .views_files import (
    serve_file,
    list_files,
)
from .views_layer_dates import (
    get_layer_available_dates,
    get_layer_group_available_dates,
    check_date_availability,
    get_all_layers_dates,
    get_latest_date,
)
from .views_reports import (
    StationReportApprovalViewSet,
    StationAssessmentViewSet,
    SavedReportViewSet,
)
from .views_geosfm import geosfm_forecast_urls, geosfm_available_dates as geosfm_gcs_dates

# Create a router and register viewsets
router = DefaultRouter()

# Removed old impact layer API registrations (affectedPop, affectedGDP, affectedCrops, etc.)

# Register APIs for models with current data
router.register(r'admin0', Admin0ViewSet, basename='admin0')
router.register(r'admin1', Admin1ViewSet, basename='admin1')
router.register(r'admin2', Admin2ViewSet, basename='admin2')
router.register(r'water-bodies', WaterbodiesViewSet, basename='water-bodies')
router.register(r'monitoring-stations', MonitoringStationViewSet, basename='monitoring-stations')
router.register(r'rivers', HydroRiversViewSet, basename='rivers')

# Register ensemble control points for forecast merging
router.register(r'ensemble-control-points', EnsembleControlPointViewSet, basename='ensemble-control-points')

# Register merged deterministic GeoJSON data
router.register(r'deterministic-forecast', MergedDeterministicGeoJSONViewSet, basename='deterministic-forecast')

# Removed IBEW v2 impact data API registrations

# NEW: Register report workflow APIs (replaces Node.js api-server)
router.register(r'station-reports', StationReportApprovalViewSet, basename='station-reports')
router.register(r'station-assessments', StationAssessmentViewSet, basename='station-assessments')
router.register(r'saved-reports', SavedReportViewSet, basename='saved-reports')


# URL patterns list for the Impact app. All URLs for the app will be handled by the viewsets registered above.
urlpatterns = [
    # The `router.urls` includes all the registered routes and automatically maps them to the corresponding viewset actions.
    # This means that for each registered ViewSet, Django will generate the appropriate URL patterns for CRUD operations (GET, POST, PUT, DELETE).
    # The '' (empty string) as the URL pattern means that all the API routes for this app will be prefixed with `/api/` in the main URL configuration.
    path('', include(router.urls)),  # This includes all the registered router URLs
    
    # GeoJSON endpoints - order matters, specific routes first
    path('geojson/available-dates/', get_available_dates, name='available-dates'),
    path('geojson/best-date/', get_best_available_date, name='best-available-date'),
    path('geojson/<str:date>/', get_geojson_by_date, name='geojson-by-date'),
    
    # New deterministic forecast GeoJSON endpoints
    path('deterministic/available-dates/', get_deterministic_available_dates, name='deterministic-available-dates'),
    path('deterministic/latest/', get_deterministic_latest, name='deterministic-latest'),
    path('deterministic/<str:date>/', get_deterministic_geojson_by_date, name='deterministic-by-date'),

    # GeoSFM forecast GeoJSON endpoints
    path('geosfm/available-dates/', get_geosfm_available_dates, name='geosfm-available-dates'),
    path('geosfm/latest/', get_geosfm_latest, name='geosfm-latest'),
    path('geosfm/<str:date>/', get_geosfm_geojson_by_date, name='geosfm-by-date'),
    
    # GeoSFM client-side loading (signed URLs from GCS)
    path('geosfm/signed-urls/', geosfm_forecast_urls, name='geosfm-signed-urls'),
    path('geosfm/gcs-dates/', geosfm_gcs_dates, name='geosfm-gcs-dates'),

    # Admin boundaries GeoJSON endpoint - simple like monitoring stations
    path('admin-boundaries/', get_admin_boundaries, name='admin-boundaries'),
    
    # NEW: File-based merged forecast endpoints (lightweight - dated files only)
    path('merged-forecast/dates/', get_merged_forecast_from_file, name='merged-forecast-dates'),
    path('merged-forecast/<str:date>/', get_merged_forecast_from_file, name='merged-forecast-by-date'),

    # NEW: Database-backed merged forecast endpoints (FloodProofs from DB)
    path('merged-forecast-db/dates/', get_merged_forecast_from_db, name='merged-forecast-db-dates'),
    path('merged-forecast-db/<str:date>/', get_merged_forecast_from_db, name='merged-forecast-db-by-date'),

    # TiTiler raster data endpoints
    path('raster/files/', get_raster_files, name='raster-files'),
    path('raster/info/', get_raster_info, name='raster-info'),
    path('raster/statistics/', get_raster_statistics, name='raster-statistics'),
    path('raster/latest-inundation/', get_latest_inundation, name='latest-inundation'),
    path('raster/latest-alerts/', get_latest_alerts, name='latest-alerts'),
    path('raster/dates/', get_raster_dates, name='raster-dates'),
    path('raster/<str:date>/', get_raster_by_date, name='raster-by-date'),

    # Layer date availability endpoints
    path('layers/all-dates/', get_all_layers_dates, name='all-layers-dates'),
    path('layers/<str:layer_id>/available-dates/', get_layer_available_dates, name='layer-available-dates'),
    path('layers/<str:layer_id>/latest-date/', get_latest_date, name='layer-latest-date'),
    path('layers/<str:layer_id>/check-date/<str:date>/', check_date_availability, name='check-date-availability'),
    path('layer-groups/<str:group_id>/available-dates/', get_layer_group_available_dates, name='layer-group-available-dates'),
    # Map layer configuration from admin
    path('map-layers/', get_map_layer_config, name='map-layers'),
]
# Import GeoSFM signed URL views
from .views_geosfm import geosfm_forecast_urls, geosfm_available_dates as geosfm_gcs_dates

# Add to urlpatterns (temporary - will integrate properly)
