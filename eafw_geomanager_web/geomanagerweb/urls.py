from django.conf import settings
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path, re_path
from wagtail import views as wagtail_views
from wagtail.admin import urls as wagtailadmin_urls
from wagtail.documents import urls as wagtaildocs_urls
from wagtail.urls import WAGTAIL_FRONTEND_LOGIN_TEMPLATE, serve_pattern
from wagtailcache.cache import cache_page
from .api import api_router
from home.views import (
    admin_boundary_tiles,
    situation_summary,
    country_summary,
    forecast_timeseries,
    forecast_dates,
    google_flood_dates,
    wrf_daily_rainfall_dates,
    wrf_extreme_rainfall_dates,
)

ADMIN_URL_PATH = getattr(settings, "ADMIN_URL_PATH", None)

urlpatterns = [
    path("documents/", include(wagtaildocs_urls)),
    path("web-api/", api_router.urls),
    # Flood situation API (ticker, country stats, chart data)
    path("api/admin-boundary/tiles/<int:z>/<int:x>/<int:y>", admin_boundary_tiles, name="admin_boundary_tiles"),
    path("api/admin-boundary/tiles/<int:z>/<int:x>/<int:y>/", admin_boundary_tiles, name="admin_boundary_tiles_slash"),
    path("api/adm0-boundary/tiles/<int:z>/<int:x>/<int:y>", admin_boundary_tiles, name="adm0_boundary_tiles"),
    path("api/adm0-boundary/tiles/<int:z>/<int:x>/<int:y>/", admin_boundary_tiles, name="adm0_boundary_tiles_slash"),
    path("api/flood/forecast-dates", forecast_dates, name="forecast_dates"),
    path("api/flood/forecast-dates/", forecast_dates, name="forecast_dates_slash"),
    path("api/flood/google-flood-dates", google_flood_dates, name="google_flood_dates"),
    path("api/flood/google-flood-dates/", google_flood_dates, name="google_flood_dates_slash"),
    path("api/v1/wrf/daily-rainfall/dates", wrf_daily_rainfall_dates, name="wrf_daily_rainfall_dates"),
    path("api/v1/wrf/daily-rainfall/dates/", wrf_daily_rainfall_dates, name="wrf_daily_rainfall_dates_slash"),
    path("api/v1/wrf/extreme-rainfall/dates", wrf_extreme_rainfall_dates, name="wrf_extreme_rainfall_dates"),
    path("api/v1/wrf/extreme-rainfall/dates/", wrf_extreme_rainfall_dates, name="wrf_extreme_rainfall_dates_slash"),
    path("api/flood/situation-summary", situation_summary, name="situation_summary"),
    path("api/flood/country-summary", country_summary, name="country_summary"),
    path("api/flood/forecast-timeseries/<int:point_id>", forecast_timeseries, name="forecast_timeseries"),
    # geomanager urls
    path("", include("geomanager.urls"), name="geomanager"),
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
