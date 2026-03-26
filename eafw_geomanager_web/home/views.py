"""
Flood situation API views — served from Django CMS.
Adapted from eafw_api multimodal router (Hillary Koros, ICPAC).
"""
import json
from datetime import date as date_cls
from django.db import connection
from django.http import Http404, HttpResponse, JsonResponse
from django.views.decorators.cache import cache_page
from django.views.decorators.http import require_GET

# ── Constants ────────────────────────────────────────────────────────────────
COUNTRY_NAMES = {
    "ET": "Ethiopia", "KE": "Kenya", "UG": "Uganda", "SD": "Sudan",
    "SS": "South Sudan", "TZ": "Tanzania", "RW": "Rwanda", "BI": "Burundi",
    "SO": "Somalia", "DJ": "Djibouti", "ER": "Eritrea",
}

IGAD_MEMBER_CODES = ("ET", "ER", "KE", "UG", "SD", "SS", "TZ", "RW", "BI", "SO", "DJ")

ISO3_TO_ISO2 = {
    "ETH": "ET", "ERI": "ER", "KEN": "KE", "UGA": "UG", "SDN": "SD",
    "SSD": "SS", "TZA": "TZ", "RWA": "RW", "BDI": "BI", "SOM": "SO", "DJI": "DJ",
}
ISO2_TO_ISO3 = {v: k for k, v in ISO3_TO_ISO2.items()}

FALLBACK_WARNING = 300.0
FALLBACK_ALARM = 500.0
FALLBACK_EMERGENCY = 750.0

# Check if per-point thresholds table exists at module load;
# fall back to fixed thresholds if it doesn't.
def _threshold_table_exists():
    try:
        with connection.cursor() as c:
            c.execute(
                "SELECT 1 FROM information_schema.tables "
                "WHERE table_schema='gha' AND table_name='point_alert_thresholds'"
            )
            return c.fetchone() is not None
    except Exception:
        return False


_HAS_THRESHOLDS = None  # lazy-checked on first request


def _get_threshold_sql():
    global _HAS_THRESHOLDS
    if _HAS_THRESHOLDS is None:
        _HAS_THRESHOLDS = _threshold_table_exists()
    if _HAS_THRESHOLDS:
        return (
            "LEFT JOIN gha.point_alert_thresholds pt ON pt.point_id = cp.point_id",
            f"COALESCE(pt.warning_threshold, {FALLBACK_WARNING})",
            f"COALESCE(pt.alarm_threshold, {FALLBACK_ALARM})",
            f"COALESCE(pt.emergency_threshold, {FALLBACK_EMERGENCY})",
        )
    return ("", str(FALLBACK_WARNING), str(FALLBACK_ALARM), str(FALLBACK_EMERGENCY))


THRESHOLD_JOIN, WARNING_SQL, ALARM_SQL, EMERGENCY_SQL = "", str(FALLBACK_WARNING), str(FALLBACK_ALARM), str(FALLBACK_EMERGENCY)

ADMIN0_CC_SQL = (
    "CASE UPPER(TRIM(COALESCE(a0.gid_0, ''))) "
    "WHEN 'ETH' THEN 'ET' WHEN 'KEN' THEN 'KE' WHEN 'UGA' THEN 'UG' "
    "WHEN 'SDN' THEN 'SD' WHEN 'SSD' THEN 'SS' WHEN 'TZA' THEN 'TZ' "
    "WHEN 'RWA' THEN 'RW' WHEN 'BDI' THEN 'BI' WHEN 'SOM' THEN 'SO' "
    "WHEN 'DJI' THEN 'DJ' WHEN 'ERI' THEN 'ER' ELSE 'UN' END"
)

POINT_CC_SQL = (
    "COALESCE("
    "NULLIF(UPPER(TRIM(cp.country_code)), ''), "
    f"(SELECT {ADMIN0_CC_SQL} FROM gha.admin0 a0 WHERE ST_Within(cp.geom, a0.geom) LIMIT 1), "
    "'UN')"
)

WHCA_CODES = ("SD", "SS", "UG", "ET", "RW")
WHCA_CODES_SQL = ",".join(f"'{c}'" for c in WHCA_CODES)
WHCA_WHERE = f"({POINT_CC_SQL}) IN ({WHCA_CODES_SQL})"


