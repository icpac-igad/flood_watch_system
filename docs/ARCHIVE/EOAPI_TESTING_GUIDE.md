# eoAPI Testing Guide
## TiPg & TiTiler API Endpoints

This guide shows how to test the TiPg and TiTiler services after deploying with Docker.

---

## Prerequisites

```bash
# Start Docker services
docker-compose up -d stac-api tipg

# Verify services are running
docker-compose ps
curl http://localhost:8083/health  # TiPg
curl http://localhost:8000/health  # TiTiler
```

---

## TiPg API Testing (Port 8083)
### Vector Tiles from PostGIS Tables

### 1. List All Collections (Tables)

```bash
curl http://localhost:8083/collections | jq
```

**Expected Response**:
```json
{
  "collections": [
    {
      "id": "Impact_admin0",
      "title": "Impact_admin0",
      "type": "Table"
    },
    {
      "id": "Impact_admin1",
      "title": "Impact_admin1"
    },
    {
      "id": "Impact_admin2",
      "title": "Impact_admin2"
    },
    {
      "id": "Impact_hydrorivers",
      "title": "Impact_hydrorivers"
    },
    {
      "id": "Impact_waterbodies",
      "title": "Impact_waterbodies"
    },
    {
      "id": "Impact_monitoringstation",
      "title": "Impact_monitoringstation"
    }
  ]
}
```

---

### 2. Get Collection Metadata

```bash
# Admin0 (Countries)
curl http://localhost:8083/collections/Impact_admin0 | jq

# Admin1 (Provinces)
curl http://localhost:8083/collections/Impact_admin1 | jq

# Rivers
curl http://localhost:8083/collections/Impact_hydrorivers | jq
```

**Expected Response**:
```json
{
  "id": "Impact_admin0",
  "title": "Impact_admin0",
  "extent": {
    "spatial": {
      "bbox": [[-20, -40, 60, 20]]
    }
  },
  "links": [
    {
      "rel": "items",
      "href": "http://localhost:8083/collections/Impact_admin0/items"
    },
    {
      "rel": "tiles",
      "href": "http://localhost:8083/collections/Impact_admin0/tiles/{z}/{x}/{y}"
    }
  ]
}
```

---

### 3. Get Features (GeoJSON)

```bash
# Get all admin0 features
curl "http://localhost:8083/collections/Impact_admin0/items?limit=10" | jq

# Get specific country by property
curl "http://localhost:8083/collections/Impact_admin0/items?filter=admin0='Kenya'" | jq

# Get features in bounding box (East Africa)
curl "http://localhost:8083/collections/Impact_admin0/items?bbox=33,-5,42,6" | jq
```

**Example Response**:
```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Polygon",
        "coordinates": [[[33.0, -5.0], [42.0, -5.0], ...]]
      },
      "properties": {
        "admin0": "Kenya",
        "iso3": "KEN",
        "population": 50000000
      }
    }
  ]
}
```

---

### 4. Get Vector Tiles (MVT)

Vector tiles use the Web Mercator tiling scheme (z/x/y).

```bash
# Get tile at zoom 4, covering East Africa
curl "http://localhost:8083/collections/Impact_admin0/tiles/4/8/8" \
  --output admin0_tile.mvt

# Get monitoring stations tile
curl "http://localhost:8083/collections/Impact_monitoringstation/tiles/6/32/32" \
  --output stations_tile.mvt

# Get rivers tile
curl "http://localhost:8083/collections/Impact_hydrorivers/tiles/7/64/64" \
  --output rivers_tile.mvt
```

**Tile Format**: Mapbox Vector Tiles (MVT) - binary format

**View in Browser**: Use Leaflet or MapLibre GL

---

### 5. TiPg Endpoints Summary

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/collections` | GET | List all PostGIS tables |
| `/collections/{id}` | GET | Get table metadata |
| `/collections/{id}/items` | GET | Get features as GeoJSON |
| `/collections/{id}/tiles/{z}/{x}/{y}` | GET | Get vector tile (MVT) |
| `/health` | GET | Health check |

**Query Parameters**:
- `limit` - Max features to return (default: 10)
- `bbox` - Bounding box filter: `minx,miny,maxx,maxy`
- `filter` - CQL filter: `property='value'`
- `properties` - Select specific properties

---

## TiTiler API Testing (Port 8000)
### Raster Tiles from Cloud Optimized GeoTIFFs

### 1. Get Raster Info

```bash
# Get metadata for inundation map
curl "http://localhost:8000/cog/info?url=/data/inundation_maps/flood_hazard_20251105.tif" | jq

# Get statistics
curl "http://localhost:8000/cog/statistics?url=/data/inundation_maps/flood_hazard_20251105.tif" | jq
```

**Expected Response**:
```json
{
  "bounds": [33.0, -5.0, 42.0, 6.0],
  "minzoom": 0,
  "maxzoom": 14,
  "band_metadata": [["b1", {}]],
  "band_descriptions": [["b1", "Band 1"]],
  "dtype": "float32",
  "nodata_type": "Nodata",
  "colorinterp": ["gray"]
}
```

---

### 2. Get Raster Tiles

```bash
# Inundation map with blues colormap
curl "http://localhost:8000/cog/tiles/4/8/8.png?url=/data/inundation_maps/flood_hazard_20251105.tif&colormap_name=blues&rescale=0,1" \
  --output inundation_tile.png

# Alert level map with reversed red-yellow-green
curl "http://localhost:8000/cog/tiles/6/32/32.png?url=/data/alert_levels/alerts_20251105.tif&colormap_name=rdylgn_r&rescale=1,4" \
  --output alerts_tile.png
