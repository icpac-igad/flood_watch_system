# East Africa Flood Watch System — Operational Guide

## Project Overview

The East Africa Flood Watch (EAFW) is a flood monitoring and early warning system for the Greater Horn of Africa (GHA), covering 11 IGAD member states: Ethiopia, Kenya, Uganda, Sudan, South Sudan, Tanzania, Rwanda, Burundi, Somalia, Djibouti, Eritrea.

## Architecture — pure orchestration parent + 4 external component repos

`flood_watch_system` is **pure Docker/infra orchestration**. No source code from upstream components lives here. The four upstream repos are pinned by `repo + ref` build args in `docker-compose.yml`, and the Dockerfiles `git clone` them at build time.

```
flood_watch_system/                  ← THIS REPO — orchestration only
├── docker-compose.yml               ← pins upstream repo+ref per service (build args)
├── docker-compose.override.yml      ← local dev only (gitignored)
├── docker/
│   ├── cms/Dockerfile               ← clones geomanager-web + uses pyproject sed-rewrite to pin geomanager + georeport
│   ├── mapviewer/Dockerfile         ← clones geomapviewer
│   ├── jobs/Dockerfile              ← uses eafw_jobs/ (will move to its own repo: eafw_jobs)
│   ├── mapserver/Dockerfile         ← (will move to its own repo: eafw_mapserver, also housing db-init)
│   └── mapcache/Dockerfile
├── scripts/                         ← deploy.sh, up.sh, down.sh, reset.sh
├── config/                          ← mapfiles, mapcache config (moves to eafw_mapserver later)
├── db-init/                         ← SQL bootstrap (moves to eafw_mapserver later)
├── eafw_jobs/                       ← jobs source code (moves to its own repo later)
├── .github/workflows/deploy-staging.yml
└── CLAUDE.md, README.md
```

### Upstream component repos (external, cloned at build time)

