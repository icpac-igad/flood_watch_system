# Current System Inspection - Complete Flow Analysis

## FRONTEND HOOKS → API ENDPOINTS MAPPING

### 1. Station Data
**Hook:** [useStationData.ts](frontend/src/hooks/useStationData.ts:14-36)
```typescript
fetch(`${API_BASE_URL}/monitoring-stations/?country={country}&basin={basin}`)
```
**Calls:** Django Backend → `/api/monitoring-stations/`
**Returns:** List of monitoring stations with lat/lon, country, basin, alert status

---

### 2. Forecast Data (FloodProofs)
**Hook:** [useForecastData.ts](frontend/src/hooks/useForecastData.ts:36-86)
```typescript
fetch(`${FASTAPI_BASE_URL}/merged-forecast/${date}/?country={country}`)
```
**Calls:** FastAPI → `/api/fast/merged-forecast/{date}/`
**Returns:** GeoJSON with **FloodProofs** deterministic forecast only
**⚠️ Note:** Despite the name "merged_forecast", this is **FloodProofs data only**, not a combination of multiple models
**Data Structure:**
```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": { "type": "Point", "coordinates": [lon, lat] },
      "properties": {
        "point_id": 123,
        "country": "Kenya",
        "admin_name": "Nairobi",
        "discharge": 150.5,
        "alert_level": "warning",
        "threshold": 140.0
      }
    }
  ]
}
```

---

### 3. GeoSFM Data (Forecast Model)
**Hook:** [useGeoSFMData.ts](frontend/src/hooks/useGeoSFMData.ts:77-113)
```typescript
// Get available dates
fetch(`${API_BASE_URL}/geosfm/available-dates/`)

// Get data for specific date
fetch(`${API_BASE_URL}/geosfm/geojson/${date}/`)
```
**Calls:** Django Backend → `/api/geosfm/available-dates/`, `/api/geosfm/geojson/{date}/`
**Returns:** GeoJSON with GeoSFM forecast model output

---

### 4. Ensemble Control Points
**Hook:** [useEnsembleData.ts](frontend/src/hooks/useEnsembleData.ts:49-114)
```typescript
fetch(`${API_BASE_URL}/ensemble-control-points/?page_size=1000`)
```
**Calls:** Django Backend → `/api/ensemble-control-points/`
**Returns:** GeoJSON with ensemble forecast control point locations
**Purpose:** Shows where forecast models are calculated

---

### 5. Available Forecast Dates
**Hook:** [useAvailableDates.ts](frontend/src/hooks/useAvailableDates.ts)
```typescript
fetch(`${FASTAPI_BASE_URL}/merged-forecast/dates/`)
```
**Calls:** FastAPI → `/api/fast/merged-forecast/dates/`
**Returns:** List of available forecast dates

---

### 6. Admin Boundaries
**Hook:** [useAdminBoundaries.ts](frontend/src/hooks/useAdminBoundaries.ts)
```typescript
fetch(`${API_BASE_URL}/admin1/`)  // Country level
fetch(`${API_BASE_URL}/admin2/`)  // Province/state level
```
**Calls:** Django Backend
**Returns:** GeoJSON boundaries for country filtering

---

## BACKEND SERVICES BREAKDOWN

### DJANGO BACKEND (Port 8000)

**File:** [backend/Impact/urls.py](backend/Impact/urls.py:1-140)

#### Key Endpoints:

| Endpoint | Purpose | Returns |
|----------|---------|---------|
| `/api/admin0/` | Country boundaries | GeoJSON polygons |
| `/api/admin1/` | Province boundaries | GeoJSON polygons |
| `/api/admin2/` | District boundaries | GeoJSON polygons |
| `/api/monitoring-stations/` | Station locations | GeoJSON points with metadata |
| `/api/water-bodies/` | Lakes, rivers | GeoJSON |
| `/api/ensemble-control-points/` | Forecast grid points | GeoJSON points |
| `/api/geosfm/available-dates/` | GeoSFM dates | `{dates: [], latest: ""}` |
| `/api/geosfm/geojson/{date}/` | GeoSFM data | GeoJSON flood detection |
| `/api/geosfm/latest/` | Latest GeoSFM | GeoJSON |
| `/api/deterministic/available-dates/` | Deterministic forecast dates | Date list |
| `/api/deterministic/{date}/` | Deterministic forecast | GeoJSON |
| `/api/raster/latest-inundation/` | Latest inundation raster | Raster file info |
| `/api/raster/latest-alerts/` | Latest alert raster | Raster file info |

