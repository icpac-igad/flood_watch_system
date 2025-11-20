# FloodWatch API Architecture Analysis - Summary Report

## Executive Summary
FloodWatch uses **Django REST Framework (DRF)** as the primary API framework with comprehensive geospatial capabilities. The system integrates **TiTiler** for raster data serving and MapServer for WMS/WMTS support. API documentation is enabled via **drf-spectacular** with Swagger/OpenAPI UI access.

---

## 1. CURRENT API STRUCTURE

### Framework & Architecture
- **Primary Framework**: Django REST Framework (DRF) 3.15.2
- **Documentation**: drf-spectacular 0.28.0 (generates OpenAPI 3.0 schemas)
- **Geospatial Support**: djangorestframework-gis 1.1 (GeoFeatureModelSerializer)
- **Authentication**: Multiple methods supported:
  - JWT (djangorestframework-simplejwt 5.5.1) - Primary
  - Token Authentication
  - Session Authentication
  - OAuth2 (Google OAuth implementation available)

### API Documentation Endpoints
Located at: `/api/schema/*`
- **Swagger UI**: `/api/schema/swagger-ui/`
- **ReDoc**: `/api/schema/redoc/`
- **OpenAPI Schema**: `/api/schema/` (JSON)

**Configuration File**: `/backend/flood_watch_system/settings/base.py` (lines 140-160)

```python
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.AllowAny'],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 100,
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'FloodWatch API',
    'DESCRIPTION': 'Flood monitoring and early warning system API',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}
```

---

## 2. API ENDPOINTS INVENTORY

### Base URL Structure
- **Main API Root**: `/api/`
- **Auth Routes**: `/api/auth/`
- **Admin Panel**: `/admin/`

### Core Data Endpoints (RESTful ViewSets)
All located in `/backend/Impact/urls.py`

#### Impact Data APIs
- `/api/affectedPop/` - Affected Population (GeoJSON, paginated)
- `/api/affectedGDP/` - Impacted GDP
- `/api/affectedCrops/` - Affected Crops
- `/api/affectedRoads/` - Affected Roads
- `/api/displacedPop/` - Displaced Population
- `/api/affectedLivestock/` - Affected Livestock
- `/api/affectedGrazingLand/` - Affected Grazing Land

#### Administrative Boundaries
- `/api/admin1/` - Admin Level 1 boundaries (GeoJSON, paginated)
- `/api/admin2/` - Admin Level 2 boundaries (GeoJSON, paginated)
- `/api/admin-boundaries/` - Simple GeoJSON endpoint

#### Infrastructure & Geographic Features
- `/api/water-bodies/` - Water bodies (GeoJSON, paginated)
- `/api/monitoring-stations/` - Monitoring stations (GeoJSON, paginated)
- `/api/rivers/` - Hydrological river networks (GeoJSON, paginated)

#### Impact Forecast Data (IBEW v2 Schema)
- `/api/ibew-v2-population/` - Population impact forecasts
- `/api/ibew-v2-infrastructure/` - Infrastructure impact forecasts
- `/api/ibew-v2-economic/` - Economic impact forecasts
- `/api/ibew-v2-health/` - Health impact forecasts
- `/api/ibew-v2-hydrological/` - Hydrological data

#### Report Workflow APIs (Node.js Replacement)
- `/api/station-reports/` - Station report approvals
  - GET/POST `/api/station-reports/by-station/{station_id}/`
- `/api/station-assessments/` - Station assessments
- `/api/saved-reports/` - Saved reports for user reports

### Temporal/Time-Series Endpoints
All return JSON with date metadata

#### GeoJSON by Date
- `/api/geojson/available-dates/` - List all available dates
- `/api/geojson/best-date/` - Get latest available date
- `/api/geojson/{date}/` - Get GeoJSON for specific date (YYYY-MM-DD format)

#### Deterministic Forecast
- `/api/deterministic/available-dates/` - Available forecast dates
- `/api/deterministic/latest/` - Latest deterministic forecast
- `/api/deterministic/{date}/` - Forecast by date

