# FloodWatch System Guide

A beginner-friendly guide to understanding and working with the FloodWatch system.

---

## What is FloodWatch?

FloodWatch is a **flood monitoring and forecasting system** for East Africa. It shows predicted river discharge (water flow) from multiple forecasting models on an interactive map.

---

## System Components (Simple Overview)

Think of FloodWatch like a restaurant:

| Component | Restaurant Analogy | What It Does |
|-----------|-------------------|--------------|
| **PostgreSQL Database** | Kitchen storage | Stores all the data |
| **Django CMS (geomanager-web)** | Kitchen | Prepares data, manages content |
| **MapViewer (geomapviewer)** | Dining room | Where users see the map |
| **pg_tileserv** | Food delivery | Sends map tiles to browser |
| **Nginx** | Front door | Routes visitors to the right place |

```
User's Browser → Nginx → MapViewer (shows map)
                     ↓
              Django CMS → Database
                     ↓
              pg_tileserv (map tiles)
```

---

## Key Features We Built

### 1. Clustered Forecast Points

**What:** Groups nearby forecast points into clusters on the map.

**Why:** With 1000+ points, showing them all makes the map cluttered. Clusters make it cleaner.

**How it works:**
- Zoom out → Points group into clusters with numbers (e.g., "45" means 45 points)
- Zoom in → Clusters expand to show individual points
- Click a cluster → Zooms in to see the points

**Colors mean:**
- 🔴 **Red** = Emergency (very high water flow)
- 🟠 **Orange** = Alarm (high water flow)
- 🟡 **Yellow** = Warning (elevated water flow)
- ⚪ **Gray** = Normal

### 2. Multi-Model Forecasts

**What:** Shows predictions from 5 different forecasting models:

| Model | Description |
|-------|-------------|
| GeoSFM | NASA satellite-based model |
| FloodProofs | CIMA Foundation model |
| Mike Hydro RFE | DHI model with RFE rainfall |
| Mike Hydro CHIRP | DHI model with CHIRP rainfall |
| Mike Hydro IMERG | DHI model with IMERG rainfall |

**Why multiple models?** Different models have different strengths. Showing all of them helps forecasters make better decisions.

### 3. Point-Specific Thresholds (Planned)

**Important:** Each forecast point should have its **own threshold values** based on:
- Historical river discharge data at that location
- Local flood risk characteristics
- Upstream/downstream relationships

This means:
- Point A might have: Warning=50, Alarm=100, Emergency=200 m³/s
- Point B might have: Warning=10, Alarm=25, Emergency=50 m³/s

**Current Status:**
- Per-point thresholds need to be added to the data by the hydrology team
- Currently using global CMS thresholds as fallback
- Once point thresholds are in the data, the system will use them automatically

**Expected Data Format** (to be added to each point):
```json
{
  "ID": 3114,
  "warning_threshold": 50.0,
  "alarm_threshold": 100.0,
  "emergency_threshold": 200.0,
  "forecasts": [...]
}
```

### 4. CMS-Configurable Settings

For **default/fallback** settings, admins can configure:

- Default alert colors
- Whether clustering is enabled
- Cluster size and zoom levels

**How to access:** CMS Admin → Settings → Multimodal Cluster Settings

**Note:** These are used when point-specific thresholds are not available.

---

## CMS Settings Reference

All settings configurable from the CMS Admin panel:

### Multimodal Cluster Settings
**Location:** Settings → Multimodal Cluster Settings

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| Enable Clustering | Boolean | True | Turn clustering on/off |
| Warning Threshold | Float | 10.0 | Default warning level (m³/s) |
| Alarm Threshold | Float | 50.0 | Default alarm level (m³/s) |
| Emergency Threshold | Float | 100.0 | Default emergency level (m³/s) |
| Normal Color | Color | #808080 | Gray color for normal |
| Warning Color | Color | #ffc107 | Yellow color for warning |
| Alarm Color | Color | #ff9800 | Orange color for alarm |
| Emergency Color | Color | #d32f2f | Red color for emergency |
| Cluster Max Zoom | Integer | 12 | Zoom level where clustering stops |
| Cluster Radius | Integer | 50 | Pixel radius for grouping |

### Site Settings
**Location:** Settings → Tab Icon

| Setting | Type | Description |
|---------|------|-------------|
| Tab Icon | Image | Browser favicon |

### Mapserver Config
**Location:** Settings → Mapserver Config

| Setting | Type | Description |
|---------|------|-------------|
| Service Title | Text | WMS/WFS service name |
| Service Purpose | Text | Service description |
| Service Provider | Text | Organization name |
| Provider URL | URL | Organization website |
| Office Country | Text | Country location |
| Office City | Text | City location |
| Physical Address | Text | Street address |
| Email Address | Email | Contact email |
| Contact Name | Text | Contact person/department |
| Default Language | Text | Platform language |
| Service Fee | Text | Fee information |
| Use Terms | Text | Terms of service |

### Language Settings
**Location:** Settings → Language Settings

Configure which languages are available on the site.

| Setting | Type | Description |
|---------|------|-------------|
| Enabled Languages | List | Languages to enable |
| Default Language | Selection | Primary language |

---

## File Structure (Where Things Are)

```
geomanager-web/
│
├── home/                      # FloodWatch customizations
│   ├── models.py              # Database tables/settings
│   ├── blocks.py              # Page building blocks
│   ├── mapviewer_config.py    # Map configuration API
│   └── templates/             # HTML templates
│
├── geomanagerweb/
│   ├── api.py                 # API endpoints
│   ├── urls.py                # URL routes
│   └── settings/              # Django settings
│
├── docker/
│   ├── cms/Dockerfile         # CMS container
│   ├── mapviewer/Dockerfile   # MapViewer container
│   └── nginx/nginx.conf       # Web server config
│
└── docker-compose.yml         # All services definition
```

