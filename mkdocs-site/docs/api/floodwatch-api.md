# FloodWatch API Documentation

Complete reference for accessing FloodWatch APIs from notebooks and applications.

## Table of Contents

1. [Environment Configuration](#environment-configuration)
2. [Django Backend API](#django-backend-api)
3. [FastAPI Service](#fastapi-service)
4. [TiPg Vector Tiles API](#tipg-vector-tiles-api)
5. [Admin Panel](#admin-panel)
6. [Notebook Examples](#notebook-examples)
7. [Authentication](#authentication)
8. [Error Handling](#error-handling)

---

## Environment Configuration

### Local Development URLs

```python
# Base URLs for local development (Docker Compose)
BACKEND_URL = "http://localhost:8090/api"      # Django API
FASTAPI_URL = "http://localhost:9050"          # FastAPI service
TIPG_URL = "http://localhost:8083"             # TiPg vector tiles
ADMIN_URL = "http://localhost:8090/admin"      # Django admin panel
FRONTEND_URL = "http://localhost:8094"         # Frontend (nginx proxy)

# Through Frontend Proxy (recommended for CORS)
BACKEND_PROXY = "http://localhost:8094/api"    # Django through nginx
FASTAPI_PROXY = "http://localhost:8094/api/fast"  # FastAPI through nginx
TIPG_PROXY = "http://localhost:8094/tipg"      # TiPg through nginx
```

### Production URLs

```python
# Production URLs (replace with your domain)
PRODUCTION_DOMAIN = "https://your-domain.com"
BACKEND_URL = f"{PRODUCTION_DOMAIN}/api"
FASTAPI_URL = f"{PRODUCTION_DOMAIN}/api/fast"
TIPG_URL = f"{PRODUCTION_DOMAIN}/tipg"
ADMIN_URL = f"{PRODUCTION_DOMAIN}/admin"
```

### Environment Detection

```python
import os

def get_api_urls():
    """
    Automatically detect environment and return appropriate URLs.
    Set ENVIRONMENT=production in your environment variables for production.
    """
    env = os.getenv('ENVIRONMENT', 'local')

    if env == 'production':
        domain = os.getenv('API_DOMAIN', 'https://your-domain.com')
        return {
            'backend': f'{domain}/api',
            'fastapi': f'{domain}/api/fast',
            'tipg': f'{domain}/tipg',
            'admin': f'{domain}/admin'
        }
    else:
        # Local development - use frontend proxy to avoid CORS
        return {
            'backend': 'http://localhost:8094/api',
            'fastapi': 'http://localhost:8094/api/fast',
            'tipg': 'http://localhost:8094/tipg',
            'admin': 'http://localhost:8090/admin'
        }

# Usage
URLS = get_api_urls()
```

---

## Django Backend API

Base URL: `/api/`

### Geographic Data APIs

#### 1. Administrative Boundaries

**Admin Level 0 (Countries)**
```http
GET /api/admin0/
GET /api/admin0/{id}/
GET /api/admin-boundaries/  # GeoJSON format
```

**Admin Level 1 (States/Provinces)**
```http
GET /api/admin1/
GET /api/admin1/{id}/
```

**Admin Level 2 (Districts)**
```http
GET /api/admin2/
GET /api/admin2/{id}/
```

#### 2. Water Bodies & Rivers

**Water Bodies (Lakes)**
```http
GET /api/water-bodies/
GET /api/water-bodies/{id}/
```

**Rivers**
```http
GET /api/rivers/
GET /api/rivers/{id}/
```

Query parameters:
- `?format=json` - JSON response
- `?format=geojson` - GeoJSON response
- `?bbox=minx,miny,maxx,maxy` - Spatial filter
- `?limit=100` - Pagination limit
- `?offset=0` - Pagination offset

#### 3. Monitoring Stations

```http
GET /api/monitoring-stations/
GET /api/monitoring-stations/{id}/
```

Response includes station metadata, location, and historical data.

### Forecast Data APIs

#### 4. Deterministic Forecast (Merged)

**Get Available Dates**
```http
GET /api/deterministic/available-dates/
```

Response:
```json
{
  "dates": ["2025-11-19", "2025-11-18", "2025-11-17"],
  "count": 3
}
```

**Get Latest Forecast**
```http
GET /api/deterministic/latest/
```

**Get Forecast by Date**
```http
GET /api/deterministic/{YYYY-MM-DD}/
```

Example: `/api/deterministic/2025-11-19/`

Response: GeoJSON FeatureCollection with forecast data for monitoring stations.

#### 5. GeoSFM Flood Extent

**Get Available Dates**
```http
GET /api/geosfm/available-dates/
```

**Get Latest GeoSFM**
```http
GET /api/geosfm/latest/
```

**Get GeoSFM by Date**
```http
GET /api/geosfm/{YYYY-MM-DD}/
```

**Get Signed URLs (for client-side loading from GCS)**
```http
GET /api/geosfm/signed-urls/?date={YYYY-MM-DD}
```

#### 6. Ensemble Control Points

```http
GET /api/ensemble-control-points/
GET /api/ensemble-control-points/{id}/
```

### Raster Data APIs (TiTiler)

```http
GET /api/raster/files/                    # List available raster files
GET /api/raster/dates/                    # List available dates
GET /api/raster/{date}/                   # Get raster for specific date
GET /api/raster/info/?url={file_path}     # Get raster metadata
GET /api/raster/statistics/?url={file_path}  # Get raster statistics
GET /api/raster/latest-inundation/        # Latest inundation map
GET /api/raster/latest-alerts/            # Latest alert map
```

### Layer Configuration

```http
GET /api/map-layers/                      # Get map layer configuration
GET /api/layers/all-dates/                # All layers with available dates
GET /api/layers/{layer_id}/available-dates/  # Dates for specific layer
GET /api/layers/{layer_id}/latest-date/   # Latest date for layer
```

### Report Management

```http
GET /api/station-reports/                 # List station reports
POST /api/station-reports/                # Create new report
GET /api/station-reports/{id}/            # Get specific report
PUT /api/station-reports/{id}/            # Update report
DELETE /api/station-reports/{id}/         # Delete report

GET /api/station-assessments/             # Station assessments
POST /api/station-assessments/            # Create assessment

GET /api/saved-reports/                   # Saved reports
POST /api/saved-reports/                  # Save report
```

### API Schema & Documentation

```http
GET /api/schema/                          # OpenAPI schema (JSON)
GET /api/schema/swagger-ui/               # Interactive Swagger UI
GET /api/schema/redoc/                    # ReDoc documentation
```

---

## FastAPI Service

High-performance forecast data API optimized for large GeoJSON responses.

Base URL: `/api/fast/`

### Endpoints

#### 1. Root / Service Info

```http
GET /
```

Response:
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

#### 2. Get Available Forecast Dates

```http
GET /api/fast/merged-forecast/dates/
```

Response:
```json
{
  "dates": [
    {
      "date": "2025-11-19",
      "date_string": "20251119",
      "feature_count": 979,
      "file_count": 12,
      "created_at": "2025-11-19T06:00:00"
    }
  ],
  "count": 15,
  "source": "database"
}
```

**Caching**: Results cached for 15 minutes (900 seconds)

#### 3. Get Latest Forecast

```http
GET /api/fast/merged-forecast/latest/
GET /api/fast/merged-forecast/latest/?country=Kenya
```

Query Parameters:
- `country` (optional): Filter by country name (case-insensitive)

Response Headers:
- `X-Forecast-Date`: Date of forecast data
- `X-Feature-Count`: Number of features returned
- `X-Original-Count`: Original count before filtering
- `X-Response-Time`: Processing time in milliseconds
- `Cache-Control`: public, max-age=1800 (30 minutes)

Response: GeoJSON FeatureCollection

#### 4. Get Forecast by Date

```http
GET /api/fast/merged-forecast/{YYYY-MM-DD}/
GET /api/fast/merged-forecast/2025-11-19/?country=Uganda
```

Query Parameters:
- `country` (optional): Filter by country name

Response Headers:
- `X-Forecast-Date`: Date of forecast data
- `X-Feature-Count`: Number of features returned
- `X-Original-Count`: Original count before filtering
- `X-Response-Time`: Processing time in milliseconds
- `X-Fallback`: "true" if requested date not found (falls back to latest)
- `X-Fallback-Date`: Date of fallback data
- `Cache-Control`: public, max-age=3600 (1 hour)

#### 5. Get Ensemble Control Points

```http
GET /api/fast/ensemble-control-points
```

Returns all ensemble control points with forecast data.

Response Headers:
- `X-Feature-Count`: Total features
- `X-Features-With-Data`: Features with forecast data
- `X-Forecast-Date`: Date of forecast
- `X-Response-Time`: Processing time
- `Cache-Control`: public, max-age=3600

#### 6. Health Check

```http
GET /health
```

Response:
```json
{
  "status": "healthy"
}
```

### Performance Characteristics

- **JSON Parser**: Uses `orjson` for 2-3x faster JSON encoding
- **Database**: Async PostgreSQL connection pool (5-20 connections)
- **Response Time**: Typically 5-100ms for cached queries
- **Caching**:
  - Dates: 15 minutes
  - Latest forecast: 30 minutes
  - Date-specific forecast: 1 hour
- **Compression**: Gzip enabled for responses

---

## TiPg Vector Tiles API

OGC-compliant vector tiles for administrative boundaries, rivers, and lakes.

Base URL: `/tipg/` (through nginx proxy) or `http://localhost:8083/` (direct)

### Collections

Available collections:
- `pgstac.Impact_admin0` - Country boundaries
- `pgstac.Impact_admin1` - State/Province boundaries
- `pgstac.Impact_admin2` - District boundaries
- `pgstac.Impact_hydrorivers` - All rivers
- `pgstac.Impact_hydrorivers_major` - Major rivers only
- `pgstac.Impact_waterbodies` - Lakes and water bodies
- `pgstac.Impact_monitoringstation` - Monitoring stations

### Endpoints

#### 1. API Root

```http
GET /tipg/
```

Returns landing page with API links and available endpoints.

#### 2. List Collections

```http
GET /tipg/collections
```

Returns list of all available vector tile collections.

#### 3. Collection Metadata

```http
GET /tipg/collections/{collectionId}
```

Example:
```http
GET /tipg/collections/pgstac.Impact_admin0
```

#### 4. Vector Tiles (MVT format)

```http
GET /tipg/collections/{collectionId}/tiles/{tileMatrixSetId}/{z}/{x}/{y}
```

Standard web map tiles:
- `tileMatrixSetId`: Use `WebMercatorQuad` for web maps
- `z`: Zoom level (0-22)
- `x`: Tile X coordinate
- `y`: Tile Y coordinate

Example:
```http
GET /tipg/collections/pgstac.Impact_admin0/tiles/WebMercatorQuad/5/17/12
```

Response: Binary Mapbox Vector Tile (MVT)

#### 5. GeoJSON Features

```http
GET /tipg/collections/{collectionId}/items
GET /tipg/collections/{collectionId}/items/{itemId}
```

Query parameters:
- `limit`: Maximum features to return (default: 10)
- `bbox`: Bounding box filter `minx,miny,maxx,maxy`
- `datetime`: Temporal filter

#### 6. Tile Viewer

```http
GET /tipg/collections/{collectionId}/tiles/WebMercatorQuad/viewer
```

Interactive map viewer for the collection.

#### 7. Health Check

```http
GET /tipg/healthz
```

Response:
```json
{"ping": "pong!"}
```

### Caching

Vector tiles are cached for 24 hours:
- Browser cache: 24 hours (`Cache-Control: public, max-age=86400`)
- Nginx proxy cache: 24 hours

---

## Admin Panel

Django admin interface for data management.

URL: `http://localhost:8090/admin/` (local) or `https://your-domain.com/admin/` (production)

### Access

1. Create superuser (first time):
```bash
docker exec -it floodwatch_backend python manage.py createsuperuser
```

2. Login at `/admin/` with your credentials

### Available Models

- Administrative boundaries (Admin0, Admin1, Admin2)
- Water bodies and rivers
- Monitoring stations
- Forecast data (Ensemble, Deterministic, GeoSFM)
- Station reports and assessments
- Map layer configuration
- User management

---

## Notebook Examples

### Setup

```python
import requests
import pandas as pd
import geopandas as gpd
from datetime import datetime, timedelta
import json

# Environment detection
import os

def get_base_urls():
    """Get API URLs based on environment"""
    env = os.getenv('ENVIRONMENT', 'local')

    if env == 'production':
        domain = os.getenv('API_DOMAIN', 'https://your-domain.com')
        return {
            'backend': f'{domain}/api',
            'fastapi': f'{domain}/api/fast',
            'tipg': f'{domain}/tipg'
        }
    else:
        # Use nginx proxy for CORS compatibility
        return {
            'backend': 'http://localhost:8094/api',
            'fastapi': 'http://localhost:8094/api/fast',
            'tipg': 'http://localhost:8094/tipg'
        }

URLS = get_base_urls()
```

### Example 1: Get Latest Forecast (FastAPI)

```python
def get_latest_forecast(country=None):
    """
    Get the latest deterministic forecast.

    Args:
        country (str, optional): Filter by country name

    Returns:
        dict: GeoJSON FeatureCollection
    """
    url = f"{URLS['fastapi']}/merged-forecast/latest/"

    params = {}
    if country:
        params['country'] = country

    response = requests.get(url, params=params)
    response.raise_for_status()

    # Print metadata from headers
    print(f"Forecast Date: {response.headers.get('X-Forecast-Date')}")
    print(f"Feature Count: {response.headers.get('X-Feature-Count')}")
    print(f"Response Time: {response.headers.get('X-Response-Time')}")

    return response.json()

# Usage
forecast = get_latest_forecast(country='Kenya')

# Convert to GeoDataFrame
gdf = gpd.GeoDataFrame.from_features(forecast['features'])
print(gdf.head())
```

### Example 2: Get Available Forecast Dates

```python
def get_forecast_dates():
    """Get list of available forecast dates"""
    url = f"{URLS['fastapi']}/merged-forecast/dates/"

    response = requests.get(url)
    response.raise_for_status()

    data = response.json()

    # Convert to DataFrame
    df = pd.DataFrame(data['dates'])
    df['date'] = pd.to_datetime(df['date'])

    return df

# Usage
dates_df = get_forecast_dates()
print(f"Available dates: {len(dates_df)}")
print(dates_df.head())
```

### Example 3: Get Forecast for Specific Date

```python
def get_forecast_by_date(date, country=None):
    """
    Get forecast for a specific date.

    Args:
        date (str): Date in YYYY-MM-DD format
        country (str, optional): Filter by country

    Returns:
        dict: GeoJSON FeatureCollection
    """
    url = f"{URLS['fastapi']}/merged-forecast/{date}/"

    params = {}
    if country:
        params['country'] = country

    response = requests.get(url, params=params)
    response.raise_for_status()

    # Check if fallback was used
    if 'X-Fallback' in response.headers:
        print(f"⚠️  Requested date not found, using fallback: {response.headers['X-Fallback-Date']}")

    return response.json()

# Usage
forecast = get_forecast_by_date('2025-11-19', country='Uganda')
gdf = gpd.GeoDataFrame.from_features(forecast['features'])
```

### Example 4: Get Administrative Boundaries (Django API)

```python
def get_admin_boundaries(level=0):
    """
    Get administrative boundaries.

    Args:
        level (int): Admin level (0=country, 1=state, 2=district)

    Returns:
        GeoDataFrame: Administrative boundaries
    """
    endpoint_map = {
        0: 'admin0',
        1: 'admin1',
        2: 'admin2'
    }

    url = f"{URLS['backend']}/{endpoint_map[level]}/"

    response = requests.get(url, params={'format': 'json'})
    response.raise_for_status()

    data = response.json()

    # Convert to GeoDataFrame
    features = data.get('results', data.get('features', []))
    gdf = gpd.GeoDataFrame.from_features(features)

    return gdf

# Usage
countries = get_admin_boundaries(level=0)
print(f"Found {len(countries)} countries")
print(countries[['name', 'iso_a2', 'iso_a3']].head())
```

### Example 5: Get Monitoring Stations

```python
def get_monitoring_stations(country=None):
    """
    Get monitoring stations.

    Args:
        country (str, optional): Filter by country name

    Returns:
        GeoDataFrame: Monitoring stations
    """
    url = f"{URLS['backend']}/monitoring-stations/"

    params = {'format': 'json'}
    if country:
        params['country'] = country

    response = requests.get(url, params=params)
    response.raise_for_status()

    data = response.json()

    # Handle paginated response
    features = data.get('results', data.get('features', []))
    gdf = gpd.GeoDataFrame.from_features(features)

    return gdf

# Usage
stations = get_monitoring_stations(country='Kenya')
print(f"Found {len(stations)} stations")
print(stations[['name', 'station_id', 'river']].head())
```

### Example 6: Get Rivers and Lakes (Django API)

```python
def get_water_features(feature_type='rivers', bbox=None):
    """
    Get rivers or lakes.

    Args:
        feature_type (str): 'rivers' or 'water-bodies'
        bbox (tuple, optional): (minx, miny, maxx, maxy)

    Returns:
        GeoDataFrame: Water features
    """
    url = f"{URLS['backend']}/{feature_type}/"

    params = {'format': 'geojson'}
    if bbox:
        params['bbox'] = ','.join(map(str, bbox))

    response = requests.get(url, params=params)
    response.raise_for_status()

    data = response.json()
    gdf = gpd.GeoDataFrame.from_features(data['features'])

    return gdf

# Usage - Get rivers in a specific area
# Bbox for East Africa: (minx, miny, maxx, maxy)
bbox = (29.0, -5.0, 42.0, 5.0)
rivers = get_water_features('rivers', bbox=bbox)
print(f"Found {len(rivers)} rivers")

lakes = get_water_features('water-bodies')
print(f"Found {len(lakes)} lakes")
```

### Example 7: Ensemble Control Points (FastAPI)

```python
def get_ensemble_forecast():
    """Get ensemble control points with forecast data"""
    url = f"{URLS['fastapi']}/ensemble-control-points"

    response = requests.get(url)
    response.raise_for_status()

    print(f"Total Features: {response.headers.get('X-Feature-Count')}")
    print(f"Features with Data: {response.headers.get('X-Features-With-Data')}")
    print(f"Forecast Date: {response.headers.get('X-Forecast-Date')}")

    data = response.json()
    gdf = gpd.GeoDataFrame.from_features(data['features'])

    return gdf

# Usage
ensemble = get_ensemble_forecast()
print(ensemble.head())
```

### Example 8: Time Series Analysis

```python
def get_forecast_time_series(station_id, days=7):
    """
    Get forecast time series for a specific station.

    Args:
        station_id (str): Station ID
        days (int): Number of days to retrieve

    Returns:
        DataFrame: Time series data
    """
    # Get available dates
    dates_df = get_forecast_dates()

    # Get last N days
    recent_dates = dates_df.head(days)

    time_series = []

    for _, row in recent_dates.iterrows():
        date_str = row['date'].strftime('%Y-%m-%d')

        # Get forecast for this date
        forecast = get_forecast_by_date(date_str)

        # Find the specific station
        for feature in forecast['features']:
            if feature['properties'].get('station_id') == station_id:
                time_series.append({
                    'date': date_str,
                    'forecast_date': row['date'],
                    **feature['properties']
                })
                break

    return pd.DataFrame(time_series)

# Usage
station_time_series = get_forecast_time_series('STATION_001', days=7)
print(station_time_series)

# Plot
import matplotlib.pyplot as plt

plt.figure(figsize=(12, 6))
plt.plot(station_time_series['date'], station_time_series['discharge_cms'])
plt.xticks(rotation=45)
plt.xlabel('Date')
plt.ylabel('Discharge (m³/s)')
plt.title(f'Forecast Time Series - Station {station_id}')
plt.tight_layout()
plt.show()
```

### Example 9: Spatial Analysis with Multiple Layers

```python
def analyze_flood_risk(date, country):
    """
    Analyze flood risk by combining forecast and geographic data.

    Args:
        date (str): Forecast date (YYYY-MM-DD)
        country (str): Country name

    Returns:
        dict: Analysis results
    """
    # Get forecast data
    forecast = get_forecast_by_date(date, country=country)
    forecast_gdf = gpd.GeoDataFrame.from_features(forecast['features'])

    # Get admin boundaries
    admin2 = get_admin_boundaries(level=2)

    # Get rivers
    rivers = get_water_features('rivers')

    # Spatial join: which districts have high-risk stations?
    high_risk = forecast_gdf[forecast_gdf['risk_level'] == 'high']

    districts_at_risk = gpd.sjoin(
        admin2,
        high_risk,
        how='inner',
        predicate='contains'
    )

    return {
        'total_stations': len(forecast_gdf),
        'high_risk_stations': len(high_risk),
        'districts_affected': len(districts_at_risk),
        'districts_list': districts_at_risk['name'].unique().tolist()
    }

# Usage
risk_analysis = analyze_flood_risk('2025-11-19', 'Kenya')
print(json.dumps(risk_analysis, indent=2))
```

### Example 10: Batch Download All Forecasts

```python
def download_all_forecasts(output_dir='forecasts'):
    """
    Download all available forecasts.

    Args:
        output_dir (str): Directory to save forecasts
    """
    import os

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # Get available dates
    dates_df = get_forecast_dates()

    print(f"Downloading {len(dates_df)} forecasts...")

    for idx, row in dates_df.iterrows():
        date_str = row['date'].strftime('%Y-%m-%d')

        try:
            # Get forecast
            forecast = get_forecast_by_date(date_str)

            # Save to file
            filename = os.path.join(output_dir, f'forecast_{date_str}.geojson')
            with open(filename, 'w') as f:
                json.dump(forecast, f)

            print(f"✓ Downloaded {date_str} ({row['feature_count']} features)")

        except Exception as e:
            print(f"✗ Failed to download {date_str}: {e}")

    print(f"\nAll forecasts saved to {output_dir}/")

# Usage
# download_all_forecasts()
```

---

## Authentication

### Current Setup

Most API endpoints are currently **public** (no authentication required) for development.

### Adding Authentication (Production)

For production deployments, add authentication:

```python
import requests

# Get authentication token
def get_auth_token(username, password):
    """Login and get JWT token"""
    url = f"{URLS['backend']}/auth/login/"

    response = requests.post(url, json={
        'username': username,
        'password': password
    })
    response.raise_for_status()

    return response.json()['token']

# Use token in requests
token = get_auth_token('your_username', 'your_password')

headers = {
    'Authorization': f'Bearer {token}'
}

response = requests.get(f"{URLS['backend']}/admin0/", headers=headers)
```

---

## Error Handling

### Standard Error Responses

All APIs return standard HTTP status codes:

- `200` - Success
- `400` - Bad Request (invalid parameters)
- `401` - Unauthorized (authentication required)
- `403` - Forbidden (insufficient permissions)
- `404` - Not Found (resource doesn't exist)
- `500` - Internal Server Error

### Example Error Handling

```python
def safe_api_call(url, params=None):
    """
    Make API call with proper error handling.

    Args:
        url (str): API endpoint URL
        params (dict, optional): Query parameters

    Returns:
        dict or None: Response data or None if error
    """
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            print(f"❌ Resource not found: {url}")
        elif e.response.status_code == 500:
            print(f"❌ Server error: {e.response.text}")
        else:
            print(f"❌ HTTP error {e.response.status_code}: {e.response.text}")
        return None

    except requests.exceptions.ConnectionError:
        print(f"❌ Cannot connect to {url}")
        print("   Make sure Docker containers are running:")
        print("   docker ps")
        return None

    except requests.exceptions.Timeout:
        print(f"❌ Request timed out: {url}")
        return None

    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return None

# Usage
data = safe_api_call(f"{URLS['fastapi']}/merged-forecast/latest/")
if data:
    print(f"✓ Got {len(data['features'])} features")
```

### Checking API Health

```python
def check_api_health():
    """Check if all APIs are responding"""
    apis = {
        'FastAPI': f"{URLS['fastapi']}/health",
        'TiPg': f"{URLS['tipg']}/healthz",
        'Django': f"{URLS['backend']}/admin0/"  # Basic endpoint
    }

    print("Checking API health...\n")

    for name, url in apis.items():
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                print(f"✓ {name:10} OK")
            else:
                print(f"✗ {name:10} Error {response.status_code}")
        except Exception as e:
            print(f"✗ {name:10} Unreachable - {e}")

# Usage
check_api_health()
```

---

## Quick Reference

### Common Tasks

| Task | API | Endpoint |
|------|-----|----------|
| Get latest forecast | FastAPI | `GET /api/fast/merged-forecast/latest/` |
| Get forecast dates | FastAPI | `GET /api/fast/merged-forecast/dates/` |
| Get countries | Django | `GET /api/admin0/` |
| Get monitoring stations | Django | `GET /api/monitoring-stations/` |
| Get rivers | Django | `GET /api/rivers/` |
| Get lakes | Django | `GET /api/water-bodies/` |
| Get vector tiles | TiPg | `GET /tipg/collections/{id}/tiles/{z}/{x}/{y}` |
| API documentation | Django | `GET /api/schema/swagger-ui/` |

### Performance Tips

1. **Use FastAPI for large GeoJSON**: 2-3x faster than Django for forecast data
2. **Cache responses**: Store frequently accessed data locally
3. **Use pagination**: Limit large queries with `?limit=` parameter
4. **Filter early**: Use `country=` or `bbox=` to reduce response size
5. **Use vector tiles**: For map visualization, MVT tiles are 90% smaller than GeoJSON
6. **Check headers**: Monitor `X-Response-Time` and `X-Cache-Hit` headers

---

## Support & Resources

- **API Schema**: `http://localhost:8094/api/schema/swagger-ui/`
- **Admin Panel**: `http://localhost:8090/admin/`
- **Docker Logs**: `docker logs floodwatch_backend` / `floodwatch_fastapi` / `floodwatch_tipg`
- **Health Checks**: All services have `/health` or `/healthz` endpoints

---

**Last Updated**: 2025-11-19
**Version**: 1.0.0
