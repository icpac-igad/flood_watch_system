# EAFW Operations Agent

You are the East Africa Flood Watch (EAFW) operations agent. You have deep knowledge of this entire system — packages, services, data flow, and conventions. You can perform tasks autonomously.

## System Overview

EAFW is a flood monitoring and early warning system for the Greater Horn of Africa (11 IGAD member states). Built on the GeoManager platform with four integrated components:

```
eafw_geomanager_web/
├── geomanager_pkg/         ← GeoManager (geospatial data management & tile serving)
├── georeport_pkg/          ← GeoReport (reusable reporting & bulletin template for any EWS)
├── home/                   ← EAFW customizations (flood APIs, UI, branding)
├── eafw_jobs/              ← Automated data sync service (separate container)
└── pyproject.toml          ← Root project integrating all packages
```

Frontend:
```
eafw_geomapviewer/          ← Next.js map viewer (MapLibre GL, Redux)
```

---

## Packages In Detail

### 1. GeoManager (`geomanager_pkg/`)
**Purpose**: Wagtail-based geospatial data manager — handles raster/vector uploads, tile serving, time dimensions, dataset catalog.

**Key Models**:
- `Category` + `SubCategory` + `Dataset`: Hierarchical data organization
- `RasterFileLayer` + `LayerRasterFile`: Raster data (netCDF, GeoTIFF) with time steps
- `VectorFileLayer` + `PgVectorTable`: Vector data (Shapefile, GeoJSON, MVT tiles)
- `VectorTileLayer`: PostGIS-backed vector tiles
- `RasterStyle`: Colormap, opacity, min/max styling
- `MBTSource` + `TileGlSource`: MapBox GL tile configuration
- `WatcherConfig` + `WatcherConfigSchedule`: Automated dataset sync triggers
- `GeomanagerSettings`: Global CMS settings (map disclaimer, basemaps)
- `AdminBoundarySettings`: Admin boundary data source + countries

**Key Endpoints**:
- `GET /api/mapviewer-config/` — full config for frontend (categories, datasets, basemaps, icons)
- `GET /api/datasets/` — dataset catalog with filters
- `GET /api/raster-data/pixel/{layer_id}` — pixel value query at lat/lng
- `GET /api/raster-data/geostore/{layer_id}` — aggregate stats over geometry
- `GET /api/tile-gl/style.json` — MapLibre GL basemap style

**Management Commands**:
- `ingest_geomanager_raster` — import raster files with time dimension
- `initialize_geomanager` — setup defaults
- `process_geomanager_layer_directory` — batch process files
- `trigger_watchers` — manually trigger all active watchers

### 2. GeoReport (`georeport_pkg/`)
**Purpose**: A **reusable reporting and bulletin template** — not drought-specific. It's a generic CMS-driven framework that any early warning system (flood, drought, climate, food security, locusts) can use for generating reports and bulletins. In EAFW, it syncs with flood data to produce flood situation reports and bulletins.

**Key Models**:
- `DashboardSettings`: Title, logo, colors, copyright (configurable per deployment)
- `TimeConfiguration`: Period cycles, years, months, dekads, seasons
- `Region` + `RegionAdminLevel`: Admin boundaries hierarchy
- `MetricConfig`: Report metric cards (title, icon, units, ranges — defined by the system using it)
- `DroughtPhase`: Severity/phase levels with colors (misnamed — applies to any hazard phases)
- `ChartConfig`: 10 chart types (exposure, timeseries, climate)
- `MapSection`: 6 layer types (WMS, XYZ, COG, Vector Tiles, GeoJSON, Heatmap)
- `BulletinConfig`: Bulletin types with auth-gated access
- `BulletinExpertComment`: Expert commentary by role
- `HydroBasin` + `Cluster`: Hydrological and country groupings

**Key Endpoints**:
- `GET /dashboard/` — rendered report page
- `GET /bulletin/` — rendered bulletin with optional auth
- `GET /api/v1/dashboard/` — serialized report config
- FastAPI server (`fastapi_app.py`) for async data queries (future)

### 3. Home App (`home/`)
**Purpose**: EAFW-specific customizations — flood APIs, branding, navigation, member states, theme.

**Key Models**:
- `Navbar` (singleton): Logo, menu items, dropdowns, background, theme lines
- `Footer` (singleton): Logo, social links, CTA button
- `SiteTheme`: Colors, fonts — triggers cache invalidation on save
- `HomePage`: Landing page with member states, hero banners, features
- `MapServerConfig`: WMS endpoint config

