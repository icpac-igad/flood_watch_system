# East Africa Flood Watch System

A comprehensive flood monitoring and early warning system for the Greater Horn of Africa region, built on the [GeoManager](https://github.com/icpac-igad/geomanager) platform.

## Architecture

The system is composed of three core components, each maintained as a separate upstream project:

| Component | Directory | Upstream |
|---|---|---|
| **GeoManager Web** | `eafw_geomanager_web/` | [geomanager-web](https://github.com/icpac-igad/geomanager-web) |
| **GeoManager** | `eafw_geomanager/` | [geomanager](https://github.com/icpac-igad/geomanager) |
| **GeoMapViewer** | `eafw_geomapviewer/` | [geomapviewer](https://github.com/icpac-igad/geomapviewer) |

### Services

| Service | Description | Port |
|---|---|---|
| **eafw-nginx** | Reverse proxy (entry point) | 9068 |
| **eafw-cms** | Django/Wagtail CMS + GeoManager | 8000 (internal) |
| **eafw-mapviewer** | Next.js map viewer | 3000 (internal) |
| **eafw-pgdb** | PostGIS database | 5431 |
| **eafw-pgbouncer** | Connection pooler | 6432 (internal) |
| **eafw-memcached** | Cache layer | 11211 (internal) |
| **eafw-mapserver** | WMS/WFS raster rendering | 80 (internal) |
| **eafw-mapcache** | Tile caching | 80 (internal) |
| **eafw-tileserv** | pg_tileserv vector tiles | 7800 (internal) |
| **eafw-jobs** | Data sync (WRF, Google Floods, FloodProofs) | - |

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Git

### Local Development

```bash
# Clone
git clone https://github.com/icpac-igad/flood_watch_system.git
cd flood_watch_system/eafw_geomanager_web

# Configure
cp ../.env.example .env
# Edit .env with your settings

# Build and start
docker compose up -d --build

# Access at http://127.0.0.1:9068
```

### Staging Deployment

Push to the `eafw` branch triggers automatic CI/CD:
1. Detects which components changed
2. Builds Docker images and pushes to GHCR
3. Deploys to staging server via SSH

## Data Sources

- **WRF Rainfall** — Weekly rainfall forecasts from KMD
- **Google Flood Forecasting** — River flood alerts via Google API
- **FloodProofs** — Deterministic discharge forecasts
- **Flash Floods** — FFPI/DFFPI from Nile Basin GeoServer
- **Admin Boundaries** — GADM administrative boundaries
- **Rivers** — HydroSHEDS river network
- **Lakes** — Water bodies dataset

## License

See [LICENSE](LICENSE) for details.
