from copy import deepcopy
import json

from django.http import HttpResponse, JsonResponse
from django.urls import reverse
from wagtail.api.v2.utils import get_full_url
from wagtailcache.cache import cache_page

from geomanager.errors import MissingTileError, MBTilesInvalid
from geomanager.models import MBTSource
from geomanager.utils.tile_gl import center_from_bounds, open_mbtiles

DEFAULT_ZOOM = 13
DEFAULT_MINZOOM = 7
DEFAULT_MAXZOOM = 15
WORLD_BOUNDS = [-180, -85.05112877980659, 180, 85.0511287798066]


def _read_mbtiles_metadata_fallback(mbtiles):
    """
    Read enough metadata for TileJSON even when strict MBTiles validation fails.
    The homepage minimap only needs a valid tilejson response, not full schema validation.
    """
    cursor = mbtiles._connection.cursor()
    cursor.execute("SELECT name, value FROM metadata")
    metadata = {row[0]: row[1] for row in cursor}
    cursor.close()

    if "bounds" in metadata and isinstance(metadata["bounds"], str):
        metadata["bounds"] = [float(val.strip()) for val in metadata["bounds"].split(",")]

    if "center" in metadata and isinstance(metadata["center"], str):
        metadata["center"] = [float(val.strip()) for val in metadata["center"].split(",")]

    for zoom_key in ("minzoom", "maxzoom"):
        if zoom_key in metadata:
            try:
                metadata[zoom_key] = float(metadata[zoom_key])
            except (TypeError, ValueError):
                metadata.pop(zoom_key, None)

    if "json" in metadata and isinstance(metadata["json"], str):
        try:
            metadata["json"] = json.loads(metadata["json"])
        except Exception:
            metadata["json"] = {}

    return metadata


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
        try:
            metadata = mbtiles.metadata()
        except MBTilesInvalid:
            metadata = _read_mbtiles_metadata_fallback(mbtiles)

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
            vector_layers = (metadata.get("json") or {}).get("vector_layers")
            if vector_layers:
                spec["vector_layers"] = vector_layers
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

    style_config = deepcopy(source.json_style or {})
    style_sources = deepcopy(style_config.get("sources") or {})

    style_config["id"] = source.pk
    style_config["name"] = source.name
    style_config["glyphs"] = "https://fonts.openmaptiles.org/{fontstack}/{range}.pbf"
    style_sources["openmaptiles"] = {"type": "vector", "url": tilejson_url}
    style_config["sources"] = style_sources

    return JsonResponse(style_config)