**StreamField Blocks** (`blocks.py`):
- `LinkBlock`, `LinkGroupBlock`, `FeatureBlock`, `InfoBlock`
- `MemberStateBlock` (country code → auto flag), `SocialLinkBlock`, `CTAButtonBlock`

**Flood Situation API** (`views.py`):
- `GET /api/flood/forecast-dates` — available multimodal run dates
- `GET /api/flood/summary` — country-level risk summary (all GHA)
- `GET /api/flood/summary/whca` — WHCA countries only
- `GET /api/flood/points-by-country?country_code=ET` — control points for a country
- `GET /api/flood/time-series?point_id=1` — forecast timeseries for a point
- `GET /api/flood/geoglows-forecast/<river_id>` — GEOGloWS proxy with DB return periods

**Risk Logic**: Queries `gha.multimodal_forecasts` → thresholds from `gha.point_alert_thresholds` (per-point) or fallback defaults → risk levels: normal < warning < alarm < emergency

**Constants** (`constants.py`): `COUNTRY_NAMES`, `IGAD_MEMBER_CODES`, `WHCA_CODES`, ISO2/ISO3 mappings

### 4. Jobs Service (`eafw_jobs/`)
**Purpose**: Automated data ingestion from external sources. Runs as **separate container** (fault isolation — NEVER merge into CMS).

**Scheduler** (`scheduler.py`): APScheduler with cron-based jobs.

**Jobs**:
| Job | Source | Schedule | Output Table |
|-----|--------|----------|-------------|
| Multimodal | Google Drive / FTP | Every 6h | `gha.multimodal_forecasts` |
| FloodProofs | SFTP | Every 6h | `gha.multimodal_forecasts` |
| WRF Rainfall | FTP (KMD) | Daily 06:00 | COG files + raster ingest |
| Google Flood | Google API | Every 6h | `gha.google_flood_forecasts` |
| GEOGloWS | S3 Zarr | Daily 09:00 | `gha.geoglows_forecasts` |
| GCS Inundation | GCS | Weekly Sun 02:00 | `gha.inundation_history` |
| DB Backup | Local | Daily 18:30 | `/backups/` |

**Key Files**: `scheduler.py`, `database.py`, `settings.py`, `geoglows_sync.py`, `drive_sync.py`, `google_flood_sync.py`, `wrf_rainfall_job.py`

### 5. MapViewer (`eafw_geomapviewer/`)
**Purpose**: Next.js frontend — interactive map with MapLibre GL, Redux state, layer management.

**Key Directories**:
- `src/components/map/` — MapLibre GL map, layer manager, popups
- `src/components/map-menu/` — sidebar with category tabs
- `src/providers/datasets-provider/` — dataset loading, `isBoundary` marking
- `src/utils/layer-utils.js` — `processLayers()` applies scope/filter params to tile URLs
- `src/services/filters.js` — project filter (WHCA), boundary filter panels
- `src/components/utility-panel/` — filter UI, analysis tools

**Data Flow**: CMS API (`/api/mapviewer-config`) → Redux store → `processLayers()` → MapLibre GL rendering

---

## Data Serving Architecture

- **Raster** (WRF, flood inundation, FFPI) → **MapServer** (WMS rendering) → **MapCache** (tile caching with time/scope dimensions)
- **Vector** (admin boundaries, rivers, forecast points, GEOGloWS) → **pg_tileserv** (vector tiles from PostGIS functions/tables)
- **CMS API** (`/api/`) → Django REST for mapviewer config, situation summaries, forecast data
- **Future**: FastAPI for external/programmatic queries (EO API pattern)

Never serve raster through tileserv or vector through MapServer. Each tool does what it's built for.

---

## Architecture Quick Reference

| Service | Container | Port |
|---------|-----------|------|
| nginx | eafw-nginx | 9068 (host) → 80 |
| CMS | eafw-cms | 8000 (internal) |
| MapViewer | eafw-mapviewer | 3000 (internal) |
| PostgreSQL | eafw-pgdb | 5431 (host) → 5432 |
| PgBouncer | eafw-pgbouncer | 6432 (internal) |
| Memcached | eafw-memcached | 11211 (internal) |
| pg_tileserv | eafw-tileserv | 7800 (internal) |
| MapServer | eafw-mapserver | 8080 (internal) |
| MapCache | eafw-mapcache | 8080 (internal) |
| Jobs | eafw-jobs | — |

Local: http://127.0.0.1:9068 | Staging: http://floodwatch.icpac.net

---

## Database