def _scope_where(scope):
    """Return a SQL WHERE clause fragment for scope filtering."""
    if scope == "whca":
        return f"WHERE {WHCA_WHERE}"
    return ""


# ── Shared CTE builder ────────────────────────────────────────────────────────
def _point_data_cte(scope="all"):
    """Build the point_data CTE with threshold SQL resolved at runtime."""
    tj, w, a, e = _get_threshold_sql()
    scope_sql = _scope_where(scope)
    return f"""
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
            ({POINT_CC_SQL}) as country_code,
            COALESCE(f.daily_avg, 0) as daily_avg,
            CASE
                WHEN COALESCE(f.daily_avg, 0) >= {e} THEN 'emergency'
                WHEN COALESCE(f.daily_avg, 0) >= {a} THEN 'alarm'
                WHEN COALESCE(f.daily_avg, 0) >= {w} THEN 'warning'
                ELSE 'normal'
            END as risk_level
        FROM gha.multimodal_control_points cp
        {tj}
        CROSS JOIN query_params qp
        CROSS JOIN first_forecast ff
        LEFT JOIN gha.multimodal_forecasts f
            ON f.point_id = cp.point_id
            AND f.data_date = qp.query_date
            AND f.forecast_date = ff.forecast_date
        {scope_sql}
    )
"""


def _latest_data_date():
    with connection.cursor() as c:
        c.execute("SELECT MAX(data_date) FROM gha.multimodal_forecasts")
        row = c.fetchone()
        return row[0] if row else None


def _resolve_summary_query_date(request):
    requested_date = (request.GET.get("date") or "").strip()
    if requested_date:
        try:
            parsed_date = date_cls.fromisoformat(requested_date)
        except ValueError:
            parsed_date = None
        if parsed_date is not None:
            with connection.cursor() as c:
                c.execute(
                    "SELECT 1 FROM gha.multimodal_forecasts WHERE data_date = %s LIMIT 1",
                    [str(parsed_date)],
                )
                if c.fetchone():
                    return parsed_date
    return _latest_data_date()


# ── /api/flood/forecast-dates ────────────────────────────────────────────────
@require_GET
@cache_page(60)
def forecast_dates(request):
    """Available multimodal run dates for minimap and other date selectors."""
    try:
        limit = int(request.GET.get("limit", 365))
    except (TypeError, ValueError):
        limit = 365

    limit = max(1, min(limit, 2000))

    with connection.cursor() as c:
        c.execute(
            """
            SELECT DISTINCT data_date
            FROM gha.multimodal_forecasts
            WHERE data_date IS NOT NULL
            ORDER BY data_date DESC
            LIMIT %s
            """,
            [limit],
        )
        rows = c.fetchall()

    timestamps = [str(row[0]) for row in rows if row and row[0] is not None]
    return JsonResponse({
        "timestamps": timestamps,
        "dates": timestamps,
        "count": len(timestamps),
    })


@require_GET
@cache_page(60)
def google_flood_dates(request):
    """Available synced dates for Google Flood data."""
    try:
        limit = int(request.GET.get("limit", 365))
    except (TypeError, ValueError):
        limit = 365

    limit = max(1, min(limit, 2000))

    with connection.cursor() as c:
        c.execute(
            """
            SELECT DISTINCT data_date
            FROM gha.google_flood_points_latest
            WHERE data_date IS NOT NULL
            ORDER BY data_date DESC
            LIMIT %s
            """,
            [limit],
        )
        rows = c.fetchall()

    timestamps = [str(row[0]) for row in rows if row and row[0] is not None]
    return JsonResponse({
        "timestamps": timestamps,
        "dates": timestamps,
        "count": len(timestamps),
    })


# ── /api/v1/wrf/daily-rainfall/dates ────────────────────────────────────────
@require_GET
@cache_page(60)
def wrf_daily_rainfall_dates(request):
    """Available weekly WRF forecast dates for total-rainfall layers."""
    with connection.cursor() as c:
        c.execute(
            """
            SELECT DISTINCT forecast_date
            FROM wrf.daily_rainfall
            WHERE forecast_date IS NOT NULL
            ORDER BY forecast_date DESC
            """
        )
        rows = c.fetchall()

    timestamps = [str(row[0]) for row in rows if row and row[0] is not None]
    return JsonResponse({"timestamps": timestamps, "dates": timestamps, "count": len(timestamps)})


