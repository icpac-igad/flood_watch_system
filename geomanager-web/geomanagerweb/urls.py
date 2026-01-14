from django.conf import settings
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path, re_path
from django.views.generic import RedirectView
from wagtail import views as wagtail_views
from wagtail.admin import urls as wagtailadmin_urls
from wagtail.documents import urls as wagtaildocs_urls
from wagtail.urls import WAGTAIL_FRONTEND_LOGIN_TEMPLATE, serve_pattern
from wagtailcache.cache import cache_page


from .api import api_router, FloodProofsAvailableDatesView, FloodProofsDataView, FloodProofsGeoJSONView, MultimodalForecastGeoJSONView, MultimodalClusteredGeoJSONView, MultimodalAvailableDatesView, AdminBoundaryView, ImpactForecastDatesView, DatasetsProxyView, ReportsListView, BasinGeometryView, GridCellsView, SituationSummaryView, HotspotsView
from home.views import map_view, partners_view
from home.mapviewer_config import get_mapviewer_config

ADMIN_URL_PATH = getattr(settings, "ADMIN_URL_PATH", None)

# Note: Wagtail API endpoints are registered in api.py
# The router is available at the path matching its name: "webapi" -> "web-api/"

urlpatterns = [
    path("i18n/", include("django.conf.urls.i18n")),  # Language switching
    path("documents/", include(wagtaildocs_urls)),
    path("", include((api_router.urls[0], api_router.urls[1]))),
    # Alias routes for mapviewer compatibility (redirects to /api/ prefixed paths)
    path("mapviewer-config", get_mapviewer_config, name="mapview_config_alias"),
    re_path(r"^datasets/(?P<path>.*)$", DatasetsProxyView.as_view(), name="datasets_proxy"),
    # FloodProofs API endpoints
    path("api/floodproofs/dates/", FloodProofsAvailableDatesView.as_view(), name="floodproofs_dates"),
    path("api/floodproofs/data/", FloodProofsDataView.as_view(), name="floodproofs_data"),
    path("api/floodproofs/geojson/", FloodProofsGeoJSONView.as_view(), name="floodproofs_geojson"),
    # Multimodal Forecast API endpoints
    path("api/multimodal/geojson/", MultimodalForecastGeoJSONView.as_view(), name="multimodal_forecast_geojson"),
    path("api/multimodal/dates/", MultimodalAvailableDatesView.as_view(), name="multimodal_dates"),
    # Multimodal Clustered GeoJSON - returns pre-clustered data based on zoom level
    path("api/multimodal/clustered/", MultimodalClusteredGeoJSONView.as_view(), name="multimodal_clustered_geojson"),
    # FloodWatch Custom: Admin Boundary API for filter dropdowns
    path("api/admin-boundaries/", AdminBoundaryView.as_view(), name="admin_boundaries"),
    path("api/reports/", ReportsListView.as_view(), name="reports"),
    # FloodProofs Impact forecast dates API
    path("api/impact/dates/", ImpactForecastDatesView.as_view(), name="impact_forecast_dates"),
    # FloodWatch Custom: Basin Geometry API - returns GeoJSON for basin by hybas_id
    path("api/basin/<int:hybas_id>/", BasinGeometryView.as_view(), name="basin_geometry"),
    # FloodWatch Custom: Grid Cells API - returns grid cells for a country/region
    path("api/grid-cells/", GridCellsView.as_view(), name="grid_cells"),
    # FloodWatch Custom: Homepage KPI APIs
    path("api/situation-summary/", SituationSummaryView.as_view(), name="situation_summary"),
    path("api/hotspots/", HotspotsView.as_view(), name="hotspots"),
    # Custom mapviewer config (includes datasets and layers) - MUST come before geomanager.urls
    path("api/mapviewer-config", get_mapviewer_config, name="mapview_config"),
    # Custom mapviewer URLs (with navbar context) - MUST come before geomanager.urls
    path("mapviewer/", map_view, name="mapview"),
    # Partners page - displays CMS-managed partners and member countries
    path("partners/", partners_view, name="partners"),
    path("mapviewer/<str:location_type>/", map_view, name="mapview_location"),
    path("mapviewer/<str:location_type>/<str:adm0>/", map_view, name="mapview_adm0"),
    path("mapviewer/<str:location_type>/<str:adm0>/<str:adm1>/", map_view, name="mapview_adm1"),
    path("mapviewer/<str:location_type>/<str:adm0>/<str:adm1>/<str:adm2>/", map_view, name="mapview_adm2"),
    # geomanager urls (without namespace so reverse() works in serializers)
    path("", include("geomanager.urls")),
    path("", include("django_nextjs.urls")),
    # forecastmanager urls
    path("forecast/", include("forecastmanager.urls")),

]

if ADMIN_URL_PATH:
    ADMIN_URL_PATH = ADMIN_URL_PATH.strip("/")
    urlpatterns += (path(f"{ADMIN_URL_PATH}/", include(wagtailadmin_urls), name="admin"),)

if settings.DEBUG:
    from django.conf.urls.static import static
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns

    # Serve static and media files from development server
    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

    # add django-admin url
    urlpatterns += (path("django-admin/", admin.site.urls),)

urlpatterns = urlpatterns + [
    # For anything not caught by a more specific rule above, hand over to
    # Wagtail's page serving mechanism. This should be the last pattern in
    # the list:
    # Copied from wagtail.urls for compatibility with wagtail-cache. See wagtail-cache documentation
    path(
        "_util/authenticate_with_password/<int:page_view_restriction_id>/<int:page_id>/",
        wagtail_views.authenticate_with_password,
        name="wagtailcore_authenticate_with_password",
    ),
    path(
        "_util/login/",
        auth_views.LoginView.as_view(template_name=WAGTAIL_FRONTEND_LOGIN_TEMPLATE),
        name="wagtailcore_login",
    ),
    # Front-end page views are handled through Wagtail's core.views.serve
    # mechanism
    # Custom wagtail pages serving with cache implements from wagtail-cache page
    re_path(serve_pattern, cache_page(wagtail_views.serve), name="wagtail_serve"),
]
