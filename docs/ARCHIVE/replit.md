# East Africa Flood Watch System

## Overview

The East Africa Flood Watch System is a comprehensive flood monitoring and forecasting platform designed for the IGAD (Intergovernmental Authority on Development) region in East Africa. The system provides real-time flood hazard assessment, impact analysis, and early warning capabilities across multiple countries including Kenya, Ethiopia, Uganda, Tanzania, and Sudan.

**Core Capabilities:**
- Real-time flood monitoring and alerts across East African river basins
- Multi-model hydrological forecasting using GFS and ICON weather models
- Impact assessment for population, infrastructure, crops, livestock, and economic sectors
- River discharge monitoring at 979 stations with geospatial visualization
- Administrative boundary-based impact aggregation (Admin0, Admin1, Admin2 levels)
- Two-stage report approval workflow (Member State → ICPAC)
- Raster data serving for flood extent and alert level maps
- GeoSFM forecast integration with client-side data loading

## User Preferences

- **Communication style**: Simple, everyday language
- **Frontend architecture**: Keep it simple - use Tailwind CSS + MUI, avoid over-engineering
- **Styling approach**: Tailwind utility classes + MUI components instead of complex custom CSS
- **Responsive design**: Fully responsive for mobile devices - sidebars slide in as overlays with backdrop

## System Architecture

### Backend Architecture

**Framework: Django 4.2 with GeoDjango**

The backend uses Django with PostGIS spatial database capabilities to handle complex geospatial queries and flood impact analysis. This combination provides:
- Robust ORM with spatial query support through GeoDjango
- Efficient geometry storage and spatial indexing via PostGIS
- Native support for geographic calculations and spatial relationships

**API Framework: Django REST Framework (DRF) 3.15.2**

All API endpoints are built with DRF, providing:
- GeoJSON serialization through djangorestframework-gis
- OpenAPI 3.0 schema generation via drf-spectacular
- Multiple authentication methods: JWT (primary), Token, Session, OAuth2
- Paginated responses with configurable page size (100 items default)

**Database Design Patterns:**

The system uses abstract base models to ensure consistency:
- `BaseImpactModel`: Common fields for administrative boundaries, impact metrics, and geometry
- `BaseRasterModel`: Timestamp tracking and metadata for raster data (COG format)
- IBEW v1/v2 models: Separate impact assessment versions with polygon geometries
- Report workflow models: Two-stage approval system (Member State → ICPAC)

**Data Processing:**

Flood forecast data is processed daily via:
- SFTP sync from external forecast sources
- Automated merge scripts combining multiple model outputs
- Celery-based task scheduling (12:15 PM UTC daily sync)
- Redis caching for frequently accessed forecast data (1 hour TTL)

**Spatial Data Handling:**

The system uses industry-standard geospatial libraries:
- GDAL/GEOS for geometry operations
- Rasterio for raster data processing (flood maps, alerts)
- GeoPandas for shapefile ingestion and vector operations
- PostGIS for spatial indexing and polygon intersection queries

**Geospatial API Services (eoAPI Stack):**

The system uses modern OGC-compliant FastAPI services for geospatial data:
- **STAC API** (port 8081): Metadata catalog and search (OGC STAC API standard)
- **TiPg** (port 8083): Vector tiles from PostGIS (OGC Features & Tiles API)
- **TiTiler** (port 8000): Raster tiles from Cloud Optimized GeoTIFFs
- **FastAPI** (port 9050): High-performance deterministic forecast data
- **PgSTAC**: PostgreSQL extension for STAC catalog storage

**Legacy Services (Deprecated):**
- MapServer (port 8095) - Commented out, replaced by eoAPI stack
- MapCache (port 8096) - Commented out, replaced by browser-native caching
- Symbology preserved in MAPSERVER_SYMBOLOGY_REFERENCE.md

**Performance Optimization:**

- Async FastAPI services with asyncpg connection pooling
- Vector tiles (MVT) replacing WMS images (10x faster, 90% smaller)
- Browser-native tile caching replacing MapCache
- orjson for faster JSON serialization
- In-memory caching for date availability queries (15 minute TTL)
- Spatial indexes on geometry fields for fast intersection checks

### Frontend Architecture

**Framework: React 19 with Vite**