```

**Colormap Options**:
- `blues` - Inundation (0-1 rescale)
- `rdylgn_r` - Alert levels (1-4: green→yellow→red)
- `viridis`, `plasma`, `inferno` - Alternative scientific colormaps

---

### 3. Preview Image

```bash
# Get quick preview (256x256)
curl "http://localhost:8000/cog/preview.png?url=/data/inundation_maps/flood_hazard_20251105.tif&colormap_name=blues&rescale=0,1" \
  --output preview.png

# Custom size
curl "http://localhost:8000/cog/preview.png?url=/data/alert_levels/alerts_20251105.tif&colormap_name=rdylgn_r&rescale=1,4&width=512&height=512" \
  --output preview_large.png
```

---

### 4. TiTiler Endpoints Summary

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/cog/info` | GET | Get raster metadata |
| `/cog/statistics` | GET | Get band statistics |
| `/cog/tiles/{z}/{x}/{y}.png` | GET | Get raster tile |
| `/cog/preview.png` | GET | Get preview image |
| `/health` | GET | Health check |

**Query Parameters**:
- `url` - **Required** - Path to COG file
- `colormap_name` - Colormap (blues, rdylgn_r, viridis, etc.)
- `rescale` - Min,max values for rescaling
- `bidx` - Band index (default: 1)
- `width`, `height` - Preview dimensions

---

## Frontend Integration Examples

### Leaflet + TiPg Vector Tiles

```javascript
import L from 'leaflet';
import 'leaflet.vectorgrid';

// Add admin boundaries
const admin0Layer = L.vectorGrid.protobuf(
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
).addTo(map);

// Add rivers
const riversLayer = L.vectorGrid.protobuf(
  "http://localhost:8083/collections/Impact_hydrorivers/tiles/{z}/{x}/{y}",
  {
    vectorTileLayerStyles: {
      Impact_hydrorivers: {
        weight: 1,
        color: '#0066cc',
        opacity: 0.8
      }
    }
  }
).addTo(map);
```

---

### Leaflet + TiTiler Raster Tiles

```javascript
import L from 'leaflet';

// Add inundation layer
const inundationLayer = L.tileLayer(
  'http://localhost:8000/cog/tiles/{z}/{x}/{y}.png?url=/data/inundation_maps/flood_hazard_20251105.tif&colormap_name=blues&rescale=0,1',
  {
    opacity: 0.6,
    attribution: 'ICPAC FloodWatch'
  }
).addTo(map);

// Add alert level layer
const alertsLayer = L.tileLayer(
  'http://localhost:8000/cog/tiles/{z}/{x}/{y}.png?url=/data/alert_levels/alerts_20251105.tif&colormap_name=rdylgn_r&rescale=1,4',
  {
    opacity: 0.7,
    attribution: 'ICPAC FloodWatch'
  }
).addTo(map);
```

---

## Testing Checklist

### TiPg Tests
- [ ] Service responds on port 8083
- [ ] `/collections` returns PostGIS tables
- [ ] `/collections/Impact_admin0/items` returns GeoJSON
- [ ] Vector tiles load without errors
- [ ] Tile size is <10KB (check with `--output` and `ls -lh`)

### TiTiler Tests
- [ ] Service responds on port 8000
- [ ] `/cog/info` returns raster metadata
- [ ] Tiles render with correct colormap
- [ ] Preview images generate successfully
- [ ] Rescaling works correctly

### Performance Tests
- [ ] Vector tiles load faster than WMS (use browser dev tools)
- [ ] Tile sizes are significantly smaller (~90% reduction)
- [ ] No CORS errors in browser console
- [ ] Tiles cache correctly (check Network tab)

---

## Troubleshooting

### TiPg Issues

**Problem**: No collections returned
```bash
# Check database connection
docker-compose exec tipg env | grep DATABASE_URL

# Verify PostGIS tables exist
docker-compose exec postgis psql -U postgres -d floodwatch -c "\dt public.*"
```

**Problem**: Vector tiles are empty
```bash
# Check table has geometry column
docker-compose exec postgis psql -U postgres -d floodwatch -c "SELECT column_name, data_type FROM information_schema.columns WHERE table_name='Impact_admin0';"
```

---

### TiTiler Issues

**Problem**: Raster file not found
```bash
# Check file exists
docker-compose exec titiler ls -lh /data/inundation_maps/

# Use absolute path in URL parameter
curl "http://localhost:8000/cog/info?url=/data/inundation_maps/flood_hazard_20251105.tif"
```

**Problem**: Wrong colors
```bash
# Check data range with statistics
curl "http://localhost:8000/cog/statistics?url=/data/test.tif" | jq '.b1.min, .b1.max'

# Adjust rescale parameter to match data range
```

---

## Next Steps

1. ✅ Test all endpoints with curl
2. ✅ Verify data is returned correctly
3. ✅ Test vector tiles in Leaflet
4. ✅ Test raster tiles with TiTiler
5. ✅ Compare performance vs MapServer
6. ✅ Update frontend to use new endpoints

---

**Quick Test Script**:
```bash
#!/bin/bash
echo "Testing TiPg..."
curl -s http://localhost:8083/health && echo "✅ TiPg healthy" || echo "❌ TiPg failed"
curl -s http://localhost:8083/collections | jq '.collections[].id' && echo "✅ Collections found" || echo "❌ No collections"

echo ""
echo "Testing TiTiler..."
curl -s http://localhost:8000/health && echo "✅ TiTiler healthy" || echo "❌ TiTiler failed"
curl -s "http://localhost:8000/cog/info?url=/data/test.tif" && echo "✅ COG accessible" || echo "❌ COG not found"
```

Save as `test_eoapi.sh`, run with `bash test_eoapi.sh`
