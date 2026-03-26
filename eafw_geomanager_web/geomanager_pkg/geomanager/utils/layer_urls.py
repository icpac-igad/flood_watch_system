from copy import deepcopy
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


WMTS_RASTER_LAYERS = {
    "daily_hmc_alert",
    "flood_extent_rp25",
    "flood_extent_rp100",
    "asap_cropland",
    "asap_rangeland",
    "wrf_daily_rainfall",
    "wrf_extreme_heavy",
    "wrf_extreme_very_heavy",
    "wrf_extreme_extremely_heavy",
    "landscan_population",
}

WMTS_TEMPORAL_LAYERS = {
    "daily_hmc_alert",
    "wrf_daily_rainfall",
    "wrf_extreme_heavy",
    "wrf_extreme_very_heavy",
    "wrf_extreme_extremely_heavy",
}


def _tileserv_source_layer_name(tile_url):
    marker = "/pg/tileserv/"
    if marker not in tile_url:
        return None

    tail = tile_url.split(marker, 1)[1]
    return tail.split("/", 1)[0] if tail else None


def _normalize_render_layers(render_layers, tile_url):
    if not isinstance(render_layers, list) or not tile_url:
        return render_layers

    source_layer_name = _tileserv_source_layer_name(tile_url)
    if not source_layer_name:
        return render_layers

    normalized_layers = []
    for render_layer in render_layers:
        if not isinstance(render_layer, dict):
            normalized_layers.append(render_layer)
            continue

        normalized_layer = deepcopy(render_layer)
        source_layer = normalized_layer.get("source-layer")
        if source_layer in {
            "default",
            "gha.multimodal_points_clustered",
            "gha.multimodal_points_clustered_project",
            "gha.multimodal_points_raw",
        }:
            normalized_layer["source-layer"] = source_layer_name
        normalized_layers.append(normalized_layer)

    return normalized_layers


def _normalize_wms_query_artifacts(tile_url):
    normalized = tile_url.replace("BBOX={bbox-epsg-3857}?time=", "BBOX={bbox-epsg-3857}&time=")
    normalized = normalized.replace("BBOX={bbox-epsg-3857}?TIME=", "BBOX={bbox-epsg-3857}&TIME=")
    return normalized


def _rewrite_multimodal_tileserv_path(tile_url):
    parsed = urlsplit(tile_url)
    path = parsed.path.replace(
        "/pg/tileserv/gha.multimodal_points_clustered_project/",
        "/pg/tileserv/gha.multimodal_points_raw/",
    ).replace(
        "/pg/tileserv/gha.multimodal_points_clustered/",
        "/pg/tileserv/gha.multimodal_points_raw/",
    )

    if path == parsed.path:
        return tile_url

    query_pairs = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if key != "cluster_zoom"
    ]
    query = urlencode(query_pairs)
    return urlunsplit((parsed.scheme, parsed.netloc, path, query, parsed.fragment))


def _replace_map_endpoint(path):
    if "/mapcache/wmts" in path:
        return path
    if "/mapserver/" in path:
        return path.replace("/mapserver/", "/mapcache/wmts", 1)
    if path == "/mapserver":
        return "/mapcache/wmts"
    if "/mapcache/" in path:
        return path.replace("/mapcache/", "/mapcache/wmts", 1)
    if path == "/mapcache":
        return "/mapcache/wmts"
    return path


def _maybe_convert_wms_to_wmts(tile_url):
    parsed = urlsplit(tile_url)
    query_pairs = parse_qsl(parsed.query, keep_blank_values=True)
    query = {key.upper(): value for key, value in query_pairs}

    if query.get("SERVICE", "").upper() != "WMS" or query.get("REQUEST", "").upper() != "GETMAP":
        return tile_url

    layer_name = query.get("LAYERS", "")
    if layer_name not in WMTS_RASTER_LAYERS:
        return tile_url

    wmts_path = _replace_map_endpoint(parsed.path)
    params = [
        ("SERVICE", "WMTS"),
        ("REQUEST", "GetTile"),
        ("VERSION", "1.0.0"),
        ("LAYER", layer_name),
        ("STYLE", "default"),
        ("FORMAT", "image/png"),
        ("TILEMATRIXSET", "GoogleMapsCompatible"),
        ("TILEMATRIX", "{z}"),
        ("TILEROW", "{y}"),
        ("TILECOL", "{x}"),
    ]

    if layer_name in WMTS_TEMPORAL_LAYERS:
        params.append(("time", query.get("TIME") or query.get("time") or "{time}"))

    params.extend(
        [
            ("scope", query.get("SCOPE") or query.get("scope") or "all"),
            (
                "project_countries",
                query.get("PROJECT_COUNTRIES") or query.get("project_countries") or "__none__",
            ),
            ("country_name", query.get("COUNTRY_NAME") or query.get("country_name") or "__none__"),
            ("region_name", query.get("REGION_NAME") or query.get("region_name") or "__none__"),
            ("district_name", query.get("DISTRICT_NAME") or query.get("district_name") or "__none__"),
        ]
    )

    query_string = "&".join(f"{key}={value}" for key, value in params)
    return urlunsplit((parsed.scheme, parsed.netloc, wmts_path, query_string, parsed.fragment))


def normalize_tile_url(tile_url):
    tile_url = str(tile_url or "")
    if not tile_url:
        return tile_url

    normalized = tile_url.replace("{{time}}", "{time}")
    normalized = _normalize_wms_query_artifacts(normalized)
    normalized = _rewrite_multimodal_tileserv_path(normalized)
    normalized = _maybe_convert_wms_to_wmts(normalized)

    return normalized


def normalize_layer_config(layer_config):
    if not isinstance(layer_config, dict):
        return layer_config

    normalized = deepcopy(layer_config)
    source = normalized.get("source")
    if not isinstance(source, dict):
        return normalized

    tiles = source.get("tiles")
    if isinstance(tiles, list):
        source["tiles"] = [normalize_tile_url(tile_url) for tile_url in tiles]

    primary_tile_url = source.get("tiles", [None])[0] if isinstance(source.get("tiles"), list) else None
    render = normalized.get("render")
    if isinstance(render, dict) and isinstance(render.get("layers"), list):
        render["layers"] = _normalize_render_layers(render.get("layers"), primary_tile_url)

    return normalized