The frontend uses modern React with Vite build tooling for:
- Fast hot module replacement during development
- Optimized production builds with code splitting
- Component-based architecture for complex map interactions

**Mapping Libraries:**

- Leaflet 1.9.4 with react-leaflet for base map functionality
- Leaflet.markercluster for station clustering at high zoom levels
- Turf.js for client-side geospatial calculations
- MapLibre GL for future vector tile support

**State Management:**

- Zustand for lightweight global state (layer visibility, date selection)
- TanStack React Query for server state management and caching
- Custom hooks for data fetching (useForecastData, useAvailableDates, useGeoSFMData)

**Data Flow Pattern:**

```
User Action → State Update → Custom Hook → API Call → Cache Check → Response → UI Update
```

**Component Structure:**

The application follows a modular component architecture:
- Page components (MapViewer, HomePage, Reports, Partners)
- Map layer components (MonitoringStationsLayer, GeoSFMLayer)
- Custom hooks for data fetching and state management
- Utility functions for caching and coordinate transformations

**MapViewer Refactoring (In Progress - November 2025):**

The MapViewer.jsx component (3,260 lines) is being refactored into maintainable, reusable components using a feature-based architecture:

*Folder Structure:*
```
frontend/src/features/map-viewer/
├── components/          # UI components
│   ├── layout/          # MapViewerShell, SidebarLayout, PanelsLayout
│   ├── map/             # MapCanvas, DynamicLayersGroup, MapLegends, PopupContent
│   ├── sidebar/         # FiltersSection, LayerGroups, MonitoringStationsSection
│   ├── panels/          # StationDetailsPanel, ForecastChartsPanel
│   ├── overlays/        # AlertLegend, MetadataTriggers
│   └── modals/          # MetadataModal, ErrorDialogs
├── context/             # MapViewerContext - centralized state management
├── hooks/               # Custom hooks (useMapLayers, useMapDates, useMapFilters)
├── services/            # API calls and data fetching
├── config/              # Layer definitions, cluster settings, animations
└── utils/               # Popup generation, data transforms, helpers
```

*State Management:*
- MapViewerContext consolidates 45+ useState calls into organized slices
- Reducer pattern with typed actions for predictable state updates
- Slice-based hooks (useMapLayers, useMapDates, useMapFilters) for granular access
- Immutable Set instances for layer selections

*Component Size Targets:*
- Main orchestrator (MapViewerShell): ~150 lines
- Major components: 200-300 lines
- Utility modules: ~100 lines

*Migration Status (5/11 tasks complete):*
✅ Folder structure created  
✅ MapViewerContext with state/actions  
✅ Configuration files (cluster, animations)  
✅ Utility functions (popups, data transforms)  
✅ MapViewerShell orchestrator  
⏳ Extract sidebar components  
⏳ Extract map components  
⏳ Extract panel components  
⏳ Wire new components into shell  
⏳ Remove old MapViewer.jsx  
⏳ Integration testing

**CSS Architecture (Simplified with Tailwind + MUI):**

The frontend uses a hybrid approach for styling:
- **Tailwind CSS**: Utility-first CSS framework for rapid styling and layout
- **Material-UI (MUI)**: Pre-built React components (AppBar, Drawer, DatePicker, etc.)
- **Custom CSS modules**: Legacy modular CSS files (being gradually migrated to Tailwind)

CSS files organized by functionality:
- base.css: Foundation and layout
- navbar.css: Top navigation
- sidebar.css: Control panel and filters
- map.css: Map container and Leaflet overrides
- legends.css: Legend components
- modals.css: Dialog windows
- charts.css: Chart visualizations

Material-UI (MUI) is used for consistent UI components (AppBar, Drawer, Tabs, Modals).

### Authentication and Security

**Multi-Method Authentication:**

The system supports multiple authentication methods for different use cases:
- JWT tokens (primary) via djangorestframework-simplejwt
- Token authentication for API clients
- Session authentication for admin interface
- OAuth2 (Google) for future SSO integration

**Security Measures:**

- CORS configuration restricting allowed origins
- CSRF protection with trusted origins whitelist
- Environment-based secret key management
- Basic HTTP auth for staging environment access
- API endpoint protection middleware (currently disabled for testing)

**User Roles:**

- Superuser: Full system administration
- Member State Admins: Country-specific data management
- ICPAC Reviewers: Final approval authority for reports