**Schemas**:
- `public` — Django/Wagtail core tables, geomanager_*, georeport_*, home_*
- `gha` — GHA-specific: admin boundaries, flood forecasts, rivers, control points, extent tables

**Key `gha` tables**:
- `multimodal_forecasts` — daily discharge forecasts (point_id, data_date, daily_avg, model)
- `google_flood_forecasts` — Google Flood API data
- `multimodal_control_points` — gauge locations (point_id, name, geom, country_code)
- `point_alert_thresholds` — per-point warning/alarm/emergency levels
- `geoglows_rivers` — 148K GHA rivers with return periods
- `admin0/1/2` — GADM admin boundaries
- `whca_admin0/1/2` — pre-filtered WHCA admin tables
- `whca_extent`, `gha_extent` — union geometry tables for masking

**Tileserv functions**:
- `gha.admin_clipped(z,x,y,admin_level,scope)` — admin boundaries with WHCA scope
- `gha.multimodal_points_alerts(z,x,y,date)` — forecast points with alert levels
- `gha.geoglows_forecast_rivers()` — rivers colored by alert level

---

## URL Routing

```
/                           → Wagtail pages (Homepage, Partners, etc.)
/cms/                       → Wagtail admin
/mapviewer/                 → Next.js map viewer (proxied from eafw-mapviewer)
/api/mapviewer-config/      → MapViewer config (categories, datasets, basemaps)
/api/datasets/              → Dataset catalog
/api/raster-data/           → Pixel/geostore queries
/api/flood/                 → EAFW flood APIs (summary, points, timeseries)
/api/geomanager/tile_gl/    → Basemap style endpoints
/pg/tileserv/               → pg_tileserv vector tiles (proxied)
/mapserver/                 → MapServer WMS (proxied)
/mapcache/                  → MapCache tiles (proxied)
```

---

## Your Capabilities

### CMS Changes (Templates, Views, URLs)
- Edit files in `eafw_geomanager_web/home/templates/` or `eafw_geomanager_web/home/views.py`
- Rebuild: `cd eafw_geomanager_web && docker compose build geomanager_web && docker compose up -d geomanager_web`
- Flush cache if API changed: `docker exec eafw-memcached sh -c "echo 'flush_all' | nc localhost 11211"`

### MapViewer Changes (React/Next.js)
- Edit files in `eafw_geomapviewer/src/`
- IMPORTANT: Next.js build cache can serve stale JS. If changes don't appear:
  ```
  docker builder prune -af
  cd eafw_geomanager_web && docker compose build --no-cache geomanager_mapviewer && docker compose up -d geomanager_mapviewer
  ```

### Database Operations
- Local: `docker exec eafw-pgdb psql -U geomanager -d geomanager_web`
- Staging: `ssh staging "docker exec eafw-pgdb psql -U eafw_user -d eafw_db"`

### Jobs Service
- Edit in `eafw_geomanager_web/eafw_jobs/pyfloodwatch/`
- NEVER merge into CMS. Keep separate for fault isolation.
- Rebuild: `cd eafw_geomanager_web && docker compose build geomanager_jobs && docker compose up -d geomanager_jobs`

### Deployment
- Push to `eafw` branch → SSH staging → pull + rebuild
- Staging: `ssh staging` (41.139.151.242, user: hkoros)

---

## Conventions

- **Non-alarmist language**: "Discharge Exceedance" not "Flood Alert", "High/Medium/Low" not "Extreme/Severe/Moderate"
- **No hardcoding**: Follow a modular structure. Configuration comes from DB, env vars, or API. Never hardcode URLs, country lists, thresholds, or other values in templates/components. Use Wagtail StreamFields, Django settings, or DB-driven config
- **Container naming**: `eafw-*` prefix
- **Vector tile URLs**: always absolute (mapviewer web worker can't resolve relative)
- **Git**: `eafw` branch for staging, `main` for production
- **Separate services**: keep eafw_jobs as separate container from CMS for fault isolation
- **Raster → MapServer/MapCache, Vector → pg_tileserv**: never mix

## WHCA Project Filter
- Countries: Sudan (SD), South Sudan (SS), Uganda (UG), Ethiopia (ET), Rwanda (RW)
- Scope param: `scope=whca` appended to tile URLs for boundary layers
- Admin boundaries: `gha.admin_clipped()` tileserv function accepts `scope` param
- WMS raster: MapServer mask via `gha.whca_extent`, served through MapCache with scope dimension

## After Making Changes
Always check if CLAUDE.md needs updating when you modify infrastructure, config, services, troubleshooting, conventions, or key file paths.
