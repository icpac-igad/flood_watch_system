from adminboundarymanager.models import AdminBoundarySettings
from django.conf import settings
from django.urls import reverse
from rest_framework.decorators import api_view, renderer_classes
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from wagtail.api.v2.utils import get_full_url as wagtail_get_full_url
from urllib.parse import quote, urljoin, urlsplit

from geomanager.models import Category, VectorLayerIcon, VectorTileLayerIcon, GeomanagerSettings, Dataset
from geomanager.serializers import CategorySerializer, DatasetSerializer
from home.models import MultimodalClusterSettings


def _build_shared_multimodal_legend_config(request=None, multimodal_settings=None):
    normal_color = getattr(multimodal_settings, "normal_color", "#b0b0b0")
    moderate_color = getattr(multimodal_settings, "warning_color", "#ffc107")
    severe_color = getattr(multimodal_settings, "alarm_color", "#ff9800")
    extreme_color = getattr(multimodal_settings, "emergency_color", "#d32f2f")

    def _build_pin_icon_data_uri(color):
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24">'
            f'<path d="M12 1.5C7.86 1.5 4.5 4.86 4.5 9c0 5.17 7.5 13.5 7.5 13.5s7.5-8.33 7.5-13.5c0-4.14-3.36-7.5-7.5-7.5z" fill="{color}"/>'
            "</svg>"
        )
        return f"data:image/svg+xml;charset=UTF-8,{quote(svg)}"

    def _item(name, color):
        return {
            "name": name,
            "color": color,
            "icon": _build_pin_icon_data_uri(color),
            "iconWidth": 12,
            "iconHeight": 16,
        }

    return {
        "type": "basic",
        "items": [
            _item("Extreme", extreme_color),
            _item("Severe", severe_color),
            _item("Moderate", moderate_color),
            _item("Normal", normal_color),
        ],
    }


def _is_multimodal_provider_dataset(dataset_name):
    normalized = (dataset_name or "").strip().lower()
    if not normalized:
        return False
    return any(
        token in normalized
        for token in (
            "multi-model",
            "multi model",
            "floodproof",
            "geosfm",
            "mike hydro",
            "google flood",
            "hype",
        )
    )


def _build_request_base_url(request):
    if not request:
        return None

    # Prefer the host seen by Django first; some proxies send X-Forwarded-Host
    # without the non-default port, which breaks generated API URLs.
    request_host = (request.get_host() or "").split(",")[0].strip()
    forwarded_host = (request.headers.get("x-forwarded-host") or "").split(",")[0].strip()
    host = request_host or forwarded_host
    if not host:
        return None

    forwarded_proto = (request.headers.get("x-forwarded-proto") or "").split(",")[0].strip()
    scheme = forwarded_proto or request.scheme or "http"

    forwarded_port = (request.headers.get("x-forwarded-port") or "").split(",")[0].strip()
    request_port = (request.get_port() or "").strip()
    effective_port = forwarded_port or request_port
    if effective_port and ":" not in host:
        is_default_http = scheme == "http" and effective_port == "80"
        is_default_https = scheme == "https" and effective_port == "443"
        if not (is_default_http or is_default_https):
            host = f"{host}:{effective_port}"

    return f"{scheme}://{host}"


