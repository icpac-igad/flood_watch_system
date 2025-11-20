# eoAPI Testing Plan

## Current Status

**Docker Services Deploying:**
- ✅ PostgreSQL (existing) - Running on port 8091
- ⏳ TiPg - Port 8083 (downloading)
- ⏳ STAC API - Port 8084 (downloading)
- ⏳ TiTiler-PgSTAC - Port 8082 (downloading)
- ⏳ STAC Browser - Port 8085 (downloading)

---

## Phase 1: TiPg Vector Tiles Testing

### 1.1 Auto-Discovery Test

**Once TiPg is running:**

```bash
# Check health
curl http://localhost:8083/healthz

# List all available collections (should auto-discover PostGIS tables)
curl http://localhost:8083/collections | jq
```

**Expected Result:**
Should automatically discover these tables without any configuration:
- `Impact_admin0` - Country boundaries
- `Impact_admin1` - Province boundaries
- `Impact_admin2` - District boundaries
- `Impact_waterbodies` - Lakes
- `Impact_hydrorivers` - River network
- `Impact_monitoringstation` - Monitoring stations

### 1.2 Vector Tile Endpoint Test

```bash
# Get metadata for admin0
curl http://localhost:8083/collections/Impact_admin0 | jq

# Get a sample vector tile (z=5, x=15, y=11)
# This is Kenya region at zoom level 5
curl "http://localhost:8083/collections/Impact_admin0/tiles/5/15/11" -o test_admin0.mvt

# Check file size (should be much smaller than MapServer PNG)
ls -lh test_admin0.mvt
```

### 1.3 Compare to MapServer WMS

**Current MapServer WMS (PNG):**
```bash
# Get same region as PNG from MapServer
curl "http://localhost:8080/mapserv?SERVICE=WMS&VERSION=1.1.0&REQUEST=GetMap&LAYERS=admin0&SRS=EPSG:4326&BBOX=33,-5,42,5&WIDTH=256&HEIGHT=256&FORMAT=image/png&TRANSPARENT=true" -o test_admin0.png

# Check file size
ls -lh test_admin0.png
```

**Expected:** MVT should be 10-20x smaller than PNG

### 1.4 Performance Test

```bash
# Benchmark MapServer WMS
time curl -s "http://localhost:8080/mapserv?SERVICE=WMS&VERSION=1.1.0&REQUEST=GetMap&LAYERS=admin0,admin1,rivers,waterbodies&SRS=EPSG:4326&BBOX=33,-5,42,5&WIDTH=512&HEIGHT=512&FORMAT=image/png" > /dev/null

# Benchmark TiPg MVT (multiple tiles)
time curl -s "http://localhost:8083/collections/Impact_admin0/tiles/5/15/11" > /dev/null
```

---

## Phase 2: STAC API Testing

### 2.1 Bootstrap pgSTAC Schema

**Note:** Your current PostgreSQL image doesn't have pgSTAC extension.

**Options:**
1. **Add pgSTAC to existing image** (recommended)
2. **Use separate database** for STAC
3. **Skip STAC API for now** and just use TiPg

**If adding pgSTAC:**
```bash
docker compose exec postgis psql -U postgres -d floodwatch -c "CREATE EXTENSION IF NOT EXISTS pgstac;"
```

### 2.2 Test STAC API

```bash
# Check STAC API health
curl http://localhost:8084/

# Get conformance classes
curl http://localhost:8084/conformance | jq

# Search for items (will be empty initially)
curl http://localhost:8084/search | jq
```

---

## Phase 3: TiTiler-PgSTAC Testing

### 3.1 Raster Tile Server

**Purpose:** Serve inundation rasters as tiles

```bash
# Check TiTiler health
curl http://localhost:8082/healthz

# List available algorithms
curl http://localhost:8082/algorithms | jq
```

**Future:** Replace Django's TiTiler integration with this service

---

## Phase 4: Frontend Integration

### 4.1 Replace MapServer WMS with TiPg MVT

**Current (MapServer WMS):**
```jsx
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

**New (TiPg MVT):**
```jsx
import { VectorTileLayer } from 'react-leaflet-vector-tile-layer';

<VectorTileLayer
  url="http://localhost:8083/collections/{layer}/tiles/{z}/{x}/{y}"
  // Supports: Impact_admin0, Impact_admin1, Impact_admin2,
  //           Impact_waterbodies, Impact_hydrorivers
  vectorTileLayerStyles={{
    Impact_admin0: {
      fill: true,
      fillOpacity: 0,
      color: '#000000',
      weight: 4,
      opacity: 1.0
    },
    Impact_rivers: {
      color: '#1e5a8e',
      weight: function(properties) {
        // Larger rivers = thicker lines
        return properties.ord_clas >= 6 ? 1.2 :
               properties.ord_clas >= 4 ? 0.8 : 0.5;
      }
    }
  }}
