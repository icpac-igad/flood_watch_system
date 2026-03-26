import json
from copy import deepcopy
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import pytz
from django import template
from django.conf import settings
from django.db import connection

from mapwidget.models import MapWidgetSettings

register = template.Library()


@register.filter(name="jsonify")
def jsonify(value):
    """Serialize a Python object to a JSON string safe for use in HTML attributes."""
    return json.dumps(value) if value is not None else "null"


def _get_legend(layer):
    """Fetch legend config for a layer without letting errors propagate."""
    try:
        return layer.get_legend_config()
    except TypeError:
        pass
    try:
        return layer.get_legend_config(request=None)
    except Exception:
        pass
    return None


RISK_LABEL_MAP = {
    "emergency": "Extreme",
    "alarm": "Severe",
    "warning": "Moderate",
    "normal": "Normal",
}

RISK_COLOR_MAP = {
    "normal": "#b0b0b0",
}


def _get_minimap_basemap():
    """Read the current MapViewer default basemap from Geomanager settings."""
    try:
        from geomanager.models import GeomanagerSettings

        gm_settings = GeomanagerSettings.objects.first()
        if not gm_settings:
            return None, {}

        style_url = None
        if gm_settings.tile_gl_source:
            style_url = gm_settings.tile_gl_source.map_style_url

        default_basemap = {}
        base_maps = list(gm_settings.base_maps or [])
        selected = None
        for block in base_maps:
            value = getattr(block, "value", None) or {}
            if value.get("default"):
                selected = value
                break
        if selected is None and base_maps:
            selected = getattr(base_maps[0], "value", None) or {}

        if selected:
            default_basemap = {
                "label": str(selected.get("label") or ""),
                "background_color": str(selected.get("backgroundColor") or ""),
                "basemap_group": str(selected.get("basemapGroup") or ""),
                "labels_group": str(selected.get("labelsGroup") or ""),
                "url": str(selected.get("url") or ""),
            }

        return style_url, default_basemap
    except Exception:
        return None, {}


def _get_mapviewer_default_style():
    """Load the same default basemap style JSON used by the MapViewer."""
    try:
        style_path = Path(__file__).resolve().parents[1] / "data" / "mapviewer_default_style.json"
        with style_path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except Exception:
        return None


def _normalize_homepage_tile_url(tile_url):
    """Normalize homepage minimap URLs without changing the wider layer config."""
    if not tile_url:
        return tile_url

    parsed = urlsplit(tile_url)
    rewritten_path = parsed.path.replace(
        "/pg/tileserv/gha.multimodal_points_clustered_project/",
        "/pg/tileserv/gha.multimodal_points_raw/",
    ).replace(
        "/pg/tileserv/gha.multimodal_points_clustered/",
        "/pg/tileserv/gha.multimodal_points_raw/",
    )
    normalized = tile_url
    if rewritten_path != parsed.path:
        query_pairs = [
            (key, value)
            for key, value in parse_qsl(parsed.query, keep_blank_values=True)
            if key != "cluster_zoom"
        ]
        normalized = urlunsplit(
            (parsed.scheme, parsed.netloc, rewritten_path, urlencode(query_pairs), parsed.fragment)
        )

    if "/pg/tileserv/gha.multimodal_points_raw/" in normalized and "project_countries=" not in normalized:
        separator = "&" if "?" in normalized else "?"
        normalized = f"{normalized}{separator}project_countries=__none__"

    if "/pg/tileserv/gha.multimodal_points_raw/" in normalized and "date={time}" not in normalized and "date=" not in normalized:
        separator = "&" if "?" in normalized else "?"
        normalized = f"{normalized}{separator}date={{time}}"

    if "/mapserver/?" in normalized and "LAYERS=wrf_" in normalized:
        normalized = normalized.replace("/mapserver/?", "/mapcache/?", 1)
    normalized = normalized.replace(
        "BBOX={bbox-epsg-3857}?time={time}",
        "BBOX={bbox-epsg-3857}&time={time}",
    )
    return normalized


def _fetch_date_strings(sql):
    try:
        with connection.cursor() as cursor:
            cursor.execute(sql)
            rows = cursor.fetchall()
    except Exception:
        return []

    return [str(row[0]) for row in rows if row and row[0] is not None]


def _fetch_date_pairs(sql):
    try:
        with connection.cursor() as cursor:
            cursor.execute(sql)
            rows = cursor.fetchall()
    except Exception:
        return []

    pairs = []
    for row in rows:
        if not row or len(row) < 2 or row[0] is None:
            continue
        pairs.append((str(row[0]), str(row[1]) if row[1] is not None else None))
    return pairs


def _get_available_times_for_tile_json(tile_json_url):
    tile_json_url = str(tile_json_url or "")

    if "/api/flood/forecast-dates" in tile_json_url:
        return _fetch_date_strings(
            """
            SELECT DISTINCT data_date
            FROM gha.multimodal_forecasts
            WHERE data_date IS NOT NULL
            ORDER BY data_date DESC
            """
        )

    if "/api/flood/google-flood-dates" in tile_json_url:
        return _fetch_date_strings(
            """
            SELECT DISTINCT data_date
            FROM gha.google_flood_points_latest
            WHERE data_date IS NOT NULL
            ORDER BY data_date DESC
            """
        )

    if "/api/v1/wrf/extreme-rainfall/dates" in tile_json_url:
        return _fetch_date_strings(
            """
            SELECT DISTINCT forecast_date
            FROM wrf.extreme_rainfall
            WHERE forecast_date IS NOT NULL
            ORDER BY forecast_date DESC
            """
        )

    if "/api/v1/wrf/daily-rainfall/dates" in tile_json_url:
        return _fetch_date_strings(
            """
            SELECT DISTINCT forecast_date
            FROM wrf.daily_rainfall
            WHERE forecast_date IS NOT NULL
            ORDER BY forecast_date DESC
            """
        )

    return []


