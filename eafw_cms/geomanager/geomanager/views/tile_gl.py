import os
from copy import deepcopy

from django.http import HttpResponse, JsonResponse
from django.urls import reverse
from wagtail.api.v2.utils import get_full_url
from wagtailcache.cache import cache_page

from geomanager.errors import MissingTileError
from geomanager.models import MBTSource
from geomanager.utils.tile_gl import center_from_bounds, open_mbtiles

DEFAULT_ZOOM = 13
DEFAULT_MINZOOM = 7
DEFAULT_MAXZOOM = 15
WORLD_BOUNDS = [-180, -85.05112877980659, 180, 85.0511287798066]
FALLBACK_OPENMAPTILES_TILEJSON_URL = "https://eahazardswatch.icpac.net/tileserver-gl/data/v3.json"


@cache_page
def tile_gl(request, source_slug, z, x, y):
    source = MBTSource.objects.get(slug=source_slug)
    with open_mbtiles(source.file.path) as mbtiles:
        try:
            data = mbtiles.tile(z, x, y)
            response = HttpResponse(
                content=data,
                status=200,
            )
            response["Content-Type"] = "application/x-protobuf"
            response["Content-Encoding"] = "gzip"

            return response

        except MissingTileError:
            return HttpResponse(
                status=204,
            )


@cache_page
def tile_json_gl(request, source_slug):
    source = MBTSource.objects.get(slug=source_slug)
    with open_mbtiles(source.file.path) as mbtiles:
        metadata = mbtiles.metadata()

        # Load valid tilejson keys from the mbtiles metadata
        valid_tilejson_keys = (
            # MUST
            "name",
            "format",
            # SHOULD
            "bounds",
            "center",
            "minzoom",
            "maxzoom",
            # MAY
            "attribution",
            "description",
            "type",
            "version",
            # UNSPECIFIED
            "scheme",
        )
        spec = {key: metadata[key] for key in valid_tilejson_keys if key in metadata}

        if spec["format"] == "pbf":
            spec["vector_layers"] = metadata["json"]["vector_layers"]
        else:
            raise NotImplementedError(f"Only mbtiles in pbf format are supported. Found {spec['format']}")

        # Optional fields
        spec["scheme"] = spec.get("scheme", "xyz")
        spec["bounds"] = spec.get("bounds", WORLD_BOUNDS)
        spec["minzoom"] = spec.get("minzoom", DEFAULT_MINZOOM)
        spec["maxzoom"] = spec.get("maxzoom", DEFAULT_MINZOOM)
        spec["center"] = spec.get("center", center_from_bounds(spec["bounds"], DEFAULT_ZOOM))

        # Tile
        tile_url = get_full_url(request, (reverse("tile_gl", args=(source.slug, 0, 0, 0))))
        tile_url = tile_url.replace("/0/0/0.pbf", r"/{z}/{x}/{y}.pbf")
        spec["tiles"] = [tile_url]

        # Version
        spec["tilejson"] = "3.0.0"

        return JsonResponse(spec)


@cache_page
def style_json_gl(request, source_slug):
    source = MBTSource.objects.get(slug=source_slug)
    tilejson_url = get_full_url(request, reverse("tile_json_gl", args=[source.slug]))

    # Copy before mutating to avoid altering cached/default style objects.
    style_config = deepcopy(source.json_style or {})

    style_config["id"] = source.pk
    style_config["name"] = source.name
    style_config["glyphs"] = "https://fonts.openmaptiles.org/{fontstack}/{range}.pbf"

    # Preserve custom raster/vector sources (e.g. external basemaps) and only
    # enforce the openmaptiles source URL for this MBTiles source.
    existing_sources = style_config.get("sources") or {}
    if not isinstance(existing_sources, dict):
        existing_sources = {}

    openmaptiles_source = existing_sources.get("openmaptiles") or {}
    if not isinstance(openmaptiles_source, dict):
        openmaptiles_source = {}

    mbtiles_exists = False
    try:
        mbtiles_path = source.file.path
        mbtiles_exists = bool(mbtiles_path and os.path.exists(mbtiles_path))
    except Exception:
        mbtiles_exists = False

    # If local MBTiles exists, serve local tile-json. Otherwise keep any
    # configured external URL and fallback to ICPAC's hosted OpenMapTiles.
    if mbtiles_exists:
        openmaptiles_source.update({"type": "vector", "url": tilejson_url})
    else:
        openmaptiles_source["type"] = "vector"
        if not openmaptiles_source.get("url"):
            openmaptiles_source["url"] = FALLBACK_OPENMAPTILES_TILEJSON_URL

    existing_sources["openmaptiles"] = openmaptiles_source
    style_config["sources"] = existing_sources

    # Enforce correct default visibility for basemap layers.
    # The default basemap is "basemap-light"; all other basemap groups
    # (e.g. satellite, OSM, Google, ESRI) must start hidden so the map
    # doesn't flash multiple basemaps before the frontend applies its selection.
    DEFAULT_BASEMAP_GROUP_KEY = "basemap_light"
    mapbox_groups = (style_config.get("metadata") or {}).get("mapbox:groups") or {}
    basemap_group_keys = {
        k for k, v in mapbox_groups.items()
        if isinstance(v, dict) and "basemap" in (v.get("name") or "").lower()
    }

    if basemap_group_keys:
        for layer in style_config.get("layers") or []:
            layer_group = (layer.get("metadata") or {}).get("mapbox:group")
            if layer_group in basemap_group_keys:
                layout = layer.setdefault("layout", {})
                if layer_group == DEFAULT_BASEMAP_GROUP_KEY:
                    layout["visibility"] = "visible"
                else:
                    layout["visibility"] = "none"

    return JsonResponse(style_config)
