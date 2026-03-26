from copy import deepcopy
from urllib.parse import urljoin, urlsplit

from django.conf import settings


FORECAST_PROVIDER_BY_SLUG = {
    "multi model": "multimodal",
    "multimodal forecast": "multimodal",
}

FORECAST_PROVIDER_BY_TITLE = {
    "multi model": "multimodal",
    "multi model forecast": "multimodal",
    "multimodal forecast": "multimodal",
    "geosfm flood forecast": "geosfm",
    "mike hydro": "mike-hydro",
    "google flood forecast": "google-flood",
}


def _normalize_key(value):
    return " ".join(str(value or "").replace("-", " ").replace("_", " ").lower().split())


def _get_full_url(request, path):
    if not path:
        return path

    path = str(path)
    if path.startswith(("http://", "https://")):
        parsed = urlsplit(path)
        if request and parsed.path.startswith(("/api/", "/pg/", "/tileserv/", "/mapcache/", "/mapserver/")):
            path = parsed.path
            if parsed.query:
                path = f"{path}?{parsed.query}"
        else:
            return path

    if request:
        url = request.build_absolute_uri(path)
        return (
            url.replace("%7B", "{")
            .replace("%7D", "}")
            .replace("%7b", "{")
            .replace("%7d", "}")
        )

    cms_base_url = getattr(settings, "CMS_BASE_URL", None)
    if cms_base_url:
        if not path.startswith("/"):
            path = f"/{path}"
        return urljoin(cms_base_url, path)

    return path


def _shared_forecast_legend():
    return {
        "type": "basic",
        "items": [
            {"name": "Extreme", "color": "#d32f2f"},
            {"name": "Severe", "color": "#ff9800"},
            {"name": "Moderate", "color": "#ffc107"},
            {"name": "Normal", "color": "#b0b0b0"},
        ],
    }


def _shared_forecast_render(source_layer):
    return {
        "layers": [
            {
                "type": "circle",
                "paint": {
                    "circle-color": [
                        "match",
                        ["get", "alert_level"],
                        "emergency",
                        "#d32f2f",
                        "alarm",
                        "#ff9800",
                        "warning",
                        "#ffc107",
                        "normal",
                        "#b0b0b0",
                        "#b0b0b0",
                    ],
                    "circle-radius": [
                        "case",
                        [">", ["get", "point_count"], 50],
                        12,
                        [">", ["get", "point_count"], 10],
                        9,
                        [">", ["get", "point_count"], 1],
                        7,
                        5,
                    ],
                    "circle-opacity": 0.9,
                    "circle-stroke-color": "#ffffff",
                    "circle-stroke-width": 1.5,
                },
                "metadata": {"position": "top", "interactive": True},
                "source-layer": source_layer,
            }
        ]
    }


def _time_selector(tile_json_url, *, url_param="date"):
    return {
        "key": "time",
        "url_param": url_param,
        "required": True,
        "sentence": "{selector}",
        "type": "datetime",
        "availableDates": [],
        "dateFormat": {"currentTime": "yyyy-MM-dd"},
        "tileJsonUrl": tile_json_url,
    }


def _google_coverage_selector():
    return {
        "key": "extended_coverage",
        "url_param": "extended_coverage",
        "required": False,
        "type": "toggle",
        "sentence": "{selector}",
        "selectorDescription": "Extended coverage",
        "default": "false",
        "options": [
            {
                "label": "Default coverage",
                "value": "false",
                "linkedParams": {"confidence": "high"},
                "hidden": True,
            },
            {
                "label": "Extended coverage",
                "value": "true",
                "linkedParams": {"confidence": "all"},
                "allowUncheck": True,
                "uncheckedValue": "false",
            },
        ],
    }


def _tile_layer_config(request, tile_path, source_layer):
    return {
        "type": "vector",
        "source": {
            "type": "vector",
            "tiles": [_get_full_url(request, tile_path)],
        },
        "render": _shared_forecast_render(source_layer),
    }


