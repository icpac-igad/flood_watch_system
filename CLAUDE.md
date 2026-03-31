# East Africa Flood Watch System — Operational Guide

## Project Overview

The East Africa Flood Watch (EAFW) is a flood monitoring and early warning system for the Greater Horn of Africa (GHA), covering 11 IGAD member states: Ethiopia, Kenya, Uganda, Sudan, South Sudan, Tanzania, Rwanda, Burundi, Somalia, Djibouti, Eritrea.

Built on the GeoManager platform with three core upstream repos maintained as subdirectories:
- `eafw_geomanager_web/` — Django/Wagtail CMS (from [geomanager-web](https://github.com/icpac-igad/geomanager-web))
- `eafw_geomanager/` — GeoManager Django app (from [geomanager](https://github.com/icpac-igad/geomanager))
- `eafw_geomapviewer/` — Next.js map viewer (from [geomapviewer](https://github.com/icpac-igad/geomapviewer))

## Architecture

### Services (Docker Compose)

All services run from `eafw_geomanager_web/docker-compose.yml`:

| Service | Container | Port | Purpose |
|---------|-----------|------|---------|
| nginx | eafw-nginx | 9068 (host) → 80 | Reverse proxy, entry point |
| CMS | eafw-cms | 8000 (internal) | Django/Wagtail + GeoManager |
| MapViewer | eafw-mapviewer | 3000 (internal) | Next.js map viewer |
| PostgreSQL | eafw-pgdb | 5431 (host) → 5432 | PostGIS database |
| PgBouncer | eafw-pgbouncer | 6432 (internal) | Connection pooler |
| Memcached | eafw-memcached | 11211 (internal) | Cache |
| MapServer | eafw-mapserver | 8080 (internal) | WMS/WFS raster rendering |
| MapCache | eafw-mapcache | 8080 (internal) | Tile caching |
| pg_tileserv | eafw-tileserv | 7800 (internal) | Vector tiles |
| Jobs | eafw-jobs | — | Data sync scheduler |

### Important: MapServer/MapCache run on port 8080 (non-root user can't bind 80).

### Database

- **Local**: `geomanager` user, `geomanager_web` database, port 5431
- **Staging**: `eafw_user` user, `eafw_db` database, port 5441

Key schemas:
- `cms` — Django/Wagtail models (geomanager_category, geomanager_dataset, etc.)
- `gha` — GHA-specific data (admin boundaries, flood points, rivers, etc.)

### Volumes (Local)

Local development uses `eafw_clean_*` volumes (mapped via `docker-compose.override.yml`):
- `eafw_clean_pgdata` — database
- `eafw_clean_media` — uploaded media files
- `eafw_clean_static` — collected static files

## Environments

### Local Development
- **URL**: http://127.0.0.1:9068
- **Working dir**: `~/IGAD-ICPAC/Projects/GHoA_Flood_watcher/eafw_geomanager_web/`
- **Config**: `.env` in `eafw_geomanager_web/`
- **Compose**: `docker-compose.yml` + `docker-compose.override.yml`

### Staging
- **URL**: http://floodwatch.icpac.net
- **Server**: 41.139.151.242 (SSH alias: `staging`)
- **SSH**: `ssh staging` (user: hkoros, key: ~/.ssh/eafw_staging_deploy)
- **Repo**: `~/flood_watch_system/eafw_geomanager_web/`
- **Config**: `.env` in `eafw_geomanager_web/`
- **DB creds**: eafw_user / eafw_db
- **Note**: CSRF_COOKIE_SECURE=False, SESSION_COOKIE_SECURE=False (HTTP, no HTTPS yet)
- **Note**: DNS goes through eadw-nginx (port 80) which proxies to eafw-nginx (port 9068). Do NOT modify eadw-nginx.

### Production
- **URL**: https://floodwatch.icpac.net (when HTTPS is configured)
- **Server**: Same as staging currently

## Common Operations

### Deploy to Staging

```bash
# 1. Push code
git add -A && git commit -m "description" && git push origin eafw

# 2. SSH and pull
ssh staging "cd ~/flood_watch_system && git pull origin eafw --ff-only"

# 3. Rebuild changed service
ssh staging "cd ~/flood_watch_system/eafw_geomanager_web && docker compose build geomanager_web"

# 4. Restart
ssh staging "cd ~/flood_watch_system/eafw_geomanager_web && docker compose up -d geomanager_web"
```

### Rebuild Specific Services

```bash
# CMS only (template/view changes)
docker compose build geomanager_web && docker compose up -d geomanager_web

# MapViewer (React component changes — slow, ~5 min)
# IMPORTANT: Next.js build cache can serve stale JS. If source changes don't appear
# in the deployed app, prune the build cache first:
#   docker builder prune -af
#   docker compose build --no-cache geomanager_mapviewer && docker compose up -d geomanager_mapviewer
# Normal rebuild (when cache is clean):
docker compose build geomanager_mapviewer && docker compose up -d geomanager_mapviewer

# MapServer/MapCache (nginx config changes)
docker compose build geomanager_mapserver geomanager_mapcache && docker compose up -d geomanager_mapserver geomanager_mapcache

# Jobs (sync script changes)
docker compose build geomanager_jobs && docker compose up -d geomanager_jobs
```

### Database Operations

```bash
# Local DB shell
docker exec eafw-pgdb psql -U geomanager -d geomanager_web

# Staging DB shell
ssh staging "docker exec eafw-pgdb psql -U eafw_user -d eafw_db"

# Backup local DB
docker exec eafw-pgdb pg_dump -U geomanager -Fc geomanager_web > backups/local_$(date +%Y%m%d).dump

# Backup staging DB
ssh staging "docker exec eafw-pgdb pg_dump -U eafw_user -Fc eafw_db > ~/eafw-backups/staging_$(date +%Y%m%d).dump"

# Restore to staging (from local dump)
scp backups/local_latest.dump staging:~/
ssh staging "docker exec -i eafw-pgdb pg_restore -U eafw_user -d eafw_db --no-owner --role=eafw_user < ~/local_latest.dump"

# Flush memcached (clear API cache)
docker exec eafw-memcached sh -c "echo 'flush_all' | nc localhost 11211"
```

### Category & Layer Management (DB)

Categories control the mapviewer sidebar. Current order:

| ID | Category | Order |
|----|----------|-------|
| 24 | Multimodal | 0 |
| 32 | GEOGloWS | 1 |
| 25 | Rainfall | 2 |
| 28 | Flash Floods | 3 |
| 23 | IBF | 4 |
| 22 | GADM Layers | 5 |

```sql
-- Add a category
INSERT INTO geomanager_category (id, created, modified, title, icon, active, public, "order")
VALUES (33, NOW(), NOW(), 'New Category', 'icon-name', true, true, 6);

-- Add subcategory
INSERT INTO geomanager_subcategory (id, title, active, public, category_id, sort_order)
VALUES (102, 'Sub Name', true, true, 33, 1);

-- Update vector tile layer URL
UPDATE geomanager_vectortilelayer SET base_url = 'new_url' WHERE id = 'uuid';

-- Always flush cache after DB changes
-- docker exec eafw-memcached sh -c "echo 'flush_all' | nc localhost 11211"
```

### Vector Tile Layer URLs

- **Local**: use absolute `http://127.0.0.1:9068/pg/tileserv/...`
- **Staging**: use absolute `http://floodwatch.icpac.net/pg/tileserv/...` or relative `/pg/tileserv/...`
- **Important**: The mapviewer web worker cannot resolve relative URLs. Always use absolute URLs for vector tile sources.

### Wagtail Site Configuration

```sql
-- Check current site config
SELECT hostname, port, site_name FROM wagtailcore_site;

-- Update for staging
UPDATE wagtailcore_site SET hostname='floodwatch.icpac.net', port=80 WHERE id=1;

-- Update for local
UPDATE wagtailcore_site SET hostname='127.0.0.1', port=9068 WHERE id=1;
```

## Data Sources & Sync Jobs

The jobs service (`eafw-jobs`) runs these scheduled syncs:

| Job | Schedule | Source | Description |
|-----|----------|--------|-------------|
| Multimodal | Daily 18:00 EAT | Google Drive / FTP | GeoSFM, FloodProofs, MIKE ensemble forecasts |
| FloodProofs | Every 6 hours | SFTP | Deterministic discharge forecasts |
| WRF Rainfall | Daily 06:00 EAT | FTP (KMD) | Weekly rainfall forecasts + COG export |
| Google Flood | Every 6 hours | Google API | River flood alerts via Flood Forecasting API |
| GEOGloWS | Daily 09:00 EAT | S3 Zarr | Global streamflow forecasts (148K GHA rivers) |
| GCS Inundation | Weekly Sunday 02:00 | Google Cloud Storage | Historical flood inundation tiles |
| DB Backup | Daily 18:30 EAT | Local | pg_dump to /backups/ |

### GEOGloWS Integration

- **River data**: 148,608 rivers in `gha.geoglows_rivers` table with geometries from TDX-Hydro
- **Return periods**: 2, 5, 10, 25, 50, 100-year thresholds from GEOGloWS retrospective analysis
- **Forecast source**: `s3://geoglows-v2-forecasts/YYYYMMDD00.zarr` (52 ensembles, 280 timesteps)
- **API proxy**: `/api/flood/geoglows-forecast/<river_id>` proxies to `geoglows.ecmwf.int` with DB return periods
- **Tileserv function**: `gha.geoglows_forecast_rivers()` serves rivers colored by alert level
- **Alert colors**: Blue(normal) → Yellow(2yr) → Orange(10yr) → Red(25yr) → Purple(50yr)

### Flash Floods (Nile Basin GeoServer)

- **FFPI/DFFPI** raster layers from `nilebasin-dss-data.azurewebsites.net/geoserver/`
- Proxied through nginx at `/nilebasin-geoserver/`

## Key Files

### Templates
- `eafw_geomanager_web/home/templates/home/home_page.html` — homepage (ticker, minimap, country panel)
- `eafw_geomanager_web/home/templates/partials/navbar.html` — navbar (includes all CSS/JS)
- `eafw_geomanager_web/mapwidget/templates/mapwidget/map_widget.html` — homepage minimap widget

### Django
- `eafw_geomanager_web/home/views.py` — API views (situation summary, forecast, GEOGloWS proxy)
- `eafw_geomanager_web/geomanagerweb/urls.py` — URL routing
- `eafw_geomanager_web/geomanagerweb/settings/production.py` — production settings
- `eafw_geomanager_web/home/models.py` — homepage model, navbar, footer

### MapViewer (Next.js)
- `eafw_geomapviewer/src/components/map/components/popup/components/data-table/component.jsx` — popup data table (detects multimodel/geoglows)
- `eafw_geomapviewer/src/components/map/components/popup/components/geoglows-chart/` — GEOGloWS forecast chart
- `eafw_geomapviewer/src/components/map/components/popup/components/multimodel-chart/` — Multimodel forecast chart

### Docker
- `eafw_geomanager_web/docker-compose.yml` — main compose file
- `eafw_geomanager_web/docker-compose.override.yml` — local overrides (volume mapping)
- `eafw_geomanager_web/docker/nginx/nginx.conf` — nginx config (proxy rules)
- `eafw_geomanager_web/docker/cms/Dockerfile` — CMS image
- `eafw_geomanager_web/docker/mapviewer/Dockerfile` — MapViewer image

### Jobs
- `eafw_geomanager_web/eafw_jobs/pyfloodwatch/scheduler.py` — job scheduler
- `eafw_geomanager_web/eafw_jobs/pyfloodwatch/geoglows_sync.py` — GEOGloWS forecast sync
- `eafw_geomanager_web/eafw_jobs/pyfloodwatch/database.py` — DB utilities

### CI/CD
- `.github/workflows/deploy-staging.yml` — builds images, deploys to staging on push to `eafw` branch

## Conventions

- **Non-alarmist language**: Use "Discharge Exceedance" instead of "Flood Alert", "High/Medium/Low" instead of "Extreme/Severe/Moderate"
- **Container naming**: `eafw-*` prefix (no `clean` suffix)
- **Git**: single repo, `eafw` branch for staging, `main` for production
- **Separate services**: keep eafw_jobs as separate container from CMS for fault isolation
- **Vector tile URLs**: always absolute (include host:port) — mapviewer web worker can't resolve relative URLs
- **No hardcoding**: Follow a modular structure throughout. Configuration comes from DB, environment variables, or API — never hardcode values (URLs, country lists, thresholds, etc.) directly in templates or components. Use Wagtail StreamFields, Django settings, or DB-driven config so changes can be made without code deploys

## Troubleshooting

### CMS won't start
```bash
docker logs eafw-cms 2>&1 | tail -20
# Common: missing migration → run migrations
# Common: log file handler → set CMS_LOG_FILE=/dev/null in .env
```

### MapServer/MapCache restarting
```bash
# Usually port 80 permission issue — ensure nginx.conf has "listen 8080"
docker logs eafw-mapserver 2>&1 | tail -5
```

### Staging CSRF 403 on login
```bash
# Ensure .env has:
# CSRF_COOKIE_SECURE=False
# SESSION_COOKIE_SECURE=False
# These must be in docker-compose environment section too
```

### Vector tiles not loading
```bash
# 1. Check tileserv sees the table/function
curl -s http://localhost:9068/pg/tileserv/index.json | python3 -c "import sys,json; [print(k) for k in json.load(sys.stdin)]"

# 2. Test a tile directly
curl -s -o /dev/null -w "%{http_code} %{size_download}b" "http://localhost:9068/pg/tileserv/gha.table_name/6/37/28.pbf"

# 3. Restart tileserv after adding new tables/functions
docker restart eafw-tileserv
```

### MapViewer source changes not appearing
```bash
# Next.js Docker build cache can serve stale JS bundles even after source edits.
# Verify: check if your change is in the deployed JS
docker exec eafw-mapviewer sh -c "grep -c 'yourSearchTerm' /home/app/.next/static/chunks/*.js"
# Fix: prune build cache and rebuild from scratch
docker builder prune -af
cd eafw_geomanager_web && docker compose build --no-cache geomanager_mapviewer && docker compose up -d geomanager_mapviewer
```

### Migrations conflict (column already exists)
```bash
# Fake the migration if the column exists but migration isn't recorded
docker exec eafw-cms /home/app/.venv/bin/python manage.py migrate app_name NNNN --fake
```