#### GeoSFM Forecast (Google Cloud Storage)
- `/api/geosfm/available-dates/` - Available GeoSFM dates
- `/api/geosfm/latest/` - Latest GeoSFM forecast
- `/api/geosfm/{date}/` - GeoSFM forecast by date
- `/api/geosfm/signed-urls/` - Signed URLs for GCS file access (frontend integration)
- `/api/geosfm/gcs-dates/` - GCS date availability

#### Merged Forecast (Dual Approach)
**File-based** (lighter weight):
- `/api/merged-forecast/dates/` - Available merged forecast dates
- `/api/merged-forecast/{date}/` - Merged forecast by date

**Database-backed** (FloodProofs from DB):
- `/api/merged-forecast-db/dates/`
- `/api/merged-forecast-db/{date}/`

### Raster Data & TiTiler Integration
All endpoints proxy to TiTiler service at `http://titiler:8000`

- `/api/raster/files/` - List available raster files (inundation, alerts, hazards)
- `/api/raster/info/` - Get raster metadata via TiTiler (requires `url` param)
- `/api/raster/statistics/` - Get raster statistics via TiTiler
- `/api/raster/latest-inundation/` - Latest inundation map with tile URLs
- `/api/raster/latest-alerts/` - Latest merged alerts with tile URLs
- `/api/raster/dates/` - Available raster dates
- `/api/raster/{date}/` - Raster files for specific date

**TiTiler Service**:
- Base URL: `http://titiler:8000` (configurable via `TITILER_BASE_URL`)
- Provides COG (Cloud Optimized GeoTIFF) endpoint: `/cog/info`, `/cog/tiles/`, `/cog/preview.png`
- Used for on-the-fly tile generation and raster statistics

### Layer Configuration & Metadata
- `/api/map-layers/` - Map layer configuration from Django admin
- `/api/layers/all-dates/` - All layers with available dates
- `/api/layers/{layer_id}/available-dates/` - Dates for specific layer
- `/api/layers/{layer_id}/latest-date/` - Latest date for layer
- `/api/layers/{layer_id}/check-date/{date}/` - Check if date available for layer
- `/api/layer-groups/{group_id}/available-dates/` - Group availability

### File Serving
- `/api/files/` - List files in directory (query param: `dir`)
- `/api/files/{file_path}/` - Serve individual file

### Authentication Endpoints
Location: `/backend/Impact/auth_views.py`
- `POST /api/auth/register/` - Register new user (AllowAny)
- `POST /api/auth/login/` - Login with credentials (AllowAny)
- `POST /api/auth/logout/` - Logout (IsAuthenticated)
- `POST /api/auth/google-login/` - Google OAuth login (AllowAny)
- `GET /api/auth/user-profile/` - Get current user profile (IsAuthenticated)
- `GET /api/auth/check-auth/` - Check authentication status (IsAuthenticated)

---

## 3. STAC API IMPLEMENTATION STATUS

### Current Status: NOT IMPLEMENTED

**pgSTAC**: Not installed or integrated
**STAC Compliance**: No STAC API endpoints present
**PySTAC**: Not in dependencies

### Related Components:
- **TiTiler** is installed (0.18.4) but used only for COG serving, not STAC
- **titiler.core** and **titiler.application** installed but not configured as STAC API
- No `/stac/`, `/collections/`, `/search/` endpoints

### What's Available Instead:
- Direct GeoJSON/date-based endpoints (custom implementation)
- File-system and database queries for temporal data
- TiTiler COG endpoints for raster data discovery

### Recommendation for STAC:
If supervisor feedback requests STAC API compliance, would require:
1. Install `stac-geoparquet` or `pgstac-py`
2. Create STAC Collections from existing models
3. Implement `/collections/` and `/search/` endpoints
4. Integrate with TiTiler's STAC API support (via stac-api)

---

## 4. RASTER DATA SERVING