FORECAST_LAYER_CONFIGS = {
    "multimodal": {
        "tile_path": (
            "/pg/tileserv/gha.multimodal_points_raw/{z}/{x}/{y}.pbf"
            "?date={time}"
        ),
        "tile_json_url": "/api/flood/forecast-dates",
        "source_layer": "gha.multimodal_points_raw",
        "params": {"date": ""},
        "interaction_output": [
            {"column": "admin_name", "property": "Location", "type": "string"},
            {"column": "point_id", "property": "Point ID", "type": "number"},
            {"column": "forecast_date", "property": "Forecast Date", "type": "string"},
            {"column": "daily_avg", "property": "Daily Avg (m3/s)", "type": "number"},
            {"column": "daily_max", "property": "Max Discharge (m3/s)", "type": "number"},
            {"column": "alert_level", "property": "Highest Alert", "type": "string"},
            {"column": "geosfm", "property": "GeoSFM (m3/s)", "type": "number"},
            {"column": "floodproof", "property": "Floodproof (m3/s)", "type": "number"},
            {"column": "mike_hydro_rfe", "property": "Mike Hydro RFE (m3/s)", "type": "number"},
            {"column": "mike_hydro_chirp", "property": "Mike Hydro CHIRP (m3/s)", "type": "number"},
            {"column": "mike_hydro_imerg", "property": "Mike Hydro IMERG (m3/s)", "type": "number"},
        ],
    },
    "geosfm": {
        "tile_path": (
            "/pg/tileserv/gha.forecast_points_clustered/{z}/{x}/{y}.pbf"
            "?provider=geosfm&cluster_zoom=7&date={time}"
        ),
        "tile_json_url": "/api/flood/forecast-dates",
        "source_layer": "gha.forecast_points_clustered",
        "params": {"date": ""},
        "interaction_output": [
            {"column": "point_count", "property": "Points in Cluster", "type": "number"},
            {"column": "admin_name", "property": "Location", "type": "string"},
            {"column": "point_id", "property": "Point ID", "type": "number"},
            {"column": "forecast_date", "property": "Forecast Date", "type": "string"},
            {"column": "alert_level", "property": "Alert Level", "type": "string"},
            {"column": "daily_avg", "property": "GeoSFM (m3/s)", "type": "number"},
            {"column": "geosfm", "property": "GeoSFM Raw (m3/s)", "type": "number"},
            {"column": "forecasts_json", "property": "Forecasts", "type": "string"},
        ],
    },
    "mike-hydro": {
        "tile_path": (
            "/pg/tileserv/gha.forecast_points_clustered/{z}/{x}/{y}.pbf"
            "?provider=mike-hydro&cluster_zoom=7&date={time}"
        ),
        "tile_json_url": "/api/flood/forecast-dates",
        "source_layer": "gha.forecast_points_clustered",
        "params": {"date": ""},
        "interaction_output": [
            {"column": "point_count", "property": "Points in Cluster", "type": "number"},
            {"column": "admin_name", "property": "Location", "type": "string"},
            {"column": "point_id", "property": "Point ID", "type": "number"},
            {"column": "forecast_date", "property": "Forecast Date", "type": "string"},
            {"column": "alert_level", "property": "Alert Level", "type": "string"},
            {"column": "daily_avg", "property": "Mike Hydro (m3/s)", "type": "number"},
            {"column": "mike_hydro_rfe", "property": "Mike Hydro RFE (m3/s)", "type": "number"},
            {"column": "mike_hydro_chirp", "property": "Mike Hydro CHIRP (m3/s)", "type": "number"},
            {"column": "mike_hydro_imerg", "property": "Mike Hydro IMERG (m3/s)", "type": "number"},
            {"column": "forecasts_json", "property": "Forecasts", "type": "string"},
        ],
    },
    "google-flood": {
        "tile_path": (
            "/pg/tileserv/gha.google_flood_points_clustered/{z}/{x}/{y}.pbf"
            "?cluster_zoom=7&date={time}&confidence={confidence}&extended_coverage={extended_coverage}"
        ),
        "tile_json_url": "/api/flood/google-flood-dates",
        "source_layer": "gha.google_flood_points_clustered",
        "params": {
            "date": "",
            "confidence": "high",
            "extended_coverage": "false",
        },
        "interaction_output": [
            {"column": "point_count", "property": "Points in Cluster", "type": "number"},
            {"column": "admin_name", "property": "Location", "type": "string"},
            {"column": "gauge_id", "property": "Gauge ID", "type": "string"},
            {"column": "point_id", "property": "Point ID", "type": "string"},
            {"column": "forecast_date", "property": "Forecast Date", "type": "string"},
            {"column": "alert_level", "property": "Alert Level", "type": "string"},
            {"column": "google_flood_severity", "property": "Google Severity", "type": "string"},
            {"column": "confidence_level", "property": "Confidence", "type": "string"},
            {"column": "confidence_score", "property": "Confidence Score", "type": "number"},
            {"column": "daily_avg", "property": "Forecast Flow (m3/s)", "type": "number"},
            {"column": "daily_max", "property": "Peak Flow (m3/s)", "type": "number"},
            {"column": "extended_coverage", "property": "Extended Coverage", "type": "string"},
            {"column": "forecasts_json", "property": "Forecasts", "type": "string"},
        ],
    },
}


def _resolve_forecast_provider(dataset):
    slug_key = _normalize_key(dataset.get("dataset_slug"))
    if slug_key in FORECAST_PROVIDER_BY_SLUG:
        return FORECAST_PROVIDER_BY_SLUG[slug_key]

    title_key = _normalize_key(dataset.get("name") or dataset.get("title"))
    return FORECAST_PROVIDER_BY_TITLE.get(title_key)


def patch_forecast_datasets(request, datasets):
    if not isinstance(datasets, list):
        return datasets

    shared_legend = _shared_forecast_legend()

    for dataset in datasets:
        if not isinstance(dataset, dict):
            continue

        provider = _resolve_forecast_provider(dataset)
        config = FORECAST_LAYER_CONFIGS.get(provider)
        if not config:
            continue

        layers = dataset.get("layers")
        if not isinstance(layers, list) or not layers:
            continue

        dataset["layer_type"] = "vector_tile"
        tile_json_url = _get_full_url(request, config["tile_json_url"])

        params_selector_config = [_time_selector(tile_json_url)]
        if provider == "google-flood":
            params_selector_config.append(_google_coverage_selector())

        for layer in layers:
            if not isinstance(layer, dict):
                continue

            layer["layerType"] = "vector_tile"
            layer["layerConfig"] = _tile_layer_config(
                request,
                config["tile_path"],
                config["source_layer"],
            )
            layer["legendConfig"] = deepcopy(shared_legend)
            layer["params"] = deepcopy(config["params"])
            layer["paramsSelectorConfig"] = deepcopy(params_selector_config)
            layer["multiTemporal"] = True
            layer["tileJsonUrl"] = tile_json_url
            layer["timestampsResponseObjectKey"] = "timestamps"
            layer["interactionConfig"] = {
                "type": "intersection",
                "output": deepcopy(config["interaction_output"]),
            }

    return datasets