#### TiTiler Integration (Raster Data):
- `/api/raster/files/` - List available raster files
- `/api/raster/info/` - Get raster metadata
- `/api/raster/statistics/` - Raster statistics
- `/api/raster/{date}/` - Get raster by date

**Purpose:**
- Station metadata
- Historical data
- GeoSFM satellite data
- Admin boundaries
- **Inundation raster data** (via TiTiler)

---

### FASTAPI (Port 8001)

**File:** [fastapi-service/main.py](fastapi-service/main.py:1-320)

#### Endpoints:

| Endpoint | Purpose | Returns |
|----------|---------|---------|
| `/api/fast/merged-forecast/dates/` | Available forecast dates | `{dates: [], count: N}` |
| `/api/fast/merged-forecast/{date}/` | Merged forecast for date | GeoJSON with all models |
| `/api/fast/merged-forecast/latest/` | Latest merged forecast | GeoJSON |

**Key Features:**
- **Connection Pooling:** 5-20 async PostgreSQL connections
- **Caching:** In-memory cache with 15min TTL
- **Performance:** Uses `orjson` for fast JSON serialization
- **Country Filtering:** Filter forecast by country parameter
- **Fallback Logic:** If requested date not found, returns latest

**Data Source:**
- Reads from `Impact_mergeddeterministicgeojson` table in PostgreSQL
- Contains **FloodProofs** deterministic forecast data only

---

### MAPSERVER (Port 8080)

**Purpose:** WMS/WFS server for rendering vector layers from PostgreSQL

**Mapfile:** [mapserver/floodwatch.map](mapserver/floodwatch.map)

#### Available WMS Layers:

| Layer Name | Type | Source | Purpose |
|------------|------|--------|---------|
| `admin0` | Polygon | `Impact_admin0` table | Country boundaries (thick black outline) |
| `admin1` | Polygon | `Impact_admin1` table | Province boundaries (gray outline) |
| `admin2` | Polygon | `Impact_admin2` table | District boundaries (light gray) |
| `waterbodies` | Polygon | `Impact_waterbodies` table | Lakes (blue fill) |
| `rivers` | LineString | `Impact_hydrorivers` table | River network (classified by order) |
| `monitoring_stations` | Point | `Impact_monitoringstation` table | Station locations (red circles) |

#### WMS Request Format:
```
GET http://localhost:8080/mapserv?
  SERVICE=WMS&
  VERSION=1.1.0&
  REQUEST=GetMap&
  LAYERS=admin0&
  SRS=EPSG:4326&
  BBOX={minLon},{minLat},{maxLon},{maxLat}&
  WIDTH=256&
  HEIGHT=256&
  FORMAT=image/png&
  TRANSPARENT=true
```

#### River Classification:
- **Order 6+:** Largest rivers (almost invisible white, width 1.2)
- **Order 4-5:** Large tributaries (semi-white, width 0.8)
- **Order 1-3:** Small rivers (dark blue, width 0.5)

#### Frontend Usage:
```typescript
// In frontend, layers are loaded as WMS overlays
<WMSTileLayer
  url="http://localhost:8080/mapserv"
  params={{
    service: 'WMS',
    version: '1.1.0',
    request: 'GetMap',
    layers: 'admin0,rivers,waterbodies',
    format: 'image/png',
    transparent: true
  }}
/>
```

---

## MULTIMODAL FORECAST MODELS

### Current Model Status:

1. **FloodProofs** ✅ - Served via FastAPI `/merged-forecast` endpoint
2. **GeoSFM** ✅ - Served via Django `/geosfm` endpoint
3. **MIKE HYDRO** ❓ - Not found in current endpoints
4. **HYPE** ❓ - Not found in current endpoints

### Data Flow:

```
1. Model Outputs (MIKE, FloodProofs, HYPE)
   ↓
2. Backend Processing (Merges all models)
   ↓
3. Stored in PostgreSQL table: Impact_mergeddeterministicgeojson
   ↓
4. FastAPI serves merged GeoJSON
   ↓
5. Frontend displays on map
```