def get_full_url(request, path):
    """
    Build absolute URLs using the active request host when available.
    Falls back to CMS_BASE_URL only when request context is missing.
    """
    if not path:
        return path

    if str(path).startswith(("http://", "https://")):
        parsed = urlsplit(str(path))
        if parsed.path.startswith(
            (
                "/api/",
                "/pg/",
                "/tileserv/",
                "/mapcache/",
                "/mapserver/",
                "/cog-tiles/",
                "/media/",
                "/static/",
                "/stac-browser/api/",
            )
        ):
            # Rebase internal URLs to the active request host to avoid cross-origin
            # requests when CMS stores absolute URLs from another environment.
            path = f"{parsed.path}{f'?{parsed.query}' if parsed.query else ''}{f'#{parsed.fragment}' if parsed.fragment else ''}"
        else:
            return path

    request_base_url = _build_request_base_url(request)
    if request_base_url:
        if not path.startswith('/'):
            path = '/' + path
        return urljoin(request_base_url, path)

    cms_base_url = getattr(settings, 'CMS_BASE_URL', None)
    if cms_base_url:
        if not path.startswith('/'):
            path = '/' + path
        return urljoin(cms_base_url, path)

    if request:
        return request.build_absolute_uri(path)

    return wagtail_get_full_url(request, path)


def _build_multimodal_alert_icon_case_expression(
    multimodal_settings=None,
    *,
    extreme_icon,
    severe_icon,
    moderate_icon,
    normal_icon,
):
    moderate_threshold = float(getattr(multimodal_settings, "warning_threshold", 300) or 300)
    severe_threshold = float(getattr(multimodal_settings, "alarm_threshold", 500) or 500)
    extreme_threshold = float(getattr(multimodal_settings, "emergency_threshold", 750) or 750)

    alert_level_expr = [
        "downcase",
        [
            "to-string",
            [
                "coalesce",
                ["get", "alert_level"],
                ["get", "risk_level"],
                ["get", "latest_severity"],
                "",
            ],
        ],
    ]
    daily_avg_expr = ["to-number", ["coalesce", ["get", "daily_avg"], 0]]
    is_extreme_expr = [
        "any",
        ["==", alert_level_expr, "extreme"],
        ["==", alert_level_expr, "emergency"],
    ]
    is_severe_expr = [
        "any",
        ["==", alert_level_expr, "severe"],
        ["==", alert_level_expr, "alarm"],
    ]
    is_moderate_expr = [
        "any",
        ["==", alert_level_expr, "moderate"],
        ["==", alert_level_expr, "warning"],
    ]
    is_normal_expr = [
        "any",
        ["==", alert_level_expr, "normal"],
        ["==", alert_level_expr, "none"],
        ["==", alert_level_expr, "minor"],
    ]

    return [
        "case",
        is_extreme_expr, extreme_icon,
        is_severe_expr, severe_icon,
        is_moderate_expr, moderate_icon,
        is_normal_expr, normal_icon,
        [">=", daily_avg_expr, extreme_threshold], extreme_icon,
        [">=", daily_avg_expr, severe_threshold], severe_icon,
        [">=", daily_avg_expr, moderate_threshold], moderate_icon,
        normal_icon,
    ]


def _build_alert_icon_image_expression(multimodal_settings=None):
    return _build_multimodal_alert_icon_case_expression(
        multimodal_settings,
        extreme_icon="forecast-pin-v2-icon-emergency",
        severe_icon="forecast-pin-v2-icon-alarm",
        moderate_icon="forecast-pin-v2-icon-warning",
        normal_icon="forecast-pin-v2-icon-normal",
    )


def _build_alert_cluster_icon_image_expression(multimodal_settings=None):
    return _build_multimodal_alert_icon_case_expression(
        multimodal_settings,
        extreme_icon="forecast-cluster-emergency",
        severe_icon="forecast-cluster-alarm",
        moderate_icon="forecast-cluster-warning",
        normal_icon="forecast-cluster-normal",
    )


def _build_multimodal_circle_color_expression(
    normal_color,
    moderate_color,
    severe_color,
    extreme_color,
):
    alert_level_expr = [
        "downcase",
        [
            "to-string",
            [
                "coalesce",
                ["get", "alert_level"],
                ["get", "risk_level"],
                ["get", "latest_severity"],
                "normal",
            ],
        ],
    ]

    return [
        "case",
        [
            "any",
            ["==", alert_level_expr, "extreme"],
            ["==", alert_level_expr, "emergency"],
        ], extreme_color,
        [
            "any",
            ["==", alert_level_expr, "severe"],
            ["==", alert_level_expr, "alarm"],
        ], severe_color,
        [
            "any",
            ["==", alert_level_expr, "moderate"],
            ["==", alert_level_expr, "warning"],
        ], moderate_color,
        [
            "any",
            ["==", alert_level_expr, "normal"],
            ["==", alert_level_expr, "none"],
            ["==", alert_level_expr, "minor"],
        ], normal_color,
        normal_color,
    ]


