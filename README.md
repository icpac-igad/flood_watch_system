# GHoA Flood Watcher (EAFW)

Operational codebase for the Greater Horn of Africa FloodWatch platform.

This repository runs a containerized geospatial early warning stack made of:
- CMS (`eafw_cms`) for content and geodata management (GeoManager/Wagtail)
- API (`eafw_api`) for public and internal flood data endpoints
- Jobs (`eafw_jobs`) for scheduled ingestion/sync from FTP, SFTP, Drive, and WRF sources
- Map services (`eafw_mapserver`, `eafw_mapcache`, `pg_tileserv`) and UI (`eafw_mapviewer`)

## Current stack and compose files

Use these compose files:
- `docker-compose.yml`: local development and integration testing
- `docker-compose.staging.yml`: staging deployment

## Quick start (local)

### 1. Prerequisites

- Docker Engine + Docker Compose plugin (`docker compose`)
- At least 8 GB RAM (16 GB recommended)
- 20+ GB free disk

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and set at minimum:
- `CMS_DB_PASSWORD`
- `SECRET_KEY`
- `FLOODPROOFS_SFTP_*` credentials
- `ENSEMBLE_FTP_*` credentials
- `WRF_FTP_*` credentials

If using Drive sync:
- put Google service account credentials at `eafw_jobs/credentials/google-credentials.json`
- set `DRIVE_FOLDER_ID`

### 3. Start services

```bash
docker compose up --build -d
```

### 4. Verify

```bash
docker compose ps
curl -f http://127.0.0.1:9068/health
curl -f http://127.0.0.1:9069/health
```

## Service endpoints (local defaults)

| Service | URL | Notes |
|---|---|---|
| Nginx entrypoint | `http://127.0.0.1:9068` | Main public gateway |
| CMS admin | `http://127.0.0.1:9068/cms-admin` | Path controlled by `ADMIN_URL_PATH` |
| FastAPI docs (via nginx) | `http://127.0.0.1:9068/api/docs` | Preferred public docs route |
| FastAPI direct | `http://127.0.0.1:9069/api/docs` | Container direct exposure |
| MapServer | `http://127.0.0.1:9065/mapserver/` | Direct mapserver endpoint |
| MapCache | `http://127.0.0.1:9066/mapcache/` | Direct mapcache endpoint |
| pg_tileserv | `http://127.0.0.1:9067/pg/tileserv/` | Direct tiles endpoint |

## Common operations

### Logs

```bash
docker compose logs -f
docker compose logs -f eafw_cms
docker compose logs -f eafw_api
docker compose logs -f eafw_jobs
```

### Stop / restart

```bash
docker compose down
docker compose restart eafw_cms eafw_api eafw_jobs
```

### Django admin and migrations

```bash
docker compose exec eafw_cms python manage.py migrate
docker compose exec eafw_cms python manage.py createsuperuser
```

### Run jobs manually (inside jobs container)

```bash
docker compose exec eafw_jobs python -m pyfloodwatch.floodproofs_sync
docker compose exec eafw_jobs python -m pyfloodwatch.ensemble_sync
docker compose exec eafw_jobs python -m pyfloodwatch.wrf_rainfall_job
```

### Database backup / restore helpers

```bash
# Backup (writes into ./backups and container /backups volume)
./scripts/db-dump.sh local

# Restore
./scripts/db-load.sh backups/<dump-file>.dump
```

## Repository layout

- `eafw_cms/`: CMS application and GeoManager package
- `eafw_api/`: FastAPI service
- `eafw_jobs/`: scheduled ingestion/sync jobs
- `eafw_docker/`: Dockerfiles, init SQL, nginx config
- `eafw_mapserver/`: MapServer resources
- `eafw_mapviewer/`: frontend map viewer
- `scripts/`: operational scripts (backup/restore, fixes, utilities)
- `docs/`: architecture and reference documentation

Note on naming:
- `eafw_jobs/` = jobs source code
- `eafw-jobs/` = runtime data/log directory kept for uniform naming

## Troubleshooting

### CMS login loop on staging

Run:

```bash
bash scripts/fix-staging-cms-login.sh
```

### Jobs failing due credentials

- confirm `.env` has valid `FLOODPROOFS_SFTP_*`, `ENSEMBLE_FTP_*`, and `WRF_FTP_*`
- if `SYNC_SOURCE=drive`, verify `DRIVE_FOLDER_ID` and credential file path

### API reachable directly but not through nginx

Check nginx routing and API container health:

```bash
docker compose logs -f eafw_nginx eafw_api
```

## Documentation

- `docs/API_DOCUMENTATION.md`
- `docs/FLOODWATCH_API_DOCUMENTATION.md`
- `docs/SIMPLIFIED_FRONTEND_ARCHITECTURE.md`
- `docs/STAGING_DEPLOYMENT.md` (legacy notes may exist; validate against current compose files)

## Security notes

- Never commit `.env` with real credentials.
- Rotate any secret if it was previously exposed.
- Use strong unique values for `SECRET_KEY` and external credential fields.
