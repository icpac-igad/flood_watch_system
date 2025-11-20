# East Africa Flood Watch System

## Overview

The East Africa Flood Watch System is a comprehensive flood monitoring and forecasting platform for the IGAD (Intergovernmental Authority on Development) region. The system provides real-time flood hazard monitoring, impact assessment, and forecast visualization through a web-based interface.

**Core Capabilities:**
- Real-time flood monitoring and alerts across East African river basins
- Impact assessment for population, infrastructure, crops, and livestock
- Multi-model hydrological forecasting (GFS, ICON weather models)
- River discharge monitoring at 979 stations with balloon markers
- Administrative boundary-based impact aggregation
- Report approval workflow for member states and ICPAC
- Admin-managed map layer configuration (no MapServer complexity)

**Recent Changes (Oct 21, 2025):**
- ✅ Added API caching (1 hour for forecast data, 15 min for dates)
- ✅ Created MapLayerConfig model for admin-managed WMS layers
- ✅ Cleaned project structure (backend + frontend only)
- ✅ Daily automated merge at 12:00 UTC via cron on SFTP server

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Backend Architecture (Django + GeoDjango)

**Framework Choice: Django 4.2 with GeoDjango**
- **Rationale:** Django provides robust ORM with PostGIS spatial database support through GeoDjango, enabling efficient spatial queries for flood extent analysis
- **Spatial Features:** Uses PostGIS for geometry storage, spatial indexing, and geographic calculations
- **API Layer:** Django REST Framework (DRF) with GeoJSON serialization via djangorestframework-gis

**Database Design:**
- **Impact Models:** Abstract base class `BaseImpactModel` with common fields (administrative boundaries, impact metrics, geometry) extended by specific impact types (population, GDP, crops, roads, livestock, displaced persons)
- **IBEW v1/v2 Layers:** Separate models for different impact assessment versions with polygon geometries
- **Forecast Data:** Time-series hydrograph data stored as JSON in database models, with date-based filtering
- **Report Workflow:** Two-stage approval system (Member State → ICPAC) for station reports and assessments

**GIS Library Configuration:**
- GDAL and GEOS libraries configured via environment variables for geospatial data processing
- Rasterio for raster data manipulation (flood maps, alerts)
- GeoPandas for shapefile processing and vector operations

### Frontend Architecture (React + Vite)

**Framework Choice: React 19 with Vite**
- **Rationale:** Vite provides fast development builds and hot module replacement; React offers component-based architecture for complex map interactions
- **Build Tool:** Vite configured for production optimization with asset bundling

**Mapping Libraries:**
- **Primary:** Leaflet + React-Leaflet for vector map visualization
- **Secondary:** MapLibre GL for potential tile-based rendering
- **Plugins:** Leaflet.markercluster for station clustering, Leaflet.vectorgrid for efficient vector tiles

**State Management:**
- Zustand for lightweight global state management
- TanStack Query (React Query) for server state caching and synchronization

**UI Framework:**
- Material-UI (MUI) for consistent component design
- Bootstrap for layout and responsive grid system
- Recharts for data visualization and time-series charts

### Raster Data Processing

**TiTiler Service:**
- **Purpose:** FastAPI-based raster tile server for serving flood inundation maps and alerts
- **Integration:** Separate microservice exposing COG (Cloud Optimized GeoTIFF) endpoints
- **Data Types:** Inundation maps, discharge alerts, hazard layers organized by date hierarchy (YYYY/MM/DD)

**MapServer Integration:**
- Date-based raster serving through WMS endpoints
- Dynamic layer configuration for temporal flood data
- Organized data structure: `/mapserver_data/{layer_type}/{YYYY}/{MM}/{DD}/`

### Data Synchronization

**SFTP Integration:**
- **Source:** ICPAC flood forecasting system (fp-eastafrica server)
- **Data Types:** Daily hydrograph JSON files, raster products (inundation, alerts)
- **Structure:** Hierarchical date-based organization (YYYY/MM/DD/HH) with deterministic and ensemble forecasts
- **Processing:** Python scripts for SFTP download, raster merging, and database ingestion

