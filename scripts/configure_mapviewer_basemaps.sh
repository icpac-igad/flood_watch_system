#!/usr/bin/env bash
set -euo pipefail

CMS_CONTAINER="${CMS_CONTAINER:-eafw-cms}"

docker exec -i "$CMS_CONTAINER" /opt/venv/bin/python manage.py shell <<'PY'
from copy import deepcopy
from wagtail.models import Site
from geomanager.constants import DEFAULT_OPEN_MAP_TILES_STYLE
from geomanager.models.geomanager_settings import GeomanagerSettings

site = Site.objects.filter(is_default_site=True).first()
if not site:
    raise SystemExit("No default site found.")

settings = GeomanagerSettings.for_site(site)
source = settings.tile_gl_source
if not source:
    raise SystemExit("No tile_gl_source configured in GeomanagerSettings.")

style = deepcopy(DEFAULT_OPEN_MAP_TILES_STYLE)
metadata = style.setdefault("metadata", {})
groups = metadata.setdefault("mapbox:groups", {})

for group_id, group_name in [
    ("basemap_google_satellite", "basemap-google-satellite"),
    ("basemap_esri_world_imagery", "basemap-esri-world-imagery"),
    ("basemap_openstreetmap", "basemap-openstreetmap"),
]:
    groups[group_id] = {"name": group_name, "collapsed": False}

sources = style.setdefault("sources", {})
if sources.get("openmaptiles", {}).get("type") == "vector":
    # Keep ICPAC's hosted vector tiles as the base source when local MBTiles
    # is unavailable in this environment.
    sources["openmaptiles"]["url"] = "https://eahazardswatch.icpac.net/tileserver-gl/data/v3.json"

sources["google_satellite"] = {
    "type": "raster",
    "tiles": ["https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}"],
    "tileSize": 256,
    "attribution": "Google",
}
sources["esri_world_imagery"] = {
    "type": "raster",
    "tiles": ["https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"],
    "tileSize": 256,
    "attribution": "Esri, Maxar, Earthstar Geographics",
}
sources["osm_standard"] = {
    "type": "raster",
    "tiles": ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
    "tileSize": 256,
    "attribution": "© OpenStreetMap contributors",
}

layers = style.setdefault("layers", [])
custom_layer_ids = {
    "basemap-google-satellite-layer",
    "basemap-esri-world-imagery-layer",
    "basemap-openstreetmap-layer",
}
layers = [layer for layer in layers if layer.get("id") not in custom_layer_ids]

new_layers = [
    {
        "id": "basemap-google-satellite-layer",
        "type": "raster",
        "source": "google_satellite",
        "metadata": {"mapbox:group": "basemap_google_satellite"},
        "paint": {"raster-opacity": 1},
    },
    {
        "id": "basemap-esri-world-imagery-layer",
        "type": "raster",
        "source": "esri_world_imagery",
        "metadata": {"mapbox:group": "basemap_esri_world_imagery"},
        "paint": {"raster-opacity": 1},
    },
    {
        "id": "basemap-openstreetmap-layer",
        "type": "raster",
        "source": "osm_standard",
        "metadata": {"mapbox:group": "basemap_openstreetmap"},
        "paint": {"raster-opacity": 1},
    },
]

insert_index = 1 if layers and layers[0].get("type") == "background" else 0
layers[insert_index:insert_index] = new_layers
style["layers"] = layers

source.use_default_style = False
source.open_map_style_json = style
source.save(update_fields=["use_default_style", "open_map_style_json"])

settings.base_maps = [
    (
        "basemap",
        {
            "label": "Current Basemap",
            "backgroundColor": "#f3f6fb",
            "basemapGroup": "basemap-light",
            "labelsGroup": "labels-light",
            "url": "",
            "default": True,
        },
    ),
    (
        "basemap",
        {
            "label": "Esri World Imagery",
            "backgroundColor": "#0f172a",
            "basemapGroup": "basemap-esri-world-imagery",
            "labelsGroup": "labels-light",
            "url": "https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
            "default": False,
        },
    ),
    (
        "basemap",
        {
            "label": "OpenStreetMap",
            "backgroundColor": "#d7e6f5",
            "basemapGroup": "basemap-openstreetmap",
            "labelsGroup": "labels-light",
            "url": "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
            "default": False,
        },
    ),
]
settings.save(update_fields=["base_maps"])

print("Configured mapviewer basemaps:")
for block in settings.base_maps:
    value = block.value
    print(f"- {value.get('label')} ({value.get('basemapGroup')})")
PY
