# FloodWatch Staging Deployment Guide

## Prerequisites on Staging Server

### 1. System Requirements
- Ubuntu/RHEL/CentOS Linux (64-bit)
- 8GB RAM minimum (16GB recommended)
- 50GB disk space minimum
- Docker Engine 20.10+
- Docker Compose 1.29+

### 2. Install Docker & Docker Compose
```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add user to docker group
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verify installation
docker --version
docker-compose --version
```

### 3. Create Deployment Directory
```bash
# Create project directory
mkdir -p ~/flood_watch_staging
cd ~/flood_watch_staging

# Create required subdirectories
mkdir -p backend/static_data
```

### 4. Required Static Data Files
Place these files in `backend/static_data/` on staging:
- `GHA_EA_admin0.geojson` (Admin level 0 boundaries)
- `GHA_EA_admin1.geojson` (Admin level 1 boundaries)
- `GHA_EA_admin2.geojson` (Admin level 2 boundaries)
- `Lakes.geojson` (Water bodies)
- `HydroRIVERS_v10_GHA.geojson` (River network)
- `ensemble_control_file.geojson` (Ensemble control points)
- `fp_sections_igad.shp/dbf/prj/shx` (Monitoring stations shapefile)

---

## Deployment Steps

### Step 1: Copy Configuration Files to Staging

From your **LOCAL machine**:

```bash
cd "/home/koros/Downloads/MusoknotetabMaranet (3)/MusoknotetabMaranet"

# Copy docker-compose configuration
scp docker-compose.staging.yml hkoros@197.254.1.10:~/flood_watch_staging/docker-compose.yml

# Copy environment configuration
scp .env.staging hkoros@197.254.1.10:~/flood_watch_staging/.env

# Copy static data files (if not already present)
scp backend/static_data/*.geojson hkoros@197.254.1.10:~/flood_watch_staging/backend/static_data/
scp backend/static_data/fp_sections_igad.* hkoros@197.254.1.10:~/flood_watch_staging/backend/static_data/
```

### Step 2: On Staging Server - Initial Setup

```bash
cd ~/flood_watch_staging

# Verify files are present
ls -la
ls -la backend/static_data/

# Fix permissions on static data directory
sudo chown -R $USER:$USER backend/static_data/
chmod 755 backend/static_data/
```

### Step 3: Pull Docker Images

```bash
cd ~/flood_watch_staging

# Login to Docker Hub (if using private images)
docker login

# Pull all images
docker-compose pull
```

### Step 4: Start Services

```bash
# Start all services
docker-compose up -d

# Wait for services to start (takes ~2 minutes)
sleep 120

# Check service status
docker-compose ps
```

**Expected output:** All services should show "Up" and "healthy" status.

### Step 5: Initialize Database

```bash
# Run database migrations
docker-compose exec backend python manage.py migrate

# Load static geospatial data
docker-compose exec backend python manage.py load_all_static_data
```

**Expected output:**
- Admin0: 12 records loaded
- Admin1: 171 records loaded
- Admin2: 1070 records loaded
- Lakes: 169 records loaded
- Ensemble Control Points: 3199 records loaded

### Step 6: Create Admin User

```bash
# Create Django superuser
docker-compose exec backend python manage.py createsuperuser
```

### Step 7: Verify Deployment

```bash
# Test backend
curl http://localhost:8090/admin/

# Test FastAPI
curl http://localhost:8093/health

# Test TiPg
curl http://localhost:8095/collections

# Test frontend
curl http://localhost:8094/
```

---

## Access Points

| Service | URL | Credentials |
|---------|-----|-------------|
| **Frontend** | http://staging-ip:8094 | - |
| **Backend Admin** | http://staging-ip:8090/admin | (created in Step 6) |
| **FastAPI Docs** | http://staging-ip:8093/docs | - |
| **TiPg Explorer** | http://staging-ip:8095 | - |

---

## Configuration Details

### Environment Variables (.env.staging)

**Required variables:**
- `DB_NAME` - Database name (default: floodwatch)
- `DB_USER` - Database user (default: postgres)
- `DB_PASSWORD` - Database password
- `DJANGO_ALLOWED_HOSTS` - Comma-separated allowed hosts
- `CORS_ALLOWED_ORIGINS` - Frontend URL
- `SECRET_KEY` - Django secret key (generate with `openssl rand -base64 50`)