def _get_date_meta_for_tile_json(tile_json_url):
    tile_json_url = str(tile_json_url or "")

    if "/api/flood/forecast-dates" in tile_json_url:
        pairs = _fetch_date_pairs(
            """
            SELECT
                data_date,
                MAX(forecast_date) AS latest_forecast_date
            FROM gha.multimodal_forecasts
            WHERE data_date IS NOT NULL
            GROUP BY data_date
            ORDER BY data_date DESC
            """
        )
        return {
            data_date: {
                "initialized": data_date,
                "latest": latest_forecast_date or data_date,
            }
            for data_date, latest_forecast_date in pairs
        }

    if "/api/flood/google-flood-dates" in tile_json_url:
        dates = _fetch_date_strings(
            """
            SELECT DISTINCT data_date
            FROM gha.google_flood_points_latest
            WHERE data_date IS NOT NULL
            ORDER BY data_date DESC
            """
        )
        return {
            value: {
                "initialized": value,
                "latest": value,
            }
            for value in dates
        }

    if "/api/v1/wrf/extreme-rainfall/dates" in tile_json_url or "/api/v1/wrf/daily-rainfall/dates" in tile_json_url:
        dates = _fetch_date_strings(
            """
            SELECT forecast_date
            FROM (
                SELECT DISTINCT forecast_date
                FROM wrf.extreme_rainfall
                WHERE forecast_date IS NOT NULL
                UNION
                SELECT DISTINCT forecast_date
                FROM wrf.daily_rainfall
                WHERE forecast_date IS NOT NULL
            ) dates
            ORDER BY forecast_date DESC
            """
        )
        return {
            value: {
                "initialized": value,
                "latest": value,
            }
            for value in dates
        }

    return {}


def _normalize_legend(legend_config):
    """Adjust homepage risk legend labels without changing underlying alert keys."""
    if not isinstance(legend_config, dict):
        return legend_config

    items = legend_config.get("items")
    if not isinstance(items, list) or not items:
        return legend_config

    normalized = deepcopy(legend_config)
    changed = False

    for item in normalized.get("items", []):
        name = str(item.get("name") or "").strip()
        if not name:
            continue

        head, _, _ = name.partition(" ")
        alert_key = head.lower()
        display_label = RISK_LABEL_MAP.get(alert_key)
        if not display_label:
            continue

        item["alert_key"] = alert_key
        item["name"] = display_label
        if alert_key in RISK_COLOR_MAP:
            item["color"] = RISK_COLOR_MAP[alert_key]
        changed = True

    return normalized if changed else legend_config


@register.inclusion_tag("mapwidget/map_widget.html")
def render_map_widget():
    mw = MapWidgetSettings.load()

    entries = []
    for entry in mw.map_datasets.order_by("sort_order"):
        enriched = {
            "title": entry.title,
            "icon": entry.icon,
            "default_active": entry.default_active,
            "dataset_id": entry.dataset_id,
            "layers": [],  # [{tile_url, layer_type, title, legend}, ...]
            "latest_time": None,
            "available_times": [],
            "date_meta": {},
        }

        if not entry.dataset_id:
            entries.append(enriched)
            continue

        try:
            from geomanager.models import Dataset

            dataset = Dataset.objects.get(id=entry.dataset_id)
        except Exception:
            entries.append(enriched)
            continue

        layers_qs = dataset.layers
        if layers_qs is not None:
            for layer in layers_qs.all():
                # Get tile URL — skip this layer if it fails or has no tiles
                try:
                    lc = layer.layer_config
                    if callable(lc):
                        lc = lc()
                    source = lc.get("source", {})
                    tiles = source.get("tiles", [])
                    if not tiles:
                        continue
                    # Normalize geomanager {{time}} placeholder to {time} for JS
                    tile_url = _normalize_homepage_tile_url(tiles[0].replace("{{time}}", "{time}"))
                    layer_type = source.get("type", "raster")
                except Exception:
                    continue

                # Get legend separately — never blocks tile rendering
                legend_config = _normalize_legend(_get_legend(layer))
                has_time = bool(getattr(layer, "has_time", False))

                enriched["layers"].append(
                    {
                        "tile_url": tile_url,
                        "layer_type": layer_type,
                        "title": layer.title,
                        "legend": legend_config,
                        "tile_json_url": getattr(layer, "tile_json_url", None) if has_time else None,
                        "timestamps_response_object_key": getattr(
                            layer,
                            "timestamps_response_object_key",
                            None,
                        )
                        if has_time
                        else None,
                        "time_parameter_name": getattr(layer, "time_parameter_name", None) if has_time else None,
                    }
                )

                if not enriched["available_times"] and has_time:
                    enriched["available_times"] = _get_available_times_for_tile_json(
                        getattr(layer, "tile_json_url", None)
                    )
                if not enriched["date_meta"] and has_time:
                    enriched["date_meta"] = _get_date_meta_for_tile_json(
                        getattr(layer, "tile_json_url", None)
                    )

        if dataset.latest_date:
            local_tz = pytz.timezone(settings.TIME_ZONE)
            enriched["latest_time"] = dataset.latest_date.astimezone(local_tz).strftime("%Y-%m-%d")

        entries.append(enriched)

    basemap_style_url, default_basemap = _get_minimap_basemap()
    mapviewer_default_style = _get_mapviewer_default_style()

    return {
        "map_widget": mw,
        "datasets": entries,
        "basemap_style_url": basemap_style_url,
        "default_basemap": default_basemap,
        "mapviewer_default_style": mapviewer_default_style,
    }
