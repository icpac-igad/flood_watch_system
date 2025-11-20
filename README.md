# FloodWatch - Early Warning System

Flood and drought early warning and anticipatory action system for Eastern Africa.

## Table of Contents
- [Services Overview](#services-overview)
- [Quick Start](#quick-start)
- [Building and Deploying](#building-and-deploying)
- [System Architecture](#system-architecture)
- [Development](#development)
- [API Endpoints](#api-endpoints)
- [Configuration](#configuration)
- [Data Management](#data-management)
- [Troubleshooting](#troubleshooting)

---

## Services Overview

FloodWatch runs 8 containerized services. Here's what each one does and how it's deployed:

| Service | Docker Image | Port(s) | Purpose | Build/Pull |
|---------|-------------|---------|---------|------------|
| **postgis** | `hkoros/floodwatch-postgis:1.1.0` | 8091 | PostgreSQL database with PostGIS and pgSTAC extensions | Pre-built - `docker pull` |
| **redis** | `hkoros/floodwatch-redis:1.1.0` | 9092 | Cache and Celery message broker | Pre-built - `docker pull` |
| **backend** | `hkoros/floodwatch-backend:1.1.0` | 8090 | Django REST API, admin panel, ORM | Built from `./backend` |
| **celery** | `hkoros/floodwatch-backend:1.1.0` | - | Background task worker (same image as backend) | Built from `./backend` |
| **celery-beat** | `hkoros/floodwatch-backend:1.1.0` | - | Scheduled task scheduler (same image as backend) | Built from `./backend` |
| **frontend** | `hkoros/floodwatch-frontend:1.1.0` | 8094 | React + Vite UI with Leaflet map (Nginx) | Built from `./frontend` |
| **fastapi** | `hkoros/floodwatch-fastapi:1.1.0` | 9050 | High-performance forecast data API | Built from `./fastapi-service` |
| **tipg** | `hkoros/floodwatch-tipg:1.1.0` | 8095 | Vector tile server for boundaries, rivers, lakes | Built from `./tipg-service` |

### Service Details

#### PostGIS Database
- **Container**: `floodwatch_pgstac`
- **Purpose**: Stores all spatial data, forecasts, stations, alerts
- **Extensions**: PostGIS, pgSTAC, pg_partman
- **Volumes**: `postgis_data` (persistent storage)
- **Health Check**: PostgreSQL ready check every 10s

#### Redis
- **Container**: `floodwatch_redis`
- **Purpose**: Caching layer and Celery message broker
- **Volumes**: `redis_data` (persistent storage)
- **Health Check**: Redis ping every 10s

#### Django Backend
- **Container**: `floodwatch_backend`
- **Purpose**: Main API server, admin interface, database ORM
- **Endpoints**: `/api/*`, `/admin/`
- **Dependencies**: PostGIS, Redis
- **Volumes**: `static_volume`, `media_volume`, `./backend/static_data`

#### Celery Worker
- **Container**: `floodwatch_celery`
- **Purpose**: Executes background tasks (data sync, processing)
- **Dependencies**: PostGIS, Redis, Backend
- **Shares Image**: Same as backend service

#### Celery Beat
- **Container**: `floodwatch_celery_beat`
- **Purpose**: Schedules periodic tasks (daily syncs, alerts)
- **Dependencies**: PostGIS, Redis, Backend
- **Shares Image**: Same as backend service

#### React Frontend
- **Container**: `floodwatch_frontend`
- **Purpose**: User interface with interactive map
- **Stack**: React, Vite, Leaflet, MUI
- **Server**: Nginx (production build)
- **Dependencies**: Backend

#### FastAPI Service
- **Container**: `floodwatch_fastapi`
- **Purpose**: Ultra-fast forecast data endpoints
- **Stack**: FastAPI, asyncpg (async PostgreSQL)
- **Endpoints**: `/api/fast/*`
- **Features**: Connection pooling, in-memory caching
- **Dependencies**: PostGIS

#### TiPg Vector Tiles
- **Container**: `floodwatch_tipg`
- **Purpose**: Serves vector tiles for boundaries, rivers, lakes
- **Replaces**: MapServer/MapCache (90% smaller, faster)
- **Format**: MVT (Mapbox Vector Tiles)
- **Optimizations**: 4096px resolution, 50k features/tile
- **Dependencies**: PostGIS

---

## Quick Start

### Prerequisites
- Docker & Docker Compose installed
- 8GB RAM minimum
- 20GB disk space

### 1. Clone and Configure

```bash
# Clone repository
git clone <repository-url>
cd floodwatch

# Create environment file
cp backend/.env.example .env

# Edit .env with your credentials
nano .env
```

### 2. Start All Services

```bash
# Pull and start all services
docker-compose up -d

# Check all services are running
docker-compose ps

# View logs
docker-compose logs -f
```

### 3. Access the System

| Service | URL | Credentials |
|---------|-----|-------------|
| **Frontend** | http://localhost:8094 | - |
| **Backend Admin** | http://localhost:8090/admin | admin / admin123 |
| **FastAPI Docs** | http://localhost:9050/docs | - |
| **TiPg Explorer** | http://localhost:8095 | - |

⚠️ **Change default credentials in production!**

---

## Building and Deploying

### Build and Push All Images

Use the automated build script to rebuild and push all custom images to Docker Hub:

```bash
# Build and push all images with version tags
./build_and_push.sh

# This will:
# 1. Build backend, frontend, fastapi, and tipg images
# 2. Tag with version from docker-compose.yml (1.1.0)
# 3. Push to hkoros Docker Hub repository
```

**Manual Build (single service):**
```bash
# Build backend
docker build -t hkoros/floodwatch-backend:1.1.0 ./backend
docker push hkoros/floodwatch-backend:1.1.0

# Build frontend
docker build -t hkoros/floodwatch-frontend:1.1.0 --target production ./frontend
docker push hkoros/floodwatch-frontend:1.1.0

# Build fastapi
docker build -t hkoros/floodwatch-fastapi:1.1.0 ./fastapi-service
docker push hkoros/floodwatch-fastapi:1.1.0

# Build tipg
docker build -t hkoros/floodwatch-tipg:1.1.0 ./tipg-service
docker push hkoros/floodwatch-tipg:1.1.0
```

### Deploy Updates

```bash
# Pull latest images
docker-compose pull

# Recreate containers with new images
docker-compose up -d

# Run database migrations
docker-compose exec backend python manage.py migrate
```

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                       FRONTEND (Nginx)                       │
│              React + Vite + Leaflet Map                      │
│                     Port 8094                                │
└────────────┬────────────────────────────┬───────────────────┘
             │                            │
             │                            │
    ┌────────▼────────┐          ┌───────▼────────┐
    │  Django Backend │          │    FastAPI     │
    │   REST API      │          │  Forecast Data │
    │   Port 8090     │          │   Port 9050    │
    └────────┬────────┘          └───────┬────────┘
             │                           │
             │    ┌──────────────────────┘
             │    │
    ┌────────▼────▼───────────────────────────────┐
    │          PostgreSQL + PostGIS                │
    │         Database (Port 8091)                 │
    │   • Forecast Data  • Stations  • Alerts     │
    └──────────────────────┬───────────────────────┘
                           │
                  ┌────────▼─────────┐
                  │   TiPg Service   │
                  │  Vector Tiles    │
                  │   Port 8095      │
                  └──────────────────┘

    Background Services:
    ┌──────────────┐  ┌────────────────┐  ┌───────────┐
    │Celery Worker │  │ Celery Beat    │  │   Redis   │
    │ (Tasks)      │  │ (Scheduler)    │  │  (Cache)  │
    └──────────────┘  └────────────────┘  └───────────┘
```

---

## Development

### Backend (Django)

```bash
# Enter backend container
docker-compose exec backend bash

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Run management commands
python manage.py sync_floodproofs_to_db
python manage.py sync_ensemble_from_ftp
```

**Key Files:**
- `flood_watch_system/settings.py` - Configuration
- `Impact/models.py` - Database models
- `Impact/views.py` - API endpoints
- `Impact/serializers.py` - Data serialization
- `Impact/tasks.py` - Celery background tasks
- `Impact/management/commands/` - Custom Django commands

### Frontend (React)

```bash
# Local development (outside Docker)
cd frontend
npm install
npm run dev  # Starts on http://localhost:5173

# Build for production
npm run build

# Inside Docker container
docker-compose exec frontend sh
```

**Key Files:**
- `src/main.tsx` - Entry point
- `src/components/pages/MapViewer.jsx` - Main map component
- `src/components/map/layers/` - Layer components
- `src/hooks/` - Data fetching hooks
- `src/config.ts` - API endpoints
- `src/config/endpoints.ts` - API endpoint definitions

### Database

**Connect to Database:**
```bash
# Using Docker
docker-compose exec postgis psql -U postgres -d floodwatch

# Direct connection
Host: localhost
Port: 8091
Database: floodwatch
User: postgres
Password: floodwatch_pass
```

**Key Tables:**
- `impact_mergeddeterministicgeojson` - Floodproofs forecast data
- `impact_ensemble_forecast_geojson` - Ensemble forecast data
- `impact_geosfmgeojson` - GeoSFM satellite data
- `pgstac.items` - STAC items (imagery metadata)
- `pgstac.admin0`, `admin1`, `admin2` - Administrative boundaries
- `pgstac.rivers` - River network
- `pgstac.waterbodies` - Lakes and water bodies

---

## API Endpoints

### Django REST API (Port 8090)

```bash
# Admin interface
http://localhost:8090/admin/

# API documentation (if DRF enabled)
http://localhost:8090/api/

# Forecast data
GET /api/forecast/
GET /api/forecast/{date}/

# Ensemble data
GET /api/ensemble/
```

### FastAPI (Port 9050)

```bash
# API documentation
http://localhost:9050/docs

# Health check
GET /health

# Merged deterministic forecasts
GET /api/fast/merged-forecast/dates/
GET /api/fast/merged-forecast/{date}/
GET /api/fast/merged-forecast/latest/

# Ensemble forecasts
GET /api/fast/ensemble-control-points
GET /api/fast/ensemble-forecast/{date}/
GET /api/fast/ensemble-forecast-dates/
```

### TiPg Vector Tiles (Port 8095)

```bash
# API explorer
http://localhost:8095

# Available collections
GET /collections

# Get tiles for rivers
GET /collections/rivers/tiles/{z}/{x}/{y}

# Get tiles for admin boundaries
GET /collections/admin0/tiles/{z}/{x}/{y}
GET /collections/admin1/tiles/{z}/{x}/{y}
GET /collections/admin2/tiles/{z}/{x}/{y}

# Get tiles for water bodies
GET /collections/waterbodies/tiles/{z}/{x}/{y}
```

---

## Configuration

### Environment Variables

Create `.env` in project root with:

```bash
# Database
DB_NAME=floodwatch
DB_USER=postgres
DB_PASSWORD=floodwatch_pass
DB_HOST=postgis
DB_PORT=5432

# Django
SECRET_KEY=your-secret-key-here-change-in-production
DEBUG=False
DJANGO_ALLOWED_HOSTS=localhost,your-domain.com

# SFTP (Floodproofs data)
SFTP_HOST=197.254.113.173
SFTP_PORT=22
SFTP_USERNAME=floodproofs
SFTP_PASSWORD=IcpaC#254

# FTP (Ensemble data)
FTP_HOST=41.215.21.156
FTP_PORT=21
FTP_USER=your-ftp-user
FTP_PASSWORD=your-ftp-password
FTP_REMOTE_DIR=output/Combined

# Google Cloud Storage (GeoSFM data)
GCS_PROJECT_ID=your-project-id
GCS_BUCKET_NAME=your-bucket
GCS_CREDENTIALS_JSON=path/to/credentials.json
GCS_GEOSFM_PREFIX=geosfm_output_icpac_pc/
```

---

## Data Management

### Sync Floodproofs Data (Deterministic Forecasts)

```bash
# Sync latest 30 days
docker-compose exec backend python manage.py sync_floodproofs_to_db

# Sync specific date
docker-compose exec backend python manage.py sync_floodproofs_to_db --date 2025-11-19

# Sync with force overwrite
docker-compose exec backend python manage.py sync_floodproofs_to_db --force
```

### Sync Ensemble Forecasts

```bash
# Sync all zones from FTP
docker-compose exec backend python manage.py sync_ensemble_from_ftp

# Sync specific zone
docker-compose exec backend python manage.py sync_ensemble_from_ftp --zone 1

# Limit number of files
docker-compose exec backend python manage.py sync_ensemble_from_ftp --limit 100

# Dry run (don't save to DB)
docker-compose exec backend python manage.py sync_ensemble_from_ftp --dry-run
```

### Load Static Data

```bash
# Load all static data (boundaries, rivers, lakes)
docker-compose exec backend python manage.py load_all_static_data

# Initialize database
docker-compose exec backend python manage.py init_db
```

### Backup and Restore

```bash
# Backup database
docker-compose exec postgis pg_dump -U postgres floodwatch > backup_$(date +%Y%m%d).sql

# Restore database
docker-compose exec -T postgis psql -U postgres floodwatch < backup_20251119.sql

# Backup specific table
docker-compose exec postgis pg_dump -U postgres -t impact_mergeddeterministicgeojson floodwatch > forecasts_backup.sql
```

---

## Troubleshooting

### Check Service Status

```bash
# List all running services
docker-compose ps

# View logs for all services
docker-compose logs -f

# View logs for specific service
docker-compose logs -f backend
docker-compose logs -f fastapi
docker-compose logs -f frontend
```

### Common Issues

#### Services won't start
```bash
# Check logs
docker-compose logs -f

# Restart specific service
docker-compose restart backend

# Restart all services
docker-compose restart
```

#### Database connection errors
```bash
# Check database is running
docker-compose ps postgis

# Test connection
docker-compose exec postgis psql -U postgres -d floodwatch -c "SELECT version();"

# Check database logs
docker-compose logs postgis
```

#### Frontend not loading
```bash
# Check nginx logs
docker-compose logs frontend

# Rebuild frontend
docker-compose up -d --build frontend

# Check if frontend container is healthy
docker-compose ps frontend
```

#### API returns no data
```bash
# Check FastAPI service
curl http://localhost:9050/health

# Check available dates
curl http://localhost:9050/api/fast/merged-forecast/dates/

# Restart FastAPI to clear cache
docker-compose restart fastapi
```

#### Vector tiles not loading
```bash
# Check TiPg service
curl http://localhost:8095/collections

# View TiPg logs
docker-compose logs tipg

# Restart TiPg
docker-compose restart tipg
```

---

## Support

For issues or questions:

1. **Check service logs**: `docker-compose logs -f [service]`
2. **Verify environment variables**: Check `.env` file exists and has correct values
3. **Ensure all services are healthy**: `docker-compose ps`
4. **Check database connectivity**: `docker-compose exec postgis psql -U postgres -d floodwatch`
5. **Review API responses**: Test endpoints with curl or browser
6. **Clear caches**: Restart FastAPI service to clear in-memory cache

---

## License

[Add your license here]
