# FloodWatch System

**Greater Horn of Africa Flood Early Warning System**

The FloodWatch System is an operational platform for flood early warning across the Greater Horn of Africa, developed by [ICPAC](https://www.icpac.net/).

## System Components

| Component | Description |
|-----------|-------------|
| **CMS** (`eafw_cms`) | Content and geodata management (GeoManager/Wagtail) |
| **API** (`eafw_api`) | Public and internal flood data endpoints (FastAPI) |
| **Jobs** (`eafw_jobs`) | Scheduled ingestion/sync from FTP, SFTP, Drive, and WRF sources |
| **Map Services** | MapServer, MapCache, pg_tileserv for raster/vector tiles |
| **Map Viewer** (`eafw_mapviewer`) | Next.js frontend for interactive flood maps |
| **Geomanager** | Wagtail-based geospatial data manager package |

## Service Endpoints (Local)

| Service | URL | Notes |
|---------|-----|-------|
| Nginx entrypoint | `http://127.0.0.1:9068` | Main public gateway |
| CMS admin | `http://127.0.0.1:9068/cms-admin` | Wagtail admin |
| FastAPI docs | `http://127.0.0.1:9068/api/docs` | Swagger UI |
| FastAPI ReDoc | `http://127.0.0.1:9068/api/redoc` | ReDoc UI |
| MapServer | `http://127.0.0.1:9065/mapserver/` | Direct MapServer |
| MapCache | `http://127.0.0.1:9066/mapcache/` | Direct MapCache |
| pg_tileserv | `http://127.0.0.1:9067/pg/tileserv/` | Vector tiles |

## Maintainer

Made with love and enthusiasm by:

- **Hillary Koros** — [hkoros@icpac.net](mailto:hkoros@icpac.net) / [hillary.koros@igad.int](mailto:hillary.koros@igad.int)

## Repository Layout

```
flood_watch_system/
├── eafw_cms/        # CMS application and GeoManager package
├── eafw_api/        # FastAPI service
├── eafw_jobs/       # Scheduled ingestion/sync jobs
├── eafw_docker/     # Dockerfiles, init SQL, nginx config
├── eafw_mapserver/  # MapServer resources
├── eafw_mapviewer/  # Frontend map viewer (Next.js)
├── scripts/         # Operational scripts
└── docs/            # Documentation
```