def _build_pin_symbol_render(source_layer=None, multimodal_settings=None):
    point_count_expr = ["to-number", ["coalesce", ["get", "point_count"], 1]]
    symbol_layer = {
        "type": "symbol",
        "layout": {
            "icon-image": [
                "case",
                [">", point_count_expr, 1], _build_alert_cluster_icon_image_expression(multimodal_settings),
                _build_alert_icon_image_expression(multimodal_settings),
            ],
            "icon-size": [
                "case",
                [">", point_count_expr, 50], 0.62,
                [">", point_count_expr, 10], 0.52,
                [">", point_count_expr, 1], 0.44,
                0.34,
            ],
            "icon-allow-overlap": False,
            "icon-ignore-placement": False,
            "icon-optional": False,
            "icon-padding": 8,
        },
        "paint": {
            "icon-opacity": 0.95,
        },
        "metadata": {"position": "top", "interactive": True},
    }
    if source_layer:
        symbol_layer["source-layer"] = source_layer

    return {"layers": [symbol_layer]}


def _build_modular_model_layer_config(request, endpoint_path, multimodal_settings=None):
    return {
        "type": "geojson",
        "source": {
            "type": "geojson",
            "data": get_full_url(request, endpoint_path),
        },
        "render": _build_pin_symbol_render(multimodal_settings=multimodal_settings),
    }