# ── /api/v1/wrf/extreme-rainfall/dates ──────────────────────────────────────
@require_GET
@cache_page(60)
def wrf_extreme_rainfall_dates(request):
    """Available forecast dates for WRF extreme rainfall layers."""
    with connection.cursor() as c:
        c.execute(
            """
            SELECT DISTINCT forecast_date
            FROM wrf.extreme_rainfall
            WHERE forecast_date IS NOT NULL
            ORDER BY forecast_date DESC
            """
        )
        rows = c.fetchall()

    timestamps = [str(row[0]) for row in rows if row and row[0] is not None]
    return JsonResponse({"timestamps": timestamps, "dates": timestamps, "count": len(timestamps)})


@require_GET
@cache_page(60)
def admin_boundary_tiles(request, z, x, y):
    """
    Compatibility vector-tile endpoint for boundary overlays.
    Reuse the clean gha boundary functions and pick the scope-aware one from
    the current request params so the mapviewer and homepage can share the
    same boundary URL.
    """
    scope = (request.GET.get("scope") or "").strip().lower()
    project_countries = (request.GET.get("project_countries") or "").strip()
    if project_countries == "__none__":
        project_countries = ""

    country_name = (request.GET.get("country_name") or "").strip() or None
    region_name = (request.GET.get("region_name") or "").strip() or None
    district_name = (request.GET.get("district_name") or "").strip() or None

    requested_level = request.GET.get("admin_level") or request.GET.get("border_level")
    if requested_level in {"0", "1", "2"}:
        admin_level = int(requested_level)
    elif z <= 5:
        admin_level = 0
    elif z <= 7:
        admin_level = 1
    else:
        admin_level = 2

    with connection.cursor() as c:
        if scope == "whca":
            c.execute(
                "SELECT gha.admin_whca(%s, %s, %s, %s, %s, %s, %s)",
                [z, x, y, admin_level, country_name, region_name, district_name],
            )
        elif project_countries:
            c.execute(
                "SELECT gha.admin_by_project(%s, %s, %s, %s, %s, %s, %s, %s)",
                [z, x, y, admin_level, project_countries, country_name, region_name, district_name],
            )
        elif country_name or region_name or district_name:
            c.execute(
                "SELECT gha.admin_clipped(%s, %s, %s, %s, %s, %s, %s)",
                [z, x, y, admin_level, country_name, region_name, district_name],
            )
        else:
            c.execute("SELECT gha.admin_by_zoom(%s, %s, %s, %s)", [z, x, y, country_name])
        row = c.fetchone()

    tile = row[0] if row else None
    if not tile:
        raise Http404()

    return HttpResponse(tile, content_type="application/x-protobuf")


# ── /api/flood/situation-summary ─────────────────────────────────────────────
@require_GET
@cache_page(60)
def situation_summary(request):
    """Risk ticker data: emergency/alarm/warning counts + peak day."""
    scope = request.GET.get("scope", "all")
    if scope not in ("all", "whca"):
        scope = "all"
    query_date = _resolve_summary_query_date(request)
    if not query_date:
        return JsonResponse({"error": "No forecast data available"}, status=404)

    tj, w, a, e = _get_threshold_sql()
    peak_scope_where = ""
    if scope == "whca":
        peak_scope_where = f"AND {WHCA_WHERE}"
    sql = _point_data_cte(scope) + f"""
    SELECT
        (SELECT COUNT(*) FROM point_data WHERE risk_level = 'emergency') as emergency,
        (SELECT COUNT(*) FROM point_data WHERE risk_level = 'alarm') as alarm,
        (SELECT COUNT(*) FROM point_data WHERE risk_level = 'warning') as warning,
        (SELECT COUNT(*) FROM point_data WHERE risk_level = 'normal') as normal,
        (SELECT COUNT(*) FROM point_data) as total,
        (
            SELECT mf.forecast_date
            FROM gha.multimodal_forecasts mf
            JOIN gha.multimodal_control_points cp ON cp.point_id = mf.point_id
            {tj}
            WHERE mf.data_date = %s
              AND COALESCE(mf.daily_avg, 0) >= {w}
              {peak_scope_where}
            GROUP BY mf.forecast_date
            ORDER BY COUNT(*) DESC
            LIMIT 1
        ) as peak_day
    """

    with connection.cursor() as c:
        c.execute(sql, [str(query_date), str(query_date)])
        row = c.fetchone()

    return JsonResponse({
        "data_date": str(query_date),
        "risk_counts": {
            "emergency": row[0] or 0,
            "alarm": row[1] or 0,
            "warning": row[2] or 0,
            "normal": row[3] or 0,
            "total": row[4] or 0,
        },
        "peak_day": str(row[5]) if row[5] else None,
    })


