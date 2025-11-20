# eoAPI Services - All Working Now! ✅

## Fixed Issues

### 1. TiPg Port Mapping ✅
**Problem:** Container listens on port 80, not 8080
**Fix:** Changed `ports: - "8083:8080"` to `ports: - "8083:80"`

### 2. TiTiler Port Mapping ✅
**Problem:** Container listens on port 80, not 8080
**Fix:** Changed `ports: - "8082:8080"` to `ports: - "8082:80"`

### 3. STAC API Missing Environment Variables ✅
**Problem:** STAC API needs `PGHOST`, `PGPORT`, etc.
**Fix:** Added complete PostgreSQL connection variables:
```yaml
- POSTGRES_HOST_READER=postgis
- POSTGRES_HOST_WRITER=postgis
- PGHOST=postgis
- PGPORT=5432
- PGUSER=postgres
- PGPASSWORD=floodwatch_pass
- PGDATABASE=floodwatch
```

---

## All Services Status

| Service | Port | Status | Test URL |
|---------|------|--------|----------|
| **TiPg** | 8083 | ✅ Working | http://localhost:8083/ |
| **TiTiler** | 8082 | ✅ Working | http://localhost:8082/healthz |
| **STAC API** | 8084 | ✅ Working | http://localhost:8084/ |
| **STAC Browser** | 8085 | ✅ Working | http://localhost:8085/ |

---

## How to Access Services

### 1. TiPg (Vector Tiles)

**Landing Page:**
```
http://localhost:8083/
```

**List Collections:**
```bash
curl http://localhost:8083/collections | jq -r '.collections[] | .id'
```

**Get Collection Info:**
```bash
# Country boundaries
curl http://localhost:8083/collections/pgstac.Impact_admin0 | jq

# Rivers
curl http://localhost:8083/collections/pgstac.Impact_hydrorivers | jq

# Lakes
curl http://localhost:8083/collections/pgstac.Impact_waterbodies | jq
```

**Interactive Map Viewer:**
```
# Admin0 (Countries)
http://localhost:8083/collections/pgstac.Impact_admin0/tiles/WebMercatorQuad/viewer

# Rivers
http://localhost:8083/collections/pgstac.Impact_hydrorivers/tiles/WebMercatorQuad/viewer

# Lakes
http://localhost:8083/collections/pgstac.Impact_waterbodies/tiles/WebMercatorQuad/viewer

# Monitoring Stations
http://localhost:8083/collections/pgstac.Impact_monitoringstation/tiles/WebMercatorQuad/viewer
```

**Vector Tile URLs (for frontend):**
```
http://localhost:8083/collections/pgstac.Impact_admin0/tiles/{z}/{x}/{y}
http://localhost:8083/collections/pgstac.Impact_admin1/tiles/{z}/{x}/{y}
http://localhost:8083/collections/pgstac.Impact_admin2/tiles/{z}/{x}/{y}
http://localhost:8083/collections/pgstac.Impact_hydrorivers/tiles/{z}/{x}/{y}
http://localhost:8083/collections/pgstac.Impact_waterbodies/tiles/{z}/{x}/{y}
http://localhost:8083/collections/pgstac.Impact_monitoringstation/tiles/{z}/{x}/{y}
```

**API Documentation:**
```
http://localhost:8083/api.html
```

---

### 2. TiTiler (Raster Tiles)

**Health Check:**
```bash
curl http://localhost:8082/healthz | jq
```

**Versions:**
```json
{
  "database_online": true,
  "versions": {
    "titiler": "0.24.2",
    "titiler.pgstac": "1.9.0",
    "rasterio": "1.4.3",
    "gdal": "3.9.3",
    "proj": "9.4.1",
    "geos": "3.11.1"
  }
}
```

**API Documentation:**
```
http://localhost:8082/docs
```

---

### 3. STAC API (Metadata Catalog)

**Landing Page:**
```bash
curl http://localhost:8084/ | jq
```

**Response:**
```json
{
  "id": "stac-fastapi",
  "title": "stac-fastapi",
  "description": "stac-fastapi",
  "type": "Catalog",
  ...
}
```

**Conformance:**
```bash
curl http://localhost:8084/conformance | jq
```

**Collections:**
```bash
curl http://localhost:8084/collections | jq
```

**Search:**
```bash
curl http://localhost:8084/search | jq
```

**API Documentation:**
```
http://localhost:8084/api.html
```

---

### 4. STAC Browser (Visual UI)

**Web Interface:**
```
http://localhost:8085/
```

This provides a visual interface to browse STAC collections and items.

---

## Data Coverage

Your PostGIS data covers **East Africa**:

- **Longitude:** 21.84° E to 51.42° E
- **Latitude:** 11.75° S to 23.14° N

**Countries covered:**
- Kenya
- Somalia
- Ethiopia
- Sudan
- South Sudan
- Uganda
- Tanzania
- And surrounding regions

---

## Testing Vector Tiles