```
geomapviewer/src/
│
├── components/map/components/
│   ├── multimodal-cluster/    # Clustering feature
│   │   └── component.jsx      # Main clustering code
│   │
│   └── popup/components/
│       └── multimodel-chart/  # Forecast chart
│           └── component.jsx  # Chart code
│
├── providers/config-provider/ # Settings from CMS
│   ├── actions.js             # Fetch settings
│   └── selectors.js           # Access settings
│
└── utils/
    └── layer-utils.js         # Map layer helpers
```

---

## How Data Flows

### 1. Data Ingestion (Getting the Data)

```
External Sources           FloodWatch Jobs           Database
─────────────────         ─────────────────         ──────────
GeoSFM (SFTP)      →
FloodProofs (FTP)  →      Merge & Process    →     Store GeoJSON
Mike Hydro (FTP)   →
```

### 2. Displaying Data (Showing to Users)

```
Database                  API                      MapViewer
────────                  ───                      ─────────
GeoJSON data    →    /api/multimodal/geojson/   →   Cluster Layer
                                                    ↓
                                                 User sees map
```

---

## Common Tasks

### Adding a New Setting

1. **Add to model** (`home/models.py`):
```python
new_setting = models.CharField(default="value")
```

2. **Add to admin panel** (same file, in `panels`):
```python
panels = [
    FieldPanel("new_setting"),
]
```

3. **Create migration**:
```bash
docker exec eafw-cms-web /opt/venv/bin/python /home/app/manage.py makemigrations
docker exec eafw-cms-web /opt/venv/bin/python /home/app/manage.py migrate
```

4. **Rebuild**:
```bash
docker-compose build geomanager_web
docker-compose up -d geomanager_web
```

### Changing Alert Colors

1. Go to CMS Admin (http://localhost:8180/cms-admin/)
2. Click **Settings** → **Multimodal Cluster Settings**
3. Change the color values
4. Save
5. Refresh the MapViewer - colors update automatically!

### Changing Alert Thresholds

Same as colors - go to CMS Admin → Settings → Multimodal Cluster Settings

| Field | What it means |
|-------|---------------|
| Warning Threshold | Water flow (m³/s) above this = Yellow |
| Alarm Threshold | Water flow (m³/s) above this = Orange |
| Emergency Threshold | Water flow (m³/s) above this = Red |

### Rebuilding After Code Changes

**CMS changes:**
```bash
docker-compose build geomanager_web
docker-compose up -d geomanager_web
```

**MapViewer changes:**
```bash
docker-compose build geomanager_mapviewer
docker-compose up -d geomanager_mapviewer
```

**Both:**
```bash
docker-compose build
docker-compose up -d
```

---

## API Endpoints

| Endpoint | What it returns |
|----------|-----------------|
| `/api/multimodal/geojson/` | All forecast points with data |
| `/api/floodproofs/dates/` | Available forecast dates |
| `/api/floodproofs/geojson/?date=YYYY-MM-DD` | FloodProofs data for specific date |
| `/api/mapviewer-config/` | Map settings including cluster config |

### Example: Get forecast data

```bash
curl http://localhost:8180/api/multimodal/geojson/
```

Returns:
```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {"type": "Point", "coordinates": [34.9, 23.3]},
      "properties": {
        "ID": 3114,
        "forecasts": [
          {"date": "2025-12-04", "GeoSFM": "1.07", "daily_avg": "0.26"}
        ]
      }
    }
  ]
}
```

---

## Docker Services

| Service | What it does | Port |
|---------|--------------|------|
| `geomanager_db` | PostgreSQL database | 5431 |
| `geomanager_web` | Django CMS | 8181 |
| `geomanager_mapviewer` | Next.js map | 3130 |
| `geomanager_tileserv` | Vector tiles | 7471 |
| `geomanager_nginx` | Web server (main entry) | 8180 |

### Useful Docker Commands

```bash
# See running containers
docker ps

# View logs
docker-compose logs -f geomanager_web

# Restart a service
docker-compose restart geomanager_mapviewer

# Run Django command
docker exec eafw-cms-web /opt/venv/bin/python /home/app/manage.py [command]

# Database shell
docker exec -it eafw-pgdb psql -U [username] -d [database]
```

---

## Troubleshooting

### Map not loading?

1. Check if services are running: `docker ps`
2. Check logs: `docker-compose logs -f geomanager_mapviewer`
3. Check browser console (F12) for errors

### Clusters not showing?

1. Check if clustering is enabled in CMS Settings
2. Check if data exists: `curl http://localhost:8180/api/multimodal/geojson/`
3. Check browser console for errors

### Changes not appearing?

1. Did you rebuild? `docker-compose build [service]`
2. Did you restart? `docker-compose up -d [service]`
3. Did you clear browser cache? (Ctrl+Shift+R)

### Database changes not working?

1. Create migration: `docker exec eafw-cms-web /opt/venv/bin/python /home/app/manage.py makemigrations`
2. Apply migration: `docker exec eafw-cms-web /opt/venv/bin/python /home/app/manage.py migrate`

---

## Quick Reference

### URLs

| What | URL |
|------|-----|
| MapViewer | http://localhost:8180/mapviewer/ |
| CMS Admin | http://localhost:8180/cms-admin/ |
| API Root | http://localhost:8180/api/ |

### Key Files to Know

| File | Purpose |
|------|---------|
| `home/models.py` | Database models and CMS settings |
| `geomanagerweb/api.py` | API endpoints |
| `multimodal-cluster/component.jsx` | Clustering feature |
| `docker-compose.yml` | All service definitions |

---

*This guide covers the FloodWatch customizations. For general Geomanager/Wagtail documentation, see the official docs.*
