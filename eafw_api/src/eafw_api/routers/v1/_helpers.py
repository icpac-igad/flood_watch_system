"""
Shared constants and async utilities for FloodWatch API routers.
"""
from datetime import datetime

# Default thresholds
DEFAULT_WARNING_THRESHOLD = 300.0
DEFAULT_ALARM_THRESHOLD = 500.0
DEFAULT_EMERGENCY_THRESHOLD = 750.0

# WHCA project countries
WHCA_COUNTRY_CODES = ("SD", "SS", "UG", "ET", "RW")
WHCA_COUNTRY_CODES_SQL = ",".join(f"'{c}'" for c in WHCA_COUNTRY_CODES)

# Country name <-> ISO2
COUNTRY_NAME_TO_ISO2 = {
    "burundi": "BI", "djibouti": "DJ", "eritrea": "ER", "ethiopia": "ET",
    "kenya": "KE", "rwanda": "RW", "somalia": "SO", "south sudan": "SS",
    "sudan": "SD", "tanzania": "TZ", "uganda": "UG", "zanzibar": "TZ",
    "region": "REGION", "east africa region": "REGION",
}

# Accept legacy/alternate codes from older payloads and map previews.
ISO_ALIAS_TO_ISO2 = {
    "BI": "BI", "BD": "BI", "BDI": "BI",
    "DJ": "DJ", "DJI": "DJ",
    "ER": "ER", "ERI": "ER",
    "ET": "ET", "ETH": "ET",
    "KE": "KE", "KEN": "KE",
    "RW": "RW", "RWA": "RW",
    "SO": "SO", "SOM": "SO",
    "SS": "SS", "SSD": "SS",
    "SD": "SD", "SDN": "SD",
    "TZ": "TZ", "TZA": "TZ",
    "UG": "UG", "UGA": "UG",
}

ISO2_TO_COUNTRY_NAME = {
    "BI": "Burundi", "DJ": "Djibouti", "ER": "Eritrea", "ET": "Ethiopia",
    "KE": "Kenya", "RW": "Rwanda", "SO": "Somalia", "SS": "South Sudan",
    "SD": "Sudan", "TZ": "Tanzania", "UG": "Uganda",
    "REGION": "East Africa Region",
}

# SQL fragments for point country code resolution
ADMIN0_COUNTRY_CODE_SQL = (
    "CASE UPPER(TRIM(COALESCE(a0.gid_0, ''))) "
    "WHEN 'ETH' THEN 'ET' WHEN 'KEN' THEN 'KE' WHEN 'UGA' THEN 'UG' "
    "WHEN 'SDN' THEN 'SD' WHEN 'SSD' THEN 'SS' WHEN 'TZA' THEN 'TZ' "
    "WHEN 'RWA' THEN 'RW' WHEN 'BDI' THEN 'BI' WHEN 'SOM' THEN 'SO' "
    "WHEN 'DJI' THEN 'DJ' WHEN 'ERI' THEN 'ER' "
    "ELSE 'UN' END"
)

POINT_COUNTRY_CODE_SQL = (
    "COALESCE("
    "NULLIF(UPPER(TRIM(cp.country_code)), ''), "
    f"(SELECT {ADMIN0_COUNTRY_CODE_SQL} FROM gha.admin0 a0 "
    "WHERE ST_Within(cp.geom, a0.geom) LIMIT 1), "
    "'UN')"
)

WHCA_SCOPE_SQL_CONDITION = (
    "(COALESCE(cp.whca_selected, FALSE) IS TRUE OR "
    f"{POINT_COUNTRY_CODE_SQL} IN ({WHCA_COUNTRY_CODES_SQL}))"
)


def parse_query_date(date_str):
    """Parse YYYY-MM-DD or return None."""
    if not date_str:
        return None
    return datetime.strptime(date_str, "%Y-%m-%d").date()


def normalize_country_code(raw_value):
    """Normalize a raw country name/code to ISO2 or REGION."""
    value = (raw_value or "").strip()
    if not value:
        return ""
    mapped = COUNTRY_NAME_TO_ISO2.get(value.lower())
    if mapped:
        return mapped
    upper = value.upper()
    if upper == "REGION":
        return "REGION"
    alias = ISO_ALIAS_TO_ISO2.get(upper)
    if alias:
        return alias
    if len(upper) == 2 and upper.isalpha():
        return upper
    return value


def coerce_bool(value, default=False):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in ("1", "true", "yes", "on"):
        return True
    if text in ("0", "false", "no", "off"):
        return False
    return default


def parse_creator_metadata(created_by):
    raw = (created_by or "").strip()
    if not raw:
        return {"creator_type": "unknown", "contributor_name": "", "contributor_country": ""}
    parts = raw.split("|")
    if len(parts) >= 3 and parts[0] in ("kpp", "public"):
        return {
            "creator_type": "key_point_person" if parts[0] == "kpp" else "public",
            "contributor_name": parts[1].strip(),
            "contributor_country": normalize_country_code(parts[2]),
        }
    return {"creator_type": "legacy", "contributor_name": raw, "contributor_country": ""}


def format_report_key(expert_type, country_code, assessment_date):
    prefix = (expert_type or "general").strip().lower()
    suffix = (normalize_country_code(country_code) or "REGION").upper()
    date_part = (assessment_date or "").strip()
    return f"{prefix}_{suffix}_{date_part}"


async def resolve_filter_geometry_ewkt(conn, country_name="", region_name="", district_name="", project_countries=None):
    """Async version of _resolve_filter_geometry_ewkt."""
    country_name = (country_name or "").strip()
    region_name = (region_name or "").strip()
    district_name = (district_name or "").strip()
    project_countries = project_countries or []

    if district_name:
        row = await conn.fetchrow(
            """SELECT ST_AsEWKT(geom) FROM gha.admin2
               WHERE LOWER(name_2) = LOWER($1)
                 AND ($2 = '' OR LOWER(name_1) = LOWER($2))
                 AND ($3 = '' OR LOWER(country) = LOWER($3))
               LIMIT 1""",
            district_name, region_name, country_name,
        )
    elif region_name:
        row = await conn.fetchrow(
            """SELECT ST_AsEWKT(geom) FROM gha.admin1
               WHERE LOWER(name_1) = LOWER($1) AND ($2 = '' OR LOWER(country) = LOWER($2))
               LIMIT 1""",
            region_name, country_name,
        )
    elif country_name:
        row = await conn.fetchrow(
            "SELECT ST_AsEWKT(geom) FROM gha.admin0 WHERE LOWER(country) = LOWER($1) LIMIT 1",
            country_name,
        )
    elif project_countries:
        row = await conn.fetchrow(
            "SELECT ST_AsEWKT(ST_Union(geom)) FROM gha.admin0 WHERE country = ANY($1)",
            project_countries,
        )
    else:
        return None

    return row[0] if row and row[0] else None
