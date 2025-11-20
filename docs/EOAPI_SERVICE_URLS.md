# eoAPI Service Access URLs

## Quick Access Links

### 1. TiPg - Vector Tile Server
- **Landing Page:** http://localhost:8083/
- **API Documentation:** http://localhost:8083/api.html
- **Collections List:** http://localhost:8083/collections
- **Interactive Map Viewer:** http://localhost:8083/collections/pgstac.Impact_admin0/tiles/WebMercatorQuad/viewer

**Example Vector Tile URLs:**
```
# Country Boundaries
http://localhost:8083/collections/pgstac.Impact_admin0/tiles/{z}/{x}/{y}

# Rivers
http://localhost:8083/collections/pgstac.Impact_hydrorivers/tiles/{z}/{x}/{y}

# Lakes
http://localhost:8083/collections/pgstac.Impact_waterbodies/tiles/{z}/{x}/{y}

# Provinces
http://localhost:8083/collections/pgstac.Impact_admin1/tiles/{z}/{x}/{y}

# Districts
http://localhost:8083/collections/pgstac.Impact_admin2/tiles/{z}/{x}/{y}

# Monitoring Stations
http://localhost:8083/collections/pgstac.Impact_monitoringstation/tiles/{z}/{x}/{y}
```

---

### 2. TiTiler-PgSTAC - Raster Tile Server
- **Landing Page:** http://localhost:8082/
- **API Documentation:** http://localhost:8082/docs
- **Health Check:** http://localhost:8082/healthz

---

### 3. STAC API - Metadata Catalog
- **Landing Page:** http://localhost:8084/
- **API Documentation:** http://localhost:8084/api
- **API Docs (HTML):** http://localhost:8084/api.html
- **Conformance:** http://localhost:8084/conformance
- **Collections:** http://localhost:8084/collections
- **Search:** http://localhost:8084/search

---

### 4. STAC Browser - Visual Data Explorer
- **Web Interface:** http://localhost:8085/

---

## Built-in Map Viewers

### TiPg Interactive Viewers (Best for Testing)

**View Country Boundaries:**
http://localhost:8083/collections/pgstac.Impact_admin0/tiles/WebMercatorQuad/viewer

**View Rivers:**
http://localhost:8083/collections/pgstac.Impact_hydrorivers/tiles/WebMercatorQuad/viewer

**View Lakes:**
http://localhost:8083/collections/pgstac.Impact_waterbodies/tiles/WebMercatorQuad/viewer

**View Monitoring Stations:**
http://localhost:8083/collections/pgstac.Impact_monitoringstation/tiles/WebMercatorQuad/viewer

---

## Testing Commands

### Check All Services Are Running

```bash
# TiPg
curl -s http://localhost:8083/ | jq -r '.title'

# TiTiler
curl -s http://localhost:8082/healthz

# STAC API
curl -s http://localhost:8084/ | jq -r '.title'

# STAC Browser
curl -s http://localhost:8085/ | head -5
```

### List All Available Collections (TiPg)

```bash
curl -s http://localhost:8083/collections | jq -r '.collections[] | "\(.id) - \(.title)"'
```

### Get Collection Metadata

```bash
# Admin0 (Countries)
curl -s http://localhost:8083/collections/pgstac.Impact_admin0 | jq

# Rivers
curl -s http://localhost:8083/collections/pgstac.Impact_hydrorivers | jq
```

### Download Sample Vector Tiles

```bash
# Kenya region (zoom=5, x=15, y=11)
curl "http://localhost:8083/collections/pgstac.Impact_admin0/tiles/5/15/11" -o admin0_sample.mvt
curl "http://localhost:8083/collections/pgstac.Impact_hydrorivers/tiles/5/15/11" -o rivers_sample.mvt
curl "http://localhost:8083/collections/pgstac.Impact_waterbodies/tiles/5/15/11" -o lakes_sample.mvt

# Check file sizes
ls -lh *.mvt
```

---

## Comparison: Old vs New

### OLD: MapServer WMS (Port 8095)
```
http://localhost:8095/mapserv?SERVICE=WMS&VERSION=1.1.0&REQUEST=GetMap&LAYERS=admin0&SRS=EPSG:4326&BBOX=33,-5,42,5&WIDTH=512&HEIGHT=512&FORMAT=image/png&TRANSPARENT=true
```
**Returns:** PNG image (150-300KB)

### NEW: TiPg MVT (Port 8083)
```
http://localhost:8083/collections/pgstac.Impact_admin0/tiles/5/15/11
```
**Returns:** Vector tile (5-15KB) - **90% smaller!**

---

## Browser Testing

### Option 1: TiPg Built-in Viewer (Easiest)
Just open in your browser:
```
http://localhost:8083/collections/pgstac.Impact_admin0/tiles/WebMercatorQuad/viewer
```
This shows an interactive map with your data!

### Option 2: STAC Browser
```
http://localhost:8085/
```
Visual interface to browse all collections

### Option 3: API Documentation
```
http://localhost:8083/api.html  (TiPg)
http://localhost:8082/docs      (TiTiler)
http://localhost:8084/api.html  (STAC API)
```
Interactive Swagger/OpenAPI docs

---

## Service Health Checks

```bash
# Check all services
docker compose ps | grep -E "(tipg|titiler|stac)"

# Expected output:
# floodwatch_tipg           Up X minutes   0.0.0.0:8083->8080/tcp
# floodwatch_titiler        Up X minutes   0.0.0.0:8082->8080/tcp
# floodwatch_stac_api       Up X minutes   0.0.0.0:8084->8080/tcp
# floodwatch_stac_browser   Up X minutes   0.0.0.0:8085->8080/tcp
```

---

## Quick Demo Script

```bash
#!/bin/bash

echo "=== eoAPI Services Status ==="
echo ""

echo "1. TiPg (Vector Tiles):"
curl -s http://localhost:8083/ | jq -r '.title' && echo "✅ Running" || echo "❌ Not accessible"

echo ""
echo "2. TiTiler (Raster Tiles):"
curl -s http://localhost:8082/healthz && echo "✅ Running" || echo "❌ Not accessible"

echo ""
echo "3. STAC API:"
curl -s http://localhost:8084/ | jq -r '.title' && echo "✅ Running" || echo "❌ Not accessible"

echo ""
echo "4. Auto-discovered PostGIS tables:"
curl -s http://localhost:8083/collections | jq -r '.collections[] | select(.id | startswith("pgstac.Impact_")) | "  - \(.id)"'

echo ""
echo "=== Open these URLs in your browser ==="
echo "TiPg Map Viewer:    http://localhost:8083/collections/pgstac.Impact_admin0/tiles/WebMercatorQuad/viewer"
echo "TiPg API Docs:      http://localhost:8083/api.html"
echo "TiTiler API Docs:   http://localhost:8082/docs"
echo "STAC Browser:       http://localhost:8085/"
```

Save this as `check_eoapi.sh` and run it!
