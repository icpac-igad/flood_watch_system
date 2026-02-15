# System Overview

The FloodWatch platform is a containerized geospatial early warning stack composed of several microservices orchestrated via Docker Compose.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────┐
│                    Nginx (9068)                       │
│               Reverse Proxy / Gateway                 │
├──────┬──────┬──────┬───────┬──────────┬──────────────┤
│      │      │      │       │          │              │
▼      ▼      ▼      ▼       ▼          ▼              ▼
CMS   API   Map    Map    Map       pg_tile         Map
8000  8000  Viewer Server  Cache     serv           Viewer
             3000  (WMS)   (tiles)   7800            (SSR)
│      │                                │
▼      ▼                                ▼
PgBouncer (6432) ──────────────────► PostgreSQL/PostGIS
                                      (5432)
```

## Service Details

### CMS (`eafw_cms`)
- **Framework**: Django + Wagtail CMS
- **Package**: GeoManager - Wagtail-based geospatial data manager
- **Responsibilities**: Content management, geodata administration, layer configuration, WMS dataset sync
- **Port**: 8000 (internal)

### API (`eafw_api`)
- **Framework**: FastAPI
- **Responsibilities**: Public flood data endpoints, regional summaries, timeseries charts, risk assessments
- **Docs**: Auto-generated Swagger at `/api/docs`, ReDoc at `/api/redoc`
- **Port**: 8000 (internal), exposed at 9069

### Map Viewer (`eafw_mapviewer`)
- **Framework**: Next.js (Pages Router)
- **Responsibilities**: Interactive flood map, layer controls, flood analysis, basemap switching
- **Port**: 3000 (internal)

### Jobs (`eafw_jobs`)
- **Responsibilities**: Scheduled data ingestion from FTP/SFTP/Drive/WRF sources
- **Runs**: Cron-scheduled sync tasks

### Map Services
- **MapServer**: WMS/WCS raster tile serving
- **MapCache**: Tile caching layer
- **pg_tileserv**: Vector tile serving from PostGIS (clustering, control points)

### Database
- **PostgreSQL/PostGIS**: Spatial database with schemas `gha` (spatial data) and `cms` (CMS tables)
- **PgBouncer**: Connection pooling

## Data Flow

1. **Ingestion**: Jobs service pulls data from external FTP/SFTP/Drive sources
2. **Storage**: Raster data stored as COGs, vector data in PostGIS tables
3. **Management**: CMS provides admin interface for layer configuration
4. **Serving**: Map services render tiles on demand (raster via MapServer, vector via pg_tileserv)
5. **API**: FastAPI serves processed data (summaries, charts, GeoJSON)
6. **Visualization**: Map Viewer consumes tiles and API data for the user interface
