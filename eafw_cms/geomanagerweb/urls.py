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

# Homepage widget APIs are served directly from Django views (DRF-style /api/* paths).

from home.views import map_view, partners_view, flood_analysis_view
from home.mapviewer_config import get_mapviewer_config
from geomanagerweb.api import (
    MultimodalForecastGeoJSONView,
    MultimodalAvailableDatesView,
    GeoSFMGeoJSONView,
    MikeHydroGeoJSONView,
    FloodproofGeoJSONView,
    GoogleFloodGeoJSONView,
    GoogleFloodAvailableDatesView,
    CountrySummaryWithBoundsView,
    SituationSummaryView,
    CountryAssessmentsView,
    RiskAssessmentView,
    RegionalSummaryView,
    RiverBasinsView,
    ForecastMajorityRiskView,
    CountryAssessmentPublishView,
)

ADMIN_URL_PATH = getattr(settings, "ADMIN_URL_PATH", None)

urlpatterns = [
    path("i18n/", include("django.conf.urls.i18n")),  # Language switching
    path("documents/", include(wagtaildocs_urls)),
    # Homepage widget API routes (Django).
    path("api/multimodal/geojson/", MultimodalForecastGeoJSONView.as_view(), name="multimodal_geojson"),
    path("api/multimodal/geojson", MultimodalForecastGeoJSONView.as_view(), name="multimodal_geojson_noslash"),
    path("api/multimodal/dates/", MultimodalAvailableDatesView.as_view(), name="multimodal_dates"),
    path("api/multimodal/dates", MultimodalAvailableDatesView.as_view(), name="multimodal_dates_noslash"),
    path("api/geosfm/geojson/", GeoSFMGeoJSONView.as_view(), name="geosfm_geojson"),
    path("api/geosfm/geojson", GeoSFMGeoJSONView.as_view(), name="geosfm_geojson_noslash"),
    path("api/mike-hydro/geojson/", MikeHydroGeoJSONView.as_view(), name="mike_hydro_geojson"),
    path("api/mike-hydro/geojson", MikeHydroGeoJSONView.as_view(), name="mike_hydro_geojson_noslash"),
    path("api/floodproof/geojson/", FloodproofGeoJSONView.as_view(), name="floodproof_geojson"),
    path("api/floodproof/geojson", FloodproofGeoJSONView.as_view(), name="floodproof_geojson_noslash"),
    path("api/google-flood/geojson/", GoogleFloodGeoJSONView.as_view(), name="google_flood_geojson"),
    path("api/google-flood/geojson", GoogleFloodGeoJSONView.as_view(), name="google_flood_geojson_noslash"),
    path("api/google-flood/dates/", GoogleFloodAvailableDatesView.as_view(), name="google_flood_dates"),
    path("api/google-flood/dates", GoogleFloodAvailableDatesView.as_view(), name="google_flood_dates_noslash"),
    path(
        "api/country-summary-with-bounds/",
        CountrySummaryWithBoundsView.as_view(),
        name="country_summary_with_bounds",
    ),
    path(
        "api/country-summary-with-bounds",
        CountrySummaryWithBoundsView.as_view(),
        name="country_summary_with_bounds_noslash",
    ),
    path("api/situation-summary/", SituationSummaryView.as_view(), name="situation_summary"),
    path("api/situation-summary", SituationSummaryView.as_view(), name="situation_summary_noslash"),
    path("api/country-assessments/", CountryAssessmentsView.as_view(), name="country_assessments"),
    path("api/country-assessments", CountryAssessmentsView.as_view(), name="country_assessments_noslash"),
    path("api/country-assessments/<int:assessment_id>/publish/", CountryAssessmentPublishView.as_view(), name="country_assessment_publish"),
    path("api/country-assessments/<int:assessment_id>/publish", CountryAssessmentPublishView.as_view(), name="country_assessment_publish_noslash"),
    path("api/risk-assessments/", RiskAssessmentView.as_view(), name="risk_assessments"),
    path("api/risk-assessments", RiskAssessmentView.as_view(), name="risk_assessments_noslash"),
    path("api/risk-majority/", ForecastMajorityRiskView.as_view(), name="risk_majority"),
    path("api/risk-majority", ForecastMajorityRiskView.as_view(), name="risk_majority_noslash"),
    path("api/regional-summary/generate/", RegionalSummaryView.as_view(), name="regional_summary_generate"),
    path("api/regional-summary/generate", RegionalSummaryView.as_view(), name="regional_summary_generate_noslash"),
    path("api/river-basins/", RiverBasinsView.as_view(), name="river_basins"),
    path("api/river-basins", RiverBasinsView.as_view(), name="river_basins_noslash"),
    # Custom mapviewer config (includes datasets and layers)
    path("mapviewer-config", get_mapviewer_config, name="mapview_config_alias"),
    path("api/mapviewer-config", get_mapviewer_config, name="mapview_config"),
    # Custom mapviewer URLs (with navbar context)
    path("mapviewer/", map_view, name="mapview"),
    # Partners page - displays CMS-managed partners and member countries
    path("partners/", partners_view, name="partners"),
    # Flood Analysis report page - renders Next.js flood-analysis page
    path("flood-analysis/", flood_analysis_view, name="flood_analysis"),
    path("mapviewer/<str:location_type>/", map_view, name="mapview_location"),
    path("mapviewer/<str:location_type>/<str:adm0>/", map_view, name="mapview_adm0"),
    path("mapviewer/<str:location_type>/<str:adm0>/<str:adm1>/", map_view, name="mapview_adm1"),
    path("mapviewer/<str:location_type>/<str:adm0>/<str:adm1>/<str:adm2>/", map_view, name="mapview_adm2"),
    # geomanager urls (without namespace so reverse() works in serializers)
    path("", include("geomanager.urls")),
    path("", include("django_nextjs.urls")),
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
