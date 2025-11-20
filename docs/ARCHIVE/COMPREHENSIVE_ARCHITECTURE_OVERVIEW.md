# East Africa Flood Watch System - Comprehensive Architecture Overview

## Project Context
**Repository:** MusoknotetabMaranet (East Africa Flood Watch)
**Current Status:** Multi-service microarchitecture with Django backend, React frontend, multiple FastAPI services
**Key Focus:** Integrating STAC API with EAOPI data and migrating FastAPI to TiPg

---

## 1. CURRENT STAC API IMPLEMENTATION

### Location
`/home/koros/Downloads/MusoknotetabMaranet (3)/MusoknotetabMaranet/stac-api/`

### Files
- **main.py** - STAC API application using stac-fastapi-pgstac
- **init_pgstac.py** - Database initialization script
- **requirements.txt** - Python dependencies

### Current Configuration
```python
# Technology Stack
- stac-fastapi-pgstac==6.1.0
- uvicorn[standard]==0.38.0
- psycopg[binary,pool]==3.2.3
- pypgstac==0.9.8

# Database Settings
- Postgres connection via stac-fastapi Settings
- PgSTAC extension enabled for STAC metadata storage
- Transactions extension enabled for data ingestion
- Response models disabled for performance
```

### Current Endpoints
```
GET  /                      - Landing page
GET  /collections           - List all collections
GET  /collections/{id}      - Get collection details
GET  /collections/{id}/items - List items
POST /search                - Spatial/temporal search
GET  /health                - Health check (port 8081)
```

### Database Setup
- **Schema:** pgstac schema automatically created in floodwatch database
- **Connection:** `postgresql://postgres:floodwatch_pass@postgis:5432/floodwatch`
- **Initialization:** init_pgstac.py uses pypgstac.db.PgstacDB for setup

### Current Limitations
- No collections are currently registered (empty catalog)
- No EAOPI data ingestion pipeline
- Service is running but not integrated with forecast data
- No custom metadata for flood forecasts

---

## 2. CURRENT FASTAPI SERVICE

### Location
`/home/koros/Downloads/MusoknotetabMaranet (3)/MusoknotetabMaranet/fastapi-service/`

### Files
- **main.py** - FastAPI forecast service
- **requirements.txt** - Dependencies
- **Dockerfile** - Container configuration

### Core Functionality

#### Database Table Served
```sql
Impact_mergeddeterministicgeojson
- data_date: Date of forecast
- date_string: YYYYMMDD format
- geojson_data: JSONB - complete FeatureCollection (979 features)
- feature_count: Integer
- file_count: Integer
- created_at, updated_at: Timestamps
```

#### Endpoints

1. **GET `/api/fast/merged-forecast/dates/`**
   - Returns all available forecast dates
   - Includes feature_count, file_count, created_at metadata
   - Response cached for 900 seconds (15 min TTL)
   - Returns: `{'dates': [...], 'count': int, 'source': 'database'}`

2. **GET `/api/fast/merged-forecast/{forecast_date}/`**
   - Gets forecast for specific date (YYYY-MM-DD)
   - Optional ?country parameter for filtering
   - Falls back to latest if exact date unavailable
   - Response headers include X-Forecast-Date, X-Feature-Count, X-Original-Count
   - Cache-Control: public, max-age=3600

3. **GET `/api/fast/merged-forecast/latest/`**
   - Returns latest available forecast
   - Optional ?country filtering
   - Cache-Control: public, max-age=1800

4. **GET `/health`**
   - Database connectivity check

#### Performance Features
- AsyncPG connection pooling (min_size=5, max_size=20)
- In-memory caching with TTL validation
- ORJSON response serialization
- Response timing headers for monitoring
- Timing logs with emoji status indicators (⚡ < 5ms, 🚀 < 20ms, ✅ < 100ms, ⚠️ > 100ms)

#### Architecture
```python
# Lifespan Management
- Startup: Creates AsyncPG pool, validates database connection
- Shutdown: Closes connection pool gracefully

# Filtering
- By date (YYYY-MM-DD format validation)
- By country (case-insensitive string matching)
- Date validation with datetime.strptime ensuring valid dates

# Data Structure
- GeoJSON FeatureCollection format
- 979 features per forecast date
- Properties include country, impact metrics
```

### Current Port
- **Docker:** 8001
- **Docker-Compose Exposed:** 9050:8001

---

## 3. TIPG SERVICE CONFIGURATION