### TiTiler Integration
**Status**: Integrated and functional
**Location**: `/backend/Impact/views_titiler.py`
**Version**: titiler.core==0.18.4, titiler.application==0.18.4

#### Capabilities:
- COG (Cloud Optimized GeoTIFF) serving
- Dynamic tile generation: `/cog/tiles/{z}/{x}/{y}.png`
- Preview generation: `/cog/preview.png`
- Raster info/statistics: `/cog/info`, `/cog/statistics`
- On-the-fly rescaling and colormap application

#### Data Directories Monitored:
- Inundation maps: `/app/data/inundation_maps/*.tif`
- Merged alerts: `/app/data/merged_alerts/*.tif`
- MapServer hazards: `/app/mapserver_data/hazards/*.tif`

#### Tile URL Example:
```
{TITILER_BASE_URL}/cog/tiles/{z}/{x}/{y}.png?url={file_url}&rescale=0,1&colormap_name=blues&nodata=0
```

### WMS/WMTS via MapServer
**Status**: Configured and integrated
**Service URLs**:
- WMS: `/mapserver/wms`
- WMTS: `/mapcache/wmts`

**MapServer Config Files**:
- `/mapserver/floodwatch.map` - Main configuration
- `/mapserver/admin0.map`, `/mapserver/admin1.map`, `/mapserver/admin2.map` - Administrative boundaries
- `/mapserver/waterbodies.map` - Water features
- `/mapserver/rivers.map` - River networks
- `/mapserver/monitoring_stations.map` - Station locations

---

## 5. VECTOR DATA SERVING

### GeoJSON APIs (Custom Implementation)
- All data models use `GeoFeatureModelSerializer` from `rest_framework_gis`
- Returns GeoJSON FeatureCollections with standard properties
- Includes pagination support (default 100 items per page)

#### Direct GeoJSON QuerySet APIs:
- Admin1, Admin2 boundaries
- Water bodies
- Monitoring stations
- Rivers
- All impact datasets (population, GDP, crops, roads, livestock, grazing land)

#### Alternative Lightweight Serializers:
For list views, uses stripped-down serializers without geometry:
- `AffectedPopulationListSerializer` - Metadata only
- `Admin1ListSerializer` - Metadata only
- `Admin2ListSerializer` - Metadata only

### WFS Integration
**Status**: Not directly implemented via DRF
**Available via**: MapServer WFS endpoints (if configured in .map files)

---

## 6. AUTHENTICATION & ACCESS CONTROL

### Authentication Methods Implemented

1. **JWT (Primary)**
   - Token generation on login
   - Access token lifetime: 1 hour
   - Refresh token lifetime: 7 days
   - Token rotation enabled
   - Blacklist after rotation

2. **Token Authentication**
   - Django built-in token auth
   - Used for API client authentication

3. **Session Authentication**
   - Traditional Django session-based auth
   - Fallback for web client

4. **Google OAuth**
   - Custom implementation in `google_login()` endpoint
   - Creates user automatically on first login
   - No password required for OAuth users

### Permission Classes
**Default**: `AllowAny` (globally configured)
**Per-endpoint**: Can override with `@permission_classes()`
- `IsAuthenticated` - Used on protected endpoints (user profile, logout)
- `AllowAny` - Used on public endpoints (register, login, data endpoints)

### Current Security Notes
- Auth middleware marked as COMPLETELY DISABLED (comment in settings: line 65)
- Map auth middleware disabled for development
- CORS headers enabled with `django-cors-headers`
- CSRF exempt decorator used on some viewsets for API access

---

## 7. API DOCUMENTATION CONFIGURATION

### DRF Spectacular Setup
**File**: `/backend/flood_watch_system/settings/base.py` (lines 154-160)

**Features Enabled**:
- Automatic OpenAPI 3.0 schema generation
- Swagger UI interface
- ReDoc documentation
- Per-endpoint schema decoration with `@extend_schema()`

**Documentation Decorators Used**:
```python
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

# Example from views.py:
@extend_schema(tags=['affected-population'])
class AffectedPopulationViewSet(viewsets.ModelViewSet):
    schema = AutoSchema()
    ...
```