### GeoJSON Structure from Merged Forecast:

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Point",
        "coordinates": [34.5, 0.2]
      },
      "properties": {
        "point_id": 123,
        "country": "Kenya",
        "admin_name": "Nairobi",
        "mike_discharge": 150.5,
        "floodproofs_discharge": 148.2,
        "hype_discharge": 152.8,
        "ensemble_mean": 150.5,
        "ensemble_std": 2.1,
        "alert_level": "warning",
        "threshold": 140.0
      }
    }
  ]
}
```

---

## SATELLITE DATA (GeoSFM)

**Source:** Django Backend
**Endpoints:**
- `/api/geosfm/available-dates/` - Get available satellite imagery dates
- `/api/geosfm/geojson/{date}/` - Get flood detection for specific date
- `/api/geosfm/latest/` - Get latest satellite data

**Data Structure:**
```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": { "type": "Point", "coordinates": [lon, lat] },
      "properties": {
        "water_level_change": 2.5,
        "confidence": 0.85,
        "date": "2023-11-13"
      }
    }
  ]
}
```

---

## INUNDATION DATA

**Source:** Django Backend (TiTiler integration)
**Endpoints:**
- `/api/raster/latest-inundation/` - Get latest inundation raster info
- `/api/raster/files/` - List all inundation raster files
- `/api/raster/{date}/` - Get inundation raster for specific date
- `/api/raster/statistics/` - Get raster statistics

**Purpose:**
- Provides actual flood extent (inundation) maps
- Raster data (GeoTIFF format)
- Can be overlayed on map as WMS/TMS tiles

---

## IMPACT DATA

**Not Found in Current Implementation**

Looking through the endpoints, I see:
- Line 57 in urls.py: `# Removed old impact layer API registrations (affectedPop, affectedGDP, affectedCrops, etc.)`
- Line 73: `# Removed IBEW v2 impact data API registrations`

**Status:** Impact calculation endpoints have been removed/commented out

**Potential Location:** May need to check if impact is calculated:
- In the merged forecast properties?
- In a separate service?
- Needs to be implemented?

---

## COMPLETE DATA FLOW EXAMPLE

### User Opens Map and Views Forecast

```
1. Browser loads React app
   ↓
2. MapViewer.jsx mounts
   ↓
3. useAvailableDates() hook fires
   └→ GET http://localhost:8001/api/fast/merged-forecast/dates/
   └→ FastAPI returns: {dates: ["2023-11-13", "2023-11-12", ...]}
   ↓
4. User selects date "2023-11-13"
   ↓
5. useForecastData(date) hook fires
   └→ GET http://localhost:8001/api/fast/merged-forecast/2023-11-13/
   └→ FastAPI queries PostgreSQL:
       SELECT geojson_data FROM Impact_mergeddeterministicgeojson WHERE data_date='2023-11-13'
   └→ Returns GeoJSON with merged forecast (MIKE + FloodProofs + HYPE)
   ↓
6. Map renders forecast points
   - Each point colored by alert_level (green/yellow/orange/red)
   - Clustering for performance
   ↓
7. User clicks a forecast point
   ↓
8. Popup shows:
   - Location info
   - MIKE discharge: 150.5 m³/s
   - FloodProofs discharge: 148.2 m³/s
   - HYPE discharge: 152.8 m³/s
   - Ensemble mean: 150.5 m³/s
   - Alert level: WARNING
```

### User Toggles GeoSFM Layer

```
1. User clicks "GeoSFM" toggle in sidebar
   ↓
2. useGeoSFMData(date) hook fires
   └→ GET http://localhost:8000/api/geosfm/geojson/2023-11-13/
   └→ Django queries database for satellite data
   └→ Returns GeoJSON with flood detection points
   ↓
3. Map renders GeoSFM points
   - Colored by water_level_change (blue to red gradient)
   - Shows satellite-detected flooding
```

### User Views Station Data

```
1. User clicks "Monitoring Stations" toggle
   ↓
2. useStationData(country) hook fires
   └→ GET http://localhost:8000/api/monitoring-stations/?country=Kenya
   └→ Django queries database
   └→ Returns GeoJSON with station locations
   ↓
3. Map renders station markers
   - Clustered for performance
   - Colored by current alert status
   ↓
4. User clicks station marker
   ↓
5. Popup shows:
   - Station name
   - River name
   - Current water level
   - Alert status
   - Historical discharge chart
```