### Location
`/home/koros/Downloads/MusoknotetabMaranet (3)/MusoknotetabMaranet/tipg-service/`

### Files
- **main.py** - TiPg application
- **requirements.txt** - Dependencies (tipg==1.2.1)
- **Dockerfile** - Container config

### Current Configuration
```python
# Technology Stack
- tipg==1.2.1
- uvicorn[standard]==0.32.0
- psycopg[binary,pool]==3.2.3

# Database
DATABASE_URL = "postgresql://postgres:floodwatch_pass@postgis:5432/floodwatch"
db_min_conn_size = 1
db_max_conn_size = 10
```

### Configured Tables to Serve
```
OGC API Tables (Automatic detection from PostGIS):
- Impact_admin0           - Country boundaries
- Impact_admin1           - Province boundaries
- Impact_admin2           - District boundaries
- Impact_waterbodies      - Lakes and water bodies
- Impact_hydrorivers      - River network (283,806 segments)
- Impact_monitoringstation - Monitoring stations
```

### Endpoints (OGC Features & Tiles API)
```
GET  /collections                              - List tables
GET  /collections/{id}                         - Table metadata
GET  /collections/{id}/items                   - Features (GeoJSON)
GET  /collections/{id}/tiles/{z}/{x}/{y}      - Vector tiles (MVT format)
POST /collections/{id}/tiles                   - Create mosaic tiles
GET  /health                                   - Health check
```

### Port
- **Docker:** 8083
- **Service Status:** Not yet exposed in docker-compose (needs configuration)

### Built-In Features
- Automatic table discovery from database
- Vector tile generation (Mapbox Vector Tiles format)
- Feature collection serving with pagination
- Built-in tile viewer at `/tiles/viewer`
- CORS enabled for all origins

---

## 4. BACKEND DJANGO/DRF ARCHITECTURE

### Location
`/home/koros/Downloads/MusoknotetabMaranet (3)/MusoknotetabMaranet/backend/`

### Port
- **Docker:** 8090

### Key Models

#### Spatial Data Models
```python
Admin0              - Country boundaries (gid_0, country, geom)
Admin1              - Province boundaries
Admin2              - District boundaries
WaterBodies         - Lakes/waterbodies (af_wtr_id, type_of_wa, geom)
HydroRivers         - River network (hyriv_id, length_km, dis_av_cms, geometry)
MonitoringStation   - Gauge stations (sec_code, sec_name, basin, geometry, thresholds)
```

#### Forecast Data Models
```python
MergedDeterministicGeoJSON
  - data_date: Date (unique)
  - date_string: YYYYMMDD format (unique)
  - geojson_data: JSONField (complete FeatureCollection)
  - feature_count, file_count: Metadata
  - created_at, updated_at, processed_by

EnsembleControlPoint
  - GRIDCODE: Unique identifier
  - zone: Zone information
  - geometry: Point location
  - Used for merging ensemble forecast data with CSV datasets
```

#### Raster Data Models
```python
AlertLevelRaster
  - data_date, time_run, alert_group
  - raster: RasterField (COG data)
  - file_path, file_size

FloodHazardMapRaster
  - data_date, time_run
  - raster: RasterField
```

### API Endpoints (REST Framework)

#### ViewSets with GeoJSON Serialization
```
GET /api/admin0/                     - Country boundaries
GET /api/admin1/                     - Province boundaries  
GET /api/admin2/                     - District boundaries
GET /api/water-bodies/               - Waterbodies
GET /api/hydro-rivers/               - River network
GET /api/monitoring-stations/        - Gauge stations
GET /api/ensemble-control-points/    - Ensemble reference points
```

#### Custom API Views
```
GET /api/geosfm/{date}/              - GeoSFM forecast by date
GET /api/geosfm/available-dates/     - GeoSFM available dates
```

### Serializers
- WaterBodiesSerializer
- Admin0/Admin1/Admin2Serializer (with list variants for performance)
- MonitoringStationSerializer
- HydroRiversSerializer
- EnsembleControlPointSerializer
- MergedDeterministicGeoJSONSerializer

### Authentication
```python
# BasicAuthMiddleware (staging only)
- Optional basic HTTP auth for staging environment
- Can be enabled via STAGING_AUTH_ENABLED setting
- Credentials: username/password via Authorization header

# MapAuthMiddleware (currently DISABLED for testing)
- JWT authentication (rest_framework_simplejwt)
- Protected patterns: geojson, deterministic, flood-hazard, layers, admin boundaries
- Public patterns: auth endpoints, admin, static, media
- Currently bypassed - returns None immediately for testing
```

