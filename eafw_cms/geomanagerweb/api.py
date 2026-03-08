from wagtail.api.v2.router import WagtailAPIRouter
from wagtail.api.v2.views import BaseAPIViewSet
from django.http import JsonResponse
from django.views import View
from datetime import datetime, timedelta

# WHCA project countries (ISO2) for scope fallback when whca_selected is unset
WHCA_COUNTRY_CODES = ("SD", "SS", "UG", "ET", "RW")
WHCA_COUNTRY_CODES_SQL = ",".join(f"'{code}'" for code in WHCA_COUNTRY_CODES)
WHCA_SCOPE_SQL_CONDITION = (
    "(COALESCE(cp.whca_selected, FALSE) IS TRUE OR "
    f"UPPER(COALESCE(cp.country_code, '')) IN ({WHCA_COUNTRY_CODES_SQL}))"
)

COUNTRY_NAME_TO_ISO2 = {
    "burundi": "BD",
    "djibouti": "DJ",
    "ethiopia": "ET",
    "kenya": "KE",
    "rwanda": "RW",
    "somalia": "SO",
    "south sudan": "SS",
    "sudan": "SD",
    "tanzania": "TZ",
    "uganda": "UG",
    "zanzibar": "TZ",
    "region": "REGION",
    "east africa region": "REGION",
}

ISO2_TO_COUNTRY_NAME = {
    "BD": "Burundi",
    "DJ": "Djibouti",
    "ET": "Ethiopia",
    "KE": "Kenya",
    "RW": "Rwanda",
    "SO": "Somalia",
    "SS": "South Sudan",
    "SD": "Sudan",
    "TZ": "Tanzania",
    "UG": "Uganda",
    "REGION": "East Africa Region",
}


