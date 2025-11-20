# FloodWatch API Documentation

## Overview

FloodWatch uses two main API services for geospatial data:
1. **FastAPI Service** - High-performance forecast data (GeoJSON)
2. **TiPg** - Vector tiles from PostGIS tables

---

## FastAPI Service

**Base URL**: `http://localhost:9050`
**Technology**: FastAPI with asyncpg for high-performance PostgreSQL queries
**Response Format**: GeoJSON with optimized JSON serialization (orjson)

### Features
- Connection pooling (5-20 connections)
- In-memory caching (15-minute TTL for dates)
- Response time logging
- Country-based filtering
- Automatic fallback to latest data

### Endpoints

#### 1. Service Info
```http
GET /
```

Returns service status and available endpoints.

**Response**:
```json
{
  "service": "FloodWatch Forecast API",
  "status": "operational",
  "endpoints": {
    "dates": "/api/fast/merged-forecast/dates/",
    "forecast": "/api/fast/merged-forecast/{date}/",
    "latest": "/api/fast/merged-forecast/latest/",
    "ensemble": "/api/fast/ensemble-control-points"
  }
}
```

#### 2. Health Check
```http
GET /health
```

Database health check.

**Response**:
```json
{
  "status": "healthy"
}
```

#### 3. Available Forecast Dates
```http
GET /api/fast/merged-forecast/dates/
```

Returns list of all available forecast dates with metadata.

**Features**:
- Cached (15 minutes TTL)
- Validates dates before returning
- Filters out invalid/overflow dates

**Response**:
```json
{
  "dates": [
    {
      "date": "2025-01-15",
      "date_string": "20250115",
      "feature_count": 15234,
      "file_count": 45,
      "created_at": "2025-01-15T12:30:00"
    }
  ],
  "count": 120,
  "source": "database"
}
```

**Response Headers**:
- `X-Cache-Hit`: `true` or `false`
- `X-Response-Time`: Response time in milliseconds

#### 4. Get Forecast by Date
```http
GET /api/fast/merged-forecast/{forecast_date}/
```

Returns deterministic forecast data for a specific date.

**Parameters**:
- `forecast_date` (path): Date in `YYYY-MM-DD` format
- `country` (query, optional): Filter features by country name

**Example**:
```bash
# Get forecast for specific date
curl http://localhost:9050/api/fast/merged-forecast/2025-01-15/

# Filter by country
curl http://localhost:9050/api/fast/merged-forecast/2025-01-15/?country=Kenya
```

**Response**: GeoJSON FeatureCollection

**Response Headers**:
- `X-Forecast-Date`: Actual date of returned data
- `X-Feature-Count`: Number of features in response
- `X-Original-Count`: Number of features before filtering
- `X-Response-Time`: Response time in milliseconds
- `X-Fallback`: `true` if fallback to latest was used
- `X-Fallback-Date`: Date of fallback data (if applicable)
- `Cache-Control`: `public, max-age=3600`

#### 5. Get Latest Forecast
```http
GET /api/fast/merged-forecast/latest/
```

Returns the most recent deterministic forecast data.

**Parameters**:
- `country` (query, optional): Filter features by country name

**Example**:
```bash
# Get latest forecast
curl http://localhost:9050/api/fast/merged-forecast/latest/

# Filter by country
curl http://localhost:9050/api/fast/merged-forecast/latest/?country=Uganda
```

**Response**: GeoJSON FeatureCollection

**Response Headers**:
- `X-Forecast-Date`: Date of the latest forecast
- `X-Feature-Count`: Number of features in response
- `X-Original-Count`: Number of features before filtering
- `X-Response-Time`: Response time in milliseconds
- `Cache-Control`: `public, max-age=1800`

#### 6. Ensemble Control Points
```http
GET /api/fast/ensemble-control-points
```

Returns ensemble forecast data with control points.

**Example**:
```bash
curl http://localhost:9050/api/fast/ensemble-control-points
```

**Response**: GeoJSON FeatureCollection with ensemble forecast points

**Response Headers**:
- `X-Feature-Count`: Total number of control points
- `X-Features-With-Data`: Number of points with forecast data
- `X-Forecast-Date`: Date of the forecast
- `X-Response-Time`: Response time in milliseconds
- `Cache-Control`: `public, max-age=3600`

### Performance

Typical response times:
- Dates endpoint (cached): < 5ms
- Dates endpoint (uncached): < 100ms
- Forecast endpoints: 20-100ms depending on data size
- Country filtering: Minimal overhead (client-side filtering)