### CORS Configuration
```python
CORS_ALLOWED_ORIGINS = [
    'http://localhost:5000',
    'http://localhost:5173'
]
```

---

## 5. EAOPI DATA INTEGRATION STATUS

### Current State
**EAOPI/Ensemble data infrastructure EXISTS but is not integrated with STAC API:**

#### Files Present
- `download_ensemble_data.py` - Script to download from FTP server
- `download_ensemble_smb.py` - Alternative SMB protocol download
- `download_ensemble_smbclient.py` - Another SMB variant
- `sync_ensemble_to_db.py` - Management command to sync ensemble data to database
- Documentation: `ENSEMBLE_DATA_GUIDE.md`, `ENSEMBLE_DOWNLOAD_STATUS.md`

#### FTP Connection Details
```env
ENSEMBLE_SFTP_HOST=41.215.21.156
ENSEMBLE_FTP_PORT=21
ENSEMBLE_SFTP_USERNAME=geosfm
ENSEMBLE_SFTP_PASSWORD="icpac#254"
ENSEMBLE_REMOTE_PATH=/ftproot/output/Combined
ENSEMBLE_LOCAL_CACHE=/app/ensemble_cache
```

#### Data Structure
```
FTP Server Directory Structure:
/ftproot/output/Combined/
├── YYYYMMDD/          (Date directories)
│   ├── Zone_00/       (Zone files)
│   ├── Zone_01/
│   └── ...Zone_N/
```

#### Integration Points
1. **Backend Management Command:** `sync_ensemble_to_db`
   - Loads ensemble forecast data from SFTP or local cache
   - Merges with ensemble control points from database
   - Creates GeoJSON for visualization
   - Supports date-based or N-days filtering

2. **EnsembleControlPoint Model**
   - Reference locations for merging ensemble data
   - GRIDCODE: Unique identifier
   - Zone: Zone information for spatial matching
   - Geometry: Point location

3. **Load Data Command:** `load_all_static_data`
   - Loads ensemble control points from GeoJSON file
   - --skip-ensemble flag to skip loading
   - Processes ensemble_control_file.geojson

### What's Missing for STAC Integration
- No STAC Collections defined for ensemble data
- No STAC Items created from ensemble forecast files
- No metadata catalog integration
- No temporal/spatial search indexing in PgSTAC

---

## 6. FRONTEND CONFIGURATION & API ENDPOINTS

### Location
`/home/koros/Downloads/MusoknotetabMaranet (3)/MusoknotetabMaranet/frontend/src/config/endpoints.ts`

### Environment Variables
```typescript
VITE_API_URL         - Django backend base (default: http://localhost:8090)
VITE_FASTAPI_URL     - FastAPI forecast service (default: http://localhost:8093)
VITE_MAPSERVER_URL   - MapServer WMS (default: http://localhost:8095)
VITE_MAPCACHE_WMS_URL - MapCache WMS (default: http://localhost:8096)
VITE_MAPCACHE_TMS_URL - MapCache TMS (default: http://localhost:8096/tms/1.0.0)
```

### Configured Endpoints Object
```typescript
API_ENDPOINTS = {
  base: 'http://localhost:8090',
  fastApi: 'http://localhost:8093',
  
  forecasts: {
    deterministic: {
      dates: '/fast/merged-forecast/dates/',      // FastAPI
      byDate: (date) => `/fast/merged-forecast/${date}/`,
      latest: '/fast/merged-forecast/latest/'
    },
    geosfm: {
      dates: '/geosfm/available-dates/',          // Django
      byDate: (date) => `/geosfm/${date}/`
    }
  },
  
  boundaries: {
    admin0: '/admin0/',
    admin1: '/admin1/',
    admin2: '/admin2/',
    waterbodies: '/water-bodies/'
  },
  
  mapserver: {
    wms: 'http://localhost:8095/',
    mapcacheWms: 'http://localhost:8096/',
    mapcacheTms: 'http://localhost:8096/tms/1.0.0'
  },
  
  stac: {
    base: 'http://localhost:8081',               // Not yet integrated
    collections: 'http://localhost:8081/collections'
  },
  
  tipg: {
    base: 'http://localhost:8083',               // Not yet integrated
    collections: 'http://localhost:8083/collections'
  }
}
```

