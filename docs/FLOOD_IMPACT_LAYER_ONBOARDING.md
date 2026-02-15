# Flood Impact Raster Onboarding

This runbook registers, ingests, and exposes new flood raster layers in CMS/GeoManager and MapViewer.

## 0) Rebuild CMS image (Docker deployments)

If your CMS container is already running, rebuild so the new management command is available:

```bash
docker compose build eafw_cms
docker compose up -d eafw_cms
```

## 1) Apply migrations

From the project root:

```bash
docker compose exec eafw_cms uv run python manage.py migrate
```

This ensures the Impact subcategories exist and are active/public:

- Exposure
- Susceptibility
- Vulnerability
- Resilience

## 2) Prepare a manifest

Use `docs/flood_impact_layers.manifest.example.json` as a template.

Required fields per entry:

- `title`
- `dataset_slug`
- `sub_category` (must be one of: Exposure, Susceptibility, Vulnerability, Resilience)
- `auto_ingest_directory`

Optional fields:

- `layer_title`
- `summary`
- `date_format` (default `yyyy-MM-dd HH:mm`)
- `time_parameter` (default `time`)
- `time_prefix`
- `published`, `public`, `can_clip`, `multi_temporal`, `initial_visible`, `current_time_method`

## 3) Bootstrap datasets and raster layers

Dry-run first:

```bash
docker compose exec eafw_cms \
  uv run python manage.py bootstrap_impact_flood_layers \
  /opt/eafw_cms/docs/flood_impact_layers.manifest.example.json \
  --dry-run
```

Apply changes:

```bash
docker compose exec eafw_cms \
  uv run python manage.py bootstrap_impact_flood_layers \
  /opt/eafw_cms/docs/flood_impact_layers.manifest.example.json
```

What this command does:

- Ensures Impact category/subcategories are present
- Creates or updates `raster_file` datasets
- Creates or updates `RasterFileLayer` with:
  - `auto_ingest_from_directory=true`
  - `auto_ingest_use_custom_directory_name=true`
  - `auto_ingest_custom_directory_name=<manifest value>`

## 4) Place raster files for ingestion

Copy files into:

```text
${GEOMANAGER_AUTO_INGEST_RASTER_DATA_DIR}/<auto_ingest_directory>/
```

GeoTIFF filenames must end with an ISO UTC timestamp:

```text
..._YYYY-MM-DDTHH:MM:SS.000Z.tif
```

Example:

```text
Exposure_Flood_2026-02-12T00:00:00.000Z.tif
```

## 5) Ingest raster files

Option A: ingest while bootstrapping:

```bash
docker compose exec eafw_cms \
  uv run python manage.py bootstrap_impact_flood_layers \
  /opt/eafw_cms/docs/flood_impact_layers.manifest.example.json \
  --ingest --overwrite
```

Option B: manual per file event:

```bash
docker compose exec eafw_cms \
  uv run python manage.py ingest_geomanager_raster created /geomanager/data/<dir>/<file>.tif --overwrite
```

## 6) Verify API exposure

Check mapviewer config includes datasets under Impact:

```text
/api/mapviewer-config
```

Check tilejson for a layer:

```text
/api/raster/<layer_uuid>/tiles.json
```

Check rendered tiles (with time and clipping support):

```text
/api/raster-tiles/<layer_uuid>/{z}/{x}/{y}?time=<timestamp>&geostore_id=<id>
```

Notes:

- Use `/api/raster-tiles/...` (hyphen), not `/api/raster_tiles/...`.
- `geostore_id` is effective when dataset `can_clip=true`.

## 7) Verify in MapViewer

Open `/mapviewer/`, then confirm:

- Category: Impact
- Subcategories: Exposure, Susceptibility, Vulnerability, Resilience
- Datasets are visible/toggleable
- Time selector shows ingested timestamps

## 8) One-Command Automation

Use the helper script to automate the full setup for Impact flood extent layers:

```bash
./scripts/automate_impact_setup.sh /home/koros/Downloads/OneDrive_1_2-15-2026
```

What it automates:

- Copies `M6_25y_clipped.tif` and `M6_100y_clipped.tif` into `data/mapfiles/data/return_periods/`
- Configures CMS Impact category/subcategories/datasets
- Converts `Flood extent/Hazard` to WMS multi-layer
- Creates 2 layers:
  - `25-year return period` (`flood_extent_rp25`)
  - `100-year return period` (`flood_extent_rp100`)
- Updates metadata fields for the flood extent dataset
- Patches MapCache runtime config to disable symlink/detect blank tile behavior
- Regenerates `mapcache.xml` and reloads nginx in the mapcache container
- Runs smoke tests for MapServer and MapCache WMS endpoints
