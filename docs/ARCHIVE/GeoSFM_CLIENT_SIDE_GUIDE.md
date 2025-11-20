# GeoSFM Client-Side Loading Guide

## 🎯 Architecture Overview

**GeoSFM uses a different approach than Floodproofs:**

### Floodproofs (Server-Side):
```
SFTP Server → Daily Merge Script → API serves merged data
```

### GeoSFM (Client-Side):
```
Frontend → Backend generates signed URLs → Frontend downloads from GCS → Local shapefile merge → Display
```

## 🔐 Why Client-Side with Signed URLs?

**Security:** GCS credentials stay on the server. Frontend gets time-limited (15-minute) URLs to download data.

**Benefits:**
- ✅ No GCS credentials exposed to browser
- ✅ Reduced server processing load
- ✅ Direct GCS downloads (fast)
- ✅ Client-side shapefile merging with local data

---

## 📡 API Endpoints

### 1. Get Signed URLs for a Date
```http
GET /api/geosfm/signed-urls/?date=2025-10-21
```

**Response:**
```json
{
  "date": "2025-10-21",
  "urls": [
    {
      "filename": "forecast_001.json",
      "url": "https://storage.googleapis.com/...", 
      "size": 125340,
      "updated": "2025-10-21T12:00:00Z"
    }
  ],
  "count": 3,
  "expires_in": "15 minutes"
}
```

### 2. List Available Dates
```http
GET /api/geosfm/gcs-dates/
```

**Response:**
```json
{
  "dates": ["2025-10-21", "2025-10-20", "2025-10-19"],
  "count": 3
}
```

---

## ⚙️ GCS Setup (Required Environment Variables)

Add these 3 environment variables to your `.env` file or deployment configuration:

```bash
GCS_PROJECT_ID           # Your Google Cloud project ID
GCS_BUCKET_NAME          # Bucket containing GeoSFM forecasts
GCS_CREDENTIALS_JSON     # Path to service account JSON file
```

### GCS Bucket Structure Expected:
```
your-bucket/
└── geosfm/
    └── 2025/
        └── 10/
            └── 21/
                ├── forecast_001.json
                ├── forecast_002.json
                └── ...
```

### Service Account Permissions:
Your service account needs:
- **Storage Object Viewer** (`roles/storage.objectViewer`)
- **Storage Object Creator** (for signed URL generation)

---

## 💻 Frontend Implementation Example

```javascript
// Example: Load GeoSFM forecast for a specific date
async function loadGeoSFMForecast(date) {
  try {
    // Step 1: Get signed URLs from backend
    const response = await fetch(`/api/geosfm/signed-urls/?date=${date}`);
    const data = await response.json();
    
    if (!data.urls || data.urls.length === 0) {
      console.log('No GeoSFM data for this date');
      return null;
    }
    
    // Step 2: Download all forecast JSON files from GCS
    const forecastPromises = data.urls.map(async (item) => {
      const res = await fetch(item.url);
      return res.json();
    });
    
    const forecasts = await Promise.all(forecastPromises);
    
    // Step 3: Merge forecasts into single object
    const mergedForecasts = {};
    forecasts.forEach(forecast => {
      Object.assign(mergedForecasts, forecast);
    });
    
    // Step 4: Load local shapefile (or use cached GeoJSON)
    const stationsGeoJSON = await loadStationsShapefile();
    
    // Step 5: Merge forecast data with station geometries
    const features = stationsGeoJSON.features.map(station => {
      const stationId = station.properties.station_id;
      return {
        ...station,
        properties: {
          ...station.properties,
          forecast: mergedForecasts[stationId] || null
        }
      };
    });
    
    return {
      type: 'FeatureCollection',
      features: features
    };
    
  } catch (error) {
    console.error('Failed to load GeoSFM forecast:', error);
    return null;
  }
}

// Helper: Load shapefile (convert to GeoJSON if needed)
async function loadStationsShapefile() {
  // Option 1: Use pre-converted GeoJSON
  const response = await fetch('/static/geosfm_stations.geojson');
  return response.json();
  
  // Option 2: Convert shapefile in browser using shpjs
  // import shp from 'shpjs';
  // const geojson = await shp('/static/geosfm_stations.zip');
  // return geojson;
}
```

---

## 📊 Comparison: Floodproofs vs GeoSFM

| Feature | Floodproofs | GeoSFM |
|---------|-------------|---------|
| **Data Source** | SFTP Server | Google Cloud Storage |
| **Processing** | Server-side merge | Client-side merge |
| **API Endpoint** | `/api/merged-forecast/` | `/api/geosfm/signed-urls/` |
| **Data Format** | Complete GeoJSON | Signed URLs → JSON |
| **Shapefile Merge** | Server (Python) | Client (JavaScript) |
| **Caching** | 1 hour | 10 minutes (URLs) |
| **Credentials** | SFTP (server-side) | GCS (server-side) |

---

## 🚀 Quick Start

### 1. Add GCS Environment Variables
```bash
# In backend/.env or your deployment environment:
GCS_PROJECT_ID = "your-project-id"
GCS_BUCKET_NAME = "your-bucket-name"
GCS_CREDENTIALS_JSON = "/path/to/service-account.json"
```

### 2. Test API
```bash
curl http://localhost:8090/api/geosfm/gcs-dates/
curl "http://localhost:8090/api/geosfm/signed-urls/?date=2025-10-21"
```

### 3. Frontend Integration
- Call `/api/geosfm/signed-urls/?date=YYYY-MM-DD`
- Download JSON files from signed URLs
- Merge with local shapefile
- Display on map (same as Floodproofs)

---

## 🔒 Security Notes

✅ **Safe:**
- GCS credentials stay on server
- Signed URLs expire after 15 minutes
- Each URL is time-limited and cryptographically signed

❌ **Unsafe:**
- Don't expose `GCS_CREDENTIALS_JSON` to browser
- Don't make bucket public (unless data is truly public)
- Don't reuse signed URLs after expiration

---

## 📝 Summary

**GeoSFM = Client-side approach**
- Backend generates secure, temporary signed URLs
- Frontend downloads data directly from GCS
- Frontend merges with local shapefile
- Same map display as Floodproofs

**Result:** Secure, efficient, scalable! 🎉
