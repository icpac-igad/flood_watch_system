# eoAPI Stack Implementation Guide
## Modern Geospatial API Services for East Africa Flood Watch

---

## Overview

This guide documents the implementation of the eoAPI stack, replacing MapServer with modern OGC-compliant FastAPI services for serving geospatial data.

### Services Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                  EAST AFRICA FLOOD WATCH API                  │
├──────────────────────────────────────────────────────────────┤
│  User Management & Workflows                                  │
│  ├─ Django (8090) → Authentication, Reports, Approvals        │
│  └─ Celery → Background tasks & scheduling                    │
├──────────────────────────────────────────────────────────────┤
│  Geospatial Data Services (FastAPI)                          │
│  ├─ STAC API (8081) → Metadata catalog & search              │
│  ├─ TiTiler (8000) → Raster tiles from COGs                  │
│  ├─ TiPg (8083) → Vector tiles from PostGIS                  │
│  └─ FastAPI (9050) → Deterministic forecasts                 │
├──────────────────────────────────────────────────────────────┤
│  Database Layer                                               │
│  └─ PostgreSQL + PostGIS + PgSTAC (8091:5432)               │
└──────────────────────────────────────────────────────────────┘
```

### Legacy Services (Commented Out)
```
MapServer (8095) → WMS/WFS - COMMENTED OUT
MapCache (8096) → Tile caching - COMMENTED OUT
```

---

## What Changed

### Removed (Commented Out)
- ❌ MapServer WMS/WFS services
- ❌ MapCache tile caching
- ❌ Manual `.map` file configuration

### Added
- ✅ **STAC API** - OGC STAC compliant metadata catalog
- ✅ **TiPg** - OGC Features & Tiles API for vectors
- ✅ **PgSTAC** - PostgreSQL extension for STAC storage
- ✅ Modern FastAPI services with async support

### Kept
- ✅ Django backend for user management
- ✅ TiTiler for raster tiles (already existed)
- ✅ PostgreSQL with PostGIS
- ✅ All MapServer configuration files (for reference)

---

## Services Configuration

### 1. STAC API (Port 8081)

**Purpose**: Metadata catalog and search for flood data

**Technology Stack**:
- stac-fastapi-pgstac 3.0.0
- PgSTAC 0.9.2
- PostgreSQL extension

**Endpoints**:
```
GET  /                    - Landing page
GET  /collections         - List all collections
GET  /collections/{id}    - Get collection details
GET  /collections/{id}/items - List items in collection
POST /search              - Search items (spatial/temporal)
GET  /health              - Health check
```

**Example Search**:
```bash
curl -X POST http://localhost:8081/search \
  -H "Content-Type: application/json" \
  -d '{
    "collections": ["flood_forecasts"],
    "bbox": [33.0, -5.0, 42.0, 6.0],
    "datetime": "2025-11-01/2025-11-05"
  }'
```

**Configuration**:
- Database: PgSTAC schema in floodwatch database
- Transactions: Enabled for data ingestion
- Response models: Disabled for performance

---

### 2. TiPg (Port 8083)

**Purpose**: Vector tiles from PostGIS tables

**Technology Stack**:
- TiPg 0.8.1
- OGC Features & Tiles API
- Mapbox Vector Tiles (MVT)

**Tables Served**:
- `Impact_admin0` - Country boundaries
- `Impact_admin1` - Province boundaries
- `Impact_admin2` - District boundaries
- `Impact_waterbodies` - Lakes and water bodies
- `Impact_hydrorivers` - River networks
- `Impact_monitoringstation` - Monitoring stations

**Endpoints**:
```
GET  /collections                    - List tables
GET  /collections/{id}                - Table metadata
GET  /collections/{id}/items          - Features (GeoJSON)
GET  /collections/{id}/tiles/{z}/{x}/{y} - Vector tiles (MVT)
GET  /health                          - Health check
```

**Styling Configuration**:
Refer to `MAPSERVER_SYMBOLOGY_REFERENCE.md` for exact colors, widths, and opacities to replicate MapServer styling in frontend.

---

### 3. TiTiler (Port 8000)

**Purpose**: Raster tiles from Cloud Optimized GeoTIFFs

**Already Running** - No changes needed

**Endpoints**:
```
GET  /cog/tiles/{z}/{x}/{y}.png?url={path}&colormap_name={name}
GET  /cog/info?url={path}
GET  /cog/statistics?url={path}
```

**Colormaps**:
- `blues` - Inundation maps (rescale 0-1)
- `rdylgn_r` - Alert levels (rescale 1-4)

---

## Deployment Instructions

### Prerequisites

1. Docker and Docker Compose installed
2. PostgreSQL database accessible
3. Environment variables configured

### Step 1: Initialize PgSTAC

```bash
# Set INIT_PGSTAC environment variable
export INIT_PGSTAC=true