**Optional but recommended:**
- `SFTP_HOST`, `SFTP_USERNAME`, `SFTP_PASSWORD` - Floodproofs data sync
- `FTP_HOST`, `FTP_USER`, `FTP_PASSWORD` - Ensemble forecast data sync
- `GCS_PROJECT_ID`, `GCS_BUCKET_NAME` - Google Cloud Storage for GeoSFM data

### Service Ports

- **8090** - Django Backend API
- **8091** - PostgreSQL Database
- **8092** - Redis Cache
- **8093** - FastAPI Service
- **8094** - Frontend (Nginx)
- **8095** - TiPg Vector Tiles

---

## Data Synchronization

### Sync Floodproofs Data (Deterministic Forecasts)

```bash
# Sync latest 30 days
docker-compose exec backend python manage.py sync_floodproofs_to_db

# Sync specific date
docker-compose exec backend python manage.py sync_floodproofs_to_db --date 2025-11-19
```

### Sync Ensemble Forecasts

```bash
# Sync all zones from FTP
docker-compose exec backend python manage.py sync_ensemble_from_ftp

# Sync specific zone
docker-compose exec backend python manage.py sync_ensemble_from_ftp --zone 1
```

---

## Troubleshooting

### Services Not Starting

```bash
# Check service logs
docker-compose logs -f [service_name]

# Restart specific service
docker-compose restart [service_name]

# Recreate service
docker-compose up -d --force-recreate [service_name]
```

### Backend Unhealthy

```bash
# Check backend logs
docker-compose logs backend | tail -100

# Common issue: collectstatic hanging
# Solution: Restart backend
docker-compose restart backend
```

### TiPg Internal Server Error

```bash
# Check TiPg logs
docker-compose logs tipg | tail -50

# Verify database connection
docker-compose exec tipg env | grep POSTGRES

# Check tables exist
docker-compose exec postgis psql -U postgres -d floodwatch -c "SELECT COUNT(*) FROM geometry_columns WHERE f_table_schema = 'pgstac';"

# Should return 6 or more tables
```

### Frontend Not Loading

```bash
# Check frontend logs
docker-compose logs frontend

# Check nginx configuration
docker-compose exec frontend cat /etc/nginx/conf.d/default.conf

# Restart frontend
docker-compose restart frontend
```

### Database Connection Errors

```bash
# Check database is running
docker-compose ps postgis

# Test connection
docker-compose exec postgis psql -U postgres -d floodwatch -c "SELECT version();"

# Check database logs
docker-compose logs postgis
```

---

## Updating Deployment

### Pull Latest Images

```bash
cd ~/flood_watch_staging

# Pull latest images
docker-compose pull

# Recreate containers with new images
docker-compose up -d

# Run migrations
docker-compose exec backend python manage.py migrate
```

### Update Configuration

```bash
# From local machine, copy updated files
scp docker-compose.staging.yml user@staging:~/flood_watch_staging/docker-compose.yml
scp .env.staging user@staging:~/flood_watch_staging/.env

# On staging, restart services
cd ~/flood_watch_staging
docker-compose down
docker-compose up -d
```

---

## Backup & Restore

### Backup Database

```bash
# Create backup
docker-compose exec postgis pg_dump -U postgres floodwatch > backup_$(date +%Y%m%d).sql

# Backup to remote location
scp backup_$(date +%Y%m%d).sql user@backup-server:/backups/
```

### Restore Database

```bash
# Restore from backup
docker-compose exec -T postgis psql -U postgres floodwatch < backup_20251119.sql
```

---

## Monitoring

### Check Service Health

```bash
# View all service status
docker-compose ps

# Check resource usage
docker stats

# View logs in real-time
docker-compose logs -f
```

### Check Data Availability

```bash
# Check available forecast dates
curl http://localhost:8093/api/fast/merged-forecast/dates/

# Check ensemble dates
curl http://localhost:8093/api/fast/ensemble-forecast-dates/
```

---

## Security Notes

1. **Change default passwords** in .env file
2. **Use strong SECRET_KEY** for Django
3. **Configure firewall** to restrict access to ports
4. **Use HTTPS** in production (add nginx reverse proxy with SSL)
5. **Restrict DJANGO_ALLOWED_HOSTS** to actual domains
6. **Set DEBUG=False** in production

---

## Support

For issues:
1. Check service logs: `docker-compose logs -f [service]`
2. Verify environment variables: Check `.env` file
3. Ensure all services are healthy: `docker-compose ps`
4. Check database connectivity: Test psql connection
5. Review API responses: Test endpoints with curl
