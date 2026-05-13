# East Africa Flood Watch System (EAFW)

Flood monitoring and early warning platform for the **Greater Horn of Africa** — Ethiopia, Kenya, Uganda, Sudan, South Sudan, Tanzania, Rwanda, Burundi, Somalia, Djibouti, Eritrea (11 IGAD member states).

This repository is the **orchestration layer**: Docker compose, build pipelines, deploy scripts, infrastructure config. **No application source code lives here.** Each component is its own repository, cloned at build time and pinned via `docker-compose.yml` build args.

Production: <https://floodwatch.icpac.net>

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│   flood_watch_system  (this repo — pure orchestration)              │
│                                                                     │
│   docker-compose.yml ─── pins each component's repo + ref           │
│   docker/{cms,mapviewer,jobs,mapserver,mapcache}/Dockerfile         │
│   scripts/deploy.sh                                                 │
│   .github/workflows/deploy-staging.yml                              │
└─────────────────────────────────────────────────────────────────────┘
        │
        │  built at deploy time from these external repos:
        ▼
```

| # | Component | Repo | Role | Build-arg pin |
|---|---|---|---|---|
| 1 | **geomanager-web** | [`icpac-igad/geomanager-web`](https://github.com/icpac-igad/geomanager-web) | EAFW Wagtail/Django app orchestration (settings, urls, home, base, partners, contact, mapwidget) | `GEOMANAGER_WEB_REPO` + `GEOMANAGER_WEB_REF` |
| 2 | **geomanager** | [`icpac-igad/geomanager`](https://github.com/icpac-igad/geomanager) | GeoManager Django app — shared lib (also used by EAMW, drought watch) | `GEOMANAGER_REPO` + `GEOMANAGER_REF` |
| 3 | **georeport** | [`icpac-igad/georeport`](https://github.com/icpac-igad/georeport) | `hazard-georeport` Django package — bulletin & report workflows; shared lib | `GEOREPORT_REPO` + `GEOREPORT_REF` |
| 4 | **geomapviewer** | [`icpac-igad/geomapviewer`](https://github.com/icpac-igad/geomapviewer) | Next.js map viewer — shared lib | `GEOMAPVIEWER_REPO` + `GEOMAPVIEWER_REF` |
| 5 | **eafw_jobs** *(planned)* | `icpac-igad/eafw_jobs` | Scheduled data ingestion (WRF, Google Floods, FloodProofs, GEOGloWS, drive sync) | `EAFW_JOBS_REPO` + `EAFW_JOBS_REF` |
| 6 | **eafw_mapserver** *(planned)* | `icpac-igad/eafw_mapserver` | MapServer (WMS/WFS) + MapCache + database init (mapfiles, mapcache config, db-init SQL) | `EAFW_MAPSERVER_REPO` + `EAFW_MAPSERVER_REF` |

Components 5–6 currently still live as directories in this repo; they will be extracted to their own repos (modelled on [`mukau-jobs`](https://github.com/icpac-igad/mukau-jobs) and [`mukau-mapserver`](https://github.com/icpac-igad/mukau-mapserver)) in the next refactor pass.

### Why no submodules

The four upstream component repos are reused across multiple ICPAC products (EAMW, Kenya Drought Watch, climweb, …). Vendoring them in would either fork them per-product (drift) or break their cross-product reuse. Pinning by `repo + ref` in `docker-compose.yml` keeps versions explicit in a single YAML while letting each component evolve in its own repo.

### Runtime services

| Container | Image source | Purpose |
|---|---|---|
| `eafw-cms` | built from components 1–3 | Django/Wagtail CMS + APIs |
| `eafw-mapviewer` | built from component 4 | Next.js map UI |
| `eafw-jobs` | component 5 | Data sync scheduler |
| `eafw-mapserver` | component 6 | WMS/WFS raster rendering |
| `eafw-mapcache` | component 6 | Tile caching |
| `eafw-pgdb` | `postgis/postgis:16-3.4` | Database |
| `eafw-pgbouncer` | `edoburu/pgbouncer` | Connection pooler |
| `eafw-memcached` | `memcached:1.6-alpine` | Cache |
| `eafw-tileserv` | `pramsey/pg_tileserv` | Vector tiles |
| `eafw-nginx` | `nginx:1.27-alpine` | Reverse proxy |
| `eafw-caddy` | `caddy:2-alpine` | TLS termination |

---

## Deploying to staging

CI/CD runs on every push to `main` (`.github/workflows/deploy-staging.yml`):

1. Detects which components changed.
2. Builds the affected images on GitHub-hosted runners (Docker clones each upstream at the pinned ref).
3. Pushes images to `ghcr.io/icpac-igad/eafw-*`.
4. SSHes into staging, runs `scripts/deploy.sh <changed-services>` — pulls new images, runs migrations, restarts containers.

Manual deploy on the staging host:

```bash
ssh staging
cd ~/projects/flood_watch_system
git pull origin main --ff-only
./scripts/deploy.sh --full          # or: ./scripts/deploy.sh cms mapviewer
```

The DB is never recreated during deploy; a fresh `pg_dump` is taken to `~/data/backups/eafw/` before every run.

---

## Local development

Clone each component repo you'll be editing as a sibling of this one; the override file bind-mounts the source over the container's clone for hot-reload. Or skip that and let Docker clone fresh — fine if you're only running the platform, not editing components.

```bash
# 1. Clone the orchestration repo
git clone https://github.com/icpac-igad/flood_watch_system
cd flood_watch_system

