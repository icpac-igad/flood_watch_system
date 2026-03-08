"""Build CAP area dicts from country geometries."""

import json
from django.db import connection


def build_cap_areas_for_country(country_code, country_name):
    """
    Build CAP area list from gha.admin0 country boundary.

    gha.admin0 columns: id, geom, gid_0 (ISO3), country (name)
    """
    areas = []
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT country, ST_AsGeoJSON(geom)
            FROM gha.admin0
            WHERE UPPER(gid_0) = UPPER(%s) OR LOWER(country) = LOWER(%s)
            LIMIT 1
        """, [country_code, country_name])
        row = cursor.fetchone()
        if row:
            areas.append({
                "areaDesc": row[0],
                "polygon": json.loads(row[1]),
                "geocode": {"valueName": "ISO3166-1", "value": country_code},
            })
    return areas