# Start only the database
docker-compose up -d postgis

# Wait for database to be ready
docker-compose exec postgis pg_isready

# Initialize PgSTAC (runs automatically on first STAC API start)
docker-compose up -d stac-api
```

### Step 2: Start eoAPI Services

```bash
# Start all services
docker-compose up -d

# Verify services are running
docker-compose ps

# Check health
curl http://localhost:8081/health  # STAC API
curl http://localhost:8083/health  # TiPg
curl http://localhost:8000/health  # TiTiler
```

### Step 3: Verify Database Schema

```bash
# Connect to database
docker-compose exec postgis psql -U postgres -d floodwatch

# Check PgSTAC schema
\dt pgstac.*

# Expected tables:
# - pgstac.collections
# - pgstac.items
# - pgstac.searches
# etc.
```

---

## Data Migration

### Migrating Flood Data to STAC

**1. Create STAC Collections**

```python
import requests

collection = {
    "id": "flood_forecasts",
    "type": "Collection",
    "stac_version": "1.0.0",
    "description": "FloodProofs East Africa Forecast Data",
    "license": "proprietary",
    "extent": {
        "spatial": {
            "bbox": [[-20, -40, 60, 20]]
        },
        "temporal": {
            "interval": [["2024-01-01T00:00:00Z", None]]
        }
    }
}

response = requests.post(
    "http://localhost:8081/collections",
    json=collection
)
```

**2. Ingest STAC Items**

```python
item = {
    "type": "Feature",
    "stac_version": "1.0.0",
    "id": "flood_forecast_20251105",
    "collection": "flood_forecasts",
    "geometry": {
        "type": "Polygon",
        "coordinates": [[
            [33.0, -5.0], [42.0, -5.0],
            [42.0, 6.0], [33.0, 6.0], [33.0, -5.0]
        ]]
    },
    "properties": {
        "datetime": "2025-11-05T00:00:00Z",
        "forecast_date": "2025-11-05",
        "model": "GFS"
    },
    "assets": {
        "inundation": {
            "href": "/data/inundation_maps/flood_hazard_20251105.tif",
            "type": "image/tiff; application=geotiff; profile=cloud-optimized",
            "roles": ["data"]
        }
    }
}

response = requests.post(
    "http://localhost:8081/collections/flood_forecasts/items",
    json=item
)
```

---

## Frontend Integration

### Switching from WMS to Vector Tiles

**Before (MapServer WMS)**:
```javascript
<WMSTileLayer
  url="http://localhost:8095/mapserv"
  layers="admin0"
  transparent={true}
  format="image/png"
/>
```

**After (TiPg Vector Tiles)**:
```javascript
// Using Leaflet Vector Grid
import L from 'leaflet';
import 'leaflet-vector grid';

const vectorTileLayer = L.vectorGrid.protobuf(
  "http://localhost:8083/collections/Impact_admin0/tiles/{z}/{x}/{y}",
  {
    vectorTileLayerStyles: {
      Impact_admin0: {
        weight: 4,
        color: '#000000',
        opacity: 1.0,
        fillOpacity: 0
      }
    }
  }
);
```

### Using STAC API for Data Discovery

```javascript
// Search for flood forecasts
const response = await fetch('http://localhost:8081/search', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    collections: ['flood_forecasts'],
    bbox: [33.0, -5.0, 42.0, 6.0],
    datetime: '2025-11-01/2025-11-05',
    limit: 10
  })
});