| Repo | Purpose | Build-arg pin |
|---|---|---|
| [`icpac-igad/geomanager-web`](https://github.com/icpac-igad/geomanager-web) | Wagtail/Django app orchestration — EAFW-specific glue (settings, urls, home/, base/, partners/, contact/, mapwidget/) | `GEOMANAGER_WEB_REPO` + `GEOMANAGER_WEB_REF` |
| [`icpac-igad/geomanager`](https://github.com/icpac-igad/geomanager) | GeoManager Django app — shared lib (also used by EAMW, drought watch) | `GEOMANAGER_REPO` + `GEOMANAGER_REF` |
| [`icpac-igad/georeport`](https://github.com/icpac-igad/georeport) | `hazard-georeport` Django package — shared lib | `GEOREPORT_REPO` + `GEOREPORT_REF` |
| [`icpac-igad/geomapviewer`](https://github.com/icpac-igad/geomapviewer) | Next.js map viewer — shared lib | `GEOMAPVIEWER_REPO` + `GEOMAPVIEWER_REF` |

### To-be-created repos (Phase 2)

| Future repo | Source today | Pattern reference |
|---|---|---|
| `eafw_jobs` | `eafw_jobs/` directory | TBD |
| `eafw_mapserver` | `docker/mapserver/`, `docker/mapcache/`, `config/mapfiles/`, `db-init/` | [`icpac-igad/mukau-mapserver`](https://github.com/icpac-igad/mukau-mapserver) |

### Why the shared libs are NOT vendored in

`geomanager-web`, `geomanager`, `georeport`, `geomapviewer` are **shared across ICPAC products** (EAFW, EAMW, kenya-drought-watch, climweb). Each product has its own branch in each repo and its own orchestration parent. Don't try to monorepo — it would break the other products.

### Services (Docker Compose)

All services run from the **parent** `docker-compose.yml` (root of `flood_watch_system/`), NOT from `eafw_geomanager_web/docker-compose.yml` (that one is the upstream's standalone-dev file — ignored here):

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
- **Working dir**: `~/IGAD-ICPAC/Projects/Systems/flood_watch_system/` (the parent, NOT inside `eafw_geomanager_web/`)
- **Config**: `.env` at the parent root
- **Compose**: `./docker-compose.yml` + `./docker-compose.override.yml`

### Staging
- **URL**: http://floodwatch.icpac.net
- **Server**: 41.139.151.242 (SSH alias: `staging`)
- **SSH**: `ssh staging` (user: hkoros, key: ~/.ssh/eafw_staging_deploy)
- **Working dir**: `~/projects/flood_watch_system/` (parent root). The `~/flood_watch_system` symlink also points here for backwards compat.
- **Compose file**: `~/projects/flood_watch_system/docker-compose.yml` (root). The `eafw_geomanager_web/docker-compose.yml` inside the submodule is unused — ignore it.
- **Config**: `.env` at `~/projects/flood_watch_system/.env`
- **DB creds**: eafw_user / eafw_db
- **DB backups**: `~/data/backups/eafw/` (auto pg_dump before every deploy)
- **Note**: CSRF_COOKIE_SECURE=False, SESSION_COOKIE_SECURE=False (HTTP, no HTTPS yet)
- **Note**: DNS goes through eadw-nginx (port 80) which proxies to eafw-nginx (port 9068). Do NOT modify eadw-nginx.
- **Note**: Caddy fronts the eafw stack at 443; staging is currently HTTP only externally.

### Production
- **URL**: https://floodwatch.icpac.net (when HTTPS is configured)
- **Server**: Same as staging currently

## Common Operations

### Deploy to Staging

**Automatic (CI)**: Push to `eafw` branch — GitHub Actions builds changed images, SSHs into staging, runs `scripts/deploy.sh --full`. DB is never touched.

**Manual (SSH)**:
```bash
ssh staging
cd ~/projects/flood_watch_system && git pull origin eafw --ff-only
git submodule update --init --recursive --force

# Deploy all app services (DB stays untouched)
./scripts/deploy.sh --full

# Deploy specific service only
./scripts/deploy.sh cms
./scripts/deploy.sh mapviewer
./scripts/deploy.sh mapserver jobs

# First-time setup (initializes DB from db-init/ scripts)
./scripts/deploy.sh --init
```

### Key Deployment Rules

1. **DB is never recreated during deploy** — `scripts/deploy.sh` only restarts app containers
2. **Auto-backup** — DB is dumped to `~/data/backups/eafw/` before every deploy
3. **Volume names are pinned** — `eafw_pgdata`, `eafw_media`, etc. are stable regardless of clone directory
4. **COMPOSE_PROJECT_NAME=eafw** — must be in `.env` for consistent container/network naming
5. **Never use `docker compose down`** on staging — use `docker compose stop <service>` or the deploy script
6. **Never `docker rm -f` the DB container** — this is the #1 cause of data loss
7. **One deploy entry point**: `scripts/deploy.sh`. There is no `deploy-staging.sh` anymore (removed 2026-05-12 — legacy that pointed at the old `eafw_geomanager_web/` compose path)

### Rebuild Specific Services

```bash
# CMS only (template/view changes)
./scripts/deploy.sh cms

# MapViewer (React component changes — slow, ~5 min)
# IMPORTANT: Next.js build cache can serve stale JS. If source changes don't appear:
#   docker builder prune -af
#   docker compose build --no-cache geomanager_mapviewer
#   ./scripts/deploy.sh mapviewer

# MapServer + MapCache
./scripts/deploy.sh mapserver mapcache

# Jobs (sync script changes)
./scripts/deploy.sh jobs
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
- **Submodules are deliberate, keep them**: `eafw_geomanager`, `eafw_georeport`, `eafw_geomapviewer` are shared across ICPAC products. Code changes there → commit to submodule first → bump submodule pointer in parent. `eafw_geomanager_web` is the EAFW-specific Wagtail glue (also a submodule, but only EAFW uses its `eafw` branch).
- **Compose files**: only the parent's `docker-compose.yml` (root) is real. The `docker-compose.yml` inside each submodule is an upstream artifact for standalone-dev users of that lib — ignore it on EAFW.

## Pending — CI/CD simplification ("Path X")

Single coherent PR to land. The pipeline works but bites us on every CMS deploy: `--no-cache` rebuilds (~15 min) and unreliable ghcr.io pulls on the staging host (we've seen blob-server stalls > 20 min on specific layers; deploy.sh silently warns and uses the old image, masking the failure).

Decided architecture (do NOT change): keep all 4 submodules. `eafw_geomanager_web` is the Wagtail orchestration layer; `geomanager` / `georeport` / `geomapviewer` are shared libs across ICPAC products. Don't monorepo.

| # | Change | File | Why |
|---|---|---|---|
| 1 | Rewrite CMS `Dockerfile` to use build-context model (mirror `Dockerfile.local`): `COPY eafw_geomanager_web/`, `COPY eafw_georeport/`, `COPY eafw_geomanager/`. Drop the in-Dockerfile `git clone` and the `GH_PAT` build-arg. Submodule pointer becomes authoritative (today it's silently ignored — correctness bug). | `docker/cms/Dockerfile` | Removes the in-build network fetch, restores layer cache, makes submodule SHA actually matter |
| 2 | `build-cms` job: drop `no-cache: true` + `CACHEBUST`; add `submodules: recursive` to its checkout | `.github/workflows/deploy-staging.yml` | CMS builds drop from ~15 min → ~3 min for incremental edits |
| 3 | `scripts/deploy.sh`: fail-fast on pull failure (today it `warn`s + uses existing image → silent stale deploys). At tail: memcached `flush_all` + `curl -fsS http://floodwatch.icpac.net/` health check. | `scripts/deploy.sh` | No more silent stale deploys; manual flush goes away |
| 4 | Add `scripts/deploy.sh --fast <service>` mode: `git pull --recurse-submodules` → docker cp source into container → migrate → restart → flush → curl. No ghcr.io. | `scripts/deploy.sh` | Source-only changes deploy in <60 s, sidesteps the ghcr.io stall entirely. Validated manually 2026-05-12 (bulletin + i18n deploy). |
| 5 | Replace 11 `sed -i` secret injections with one `envsubst` from a `.env.template` (or single Python one-liner) | `.github/workflows/deploy-staging.yml` | One less way to silently corrupt `.env` |
| 6 | Strengthen prune at end of `scripts/deploy.sh`: `docker image prune -af --filter "until=720h"` + `find ~/data/backups/eafw -name 'pre_deploy_*.dump' -mtime +30 -delete` | `scripts/deploy.sh` | Disk doesn't drift |

Out of scope for this PR (defer): self-hosted runner, Kamal migration, touching mapviewer/mapserver/mapcache/jobs Dockerfiles, removing `GH_PAT` entirely (still needed for repo clone in `appleboy/ssh-action` step), build-on-staging.

### Things NOT to do
- Don't vendor submodules into the parent ("merge the monorepo"). The shared libs are used by other ICPAC products (drought watch, climweb). Keep them as submodules.
- Don't touch each submodule's own `Dockerfile` / `docker-compose.yml` — those are for upstream standalone-dev users.
- Don't build CMS on staging — only ~600 MB RAM free, 84 % swap used. Would OOM. (mapserver/mapcache/mapviewer would be fine; CMS/jobs are not.)

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

## Restoration Log

### 2026-05-11 — Restored from Debian backup
The project was missing from this machine and was restored from the Debian backup on the portable SSD.

- **Source**: `/media/koros/PortableSSD/backup-debian-2026-05-05/IGAD_ICPAC-2026-05-05.tar` (49 GB, taken 2026-05-05 17:32)
- **Restored to**: `/home/koros/IGAD-ICPAC/Projects/Systems/flood_watch_system/` (20 GB on disk, 71,883 files)
- **Command used**:
  ```bash
  tar -xf /media/koros/PortableSSD/backup-debian-2026-05-05/IGAD_ICPAC-2026-05-05.tar \
    -C /home/koros/IGAD-ICPAC/Projects/Systems \
    --strip-components=2 \
    IGAD_ICPAC/Projects/flood_watch_system
  ```

**Note on working dir**: the path referenced earlier in this doc (`~/IGAD-ICPAC/Projects/GHoA_Flood_watcher/eafw_geomanager_web/`) is stale. Current working dir is `~/IGAD-ICPAC/Projects/Systems/flood_watch_system/`.

#### Verification (post-extract)
- 125 secret/`.env`/credential paths — all match the tar listing
- Top-level `.env` (2183 B), `.env.example` (3211 B), `.env.bak.20260421_1154` (2116 B) — present
- `WHCA_CREDENTIALS.md`, `FW_ DELAYED TLS CERTS.zip` — present
- All 5 `.git` directories intact (root + 4 submodules: geomanager, geomanager_web, geomapviewer, georeport)
- All submodules on branch `eafw` tracking `origin/eafw`
- Pre-backup uncommitted edits preserved as-is:
  - `eafw_geomanager_web`: `M geomanagerweb/settings/base.py`
  - `eafw_georeport`: `M georeport/dashboard/models.py`
  - `eafw_geomapviewer`: untracked `src/projects/`

#### HEADs at restore time
| Repo | Commit | Subject |
|---|---|---|
| flood_watch_system | `f2b03ca` | chore: bump eafw_geomapviewer — welcome-modal storage key versioning |
| eafw_geomanager | `7db7498` | legend: pass icon URL from raw legend JSON through vector-tile serializer |
| eafw_geomanager_web | `bf7e3cb` | perf: tile function 100× faster + correct freshness rule |
| eafw_geomapviewer | `0ab2c7a` | fix(welcome-modal): version localStorage key so content updates re-show modal |
| eafw_georeport | `f43ca5a` | assessment: Regional Advisory Report title, rolling Thu validity, CAP 4-tier severity, map-only layout |
