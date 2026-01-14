# East Africa Flood Watch (EAFW) - Comprehensive Changes Documentation

**Generated:** 2026-01-03
**Branch Status:** Local is behind `origin/main` by 21 commits + has local uncommitted changes

---

## Table of Contents

1. [Infrastructure Changes](#1-infrastructure-changes)
   - [Docker Compose](#11-docker-compose)
   - [CMS Dockerfile](#12-cms-dockerfile)
   - [Mapviewer Dockerfile](#13-mapviewer-dockerfile)
   - [Nginx Configuration](#14-nginx-configuration)
2. [New Services Added](#2-new-services-added)
   - [MapServer](#21-mapserver)
   - [MapCache](#22-mapcache)
   - [Tile Server](#23-tile-server)
   - [Celery (Future)](#24-celery-background-tasks)
3. [API Changes](#3-api-changes)
   - [FloodProofs API](#31-floodproofs-api)
   - [Multimodal Forecast API](#32-multimodal-forecast-api)
   - [Admin Boundary API](#33-admin-boundary-api)
   - [Impact Data API](#34-impact-data-api)
4. [CMS Model Changes](#4-cms-model-changes)
   - [Navbar Model](#41-navbar-model)
   - [Footer Model](#42-footer-model)
   - [Homepage Model](#43-homepage-model)
   - [Site Theme Model](#44-site-theme-model)
   - [Report Pages](#45-report-pages)
   - [Language Settings](#46-language-settings)
   - [Multimodal Settings](#47-multimodal-cluster-settings)
   - [Data Upload Model](#48-multimodal-data-upload)
5. [Block System](#5-block-system)
   - [Report Blocks](#51-report-blocks)
   - [Navigation Blocks](#52-navigation-blocks)
   - [Homepage Blocks](#53-homepage-blocks)
6. [Internationalization](#6-internationalization)
7. [Configuration Changes](#7-configuration-changes)

---

## 1. Infrastructure Changes

### 1.1 Docker Compose

**File:** `docker-compose.yml`

#### Container Naming Changes
| Before | After | Description |
|--------|-------|-------------|
| `${CNTR_NAME_PREFIX:-eahw-}cms-pgdb` | `${DB_CNTR_NAME:-eafw-pgdb}` | Individual env var for each container |
| `${CNTR_NAME_PREFIX:-eahw-}cms-web` | `${WEB_CNTR_NAME:-eafw-cms-web}` | More flexible naming |

#### Image Versioning
- Changed from `:latest` or untagged to explicit `:v1.0.0` tags
- Example: `postgis/postgis:${PG_VERSION:-v1.0.0}`

#### Build Context Changes
```yaml
# Before
build:
  context: .
  dockerfile: ./docker/cms/Dockerfile
  ssh: ["default"]

# After
build:
  context: ..
  dockerfile: geomanager-web/docker/cms/Dockerfile
```
**Reason:** Build context moved to parent directory to allow copying `geomanager` and `forecastmanager` dependencies.

#### SELinux Support
All volume mounts now include `:z` suffix for SELinux compatibility:
```yaml
volumes:
  - ${CMS_STATIC_VOLUME}:/home/app/static:z
  - ${CMS_MEDIA_VOLUME}:/home/app/media:z
```

#### New Environment Variables
```yaml
# FTP credentials for data sync
- SFTP_HOST=${SFTP_HOST}
- SFTP_PORT=${SFTP_PORT:-22}
- SFTP_USERNAME=${SFTP_USERNAME}
- SFTP_PASSWORD=${SFTP_PASSWORD}
- ENSEMBLE_FTP_HOST=${ENSEMBLE_FTP_HOST}
- ENSEMBLE_FTP_PORT=${ENSEMBLE_FTP_PORT:-21}
- ENSEMBLE_FTP_USER=${ENSEMBLE_FTP_USER}
- ENSEMBLE_FTP_PASSWORD=${ENSEMBLE_FTP_PASSWORD}
- ENSEMBLE_FTP_DIR=${ENSEMBLE_FTP_DIR}
```

#### Template Volume Mount
Added live template reloading support:
```yaml
- ./home/templates:/app/home/templates:z
```

---

### 1.2 CMS Dockerfile

**File:** `docker/cms/Dockerfile`

#### Build Stage Simplification
| Before | After |
|--------|-------|
| 2-stage build (builder + runner) | Single-stage build |
| SSH-based git clone | Local COPY from parent directory |
| `${APP_HOME}/.venv` | `/opt/venv` (UV_PROJECT_ENVIRONMENT) |

#### Key Changes

**1. GDAL Version Update**
```dockerfile
ARG GDAL_VERSION=3.10.1  # Was 3.10.0
```

**2. UV Package Manager**
```dockerfile
# Now uses pre-built binary
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
```

**3. Dependency Copying**
```dockerfile
# Local dependencies now copied from parent directory
COPY ./geomanager /home/geomanager
COPY ./forecastmanager /home/forecastmanager
```

**4. Additional Packages**
```dockerfile
RUN uv pip install --python $UV_PROJECT_ENVIRONMENT gunicorn uvicorn
RUN uv pip install --python $UV_PROJECT_ENVIRONMENT watchdog
```

**5. Gunicorn Path**
```yaml
# Command changed to use venv path
/opt/venv/bin/gunicorn geomanagerweb.asgi
```

---

### 1.3 Mapviewer Dockerfile

**File:** `docker/mapviewer/Dockerfile`

#### Build Approach Change
| Before | After |
|--------|-------|
| SSH clone from GitHub | Copy from local `geomapviewer/` directory |
| `node:20-slim` | `node:20-bookworm-slim` |

#### New Environment Variable
```dockerfile
ARG ADMIN_BOUNDARY_API
ENV ADMIN_BOUNDARY_API=$ADMIN_BOUNDARY_API
```
Added to `.env` file for the mapviewer to access admin boundary filtering.

#### Explicit Port Exposure
```dockerfile
EXPOSE 3000
```

---

### 1.4 Nginx Configuration

**File:** `docker/nginx/nginx.conf`

#### CORS Headers for Media
```nginx
location /media/ {
    alias /wagtail_media/;
    # New CORS headers for vector tile icons
    add_header Access-Control-Allow-Origin *;
    add_header Access-Control-Allow-Methods "GET, OPTIONS";
    add_header Access-Control-Allow-Headers "Origin, Content-Type, Accept";
}
```

#### Mapviewer Routing Change
```nginx
# /mapviewer/ now handled by Django (root location) to include navbar
# Direct Next.js proxy removed - Django will proxy internally
```

#### New Tile Server Routes
```nginx
# Handle malformed mapviewer URLs
location ~ ^/tileserv/([^/]+)/(.+)$ {
    rewrite ^/tileserv/([^/]+)/(.+)$ /pg/tileserv/$1.$2 break;
    proxy_pass http://geomanager_tileserv:7800;
    # CORS headers included
}

location /pg/tileserv/ {
    proxy_pass http://geomanager_tileserv:7800/pg/tileserv/;
    # CORS headers included
}
```

#### New MapServer/MapCache Routes
```nginx
location /mapserver/ {
    proxy_pass http://geomanager_mapserver/mapserver/;
}

location /mapcache/ {
    proxy_pass http://geomanager_mapcache/mapcache/;
}
```

---

## 2. New Services Added

### 2.1 MapServer

**Container:** `eafw-mapserver`
**Port:** `127.0.0.1:8482`
**Image:** `icpac/eafw-mapserver:v1.0.0`

```yaml
environment:
  - MS_DEBUGLEVEL=${MS_DEBUGLEVEL:-2}
  - MS_ERRORFILE=${MS_ERRORFILE:-stderr}
  - MAPFILES_DIR=${MS_MAPFILES_DIR:-/opt/mapfiles}
  - MS_MAPFILE=${MS_MAPFILES_DIR:-/opt/mapfiles}/mapserver.map
  - WGS84_GRID_EXTENTS=${WGS84_GRID_EXTENTS:-21 -12 52 23}
  - MS_SERVICE_URL=${MS_SERVICE_URL:-http://localhost:8482/mapserver/}
  - DB_HOST=${PGB_HOST:-pgbouncer}
  - DB_MAP_USER=${CMS_DB_USER}
  - DB_MAP_USER_PASSWORD=${CMS_DB_PASSWORD}
  - DB_NAME=${CMS_DB_NAME}
  - DB_PORT=${PGB_PORT:-6432}
```

**Purpose:** Provides WMS/WFS services for raster and vector data rendering.

---

### 2.2 MapCache

**Container:** `eafw-mapcache`
**Port:** `127.0.0.1:8483`
**Image:** `icpac/eafw-mapcache:v1.0.0`

```yaml
environment:
  - SERVICE_URL=${MC_SERVICE_URL:-http://localhost:8483/mapcache/}
  - SOURCE_URL=${MC_SOURCE_URL:-http://geomanager_mapserver/mapserver/?}
  - WEB_GRID_EXTENTS=${WEB_GRID_EXTENTS:-2337709 -1329087 5792092 2632018}
  - WGS84_GRID_EXTENTS=${WGS84_GRID_EXTENTS:-21 -12 52 23}
  - TILES_DIR=${APP_TILES_DIR:-/opt/tiles}
  - TILESET_EXPIRE_SEC=${MC_TILESET_EXPIRE_SEC:-3600}
```

**Purpose:** Tile caching layer in front of MapServer for improved performance.

---

### 2.3 Tile Server

**Container:** `eafw-tileserv`
**Port:** `127.0.0.1:7471`
**Image:** `pramsey/pg_tileserv:v1.0.0`

```yaml
environment:
  - DATABASE_URL=postgresql://${CMS_DB_USER}:${CMS_DB_PASSWORD}@geomanager_db:5432/${CMS_DB_NAME}
  - TS_BASEPATH=/pg/tileserv
  - TS_DEBUG=${TILESERV_DEBUG:-false}
```

**Purpose:** Serves vector tiles directly from PostGIS database tables.

---

### 2.4 Celery Background Tasks

**Status:** Commented out (ready for future use)

**New Containers (when enabled):**
- `eafw-redis` - Message broker
- `eafw-celery-worker` - Background task worker
- `eafw-celery-beat` - Scheduled task scheduler

**Planned Tasks:**
- Daily multimodal forecast data sync from FTP
- Automated data processing

---

## 3. API Changes

**File:** `geomanagerweb/api.py`

### 3.1 FloodProofs API

#### Available Dates Endpoint
**URL:** `/api/floodproofs/dates/`

```python
class FloodProofsAvailableDatesView(View):
    """API endpoint to get available FloodProofs forecast dates"""

    def get(self, request):
        # Returns list of available dates from MergedDeterministicGeoJSON
        return JsonResponse({
            'timestamps': dates_list,
            'dates': dates_list,
            'count': len(dates_list)
        })
```

#### Data Endpoint
**URL:** `/api/floodproofs/data/`

Returns raw GeoJSON data for a specific date with feature counts.

#### GeoJSON with Alert Levels
**URL:** `/api/floodproofs/geojson/`

**Features:**
- Computes alert levels on-the-fly using PostgreSQL
- Returns processed GeoJSON with properties:
  - `station_id`, `station_name`, `river_name`
  - `alert_level` (Normal/Warning/Alarm/Emergency)
  - `discharge_gfs`, `discharge_icon`, `discharge_primary`
  - `threshold_alert`, `threshold_alarm`, `threshold_emergency`
  - `basin`, `admin_level_1`

**Alert Level Logic:**
```sql
CASE
    WHEN all thresholds = 0 THEN 'Normal'
    WHEN discharge >= threshold_emergency THEN 'Emergency'
    WHEN discharge >= threshold_alarm THEN 'Alarm'
    WHEN discharge >= threshold_alert THEN 'Warning'
    ELSE 'Normal'
END
```

---

### 3.2 Multimodal Forecast API

#### GeoJSON Endpoint
**URL:** `/api/multimodal/geojson/`

Returns multimodal ensemble forecast data as GeoJSON.

#### Clustered GeoJSON
**URL:** `/api/multimodal/clustered/`

**Parameters:**
- `zoom` (int): Zoom level for clustering granularity

**Features:**
- Server-side clustering using `ST_SnapToGrid`
- Grid size calculated: `10 / (2 ** zoom)`
- Returns clustered features with `point_count`

#### Available Dates
**URL:** `/api/multimodal/dates/`

Returns available forecast dates.

---

### 3.3 Admin Boundary API

**URL:** `/api/admin-boundaries/`

**Parameters:**
- `admin_level`: None=countries, 0=regions, 1=districts
- `unit_id`: Parent unit code
- `with_bbox`: Include bounding box (true/false)
- `country_id`: Filter by country (for admin level 1)

**Tables Used:**
- `impact.admin0` - Countries
- `impact.admin1` - Regions (name_1)
- `impact.admin2` - Districts (name_2)

**Response:**
```json
[
    {"code": "Kenya", "name": "Kenya", "bbox": {...}},
    {"code": "Ethiopia", "name": "Ethiopia", "bbox": {...}}
]
```

---

### 3.4 Impact Data API

**URL:** `/api/impact/dates/`

**Parameters:**
- `impact_type` (optional): Filter by impact type

Returns available forecast dates from `impact.floodproofs_impacts` table.

---

## 4. CMS Model Changes

**File:** `home/models.py`

### 4.1 Navbar Model

**New Model:** `Navbar` (Wagtail Page)

```python
class Navbar(Page):
    max_count = 1

    logo = ForeignKey("wagtailimages.Image")
    menu_items = StreamField([
        ("link", LinkBlock()),
        ("dropdown", LinkGroupBlock()),
    ])

    # Utility Bar Settings
    show_utility_bar = BooleanField(default=True)
    utility_email = EmailField()
    utility_phone = CharField()
    utility_links = StreamField([("link", LinkBlock())])
```

**Features:**
- Single navbar instance per site
- Flexible menu items (links or dropdowns)
- Utility bar with contact info and quick links

---

### 4.2 Footer Model

**Updated Model:** `Footer` (Wagtail Page)

```python
class Footer(Page):
    max_count = 1

    logo = ForeignKey("wagtailimages.Image")
    description = TextField()

    sections = StreamField([("section", LinkGroupBlock())])
    member_countries = StreamField([("country", CountryBlock())])
    partners = StreamField([("partner", LogoItemBlock())])

    copyright_organization = CharField(default="ICPAC")
    social_links = StreamField([("social_link", SocialLinkBlock())])
```

**New Features:**
- Country flags from CDN (using `CountryBlock`)
- Partner logos with descriptions
- Custom social media links

---

### 4.3 Homepage Model

**Updated Model:** `HomePage`

**New Fields:**

```python
# Weather Widget
show_weather_widget = BooleanField(default=False)
weather_widget_title = CharField(default="Weather Forecast")

# Action Cards
action_cards = StreamField([
    ("action", ActionCardBlock()),
])

# Map Preview
show_map_preview = BooleanField(default=True)
map_preview_title = CharField(default="Live Flood Monitoring")
map_preview_subtitle = CharField()
```

**New Context Data:**
- `dataset_categories` with homepage descriptions
- `forecasts` from forecastmanager (weather widget)
- `navbar` and `footer` objects

---

### 4.4 Site Theme Model

**New Model:** `SiteTheme`

```python
class SiteTheme(models.Model):
    name = CharField()
    is_active = BooleanField(default=True)

    # Theme Colors
    primary_color = CharField(default="#034930")
    secondary_color = CharField(default="#198754")
    accent_color = CharField(default="#fbc02d")
    primary_text_color = CharField(default="#ffffff")
    secondary_text_color = CharField(default="#333333")
    background_color = CharField(default="#ffffff")

    # Wave Animation Settings
    enable_wave_animation = BooleanField(default=False)
    wave_color_1 = CharField(default="#e0f7fa")
    wave_color_2 = CharField(default="#4dd0e1")
    wave_color_3 = CharField(default="#0097a7")
    wave_opacity = IntegerField(default=60)
    wave_height = IntegerField(default=150)
```

**Features:**
- Color picker panels in admin
- Water-themed wave animation for hero section
- Only one active theme at a time

---

### 4.5 Report Pages

#### Report Index Page
```python
class ReportIndexPage(Page):
    template = "reports/report_index_page.html"
    subpage_types = ["home.FloodBulletinPage", "home.SituationReportPage"]

    introduction = RichTextField()
```

#### Flood Bulletin Page
```python
class FloodBulletinPage(Page):
    report_number = CharField()  # e.g., 'FB-2024-001'
    report_date = DateField()
    valid_from = DateField()
    valid_to = DateField()

    header_logo = ForeignKey("wagtailimages.Image")
    issuing_authority = CharField(default="ICPAC")

    overall_alert_level = CharField(choices=[
        ('normal', 'Normal'),
        ('warning', 'Warning'),
        ('alarm', 'Alarm'),
        ('emergency', 'Emergency'),
    ])

    executive_summary = RichTextField()

    content = StreamField([
        ("text", ReportTextBlock()),
        ("alert_summary", AlertSummaryBlock()),
        ("statistics", StatisticsRowBlock()),
        ("affected_areas", AffectedAreasTableBlock()),
        ("map", MapEmbedBlock()),
        ("forecast", ForecastBlock()),
        ("image", ReportImageBlock()),
        ("contacts", ContactsBlock()),
    ])

    disclaimer = TextField()
```

#### Situation Report Page
```python
class SituationReportPage(Page):
    report_number = CharField()  # e.g., 'SITREP-2024-001'
    report_date = DateField()
    reporting_period_start = DateField()
    reporting_period_end = DateField()

    event_name = CharField()  # e.g., 'Kenya Floods - October 2024'
    event_type = CharField(choices=[
        ('flood', 'Flood'),
        ('flash_flood', 'Flash Flood'),
        ('riverine_flood', 'Riverine Flood'),
        ('coastal_flood', 'Coastal Flood'),
    ])

    situation_overview = RichTextField()

    content = StreamField([
        # Same blocks as FloodBulletinPage
        ("response_actions", ResponseActionsBlock()),  # Additional block
    ])

    recommendations = RichTextField()
    disclaimer = TextField()
```

---

### 4.6 Language Settings

**New Model:** `LanguageSettings` (Wagtail Setting)

```python
LANGUAGE_CHOICES = [
    ("en", "English"),
    ("sw", "Swahili"),
    ("ar", "Arabic"),
    ("am", "Amharic"),
    ("fr", "French"),
    ("so", "Somali"),
    ("om", "Oromo"),
    ("ti", "Tigrinya"),
    ("pt", "Portuguese"),
    ("es", "Spanish"),
]

class EnabledLanguage(Orderable):
    language_setting = ParentalKey("LanguageSettings")
    language_code = CharField(choices=LANGUAGE_CHOICES)
    is_default = BooleanField(default=False)

@register_setting
class LanguageSettings(ClusterableModel, BaseGenericSetting):
    # Inline panel for enabled languages
```

**Features:**
- CMS-configurable language list
- Drag-and-drop language ordering
- Default language selection

---

### 4.7 Multimodal Cluster Settings

**New Model:** `MultimodalClusterSettings` (Wagtail Setting)

```python
@register_setting
class MultimodalClusterSettings(BaseGenericSetting):
    enable_clustering = BooleanField(default=True)

    # Alert Thresholds (m³/s)
    warning_threshold = FloatField(default=10.0)
    alarm_threshold = FloatField(default=50.0)
    emergency_threshold = FloatField(default=100.0)

    # Alert Colors
    normal_color = CharField(default="#808080")
    warning_color = CharField(default="#ffc107")
    alarm_color = CharField(default="#ff9800")
    emergency_color = CharField(default="#d32f2f")

    # Cluster Config
    cluster_max_zoom = IntegerField(default=12)
    cluster_radius = IntegerField(default=50)

    def get_config(self):
        """Return settings for frontend consumption."""
        return {
            "enableClustering": self.enable_clustering,
            "thresholds": {...},
            "colors": {...},
        }
```

---

### 4.8 Multimodal Data Upload

**New Model:** `MultimodalDataUpload`

```python
class MultimodalDataUpload(models.Model):
    title = CharField()
    data_date = DateField()
    source = CharField(choices=[
        ("upload", "File Upload"),
        ("ftp", "FTP Server"),
        ("drive", "Google Drive"),
    ])

    csv_file = FileField(upload_to="multimodal/csv/")
    shapefile = FileField(upload_to="multimodal/shapefiles/")

    status = CharField(choices=[
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    ])

    processing_log = TextField()
    feature_count = IntegerField()
    matched_count = IntegerField()
    geojson_data = JSONField()
```

**Methods:**
- `process_upload()` - Main processing pipeline
- `_load_control_points()` - Load from DB or shapefile
- `_parse_csv_files()` - Parse Zone CSV files
- `_create_geojson()` - Generate GeoJSON
- `_save_to_forecast_table()` - Save to database

---

## 5. Block System

**File:** `home/blocks.py`

### 5.1 Report Blocks

| Block | Description |
|-------|-------------|
| `ReportTextBlock` | Rich text with optional heading |
| `AlertSummaryBlock` | Alert status table with levels |
| `StatisticsRowBlock` | Key statistics display |
| `AffectedAreasTableBlock` | Table of affected areas |
| `MapEmbedBlock` | Embedded map or static image |
| `ForecastBlock` | Multi-day forecast display |
| `ReportImageBlock` | Image with caption |
| `ResponseActionsBlock` | Response actions list (SitRep) |
| `ContactsBlock` | Contact information |

### 5.2 Navigation Blocks

| Block | Description |
|-------|-------------|
| `LinkBlock` | Single link with target option |
| `LinkGroupBlock` | Dropdown menu with multiple links |
| `SocialLinkBlock` | Social media link with icon |
| `CountryBlock` | Country with auto-loaded flag |
| `LogoItemBlock` | Partner logo with description |

### 5.3 Homepage Blocks

| Block | Description |
|-------|-------------|
| `InfoBlock` | Title, items list, and image |
| `FeatureBlock` | Feature with icon and description |
| `ActionCardBlock` | Action card with link |

---

## 6. Internationalization

**File:** `geomanagerweb/settings/base.py`

### Supported Languages
```python
LANGUAGES = [
    ("en", "English"),
    ("sw", "Swahili"),      # Kenya, Uganda, Tanzania
    ("ar", "Arabic"),       # Sudan, South Sudan, Djibouti, Somalia, Eritrea
    ("am", "Amharic"),      # Ethiopia
    ("fr", "French"),       # Djibouti
    ("so", "Somali"),       # Somalia
    ("om", "Oromo"),        # Ethiopia
]
```

### Locale Paths
```python
LOCALE_PATHS = [
    os.path.join(BASE_DIR, "locale"),
    os.path.join(PROJECT_DIR, "locale"),
    os.path.join(BASE_DIR, "home", "locale"),
]
```

### Wagtail Localization
```python
WAGTAIL_I18N_ENABLED = True
WAGTAIL_CONTENT_LANGUAGES = LANGUAGES

INSTALLED_APPS = [
    "wagtail_localize",
    "wagtail_localize.locales",
    "django_deep_translator",
    ...
]
```

---

## 7. Configuration Changes

**File:** `geomanagerweb/settings/base.py`

### New Context Processors
```python
"context_processors": [
    ...
    "home.context_processors.theme_context",
    "home.context_processors.navbar_context",
    "home.context_processors.language_context",
],
```

### Celery Configuration (Commented)
```python
# CELERY_BROKER_URL = "redis://localhost:6379/0"
# CELERY_RESULT_BACKEND = "redis://localhost:6379/0"
# CELERY_BEAT_SCHEDULE = {
#     "sync-multimodal-daily": {
#         "task": "home.tasks.sync_multimodal_daily",
#         "schedule": crontab(hour=14, minute=30),
#     },
# }
```

### Multimodal FTP Configuration
```python
MULTIMODAL_FTP_HOST = env.str("ENSEMBLE_FTP_HOST", "")
MULTIMODAL_FTP_PORT = env.int("ENSEMBLE_FTP_PORT", 21)
MULTIMODAL_FTP_USER = env.str("ENSEMBLE_FTP_USER", "")
MULTIMODAL_FTP_PASSWORD = env.str("ENSEMBLE_FTP_PASSWORD", "")
MULTIMODAL_FTP_DIR = env.str("ENSEMBLE_FTP_DIR", "")
```

---

## Summary of Key Changes

### New Features
1. **FloodProofs Integration** - Real-time flood forecast data with alert levels
2. **Multimodal Forecasts** - Ensemble forecast visualization with clustering
3. **Admin Boundary Filtering** - Hierarchical location filtering
4. **Report System** - Flood bulletins and situation reports
5. **Theme System** - CMS-configurable colors and wave animations
6. **Multi-language Support** - IGAD member state languages
7. **MapServer Stack** - Full OGC services (WMS/WFS/WMTS)

### Infrastructure Improvements
1. **Build optimization** - Single-stage Docker builds with uv
2. **SELinux support** - Volume mounts with `:z` suffix
3. **CORS support** - Headers for all API endpoints
4. **Tile serving** - pg_tileserv for vector tiles

### API Endpoints Added
| Endpoint | Purpose |
|----------|---------|
| `/api/floodproofs/dates/` | Available forecast dates |
| `/api/floodproofs/geojson/` | Processed FloodProofs data |
| `/api/multimodal/geojson/` | Multimodal forecast data |
| `/api/multimodal/clustered/` | Clustered forecast points |
| `/api/admin-boundaries/` | Admin boundary filtering |
| `/api/impact/dates/` | Impact forecast dates |

---

## New Migrations Required

The following new migrations exist locally but are not in the remote:
- `0015_mergeddeterministicgeojson_and_more`
- `0016_homepage_show_weather_widget_and_more`
- `0017_language_settings`
- `0018_wave_animation_settings`
- `0019_create_multimodal_clustered_functions`
- `0020_add_action_cards_to_homepage`
- `0021_add_map_preview_fields`
- `0022_add_utility_bar_fields`
- `0023_add_image_to_action_card`
- `0024_add_category_description`