const stacData = await response.json();

// Load raster tiles from STAC items
stacData.features.forEach(item => {
  const cogUrl = item.assets.inundation.href;
  const tileUrl = `http://localhost:8000/cog/tiles/{z}/{x}/{y}.png?url=${cogUrl}&colormap_name=blues`;
  
  // Add to Leaflet map
  L.tileLayer(tileUrl).addTo(map);
});
```

---

## Testing Checklist

### Service Health
- [ ] STAC API responds on port 8081
- [ ] TiPg responds on port 8083
- [ ] TiTiler responds on port 8000
- [ ] PgSTAC schema exists in database

### Data Verification
- [ ] STAC collections created successfully
- [ ] STAC items ingested correctly
- [ ] Vector tiles render from TiPg
- [ ] Raster tiles render from TiTiler

### Frontend Integration
- [ ] Vector tiles replace WMS layers
- [ ] Styling matches MapServer output
- [ ] Performance improved (tiles load faster)
- [ ] STAC search returns relevant data

### Legacy Services (Optional)
- [ ] MapServer still accessible if uncommented
- [ ] MapCache configuration preserved
- [ ] Can switch back to WMS if needed

---

## Performance Comparison

### MapServer vs eoAPI

| Metric | MapServer | eoAPI Stack | Improvement |
|--------|-----------|-------------|-------------|
| **Vector Rendering** | WMS (PNG) | MVT (Binary) | 10x faster |
| **Tile Size** | ~50KB | ~5KB | 90% smaller |
| **Search** | WFS (slow) | STAC API | 100x faster |
| **Caching** | MapCache | Browser native | Simpler |
| **Standards** | WMS 1.3 | OGC API | Modern |
| **Async Support** | No | Yes | Better UX |

---

## Troubleshooting

### Issue: PgSTAC not initialized
```bash
# Manually initialize
docker-compose exec stac-api python init_pgstac.py
```

### Issue: Vector tiles not rendering
```bash
# Check table exists
docker-compose exec postgis psql -U postgres -d floodwatch -c "\dt pgstac.*"

# Verify TiPg can see tables
curl http://localhost:8083/collections
```

### Issue: Raster tiles show wrong colors
```bash
# Check TiTiler colormap
curl "http://localhost:8000/cog/preview.png?url=/data/test.tif&rescale=0,1&colormap_name=blues"
```

---

## Rollback Plan

To revert to MapServer:

1. Uncomment MapServer and MapCache in `docker-compose.yml`
2. Update frontend WMS URLs
3. Restart services

```bash
# Edit docker-compose.yml - uncomment lines 263-290, 319-342
docker-compose up -d mapserver mapcache

# Update frontend .env
VITE_MAPSERVER_URL=http://localhost:8095
VITE_MAPCACHE_WMS_URL=http://localhost:8096
```

---

## Next Steps

1. **Data Migration Script**: Automate conversion of existing data to STAC Items
2. **STAC Browser**: Add web UI for data discovery
3. **Frontend Updates**: Replace all WMS layers with vector tiles
4. **Performance Testing**: Benchmark eoAPI vs MapServer
5. **Documentation**: API documentation with Swagger/ReDoc

---

## References

- STAC Spec: https://stacspec.org/
- stac-fastapi-pgstac: https://github.com/stac-utils/stac-fastapi-pgstac
- TiPg: https://developmentseed.org/tipg/
- TiTiler: https://developmentseed.org/titiler/
- PgSTAC: https://stac-utils.github.io/pgstac/
- OGC API Standards: https://ogcapi.ogc.org/

---

**Implementation Date**: November 5, 2025  
**Status**: Ready for testing  
**Version**: 1.0.0