### Error Handling

All errors return standard HTTP status codes:
- `400`: Invalid date format
- `404`: No data found
- `500`: Server error

**Error Response**:
```json
{
  "detail": "Error message"
}
```

---

## TiPg - Vector Tiles Service

**Base URL**: `http://localhost:8083`
**Technology**: TiPg (OGC Vector Tiles from PostGIS)
**Tile Format**: Mapbox Vector Tiles (MVT)

### Features
- OGC-compliant vector tiles
- Optimized for dense river networks
- High-resolution tiles (4096x4096)
- Supports zoom levels 0-22
- Large tile buffer (256px) to prevent clipping
- Up to 50,000 features per tile

### Configuration

The service is optimized with these settings:
```yaml
TIPG_TILE_RESOLUTION: 4096      # High resolution
TIPG_TILE_BUFFER: 256           # Prevents clipping at tile edges
TIPG_MAX_FEATURES_PER_TILE: 50000  # For dense networks
TIPG_DEFAULT_MINZOOM: 0         # Available from zoom 0
TIPG_DEFAULT_MAXZOOM: 22        # Available up to zoom 22
TIPG_DB_SCHEMAS: ["pgstac"]     # Serves tables from pgstac schema
```

### Endpoints

#### 1. API Documentation
```http
GET /docs
```

Interactive OpenAPI documentation (Swagger UI).

**Browser Access**: http://localhost:8083/docs

#### 2. Service Landing Page
```http
GET /
```

OGC API landing page with links to all available resources.

#### 3. Collections List
```http
GET /collections
```

Lists all available vector tile collections (PostGIS tables/views).

**Response**:
```json
{
  "collections": [
    {
      "id": "river_networks",
      "title": "River Networks",
      "extent": {
        "spatial": {...},
        "temporal": {...}
      },
      "links": [...]
    }
  ]
}
```

#### 4. Collection Metadata
```http
GET /collections/{collectionId}
```

Get detailed metadata for a specific collection.

**Example**:
```bash
curl http://localhost:8083/collections/river_networks
```

#### 5. Vector Tiles
```http
GET /collections/{collectionId}/tiles/{tileMatrixSetId}/{z}/{x}/{y}
```

Returns vector tiles in Mapbox Vector Tiles (MVT) format.

**Parameters**:
- `collectionId`: Table/view name from pgstac schema
- `tileMatrixSetId`: Usually `WebMercatorQuad`
- `z`: Zoom level (0-22)
- `x`: Tile column
- `y`: Tile row

**Example**:
```bash
# Get tile at zoom 10, x=512, y=384
curl http://localhost:8083/collections/river_networks/tiles/WebMercatorQuad/10/512/384
```

#### 6. TileJSON
```http
GET /collections/{collectionId}/tiles/{tileMatrixSetId}/tilejson.json
```

Returns TileJSON metadata for use with mapping libraries.

**Example**:
```bash
curl http://localhost:8083/collections/river_networks/tiles/WebMercatorQuad/tilejson.json
```

**Response**:
```json
{
  "tilejson": "3.0.0",
  "name": "river_networks",
  "tiles": [
    "http://localhost:8083/collections/river_networks/tiles/WebMercatorQuad/{z}/{x}/{y}"
  ],
  "minzoom": 0,
  "maxzoom": 22,
  "bounds": [-180, -90, 180, 90]
}
```

#### 7. Health Check
```http
GET /healthz
```

Service health check.

### Usage in Web Maps

#### MapLibre GL JS Example

```javascript
map.addSource('rivers', {
  type: 'vector',
  tiles: [
    'http://localhost:8083/collections/river_networks/tiles/WebMercatorQuad/{z}/{x}/{y}'
  ],
  minzoom: 0,
  maxzoom: 22
});

map.addLayer({
  id: 'rivers-layer',
  type: 'line',
  source: 'rivers',
  'source-layer': 'default',  // TiPg uses 'default' as layer name
  paint: {
    'line-color': '#0080ff',
    'line-width': 2
  }
});
```

#### Leaflet Example

```javascript
// Using Leaflet.VectorGrid plugin
const vectorTileOptions = {
  rendererFactory: L.canvas.tile,
  vectorTileLayerStyles: {
    default: {
      color: '#0080ff',
      weight: 2
    }
  }
};

const riverLayer = L.vectorGrid.protobuf(
  'http://localhost:8083/collections/river_networks/tiles/WebMercatorQuad/{z}/{x}/{y}',
  vectorTileOptions
).addTo(map);
```