def _add_cors_headers(response):
    """Attach permissive CORS headers used by mapviewer data endpoints."""
    response['Access-Control-Allow-Origin'] = '*'
    response['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
    response['Access-Control-Allow-Headers'] = 'Content-Type'
    return response


def _get_multimodal_thresholds(request):
    """Read cluster thresholds from CMS settings with safe defaults."""
    try:
        from home.models import MultimodalClusterSettings
        cluster_settings = MultimodalClusterSettings.load(request_or_site=request)
        return (
            float(cluster_settings.warning_threshold),
            float(cluster_settings.alarm_threshold),
            float(cluster_settings.emergency_threshold),
        )
    except Exception:
        return (150.0, 300.0, 450.0)


def _parse_query_date(date_str):
    """Parse YYYY-MM-DD date or return (None, error_response)."""
    if not date_str:
        return None, None
    try:
        return datetime.strptime(date_str, '%Y-%m-%d').date(), None
    except ValueError:
        response = JsonResponse({'error': 'Invalid date format. Use YYYY-MM-DD'}, status=400)
        return None, _add_cors_headers(response)


def _is_truthy_param(value):
    return str(value).strip().lower() in ('1', 'true', 'yes', 'on')


def _coerce_bool(value, default=False):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    if text in ('1', 'true', 'yes', 'on'):
        return True
    if text in ('0', 'false', 'no', 'off'):
        return False
    return default


def _split_csv_values(raw_value):
    if not raw_value:
        return []
    return [item.strip() for item in str(raw_value).split(',') if item and item.strip()]


def _resolve_scope_mode(request):
    scope_mode = (request.GET.get('scope') or '').strip().lower()
    if not scope_mode and _is_truthy_param(request.GET.get('whca_filter')):
        scope_mode = 'whca'
    return scope_mode or 'all'


def _normalize_country_code(raw_value):
    value = (raw_value or "").strip()
    if not value:
        return ""

    mapped = COUNTRY_NAME_TO_ISO2.get(value.lower())
    if mapped:
        return mapped

    upper_value = value.upper()
    if upper_value in ("REGION",):
        return "REGION"
    if len(upper_value) == 2 and upper_value.isalpha():
        return upper_value
    return value


def _parse_creator_metadata(created_by):
    raw = (created_by or "").strip()
    if not raw:
        return {
            "creator_type": "unknown",
            "contributor_name": "",
            "contributor_country": "",
        }

    # Encoded format used by flood-analysis UI:
    #   "kpp|<name>|<country_code>" or "public|<name>|<country_code>"
    parts = raw.split("|")
    if len(parts) >= 3 and parts[0] in ("kpp", "public"):
        return {
            "creator_type": "key_point_person" if parts[0] == "kpp" else "public",
            "contributor_name": parts[1].strip(),
            "contributor_country": _normalize_country_code(parts[2]),
        }

    # Legacy fallback keeps old created_by values visible as a name.
    return {
        "creator_type": "legacy",
        "contributor_name": raw,
        "contributor_country": "",
    }


def _format_report_key(expert_type, country_code, assessment_date):
    expert_prefix = (expert_type or "general").strip().lower()
    country_suffix = (_normalize_country_code(country_code) or "REGION").upper()
    date_part = (assessment_date or "").strip()
    return f"{expert_prefix}_{country_suffix}_{date_part}"


def _normalize_role_name(value):
    return str(value or '').strip().lower().replace('-', '_').replace(' ', '_')


def _resolve_request_user(request):
    user = getattr(request, 'user', None)
    if user and getattr(user, 'is_authenticated', False):
        return user

    auth_header = (
        request.headers.get('Authorization')
        or request.META.get('HTTP_AUTHORIZATION')
        or ''
    ).strip()
    if not auth_header.lower().startswith('bearer '):
        return None

    token = auth_header.split(' ', 1)[1].strip() if ' ' in auth_header else ''
    if not token:
        return None

    try:
        from django.contrib.auth import get_user_model
        from rest_framework_simplejwt.tokens import AccessToken

        parsed = AccessToken(token)
        user_id = parsed.get('user_id')
        if not user_id:
            return None

        user_model = get_user_model()
        return user_model.objects.filter(id=user_id).first()
    except Exception:
        return None


def _user_role_names(user):
    if not user:
        return set()
    try:
        return {
            _normalize_role_name(group.name)
            for group in user.groups.all()
            if getattr(group, 'name', None)
        }
    except Exception:
        return set()


def _can_submit_expert_assessment(user, expert_type):
    if not user:
        return False
    if getattr(user, 'is_superuser', False) or getattr(user, 'is_staff', False):
        return True

    role_names = _user_role_names(user)
    role = _normalize_role_name(expert_type)
    role_aliases = {
        'hydrologist': {'hydrologist', 'hydrologists', 'expert_hydrologist', 'flood_hydrologist'},
        'meteorologist': {'meteorologist', 'meteorologists', 'expert_meteorologist', 'flood_meteorologist'},
    }
    required = role_aliases.get(role, {role})
    return any(name in role_names for name in required)


def _can_publish_expert_assessment(user):
    if not user:
        return False
    if getattr(user, 'is_superuser', False) or getattr(user, 'is_staff', False):
        return True

    role_names = _user_role_names(user)
    publish_roles = {
        'hydrologist',
        'meteorologist',
        'flood_report_publisher',
        'flood_reports_publisher',
        'flood_report_admin',
        'flood_reports_admin',
    }
    return any(name in role_names for name in publish_roles)


def _user_display_name(user):
    if not user:
        return ''
    full_name = ''
    try:
        full_name = (user.get_full_name() or '').strip()
    except Exception:
        full_name = ''
    if full_name:
        return full_name
    username = getattr(user, 'username', '') or getattr(user, 'email', '')
    return str(username).strip()


def _resolve_filter_geometry_ewkt(
    cursor,
    country_name='',
    region_name='',
    district_name='',
    project_countries=None,
):
    """Resolve admin/project clip geometry and return EWKT text or None."""
    country_name = (country_name or '').strip()
    region_name = (region_name or '').strip()
    district_name = (district_name or '').strip()
    project_countries = project_countries or []

    if district_name:
        cursor.execute(
            """
            SELECT ST_AsEWKT(geom)
            FROM gha.admin2
            WHERE LOWER(name_2) = LOWER(%s)
              AND (%s = '' OR LOWER(name_1) = LOWER(%s))
              AND (%s = '' OR LOWER(country) = LOWER(%s))
            LIMIT 1
            """,
            [district_name, region_name, region_name, country_name, country_name],
        )
    elif region_name:
        cursor.execute(
            """
            SELECT ST_AsEWKT(geom)
            FROM gha.admin1
            WHERE LOWER(name_1) = LOWER(%s)
              AND (%s = '' OR LOWER(country) = LOWER(%s))
            LIMIT 1
            """,
            [region_name, country_name, country_name],
        )
    elif country_name:
        cursor.execute(
            """
            SELECT ST_AsEWKT(geom)
            FROM gha.admin0
            WHERE LOWER(country) = LOWER(%s)
            LIMIT 1
            """,
            [country_name],
        )
    elif project_countries:
        cursor.execute(
            """
            SELECT ST_AsEWKT(ST_Union(geom))
            FROM gha.admin0
            WHERE country = ANY(%s)
            """,
            [project_countries],
        )
    else:
        return None

    row = cursor.fetchone()
    return row[0] if row and row[0] else None

# Create API router
api_router = WagtailAPIRouter("webapi")


# MapserverConfig API ViewSet
class MapserverConfigAPIViewSet(BaseAPIViewSet):
    def get_queryset(self):
        from home.models import MapserverConfig
        return MapserverConfig.objects.all()

    @property
    def model(self):
        from home.models import MapserverConfig
        return MapserverConfig

    model_fields = [
        "service_title",
        "service_purpose",
        "service_provider",
        "provider_url",
        "contact_name",
        "email_address",
        "office_country",
        "office_city",
        "physical_address",
        "default_language",
        "service_fee",
        "use_terms",
    ]
    listing_default_fields = model_fields
    body_fields = model_fields


# Register mapserver config endpoint
api_router.register_endpoint("wms-wfs", MapserverConfigAPIViewSet)


# FloodProofs API Views
class FloodProofsAvailableDatesView(View):
    """API endpoint to get available FloodProofs forecast dates"""

    def get(self, request):
        from home.models import MergedDeterministicGeoJSON
        from datetime import datetime, time

        dates = MergedDeterministicGeoJSON.objects.values_list(
            'data_date', 'feature_count'
        ).order_by('-data_date')

        # Convert dates to string format YYYY-MM-DD
        dates_list = [
            date.strftime('%Y-%m-%d')
            for date, count in dates
        ]

        response = JsonResponse({
            'timestamps': dates_list,  # Frontend expects 'timestamps' key
            'dates': dates_list,       # Keep for backwards compatibility
            'count': len(dates_list)
        })

        # Add CORS headers
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        response['Access-Control-Allow-Headers'] = 'Content-Type'

        return response


class FloodProofsDataView(View):
    """API endpoint to get FloodProofs GeoJSON data for a specific date"""

    def get(self, request):
        from home.models import MergedDeterministicGeoJSON

        # Get date parameter (defaults to latest)
        date_str = request.GET.get('date')

        if date_str:
            try:
                date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
                forecast = MergedDeterministicGeoJSON.objects.filter(
                    data_date=date_obj
                ).first()
            except ValueError:
                return JsonResponse({
                    'error': 'Invalid date format. Use YYYY-MM-DD'
                }, status=400)
        else:
            # Get latest forecast
            forecast = MergedDeterministicGeoJSON.objects.order_by('-data_date').first()

        if not forecast:
            return JsonResponse({
                'error': 'No forecast data available'
            }, status=404)

        return JsonResponse({
            'date': forecast.data_date.isoformat(),
            'feature_count': forecast.feature_count,
            'geojson': forecast.geojson_data
        })


class FloodProofsGeoJSONView(View):
    """API endpoint to get processed FloodProofs GeoJSON with alert levels"""

    def get(self, request):
        from django.db import connection

        # Get date parameter (defaults to latest)
        date_str = request.GET.get('date')

        # SQL to query raw data and compute alert levels on the fly
        base_query = """
            WITH target_data AS (
                SELECT data_date, geojson_data
                FROM floodproofs.merged_deterministic_geojson
                WHERE {date_filter}
                LIMIT 1
            ),
            features AS (
                SELECT
                    td.data_date,
                    jsonb_array_elements(td.geojson_data -> 'features') AS feature
                FROM target_data td
            ),
            processed AS (
                SELECT
                    f.data_date,
                    (f.feature -> 'properties' ->> 'section_id')::text AS station_id,
                    COALESCE(f.feature -> 'properties' ->> 'section_name', f.feature -> 'properties' ->> 'SEC_NAME')::text AS station_name,
                    (f.feature -> 'properties' ->> 'TYPE')::text AS river_name,
                    round(floodproofs.get_first_csv_value(f.feature -> 'properties' ->> 'time_series_discharge_simulated-gfs')) AS discharge_gfs,
                    round(floodproofs.get_first_csv_value(f.feature -> 'properties' ->> 'time_series_discharge_simulated-icon')) AS discharge_icon,
                    round(GREATEST(
                        COALESCE(floodproofs.get_first_csv_value(f.feature -> 'properties' ->> 'time_series_discharge_simulated-gfs'), 0),
                        COALESCE(floodproofs.get_first_csv_value(f.feature -> 'properties' ->> 'time_series_discharge_simulated-icon'), 0)
                    )) AS discharge_primary,
                    round((f.feature -> 'properties' ->> 'section_discharge_thr_alert')::numeric) AS threshold_alert,
                    round((f.feature -> 'properties' ->> 'section_discharge_thr_alarm')::numeric) AS threshold_alarm,
                    round((f.feature -> 'properties' ->> 'section_discharge_thr_emergency')::numeric) AS threshold_emergency,
                    CASE
                        -- If all thresholds are 0 or null, mark as Normal (no meaningful data)
                        WHEN COALESCE(round((f.feature -> 'properties' ->> 'section_discharge_thr_alert')::numeric), 0) = 0
                             AND COALESCE(round((f.feature -> 'properties' ->> 'section_discharge_thr_alarm')::numeric), 0) = 0
                             AND COALESCE(round((f.feature -> 'properties' ->> 'section_discharge_thr_emergency')::numeric), 0) = 0
                        THEN 'Normal'
                        -- Check emergency threshold (must be > 0 to be meaningful)
                        WHEN round((f.feature -> 'properties' ->> 'section_discharge_thr_emergency')::numeric) > 0
                             AND GREATEST(
                                 COALESCE(floodproofs.get_first_csv_value(f.feature -> 'properties' ->> 'time_series_discharge_simulated-gfs'), 0),
                                 COALESCE(floodproofs.get_first_csv_value(f.feature -> 'properties' ->> 'time_series_discharge_simulated-icon'), 0)
                             ) >= round((f.feature -> 'properties' ->> 'section_discharge_thr_emergency')::numeric)
                        THEN 'Emergency'
                        -- Check alarm threshold
                        WHEN round((f.feature -> 'properties' ->> 'section_discharge_thr_alarm')::numeric) > 0
                             AND GREATEST(
                                 COALESCE(floodproofs.get_first_csv_value(f.feature -> 'properties' ->> 'time_series_discharge_simulated-gfs'), 0),
                                 COALESCE(floodproofs.get_first_csv_value(f.feature -> 'properties' ->> 'time_series_discharge_simulated-icon'), 0)
                             ) >= round((f.feature -> 'properties' ->> 'section_discharge_thr_alarm')::numeric)
                        THEN 'Alarm'
                        -- Check alert threshold
                        WHEN round((f.feature -> 'properties' ->> 'section_discharge_thr_alert')::numeric) > 0
                             AND GREATEST(
                                 COALESCE(floodproofs.get_first_csv_value(f.feature -> 'properties' ->> 'time_series_discharge_simulated-gfs'), 0),
                                 COALESCE(floodproofs.get_first_csv_value(f.feature -> 'properties' ->> 'time_series_discharge_simulated-icon'), 0)
                             ) >= round((f.feature -> 'properties' ->> 'section_discharge_thr_alert')::numeric)
                        THEN 'Warning'
                        ELSE 'Normal'
                    END::text AS alert_level,
                    (f.feature -> 'properties' ->> 'BASIN')::text AS basin,
                    (f.feature -> 'properties' ->> 'ADMIN_B_L1')::text AS admin_level_1,
                    ST_SetSRID(ST_MakePoint(
                        ((f.feature -> 'properties' ->> 'LON')::numeric)::double precision,
                        ((f.feature -> 'properties' ->> 'LAT')::numeric)::double precision
                    ), 4326) AS geom
                FROM features f
                WHERE (f.feature -> 'properties' ->> 'section_id') IS NOT NULL
            )
            SELECT json_build_object(
                'type', 'FeatureCollection',
                'features', COALESCE(json_agg(
                    json_build_object(
                        'type', 'Feature',
                        'geometry', ST_AsGeoJSON(geom)::json,
                        'properties', json_build_object(
                            'station_id', station_id,
                            'station_name', station_name,
                            'river_name', river_name,
                            'alert_level', alert_level,
                            'discharge_gfs', discharge_gfs,
                            'discharge_icon', discharge_icon,
                            'discharge_primary', discharge_primary,
                            'threshold_alert', threshold_alert,
                            'threshold_alarm', threshold_alarm,
                            'threshold_emergency', threshold_emergency,
                            'basin', basin,
                            'admin_level_1', admin_level_1,
                            'data_date', data_date::text
                        )
                    )
                ), '[]'::json)
            ) as geojson
            FROM processed
        """

        with connection.cursor() as cursor:
            try:
                if date_str:
                    try:
                        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
                        query = base_query.format(date_filter="data_date = %s")
                        cursor.execute(query, [date_obj])
                    except ValueError:
                        response = JsonResponse({
                            'error': 'Invalid date format. Use YYYY-MM-DD'
                        }, status=400)
                        response['Access-Control-Allow-Origin'] = '*'
                        return response
                else:
                    # Get latest date
                    query = base_query.format(
                        date_filter="data_date = (SELECT MAX(data_date) FROM floodproofs.merged_deterministic_geojson)"
                    )
                    cursor.execute(query)

                result = cursor.fetchone()

                if not result or not result[0]:
                    response = JsonResponse({
                        'error': 'No data available'
                    }, status=404)
                    response['Access-Control-Allow-Origin'] = '*'
                    return response

                geojson = result[0]

            except Exception as e:
                response = JsonResponse({
                    'error': f'Query failed: {str(e)}'
                }, status=500)
                response['Access-Control-Allow-Origin'] = '*'
                return response

        response = JsonResponse(geojson, safe=False)

        # Add CORS headers
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        response['Access-Control-Allow-Headers'] = 'Content-Type'

        return response


class MultimodalForecastGeoJSONView(View):
    """API endpoint to get multimodal ensemble forecast GeoJSON data

    Now uses normalized gha.multimodal_control_points and gha.multimodal_forecasts tables
    instead of the old home_multimodal_forecast_geojson JSONB blob table.

    Query Parameters:
        date: Filter by specific date (YYYY-MM-DD format). Defaults to latest.
        filter: Filter points by alert level. Options:
            - 'all': All points (default)
            - 'active': Warning level and above (daily_avg >= warning_threshold)
            - 'alarm': Alarm level and above (daily_avg >= alarm_threshold)
            - 'emergency': Emergency only (daily_avg >= emergency_threshold)
        scope: Country scope filter:
            - 'all': All countries (default)
            - 'whca': WHCA project countries only (uses cp.whca_selected = true)
    """

    def get(self, request):
        from django.db import connection
        import json as json_module
        from home.models import MultimodalClusterSettings

        # Get date parameter (defaults to latest)
        date_str = request.GET.get('date')

        # Get filter parameter for alert level filtering
        filter_mode = request.GET.get('filter', 'all')

        # Optional country scope filter (also inferred from whca_filter=true)
        scope_mode = _resolve_scope_mode(request)
        if scope_mode not in ('all', 'whca'):
            response = JsonResponse({
                'error': 'Invalid scope. Use all or whca'
            }, status=400)
            response['Access-Control-Allow-Origin'] = '*'
            return response

        country_name = request.GET.get('country_name', '')
        region_name = request.GET.get('region_name', '')
        district_name = request.GET.get('district_name', '')
        project_countries = _split_csv_values(request.GET.get('project_countries', ''))

        # Get thresholds from CMS settings
        try:
            cluster_settings = MultimodalClusterSettings.load(request_or_site=request)
            warning_threshold = cluster_settings.warning_threshold
            alarm_threshold = cluster_settings.alarm_threshold
            emergency_threshold = cluster_settings.emergency_threshold
        except Exception:
            # Default thresholds if settings not configured
            warning_threshold = 150.0
            alarm_threshold = 300.0
            emergency_threshold = 450.0

        # Build filter SQL based on filter mode
        filter_sql = ""
        if filter_mode == 'active':
            filter_sql = f"WHERE daily_avg >= {warning_threshold}"
        elif filter_mode == 'alarm':
            filter_sql = f"WHERE daily_avg >= {alarm_threshold}"
        elif filter_mode == 'emergency':
            filter_sql = f"WHERE daily_avg >= {emergency_threshold}"

        with connection.cursor() as cursor:
            try:
                # Parse date or get latest
                if date_str:
                    try:
                        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
                        query_date_sql = "%s"
                        params = [date_obj]
                    except ValueError:
                        response = JsonResponse({
                            'error': 'Invalid date format. Use YYYY-MM-DD'
                        }, status=400)
                        response['Access-Control-Allow-Origin'] = '*'
                        return response
                else:
                    query_date_sql = "(SELECT MAX(data_date) FROM gha.multimodal_forecasts)"
                    params = []

                clip_geom_ewkt = _resolve_filter_geometry_ewkt(
                    cursor,
                    country_name=country_name,
                    region_name=region_name,
                    district_name=district_name,
                    project_countries=project_countries,
                )

                point_filters = []
                point_filter_params = []
                if scope_mode == 'whca':
                    point_filters.append(WHCA_SCOPE_SQL_CONDITION)
                if clip_geom_ewkt:
                    point_filters.append("ST_Within(cp.geom, ST_GeomFromEWKT(%s))")
                    point_filter_params.append(clip_geom_ewkt)

                point_where_sql = f"WHERE {' AND '.join(point_filters)}" if point_filters else ""
                query_params = params + point_filter_params

                # Query using normalized tables - builds GeoJSON from control points and forecasts
                cursor.execute(f"""
                    WITH query_params AS (
                        SELECT {query_date_sql}::date as query_date
                    ),
                    first_forecast AS (
                        SELECT MIN(forecast_date) as forecast_date
                        FROM gha.multimodal_forecasts mf, query_params qp
                        WHERE mf.data_date = qp.query_date
                          AND mf.forecast_date >= qp.query_date
                    ),
                    point_data AS (
                        SELECT
                            cp.point_id,
                            cp.zone,
                            cp.gridcode,
                            cp.admin_name,
                            cp.country_code,
                            cp.whca_selected,
                            cp.hybas_id,
                            cp.geom,
                            f.data_date,
                            f.forecast_date,
                            f.daily_avg,
                            f.daily_max,
                            f.daily_min,
                            f.geosfm,
                            f.floodproof,
                            f.mike_hydro_rfe,
                            f.mike_hydro_chirp,
                            f.mike_hydro_imerg,
                            -- Get all forecasts for this point as JSON array
                            COALESCE((
                                SELECT json_agg(json_build_object(
                                    'date', fc.forecast_date,
                                    'daily_avg', fc.daily_avg,
                                    'daily_max', fc.daily_max,
                                    'daily_min', fc.daily_min,
                                    'GeoSFM', fc.geosfm,
                                    'Floodproof', fc.floodproof,
                                    'Mike_Hydro_RFE', fc.mike_hydro_rfe,
                                    'Mike_Hydro_CHIRP', fc.mike_hydro_chirp,
                                    'Mike_Hydro_IMERG', fc.mike_hydro_imerg
                                ) ORDER BY fc.forecast_date)
                                FROM gha.multimodal_forecasts fc, query_params qp
                                WHERE fc.point_id = cp.point_id
                                  AND fc.data_date = qp.query_date
                            ), '[]'::json) as forecasts
                        FROM gha.multimodal_control_points cp
                        CROSS JOIN query_params qp
                        CROSS JOIN first_forecast ff
                        LEFT JOIN gha.multimodal_forecasts f
                            ON f.point_id = cp.point_id
                            AND f.data_date = qp.query_date
                            AND f.forecast_date = ff.forecast_date
                        {point_where_sql}
                    )
                    SELECT json_build_object(
                        'type', 'FeatureCollection',
                        'features', COALESCE(json_agg(
                            json_build_object(
                                'type', 'Feature',
                                'geometry', ST_AsGeoJSON(geom)::json,
                                'properties', json_build_object(
                                    'point_id', point_id,
                                    'zone', zone,
                                    'gridcode', gridcode,
                                    'admin_name', admin_name,
                                    'country_code', country_code,
                                    'whca_selected', whca_selected,
                                    'hybas_id', hybas_id,
                                    'data_date', data_date::text,
                                    'forecast_date', forecast_date::text,
                                    'daily_avg', daily_avg,
                                    'daily_max', daily_max,
                                    'daily_min', daily_min,
                                    'geosfm', geosfm,
                                    'floodproof', floodproof,
                                    'mike_hydro_rfe', mike_hydro_rfe,
                                    'mike_hydro_chirp', mike_hydro_chirp,
                                    'mike_hydro_imerg', mike_hydro_imerg,
                                    'forecasts', forecasts
                                )
                            )
                        ), '[]'::json)
                    ) as geojson
                    FROM point_data
                    {filter_sql}
                """, query_params)

                result = cursor.fetchone()

                if not result or not result[0]:
                    response = JsonResponse({
                        'error': 'No forecast data available'
                    }, status=404)
                    response['Access-Control-Allow-Origin'] = '*'
                    return response

                # The result is already a dict from PostgreSQL JSON
                geojson = result[0]
                # If it's a string, parse it to dict
                if isinstance(geojson, str):
                    geojson = json_module.loads(geojson)

            except Exception as e:
                response = JsonResponse({
                    'error': f'Query failed: {str(e)}'
                }, status=500)
                response['Access-Control-Allow-Origin'] = '*'
                return response

        response = JsonResponse(geojson, safe=False)

        # Add CORS headers
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        response['Access-Control-Allow-Headers'] = 'Content-Type'

        return response


class MultimodalClusteredGeoJSONView(View):
    """API endpoint to get clustered multimodal forecast GeoJSON data based on zoom level

    Now uses normalized gha.multimodal_control_points and gha.multimodal_forecasts tables.
    """

    def get(self, request):
        from django.db import connection
        import json
        from datetime import datetime

        # Get zoom level parameter (determines clustering granularity)
        zoom = int(request.GET.get('zoom', 5))

        # Get date parameter (defaults to latest available)
        date_str = request.GET.get('date')

        # Calculate grid size based on zoom level
        # Higher zoom = smaller grid = more detail
        # At zoom 0, grid is ~10 degrees; at zoom 12, grid is ~0.01 degrees
        grid_size = 10 / (2 ** zoom)
        # Minimum grid size to prevent too many points
        grid_size = max(grid_size, 0.01)

        with connection.cursor() as cursor:
            try:
                # Build date filter based on parameter
                if date_str:
                    try:
                        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
                        query_date_sql = "%s"
                        params = [date_obj, grid_size, grid_size]
                    except ValueError:
                        response = JsonResponse({
                            'error': 'Invalid date format. Use YYYY-MM-DD'
                        }, status=400)
                        response['Access-Control-Allow-Origin'] = '*'
                        return response
                else:
                    query_date_sql = "(SELECT MAX(data_date) FROM gha.multimodal_forecasts)"
                    params = [grid_size, grid_size]

                # Use PostgreSQL to cluster points using ST_SnapToGrid
                # Now queries from normalized tables
                cursor.execute(f"""
                    WITH query_params AS (
                        SELECT {query_date_sql}::date as query_date
                    ),
                    first_forecast AS (
                        SELECT MIN(forecast_date) as forecast_date
                        FROM gha.multimodal_forecasts mf, query_params qp
                        WHERE mf.data_date = qp.query_date
                          AND mf.forecast_date >= qp.query_date
                    ),
                    points AS (
                        SELECT
                            ST_X(cp.geom) AS lon,
                            ST_Y(cp.geom) AS lat,
                            f.daily_avg,
                            f.daily_max
                        FROM gha.multimodal_control_points cp
                        CROSS JOIN query_params qp
                        CROSS JOIN first_forecast ff
                        LEFT JOIN gha.multimodal_forecasts f
                            ON f.point_id = cp.point_id
                            AND f.data_date = qp.query_date
                            AND f.forecast_date = ff.forecast_date
                    ),
                    clustered AS (
                        SELECT
                            ST_SnapToGrid(ST_MakePoint(lon, lat), %s) AS cluster_geom,
                            COUNT(*) AS point_count,
                            AVG(lon) AS avg_lon,
                            AVG(lat) AS avg_lat,
                            MAX(daily_avg) AS max_daily_avg,
                            MAX(daily_max) AS max_daily_max
                        FROM points
                        GROUP BY ST_SnapToGrid(ST_MakePoint(lon, lat), %s)
                    )
                    SELECT json_build_object(
                        'type', 'FeatureCollection',
                        'features', COALESCE(json_agg(
                            CASE
                                WHEN point_count = 1 THEN
                                    json_build_object(
                                        'type', 'Feature',
                                        'geometry', json_build_object(
                                            'type', 'Point',
                                            'coordinates', json_build_array(avg_lon, avg_lat)
                                        ),
                                        'properties', json_build_object(
                                            'point_count', 1,
                                            'daily_avg', max_daily_avg,
                                            'daily_max', max_daily_max
                                        )
                                    )
                                ELSE
                                    json_build_object(
                                        'type', 'Feature',
                                        'geometry', json_build_object(
                                            'type', 'Point',
                                            'coordinates', json_build_array(avg_lon, avg_lat)
                                        ),
                                        'properties', json_build_object(
                                            'cluster', true,
                                            'point_count', point_count,
                                            'point_count_abbreviated',
                                                CASE
                                                    WHEN point_count >= 1000 THEN CONCAT(ROUND(point_count::numeric / 1000, 1), 'k')
                                                    ELSE point_count::text
                                                END,
                                            'max_daily_avg', max_daily_avg,
                                            'max_daily_max', max_daily_max
                                        )
                                    )
                            END
                        ), '[]'::json)
                    ) as geojson
                    FROM clustered
                """, params)

                result = cursor.fetchone()

                if not result or not result[0]:
                    response = JsonResponse({
                        'type': 'FeatureCollection',
                        'features': []
                    })
                    response['Access-Control-Allow-Origin'] = '*'
                    return response

                geojson = result[0]

            except Exception as e:
                response = JsonResponse({
                    'error': f'Query failed: {str(e)}'
                }, status=500)
                response['Access-Control-Allow-Origin'] = '*'
                return response

        response = JsonResponse(geojson, safe=False)

        # Add CORS headers
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        response['Access-Control-Allow-Headers'] = 'Content-Type'

        return response


class MultimodalAvailableDatesView(View):
    """API endpoint to get available dates for multimodal forecast data"""

    def get(self, request):
        from django.db import connection

        with connection.cursor() as cursor:
            try:
                cursor.execute("""
                    SELECT DISTINCT data_date
                    FROM gha.multimodal_forecasts
                    ORDER BY data_date DESC
                """)
                rows = cursor.fetchall()

                if not rows:
                    response = JsonResponse({
                        'timestamps': []
                    })
                    response['Access-Control-Allow-Origin'] = '*'
                    return response

                # Format dates as ISO strings for the frontend
                timestamps = [row[0].strftime('%Y-%m-%d') for row in rows]

            except Exception as e:
                response = JsonResponse({
                    'error': f'Query failed: {str(e)}'
                }, status=500)
                response['Access-Control-Allow-Origin'] = '*'
                return response

        response = JsonResponse({
            'timestamps': timestamps
        })

        # Add CORS headers
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        response['Access-Control-Allow-Headers'] = 'Content-Type'

        return response


class BaseModularModelGeoJSONView(View):
    """Base GeoJSON API for model-specific views sourced from multimodal forecasts."""

    endpoint_path = "/api/v1/multimodal/geojson/"

    def _current_value_sql(self, alias):
        raise NotImplementedError

    def _forecast_object_sql(self):
        raise NotImplementedError

    def get(self, request):
        from django.db import connection
        import json as json_module

        date_str = request.GET.get('date')
        filter_mode = request.GET.get('filter', 'all')
        scope_mode = _resolve_scope_mode(request)

        if scope_mode not in ('all', 'whca'):
            return _add_cors_headers(JsonResponse({'error': 'Invalid scope. Use all or whca'}, status=400))

        country_name = request.GET.get('country_name', '')
        region_name = request.GET.get('region_name', '')
        district_name = request.GET.get('district_name', '')
        project_countries = _split_csv_values(request.GET.get('project_countries', ''))

        warning_threshold, alarm_threshold, emergency_threshold = _get_multimodal_thresholds(request)

        filter_sql = ""
        if filter_mode == 'active':
            filter_sql = f"WHERE daily_avg >= {warning_threshold}"
        elif filter_mode == 'alarm':
            filter_sql = f"WHERE daily_avg >= {alarm_threshold}"
        elif filter_mode == 'emergency':
            filter_sql = f"WHERE daily_avg >= {emergency_threshold}"

        query_date, date_error = _parse_query_date(date_str)
        if date_error:
            return date_error

        if query_date:
            query_date_sql = "%s"
            params = [query_date]
        else:
            query_date_sql = "(SELECT MAX(data_date) FROM gha.multimodal_forecasts)"
            params = []

        current_value_mf = self._current_value_sql("mf")
        current_value_f = self._current_value_sql("f")
        current_value_fc = self._current_value_sql("fc")
        forecast_object_sql = self._forecast_object_sql()

        with connection.cursor() as cursor:
            try:
                clip_geom_ewkt = _resolve_filter_geometry_ewkt(
                    cursor,
                    country_name=country_name,
                    region_name=region_name,
                    district_name=district_name,
                    project_countries=project_countries,
                )

                point_filters = []
                point_filter_params = []
                if scope_mode == 'whca':
                    point_filters.append(WHCA_SCOPE_SQL_CONDITION)
                if clip_geom_ewkt:
                    point_filters.append("ST_Within(cp.geom, ST_GeomFromEWKT(%s))")
                    point_filter_params.append(clip_geom_ewkt)

                point_where_sql = f"WHERE {' AND '.join(point_filters)}" if point_filters else ""
                query_params = params + point_filter_params

                cursor.execute(
                    f"""
                    WITH query_params AS (
                        SELECT {query_date_sql}::date AS query_date
                    ),
                    first_forecast AS (
                        SELECT
                            mf.point_id,
                            MIN(mf.forecast_date) AS forecast_date
                        FROM gha.multimodal_forecasts mf, query_params qp
                        WHERE mf.data_date = qp.query_date
                          AND mf.forecast_date >= qp.query_date
                          AND {current_value_mf} IS NOT NULL
                        GROUP BY mf.point_id
                    ),
                    point_data AS (
                        SELECT
                            cp.point_id,
                            cp.zone,
                            cp.gridcode,
                            cp.admin_name,
                            cp.country_code,
                            cp.whca_selected,
                            cp.hybas_id,
                            cp.geom,
                            f.data_date,
                            f.forecast_date,
                            {current_value_f} AS daily_avg,
                            f.geosfm,
                            f.floodproof,
                            f.mike_hydro_rfe,
                            f.mike_hydro_chirp,
                            f.mike_hydro_imerg,
                            COALESCE((
                                SELECT json_agg({forecast_object_sql} ORDER BY fc.forecast_date)
                                FROM gha.multimodal_forecasts fc, query_params qp
                                WHERE fc.point_id = cp.point_id
                                  AND fc.data_date = qp.query_date
                                  AND {current_value_fc} IS NOT NULL
                            ), '[]'::json) AS forecasts
                        FROM gha.multimodal_control_points cp
                        JOIN first_forecast ff ON ff.point_id = cp.point_id
                        CROSS JOIN query_params qp
                        LEFT JOIN gha.multimodal_forecasts f
                            ON f.point_id = cp.point_id
                            AND f.data_date = qp.query_date
                            AND f.forecast_date = ff.forecast_date
                        {point_where_sql}
                    )
                    SELECT json_build_object(
                        'type', 'FeatureCollection',
                        'features', COALESCE(json_agg(
                            json_build_object(
                                'type', 'Feature',
                                'geometry', ST_AsGeoJSON(geom)::json,
                                'properties', json_build_object(
                                    'point_id', point_id,
                                    'zone', zone,
                                    'gridcode', gridcode,
                                    'admin_name', admin_name,
                                    'country_code', country_code,
                                    'whca_selected', whca_selected,
                                    'hybas_id', hybas_id,
                                    'data_date', data_date::text,
                                    'forecast_date', forecast_date::text,
                                    'daily_avg', daily_avg,
                                    'geosfm', geosfm,
                                    'floodproof', floodproof,
                                    'mike_hydro_rfe', mike_hydro_rfe,
                                    'mike_hydro_chirp', mike_hydro_chirp,
                                    'mike_hydro_imerg', mike_hydro_imerg,
                                    'threshold_alert', {warning_threshold},
                                    'threshold_alarm', {alarm_threshold},
                                    'threshold_emergency', {emergency_threshold},
                                    'alert_level', CASE
                                        WHEN daily_avg >= {emergency_threshold} THEN 'emergency'
                                        WHEN daily_avg >= {alarm_threshold} THEN 'alarm'
                                        WHEN daily_avg >= {warning_threshold} THEN 'warning'
                                        ELSE 'normal'
                                    END,
                                    'data_endpoint', '{self.endpoint_path}',
                                    'forecasts', forecasts
                                )
                            )
                        ), '[]'::json)
                    ) AS geojson
                    FROM point_data
                    {filter_sql}
                    """,
                    query_params,
                )
                result = cursor.fetchone()
                geojson = result[0] if result and result[0] else {'type': 'FeatureCollection', 'features': []}
                if isinstance(geojson, str):
                    geojson = json_module.loads(geojson)
            except Exception as e:
                return _add_cors_headers(JsonResponse({'error': f'Query failed: {str(e)}'}, status=500))

        return _add_cors_headers(JsonResponse(geojson, safe=False))


class GeoSFMGeoJSONView(BaseModularModelGeoJSONView):
    endpoint_path = "/api/v1/models/geosfm/geojson/"

    def _current_value_sql(self, alias):
        return f"{alias}.geosfm"

    def _forecast_object_sql(self):
        return """json_build_object(
            'date', fc.forecast_date,
            'daily_avg', fc.geosfm,
            'GeoSFM', fc.geosfm
        )"""


class MikeHydroGeoJSONView(BaseModularModelGeoJSONView):
    endpoint_path = "/api/v1/models/mike-hydro/geojson/"

    def _current_value_sql(self, alias):
        return (
            f"(SELECT MAX(v) FROM (VALUES ({alias}.mike_hydro_rfe), "
            f"({alias}.mike_hydro_chirp), ({alias}.mike_hydro_imerg)) AS vals(v))"
        )

    def _forecast_object_sql(self):
        return """json_build_object(
            'date', fc.forecast_date,
            'daily_avg', (
                SELECT MAX(v) FROM (VALUES (fc.mike_hydro_rfe), (fc.mike_hydro_chirp), (fc.mike_hydro_imerg)) AS vals(v)
            ),
            'Mike_Hydro_RFE', fc.mike_hydro_rfe,
            'Mike_Hydro_CHIRP', fc.mike_hydro_chirp,
            'Mike_Hydro_IMERG', fc.mike_hydro_imerg
        )"""


class FloodproofGeoJSONView(BaseModularModelGeoJSONView):
    """Floodproof model-only view sourced from gha.multimodal_forecasts.floodproof."""

    endpoint_path = "/api/v1/models/floodproof/geojson/"

    def _current_value_sql(self, alias):
        return f"{alias}.floodproof"

    def _forecast_object_sql(self):
        return """json_build_object(
            'date', fc.forecast_date,
            'daily_avg', fc.floodproof,
            'Floodproof', fc.floodproof
        )"""


class GoogleFloodGeoJSONView(View):
    """GeoJSON endpoint backed by synced Google Flood API rows in gha.google_flood_points_latest."""

    endpoint_path = "/api/v1/google-flood/geojson/"

    def get(self, request):
        from django.db import connection
        import json as json_module

        date_str = request.GET.get('date')
        filter_mode = request.GET.get('filter', 'all')
        scope_mode = _resolve_scope_mode(request)
        confidence_mode = request.GET.get('confidence', 'high').strip().lower()
        extended_coverage_param = request.GET.get('extended_coverage', 'false').strip().lower()
        country_name = request.GET.get('country_name', '')
        region_name = request.GET.get('region_name', '')
        district_name = request.GET.get('district_name', '')
        project_countries = _split_csv_values(request.GET.get('project_countries', ''))

        extended_coverage_enabled = extended_coverage_param in ('1', 'true', 'yes', 'on')

        if scope_mode not in ('all', 'whca'):
            return _add_cors_headers(JsonResponse({'error': 'Invalid scope. Use all or whca'}, status=400))
        if confidence_mode not in ('all', 'high', 'low'):
            # Be resilient to unresolved template placeholders (e.g. {{confidence}})
            # and fall back to the default high-confidence view.
            confidence_mode = 'high'

        # Extended coverage mirrors Google Flood Hub behavior by including
        # lower-confidence gauges in addition to the default high-confidence set.
        if extended_coverage_enabled:
            confidence_mode = 'all'

        query_date, date_error = _parse_query_date(date_str)
        if date_error:
            return date_error

        with connection.cursor() as cursor:
            try:
                cursor.execute("SELECT to_regclass('gha.google_flood_points_latest')")
                table_exists = cursor.fetchone()[0] is not None
                if not table_exists:
                    return _add_cors_headers(JsonResponse({'type': 'FeatureCollection', 'features': []}, safe=False))

                if query_date:
                    query_date_sql = "%s"
                    params = [query_date]
                else:
                    query_date_sql = "(SELECT MAX(data_date) FROM gha.google_flood_points_latest)"
                    params = []

                clip_geom_ewkt = _resolve_filter_geometry_ewkt(
                    cursor,
                    country_name=country_name,
                    region_name=region_name,
                    district_name=district_name,
                    project_countries=project_countries,
                )

                scope_sql = ""
                if scope_mode == 'whca':
                    scope_sql = (
                        "AND UPPER(COALESCE(NULLIF(g.country_code, ''), NULLIF(g.region_code, ''), '')) "
                        "IN ('SD','SS','UG','ET','RW')"
                    )

                filter_sql = ""
                if filter_mode == 'active':
                    filter_sql = "WHERE alert_level != 'normal'"
                elif filter_mode == 'alarm':
                    filter_sql = "WHERE alert_level IN ('alarm', 'emergency')"
                elif filter_mode == 'emergency':
                    filter_sql = "WHERE alert_level = 'emergency'"

                confidence_sql = ""
                if confidence_mode == 'high':
                    confidence_sql = "AND UPPER(COALESCE(g.confidence_level, '')) = 'HIGH'"
                elif confidence_mode == 'low':
                    confidence_sql = "AND UPPER(COALESCE(g.confidence_level, '')) = 'LOW'"

                spatial_clip_sql = ""
                if clip_geom_ewkt:
                    spatial_clip_sql = "AND ST_Within(g.geom, ST_GeomFromEWKT(%s))"
                    params = params + [clip_geom_ewkt]

                cursor.execute(
                    f"""
                    WITH query_params AS (
                        SELECT {query_date_sql}::date AS query_date
                    ),
                    point_data AS (
                        SELECT
                            g.gauge_id,
                            COALESCE(NULLIF(g.point_id, ''), g.gauge_id) AS point_id,
                            COALESCE(NULLIF(g.admin_name, ''), NULLIF(g.site_name, ''), g.gauge_id) AS admin_name,
                            g.hybas_id,
                            COALESCE(NULLIF(g.country_code, ''), NULLIF(g.region_code, '')) AS country_code,
                            g.region_code,
                            g.data_date,
                            g.latest_issued_time AS forecast_date,
                            g.daily_avg,
                            g.daily_max,
                            g.daily_min,
                            g.threshold_alert,
                            g.threshold_alarm,
                            g.threshold_emergency,
                            g.latest_severity,
                            g.latest_forecast_trend,
                            g.confidence_level,
                            g.confidence_score,
                            g.quality_verified,
                            g.model_quality_verified,
                            g.status_quality_verified,
                            COALESCE(g.forecasts_json, '[]'::jsonb) AS forecasts,
                            CASE
                                -- Prefer explicit Google severity classes when provided.
                                WHEN UPPER(COALESCE(g.latest_severity, '')) IN ('EXTREME', 'EXTREME_FLOODING', 'MAJOR_FLOODING') THEN 'emergency'
                                WHEN UPPER(COALESCE(g.latest_severity, '')) IN ('SEVERE', 'DANGER', 'MODERATE_FLOODING') THEN 'alarm'
                                WHEN UPPER(COALESCE(g.latest_severity, '')) IN ('WARNING', 'WATCH', 'MINOR_FLOODING', 'ALERT') THEN 'warning'

                                -- Fallback to threshold-based classification using forecast discharge.
                                WHEN g.daily_max IS NOT NULL AND g.threshold_emergency IS NOT NULL AND g.daily_max >= g.threshold_emergency THEN 'emergency'
                                WHEN g.daily_max IS NOT NULL AND g.threshold_alarm IS NOT NULL AND g.daily_max >= g.threshold_alarm THEN 'alarm'
                                WHEN g.daily_max IS NOT NULL AND g.threshold_alert IS NOT NULL AND g.daily_max >= g.threshold_alert THEN 'warning'

                                WHEN g.daily_avg IS NOT NULL AND g.threshold_emergency IS NOT NULL AND g.daily_avg >= g.threshold_emergency THEN 'emergency'
                                WHEN g.daily_avg IS NOT NULL AND g.threshold_alarm IS NOT NULL AND g.daily_avg >= g.threshold_alarm THEN 'alarm'
                                WHEN g.daily_avg IS NOT NULL AND g.threshold_alert IS NOT NULL AND g.daily_avg >= g.threshold_alert THEN 'warning'
                                ELSE 'normal'
                            END AS alert_level,
                            g.geom
                        FROM gha.google_flood_points_latest g
                        CROSS JOIN query_params qp
                        WHERE (qp.query_date IS NULL OR g.data_date = qp.query_date)
                          AND g.geom IS NOT NULL
                          {scope_sql}
                          {confidence_sql}
                          {spatial_clip_sql}
                    )
                    SELECT json_build_object(
                        'type', 'FeatureCollection',
                        'features', COALESCE(json_agg(
                            json_build_object(
                                'type', 'Feature',
                                'geometry', ST_AsGeoJSON(geom)::json,
                                'properties', json_build_object(
                                    'gauge_id', gauge_id,
                                    'point_id', point_id,
                                    'admin_name', admin_name,
                                    'hybas_id', hybas_id,
                                    'country_code', country_code,
                                    'region_code', region_code,
                                    'data_date', data_date::text,
                                    'forecast_date', forecast_date::text,
                                    'daily_avg', daily_avg,
                                    'daily_max', daily_max,
                                    'daily_min', daily_min,
                                    'threshold_alert', threshold_alert,
                                    'threshold_alarm', threshold_alarm,
                                    'threshold_emergency', threshold_emergency,
                                    'google_flood_severity', latest_severity,
                                    'forecast_trend', latest_forecast_trend,
                                    'confidence_level', confidence_level,
                                    'confidence_score', confidence_score,
                                    'quality_verified', quality_verified,
                                    'model_quality_verified', model_quality_verified,
                                    'status_quality_verified', status_quality_verified,
                                    'extended_coverage', CASE
                                        WHEN UPPER(COALESCE(confidence_level, '')) = 'LOW' THEN TRUE
                                        ELSE FALSE
                                    END,
                                    'alert_level', alert_level,
                                    'data_endpoint', '{self.endpoint_path}',
                                    'forecasts', forecasts
                                )
                            )
                        ), '[]'::json)
                    ) AS geojson
                    FROM point_data
                    {filter_sql}
                    """,
                    params,
                )
                result = cursor.fetchone()
                geojson = result[0] if result and result[0] else {'type': 'FeatureCollection', 'features': []}
                if isinstance(geojson, str):
                    geojson = json_module.loads(geojson)
            except Exception as e:
                return _add_cors_headers(JsonResponse({'error': f'Query failed: {str(e)}'}, status=500))

        return _add_cors_headers(JsonResponse(geojson, safe=False))


class GoogleFloodAvailableDatesView(View):
    """Available synced dates for Google Flood API rows."""

    def get(self, request):
        from django.db import connection

        with connection.cursor() as cursor:
            try:
                cursor.execute("SELECT to_regclass('gha.google_flood_points_latest')")
                table_exists = cursor.fetchone()[0] is not None
                if not table_exists:
                    return _add_cors_headers(JsonResponse({'timestamps': []}))

                cursor.execute("""
                    SELECT DISTINCT data_date
                    FROM gha.google_flood_points_latest
                    WHERE data_date IS NOT NULL
                    ORDER BY data_date DESC
                """)
                rows = cursor.fetchall()
                timestamps = [row[0].strftime('%Y-%m-%d') for row in rows]
            except Exception as e:
                return _add_cors_headers(JsonResponse({'error': f'Query failed: {str(e)}'}, status=500))

        return _add_cors_headers(JsonResponse({'timestamps': timestamps}))


# =============================================================================
# FloodWatch Custom: Admin Boundary API for filter dropdowns
# Uses gha.admin0, admin1, admin2 tables from GHA schema
# =============================================================================
class AdminBoundaryView(View):
    """API endpoint to get admin boundaries for filter dropdowns"""

    def get(self, request):
        from django.db import connection

        # Get parameters
        admin_level = request.GET.get('admin_level')  # None=countries, 0=regions, 1=districts
        unit_id = request.GET.get('unit_id', '')  # Parent unit code (country name or region name)
        with_bbox = request.GET.get('with_bbox', 'false').lower() == 'true'

        with connection.cursor() as cursor:
            try:
                if admin_level is None:
                    # Return all countries from gha.admin0
                    if with_bbox:
                        cursor.execute("""
                            SELECT country as code, country as name,
                                   ST_XMin(ST_Envelope(geom)) as left,
                                   ST_YMin(ST_Envelope(geom)) as bottom,
                                   ST_XMax(ST_Envelope(geom)) as right,
                                   ST_YMax(ST_Envelope(geom)) as top
                            FROM gha.admin0
                            WHERE country IS NOT NULL
                              AND country != ''
                              AND LOWER(TRIM(country)) != 'eritrea'
                            ORDER BY country
                        """)
                    else:
                        cursor.execute("""
                            SELECT country as code, country as name
                            FROM gha.admin0
                            WHERE country IS NOT NULL
                              AND country != ''
                              AND LOWER(TRIM(country)) != 'eritrea'
                            ORDER BY country
                        """)
                elif admin_level == '0':
                    # Return admin1 regions within a country (name_1 is region name)
                    if with_bbox:
                        cursor.execute("""
                            SELECT name_1 as code, name_1 as name,
                                   ST_XMin(ST_Envelope(geom)) as left,
                                   ST_YMin(ST_Envelope(geom)) as bottom,
                                   ST_XMax(ST_Envelope(geom)) as right,
                                   ST_YMax(ST_Envelope(geom)) as top
                            FROM gha.admin1
                            WHERE country = %s
                              AND name_1 IS NOT NULL
                              AND name_1 != ''
                              AND LOWER(TRIM(country)) != 'eritrea'
                            ORDER BY name_1
                        """, [unit_id])
                    else:
                        cursor.execute("""
                            SELECT name_1 as code, name_1 as name
                            FROM gha.admin1
                            WHERE country = %s
                              AND name_1 IS NOT NULL
                              AND name_1 != ''
                              AND LOWER(TRIM(country)) != 'eritrea'
                            ORDER BY name_1
                        """, [unit_id])
                elif admin_level == '1':
                    # Return admin2 districts within a region (name_2 is district name)
                    # unit_id is the region name (name_1), country_id is optional for filtering
                    country_id = request.GET.get('country_id', '')
                    if with_bbox:
                        if country_id:
                            cursor.execute("""
                                SELECT name_2 as code, name_2 as name,
                                       ST_XMin(ST_Envelope(geom)) as left,
                                       ST_YMin(ST_Envelope(geom)) as bottom,
                                       ST_XMax(ST_Envelope(geom)) as right,
                                       ST_YMax(ST_Envelope(geom)) as top
                                FROM gha.admin2
                                WHERE country = %s
                                  AND name_1 = %s
                                  AND name_2 IS NOT NULL
                                  AND name_2 != ''
                                  AND LOWER(TRIM(country)) != 'eritrea'
                                ORDER BY name_2
                            """, [country_id, unit_id])
                        else:
                            cursor.execute("""
                                SELECT name_2 as code, name_2 as name,
                                       ST_XMin(ST_Envelope(geom)) as left,
                                       ST_YMin(ST_Envelope(geom)) as bottom,
                                       ST_XMax(ST_Envelope(geom)) as right,
                                       ST_YMax(ST_Envelope(geom)) as top
                                FROM gha.admin2
                                WHERE name_1 = %s
                                  AND name_2 IS NOT NULL
                                  AND name_2 != ''
                                  AND LOWER(TRIM(country)) != 'eritrea'
                                ORDER BY name_2
                            """, [unit_id])
                    else:
                        if country_id:
                            cursor.execute("""
                                SELECT name_2 as code, name_2 as name
                                FROM gha.admin2
                                WHERE country = %s
                                  AND name_1 = %s
                                  AND name_2 IS NOT NULL
                                  AND name_2 != ''
                                  AND LOWER(TRIM(country)) != 'eritrea'
                                ORDER BY name_2
                            """, [country_id, unit_id])
                        else:
                            cursor.execute("""
                                SELECT name_2 as code, name_2 as name
                                FROM gha.admin2
                                WHERE name_1 = %s
                                  AND name_2 IS NOT NULL
                                  AND name_2 != ''
                                  AND LOWER(TRIM(country)) != 'eritrea'
                                ORDER BY name_2
                            """, [unit_id])
                else:
                    response = JsonResponse({'error': 'Invalid admin_level'}, status=400)
                    response['Access-Control-Allow-Origin'] = '*'
                    return response

                columns = [col[0] for col in cursor.description]
                results = []
                for row in cursor.fetchall():
                    item = dict(zip(columns, row))
                    if with_bbox and 'left' in item:
                        item['bbox'] = {
                            'left': float(item.pop('left')) if item.get('left') else None,
                            'bottom': float(item.pop('bottom')) if item.get('bottom') else None,
                            'right': float(item.pop('right')) if item.get('right') else None,
                            'top': float(item.pop('top')) if item.get('top') else None
                        }
                    results.append(item)

            except Exception as e:
                response = JsonResponse({
                    'error': f'Query failed: {str(e)}'
                }, status=500)
                response['Access-Control-Allow-Origin'] = '*'
                return response

        response = JsonResponse(results, safe=False)
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        response['Access-Control-Allow-Headers'] = 'Content-Type'

        return response


# =============================================================================
# FloodProofs Impact Data API - Returns available forecast dates for impact layers
# =============================================================================
class ImpactForecastDatesView(View):
    """API endpoint to get available FloodProofs impact forecast dates"""

    def get(self, request):
        from django.db import connection

        # Get optional impact_type parameter
        impact_type = request.GET.get('impact_type')

        with connection.cursor() as cursor:
            try:
                if impact_type:
                    cursor.execute("""
                        SELECT DISTINCT forecast_date
                        FROM public.floodproofs_impacts
                        WHERE impact_type = %s
                        ORDER BY forecast_date DESC
                    """, [impact_type])
                else:
                    cursor.execute("""
                        SELECT DISTINCT forecast_date
                        FROM public.floodproofs_impacts
                        ORDER BY forecast_date DESC
                    """)

                dates = [row[0].strftime('%Y-%m-%d') for row in cursor.fetchall()]

            except Exception as e:
                response = JsonResponse({
                    'error': f'Query failed: {str(e)}'
                }, status=500)
                response['Access-Control-Allow-Origin'] = '*'
                return response

        response = JsonResponse({
            'timestamps': dates,
            'count': len(dates)
        })

        # Add CORS headers
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        response['Access-Control-Allow-Headers'] = 'Content-Type'

        return response


# =============================================================================
# Proxy view for datasets - handles mapviewer requests without /api/ prefix
# =============================================================================
class DatasetsProxyView(View):
    """Proxy view to redirect /datasets/ to /api/datasets/"""

    def get(self, request, path=''):
        from django.http import HttpResponseRedirect

        # Build the target URL with the path suffix and query string
        target_url = f'/api/datasets/{path}'
        if request.GET:
            target_url += '?' + request.GET.urlencode()

        return HttpResponseRedirect(target_url)


# =============================================================================
# FloodWatch Custom: Basin Geometry API
# Returns GeoJSON for a basin given hybas_id from hydrobasins_lev06
# Used for auto-loading basin boundary when clicking on forecast points
# =============================================================================
class BasinGeometryView(View):
    """API endpoint to get basin geometry by hybas_id"""

    def get(self, request, hybas_id=None):
        from django.db import connection
        import json

        if not hybas_id:
            response = JsonResponse({'error': 'hybas_id is required'}, status=400)
            response['Access-Control-Allow-Origin'] = '*'
            return response

        with connection.cursor() as cursor:
            try:
                cursor.execute("""
                    SELECT
                        hybas_id,
                        main_bas,
                        sub_area,
                        up_area,
                        ST_AsGeoJSON(geom)::json as geometry,
                        ST_XMin(ST_Envelope(geom)) as bbox_left,
                        ST_YMin(ST_Envelope(geom)) as bbox_bottom,
                        ST_XMax(ST_Envelope(geom)) as bbox_right,
                        ST_YMax(ST_Envelope(geom)) as bbox_top
                    FROM gha.hydrobasins_lev06
                    WHERE hybas_id = %s
                    LIMIT 1
                """, [hybas_id])

                row = cursor.fetchone()

                if not row:
                    response = JsonResponse({'error': 'Basin not found'}, status=404)
                    response['Access-Control-Allow-Origin'] = '*'
                    return response

                # Build GeoJSON Feature
                feature = {
                    'type': 'Feature',
                    'geometry': row[4],
                    'properties': {
                        'hybas_id': int(row[0]) if row[0] else None,
                        'main_bas': int(row[1]) if row[1] else None,
                        'sub_area_km2': float(row[2]) if row[2] else None,
                        'upstream_area_km2': float(row[3]) if row[3] else None,
                    },
                    'bbox': [
                        float(row[5]) if row[5] else None,
                        float(row[6]) if row[6] else None,
                        float(row[7]) if row[7] else None,
                        float(row[8]) if row[8] else None,
                    ]
                }

            except Exception as e:
                response = JsonResponse({
                    'error': f'Query failed: {str(e)}'
                }, status=500)
                response['Access-Control-Allow-Origin'] = '*'
                return response

        response = JsonResponse(feature, safe=False)
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        response['Access-Control-Allow-Headers'] = 'Content-Type'

        return response


# =============================================================================
# FloodWatch Custom: Grid Cells API
# Returns grid cells for a given country/region for filtering
# =============================================================================
class GridCellsView(View):
    """API endpoint to get grid cells for a country/region"""

    def get(self, request):
        from django.db import connection

        country = request.GET.get('country')
        region = request.GET.get('region')

        if not country or not region:
            response = JsonResponse({'error': 'country and region are required'}, status=400)
            response['Access-Control-Allow-Origin'] = '*'
            return response

        with connection.cursor() as cursor:
            try:
                cursor.execute("""
                    SELECT
                        id,
                        xcol,
                        yrow,
                        centroid_lon,
                        centroid_lat,
                        ST_XMin(ST_Envelope(cell)) as bbox_left,
                        ST_YMin(ST_Envelope(cell)) as bbox_bottom,
                        ST_XMax(ST_Envelope(cell)) as bbox_right,
                        ST_YMax(ST_Envelope(cell)) as bbox_top
                    FROM gha.grid_025dd
                    WHERE LOWER(admin0_name) = LOWER(%s)
                      AND LOWER(admin1_name) = LOWER(%s)
                    ORDER BY yrow, xcol
                """, [country, region])

                columns = ['id', 'xcol', 'yrow', 'centroid_lon', 'centroid_lat',
                          'bbox_left', 'bbox_bottom', 'bbox_right', 'bbox_top']
                results = []
                for row in cursor.fetchall():
                    item = {
                        'id': row[0],
                        'xcol': row[1],
                        'yrow': row[2],
                        'centroid_lon': float(row[3]) if row[3] else None,
                        'centroid_lat': float(row[4]) if row[4] else None,
                        'bbox': [
                            float(row[5]) if row[5] else None,
                            float(row[6]) if row[6] else None,
                            float(row[7]) if row[7] else None,
                            float(row[8]) if row[8] else None,
                        ]
                    }
                    results.append(item)

            except Exception as e:
                response = JsonResponse({
                    'error': f'Query failed: {str(e)}'
                }, status=500)
                response['Access-Control-Allow-Origin'] = '*'
                return response

        response = JsonResponse(results, safe=False)
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        response['Access-Control-Allow-Headers'] = 'Content-Type'

        return response


# =============================================================================
# FloodWatch Custom: Country Summary with Bounds API for Homepage Mini-Map
# Returns per-country alert counts with bounding boxes for map zoom
# =============================================================================
class CountrySummaryWithBoundsView(View):
    """API endpoint to get country summary with bounds for homepage mini-map"""

    def get(self, request):
        from django.db import connection

        scope_mode = request.GET.get('scope', 'all').strip().lower()
        if scope_mode not in ('all', 'whca'):
            response = JsonResponse({'error': 'Invalid scope. Use all or whca'}, status=400)
            response['Access-Control-Allow-Origin'] = '*'
            return response

        scope_sql = ""
        if scope_mode == 'whca':
            scope_sql = f"WHERE {WHCA_SCOPE_SQL_CONDITION}"

        with connection.cursor() as cursor:
            try:
                # Get the latest available data date from multimodal forecasts
                cursor.execute("""
                    SELECT MAX(data_date) FROM gha.multimodal_forecasts
                """)
                latest_date = cursor.fetchone()[0]

                if not latest_date:
                    response = JsonResponse({
                        'error': 'No forecast data available'
                    }, status=404)
                    response['Access-Control-Allow-Origin'] = '*'
                    return response

                # Get CMS thresholds if available, else use defaults
                try:
                    from home.models import MultimodalClusterSettings
                    settings = MultimodalClusterSettings.load(request_or_site=request)
                    warning_threshold = settings.warning_threshold
                    alarm_threshold = settings.alarm_threshold
                    emergency_threshold = settings.emergency_threshold
                except Exception:
                    warning_threshold = 150.0
                    alarm_threshold = 300.0
                    emergency_threshold = 450.0

                # Query to get country summary with alert counts and bounds
                # Uses first forecast day (same basis as situation-summary).
                # Fast path derives ISO country code from admin_name prefix,
                # then falls back to spatial join only when prefix is missing/invalid.
                cursor.execute(f"""
                    WITH query_params AS (
                        SELECT %s::date as query_date
                    ),
                    first_forecast AS (
                        SELECT MIN(forecast_date) as forecast_date
                        FROM gha.multimodal_forecasts mf, query_params qp
                        WHERE mf.data_date = qp.query_date
                          AND mf.forecast_date >= qp.query_date
                    ),
                    point_data AS (
                        SELECT
                            cp.point_id,
                            cp.geom,
                            cp.admin_name,
                            COALESCE(f.daily_avg, 0) as daily_avg
                        FROM gha.multimodal_control_points cp
                        CROSS JOIN query_params qp
                        CROSS JOIN first_forecast ff
                        LEFT JOIN gha.multimodal_forecasts f
                            ON f.point_id = cp.point_id
                            AND f.data_date = qp.query_date
                            AND f.forecast_date = ff.forecast_date
                        {scope_sql}
                    ),
                    point_country AS (
                        SELECT
                            pd.point_id,
                            pd.daily_avg,
                            COALESCE(
                                CASE
                                    WHEN UPPER(SUBSTRING(COALESCE(pd.admin_name, '') FROM 1 FOR 2)) IN (
                                        'ET', 'KE', 'UG', 'SD', 'SS', 'TZ', 'RW', 'BI', 'SO', 'DJ'
                                    ) THEN UPPER(SUBSTRING(pd.admin_name FROM 1 FOR 2))
                                    ELSE NULL
                                END,
                                (
                                    SELECT CASE
                                        WHEN LOWER(TRIM(a0.country)) = 'ethiopia' THEN 'ET'
                                        WHEN LOWER(TRIM(a0.country)) = 'kenya' THEN 'KE'
                                        WHEN LOWER(TRIM(a0.country)) = 'uganda' THEN 'UG'
                                        WHEN LOWER(TRIM(a0.country)) = 'sudan' THEN 'SD'
                                        WHEN LOWER(TRIM(a0.country)) = 'south sudan' THEN 'SS'
                                        WHEN LOWER(TRIM(a0.country)) IN ('tanzania', 'zanzibar') THEN 'TZ'
                                        WHEN LOWER(TRIM(a0.country)) = 'rwanda' THEN 'RW'
                                        WHEN LOWER(TRIM(a0.country)) = 'burundi' THEN 'BI'
                                        WHEN LOWER(TRIM(a0.country)) = 'somalia' THEN 'SO'
                                        WHEN LOWER(TRIM(a0.country)) = 'djibouti' THEN 'DJ'
                                        ELSE 'UN'
                                    END
                                    FROM gha.admin0 a0
                                    WHERE a0.geom && pd.geom
                                      AND ST_Covers(a0.geom, pd.geom)
                                    LIMIT 1
                                ),
                                'UN'
                            ) as country_code
                        FROM point_data pd
                    ),
                    point_risk AS (
                        SELECT
                            point_id,
                            country_code,
                            daily_avg,
                            CASE
                                WHEN daily_avg >= %s THEN 'emergency'
                                WHEN daily_avg >= %s THEN 'alarm'
                                WHEN daily_avg >= %s THEN 'warning'
                                ELSE 'normal'
                            END as risk_level
                        FROM point_country
                    ),
                    country_agg AS (
                        SELECT
                            country_code,
                            SUM(CASE WHEN risk_level = 'emergency' THEN 1 ELSE 0 END) as emergency,
                            SUM(CASE WHEN risk_level = 'alarm' THEN 1 ELSE 0 END) as alarm,
                            SUM(CASE WHEN risk_level = 'warning' THEN 1 ELSE 0 END) as warning,
                            COUNT(*) as total_points,
                            -- Calculate severity score for sorting
                            SUM(CASE WHEN risk_level = 'emergency' THEN 100 ELSE 0 END) +
                            SUM(CASE WHEN risk_level = 'alarm' THEN 10 ELSE 0 END) +
                            SUM(CASE WHEN risk_level = 'warning' THEN 1 ELSE 0 END) as severity_score
                        FROM point_risk
                        GROUP BY country_code
                    ),
                    country_bounds AS (
                        SELECT
                            country_code,
                            MIN(ST_XMin(ST_Envelope(geom))) as west,
                            MIN(ST_YMin(ST_Envelope(geom))) as south,
                            MAX(ST_XMax(ST_Envelope(geom))) as east,
                            MAX(ST_YMax(ST_Envelope(geom))) as north
                        FROM (
                            SELECT
                                CASE
                                    WHEN LOWER(TRIM(a0.country)) = 'ethiopia' THEN 'ET'
                                    WHEN LOWER(TRIM(a0.country)) = 'kenya' THEN 'KE'
                                    WHEN LOWER(TRIM(a0.country)) = 'uganda' THEN 'UG'
                                    WHEN LOWER(TRIM(a0.country)) = 'sudan' THEN 'SD'
                                    WHEN LOWER(TRIM(a0.country)) = 'south sudan' THEN 'SS'
                                    WHEN LOWER(TRIM(a0.country)) IN ('tanzania', 'zanzibar') THEN 'TZ'
                                    WHEN LOWER(TRIM(a0.country)) = 'rwanda' THEN 'RW'
                                    WHEN LOWER(TRIM(a0.country)) = 'burundi' THEN 'BI'
                                    WHEN LOWER(TRIM(a0.country)) = 'somalia' THEN 'SO'
                                    WHEN LOWER(TRIM(a0.country)) = 'djibouti' THEN 'DJ'
                                    ELSE 'UN'
                                END as country_code,
                                a0.geom
                            FROM gha.admin0 a0
                            WHERE a0.country IS NOT NULL AND a0.country != ''
                        ) country_polygons
                        WHERE country_code != 'UN'
                        GROUP BY country_code
                    )
                    SELECT
                        ca.country_code,
                        ca.emergency,
                        ca.alarm,
                        ca.warning,
                        ca.total_points,
                        ca.severity_score,
                        cb.west,
                        cb.south,
                        cb.east,
                        cb.north
                    FROM country_agg ca
                    LEFT JOIN country_bounds cb ON cb.country_code = ca.country_code
                    WHERE ca.emergency > 0 OR ca.alarm > 0 OR ca.warning > 0
                    ORDER BY ca.severity_score DESC, ca.emergency DESC, ca.alarm DESC, ca.warning DESC
                """, [latest_date,
                      emergency_threshold, alarm_threshold, warning_threshold])

                countries = []
                country_names = {
                    'ET': 'Ethiopia', 'KE': 'Kenya', 'UG': 'Uganda',
                    'SD': 'Sudan', 'SS': 'South Sudan', 'TZ': 'Tanzania',
                    'RW': 'Rwanda', 'BI': 'Burundi', 'SO': 'Somalia',
                    'DJ': 'Djibouti', 'UN': 'Unknown'
                }

                for row in cursor.fetchall():
                    code = row[0] or 'UN'
                    country_name = country_names.get(code, code)

                    country_data = {
                        'code': code,
                        'name': country_name,
                        'emergency': row[1] or 0,
                        'alarm': row[2] or 0,
                        'warning': row[3] or 0,
                        'total_points': row[4] or 0,
                    }

                    # Add bounds if available
                    if row[6] is not None:
                        country_data['bounds'] = {
                            'west': float(row[6]),
                            'south': float(row[7]),
                            'east': float(row[8]),
                            'north': float(row[9])
                        }
                    else:
                        # Use default bounds for GHA region if not found
                        country_data['bounds'] = None

                    countries.append(country_data)

                result = {
                    'data_date': latest_date.strftime('%Y-%m-%d'),
                    'scope': scope_mode,
                    'countries': countries,
                    'thresholds': {
                        'warning': warning_threshold,
                        'alarm': alarm_threshold,
                        'emergency': emergency_threshold,
                    }
                }

            except Exception as e:
                import traceback
                response = JsonResponse({
                    'error': f'Query failed: {str(e)}',
                    'traceback': traceback.format_exc()
                }, status=500)
                response['Access-Control-Allow-Origin'] = '*'
                return response

        response = JsonResponse(result)
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        response['Access-Control-Allow-Headers'] = 'Content-Type'
        return response


# =============================================================================
# FloodWatch Custom: Situation Summary API for Homepage KPIs
# Returns aggregated risk counts, peak forecast info, and top affected basin
# =============================================================================
class SituationSummaryView(View):
    """API endpoint to get situation summary for homepage KPIs"""

    def get(self, request):
        from django.db import connection

        # Get optional horizon parameter (days ahead, default 7)
        horizon = int(request.GET.get('horizon', 7))
        requested_date = request.GET.get('date') or request.GET.get('forecast_date')
        scope_mode = request.GET.get('scope', 'all').strip().lower()
        if scope_mode not in ('all', 'whca'):
            response = JsonResponse({
                'error': 'Invalid scope. Use all or whca'
            }, status=400)
            response['Access-Control-Allow-Origin'] = '*'
            return response

        scope_where_sql = ""
        if scope_mode == 'whca':
            scope_where_sql = f" AND {WHCA_SCOPE_SQL_CONDITION}"

        with connection.cursor() as cursor:
            try:
                # Resolve query date: use requested date if provided, otherwise latest available
                if requested_date:
                    try:
                        query_date = datetime.strptime(requested_date, "%Y-%m-%d").date()
                    except ValueError:
                        response = JsonResponse({
                            'error': f'Invalid date format: {requested_date}. Expected YYYY-MM-DD.'
                        }, status=400)
                        response['Access-Control-Allow-Origin'] = '*'
                        return response
                else:
                    cursor.execute("""
                        SELECT MAX(data_date) FROM gha.multimodal_forecasts
                    """)
                    query_date = cursor.fetchone()[0]

                if not query_date:
                    response = JsonResponse({
                        'error': 'No forecast data available'
                    }, status=404)
                    response['Access-Control-Allow-Origin'] = '*'
                    return response

                # If a specific date is requested, validate that we actually have data for that data_date
                if requested_date:
                    cursor.execute("""
                        SELECT 1
                        FROM gha.multimodal_forecasts
                        WHERE data_date = %s
                        LIMIT 1
                    """, [query_date])
                    if not cursor.fetchone():
                        response = JsonResponse({
                            'error': f'No forecast data available for date {requested_date}'
                        }, status=404)
                        response['Access-Control-Allow-Origin'] = '*'
                        return response

                # Thresholds from CMS (same as map), fallback to defaults
                try:
                    from home.models import MultimodalClusterSettings
                    cluster_settings = MultimodalClusterSettings.load(request_or_site=request)
                    warning_threshold = cluster_settings.warning_threshold
                    alarm_threshold = cluster_settings.alarm_threshold
                    emergency_threshold = cluster_settings.emergency_threshold
                except Exception:
                    warning_threshold = 150.0
                    alarm_threshold = 300.0
                    emergency_threshold = 450.0

                # Query to get summary statistics using latest normalized data
                cursor.execute(f"""
                    WITH query_params AS (
                        SELECT %s::date as query_date
                    ),
                    first_forecast AS (
                        SELECT MIN(forecast_date) as forecast_date
                        FROM gha.multimodal_forecasts mf, query_params qp
                        WHERE mf.data_date = qp.query_date
                          AND mf.forecast_date >= qp.query_date
                    ),
                    point_data AS (
                        SELECT
                            cp.point_id,
                            cp.admin_name,
                            COALESCE(f.daily_avg, 0) as daily_avg
                        FROM gha.multimodal_control_points cp
                        CROSS JOIN query_params qp
                        CROSS JOIN first_forecast ff
                        LEFT JOIN gha.multimodal_forecasts f
                            ON f.point_id = cp.point_id
                            AND f.data_date = qp.query_date
                            AND f.forecast_date = ff.forecast_date
                        WHERE 1=1 {scope_where_sql}
                    ),
                    risk_levels AS (
                        SELECT
                            point_id,
                            admin_name,
                            daily_avg,
                            CASE
                                WHEN daily_avg >= %s THEN 'emergency'
                                WHEN daily_avg >= %s THEN 'alarm'
                                WHEN daily_avg >= %s THEN 'warning'
                                ELSE 'normal'
                            END as risk_level
                        FROM point_data
                    ),
                    risk_by_date AS (
                        SELECT
                            mf.forecast_date,
                            CASE
                                WHEN mf.daily_avg >= %s THEN 'emergency'
                                WHEN mf.daily_avg >= %s THEN 'alarm'
                                WHEN mf.daily_avg >= %s THEN 'warning'
                                ELSE 'normal'
                            END as risk_level
                        FROM gha.multimodal_forecasts mf
                        JOIN gha.multimodal_control_points cp ON cp.point_id = mf.point_id
                        CROSS JOIN query_params qp
                        WHERE mf.data_date = qp.query_date
                        {scope_where_sql}
                    )
                    SELECT
                        (SELECT COUNT(*) FROM risk_levels WHERE risk_level = 'emergency') as emergency_count,
                        (SELECT COUNT(*) FROM risk_levels WHERE risk_level = 'alarm') as alarm_count,
                        (SELECT COUNT(*) FROM risk_levels WHERE risk_level = 'warning') as warning_count,
                        (SELECT COUNT(*) FROM risk_levels WHERE risk_level = 'normal') as normal_count,
                        (SELECT COUNT(*) FROM risk_levels) as total_points,
                        (
                            SELECT forecast_date
                            FROM risk_by_date
                            WHERE risk_level IN ('emergency', 'alarm', 'warning')
                            GROUP BY forecast_date
                            ORDER BY COUNT(*) DESC
                            LIMIT 1
                        ) as peak_day
                """, [query_date,
                      emergency_threshold, alarm_threshold, warning_threshold,
                      emergency_threshold, alarm_threshold, warning_threshold])

                row = cursor.fetchone()

                # Get country breakdown
                cursor.execute(f"""
                    WITH query_params AS (
                        SELECT %s::date as query_date
                    ),
                    first_forecast AS (
                        SELECT MIN(forecast_date) as forecast_date
                        FROM gha.multimodal_forecasts mf, query_params qp
                        WHERE mf.data_date = qp.query_date
                          AND mf.forecast_date >= qp.query_date
                    ),
                    point_country AS (
                        SELECT
                            cp.point_id,
                            cp.admin_name,
                            COALESCE(f.daily_avg, 0) as daily_avg,
                            UPPER(LEFT(cp.admin_name, 2)) as country_code
                        FROM gha.multimodal_control_points cp
                        CROSS JOIN query_params qp
                        CROSS JOIN first_forecast ff
                        LEFT JOIN gha.multimodal_forecasts f
                            ON f.point_id = cp.point_id
                            AND f.data_date = qp.query_date
                            AND f.forecast_date = ff.forecast_date
                        WHERE 1=1 {scope_where_sql}
                    ),
                    risk_levels AS (
                        SELECT
                            point_id,
                            country_code,
                            CASE
                                WHEN daily_avg >= %s THEN 'emergency'
                                WHEN daily_avg >= %s THEN 'alarm'
                                WHEN daily_avg >= %s THEN 'warning'
                                ELSE 'normal'
                            END as risk_level
                        FROM point_country
                    )
                    SELECT
                        country_code,
                        SUM(CASE WHEN risk_level = 'emergency' THEN 1 ELSE 0 END) as emergency,
                        SUM(CASE WHEN risk_level = 'alarm' THEN 1 ELSE 0 END) as alarm,
                        SUM(CASE WHEN risk_level = 'warning' THEN 1 ELSE 0 END) as warning,
                        COUNT(*) as total
                    FROM risk_levels
                    WHERE risk_level != 'normal'
                    GROUP BY country_code
                    HAVING SUM(CASE WHEN risk_level IN ('emergency', 'alarm', 'warning') THEN 1 ELSE 0 END) > 0
                    ORDER BY
                        SUM(CASE WHEN risk_level = 'emergency' THEN 1 ELSE 0 END) DESC,
                        SUM(CASE WHEN risk_level = 'alarm' THEN 1 ELSE 0 END) DESC,
                        SUM(CASE WHEN risk_level = 'warning' THEN 1 ELSE 0 END) DESC
                """, [query_date, emergency_threshold, alarm_threshold, warning_threshold])

                # Load exposure scores from floodreport for enrichment
                exposure_by_country = {}
                try:
                    from floodreport.models import FloodExposureScore
                    from django.db.models import Sum, Avg
                    for code, cname in ISO2_TO_COUNTRY_NAME.items():
                        if code == "REGION":
                            continue
                        qs = FloodExposureScore.objects.filter(country__iexact=cname, admin_level=0)
                        if qs.exists():
                            agg = qs.aggregate(
                                pop=Sum("affected_population"),
                                area=Sum("flooded_area_km2"),
                                score=Avg("composite_score"),
                            )
                            exposure_by_country[code] = {
                                'affected_population': agg['pop'] or 0,
                                'affected_area_km2': round(agg['area'] or 0, 1),
                                'composite_score': round(agg['score'] or 0, 4),
                            }
                except Exception:
                    pass

                country_breakdown = []
                for c_row in cursor.fetchall():
                    code = c_row[0]
                    # Only include if code is a valid 2-letter alphabetic code
                    if code and len(code) == 2 and code.isalpha():
                        entry = {
                            'code': code,
                            'name': code,  # Frontend can map to full name if needed
                            'emergency': c_row[1] or 0,
                            'alarm': c_row[2] or 0,
                            'warning': c_row[3] or 0,
                            'total_at_risk': (c_row[1] or 0) + (c_row[2] or 0) + (c_row[3] or 0),
                        }
                        # Enrich with exposure data
                        if code in exposure_by_country:
                            entry.update(exposure_by_country[code])
                        country_breakdown.append(entry)

                # Add countries that have exposure scores but no point-based alerts
                seen_codes = {e['code'] for e in country_breakdown}
                for code, exp_data in exposure_by_country.items():
                    if code not in seen_codes and exp_data['composite_score'] > 0:
                        country_breakdown.append({
                            'code': code,
                            'name': code,
                            'emergency': 0, 'alarm': 0, 'warning': 0, 'total_at_risk': 0,
                            **exp_data,
                        })

                if row:
                    summary = {
                        'data_date': query_date.strftime('%Y-%m-%d'),
                        'scope': scope_mode,
                        'horizon_days': horizon,
                        'risk_counts': {
                            'emergency': row[0] or 0,
                            'alarm': row[1] or 0,
                            'warning': row[2] or 0,
                            'normal': row[3] or 0,
                            'total': row[4] or 0,
                        },
                        'peak_day': row[5],
                        'country_breakdown': country_breakdown,
                        'thresholds': {
                            'warning': warning_threshold,
                            'alarm': alarm_threshold,
                            'emergency': emergency_threshold,
                        }
                    }
                else:
                    summary = {
                        'data_date': query_date.strftime('%Y-%m-%d'),
                        'scope': scope_mode,
                        'horizon_days': horizon,
                        'risk_counts': {
                            'emergency': 0,
                            'alarm': 0,
                            'warning': 0,
                            'normal': 0,
                            'total': 0,
                        },
                        'peak_day': None,
                        'country_breakdown': [],
                        'thresholds': {
                            'warning': warning_threshold,
                            'alarm': alarm_threshold,
                            'emergency': emergency_threshold,
                        }
                    }

            except Exception as e:
                import traceback
                response = JsonResponse({
                    'error': f'Query failed: {str(e)}',
                    'traceback': traceback.format_exc()
                }, status=500)
                response['Access-Control-Allow-Origin'] = '*'
                return response

        response = JsonResponse(summary)
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        response['Access-Control-Allow-Headers'] = 'Content-Type'

        return response


# =============================================================================
# FloodWatch Custom: Hotspots API for Homepage Table
# Returns ranked list of locations with highest flood risk
# =============================================================================
class HotspotsView(View):
    """API endpoint to get ranked hotspots for homepage table"""

    def get(self, request):
        from django.db import connection

        # Get optional limit parameter (default 10)
        limit = int(request.GET.get('limit', 10))

        # Thresholds (matching frontend config)
        warning_threshold = 500
        alarm_threshold = 750
        emergency_threshold = 1500

        with connection.cursor() as cursor:
            try:
                # Get the latest available data date
                cursor.execute("""
                    SELECT MAX(data_date) FROM home_multimodal_forecast_geojson
                """)
                latest_date = cursor.fetchone()[0]

                if not latest_date:
                    response = JsonResponse({
                        'error': 'No forecast data available'
                    }, status=404)
                    response['Access-Control-Allow-Origin'] = '*'
                    return response

                # Query to get hotspots ranked by severity
                cursor.execute("""
                    WITH latest_forecasts AS (
                        SELECT
                            jsonb_array_elements(geojson_data->'features') as feature
                        FROM home_multimodal_forecast_geojson
                        WHERE data_date = %s
                    ),
                    forecast_data AS (
                        SELECT
                            feature->'properties'->>'point_id' as point_id,
                            feature->'properties'->>'admin_name' as admin_name,
                            feature->'properties'->'forecasts' as forecasts,
                            (feature->'geometry'->'coordinates'->0)::float as lon,
                            (feature->'geometry'->'coordinates'->1)::float as lat
                        FROM latest_forecasts
                        WHERE feature->'properties'->'forecasts' IS NOT NULL
                    ),
                    point_stats AS (
                        SELECT
                            point_id,
                            admin_name,
                            lon,
                            lat,
                            MAX((f->>'daily_avg')::float) as max_discharge,
                            (
                                SELECT f2->>'date'
                                FROM jsonb_array_elements(forecasts) f2
                                ORDER BY (f2->>'daily_avg')::float DESC
                                LIMIT 1
                            ) as peak_date
                        FROM forecast_data,
                             jsonb_array_elements(forecasts) f
                        GROUP BY point_id, admin_name, lon, lat, forecasts
                    ),
                    ranked_points AS (
                        SELECT
                            point_id,
                            admin_name,
                            lon,
                            lat,
                            max_discharge,
                            peak_date,
                            CASE
                                WHEN max_discharge >= %s THEN 'emergency'
                                WHEN max_discharge >= %s THEN 'alarm'
                                WHEN max_discharge >= %s THEN 'warning'
                                ELSE 'normal'
                            END as risk_level,
                            CASE
                                WHEN max_discharge >= %s THEN 3
                                WHEN max_discharge >= %s THEN 2
                                WHEN max_discharge >= %s THEN 1
                                ELSE 0
                            END as risk_score
                        FROM point_stats
                    )
                    SELECT
                        point_id,
                        admin_name,
                        lon,
                        lat,
                        ROUND(max_discharge::numeric, 1) as max_discharge,
                        peak_date,
                        risk_level
                    FROM ranked_points
                    WHERE risk_level != 'normal'
                    ORDER BY risk_score DESC, max_discharge DESC
                    LIMIT %s
                """, [
                    latest_date,
                    emergency_threshold, alarm_threshold, warning_threshold,
                    emergency_threshold, alarm_threshold, warning_threshold,
                    limit
                ])

                columns = ['point_id', 'admin_name', 'lon', 'lat',
                          'max_discharge', 'peak_date', 'risk_level']
                hotspots = []
                for i, row in enumerate(cursor.fetchall(), 1):
                    item = dict(zip(columns, row))
                    item['rank'] = i
                    # Convert Decimal to float for JSON
                    if item['max_discharge']:
                        item['max_discharge'] = float(item['max_discharge'])
                    # Handle null admin_name
                    if not item['admin_name']:
                        item['admin_name'] = 'No Admin'
                    hotspots.append(item)

                # Get daily forecast values for each hotspot
                if hotspots:
                    point_ids = [h['point_id'] for h in hotspots]
                    cursor.execute("""
                        WITH latest_forecasts AS (
                            SELECT
                                jsonb_array_elements(geojson_data->'features') as feature
                            FROM home_multimodal_forecast_geojson
                            WHERE data_date = %s
                        ),
                        point_forecasts AS (
                            SELECT
                                feature->'properties'->>'point_id' as point_id,
                                feature->'properties'->'forecasts' as forecasts
                            FROM latest_forecasts
                            WHERE feature->'properties'->>'point_id' = ANY(%s)
                        )
                        SELECT
                            point_id,
                            jsonb_agg(
                                jsonb_build_object(
                                    'date', f->>'date',
                                    'discharge', ROUND((f->>'daily_avg')::numeric, 0)
                                )
                                ORDER BY f->>'date'
                            ) as daily_values
                        FROM point_forecasts,
                             jsonb_array_elements(forecasts) f
                        GROUP BY point_id
                    """, [latest_date, point_ids])

                    daily_data = {row[0]: row[1] for row in cursor.fetchall()}
                    for h in hotspots:
                        h['daily_values'] = daily_data.get(h['point_id'], [])

            except Exception as e:
                import traceback
                response = JsonResponse({
                    'error': f'Query failed: {str(e)}',
                    'traceback': traceback.format_exc()
                }, status=500)
                response['Access-Control-Allow-Origin'] = '*'
                return response

        response = JsonResponse({
            'data_date': latest_date.strftime('%Y-%m-%d'),
            'hotspots': hotspots,
            'count': len(hotspots),
            'thresholds': {
                'warning': warning_threshold,
                'alarm': alarm_threshold,
                'emergency': emergency_threshold,
            }
        })
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        response['Access-Control-Allow-Headers'] = 'Content-Type'

        return response


# =============================================================================
# FloodWatch: Expert Assessments API (gha.expert_assessments)
# Professional multi-stakeholder flood risk assessment system
# =============================================================================
class CountryAssessmentsView(View):
    """
    API for country/regional level expert flood risk assessments.
    Used by hydrologists and meteorologists to submit their professional assessments.
    Data stored in gha.expert_assessments table.
    """

    def get(self, request):
        from django.db import connection

        date_str = request.GET.get('date')
        expert_type = request.GET.get('expert_type')
        raw_country = request.GET.get('country')
        country_code = _normalize_country_code(raw_country)
        status = (request.GET.get('status') or 'all').strip().lower()
        report_group = (request.GET.get('report_group') or 'all').strip().lower()
        assessment_id = request.GET.get('id')
        include_districts = _coerce_bool(request.GET.get('include_districts'), default=False)
        request_user = _resolve_request_user(request)
        can_view_unpublished = _can_publish_expert_assessment(request_user)

        published_only = request.GET.get('published')
        if published_only is not None:
            published_only = _coerce_bool(published_only, default=False)
        else:
            published_only = None

        if not can_view_unpublished:
            if status in ('draft', 'unapproved'):
                response = JsonResponse({'error': 'Authentication is required to access draft reports'}, status=403)
                response['Access-Control-Allow-Origin'] = '*'
                response['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
                response['Access-Control-Allow-Headers'] = 'Content-Type, X-CSRFToken, Authorization'
                return response
            if published_only is False:
                response = JsonResponse({'error': 'Authentication is required to access unpublished reports'}, status=403)
                response['Access-Control-Allow-Origin'] = '*'
                response['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
                response['Access-Control-Allow-Headers'] = 'Content-Type, X-CSRFToken, Authorization'
                return response
            # Anonymous consumers can only read published assessments.
            published_only = True

        with connection.cursor() as cursor:
            try:
                query = """
                    SELECT id, expert_type, assessment_date, valid_from, valid_to,
                           country_code, country_name, risk_level, assessment_comment,
                           affected_areas, recommendations, created_by, created_at,
                           updated_at, is_published
                    FROM gha.expert_assessments
                    WHERE 1=1
                """
                params = []

                if assessment_id:
                    try:
                        assessment_id = int(assessment_id)
                    except ValueError:
                        response = JsonResponse({'error': 'Invalid assessment id'}, status=400)
                        response['Access-Control-Allow-Origin'] = '*'
                        return response
                    query += " AND id = %s"
                    params.append(assessment_id)

                if expert_type:
                    query += " AND expert_type = %s"
                    params.append(expert_type)

                if date_str:
                    query += " AND assessment_date = %s"
                    params.append(date_str)

                if country_code:
                    if country_code == "REGION":
                        query += " AND UPPER(COALESCE(country_code, 'REGION')) = 'REGION'"
                    elif len(country_code) == 2:
                        query += " AND (UPPER(COALESCE(country_code, '')) = %s OR LOWER(COALESCE(country_name, '')) = LOWER(%s))"
                        params.extend([country_code, raw_country or country_code])
                    else:
                        query += " AND LOWER(COALESCE(country_name, '')) = LOWER(%s)"
                        params.append(raw_country or country_code)

                if status == 'published':
                    query += " AND COALESCE(is_published, FALSE) = TRUE"
                elif status in ('draft', 'unapproved'):
                    query += " AND COALESCE(is_published, FALSE) = FALSE"
                elif published_only is True:
                    query += " AND COALESCE(is_published, FALSE) = TRUE"
                elif published_only is False:
                    query += " AND COALESCE(is_published, FALSE) = FALSE"

                if report_group == 'general':
                    query += " AND UPPER(COALESCE(country_code, 'REGION')) = 'REGION'"
                elif report_group in ('member', 'member_state', 'member-state'):
                    query += " AND UPPER(COALESCE(country_code, 'REGION')) != 'REGION'"

                query += " ORDER BY assessment_date DESC, country_name"

                cursor.execute(query, params)
                columns = [col[0] for col in cursor.description]
                assessments = []
                for row in cursor.fetchall():
                    item = dict(zip(columns, row))
                    for date_field in ['assessment_date', 'valid_from', 'valid_to', 'created_at', 'updated_at']:
                        if item.get(date_field):
                            item[date_field] = item[date_field].isoformat() if hasattr(item[date_field], 'isoformat') else str(item[date_field])
                    normalized_country_code = _normalize_country_code(item.get('country_code') or item.get('country_name')) or 'REGION'
                    item['country_code'] = normalized_country_code
                    if not item.get('country_name'):
                        item['country_name'] = ISO2_TO_COUNTRY_NAME.get(normalized_country_code, normalized_country_code)

                    item['report_group'] = (
                        'general'
                        if normalized_country_code == 'REGION'
                        else 'member_state'
                    )
                    item['status'] = 'published' if item.get('is_published') else 'draft'
                    item['report_key'] = _format_report_key(
                        item.get('expert_type'),
                        normalized_country_code,
                        item.get('assessment_date') or date_str or '',
                    )
                    item.update(_parse_creator_metadata(item.get('created_by')))
                    item['district_count'] = 0
                    if include_districts:
                        item['district_assessments'] = []
                    assessments.append(item)

                # Enrich with district-level inputs so a full interactive report can be restored.
                for item in assessments:
                    member_country_name = item.get('country_name') or ISO2_TO_COUNTRY_NAME.get(item.get('country_code'), item.get('country_code'))
                    district_params = [item.get('expert_type'), item.get('assessment_date')]
                    if include_districts:
                        district_query = """
                            SELECT country, admin1, admin2, gid_2, risk_level, comment, created_at, updated_at
                            FROM gha.district_risk_levels
                            WHERE expert_type = %s
                              AND assessment_date = %s
                        """
                    else:
                        district_query = """
                            SELECT COUNT(*)
                            FROM gha.district_risk_levels
                            WHERE expert_type = %s
                              AND assessment_date = %s
                        """

                    if item.get('country_code') == 'REGION':
                        district_query += " AND UPPER(COALESCE(country, '')) LIKE 'REGION::%'"
                    else:
                        district_query += " AND (UPPER(COALESCE(country, '')) = %s OR LOWER(COALESCE(country, '')) = LOWER(%s))"
                        district_params.extend([item.get('country_code'), member_country_name])

                    if include_districts:
                        district_query += " ORDER BY country, admin1, admin2"
                        cursor.execute(district_query, district_params)
                        districts = []
                        for drow in cursor.fetchall():
                            district_country = drow[0]
                            if district_country and district_country.startswith('REGION::'):
                                district_country = district_country.split('REGION::', 1)[1]
                            district_item = {
                                'country': district_country,
                                'admin1': drow[1],
                                'admin2': drow[2],
                                'gid_2': drow[3],
                                'risk_level': drow[4],
                                'comment': drow[5] or '',
                                'created_at': drow[6].isoformat() if drow[6] and hasattr(drow[6], 'isoformat') else (str(drow[6]) if drow[6] else None),
                                'updated_at': drow[7].isoformat() if drow[7] and hasattr(drow[7], 'isoformat') else (str(drow[7]) if drow[7] else None),
                            }
                            districts.append(district_item)
                        item['district_assessments'] = districts
                        item['district_count'] = len(districts)
                        item['interactive_report'] = {
                            'overall': {
                                'risk_level': item.get('risk_level', 'normal'),
                                'assessment_comment': item.get('assessment_comment') or '',
                                'affected_areas': item.get('affected_areas') or '',
                                'recommendations': item.get('recommendations') or '',
                            },
                            'district_assessments': districts,
                        }
                    else:
                        cursor.execute(district_query, district_params)
                        row_count = cursor.fetchone()
                        item['district_count'] = int(row_count[0] or 0) if row_count else 0

                    has_overall_content = bool(
                        (item.get('assessment_comment') or '').strip()
                        or (item.get('affected_areas') or '').strip()
                        or (item.get('recommendations') or '').strip()
                    )
                    if item.get('is_published'):
                        item['completion_state'] = 'approved'
                    elif has_overall_content or item.get('district_count', 0) > 0:
                        item['completion_state'] = 'unapproved'
                    else:
                        item['completion_state'] = 'unfinished'

            except Exception as exc:
                response = JsonResponse({'error': f'Failed to fetch assessments: {str(exc)}'}, status=500)
                response['Access-Control-Allow-Origin'] = '*'
                response['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
                response['Access-Control-Allow-Headers'] = 'Content-Type, X-CSRFToken, Authorization'
                return response

        response = JsonResponse({'assessments': assessments, 'count': len(assessments)})
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response['Access-Control-Allow-Headers'] = 'Content-Type, X-CSRFToken, Authorization'
        return response

    def post(self, request):
        from django.db import connection, transaction
        import json

        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            response = JsonResponse({'error': 'Invalid JSON'}, status=400)
            response['Access-Control-Allow-Origin'] = '*'
            return response

        valid_risk_levels = {'normal', 'watch', 'warning', 'alarm', 'emergency'}
        expert_type = (data.get('expert_type') or 'hydrologist').strip().lower()
        if expert_type not in ('hydrologist', 'meteorologist'):
            expert_type = 'hydrologist'

        assessment_date = data.get('forecast_date') or data.get('assessment_date')
        report_group = (data.get('report_group') or '').strip().lower()
        raw_country_code = data.get('country_code') or data.get('country')
        raw_country_name = data.get('country_name')
        country_code = _normalize_country_code(raw_country_code or raw_country_name)
        country_name = (raw_country_name or '').strip()
        if not country_name and country_code:
            country_name = ISO2_TO_COUNTRY_NAME.get(country_code, country_code)

        if report_group in ('general',):
            country_code = 'REGION'
            country_name = 'East Africa Region'
        elif report_group in ('member', 'member_state', 'member-state') and (not country_code or country_code == 'REGION'):
            response = JsonResponse({'error': 'Member-state report requires a country'}, status=400)
            response['Access-Control-Allow-Origin'] = '*'
            return response
        elif not country_code:
            country_code = 'REGION'
            country_name = country_name or 'East Africa Region'

        risk_level = (data.get('risk_level') or 'normal').strip().lower()
        if risk_level not in valid_risk_levels:
            risk_level = 'normal'

        comment = data.get('comment', '') or ''
        affected_areas = data.get('affected_areas', '') or ''
        recommendations = data.get('recommendations', '') or ''
        contributor_name = (data.get('contributor_name') or '').strip()
        contributor_country = _normalize_country_code(
            data.get('contributor_country') or data.get('country_of_origin')
        )
        explicit_creator = (data.get('created_by') or '').strip()
        district_assessments = data.get('district_assessments')
        district_payload_provided = district_assessments is not None
        if district_payload_provided and not isinstance(district_assessments, list):
            response = JsonResponse({'error': 'district_assessments must be a list'}, status=400)
            response['Access-Control-Allow-Origin'] = '*'
            return response
        replace_district_assessments = _coerce_bool(
            data.get('replace_district_assessments'),
            default=district_payload_provided,
        )

        save_mode = (data.get('save_mode') or 'draft').strip().lower()
        is_published = _coerce_bool(
            data.get('is_published'),
            default=save_mode in ('submitted', 'publish', 'published'),
        )
        request_user = _resolve_request_user(request)
        is_authenticated = bool(request_user)
        if not is_authenticated:
            response = JsonResponse(
                {'error': 'Sign-in is required for expert assessments'},
                status=403,
            )
            response['Access-Control-Allow-Origin'] = '*'
            return response

        if not _can_submit_expert_assessment(request_user, expert_type):
            response = JsonResponse(
                {'error': f'Permission denied. {expert_type.title()} role is required.'},
                status=403,
            )
            response['Access-Control-Allow-Origin'] = '*'
            return response

        if country_code == 'REGION':
            display_name = explicit_creator or _user_display_name(request_user) or contributor_name or 'authenticated-user'
            display_country = contributor_country or 'REGION'
            created_by = f"public|{display_name}|{display_country}"
        else:
            display_name = explicit_creator or _user_display_name(request_user) or contributor_name or 'authenticated-user'
            created_by = f"kpp|{display_name}|{country_code}"

        if not assessment_date:
            response = JsonResponse({'error': 'Assessment date is required'}, status=400)
            response['Access-Control-Allow-Origin'] = '*'
            return response

        if save_mode in ('submitted', 'publish', 'published') and not comment.strip():
            response = JsonResponse({'error': 'Assessment comment is required'}, status=400)
            response['Access-Control-Allow-Origin'] = '*'
            return response

        district_saved_count = 0
        with transaction.atomic():
            with connection.cursor() as cursor:
                try:
                    cursor.execute("""
                        INSERT INTO gha.expert_assessments
                            (expert_type, assessment_date, country_code, country_name,
                             risk_level, assessment_comment, affected_areas, recommendations,
                             created_by, is_published, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                        ON CONFLICT (expert_type, assessment_date, country_code)
                        DO UPDATE SET
                            risk_level = EXCLUDED.risk_level,
                            assessment_comment = EXCLUDED.assessment_comment,
                            affected_areas = EXCLUDED.affected_areas,
                            recommendations = EXCLUDED.recommendations,
                            created_by = EXCLUDED.created_by,
                            country_name = EXCLUDED.country_name,
                            is_published = EXCLUDED.is_published,
                            updated_at = CURRENT_TIMESTAMP
                        RETURNING id
                    """, [expert_type, assessment_date, country_code, country_name,
                          risk_level, comment, affected_areas, recommendations, created_by, is_published])

                    result = cursor.fetchone()
                    assessment_id = result[0] if result else None

                    # Full interactive save: persist all district/admin edits together
                    # with the overall assessment in a single transaction.
                    if district_payload_provided:
                        if replace_district_assessments:
                            if country_code == 'REGION':
                                cursor.execute("""
                                    DELETE FROM gha.district_risk_levels
                                    WHERE expert_type = %s
                                      AND assessment_date = %s
                                      AND UPPER(COALESCE(country, '')) LIKE 'REGION::%'
                                """, [expert_type, assessment_date])
                            else:
                                cursor.execute("""
                                    DELETE FROM gha.district_risk_levels
                                    WHERE expert_type = %s
                                      AND assessment_date = %s
                                      AND (UPPER(COALESCE(country, '')) = %s OR LOWER(COALESCE(country, '')) = LOWER(%s))
                                """, [expert_type, assessment_date, country_code, country_name])

                        for district in district_assessments:
                            if not isinstance(district, dict):
                                continue
                            admin1 = (district.get('admin1') or district.get('name_1') or '').strip()
                            admin2 = (district.get('admin2') or district.get('name_2') or '').strip()
                            if not admin1 or not admin2:
                                continue

                            district_country_code = _normalize_country_code(
                                district.get('country_code') or district.get('country') or country_code
                            )
                            if district_country_code == 'REGION':
                                district_country_code = country_code if country_code != 'REGION' else ''

                            district_country_name = (district.get('country_name') or '').strip()
                            if not district_country_name and district_country_code:
                                district_country_name = ISO2_TO_COUNTRY_NAME.get(district_country_code, '')
                            if not district_country_name and country_code != 'REGION':
                                district_country_name = country_name
                            if not district_country_name:
                                district_country_name = (district.get('country') or '').strip()
                            if not district_country_name:
                                continue

                            district_risk_level = (district.get('risk_level') or 'normal').strip().lower()
                            if district_risk_level not in valid_risk_levels:
                                district_risk_level = 'normal'
                            district_comment = (district.get('comment') or '').strip()
                            district_gid_2 = (district.get('gid_2') or '').strip() or None
                            stored_country = district_country_name
                            if country_code == 'REGION':
                                stored_country = f"REGION::{district_country_name}"

                            cursor.execute("""
                                INSERT INTO gha.district_risk_levels
                                    (expert_type, assessment_date, country, admin1, admin2, gid_2, risk_level, comment, updated_at)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                                ON CONFLICT (expert_type, assessment_date, country, admin1, admin2)
                                DO UPDATE SET
                                    risk_level = EXCLUDED.risk_level,
                                    comment = EXCLUDED.comment,
                                    gid_2 = EXCLUDED.gid_2,
                                    updated_at = CURRENT_TIMESTAMP
                            """, [
                                expert_type,
                                assessment_date,
                                stored_country,
                                admin1,
                                admin2,
                                district_gid_2,
                                district_risk_level,
                                district_comment,
                            ])
                            district_saved_count += 1

                except Exception as exc:
                    response = JsonResponse({'error': f'Database error: {str(exc)}'}, status=500)
                    response['Access-Control-Allow-Origin'] = '*'
                    return response

        response = JsonResponse({
            'success': True,
            'id': assessment_id,
            'status': 'published' if is_published else 'draft',
            'report_key': _format_report_key(expert_type, country_code, str(assessment_date)),
            'country_code': country_code,
            'country_name': country_name,
            'district_saved_count': district_saved_count,
            'replace_district_assessments': replace_district_assessments,
            'full_saved': True,
            'message': 'Expert assessment saved successfully'
        })
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response['Access-Control-Allow-Headers'] = 'Content-Type, X-CSRFToken, Authorization'
        return response

    def options(self, request):
        response = JsonResponse({})
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response['Access-Control-Allow-Headers'] = 'Content-Type, X-CSRFToken, Authorization'
        return response


class CountryAssessmentPublishView(View):
    """Publish or unpublish expert assessments."""

    def post(self, request, assessment_id):
        from django.db import connection
        import json

        request_user = _resolve_request_user(request)
        if not _can_publish_expert_assessment(request_user):
            response = JsonResponse(
                {'error': 'Permission denied. Expert publisher role is required.'},
                status=403,
            )
            response['Access-Control-Allow-Origin'] = '*'
            response['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
            response['Access-Control-Allow-Headers'] = 'Content-Type, X-CSRFToken, Authorization'
            return response

        try:
            data = json.loads(request.body) if request.body else {}
        except json.JSONDecodeError:
            data = {}

        publish = _coerce_bool(data.get('is_published'), default=True)

        with connection.cursor() as cursor:
            try:
                cursor.execute("""
                    UPDATE gha.expert_assessments
                    SET is_published = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                    RETURNING id, is_published
                """, [publish, assessment_id])
                row = cursor.fetchone()
                if not row:
                    response = JsonResponse({'error': 'Assessment not found'}, status=404)
                    response['Access-Control-Allow-Origin'] = '*'
                    return response
            except Exception as exc:
                response = JsonResponse({'error': f'Database error: {str(exc)}'}, status=500)
                response['Access-Control-Allow-Origin'] = '*'
                return response

        response = JsonResponse({
            'success': True,
            'id': row[0],
            'is_published': row[1],
            'status': 'published' if row[1] else 'draft',
        })
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response['Access-Control-Allow-Headers'] = 'Content-Type, X-CSRFToken, Authorization'
        return response

    def options(self, request, assessment_id):
        response = JsonResponse({})
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response['Access-Control-Allow-Headers'] = 'Content-Type, X-CSRFToken, Authorization'
        return response


# =============================================================================
# FloodWatch Custom: Regional Summary Generator API
# =============================================================================
class RegionalSummaryView(View):
    """API to generate regional summary from country assessments"""

    def post(self, request):
        import json

        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            response = JsonResponse({'error': 'Invalid JSON'}, status=400)
            response['Access-Control-Allow-Origin'] = '*'
            return response

        assessments = data.get('assessments', {})
        forecast_date = data.get('forecast_date')

        # Aggregate risk levels
        risk_priority = {'emergency': 5, 'alarm': 4, 'warning': 3, 'watch': 2, 'normal': 1}
        max_risk = 'normal'
        max_priority = 1

        affected_areas = []
        recommendations = []
        comments = []

        for country_code, assessment in assessments.items():
            if not assessment:
                continue

            risk = assessment.get('risk_level', 'normal')
            if risk_priority.get(risk, 1) > max_priority:
                max_priority = risk_priority[risk]
                max_risk = risk

            if assessment.get('affected_areas'):
                affected_areas.append(f"**{assessment.get('country_name', country_code)}:** {assessment['affected_areas']}")

            if assessment.get('recommendations'):
                recommendations.append(f"**{assessment.get('country_name', country_code)}:** {assessment['recommendations']}")

            if assessment.get('comment'):
                comments.append(f"**{assessment.get('country_name', country_code)}:** {assessment['comment']}")

        summary = {
            'forecast_date': forecast_date,
            'overall_risk': max_risk,
            'affected_areas': '\n\n'.join(affected_areas),
            'combined_recommendations': '\n\n'.join(recommendations),
            'situation_summary': '\n\n'.join(comments),
            'countries_reported': len([a for a in assessments.values() if a and a.get('comment')]),
            'generated_at': datetime.now().isoformat(),
        }

        response = JsonResponse({'summary': summary})
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response['Access-Control-Allow-Headers'] = 'Content-Type'
        return response

    def options(self, request):
        response = JsonResponse({})
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response['Access-Control-Allow-Headers'] = 'Content-Type'
        return response


# =============================================================================
# FloodWatch Custom: River Basins API
# Returns major river basins in the GHA region from hydrobasins
# =============================================================================
class RiverBasinsView(View):
    """API endpoint to get river basins for filter dropdowns"""

    def get(self, request):
        from django.db import connection

        with connection.cursor() as cursor:
            try:
                # Query distinct basins from hydrobasins_lev06 or use predefined GHA basins
                # First try to get from database
                cursor.execute("""
                    SELECT DISTINCT main_bas as code,
                           CASE main_bas
                               WHEN 1060000010 THEN 'Nile Basin'
                               WHEN 1060013900 THEN 'Juba-Shabelle Basin'
                               WHEN 1060015050 THEN 'Omo-Turkana Basin'
                               WHEN 1060017830 THEN 'Tana Basin'
                               WHEN 1060016650 THEN 'Awash Basin'
                               WHEN 1060018330 THEN 'Rift Valley Lakes'
                               WHEN 1060019040 THEN 'Lake Victoria Basin'
                               ELSE 'Basin ' || main_bas
                           END as name,
                           ST_XMin(ST_Extent(geom)) as left,
                           ST_YMin(ST_Extent(geom)) as bottom,
                           ST_XMax(ST_Extent(geom)) as right,
                           ST_YMax(ST_Extent(geom)) as top
                    FROM gha.hydrobasins_lev06
                    GROUP BY main_bas
                    ORDER BY name
                """)

                columns = ['code', 'name', 'left', 'bottom', 'right', 'top']
                basins = []
                for row in cursor.fetchall():
                    basins.append({
                        'code': str(row[0]),
                        'name': row[1],
                        'bbox': {
                            'left': float(row[2]) if row[2] else None,
                            'bottom': float(row[3]) if row[3] else None,
                            'right': float(row[4]) if row[4] else None,
                            'top': float(row[5]) if row[5] else None,
                        }
                    })

            except Exception as e:
                # NO FALLBACK - return error if table doesn't exist
                response = JsonResponse({
                    'error': f'Failed to fetch river basins: {str(e)}'
                }, status=500)
                response['Access-Control-Allow-Origin'] = '*'
                return response

        response = JsonResponse(basins, safe=False)
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        response['Access-Control-Allow-Headers'] = 'Content-Type'
        return response


# =============================================================================
# FloodWatch: Forecast Majority Risk API
# Aggregates forecast point risk by admin unit and returns majority risk level
# =============================================================================
class ForecastMajorityRiskView(View):
    """Majority flood risk by admin unit from forecast points."""

    def get(self, request):
        from django.db import connection

        date_str = request.GET.get('date')
        country = (request.GET.get('country') or '').strip()
        country_code = _normalize_country_code(country)
        country_name = ISO2_TO_COUNTRY_NAME.get(country_code, country) if country_code else ''
        admin_level = str(request.GET.get('admin_level', '2')).strip()
        if admin_level not in ('1', '2'):
            admin_level = '2'

        warning_threshold, alarm_threshold, emergency_threshold = _get_multimodal_thresholds(request)

        with connection.cursor() as cursor:
            try:
                if date_str:
                    try:
                        query_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                    except ValueError:
                        response = JsonResponse({'error': 'Invalid date format. Use YYYY-MM-DD'}, status=400)
                        response['Access-Control-Allow-Origin'] = '*'
                        return response
                else:
                    cursor.execute("SELECT MAX(data_date) FROM gha.multimodal_forecasts")
                    query_date = cursor.fetchone()[0]

                if not query_date:
                    response = JsonResponse({'risk_by_admin': [], 'count': 0})
                    response['Access-Control-Allow-Origin'] = '*'
                    return response

                country_filter_sql = ""
                params = [query_date]
                if country_code and country_code != 'REGION':
                    # Admin tables may store either country names or ISO-like values;
                    # support both to keep the filter resilient.
                    country_filter_sql = "AND (UPPER(COALESCE(ad.country, '')) = %s OR LOWER(COALESCE(ad.country, '')) = LOWER(%s))"
                    params.extend([country_code, country_name or country])

                admin_fields = (
                    "ad.country, ad.name_1 as admin1, ad.name_2 as admin2, ad.gid_2 as gid_2"
                    if admin_level == '2'
                    else "ad.country, ad.name_1 as admin1, NULL::text as admin2, NULL::text as gid_2"
                )
                admin_group = "country, admin1, admin2, gid_2"
                admin_join_table = "gha.admin2" if admin_level == '2' else "gha.admin1"

                cursor.execute(f"""
                    WITH query_params AS (
                        SELECT %s::date as query_date
                    ),
                    first_forecast AS (
                        SELECT MIN(forecast_date) as forecast_date
                        FROM gha.multimodal_forecasts mf, query_params qp
                        WHERE mf.data_date = qp.query_date
                          AND mf.forecast_date >= qp.query_date
                    ),
                    points AS (
                        SELECT
                            cp.point_id,
                            cp.geom,
                            COALESCE(f.daily_avg, 0) as daily_avg
                        FROM gha.multimodal_control_points cp
                        CROSS JOIN query_params qp
                        CROSS JOIN first_forecast ff
                        LEFT JOIN gha.multimodal_forecasts f
                            ON f.point_id = cp.point_id
                            AND f.data_date = qp.query_date
                            AND f.forecast_date = ff.forecast_date
                    ),
                    risk_points AS (
                        SELECT
                            p.point_id,
                            p.geom,
                            CASE
                                WHEN p.daily_avg >= {emergency_threshold} THEN 'emergency'
                                WHEN p.daily_avg >= {alarm_threshold} THEN 'alarm'
                                WHEN p.daily_avg >= {warning_threshold} THEN 'warning'
                                ELSE 'normal'
                            END as risk_level
                        FROM points p
                    ),
                    point_admin AS (
                        SELECT
                            {admin_fields},
                            rp.risk_level
                        FROM risk_points rp
                        JOIN {admin_join_table} ad
                          ON ST_Within(rp.geom, ad.geom)
                        WHERE 1=1 {country_filter_sql}
                    ),
                    grouped AS (
                        SELECT
                            {admin_group},
                            risk_level,
                            COUNT(*) as point_count
                        FROM point_admin
                        GROUP BY {admin_group}, risk_level
                    ),
                    ranked AS (
                        SELECT
                            g.*,
                            ROW_NUMBER() OVER (
                                PARTITION BY {admin_group}
                                ORDER BY
                                    g.point_count DESC,
                                    CASE
                                        WHEN g.risk_level = 'emergency' THEN 4
                                        WHEN g.risk_level = 'alarm' THEN 3
                                        WHEN g.risk_level = 'warning' THEN 2
                                        ELSE 1
                                    END DESC
                            ) as rn
                        FROM grouped g
                    ),
                    totals AS (
                        SELECT
                            {admin_group},
                            SUM(point_count) as total_points
                        FROM grouped
                        GROUP BY {admin_group}
                    )
                    SELECT
                        r.country,
                        r.admin1,
                        r.admin2,
                        r.gid_2,
                        r.risk_level,
                        r.point_count as majority_points,
                        t.total_points
                    FROM ranked r
                    JOIN totals t
                      ON t.country = r.country
                     AND t.admin1 = r.admin1
                     AND (t.admin2 = r.admin2 OR (t.admin2 IS NULL AND r.admin2 IS NULL))
                     AND (t.gid_2 = r.gid_2 OR (t.gid_2 IS NULL AND r.gid_2 IS NULL))
                    WHERE r.rn = 1
                    ORDER BY r.country, r.admin1, r.admin2
                """, params)

                rows = cursor.fetchall()
                risk_by_admin = []
                for row in rows:
                    item = {
                        'country': row[0],
                        'admin1': row[1],
                        'admin2': row[2],
                        'gid_2': row[3],
                        'risk_level': row[4],
                        'majority_points': int(row[5] or 0),
                        'total_points': int(row[6] or 0),
                    }
                    if item['gid_2']:
                        item['key'] = item['gid_2']
                    elif item['admin2']:
                        item['key'] = f"{item['country']}-{item['admin1']}-{item['admin2']}"
                    else:
                        item['key'] = f"{item['country']}-{item['admin1']}"
                    risk_by_admin.append(item)

            except Exception as exc:
                response = JsonResponse({'error': f'Query failed: {str(exc)}'}, status=500)
                response['Access-Control-Allow-Origin'] = '*'
                return response

        response = JsonResponse({
            'date': query_date.strftime('%Y-%m-%d') if hasattr(query_date, 'strftime') else str(query_date),
            'admin_level': admin_level,
            'risk_by_admin': risk_by_admin,
            'count': len(risk_by_admin),
        })
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        response['Access-Control-Allow-Headers'] = 'Content-Type'
        return response


# =============================================================================
# FloodWatch: District Risk Levels API (gha.district_risk_levels)
# Allows experts to set risk levels at admin2 (district) level
# =============================================================================
class RiskAssessmentView(View):
    """
    API for district-level flood risk assessments.
    Experts can set risk levels for individual districts on the map.
    Data stored in gha.district_risk_levels table.
    """

    def get(self, request):
        from django.db import connection

        date_str = request.GET.get('date')
        expert_type = request.GET.get('expert_type')
        country = request.GET.get('country')

        with connection.cursor() as cursor:
            try:
                query = """
                    SELECT id, expert_type, assessment_date, country, admin1, admin2,
                           gid_2, risk_level, comment, created_at, updated_at
                    FROM gha.district_risk_levels
                    WHERE 1=1
                """
                params = []

                if date_str:
                    query += " AND assessment_date = %s"
                    params.append(date_str)

                if expert_type:
                    query += " AND expert_type = %s"
                    params.append(expert_type)

                if country:
                    query += " AND country = %s"
                    params.append(country)

                query += " ORDER BY country, admin1, admin2"

                cursor.execute(query, params)
                columns = [col[0] for col in cursor.description]
                assessments = []
                for row in cursor.fetchall():
                    item = dict(zip(columns, row))
                    for date_field in ['assessment_date', 'created_at', 'updated_at']:
                        if item.get(date_field):
                            item[date_field] = item[date_field].isoformat() if hasattr(item[date_field], 'isoformat') else str(item[date_field])
                    assessments.append(item)

            except Exception as e:
                assessments = []

        response = JsonResponse({'assessments': assessments, 'count': len(assessments)})
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response['Access-Control-Allow-Headers'] = 'Content-Type'
        return response

    def post(self, request):
        from django.db import connection
        import json

        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            response = JsonResponse({'error': 'Invalid JSON'}, status=400)
            response['Access-Control-Allow-Origin'] = '*'
            return response

        expert_type = data.get('expert_type', 'hydrologist')
        assessment_date = data.get('forecast_date') or data.get('assessment_date')
        country = data.get('country')
        admin1 = data.get('admin1')
        admin2 = data.get('admin2')
        risk_level = data.get('risk_level', 'normal')
        comment = data.get('comment', '')
        gid_2 = data.get('gid_2')

        if not all([assessment_date, country, admin1, admin2]):
            response = JsonResponse({'error': 'Missing required fields: date, country, admin1, admin2'}, status=400)
            response['Access-Control-Allow-Origin'] = '*'
            return response

        with connection.cursor() as cursor:
            try:
                cursor.execute("""
                    INSERT INTO gha.district_risk_levels
                        (expert_type, assessment_date, country, admin1, admin2, gid_2, risk_level, comment, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                    ON CONFLICT (expert_type, assessment_date, country, admin1, admin2)
                    DO UPDATE SET
                        risk_level = EXCLUDED.risk_level,
                        comment = EXCLUDED.comment,
                        gid_2 = EXCLUDED.gid_2,
                        updated_at = CURRENT_TIMESTAMP
                    RETURNING id
                """, [expert_type, assessment_date, country, admin1, admin2, gid_2, risk_level, comment])

                result = cursor.fetchone()
                assessment_id = result[0] if result else None

            except Exception as e:
                response = JsonResponse({'error': f'Database error: {str(e)}'}, status=500)
                response['Access-Control-Allow-Origin'] = '*'
                return response

        response = JsonResponse({
            'success': True,
            'id': assessment_id,
            'message': 'District risk level saved'
        })
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response['Access-Control-Allow-Headers'] = 'Content-Type'
        return response

    def options(self, request):
        """Handle CORS preflight"""
        response = JsonResponse({})
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response['Access-Control-Allow-Headers'] = 'Content-Type'
        return response


class CountryInundationView(View):
    """
    GET /api/country-inundation/?country=KE&date=...
    Serves exposure-based inundation impact stats from floodreport.flood_exposure_scores.
    Compatible with frontend CountryDetailView inundation widget.
    """

    def get(self, request):
        from django.db.models import Sum, Avg, Count, Q

        country_param = request.GET.get("country", "").strip()
        if not country_param:
            data = {"affected_population": "N/A", "affected_area_km2": "N/A",
                    "affected_cropland_km2": "N/A", "affected_infrastructure": "N/A"}
            return _add_cors_headers(JsonResponse(data))

        # Resolve country code to name
        country_name = ISO2_TO_COUNTRY_NAME.get(country_param.upper())
        if not country_name:
            # Try direct name match
            country_name = country_param

        try:
            from floodreport.models import FloodExposureScore

            qs = FloodExposureScore.objects.filter(country__iexact=country_name)
            if not qs.exists():
                # Try broader match
                qs = FloodExposureScore.objects.filter(country__icontains=country_name)

            if qs.exists():
                agg = qs.aggregate(
                    total_affected_pop=Sum("affected_population"),
                    total_flooded_area=Sum("flooded_area_km2"),
                    total_rp25_area=Sum("rp25_area_km2"),
                    total_rp100_area=Sum("rp100_area_km2"),
                    avg_score=Avg("composite_score"),
                )
                data = {
                    "affected_population": agg["total_affected_pop"] or 0,
                    "affected_area_km2": round(agg["total_flooded_area"] or 0, 1),
                    "affected_cropland_km2": "N/A",
                    "affected_infrastructure": "N/A",
                    "composite_score": round(agg["avg_score"] or 0, 4),
                    "rp25_area_km2": round(agg["total_rp25_area"] or 0, 1),
                    "rp100_area_km2": round(agg["total_rp100_area"] or 0, 1),
                }
            else:
                data = {"affected_population": 0, "affected_area_km2": 0,
                        "affected_cropland_km2": "N/A", "affected_infrastructure": "N/A"}

        except Exception:
            data = {"affected_population": "N/A", "affected_area_km2": "N/A",
                    "affected_cropland_km2": "N/A", "affected_infrastructure": "N/A"}

        return _add_cors_headers(JsonResponse(data))

    def options(self, request):
        response = JsonResponse({})
        return _add_cors_headers(response)


def country_inundation_view(request):
    return CountryInundationView.as_view()(request)


# =============================================================================
# CAP Alert Draft Creation API
# =============================================================================
class CAPDraftCreateView(View):
    """Create a draft CAP alert from a published expert assessment."""

    @classmethod
    def as_view(cls, **kwargs):
        from django.views.decorators.csrf import csrf_exempt
        return csrf_exempt(super().as_view(**kwargs))

    def post(self, request):
        import json

        try:
            data = json.loads(request.body) if request.body else {}
        except json.JSONDecodeError:
            response = JsonResponse({'error': 'Invalid JSON'}, status=400)
            response['Access-Control-Allow-Origin'] = '*'
            return response

        assessment_id = data.get('assessment_id')
        expires_hours = data.get('expires_hours', 48)

        if not assessment_id:
            response = JsonResponse({'success': False, 'message': 'assessment_id required'}, status=400)
            response['Access-Control-Allow-Origin'] = '*'
            return response

        try:
            from home.cap_bridge.creator import create_cap_draft_from_assessment
            cap_page = create_cap_draft_from_assessment(assessment_id, expires_hours)

            response = JsonResponse({
                'success': True,
                'cap_alert_id': cap_page.id,
                'edit_url': f'/cms-admin/pages/{cap_page.id}/edit/',
                'message': 'CAP alert draft created',
            })
            response['Access-Control-Allow-Origin'] = '*'
            return response
        except ValueError as e:
            response = JsonResponse({'success': False, 'message': str(e)}, status=404)
            response['Access-Control-Allow-Origin'] = '*'
            return response
        except Exception as e:
            response = JsonResponse({'success': False, 'message': str(e)}, status=500)
            response['Access-Control-Allow-Origin'] = '*'
            return response

    def options(self, request):
        response = JsonResponse({})
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response['Access-Control-Allow-Headers'] = 'Content-Type, X-CSRFToken, Authorization'
        return response


class CAPForecastDraftView(View):
    """Create CAP alert drafts from live multimodal forecast data."""

    @classmethod
    def as_view(cls, **kwargs):
        from django.views.decorators.csrf import csrf_exempt
        return csrf_exempt(super().as_view(**kwargs))

    def post(self, request):
        import json

        try:
            data = json.loads(request.body) if request.body else {}
        except json.JSONDecodeError:
            response = JsonResponse({'error': 'Invalid JSON'}, status=400)
            response['Access-Control-Allow-Origin'] = '*'
            return response

        country_code = data.get('country_code')  # Optional ISO-2, omit for all countries
        expires_hours = data.get('expires_hours', 48)

        try:
            from home.cap_bridge.creator import create_cap_draft_from_forecast
            results = create_cap_draft_from_forecast(
                country_code=country_code,
                expires_hours=expires_hours,
            )

            if not results:
                response = JsonResponse({
                    'success': True,
                    'message': 'No countries at warning level or above',
                    'drafts': [],
                })
                response['Access-Control-Allow-Origin'] = '*'
                return response

            response = JsonResponse({
                'success': True,
                'message': f'{len(results)} CAP draft(s) created',
                'drafts': results,
            })
            response['Access-Control-Allow-Origin'] = '*'
            return response
        except Exception as e:
            response = JsonResponse({'success': False, 'message': str(e)}, status=500)
            response['Access-Control-Allow-Origin'] = '*'
            return response

    def options(self, request):
        response = JsonResponse({})
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response['Access-Control-Allow-Headers'] = 'Content-Type, X-CSRFToken, Authorization'
        return response


# Register standard Wagtail API endpoints
try:
    from wagtail.api.v2.views import PagesAPIViewSet
    from wagtail.images.api.v2.views import ImagesAPIViewSet
    from wagtail.documents.api.v2.views import DocumentsAPIViewSet

    api_router.register_endpoint("pages", PagesAPIViewSet)
    api_router.register_endpoint("images", ImagesAPIViewSet)
    api_router.register_endpoint("documents", DocumentsAPIViewSet)
except Exception:
    # Silently fail if apps aren't ready yet - endpoints will be registered later
    pass
