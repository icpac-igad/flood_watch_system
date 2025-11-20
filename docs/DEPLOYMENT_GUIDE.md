# FloodWatch Deployment Guide

Complete guide for deploying and managing the FloodWatch system.

## Table of Contents
- [Services Overview](#services-overview)
- [Building Docker Images](#building-docker-images)
- [Configuration](#configuration)
- [Data Management](#data-management)
- [Troubleshooting](#troubleshooting)

---

## Services Overview

FloodWatch runs 8 containerized services:

| Service | Docker Image | Port(s) | Purpose | Build/Pull |
|---------|-------------|---------|---------|------------|
| **postgis** | `hkoros/floodwatch-postgis:1.1.0` | 8091 | PostgreSQL database with PostGIS and pgSTAC | Pre-built |
| **redis** | `hkoros/floodwatch-redis:1.1.0` | 9092 | Cache and Celery message broker | Pre-built |
| **backend** | `hkoros/floodwatch-backend:1.1.0` | 8090 | Django REST API, admin panel, ORM | Built from `./backend` |
| **celery** | `hkoros/floodwatch-backend:1.1.0` | - | Background task worker | Built from `./backend` |
| **celery-beat** | `hkoros/floodwatch-backend:1.1.0` | - | Scheduled task scheduler | Built from `./backend` |
| **frontend** | `hkoros/floodwatch-frontend:1.1.0` | 8094 | React + Vite UI (Nginx) | Built from `./frontend` |
| **fastapi** | `hkoros/floodwatch-fastapi:1.1.0` | 9050 | High-performance forecast API | Built from `./fastapi-service` |
| **tipg** | `hkoros/floodwatch-tipg:1.1.0` | 8095 | Vector tile server | Built from `./tipg-service` |

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

## Building Docker Images

### Automated Build and Push

Use the build script to build and push all custom images:

```bash
./build_and_push.sh
```

This will:
1. Build backend, frontend, fastapi, and tipg images
2. Tag with version from docker-compose.yml (1.1.0)
3. Push to Docker Hub repository

### Manual Build

Build individual services:

```bash
# Backend
docker build -t hkoros/floodwatch-backend:1.1.0 ./backend
docker push hkoros/floodwatch-backend:1.1.0

# Frontend
docker build -t hkoros/floodwatch-frontend:1.1.0 --target production ./frontend
docker push hkoros/floodwatch-frontend:1.1.0

# FastAPI
docker build -t hkoros/floodwatch-fastapi:1.1.0 ./fastapi-service
docker push hkoros/floodwatch-fastapi:1.1.0

# TiPg
docker build -t hkoros/floodwatch-tipg:1.1.0 ./tipg-service
docker push hkoros/floodwatch-tipg:1.1.0
```

### Deploy Updates

```bash
# Pull latest images
docker-compose pull

# Recreate containers
docker-compose up -d

# Run migrations
docker-compose exec backend python manage.py migrate
```

---

## Configuration

### Environment Variables

Create `.env` in project root:

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

### Sync Floodproofs Data

```bash
# Sync latest 30 days
docker-compose exec backend python manage.py sync_floodproofs_to_db

# Sync specific date
docker-compose exec backend python manage.py sync_floodproofs_to_db --date 2025-11-19

# Force overwrite
docker-compose exec backend python manage.py sync_floodproofs_to_db --force
```

### Sync Ensemble Forecasts

```bash
# Sync all zones
docker-compose exec backend python manage.py sync_ensemble_from_ftp

# Sync specific zone
docker-compose exec backend python manage.py sync_ensemble_from_ftp --zone 1

# Limit files
docker-compose exec backend python manage.py sync_ensemble_from_ftp --limit 100

# Dry run
docker-compose exec backend python manage.py sync_ensemble_from_ftp --dry-run
```

### Load Static Data

```bash
# Load all static data
docker-compose exec backend python manage.py load_all_static_data

# Initialize database
docker-compose exec backend python manage.py init_db
```

### Database Operations

#### Connect to Database

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

#### Key Tables

- `impact_mergeddeterministicgeojson` - Floodproofs forecast data
- `impact_ensemble_forecast_geojson` - Ensemble forecast data
- `impact_geosfmgeojson` - GeoSFM satellite data
- `pgstac.items` - STAC items (imagery metadata)
- `pgstac.admin0`, `admin1`, `admin2` - Administrative boundaries
- `pgstac.rivers` - River network
- `pgstac.waterbodies` - Lakes and water bodies

#### Backup and Restore

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
# List all services
docker-compose ps

# View logs (all services)
docker-compose logs -f

# View logs (specific service)
docker-compose logs -f backend
docker-compose logs -f fastapi
docker-compose logs -f frontend
```

### Common Issues

#### Services Won't Start

```bash
# Check logs
docker-compose logs -f

# Restart specific service
docker-compose restart backend

# Restart all
docker-compose restart
```

#### Database Connection Errors

```bash
# Check database status
docker-compose ps postgis

# Test connection
docker-compose exec postgis psql -U postgres -d floodwatch -c "SELECT version();"

# Check logs
docker-compose logs postgis
```

#### Frontend Not Loading

```bash
# Check nginx logs
docker-compose logs frontend

# Rebuild frontend
docker-compose up -d --build frontend

# Check health
docker-compose ps frontend
```

#### API Returns No Data

```bash
# Check FastAPI
curl http://localhost:9050/health

# Check available dates
curl http://localhost:9050/api/fast/merged-forecast/dates/

# Restart to clear cache
docker-compose restart fastapi
```

#### Vector Tiles Not Loading

```bash
# Check TiPg service
curl http://localhost:8095/collections

# View logs
docker-compose logs tipg

# Restart
docker-compose restart tipg
```

---

## Support Checklist

When troubleshooting issues:

1. ✓ Check service logs: `docker-compose logs -f [service]`
2. ✓ Verify environment variables in `.env`
3. ✓ Ensure all services are healthy: `docker-compose ps`
4. ✓ Test database connectivity
5. ✓ Review API responses with curl
6. ✓ Clear caches by restarting services