#### OpenLayers Example

```javascript
import MVT from 'ol/format/MVT';
import VectorTileLayer from 'ol/layer/VectorTile';
import VectorTileSource from 'ol/source/VectorTile';

const vectorLayer = new VectorTileLayer({
  source: new VectorTileSource({
    format: new MVT(),
    url: 'http://localhost:8083/collections/river_networks/tiles/WebMercatorQuad/{z}/{x}/{y}'
  }),
  style: {
    'stroke-color': '#0080ff',
    'stroke-width': 2
  }
});
```

### Performance Considerations

1. **Tile Caching**: Consider implementing a CDN or tile cache (MapCache) in front of TiPg for production
2. **Zoom Level Strategy**:
   - Use simplified geometries at lower zoom levels
   - Full detail at higher zoom levels
3. **Feature Filtering**: Use SQL views to pre-filter data by relevance
4. **Index Optimization**: Ensure PostGIS spatial indexes exist on all geometry columns

### Query Available Collections

```bash
# List all collections
curl http://localhost:8083/collections | jq '.collections[].id'

# Get collection details
curl http://localhost:8083/collections/your_table_name | jq
```

---

## Migrating from MapServer to TiPg

### Why TiPg?

1. **Modern Protocol**: OGC API compliance instead of legacy WMS/WFS
2. **Better Performance**: Vector tiles are more efficient than WMS/WFS for vector data
3. **Client-Side Styling**: Tiles can be styled dynamically in the browser
4. **Smaller Payloads**: Only download tiles in viewport
5. **Better Caching**: Tile-based caching is more effective
6. **Zoom-Dependent Rendering**: Automatic level-of-detail

### Migration Steps

1. **Identify Vector Layers**: Determine which MapServer layers serve vector data
2. **Update Frontend**: Replace WMS/WFS layers with vector tile layers
3. **Style Translation**: Convert MapServer styles to client-side styles
4. **Testing**: Verify performance and rendering quality
5. **Deprecation**: Remove MapServer layers once TiPg is stable

### Current Status

- **MapServer** (port 8095): Still active for backward compatibility
- **MapCache** (port 8096): Still active for raster tile caching
- **TiPg** (port 8083): Ready for vector tile serving

---

## Environment Variables

### FastAPI Service
```bash
DB_HOST=postgis              # Database host
DB_PORT=5432                 # Database port
DB_NAME=floodwatch          # Database name
DB_USER=postgres            # Database user
DB_PASSWORD=floodwatch_pass # Database password
```

### TiPg Service
```bash
POSTGRES_HOST=postgis              # Database host
POSTGRES_PORT=5432                 # Database port
POSTGRES_DBNAME=floodwatch        # Database name
POSTGRES_USER=postgres            # Database user
POSTGRES_PASS=floodwatch_pass     # Database password
TIPG_DB_SCHEMAS=["pgstac"]        # Schemas to serve
TIPG_TILE_RESOLUTION=4096         # Tile resolution
TIPG_TILE_BUFFER=256              # Tile buffer size
TIPG_MAX_FEATURES_PER_TILE=50000  # Max features per tile
```

---

## Testing the APIs

### FastAPI Tests

```bash
# Health check
curl http://localhost:9050/health

# Get available dates
curl http://localhost:9050/api/fast/merged-forecast/dates/

# Get latest forecast
curl http://localhost:9050/api/fast/merged-forecast/latest/

# Get forecast by date
curl http://localhost:9050/api/fast/merged-forecast/2025-01-15/

# Filter by country
curl "http://localhost:9050/api/fast/merged-forecast/latest/?country=Kenya"

# Get ensemble data
curl http://localhost:9050/api/fast/ensemble-control-points
```

### TiPg Tests

```bash
# Health check
curl http://localhost:8083/healthz

# List collections
curl http://localhost:8083/collections

# Get TileJSON
curl http://localhost:8083/collections/your_table/tiles/WebMercatorQuad/tilejson.json

# Get a tile (returns binary MVT data)
curl http://localhost:8083/collections/your_table/tiles/WebMercatorQuad/5/16/12
```

---

## Accessing APIs from Jupyter Notebooks

### Installation

First, install required Python packages:

```bash
pip install requests geopandas pandas matplotlib folium
```

### FastAPI - Forecast Data

#### 1. Get Available Dates