/>
```

### 4.2 Benefits

**Performance:**
- **15x smaller file size** (MVT vs PNG)
- **Client-side rendering** (GPU accelerated)
- **No image artifacts** at any zoom level
- **Interactive features** (hover, click on individual polygons)
- **Attribute access** (can display river names, admin codes, etc.)

**Flexibility:**
- **Dynamic styling** based on properties
- **Filter by attributes** (show only order 6+ rivers)
- **Declutter labels** automatically
- **Smooth zoom** (no tile reloading)

---

## Phase 5: Architecture Comparison

### Current Architecture (Before eoAPI)

```
Frontend (React + Leaflet)
  ↓ WMS PNG (large files, slow)
MapServer (vector → raster conversion)
  ↓ SQL queries
PostgreSQL (PostGIS tables)
```

**Issues:**
- PNG tiles are 100-300KB each
- MapServer converts vectors to raster (CPU intensive)
- Can't interact with features (click rivers, hover boundaries)
- Styling is server-side (requires mapfile changes)

### New Architecture (With eoAPI)

```
Frontend (React + Leaflet)
  ↓ MVT tiles (tiny, fast)
TiPg (zero-config vector tile server)
  ↓ Optimized SQL
PostgreSQL (PostGIS tables)
```

**Benefits:**
- MVT tiles are 5-20KB each (15x smaller)
- No raster conversion (direct vector streaming)
- Interactive features (click, hover, select)
- Client-side styling (instant changes, no server restarts)
- Auto-discovery (no configuration files needed)

---

## Testing Checklist

### TiPg
- [ ] Service is running on port 8083
- [ ] Auto-discovers all 6 PostGIS tables
- [ ] Returns valid MVT tiles
- [ ] MVT tiles are smaller than WMS PNG
- [ ] Response time is faster than MapServer

### STAC API
- [ ] Service is running on port 8084
- [ ] pgSTAC extension is installed
- [ ] Can create collections
- [ ] Can ingest STAC items
- [ ] Search API works

### TiTiler-PgSTAC
- [ ] Service is running on port 8082
- [ ] Can serve raster tiles
- [ ] Supports COG (Cloud Optimized GeoTIFF)
- [ ] Can replace Django TiTiler integration

### STAC Browser
- [ ] Service is running on port 8085
- [ ] Connects to STAC API
- [ ] Can browse collections
- [ ] Can preview items

---

## Migration Strategy

### Step 1: Parallel Testing ✅ (Current Phase)
Run eoAPI alongside existing system without breaking anything

### Step 2: Prove Performance
- Benchmark file sizes (MVT vs PNG)
- Benchmark response times
- Test frontend with TiPg vector tiles

### Step 3: Gradual Migration
1. Replace MapServer admin boundaries with TiPg (admin0, admin1, admin2)
2. Replace MapServer rivers with TiPg (hydrorivers)
3. Replace MapServer waterbodies with TiPg
4. Integrate STAC API for forecast metadata
5. Use TiTiler-PgSTAC for raster tiles

### Step 4: Remove Old Services
- Stop MapServer once TiPg is proven
- Remove Django TiTiler integration once TiTiler-PgSTAC is proven
- Keep FastAPI for FloodProofs (it's working well)

---

## Expected Results

### File Size Comparison
| Layer | MapServer PNG | TiPg MVT | Reduction |
|-------|--------------|----------|-----------|
| admin0 | ~120KB | ~8KB | **93%** |
| rivers | ~250KB | ~15KB | **94%** |
| combined | ~350KB | ~20KB | **94%** |

### Response Time
- MapServer WMS: 200-500ms
- TiPg MVT: 50-150ms
- **Improvement: 3-4x faster**

### User Experience
- **Sharper rendering** at all zoom levels
- **Click on rivers** to see names and attributes
- **Hover over boundaries** to highlight
- **Instant style changes** (no server restart)
- **Smaller bundle size** for mobile users

---

## Next Steps

1. ✅ Wait for Docker images to finish downloading
2. ⏳ Test TiPg auto-discovery
3. ⏳ Compare MVT vs PNG file sizes
4. ⏳ Create frontend proof-of-concept with vector tiles
5. ⏳ Simplify frontend to 5 core components using new architecture