### Frontend Services
- **hooks/useForecastData.ts** - React hook for forecast data fetching
- **utils/forecastCache.js** - Client-side caching with TTL
- **utils/chartUtils.jsx** - Chart rendering (DischargeChart, GeoSFMChart)
- **services/forecastService.ts** - Forecast data fetching logic

### Port
- **Docker:** 8080 (exposed as 8094:8080)

---

## 7. AUTHENTICATION & SECURITY

### Current Implementation Status
```
BasicAuthMiddleware      - IMPLEMENTED (staging only)
MapAuthMiddleware        - IMPLEMENTED but DISABLED
JWT Authentication       - CONFIGURED but DISABLED
```

### BasicAuth (Staging)
```python
# File: backend/Impact/utils/auth_middleware.py
- Only enabled if STAGING_AUTH_ENABLED = True
- Credentials: username/password via Authorization header
- Exemptions: /admin/, /health/
```

### JWT (Disabled for Testing)
```python
# File: backend/Impact/utils/map_auth_middleware.py
- Uses rest_framework_simplejwt.JWTAuthentication
- Protected patterns: /api/.*geojson.*, /api/.*deterministic.*, /api/.*layers.*
- Public patterns: /api/auth/*, /admin/*, /health
- Currently returns None (allows all requests)
```

### CORS
```python
# All services have CORS enabled for * origins
# In production, should restrict to specific domains
```

---

## 8. DOCKER COMPOSE INFRASTRUCTURE

### Port Mappings
```
Frontend         8094:8080  (React app)
Django Backend   8090:8090  (DRF API)
FastAPI          9050:8001  (Forecast service)
MapServer        8095:80    (WMS/WFS) [commented out in newer config]
MapCache         8096:80    (Tile caching) [commented out]
PostgreSQL       8091:5432  (Database)
Redis            9092:6379  (Cache/Celery)
```

### Services Defined
```yaml
postgis          - PostgreSQL + PostGIS + PgSTAC
redis            - Caching and Celery broker
backend          - Django application (health check: /admin/)
celery           - Background task worker
celery-beat      - Task scheduler
frontend         - React application
mapserver        - WMS/WFS service [COMMENTED OUT]
mapcache         - Tile cache [COMMENTED OUT]
fastapi          - Forecast data service
# NOT YET CONFIGURED:
stac-api         - STAC service (port 8081)
tipg-service     - Vector tiles (port 8083)
titiler-pgstac   - Raster tiles (not exposed)
```

### Database Health Checks
```yaml
postgis:
  test: pg_isready -U postgres -d floodwatch
  interval: 10s
  timeout: 5s
  retries: 5
```

### Volume Mounts
```
postgis_data       - Database persistence
redis_data         - Cache persistence
static_volume      - Django static files
media_volume       - User uploads
mapcache_data      - Tile cache
mapserver conf     - ./mapserver:z
backend static data - ./backend/static_data:ro,z
```

---

## 9. SERVICE INTEGRATION DIAGRAM

```
┌─────────────────────────────────────────────────────────────────┐
│                  FRONTEND (React + Vite)                         │
│  Port 8094 - MapViewer, Charts, Sidebar Controls               │
└────────────────────────┬────────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
        v                v                v
   ┌────────────────┐ ┌──────────────┐ ┌──────────────┐
   │  DJANGO (8090) │ │ FastAPI(9050)│ │MapServer(8095)
   │ - GeoJSON APIs │ │ - Forecasts  │ │  - WMS/WFS
   │ - Boundaries   │ │ - Caching    │ │  - Tiles
   │ - Monitoring   │ │ - Timing logs│ │
   │ - Auth         │ │              │ │
   └────────┬────────┘ └──────┬───────┘ └──────┬───────┘
            │                 │                │
            └─────────────────┼────────────────┘
                              │
                    ┌─────────v─────────┐
                    │  PostgreSQL+PostGIS
                    │  (Port 8091)
                    │  - Spatial data
                    │  - Forecasts
                    │  - PgSTAC schema
                    └───────────────────┘

NOT YET INTEGRATED:
┌────────────────┐  ┌──────────────┐  ┌──────────────┐
│  STAC API(8081)│  │  TiPg(8083)  │  │TiTiler(8000) │
│ - Metadata cat │  │ - Vec tiles  │  │ - Raster img │
│ - Collections  │  │ - OGC API    │  │ - COGs       │
└────────────────┘  └──────────────┘  └──────────────┘
```

---

## 10. KEY CONFIGURATION FILES