### Async Processing

**Celery Task Queue:**

Background tasks are managed through Celery with Redis broker:
- Daily forecast data sync (12:15 PM UTC)
- Shapefile processing and geometry validation
- Report generation with chart rendering
- Email notifications for approvals

**Beat Schedule:**

Automated tasks run on cron-like schedules:
- FloodProofs sync: Daily at 12:15 PM
- GeoSFM data check: Daily at 12:30 PM
- Database cleanup: Weekly on Sundays

### Report Workflow

**Two-Stage Approval Process:**

1. **Member State Review**: National focal points review and approve station reports
2. **ICPAC Approval**: Regional reviewers provide final approval

**Report Types:**

- Station flood reports with discharge time series
- Impact assessments with affected population/infrastructure
- Saved reports with PDF generation capability

**PDF Generation:**

Reports are generated using ReportLab with:
- Dynamic chart rendering via matplotlib
- Administrative boundary metadata
- Time series discharge graphs
- Approval signatures and timestamps

## External Dependencies

### Third-Party Services

**Google Cloud Storage (GCS):**
- Purpose: GeoSFM forecast data storage
- Access: Signed URLs with 15-minute expiration
- Data Format: JSON shapefiles organized by YYYY/MM/DD
- Client-side download: Frontend fetches directly from GCS

**SFTP Server:**
- Purpose: FloodProofs deterministic forecast data
- Sync Schedule: Daily at 12:00 UTC
- Data Format: GeoJSON files merged on server
- Storage: Local filesystem under /data/floodproofs/

**TiTiler (Port 8000):**
- Purpose: Cloud-Optimized GeoTIFF (COG) tile serving
- Endpoints: /cog/tiles, /cog/info, /cog/statistics
- Data Types: Inundation maps, alert levels, flood hazards
- Performance: Direct raster tile serving without MapServer

### Database

**PostgreSQL 16 with PostGIS 3.4:**
- Spatial queries and geometry operations
- GIST indexes for fast spatial lookups
- JSON fields for time series storage
- Async connection pooling via asyncpg

**Redis 7:**
- Celery message broker
- API response caching (1 hour for forecasts, 15 min for dates)
- Session storage

### API Integrations

**MapServer (Port 8093):**
- WMS layer serving for historical compatibility
- Configured via .map files in /mapserver directory
- Gradually being replaced by TiTiler for raster data

**Internal Services:**

- FastAPI service (port 9050): High-performance deterministic data endpoint
- Django backend (port 8090): Primary REST API
- Frontend dev server (port 5173): Vite HMR during development
- Nginx proxy: Production reverse proxy and static file serving

### Key Python Libraries

**Geospatial:**
- GeoPandas 1.0.1: Vector data processing
- Rasterio 1.4.3: Raster manipulation
- Shapely 2.0.6: Geometry operations
- GDAL 3.9.3: Format conversions

**API & Web:**
- Django 4.2.25: Web framework
- djangorestframework 3.15.2: REST API
- FastAPI 0.115.0: High-performance endpoints
- drf-spectacular 0.28.0: OpenAPI documentation

**Task Processing:**
- Celery 5.4.0: Distributed task queue
- django-celery-beat 2.7.0: Periodic task scheduler
- Paramiko 3.5.0: SFTP client

**Performance:**
- asyncpg 0.29.0: Async PostgreSQL driver
- orjson 3.10.7: Fast JSON serialization
- django-redis 5.4.0: Redis cache backend

### Key JavaScript Libraries

**React Ecosystem:**
- React 19.0.0: UI framework
- react-router-dom 7.9.3: Client-side routing
- @tanstack/react-query 5.90.2: Server state management

**Mapping:**
- Leaflet 1.9.4: Map rendering
- react-leaflet 5.0.0: React bindings
- leaflet.markercluster 1.5.3: Station clustering
- @turf/turf 7.2.0: Spatial analysis

**UI Components:**
- @mui/material 7.3.4: Component library
- @mui/icons-material 7.3.4: Icon set
- recharts 2.15.1: Chart visualization
- framer-motion 12.23.22: Animations

**Utilities:**
- date-fns 4.1.0: Date manipulation
- zustand 5.0.8: State management
- papaparse 5.5.2: CSV parsing