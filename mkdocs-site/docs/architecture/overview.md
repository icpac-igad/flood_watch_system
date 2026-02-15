# System Architecture

## Design Principles

FloodWatch follows a **microservices architecture** where each component is independently deployable, scalable, and maintainable. The system is fully containerized using Docker Compose, enabling consistent deployment across development, staging, and production environments.

**Core design decisions:**

- **Separation of concerns** — Data ingestion, storage, API, rendering, and presentation are independent services
- **OGC compliance** — Map services follow Open Geospatial Consortium standards (WMS, WCS, vector tiles)
- **Spatial-first** — PostGIS powers all geospatial queries, with server-side clustering for performance at scale
- **Real-time capable** — Automated ingestion pipelines keep forecast data current with minimal latency

## High-Level Architecture

```mermaid
graph TB
    subgraph External Sources
        HYDRO[GeoSFM / MIKE / FloodPROOFS<br/>Hydrological Forecasts]
        WRF[WRF Model<br/>Rainfall Predictions]
        SAT[Satellite<br/>Flood Extent]
        FTP[SFTP / FTP<br/>Data Feeds]
    end

    subgraph Ingestion Layer
        JOBS[Scheduled Jobs<br/><i>Python cron tasks</i>]
    end

    subgraph Data Layer
        DB[(PostgreSQL / PostGIS<br/><i>Spatial database</i>)]
        PGBOUNCER[PgBouncer<br/><i>Connection pooling</i>]
    end

    subgraph Application Layer
        CMS[GeoManager CMS<br/><i>Django + Wagtail</i>]
        API[FloodWatch API<br/><i>FastAPI</i>]
    end

    subgraph Map Rendering Layer
        MAPSERVER[MapServer<br/><i>WMS raster tiles</i>]
        MAPCACHE[MapCache<br/><i>Tile caching</i>]
        TILESERV[pg_tileserv<br/><i>Vector tiles</i>]
    end

    subgraph Presentation Layer
        VIEWER[Map Viewer<br/><i>Next.js + MapLibre GL</i>]
    end

    subgraph Gateway
        NGINX[Nginx<br/><i>Reverse proxy</i>]
    end

    HYDRO --> JOBS
    WRF --> JOBS
    FTP --> JOBS
    SAT --> CMS

    JOBS --> DB
    CMS --> DB
    DB --> PGBOUNCER
    PGBOUNCER --> API
    PGBOUNCER --> TILESERV
    DB --> MAPSERVER
    MAPSERVER --> MAPCACHE

    API --> NGINX
    MAPCACHE --> NGINX
    TILESERV --> NGINX
    CMS --> NGINX
    VIEWER --> NGINX

    NGINX --> USERS[End Users<br/><i>Forecasters, Agencies, Public</i>]
```

## Data Flow

### 1. Ingestion Pipeline

External data sources deliver forecast and observation data via scheduled transfers:

```mermaid
sequenceDiagram
    participant Source as External Source
    participant Jobs as Ingestion Jobs
    participant DB as PostGIS Database
    participant CMS as GeoManager CMS

    Source->>Jobs: Hydrological forecasts (FTP/SFTP)
    Source->>Jobs: WRF rainfall (SFTP)
    Source->>CMS: Satellite imagery (upload)

    Jobs->>DB: Parse, validate, and load forecast data
    Jobs->>DB: Update multimodal_forecast table
    CMS->>DB: Register raster layers (COG format)

    Note over DB: ~5.6M forecast rows<br/>3,199 control points
```

### 2. Request Flow

When a user interacts with the map viewer:

```mermaid
sequenceDiagram
    participant User as End User
    participant Nginx as Nginx Gateway
    participant Viewer as Map Viewer
    participant API as FastAPI
    participant Tiles as Map Services
    participant DB as PostGIS

    User->>Nginx: Open FloodWatch
    Nginx->>Viewer: Serve application
    Viewer->>Nginx: Request vector tiles
    Nginx->>Tiles: pg_tileserv query
    Tiles->>DB: Clustered point query
    DB-->>Tiles: GeoJSON features
    Tiles-->>Viewer: Vector tiles (MVT)

    Viewer->>Nginx: Request forecast chart
    Nginx->>API: /api/v1/multimodal/timeseries
    API->>DB: Query forecast data
    DB-->>API: Time series results
    API-->>Viewer: JSON response
```

## Component Overview

### Frontend — Map Viewer
The web interface built with **Next.js** and **MapLibre GL JS**. Renders an interactive map with vector tiles (control points with clustering), raster overlays (flood extents, rainfall), and analytical widgets (time series charts, impact summaries).

### API — FastAPI Service
High-performance REST API serving flood data as JSON and GeoJSON. Provides endpoints for regional summaries, time series forecasts, alert statistics, risk assessments, and expert impact assessments. Auto-generates OpenAPI documentation.

### CMS — GeoManager
**[GeoManager](../geomanager/index.md)** is a Wagtail-based Django application for geospatial data management. Administrators use it to configure map layers, manage raster/vector datasets, set up automated data watchers, and style layer visualizations.

### Map Services
Three specialized services handle different tile formats:

- **MapServer** — Renders raster data (flood extents, rainfall grids) as WMS tiles
- **MapCache** — Caches rendered tiles for performance
- **pg_tileserv** — Serves vector tiles directly from PostGIS with server-side clustering

### Database — PostgreSQL/PostGIS
Central data store with two primary schemas:

- **`gha`** — Spatial operational data (control points, forecasts, admin boundaries)
- **`cms`** — Application data (CMS pages, layer configurations, user data)

### Ingestion — Scheduled Jobs
Python-based cron jobs that synchronize data from external sources:

- GeoSFM, MIKE, FloodPROOFS discharge forecasts
- WRF weather model rainfall predictions
- Google Flood Forecasts
- Satellite-derived flood extent observations

## Alert Classification

The system uses a three-tier alert classification based on river discharge thresholds:

```mermaid
graph LR
    subgraph Discharge Thresholds
        NORMAL[Normal<br/>&lt; 300 m³/s] --> WARNING[Warning<br/>≥ 300 m³/s]
        WARNING --> ALARM[Alarm<br/>≥ 500 m³/s]
        ALARM --> EMERGENCY[Emergency<br/>≥ 750 m³/s]
    end

    style NORMAL fill:#4CAF50,color:#fff
    style WARNING fill:#FF9800,color:#fff
    style ALARM fill:#f44336,color:#fff
    style EMERGENCY fill:#9C27B0,color:#fff
```

These thresholds are applied consistently across the API, map visualization, and alerting systems.