# ── /api/flood/country-summary ───────────────────────────────────────────────
@require_GET
@cache_page(60)
def country_summary(request):
    """Country-level alert counts with bounding boxes for homepage."""
    scope = request.GET.get("scope", "all")
    if scope not in ("all", "whca"):
        scope = "all"
    query_date = _resolve_summary_query_date(request)
    if not query_date:
        return JsonResponse({"error": "No forecast data available"}, status=404)

    sql = _point_data_cte(scope) + """
    , country_agg AS (
        SELECT
            country_code,
            SUM(CASE WHEN risk_level = 'emergency' THEN 1 ELSE 0 END) as emergency,
            SUM(CASE WHEN risk_level = 'alarm' THEN 1 ELSE 0 END) as alarm,
            SUM(CASE WHEN risk_level = 'warning' THEN 1 ELSE 0 END) as warning,
            COUNT(*) as total_points,
            SUM(CASE WHEN risk_level = 'emergency' THEN 100 ELSE 0 END) +
            SUM(CASE WHEN risk_level = 'alarm' THEN 10 ELSE 0 END) +
            SUM(CASE WHEN risk_level = 'warning' THEN 1 ELSE 0 END) as severity_score
        FROM point_data
        GROUP BY country_code
    ),
    country_bounds AS (
        SELECT
            cc as country_code,
            MIN(ST_XMin(ST_Envelope(geom))) as west,
            MIN(ST_YMin(ST_Envelope(geom))) as south,
            MAX(ST_XMax(ST_Envelope(geom))) as east,
            MAX(ST_YMax(ST_Envelope(geom))) as north
        FROM (
            SELECT {admin0_cc} as cc, a0.geom
            FROM gha.admin0 a0
            WHERE a0.geom IS NOT NULL
        ) t
        WHERE cc != 'UN'
        GROUP BY cc
    )
    SELECT
        ca.country_code,
        ca.emergency, ca.alarm, ca.warning, ca.total_points, ca.severity_score,
        cb.west, cb.south, cb.east, cb.north
    FROM country_agg ca
    LEFT JOIN country_bounds cb ON cb.country_code = ca.country_code
    ORDER BY ca.severity_score DESC
    """.format(admin0_cc=ADMIN0_CC_SQL)

    with connection.cursor() as c:
        c.execute(sql, [str(query_date)])
        rows = c.fetchall()

    seen = set()
    countries = []
    for r in rows:
        code = r[0] or "UN"
        if code == "UN":
            continue
        seen.add(code)
        entry = {
            "code": code,
            "name": COUNTRY_NAMES.get(code, code),
            "emergency": r[1] or 0,
            "alarm": r[2] or 0,
            "warning": r[3] or 0,
            "total_points": r[4] or 0,
        }
        if r[6] is not None:
            entry["bounds"] = {"west": r[6], "south": r[7], "east": r[8], "north": r[9]}
        else:
            entry["bounds"] = None
        countries.append(entry)

    # Pad members with no data — only WHCA countries when scope=whca
    pad_codes = WHCA_CODES if scope == "whca" else IGAD_MEMBER_CODES
    for code in pad_codes:
        if code in seen:
            continue
        iso3 = ISO2_TO_ISO3.get(code, code)
        with connection.cursor() as c:
            c.execute(
                "SELECT ST_XMin(ST_Envelope(geom)), ST_YMin(ST_Envelope(geom)), "
                "ST_XMax(ST_Envelope(geom)), ST_YMax(ST_Envelope(geom)) "
                "FROM gha.admin0 WHERE UPPER(gid_0) = %s LIMIT 1",
                [iso3],
            )
            br = c.fetchone()
        bounds = {"west": br[0], "south": br[1], "east": br[2], "north": br[3]} if br and br[0] is not None else None
        countries.append({
            "code": code, "name": COUNTRY_NAMES.get(code, code),
            "emergency": 0, "alarm": 0, "warning": 0, "total_points": 0,
            "bounds": bounds,
        })

    return JsonResponse({
        "data_date": str(query_date),
        "countries": countries,
    })