```python
import requests
import pandas as pd

# Base URL
FASTAPI_URL = "http://localhost:9050"

# Get available dates
response = requests.get(f"{FASTAPI_URL}/api/fast/merged-forecast/dates/")
dates_data = response.json()

# Convert to DataFrame
dates_df = pd.DataFrame(dates_data['dates'])
print(f"Total dates available: {dates_data['count']}")
print(dates_df.head())

# Check if cached
print(f"Cache hit: {response.headers.get('X-Cache-Hit')}")
print(f"Response time: {response.headers.get('X-Response-Time')}ms")
```

#### 2. Load Forecast Data as GeoDataFrame

```python
import geopandas as gpd
from shapely.geometry import shape

# Get latest forecast
response = requests.get(f"{FASTAPI_URL}/api/fast/merged-forecast/latest/")
forecast_data = response.json()

# Convert GeoJSON to GeoDataFrame
gdf = gpd.GeoDataFrame.from_features(forecast_data['features'])

print(f"Total features: {len(gdf)}")
print(f"Forecast date: {response.headers.get('X-Forecast-Date')}")
print(gdf.head())
```

#### 3. Filter by Country

```python
# Get forecast for specific country
country = "Kenya"
response = requests.get(
    f"{FASTAPI_URL}/api/fast/merged-forecast/latest/",
    params={"country": country}
)
kenya_data = response.json()

# Convert to GeoDataFrame
kenya_gdf = gpd.GeoDataFrame.from_features(kenya_data['features'])

print(f"Features in {country}: {len(kenya_gdf)}")
print(f"Original count: {response.headers.get('X-Original-Count')}")
```

#### 4. Analyze Forecast Data

```python
import matplotlib.pyplot as plt

# Get latest forecast
response = requests.get(f"{FASTAPI_URL}/api/fast/merged-forecast/latest/")
gdf = gpd.GeoDataFrame.from_features(response.json()['features'])

# Basic statistics
print("Forecast Statistics:")
print(gdf.describe())

# Plot if you have numeric columns
if 'flood_risk' in gdf.columns:
    gdf['flood_risk'].hist(bins=20)
    plt.title('Flood Risk Distribution')
    plt.xlabel('Risk Level')
    plt.ylabel('Frequency')
    plt.show()
```

#### 5. Time Series Analysis

```python
import pandas as pd
from datetime import datetime, timedelta

# Get multiple dates
dates_response = requests.get(f"{FASTAPI_URL}/api/fast/merged-forecast/dates/")
dates = dates_response.json()['dates']

# Load data for last 7 days
forecasts = []
for date_info in dates[-7:]:
    date_str = date_info['date']
    response = requests.get(f"{FASTAPI_URL}/api/fast/merged-forecast/{date_str}/")
    gdf = gpd.GeoDataFrame.from_features(response.json()['features'])
    gdf['forecast_date'] = date_str
    forecasts.append(gdf)

# Combine all forecasts
all_forecasts = gpd.GeoDataFrame(pd.concat(forecasts, ignore_index=True))
print(f"Total records: {len(all_forecasts)}")
```

#### 6. Interactive Map with Folium

```python
import folium
from folium import GeoJson

# Get latest forecast
response = requests.get(f"{FASTAPI_URL}/api/fast/merged-forecast/latest/")
forecast_data = response.json()

# Create map centered on data
gdf = gpd.GeoDataFrame.from_features(forecast_data['features'])
center = [gdf.geometry.centroid.y.mean(), gdf.geometry.centroid.x.mean()]

m = folium.Map(location=center, zoom_start=6)

# Add forecast data
GeoJson(
    forecast_data,
    name='Forecast Data',
    tooltip=folium.GeoJsonTooltip(fields=['properties'], aliases=['Properties'])
).add_to(m)

m.save('forecast_map.html')
print("Map saved to forecast_map.html")
```

#### 7. Ensemble Control Points

```python
# Get ensemble forecast data
response = requests.get(f"{FASTAPI_URL}/api/fast/ensemble-control-points")
ensemble_data = response.json()

# Convert to GeoDataFrame
ensemble_gdf = gpd.GeoDataFrame.from_features(ensemble_data['features'])

print(f"Control points: {response.headers.get('X-Feature-Count')}")
print(f"Points with data: {response.headers.get('X-Features-With-Data')}")
print(ensemble_gdf.head())
```

### TiPg - Vector Tiles

#### 1. List Available Collections