**Access Points**:
- Swagger UI: `http://localhost:8000/api/schema/swagger-ui/`
- ReDoc: `http://localhost:8000/api/schema/redoc/`
- Raw Schema: `http://localhost:8000/api/schema/`

---

## 8. KEY CONFIGURATION FILES

### Settings
- **Base**: `/backend/flood_watch_system/settings/base.py` (312 lines)
- **Production**: `/backend/flood_watch_system/settings/production.py`
- **Staging**: `/backend/flood_watch_system/settings/staging.py`
- **Local Dev**: `/backend/flood_watch_system/settings/local.py`

### URL Routing
- **Main**: `/backend/flood_watch_system/urls.py` (34 lines)
- **App**: `/backend/Impact/urls.py` (169 lines)
- **Custom Router**: `/backend/Impact/custom_router.py` - RelativeURLRouter class

### Data Models & Serializers
- **Models**: `/backend/Impact/models.py` (multiple impact models)
- **Serializers**: `/backend/Impact/serializers.py` (GeoJSON serializers)
- **Report Models**: `/backend/Impact/models_reports.py`
- **Report Serializers**: `/backend/Impact/serializers_reports.py`

### View Modules
- **Main Views**: `/backend/Impact/views.py` (ViewSets)
- **Auth Views**: `/backend/Impact/auth_views.py` (User management)
- **TiTiler Views**: `/backend/Impact/views_titiler.py` (Raster serving)
- **GeoSFM Views**: `/backend/Impact/views_geosfm.py` (GCS integration)
- **Flood Hazard**: `/backend/Impact/views_flood_hazard.py` (MapServer integration)
- **Reports**: `/backend/Impact/views_reports.py` (Report workflow)
- **Files**: `/backend/Impact/views_files.py` (File serving)
- **Layer Dates**: `/backend/Impact/views_layer_dates.py` (Date availability)

---

## 9. CURRENTLY IMPLEMENTED vs. TODO

### What's Already Built

**Vector Data APIs**:
- ✅ RESTful endpoints for all spatial models (GeoFeatureModelSerializer)
- ✅ Pagination support (100 items/page)
- ✅ GeoJSON output format
- ✅ Lightweight metadata-only serializers for list views
- ✅ Admin boundary endpoints (Admin0, Admin1, Admin2)
- ✅ Feature endpoints (water bodies, rivers, monitoring stations)
- ✅ Impact data endpoints (population, GDP, crops, roads, livestock, etc.)

**Raster Data APIs**:
- ✅ TiTiler integration for COG serving
- ✅ Dynamic tile generation with colormaps
- ✅ Raster statistics endpoints
- ✅ Raster file discovery by date
- ✅ Latest inundation/alerts endpoints

**Temporal/Forecast APIs**:
- ✅ Date-based GeoJSON queries
- ✅ Deterministic forecast endpoints
- ✅ GeoSFM forecast with GCS signed URLs
- ✅ Merged forecast (file-based and DB-backed)

**Authentication**:
- ✅ JWT token authentication
- ✅ Google OAuth login
- ✅ User registration/login/logout
- ✅ Multiple auth methods (JWT, Token, Session)

**Documentation**:
- ✅ OpenAPI 3.0 schema generation (drf-spectacular)
- ✅ Swagger UI and ReDoc interfaces
- ✅ Per-endpoint schema decoration

**Report Workflow** (Node.js Replacement):
- ✅ Station report approval endpoints
- ✅ Station assessment endpoints
- ✅ Saved report endpoints with CRUD operations

### What's NOT Implemented

**STAC API**:
- ❌ STAC Collections endpoints
- ❌ STAC Search API
- ❌ pgSTAC integration
- ❌ STAC Item queries

**Advanced Data Access**:
- ❌ WFS (Web Feature Service) via DRF - only via MapServer
- ❌ Advanced spatial queries (intersection, buffering, etc.)
- ❌ Vector tile serving (MVT)
- ❌ Tipg integration for PostGIS queries

