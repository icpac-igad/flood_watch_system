# Services Reference

## Docker Compose Services

All services are defined in `docker-compose.yml` (local) and `docker-compose.staging.yml` (staging).

### Service Names and Ports

| Service | Container Name | Internal Port | External Port |
|---------|---------------|---------------|---------------|
| `eafw_pgdb` | `eafw-pgdb` | 5432 | 5432 |
| `eafw_pgbouncer` | `eafw-pgbouncer` | 6432 | 6432 |
| `eafw_cms` | `eafw-cms` | 8000 | - |
| `eafw_api` | `eafw-api` | 8000 | 9069 |
| `eafw_mapviewer` | `eafw-mapviewer` | 3000 | - |
| `eafw_mapserver` | `eafw-mapserver` | 80 | 9065 |
| `eafw_mapcache` | `eafw-mapcache` | 80 | 9066 |
| `eafw_tileserv` | `eafw-tileserv` | 7800 | 9067 |
| `eafw_nginx` | `eafw-nginx` | 80 | 9068 |
| `eafw_jobs` | `eafw-jobs` | - | - |

!!! note
    Service names use **underscores** (`eafw_mapviewer`), container names use **dashes** (`eafw-mapviewer`).

### Nginx Routing

Nginx (`eafw_nginx`) acts as the main gateway at port 9068:

| Path | Backend |
|------|---------|
| `/` | Map Viewer |
| `/api/` | FastAPI |
| `/cms-admin/` | CMS Admin |
| `/mapserver/` | MapServer |
| `/mapcache/` | MapCache |
| `/pg/tileserv/` | pg_tileserv |

## Database Schema

The PostgreSQL database uses two main schemas:

- **`gha`**: Spatial data (control points, forecasts, admin boundaries, flood extents)
- **`cms`**: CMS tables (Wagtail pages, geomanager layers, datasets)

### Key Tables

| Schema | Table | Description |
|--------|-------|-------------|
| `gha` | `multimodal_control_points` | ~3,199 river monitoring points |
| `gha` | `multimodal_forecast` | ~5.6M forecast rows |
| `gha` | `admin0`, `admin1`, `admin2` | Administrative boundaries |
| `cms` | `geomanager_*` | Layer definitions, styles, datasets |

### Alert Thresholds

Consistent across all components:

| Level | Threshold |
|-------|-----------|
| Warning | >= 300 m³/s |
| Alarm | >= 500 m³/s |
| Emergency | >= 750 m³/s |