def _patch_modular_model_datasets(request, datasets_data, multimodal_settings=None):
    """Patch placeholder model layers to true GeoJSON sources with popup fields."""
    shared_multimodal_legend = _build_shared_multimodal_legend_config(request, multimodal_settings)
    multimodal_forecast_interaction_output = [
        {"column": "admin_name", "property": "Location", "type": "string"},
        {"column": "point_id", "property": "Point ID", "type": "string", "hidden": True},
        {"column": "hybas_id", "property": "Basin ID", "type": "string", "hidden": True},
        {"column": "alert_level", "property": "Alert Level", "type": "string"},
        {"column": "daily_avg", "property": "Forecast Flow (m³/s)", "type": "number"},
        {"column": "geosfm", "property": "GeoSFM (m³/s)", "type": "number"},
        {"column": "floodproof", "property": "Floodproof (m³/s)", "type": "number"},
        {"column": "mike_hydro_rfe", "property": "Mike Hydro RFE (m³/s)", "type": "number"},
        {"column": "mike_hydro_chirp", "property": "Mike Hydro CHIRP (m³/s)", "type": "number"},
        {"column": "mike_hydro_imerg", "property": "Mike Hydro IMERG (m³/s)", "type": "number"},
        {"column": "threshold_alert", "property": "Warning Threshold", "type": "number"},
        {"column": "threshold_alarm", "property": "Alarm Threshold", "type": "number"},
        {"column": "threshold_emergency", "property": "Emergency Threshold", "type": "number"},
        {"column": "data_date", "property": "Data Date", "type": "string"},
        {"column": "forecasts", "property": "Forecasts", "type": "string", "hidden": True},
        {"column": "data_endpoint", "property": "Data Endpoint", "type": "string", "hidden": True},
    ]

    overrides = {
        "Multi Model": {
            "endpoint": "/api/v1/multimodal/geojson/",
            "interaction_output": multimodal_forecast_interaction_output,
        },
        "Multi-Model": {
            "endpoint": "/api/v1/multimodal/geojson/",
            "interaction_output": multimodal_forecast_interaction_output,
        },
        "Multimodal Forecast": {
            "endpoint": "/api/v1/multimodal/geojson/",
            "interaction_output": multimodal_forecast_interaction_output,
        },
        "GeoSFM Flood Forecast": {
            "endpoint": "/api/v1/models/geosfm/geojson/",
            "interaction_output": [
                {"column": "admin_name", "property": "Location", "type": "string"},
                {"column": "point_id", "property": "Point ID", "type": "string", "hidden": True},
                {"column": "hybas_id", "property": "Basin ID", "type": "string", "hidden": True},
                {"column": "alert_level", "property": "Alert Level", "type": "string"},
                {"column": "daily_avg", "property": "GeoSFM (m³/s)", "type": "number"},
                {"column": "threshold_alert", "property": "Warning Threshold", "type": "number"},
                {"column": "threshold_alarm", "property": "Alarm Threshold", "type": "number"},
                {"column": "threshold_emergency", "property": "Emergency Threshold", "type": "number"},
                {"column": "data_date", "property": "Data Date", "type": "string"},
                {"column": "forecasts", "property": "Forecasts", "type": "string", "hidden": True},
                {"column": "data_endpoint", "property": "Data Endpoint", "type": "string", "hidden": True},
            ],
        },
        "Mike Hydro": {
            "endpoint": "/api/v1/models/mike-hydro/geojson/",
            "interaction_output": [
                {"column": "admin_name", "property": "Location", "type": "string"},
                {"column": "point_id", "property": "Point ID", "type": "string", "hidden": True},
                {"column": "hybas_id", "property": "Basin ID", "type": "string", "hidden": True},
                {"column": "alert_level", "property": "Alert Level", "type": "string"},
                {"column": "daily_avg", "property": "Mike Hydro (m³/s)", "type": "number"},
                {"column": "mike_hydro_rfe", "property": "Mike Hydro RFE (m³/s)", "type": "number"},
                {"column": "mike_hydro_chirp", "property": "Mike Hydro CHIRP (m³/s)", "type": "number"},
                {"column": "mike_hydro_imerg", "property": "Mike Hydro IMERG (m³/s)", "type": "number"},
                {"column": "threshold_alert", "property": "Warning Threshold", "type": "number"},
                {"column": "threshold_alarm", "property": "Alarm Threshold", "type": "number"},
                {"column": "threshold_emergency", "property": "Emergency Threshold", "type": "number"},
                {"column": "data_date", "property": "Data Date", "type": "string"},
                {"column": "forecasts", "property": "Forecasts", "type": "string", "hidden": True},
                {"column": "data_endpoint", "property": "Data Endpoint", "type": "string", "hidden": True},
            ],
        },
        "Google Flood Forecast": {
            "endpoint": "/api/v1/google-flood/geojson",
            "interaction_output": [
                {"column": "admin_name", "property": "Location", "type": "string"},
                {"column": "gauge_id", "property": "Gauge ID", "type": "string"},
                {"column": "point_id", "property": "Point ID", "type": "string", "hidden": True},
                {"column": "hybas_id", "property": "Basin ID", "type": "string", "hidden": True},
                {"column": "alert_level", "property": "Alert Level", "type": "string"},
                {"column": "google_flood_severity", "property": "Google Severity", "type": "string"},
                {"column": "confidence_level", "property": "Confidence", "type": "string"},
                {"column": "confidence_score", "property": "Confidence Score", "type": "number"},
                {"column": "daily_avg", "property": "Forecast Flow (m³/s)", "type": "number"},
                {"column": "threshold_alert", "property": "Warning Threshold", "type": "number"},
                {"column": "threshold_alarm", "property": "Alarm Threshold", "type": "number"},
                {"column": "threshold_emergency", "property": "Emergency Threshold", "type": "number"},
                {"column": "data_date", "property": "Data Date", "type": "string"},
                {"column": "forecasts", "property": "Forecasts", "type": "string", "hidden": True},
                {"column": "data_endpoint", "property": "Data Endpoint", "type": "string", "hidden": True},
            ],
            "params": {
                "confidence": "high",
                "extended_coverage": "false",
            },
            "params_selector_config": [
                {
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
                },
            ],
        },
        "Floodproofs Discharge Forecast": {
            "endpoint": "/api/v1/models/floodproof/geojson/",
            "interaction_output": [
                {"column": "admin_name", "property": "Location", "type": "string"},
                {"column": "point_id", "property": "Point ID", "type": "string", "hidden": True},
                {"column": "hybas_id", "property": "Basin ID", "type": "string", "hidden": True},
                {"column": "alert_level", "property": "Alert Level", "type": "string"},
                {"column": "daily_avg", "property": "Floodproof (m³/s)", "type": "number"},
                {"column": "threshold_alert", "property": "Warning Threshold", "type": "number"},
                {"column": "threshold_alarm", "property": "Alarm Threshold", "type": "number"},
                {"column": "threshold_emergency", "property": "Emergency Threshold", "type": "number"},
                {"column": "data_date", "property": "Data Date", "type": "string"},
                {"column": "forecasts", "property": "Forecasts", "type": "string", "hidden": True},
                {"column": "data_endpoint", "property": "Data Endpoint", "type": "string", "hidden": True},
            ],
        },
    }

    for dataset in datasets_data:
        dataset_name = dataset.get("name") or dataset.get("title")
        normalized_dataset_name = " ".join(
            str(dataset_name or "").replace("-", " ").strip().lower().split()
        )
        applies_shared_legend = _is_multimodal_provider_dataset(dataset_name)
        override = overrides.get(dataset_name)
        if not override and normalized_dataset_name in {"multi model", "multimodal forecast"}:
            override = overrides.get("Multi Model")

        for layer in dataset.get("layers", []):
            if applies_shared_legend:
                layer["legendConfig"] = shared_multimodal_legend

                # Force non-overridden multimodal provider layers (e.g. Multi Model, Hype)
                # to use the same balloon/pin symbol style.
                if not override:
                    layer_config = layer.get("layerConfig") or {}
                    source = layer_config.get("source") or {}
                    source_type = source.get("type")
                    if source_type in ("vector", "geojson"):
                        source_layer = None
                        for render_layer in (layer_config.get("render", {}) or {}).get("layers", []) or []:
                            if isinstance(render_layer, dict) and render_layer.get("source-layer"):
                                source_layer = render_layer.get("source-layer")
                                break
                        layer_config["render"] = _build_pin_symbol_render(
                            source_layer=source_layer,
                            multimodal_settings=multimodal_settings,
                        )
                        layer["layerConfig"] = layer_config

            if not override:
                continue

            endpoint_path = override["endpoint"]
            layer["layerConfig"] = _build_modular_model_layer_config(
                request, endpoint_path, multimodal_settings
            )
            layer["interactionConfig"] = {
                "type": "intersection",
                "output": override["interaction_output"],
            }
            layer["params"] = override.get("params", layer.get("params", {}))
            layer["paramsSelectorConfig"] = override.get(
                "params_selector_config",
                layer.get("paramsSelectorConfig", []),
            )