# ── /api/flood/forecast-timeseries/<point_id> ────────────────────────────────
@require_GET
@cache_page(60)
def forecast_timeseries(request, point_id):
    """Forecast time series for a single control point (mapviewer chart popup)."""
    requested_date = (request.GET.get("date") or "").strip()
    query_date = None
    if requested_date:
        try:
            query_date = date_cls.fromisoformat(requested_date)
        except ValueError:
            query_date = None

    threshold_join, warning_sql, alarm_sql, emergency_sql = _get_threshold_sql()

    def _fetch_rows(run_date):
        with connection.cursor() as c:
            c.execute(
                f"""
                WITH selected_run AS (
                    SELECT COALESCE(
                        %s::date,
                        (
                            SELECT MAX(mf.data_date)
                            FROM gha.multimodal_forecasts mf
                            WHERE mf.point_id = %s
                        )
                    ) AS data_date
                )
                SELECT
                    mf.data_date,
                    mf.forecast_date,
                    mf.daily_avg,
                    mf.daily_max,
                    mf.daily_min,
                    mf.geosfm,
                    mf.floodproof,
                    mf.mike_hydro_rfe,
                    mf.mike_hydro_chirp,
                    mf.mike_hydro_imerg,
                    cp.admin_name,
                    {warning_sql} AS warning_threshold,
                    {alarm_sql} AS alarm_threshold,
                    {emergency_sql} AS emergency_threshold
                FROM gha.multimodal_forecasts mf
                JOIN gha.multimodal_control_points cp
                  ON cp.point_id = mf.point_id
                {threshold_join}
                CROSS JOIN selected_run sr
                WHERE mf.point_id = %s
                  AND mf.data_date = sr.data_date
                ORDER BY mf.forecast_date ASC
                """,
                [run_date, point_id, point_id],
            )
            return c.fetchall()

    rows = _fetch_rows(query_date)
    if not rows and query_date is not None:
        rows = _fetch_rows(None)

    if not rows:
        return JsonResponse({"point_id": point_id, "count": 0, "forecasts": [], "timeseries": []})

    data_date = rows[0][0]
    admin_name = rows[0][10]
    thresholds = {
        "warning": rows[0][11],
        "alarm": rows[0][12],
        "emergency": rows[0][13],
    }

    forecasts = []
    timeseries = []
    for r in rows:
        forecast_entry = {
            "date": str(r[1]),
            "daily_avg": r[2],
            "daily_max": r[3],
            "daily_min": r[4],
            "GeoSFM": r[5],
            "Floodproof": r[6],
            "Mike_Hydro_RFE": r[7],
            "Mike_Hydro_CHIRP": r[8],
            "Mike_Hydro_IMERG": r[9],
        }
        forecasts.append(forecast_entry)
        timeseries.append({
            "data_date": str(r[0]),
            "forecast_date": str(r[1]),
            "daily_avg": r[2],
            "daily_max": r[3],
            "daily_min": r[4],
            "geosfm": r[5],
            "floodproof": r[6],
            "mike_hydro_rfe": r[7],
            "mike_hydro_chirp": r[8],
            "mike_hydro_imerg": r[9],
        })

    return JsonResponse({
        "point_id": point_id,
        "admin_name": admin_name,
        "data_date": str(data_date),
        "thresholds": thresholds,
        "forecasts": forecasts,
        "timeseries": timeseries,
        "count": len(timeseries),
    })