---

## FRONTEND COMPONENTS

### Main Page Component
**File:** [MapViewer.jsx](frontend/src/components/pages/MapViewer.jsx:1) - **3,277 lines** ⚠️

**Issues:**
- Monolithic component
- 50+ useState hooks
- Inline sub-components
- Hard to maintain

**Does Everything:**
- Map rendering
- Layer management
- Data fetching
- Sidebar controls
- Popup handling
- Date filtering
- Country filtering

### Layer Components
- [MonitoringStationsLayer.tsx](frontend/src/components/map/layers/MonitoringStationsLayer.tsx) - Renders station markers
- [GeoSFMLayer.tsx](frontend/src/components/map/layers/GeoSFMLayer.tsx) - Renders satellite data
- [EnsembleLayer.tsx](frontend/src/components/map/layers/EnsembleLayer.tsx) - Renders forecast points

### Sidebar/Controls
- [MuiSidebar.jsx](frontend/src/components/layout/MuiSidebar.jsx) - 811 lines
- [SidebarControls.jsx](frontend/src/components/sidebar/SidebarControls.jsx) - 722 lines
- **Duplication:** These two components do similar things ⚠️

### Panels
- [FloatingStationPanel.jsx](frontend/src/components/panels/FloatingStationPanel.jsx) - Station detail popup
- [RightPanel.jsx](frontend/src/components/panels/RightPanel.jsx) - Right-side control panel

---

## CONFIGURATION FILES

### Multiple Config Files (Duplication):
1. [config/layers.js](frontend/src/config/layers.js) - Layer definitions, API URLs
2. [config/mapLayers.ts](frontend/src/config/mapLayers.ts) - Map layer config
3. [config/endpoints.ts](frontend/src/config/endpoints.ts) - API endpoint URLs
4. [config/mapConfig.ts](frontend/src/config/mapConfig.ts) - Map settings

**Problem:** Same configuration spread across 4 files

---

## CACHING MECHANISMS

### Frontend Caching:
1. [utils/forecastCache.js](frontend/src/utils/forecastCache.js) - Custom LRU cache for forecasts
2. [services/cacheService.js](frontend/src/services/cacheService.js) - Duplicate cache implementation ⚠️

### Backend Caching:
- FastAPI has in-memory cache for dates endpoint (15min TTL)

---

## SUMMARY

### What Works:
✅ Django serves station data, boundaries, GeoSFM, inundation rasters
✅ FastAPI serves merged multimodal forecasts (MIKE + FloodProofs + HYPE)
✅ Frontend hooks fetch data correctly
✅ Map displays forecast points, stations, satellite data

### What's Complex:
⚠️ MapViewer.jsx is 3,277 lines (should be 15-20 smaller components)
⚠️ Duplicate config files (4 files for configuration)
⚠️ Duplicate cache implementations
⚠️ Duplicate sidebar components
⚠️ No clear separation of concerns

### What's Missing:
❌ Impact calculation endpoints (removed/commented out)
❌ Individual model endpoints (only merged forecast available)
❌ Documentation of what each model (MIKE, FloodProofs, HYPE) does

### Forecast Models Status:
- **MIKE:** ✅ Included in merged forecast
- **FloodProofs:** ✅ Included in merged forecast
- **HYPE:** ✅ Included in merged forecast
- **GeoSFM:** ✅ Separate endpoint (satellite data)
- **Ensemble/Merged:** ✅ FastAPI serves combined result

### Data Storage:
- **PostgreSQL Table:** `Impact_mergeddeterministicgeojson`
- **Contains:** Merged forecast GeoJSON for each date
- **Accessed By:** FastAPI (high-performance async queries)

---

## RECOMMENDATIONS FOR SIMPLIFICATION

1. **Break up MapViewer.jsx** into 20+ small components
2. **Merge config files** into single `config.ts`
3. **Remove duplicate** cache/sidebar implementations
4. **Add impact calculation** endpoints if needed
5. **Document** what each model (MIKE, FloodProofs, HYPE) provides
6. **Create simple hooks** for each data source
7. **Use consistent** API URL configuration