# 2. (Optional) Clone any components you'll edit, as siblings
cd ..
git clone https://github.com/icpac-igad/geomanager-web
git clone https://github.com/icpac-igad/geomanager
git clone https://github.com/icpac-igad/georeport
git clone https://github.com/icpac-igad/geomapviewer
cd flood_watch_system

# 3. Set up environment
cp .env.example .env        # fill in GH_TOKEN, SECRET_KEY, …

# 4. Bring it up
./scripts/up.sh
# -> http://127.0.0.1:9068
```

### Scripts

| Script | Purpose |
|---|---|
| `scripts/deploy.sh` | Single deploy entry point (used by CI and on the staging host) |
| `scripts/up.sh` | Local: build (if needed) and start the stack |
| `scripts/down.sh` | Local: stop the stack (volumes preserved) |
| `scripts/reset.sh` | Local: nuke volumes + rebuild for a clean slate |

---

## Pinning component versions

Defaults in `docker-compose.yml` point at each component's `eafw` branch. Override in `.env`:

```env
# Pin to a branch or specific SHA for reproducible builds
GEOMANAGER_WEB_REF=eafw
GEOMANAGER_REF=eafw
GEOREPORT_REF=eafw
GEOMAPVIEWER_REF=eafw
```

---

## Repository layout

```
.
├── docker-compose.yml              # service definitions + component build-arg pins
├── docker-compose.override.yml     # local dev only (gitignored)
├── docker/                         # Dockerfiles, one per service
│   ├── cms/        — clones geomanager-web + geomanager + georeport
│   ├── mapviewer/  — clones geomapviewer
│   ├── jobs/       — (until eafw_jobs repo exists)
│   ├── mapserver/  — (until eafw_mapserver repo exists)
│   └── mapcache/   — (until eafw_mapserver repo exists)
├── scripts/                        # deploy + local lifecycle
├── config/                         # mapfiles, mapcache config (moves to eafw_mapserver)
├── db-init/                        # SQL bootstrap (moves to eafw_mapserver)
├── eafw_jobs/                      # jobs source (moves to eafw_jobs repo)
└── .github/workflows/              # CI/CD
```

---

## License

MIT — see `LICENSE`.

## Acknowledgements

Developed by [ICPAC](https://www.icpac.net) — the IGAD Climate Prediction & Applications Centre — with support from partners across the GHA region.
