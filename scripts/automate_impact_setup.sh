#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE_DIR="${1:-/home/koros/Downloads/OneDrive_1_2-15-2026}"
MAP_BASE_URL="${MAP_BASE_URL:-/mapcache/}"

CMS_CONTAINER="${CMS_CONTAINER:-eafw-cms}"
MAPCACHE_CONTAINER="${MAPCACHE_CONTAINER:-eafw-mapcache}"
MAPSERVER_PUBLIC_URL="${MAPSERVER_PUBLIC_URL:-http://127.0.0.1:9068/mapserver/}"
MAPCACHE_PUBLIC_URL="${MAPCACHE_PUBLIC_URL:-http://127.0.0.1:9068/mapcache/}"

DST_DIR="$ROOT_DIR/data/mapfiles/data/return_periods"
TIF_25="M6_25y_clipped.tif"
TIF_100="M6_100y_clipped.tif"

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Missing required command: $1" >&2
    exit 1
  }
}

require_file() {
  local path="$1"
  [[ -f "$path" ]] || {
    echo "Required file not found: $path" >&2
    exit 1
  }
}

smoke_test() {
  local base="$1"
  local layer="$2"
  local bbox="3365675.229452882,-234814.5508920609,3443946.7464169026,-156543.03392804042"
  local url="${base}?SERVICE=WMS&VERSION=1.1.1&REQUEST=GetMap&LAYERS=${layer}&STYLES=&FORMAT=image/png&TRANSPARENT=true&SRS=EPSG:3857&BBOX=${bbox}&WIDTH=256&HEIGHT=256"

  local headers
  headers="$(mktemp)"
  local body
  body="$(mktemp)"

  curl -sS -D "$headers" "$url" -o "$body"
  local code
  code="$(awk '/^HTTP\//{c=$2} END{print c}' "$headers")"
  local ctype
  ctype="$(awk -F': ' 'tolower($1)=="content-type"{print tolower($2)}' "$headers" | tr -d '\r' | tail -n1)"

  if [[ "$code" != "200" ]]; then
    echo "Smoke test failed for $layer at $base (HTTP $code)" >&2
    cat "$headers" >&2
    rm -f "$headers" "$body"
    exit 1
  fi

  if [[ "$ctype" != image/* ]]; then
    echo "Smoke test failed for $layer at $base (unexpected content-type: $ctype)" >&2
    cat "$headers" >&2
    rm -f "$headers" "$body"
    exit 1
  fi

  echo "OK: $layer via $base (HTTP $code, $ctype)"
  rm -f "$headers" "$body"
}

require_cmd docker
require_cmd curl

require_file "$SOURCE_DIR/$TIF_25"
require_file "$SOURCE_DIR/$TIF_100"

mkdir -p "$DST_DIR"
cp -f "$SOURCE_DIR/$TIF_25" "$DST_DIR/$TIF_25"
cp -f "$SOURCE_DIR/$TIF_100" "$DST_DIR/$TIF_100"
echo "Copied return-period TIFFs into $DST_DIR"

docker exec -i "$CMS_CONTAINER" /opt/venv/bin/python manage.py shell <<PY
from django.db import transaction
from geomanager.models import Category, SubCategory, Dataset, Metadata
from geomanager.models import WmsLayer, WmsRequestLayer

map_base_url = "${MAP_BASE_URL}"

required_subcats = ["Exposure", "Flood Extent / Hazard"]
required_exposure = ["Population", "Buildings", "Roads", "Cropland", "Hospitals", "Health Facilities"]

with transaction.atomic():
    impact = Category.objects.filter(title__icontains="impact").first()
    if not impact:
        impact = Category.objects.create(title="Impact", icon="", active=True, public=True)

    impact.active = True
    impact.public = True
    impact.save(update_fields=["active", "public", "modified"])

    subcats = {}
    for title in required_subcats:
        subcat, _ = SubCategory.objects.get_or_create(
            category=impact,
            title=title,
            defaults={"active": True, "public": True},
        )
        if not subcat.active or not subcat.public:
            subcat.active = True
            subcat.public = True
            subcat.save(update_fields=["active", "public"])
        subcats[title] = subcat

    allowed_titles = set(required_exposure + ["Flood extent/Hazard"])
    for ds in Dataset.objects.filter(category=impact):
        if ds.title not in allowed_titles:
            ds.delete()

    for title in required_exposure:
        ds = Dataset.objects.filter(title__iexact=title).first()
        if not ds:
            ds = Dataset.objects.create(
                title=title,
                category=impact,
                sub_category=subcats["Exposure"],
                layer_type="wms" if title == "Population" else "raster_file",
                dataset_slug=title.lower().replace(" ", "-"),
                published=True,
                public=True,
                multi_temporal=False,
                multi_layer=False,
                initial_visible=False,
                current_time_method="latest_from_source",
                can_clip=True,
            )
        ds.category = impact
        ds.sub_category = subcats["Exposure"]
        ds.dataset_slug = title.lower().replace(" ", "-")
        ds.published = True
        ds.public = True
        ds.save()

    flood_ds, _ = Dataset.objects.get_or_create(
        title="Flood extent/Hazard",
        category=impact,
        defaults={
            "sub_category": subcats["Flood Extent / Hazard"],
            "layer_type": "wms",
            "dataset_slug": "flood-extent-hazard",
            "published": True,
            "public": True,
            "multi_temporal": False,
            "multi_layer": True,
            "enable_all_multi_layers_on_add": False,
            "initial_visible": False,
            "current_time_method": "latest_from_source",
            "can_clip": False,
        },
    )

    flood_ds.category = impact
    flood_ds.sub_category = subcats["Flood Extent / Hazard"]
    flood_ds.layer_type = "wms"
    flood_ds.dataset_slug = "flood-extent-hazard"
    flood_ds.summary = "Fluvial flood hazard model-consensus for 25-year and 100-year return periods"
    flood_ds.published = True
    flood_ds.public = True
    flood_ds.multi_temporal = False
    flood_ds.multi_layer = True
    flood_ds.enable_all_multi_layers_on_add = False
    flood_ds.initial_visible = False
    flood_ds.current_time_method = "latest_from_source"
    flood_ds.can_clip = False
    flood_ds.save()

    flood_ds.raster_file_layers.all().delete()

    md = flood_ds.metadata
    if md is None:
        md = Metadata.objects.create(title="Aggregated Fluvial Flood Hazard Outputs for Africa")
        flood_ds.metadata = md
        flood_ds.save(update_fields=["metadata", "modified"])

    md.title = "Aggregated Fluvial Flood Hazard Outputs for Africa"
    md.subtitle = "Global Flood Partnership model-consensus hazard (return periods)"
    md.function = "Model-consensus fluvial flood hazard indicator for screening, uncertainty assessment, and planning."
    md.resolution = None
    md.geographic_coverage = "Africa"
    md.source = "Global Flood Partnership / Global Flood Model Intercomparison Project"
    md.license = "Creative Commons Attribution 4.0 International (CC BY 4.0)"
    md.frequency_of_update = "Static (scenario-based return periods)"
    md.overview = (
        "<p>Aggregated fluvial flood hazard outputs for Africa derived from six global flood models. "
        "Pixel values represent inter-model inundation agreement (0-6), where higher values indicate stronger consensus.</p>"
        "<p>Available return periods in this deployment: 1-in-25 years and 1-in-100 years.</p>"
        "<p>Data characteristics: WGS84, ~1/1200 degree (~90 m), single-band integer GeoTIFF.</p>"
    )
    md.cautions = (
        "<p>This is a model-consensus hazard layer, not observed inundation depth. "
        "Use with local context and exposure/vulnerability layers.</p>"
    )
    md.citation = (
        "<p>Trigg, M.A., Bates, P.D., Neal, J.C. et al. (2016). "
        "The credibility challenge for global fluvial flood risk analysis. Environmental Research Letters.</p>"
    )
    md.learn_more = "https://doi.org/10.1088/1748-9326/11/1/014002"
    md.save()

    return_period_legend = [
        {
            "type": "legend",
            "value": {
                "type": "basic",
                "items": [
                    {"value": "Low consensus (1/6)", "color": "#DEEBF7"},
                    {"value": "Consensus (2/6)", "color": "#C6DBEF"},
                    {"value": "Consensus (3/6)", "color": "#9ECAE1"},
                    {"value": "Consensus (4/6)", "color": "#6BAED6"},
                    {"value": "High consensus (5/6)", "color": "#3182BD"},
                    {"value": "Very high consensus (6/6)", "color": "#08519C"},
                ],
            },
        }
    ]

    desired = [
        ("25-year return period", "flood_extent_rp25", True, 0),
        ("100-year return period", "flood_extent_rp100", False, 1),
    ]

    keep = []
    for title, req_layer, is_default, order in desired:
        wl = flood_ds.wms_layers.filter(title__iexact=title).first()
        if wl is None:
            wl = flood_ds.wms_layers.create(
                title=title,
                default=is_default,
                base_url=map_base_url,
                version="1.1.1",
                width=256,
                height=256,
                transparent=True,
                srs="EPSG:3857",
                format="image/png",
                request_time_from_capabilities=False,
                can_clip=False,
                order=order,
                legend=return_period_legend,
            )
        else:
            wl.title = title
            wl.default = is_default
            wl.base_url = map_base_url
            wl.version = "1.1.1"
            wl.width = 256
            wl.height = 256
            wl.transparent = True
            wl.srs = "EPSG:3857"
            wl.format = "image/png"
            wl.request_time_from_capabilities = False
            wl.can_clip = False
            wl.order = order
            wl.legend = return_period_legend
            wl.save()

        req = wl.wms_request_layers.first()
        if req is None:
            WmsRequestLayer.objects.create(layer=wl, name=req_layer, sort_order=0)
        else:
            req.name = req_layer
            req.sort_order = 0
            req.save(update_fields=["name", "sort_order"])
            wl.wms_request_layers.exclude(pk=req.pk).delete()

        keep.append(wl.pk)

    flood_ds.wms_layers.exclude(pk__in=keep).delete()

    # --- Population (LandScan) WMS layer ---
    pop_ds = Dataset.objects.filter(title__iexact="Population", category=impact).first()
    if pop_ds:
        pop_ds.layer_type = "wms"
        pop_ds.multi_temporal = False
        pop_ds.multi_layer = False
        pop_ds.initial_visible = False
        pop_ds.can_clip = False
        pop_ds.save()

        pop_md = pop_ds.metadata
        if pop_md is None:
            pop_md = Metadata.objects.create(title="LandScan Global 2024 Population Distribution")
            pop_ds.metadata = pop_md
            pop_ds.save(update_fields=["metadata", "modified"])

        pop_md.title = "LandScan Global 2024 Population Distribution"
        pop_md.subtitle = "Ambient (average over 24 hours) population distribution"
        pop_md.function = "High-resolution population distribution for exposure and vulnerability assessment."
        pop_md.resolution = "~1 km (30 arc-seconds)"
        pop_md.geographic_coverage = "Greater Horn of Africa"
        pop_md.source = "Oak Ridge National Laboratory (ORNL)"
        pop_md.license = "Creative Commons Attribution 4.0 International (CC BY 4.0)"
        pop_md.frequency_of_update = "Annual"
        pop_md.overview = (
            "<p>LandScan Global 2024 represents an ambient (average over 24 hours) population distribution "
            "at approximately 1 km resolution. Values indicate estimated population count per grid cell.</p>"
            "<p>This layer has been clipped to the Greater Horn of Africa administrative extent.</p>"
        )
        pop_md.cautions = (
            "<p>Population counts are modelled estimates, not census enumerations. "
            "Use for screening and planning, not as ground truth.</p>"
        )
        pop_md.citation = (
            "<p>Sims, K., Reith, A., Bright, E., McKee, J., Rose, A. (2023). "
            "LandScan Global 2024. Oak Ridge National Laboratory.</p>"
        )
        pop_md.learn_more = "https://landscan.ornl.gov/"
        pop_md.save()

        pop_legend = [
            {
                "type": "legend",
                "value": {
                    "type": "gradient",
                    "items": [
                        {"value": "1 - 5", "color": "#FFFFBE"},
                        {"value": "6 - 25", "color": "#FFFF73"},
                        {"value": "26 - 50", "color": "#FFFF00"},
                        {"value": "51 - 100", "color": "#FFAA00"},
                        {"value": "101 - 500", "color": "#FF6600"},
                        {"value": "501 - 2500", "color": "#FF0000"},
                        {"value": "2501 - 5000", "color": "#CC0000"},
                        {"value": "5001+", "color": "#730000"},
                    ],
                },
            }
        ]

        pop_wl = pop_ds.wms_layers.first()
        if pop_wl is None:
            pop_wl = pop_ds.wms_layers.create(
                title="LandScan Population 2024",
                default=True,
                base_url=map_base_url,
                version="1.1.1",
                width=256,
                height=256,
                transparent=True,
                srs="EPSG:3857",
                format="image/png",
                request_time_from_capabilities=False,
                can_clip=False,
                order=0,
                legend=pop_legend,
            )
        else:
            pop_wl.title = "LandScan Population 2024"
            pop_wl.default = True
            pop_wl.base_url = map_base_url
            pop_wl.version = "1.1.1"
            pop_wl.width = 256
            pop_wl.height = 256
            pop_wl.transparent = True
            pop_wl.srs = "EPSG:3857"
            pop_wl.format = "image/png"
            pop_wl.request_time_from_capabilities = False
            pop_wl.can_clip = False
            pop_wl.order = 0
            pop_wl.legend = pop_legend
            pop_wl.save()

        pop_req = pop_wl.wms_request_layers.first()
        if pop_req is None:
            WmsRequestLayer.objects.create(layer=pop_wl, name="landscan_population", sort_order=0)
        else:
            pop_req.name = "landscan_population"
            pop_req.sort_order = 0
            pop_req.save(update_fields=["name", "sort_order"])
            pop_wl.wms_request_layers.exclude(pk=pop_req.pk).delete()

        pop_ds.wms_layers.exclude(pk=pop_wl.pk).delete()
        print("Population (LandScan) WMS layer configured.")

print("CMS Impact configuration updated.")
PY

echo "Patching MapCache runtime config to disable symlink/detect_blank..."
docker exec -u 0 "$MAPCACHE_CONTAINER" sh -lc "python3 - <<'PY'
import json
cfg_path='/opt/mapcache/mapcache_config.json'
with open(cfg_path) as f:
    cfg=json.load(f)
for cache in cfg.get('caches', []):
    opts = cache.get('options', {})
    opts.pop('detect_blank', None)
    opts.pop('symlink_blank', None)
with open(cfg_path, 'w') as f:
    json.dump(cfg, f, indent=2)
print('updated', cfg_path)
PY
cd /opt/mapcache
python3 generate_mapcache_config.py mapcache_config.json mapcache.xml true
nginx -s reload || true"

echo "Running smoke tests..."
smoke_test "$MAPSERVER_PUBLIC_URL" "flood_extent_rp25"
smoke_test "$MAPSERVER_PUBLIC_URL" "flood_extent_rp100"
smoke_test "$MAPSERVER_PUBLIC_URL" "landscan_population"
smoke_test "$MAPCACHE_PUBLIC_URL" "flood_extent_rp25"
smoke_test "$MAPCACHE_PUBLIC_URL" "flood_extent_rp100"
smoke_test "$MAPCACHE_PUBLIC_URL" "landscan_population"

echo "Done. Impact setup is automated and applied."