**Performance Optimization**:
- ❌ Database connection pooling (partially: CONN_MAX_AGE=600)
- ❌ API caching layer (except geosfm/gcs dates)
- ❌ Response compression
- ❌ Pagination for large datasets (only basic PageNumberPagination)

**API Management**:
- ❌ API versioning (no v1/, v2/ routes)
- ❌ Rate limiting
- ❌ Request validation schemas (beyond serializer validation)
- ❌ GraphQL API layer

**Data Transformation**:
- ❌ Field-level filtering in API responses
- ❌ Custom aggregations
- ❌ Time-series data endpoints with interpolation

---

## 10. SUMMARY TABLE

| Feature | Framework | Status | Location |
|---------|-----------|--------|----------|
| REST API | Django REST Framework 3.15.2 | ✅ | `/backend/Impact/` |
| Vector Data (GeoJSON) | DRF-GIS 1.1 | ✅ | `/backend/Impact/serializers.py` |
| Raster Data | TiTiler 0.18.4 | ✅ | `/backend/Impact/views_titiler.py` |
| WMS/WMTS | MapServer | ✅ | `/mapserver/*.map` |
| Authentication | JWT + OAuth | ✅ | `/backend/Impact/auth_views.py` |
| Documentation | drf-spectacular 0.28.0 | ✅ | `/api/schema/swagger-ui/` |
| STAC API | None | ❌ | N/A |
| WFS | MapServer only | ⚠️ | `/mapserver/wms` |
| Vector Tiles (MVT) | None | ❌ | N/A |

---

## 11. RECOMMENDATIONS FOR SUPERVISOR FEEDBACK

### Short-term API Improvements:
1. **Add STAC API Support** - If supervisor requests standards compliance
   - Use titiler.application with STAC extensions
   - Create STAC Collections from existing data models
   - Implement `/collections/` and `/search/` endpoints

2. **Implement Vector Tile API** - For better frontend performance
   - Tipg integration for MVT serving
   - Reduce data transfer for large datasets

3. **Add Request Validation** - Currently reliant on serializer validation
   - Implement OpenAPI-compliant request body schemas
   - Better error messaging

4. **Implement Rate Limiting** - For production deployment
   - Use django-ratelimit or drf-extensions
   - Protect against abuse

5. **Add Response Caching** - Improve performance
   - Redis-backed caching for date endpoints
   - ETags for conditional requests

### Medium-term Architecture:
1. **API Versioning** - Prepare for future changes
   - Namespace API routes (v1, v2)
   - Support multiple versions simultaneously

2. **Advanced Filtering** - Enhance query capabilities
   - Spatial filters (within, intersects)
   - Temporal range queries
   - Attribute filters

3. **GraphQL Layer** - Alternative query interface
   - Graphene-Django integration
   - Better developer experience

### Long-term Strategic:
1. **Microservices** - If system grows
   - Separate raster serving service (TiTiler)
   - Separate forecast processing service (Celery)
   - Separate reporting service

2. **Data Lake** - Consolidate data sources
   - Use pgSTAC for standardized catalog
   - Implement data lineage tracking
   - Versioned datasets

---

## Quick Reference: File Locations

### Most Important API Files
1. **Settings** - `/backend/flood_watch_system/settings/base.py` - REST_FRAMEWORK config
2. **URL Routing** - `/backend/Impact/urls.py` - All endpoint definitions
3. **Views** - `/backend/Impact/views.py` - Main ViewSets
4. **Auth** - `/backend/Impact/auth_views.py` - Authentication endpoints
5. **Serializers** - `/backend/Impact/serializers.py` - GeoJSON serializers
6. **Raster** - `/backend/Impact/views_titiler.py` - TiTiler integration

### Documentation Access
- Swagger UI: `http://localhost:8000/api/schema/swagger-ui/`
- OpenAPI Schema: `http://localhost:8000/api/schema/`