### Environment File (.env)
```
# SFTP (Floodproofs Data)
SFTP_HOST=197.254.113.173
SFTP_USERNAME=floodproofs
REMOTE_FOLDER_BASE=fp-eastafrica/storage/impact_assessment/...

# Ensemble (GeoSFM/EAOPI)
ENSEMBLE_SFTP_HOST=41.215.21.156
ENSEMBLE_SFTP_USERNAME=geosfm
ENSEMBLE_REMOTE_PATH=/ftproot/output/Combined

# Database
DB_NAME=floodwatch
DB_USER=postgres
DB_PASSWORD=floodwatch_pass

# Google Cloud Storage (optional)
GCS_PROJECT_ID=
GCS_BUCKET_NAME=geosfm
GCS_GEOSFM_PREFIX=geosfm_output_icpac_pc/
```

### Docker Compose Staging
`docker-compose.staging.yml` - Similar setup but with staging-specific configurations

---

## 11. WHAT NEEDS TO BE MIGRATED/INTEGRATED

### Priority 1: STAC API Integration
1. Define STAC Collections for:
   - Deterministic Forecasts
   - Ensemble Forecasts (EAOPI)
   - Raster Products (Inundation, Alerts)
   - Administrative Boundaries
   - River Network Data

2. Create STAC Item ingestion pipeline:
   - Convert forecast GeoJSON to STAC Items
   - Index ensemble data as STAC Items
   - Register collections in PgSTAC

3. Temporal/spatial search:
   - Enable /search endpoint
   - Index by date ranges
   - Spatial bbox filtering

### Priority 2: TiPg Vector Tiles
1. Expose TiPg service in docker-compose
2. Configure in frontend endpoints.ts
3. Create vector tile layers in map viewer
4. Replace MapServer WMS with TiPg OGC Features API

### Priority 3: FastAPI to TiPg Migration
1. Move forecast GeoJSON serving from FastAPI to TiPg
2. Use TiPg's /collections/{id}/items for feature serving
3. Use TiPg's /tiles endpoint for map rendering
4. Keep FastAPI only if needed for specialized queries

### Priority 4: EAOPI Data Integration
1. Create STAC Collection for Ensemble Forecasts
2. Index ensemble data from sync_ensemble_to_db
3. Make searchable through STAC /search endpoint
4. Create Items for each ensemble forecast date

---

## 12. DEPENDENCY VERSIONS SUMMARY

### STAC API Stack
```
stac-fastapi-pgstac==6.1.0
pypgstac==0.9.8
uvicorn[standard]==0.38.0
psycopg[binary,pool]==3.2.3
```

### FastAPI Stack
```
fastapi==0.115.0
uvicorn[standard]==0.32.0
asyncpg==0.29.0
orjson==3.10.7
psycopg2-binary==2.9.9
```

### TiPg Stack
```
tipg==1.2.1
uvicorn[standard]==0.32.0
psycopg[binary,pool]==3.2.3
```

### Backend (Django)
```
Django==4.2.11
djangorestframework>=3.14.0
djangorestframework-gis>=0.20
drf-spectacular>=0.27
django-cors-headers>=4.3
psycopg2-binary==2.9.9
celery>=5.3
```

### Frontend (React)
```
react==19.0.0
react-router-dom>=6.0
vite>=5.0
@mui/material>=5.0
recharts>=2.0
leaflet==1.9.4
react-leaflet==5.0
maplibre-gl==5.0
zustand>=4.0
@tanstack/react-query>=4.0
```

---

## SUMMARY TABLE

| Component | Status | Port | Technology | Notes |
|-----------|--------|------|-----------|-------|
| STAC API | Implemented | 8081 | stac-fastapi-pgstac | No data ingested yet |
| FastAPI | Implemented | 8001/9050 | FastAPI + AsyncPG | High-performance forecast serving |
| TiPg | Implemented | 8083 | TiPg 1.2.1 | Auto-serves PostGIS tables |
| Django | Implemented | 8090 | Django + DRF | GeoJSON APIs + auth |
| Frontend | Implemented | 8080/8094 | React + Vite | Partially configured for new services |
| PostgreSQL | Implemented | 5432/8091 | PostGIS + PgSTAC | All data stored here |
| Redis | Implemented | 6379/9092 | Redis | Caching + Celery |
| MapServer | Implemented | 8095 | MapServer | WMS/WFS (commented out in config) |
| EAOPI Data | Partial | - | FTP sync scripts | Infrastructure exists, not integrated |