**Celery Task Queue:**
- Asynchronous data synchronization tasks
- Scheduled jobs via django-celery-beat for periodic SFTP sync
- Management commands wrapped as Celery tasks for IBEW layer updates

### API Architecture

**RESTful Design:**
- Resource-based endpoints following REST conventions
- GeoJSON FeatureCollection responses for spatial data
- Date filtering via query parameters (`?date=YYYY-MM-DD`)
- Metadata endpoints for available dates and layer configurations

**Key Endpoint Categories:**
1. **Impact Layers:** `/api/affected-population/`, `/api/impacted-gdp/`, etc.
2. **Forecasts:** `/api/merged-deterministic-geojson/`, `/api/geosfm-forecast/`
3. **Administrative:** `/api/admin1/`, `/api/admin2/` for boundaries
4. **Monitoring:** `/api/monitoring-stations/` for station network
5. **Reports:** `/api/station-reports/` for approval workflow
6. **Raster Data:** `/api/raster/` endpoints proxying to TiTiler

**API Documentation:**
- drf-spectacular for OpenAPI 3.0 schema generation
- Swagger UI and ReDoc interfaces at `/api/schema/swagger-ui/` and `/api/schema/redoc/`

### File Organization

**Backend Structure:**
- `Impact/` - Main Django app containing models, views, serializers
- `flood_watch_system/` - Project settings and configuration
- `scripts/` - Utility scripts for data processing (SFTP sync, raster merging)
- `staticfiles/` - Collected static assets for production

**Frontend Structure:**
- `src/components/` - React components
- `src/utils/` - Utility functions
- `src/config/` - Configuration files
- `dist/` - Production build output

**Data Directories:**
- `/mapserver_data/` - Raster data organized by layer type and date
- `/data/` - General data storage (shapefiles, GeoJSON)
- `/merged_alerts/` - Processed alert rasters

## External Dependencies

### Third-Party Services

**ICPAC Flood Forecasting System:**
- **Connection:** SFTP server at 197.254.113.173
- **Data Products:** Hydrological model outputs (Continuum HMC), inundation maps, discharge forecasts
- **Update Frequency:** Daily operational forecasts

**Weather Models:**
- GFS (Global Forecast System) - NOAA global model
- ICON (Icosahedral Nonhydrostatic) - DWD regional model
- Multi-model ensemble approach for forecast uncertainty

### Python Dependencies

**Geospatial Libraries:**
- GDAL/OGR - Raster and vector data processing
- GEOS - Geometric operations
- GeoPandas - Vector data manipulation
- Rasterio - Raster I/O and processing
- Fiona - Vector file I/O

**Web Framework:**
- Django 4.2.11 - Core framework
- djangorestframework - API development
- djangorestframework-gis - GeoJSON serialization
- drf-spectacular - API documentation
- django-cors-headers - CORS handling

**Task Processing:**
- Celery - Asynchronous task queue
- django-celery-beat - Periodic task scheduling

**File Transfer:**
- Paramiko - SSH/SFTP client for remote data access

### JavaScript Dependencies

**Core Libraries:**
- React 19 - UI framework
- React Router DOM - Client-side routing
- Zustand - State management
- TanStack Query - Server state management

**Mapping:**
- Leaflet 1.9.4 - Map visualization
- React-Leaflet 5.0 - React bindings
- MapLibre GL 5.0 - Vector tile rendering
- @turf/turf - Geospatial analysis

**UI Components:**
- @mui/material - Material Design components
- Bootstrap 5.3 - CSS framework
- Recharts - Charting library
- Lucide React - Icon library

**Utilities:**
- date-fns - Date manipulation
- PapaParse - CSV parsing
- html2canvas - Screenshot generation
- jsPDF - PDF generation for reports

### Database

**PostGIS-enabled PostgreSQL:**
- Spatial extensions for geometry storage and operations
- Spatial indexes (GIST) for efficient geographic queries
- Support for multiple geometry types (Point, LineString, Polygon, MultiPolygon)

### Development Tools

**Backend:**
- python-decouple - Environment variable management
- Gunicorn - WSGI HTTP server for production

**Frontend:**
- Vite - Build tool and dev server
- ESLint - Code linting
- TypeScript support (tsconfig present but using JSX)