@api_view(['GET'])
@renderer_classes([JSONRenderer])
def get_mapviewer_config(request):
    """Custom mapviewer config that includes datasets and layers"""
    gm_settings = GeomanagerSettings.for_request(request)
    abm_settings = AdminBoundarySettings.for_request(request)

    categories = Category.objects.all()
    categories_data = CategorySerializer(categories, many=True).data

    # Add datasets with layers
    datasets = Dataset.objects.filter(published=True)
    datasets_data = DatasetSerializer(datasets, many=True, context={"request": request}).data

    cluster_settings = None
    try:
        cluster_settings = MultimodalClusterSettings.load(request_or_site=request)
    except Exception:
        cluster_settings = None

    _patch_modular_model_datasets(request, datasets_data, cluster_settings)

    response = {
        "categories": categories_data,
        "datasets": datasets_data,  # Add datasets to response
        "enableMyAccount": False,
        "allowSignups": False,
    }

    if gm_settings.enable_my_account:
        response.update({
            "enableMyAccount": True,
        })

    if gm_settings.allow_signups:
        response.update({
            "allowSignups": True,
        })

    if gm_settings.map_disclaimer_text:
        response.update({"disclaimerText": gm_settings.map_disclaimer_text})

    links = {
        "mapViewerBaseUrl": get_full_url(request, (reverse("mapview"))),
    }

    if gm_settings.terms_of_service_page:
        links.update(
            {"termsOfServicePageUrl": get_full_url(request, gm_settings.terms_of_service_page.get_full_url(request))})

    if gm_settings.privacy_policy_page:
        links.update(
            {"privacyPolicyPageUrl": get_full_url(request, gm_settings.privacy_policy_page.get_full_url(request))})

    if gm_settings.map_disclaimer_page:
        links.update({"disclaimerPageUrl": gm_settings.map_disclaimer_page.get_full_url(request)})

    if gm_settings.contact_us_page:
        links.update({"contactUsPageUrl": gm_settings.contact_us_page.get_full_url(request)})

    response.update({"links": links})

    icon_images = []
    for icon in VectorLayerIcon.objects.all():
        icon_images.append({"name": icon.name, "url": get_full_url(request, icon.file.url)})

    for icon in VectorTileLayerIcon.objects.all():
        icon_images.append({"name": icon.name, "url": get_full_url(request, icon.file.url)})

    response.update({"vectorLayerIcons": icon_images})

    if gm_settings.logo:
        logo = {
            "imageUrl": get_full_url(request, gm_settings.logo.file.url)
        }

        if gm_settings.logo_page:
            logo.update({"linkUrl": get_full_url(request, gm_settings.logo_page.url)})

        if not gm_settings.logo_page and gm_settings.logo_external_link:
            logo.update({"linkUrl": gm_settings.logo_external_link, "external": True})

        response.update({"logo": logo})

    if abm_settings.countries_list:
        response.update({
            "countries": abm_settings.countries_list,
            "bounds": abm_settings.combined_countries_bounds,
            "boundaryDataSource": abm_settings.data_source
        })

    base_maps_data = []

    tile_gl_source = gm_settings.tile_gl_source

    if tile_gl_source:
        # get base maps
        for base_map in gm_settings.base_maps:
            data = base_map.block.get_api_representation(base_map.value)
            for key, value in base_map.value.items():
                if key == "image" and value:
                    data.update({"image": get_full_url(request, value.file.url)})

            data.update({"mapStyle": get_full_url(request, tile_gl_source.map_style_url)})
            base_maps_data.append(data)

    response.update({"basemaps": base_maps_data})

    # Add multimodal cluster settings
    if cluster_settings:
        response.update({"multimodalClusterConfig": cluster_settings.get_config()})

    # Add boundary layer config
    response.update({
        "boundaryLayerConfig": {
            "default": {
                "admin0": "b6c3b7d9-c3dd-4012-9cc9-857f0640e702",
                "admin1": "02453614-2716-4ca3-bc82-589b364fe47e",
                "admin2": "c47279f5-8481-4529-86f3-f58810f7d567",
            },
        }
    })

    # Add multimodal layer URL config
    response.update({
        "multimodalLayerConfig": {
            "default": {
                "baseUrl": "/pg/tileserv/gha.multimodal_points_clustered/{z}/{x}/{y}.pbf",
                "sourceLayer": "gha.multimodal_points_clustered",
            },
        }
    })

    return Response(response)