```python
import requests

TIPG_URL = "http://localhost:8083"

# Get all collections
response = requests.get(f"{TIPG_URL}/collections")
collections = response.json()

# List collection IDs
for collection in collections['collections']:
    print(f"Collection: {collection['id']}")
    print(f"  Title: {collection.get('title', 'N/A')}")
    if 'extent' in collection:
        spatial = collection['extent'].get('spatial', {})
        if 'bbox' in spatial and spatial['bbox']:
            print(f"  Bounds: {spatial['bbox'][0]}")
    print()
```

#### 2. Get Collection Metadata

```python
# Get specific collection details
collection_id = "pgstac.Impact_admin0"  # Example collection

response = requests.get(f"{TIPG_URL}/collections/{collection_id}")
metadata = response.json()

print(f"Collection: {metadata['id']}")
print(f"Description: {metadata.get('description', 'N/A')}")
print(f"Extent: {metadata.get('extent', {})}")
```

#### 3. Get TileJSON Metadata

```python
# Get TileJSON for a collection
collection_id = "pgstac.Impact_admin0"
tile_matrix = "WebMercatorQuad"

response = requests.get(
    f"{TIPG_URL}/collections/{collection_id}/tiles/{tile_matrix}/tilejson.json"
)
tilejson = response.json()

print(f"Name: {tilejson['name']}")
print(f"Min Zoom: {tilejson['minzoom']}")
print(f"Max Zoom: {tilejson['maxzoom']}")
print(f"Bounds: {tilejson['bounds']}")
print(f"Tile URL: {tilejson['tiles'][0]}")
```

#### 4. Access Vector Tile Data

```python
import requests
from io import BytesIO

# Note: Vector tiles are binary MVT format
# For analysis, you typically use them in web maps
# But you can download and inspect them

collection_id = "pgstac.Impact_rivers"
z, x, y = 5, 16, 12  # Example tile coordinates

tile_url = f"{TIPG_URL}/collections/{collection_id}/tiles/WebMercatorQuad/{z}/{x}/{y}"
response = requests.get(tile_url)

print(f"Tile size: {len(response.content)} bytes")
print(f"Content-Type: {response.headers.get('Content-Type')}")

# Vector tiles are meant for web rendering, not direct analysis
# For data analysis, use FastAPI endpoints instead
```

#### 5. Query Features Using Items Endpoint

Some TiPg deployments support querying features as GeoJSON:

```python
# Check if items endpoint is available
collection_id = "pgstac.Impact_admin0"

try:
    # Try to get features as GeoJSON (if supported)
    response = requests.get(
        f"{TIPG_URL}/collections/{collection_id}/items",
        params={
            'limit': 100,  # Limit number of features
            'bbox': '32,-5,42,5'  # Bounding box filter (minx,miny,maxx,maxy)
        }
    )

    if response.status_code == 200:
        features = response.json()
        gdf = gpd.GeoDataFrame.from_features(features['features'])
        print(f"Retrieved {len(gdf)} features")
        print(gdf.head())
    else:
        print(f"Items endpoint not available (status {response.status_code})")
        print("Use vector tiles for visualization instead")
except Exception as e:
    print(f"Error accessing items: {e}")
    print("TiPg is optimized for vector tiles, use them in web maps")
```

#### 6. Display Vector Tiles in Folium

```python
import folium

# Create map
m = folium.Map(location=[0, 35], zoom_start=6)

# Add vector tile layer using TileLayer
# Note: Folium doesn't natively support MVT, use raster tiles or MapLibre
collection_id = "pgstac.Impact_admin0"
tile_url = f"{TIPG_URL}/collections/{collection_id}/tiles/WebMercatorQuad/{{z}}/{{x}}/{{y}}"

# For MVT support, use MapLibre GL JS in HTML
html = f"""
<!DOCTYPE html>
<html>
<head>
    <script src='https://unpkg.com/maplibre-gl@latest/dist/maplibre-gl.js'></script>
    <link href='https://unpkg.com/maplibre-gl@latest/dist/maplibre-gl.css' rel='stylesheet' />
    <style>
        body {{ margin: 0; padding: 0; }}
        #map {{ position: absolute; top: 0; bottom: 0; width: 100%; }}
    </style>
</head>
<body>
    <div id='map'></div>
    <script>
        var map = new maplibregl.Map({{
            container: 'map',
            style: {{
                'version': 8,
                'sources': {{
                    'osm': {{
                        'type': 'raster',
                        'tiles': ['https://tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png'],
                        'tileSize': 256
                    }},
                    'vector-tiles': {{
                        'type': 'vector',
                        'tiles': ['{tile_url}'],
                        'minzoom': 0,
                        'maxzoom': 22
                    }}
                }},
                'layers': [
                    {{
                        'id': 'osm',
                        'type': 'raster',
                        'source': 'osm'
                    }},
                    {{
                        'id': 'vector-layer',
                        'type': 'line',
                        'source': 'vector-tiles',
                        'source-layer': 'default',
                        'paint': {{
                            'line-color': '#000000',
                            'line-width': 2
                        }}
                    }}
                ]
            }},
            center: [35, 0],
            zoom: 6
        }});
    </script>
</body>
</html>
"""

with open('vector_tiles_map.html', 'w') as f:
    f.write(html)

print("Vector tiles map saved to vector_tiles_map.html")
```