### Quick Test

```bash
# Get a tile from the Kenya region
curl "http://localhost:8083/collections/pgstac.Impact_admin0/tiles/6/33/23" -o test.mvt

# Check file size
ls -lh test.mvt
```

### Using the Interactive Viewer

1. Open in browser:
   ```
   http://localhost:8083/collections/pgstac.Impact_admin0/tiles/WebMercatorQuad/viewer
   ```

2. **Pan to East Africa** (if not already centered there)
   - The map should show your admin boundaries
   - Zoom in/out to see different detail levels

3. **Try other layers:**
   - Rivers: http://localhost:8083/collections/pgstac.Impact_hydrorivers/tiles/WebMercatorQuad/viewer
   - Lakes: http://localhost:8083/collections/pgstac.Impact_waterbodies/tiles/WebMercatorQuad/viewer

---

## Frontend Integration Example

```jsx
import { VectorTileLayer } from 'react-leaflet-vector-tile-layer';

function Map() {
  return (
    <MapContainer center={[0.3, 37.5]} zoom={6}>
      {/* Base map */}
      <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />

      {/* Admin boundaries - Vector tiles from TiPg */}
      <VectorTileLayer
        url="http://localhost:8083/collections/pgstac.Impact_admin0/tiles/{z}/{x}/{y}"
        vectorTileLayerStyles={{
          'pgstac.Impact_admin0': {
            fill: false,
            color: '#000000',
            weight: 4,
            opacity: 1.0
          }
        }}
        interactive={true}
        onClick={(e) => {
          console.log('Clicked country:', e.layer.properties);
        }}
      />

      {/* Rivers - Vector tiles */}
      <VectorTileLayer
        url="http://localhost:8083/collections/pgstac.Impact_hydrorivers/tiles/{z}/{x}/{y}"
        vectorTileLayerStyles={{
          'pgstac.Impact_hydrorivers': (properties) => ({
            color: properties.ord_clas >= 6 ? '#f5faff' :
                   properties.ord_clas >= 4 ? '#dcebf5' : '#1e5a8e',
            weight: properties.ord_clas >= 6 ? 1.2 :
                    properties.ord_clas >= 4 ? 0.8 : 0.5,
            opacity: 0.6
          })
        }}
      />

      {/* Lakes - Vector tiles */}
      <VectorTileLayer
        url="http://localhost:8083/collections/pgstac.Impact_waterbodies/tiles/{z}/{x}/{y}"
        vectorTileLayerStyles={{
          'pgstac.Impact_waterbodies': {
            fill: true,
            fillColor: '#55a0d2',
            fillOpacity: 1.0,
            color: '#55a0d2',
            weight: 1
          }
        }}
      />
    </MapContainer>
  );
}
```

---

## Troubleshooting

### If interactive viewer doesn't show data:

1. **Check tile has data:**
   ```bash
   # Try different tiles
   curl "http://localhost:8083/collections/pgstac.Impact_admin0/tiles/4/8/7" -o tile1.mvt
   curl "http://localhost:8083/collections/pgstac.Impact_admin0/tiles/5/16/15" -o tile2.mvt
   curl "http://localhost:8083/collections/pgstac.Impact_admin0/tiles/6/33/23" -o tile3.mvt

   # Check sizes
   ls -lh tile*.mvt
   ```

2. **View collection extent:**
   ```bash
   curl http://localhost:8083/collections/pgstac.Impact_admin0 | jq '.extent.spatial.bbox'
   ```

3. **Check data in database:**
   ```bash
   docker compose exec postgis psql -U postgres -d floodwatch \
     -c "SELECT COUNT(*) FROM pgstac.\"Impact_admin0\";"
   ```

### If services don't respond:

1. **Check all services are running:**
   ```bash
   docker compose ps | grep -E "(tipg|titiler|stac)"
   ```

2. **Check logs:**
   ```bash
   docker compose logs tipg | tail -20
   docker compose logs titiler-pgstac | tail -20
   docker compose logs stac-api | tail -20
   ```

3. **Restart services:**
   ```bash
   docker compose restart tipg titiler-pgstac stac-api
   ```

---

## Next Steps

1. ✅ All services working
2. ✅ Vector tiles accessible
3. ✅ Raster tile server ready
4. ✅ STAC API functional
5. ⏳ Create simplified 5-component frontend
6. ⏳ Integrate TiPg vector tiles into frontend
7. ⏳ Replace MapServer WMS with TiPg MVT

---

## Summary

**All eoAPI services are now working!**

- **TiPg:** Serving vector tiles for all 6 PostGIS tables
- **TiTiler:** Ready for raster tiles
- **STAC API:** Metadata catalog operational
- **STAC Browser:** Visual data explorer accessible

**Test the interactive viewer:**
```
http://localhost:8083/collections/pgstac.Impact_admin0/tiles/WebMercatorQuad/viewer
```

Pan to **Kenya (0.3°N, 37.5°E)** to see your data!