### Combined Workflow Example

```python
import requests
import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt

# Setup
FASTAPI_URL = "http://localhost:9050"
TIPG_URL = "http://localhost:8083"

# 1. Get latest forecast from FastAPI
print("1. Loading forecast data...")
forecast_response = requests.get(f"{FASTAPI_URL}/api/fast/merged-forecast/latest/")
forecast_gdf = gpd.GeoDataFrame.from_features(forecast_response.json()['features'])
forecast_date = forecast_response.headers.get('X-Forecast-Date')

print(f"   Loaded {len(forecast_gdf)} forecast points for {forecast_date}")

# 2. Get available TiPg collections
print("\n2. Checking available vector collections...")
collections_response = requests.get(f"{TIPG_URL}/collections")
collections = [c['id'] for c in collections_response.json()['collections']]
print(f"   Available collections: {collections[:5]}...")

# 3. Analyze forecast data
print("\n3. Analyzing forecast data...")
if len(forecast_gdf) > 0:
    print(f"   Bounds: {forecast_gdf.total_bounds}")
    print(f"   CRS: {forecast_gdf.crs}")
    print(f"   Columns: {list(forecast_gdf.columns)}")

# 4. Summary
print(f"\n4. Summary:")
print(f"   - Forecast date: {forecast_date}")
print(f"   - Number of points: {len(forecast_gdf)}")
print(f"   - Vector collections: {len(collections)}")
print(f"   - Ready for analysis!")
```

### Best Practices

1. **Use FastAPI for Data Analysis**: FastAPI returns GeoJSON which is easy to work with in Python
2. **Use TiPg for Visualization**: Vector tiles are optimized for web map rendering
3. **Cache Responses**: Store frequently-used data locally to reduce API calls
4. **Handle Errors**: Always check response status codes
5. **Respect Rate Limits**: In production, implement request throttling
6. **Use Async for Multiple Requests**: Consider `aiohttp` for concurrent requests

### Error Handling Example

```python
import requests

def get_forecast_safe(date=None):
    """Safely retrieve forecast data with error handling"""
    try:
        url = f"{FASTAPI_URL}/api/fast/merged-forecast/latest/"
        if date:
            url = f"{FASTAPI_URL}/api/fast/merged-forecast/{date}/"

        response = requests.get(url, timeout=30)
        response.raise_for_status()

        data = response.json()
        gdf = gpd.GeoDataFrame.from_features(data['features'])

        return {
            'success': True,
            'data': gdf,
            'date': response.headers.get('X-Forecast-Date'),
            'count': len(gdf)
        }
    except requests.exceptions.Timeout:
        return {'success': False, 'error': 'Request timeout'}
    except requests.exceptions.HTTPError as e:
        return {'success': False, 'error': f'HTTP error: {e}'}
    except Exception as e:
        return {'success': False, 'error': f'Unexpected error: {e}'}

# Usage
result = get_forecast_safe()
if result['success']:
    print(f"Loaded {result['count']} features for {result['date']}")
else:
    print(f"Error: {result['error']}")
```

---

## Production Considerations

### FastAPI
1. Increase connection pool size for high traffic
2. Add Redis for distributed caching
3. Enable HTTP/2 for better performance
4. Add rate limiting
5. Implement authentication if needed

### TiPg
1. Add tile caching layer (Varnish, CloudFlare, etc.)
2. Set up CDN for global distribution
3. Monitor tile generation performance
4. Optimize database indexes
5. Consider materialized views for complex queries

---

## Support

For issues or questions:
- FastAPI service logs: `docker logs floodwatch_fastapi`
- TiPg service logs: `docker logs floodwatch_tipg`
- Database logs: `docker logs floodwatch_pgstac`
