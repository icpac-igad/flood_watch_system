# FloodWatch Database Model

## Database: `geomanager_web`

---

## Schema Overview

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           FloodWatch Database Model                              │
├─────────────────────────────────────────────────────────────────────────────────┤
│  Schemas: public, floodproofs, alerts, grids, rivers, impact                    │
│  Tables: 145 | Views: 2 | Materialized Views: 10 | MVT Functions: 21            │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 1. FLOODPROOFS Schema (Deterministic Flood Forecasts)

### Tables

#### `floodproofs.merged_deterministic_geojson`
Stores daily GeoJSON data from FloodProofs deterministic model outputs.

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| data_date | DATE | Forecast reference date |
| date_string | VARCHAR | Date as string (YYYYMMDD) |
| geojson_data | JSONB | Full GeoJSON FeatureCollection (979 features/day) |
| feature_count | INTEGER | Number of features in GeoJSON |
| file_count | INTEGER | Number of source files merged |
| file_path | VARCHAR | Source file path |
| processed_by | VARCHAR | Processing job identifier |
| created_at | TIMESTAMPTZ | Record creation time |
| updated_at | TIMESTAMPTZ | Last update time |

**GeoJSON Feature Properties:**
- `SEC_NAME`: Station name
- `Q_THR1`: Warning threshold (m³/s)
- `Q_THR2`: Alarm threshold (m³/s)
- `Q_THR3`: Emergency threshold (m³/s)
- `time_series_discharge_simulated-gfs`: Hourly discharge forecast values
- `BASIN`, `ADMIN_B_L1`: Basin and admin location

### Materialized Views

#### `floodproofs.discharge_points`
Flattened view of latest GeoJSON features as individual point records.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Feature ID |
| data_date | DATE | Data date |
| station_id, station_name | VARCHAR | Station identifiers |
| discharge_gfs, discharge_icon, discharge_primary | NUMERIC | Discharge values |
| threshold_alert, threshold_alarm, threshold_emergency | NUMERIC | Alert thresholds |
| alert_level | VARCHAR | Calculated: Normal/Warning/Alarm/Emergency |
| geom | GEOMETRY(Point, 4326) | Station location |

### MVT Functions (pg_tileserv)

#### `floodproofs.discharge_points_clustered(z, x, y, cluster_zoom, data_date)`
Clustered vector tiles with alert level calculation.

**Parameters:**
- `cluster_zoom` (default 7): Zoom level for individual points
- `data_date`: Filter by date (default: latest)

**Returns:** Clustered or individual points with `alert_level`, `alert_priority`, `point_count`

---

## 2. PUBLIC Schema (Multimodal & Core Data)

### Materialized Views

#### `public.multimodal_points`
Combined flood forecast data from multiple models (GeoSFM, FloodProofs, Mike Hydro).

| Column | Type | Description |
|--------|------|-------------|
| id | BIGINT | Unique identifier |
| data_date | DATE | Data date |
| x, y | NUMERIC | Grid coordinates |
| point_id | INTEGER | Grid point ID |
| zone, gridcode | INTEGER | Grid zone info |
| has_data | BOOLEAN | Data availability flag |
| admin_name | TEXT | Admin boundary name |
| forecast_date | DATE | Forecast reference date |
| daily_max, daily_avg, daily_min | NUMERIC | Daily discharge stats |
| geosfm | NUMERIC | GeoSFM model output |
| floodproof | NUMERIC | FloodProofs model output |
| mike_hydro_rfe, mike_hydro_chirp, mike_hydro_imerg | NUMERIC | Mike Hydro outputs |
| forecasts_json | JSONB | Time series forecasts |
| geom | GEOMETRY(Point, 4326) | Point location |

### MVT Functions

#### `public.multimodal_points_clustered(z, x, y, cluster_zoom)`
Clustered multimodal points with threshold-based alert levels.

**Alert Thresholds (configurable via `home_multimodalclustersettings`):**
- Emergency: ≥100
- Alarm: 50-100
- Warning: 10-50
- Normal: <10

#### `public.multimodal_points_clustered_whca(z, x, y, cluster_zoom)`
WHCA (5-country) filtered version.

### Key Tables

#### `public.multimodal_ensemble_forecast`
| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| point_id | INTEGER | Reference to grid point |
| forecast_date | DATE | Forecast date |
| data_date | DATE | Data reference date |
| model_name | VARCHAR | Model identifier |
| forecast_values | JSONB | Forecast time series |
| created_at | TIMESTAMPTZ | Creation time |

#### `public.floodproofs_ensemble_points`
| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| station_id | VARCHAR | FloodProofs station ID |
| forecast_date | DATE | Forecast date |
| ensemble_data | JSONB | Ensemble forecast data |
| geom | GEOMETRY | Station location |

---

## 3. ALERTS Schema (Daily Alert Calculations)

### Tables

#### `alerts.daily_hmc_alerts`
Daily HMC (Hydrological Model Chain) alert levels per grid cell.

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| grid_id | INTEGER | FK to grids.grid_01dd |
| alert_date | DATE | Alert date |
| alert_level | INTEGER | 1=Normal, 2=Warning, 3=Alarm, 4=Emergency |
| created_at | TIMESTAMP | Creation time |

#### `alerts.flood_hazard`
Flood hazard levels per grid cell.

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| grid_id | INTEGER | FK to grids.grid_01dd |
| hazard_date | DATE | Hazard date |
| hazard_level | INTEGER | Hazard classification |
| created_at | TIMESTAMP | Creation time |

#### `alerts.wrf_streamflow`
WRF model streamflow outputs.

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| grid_id | INTEGER | FK to grids.grid_01dd |
| flow_date | DATE | Flow date |
| flow_level | INTEGER | Flow classification |
| created_at | TIMESTAMP | Creation time |

---

## 4. GRIDS Schema (Spatial Grid System)

### Tables

#### `grids.grid_01dd`
0.1 degree grid cells covering East Africa.

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Grid cell ID (primary key) |
| xcol | INTEGER | X column index |
| yrow | INTEGER | Y row index |
| cell | GEOMETRY | Grid cell polygon |

#### `grids.grid_clipped_admin0`
Grid cells clipped to country boundaries.

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| grid_id | INTEGER | FK to grid_01dd |
| admin0_id | INTEGER | Country ID |
| clipped_geom | GEOMETRY | Clipped grid cell |

### Materialized Views

- `grids.admin0_boundary` - Country boundaries
- `grids.whca_boundary` - WHCA region boundary
- `grids.whca_grid_ids` - Grid IDs within WHCA
- `grids.country_boundaries` - All country boundaries
- `grids.valid_grid_cells_admin0` - Valid grid cells per country

---

## 5. RIVERS Schema (Hydrological Features)

### Tables

#### `rivers.osm_waterways`
OpenStreetMap waterways for the region.

| Column | Type | Description |
|--------|------|-------------|
| gid | SERIAL | Primary key |
| geom | GEOMETRY | River/waterway geometry |
| osm_id2 | VARCHAR | OSM feature ID |
| name, name_en | VARCHAR | Waterway names |
| waterway | VARCHAR | Type: river, stream, canal |
| intermittent, seasonal | VARCHAR | Flow characteristics |
| width | VARCHAR | Waterway width |

### MVT Functions

- `rivers.osm_waterways_default(z, x, y)` - All waterways
- `rivers.osm_waterways_whca(z, x, y)` - WHCA filtered

---

## 6. IMPACT Schema (Flood Impact Data)

### Tables

#### `impact.admin0`, `impact.admin1`, `impact.admin2`
Administrative boundaries at different levels.

#### `impact.floodproofs_impacts`
Flood impact assessments per admin unit.

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| forecast_date | DATE | Forecast date |
| impact_type | VARCHAR | Impact category |
| code_adm | VARCHAR | Admin code |
| name_0, name_1 | VARCHAR | Country/region names |
| pop_tot | BIGINT | Total population |
| flood_tot | BIGINT | Flooded population |
| tot_crop, tot_graze | BIGINT | Agricultural impact |
| flood_perc | FLOAT | Flood percentage |
| flood_clas | INTEGER | Impact classification |
| geom | GEOMETRY | Admin boundary |

#### `impact.water_bodies`
Lakes and water bodies.

#### `impact.hydro_rivers`
HydroSHEDS river network.

### MVT Functions

- `impact.admin0_whca`, `impact.admin1_whca` - WHCA boundaries
- `impact.popaff25`, `impact.popaff100` - Population affected
- `impact.popage25`, `impact.popage100` - Vulnerable age groups
- `impact.popmob25`, `impact.popmob100` - Reduced mobility
- `impact.healthtot` - Health facilities affected

---

## 7. HOME App Tables (CMS Configuration)

### Key Tables

#### `home_multimodalclustersettings`
Configures multimodal clustering behavior and thresholds.

| Column | Type | Default | Description |
|--------|------|---------|-------------|
| enable_clustering | BOOLEAN | true | Enable cluster mode |
| warning_threshold | FLOAT | 10.0 | Warning level threshold |
| alarm_threshold | FLOAT | 50.0 | Alarm level threshold |
| emergency_threshold | FLOAT | 100.0 | Emergency level threshold |
| normal_color | VARCHAR | #808080 | Normal marker color |
| warning_color | VARCHAR | #ffc107 | Warning marker color |
| alarm_color | VARCHAR | #ff9800 | Alarm marker color |
| emergency_color | VARCHAR | #d32f2f | Emergency marker color |
| cluster_max_zoom | INTEGER | 12 | Max zoom for clustering |
| cluster_radius | INTEGER | 50 | Cluster radius in pixels |

#### `home_merged_deterministic_geojson`
Backup/duplicate of floodproofs data.

#### `home_ensemble_forecast_geojson`
Ensemble forecast GeoJSON storage.

#### `home_mapserverconfig`
MapServer/MapCache service configuration.

#### `home_sitetheme`
Site theming and wave animation settings.

---

## 8. GEOMANAGER Tables (Layer Configuration)

### `geomanager_vectortilelayer`
Vector tile layer configuration.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| title | VARCHAR | Layer title |
| base_url | VARCHAR | Tile URL template |
| render_layers_json | JSONB | MapLibre GL style |
| legend | JSONB | Legend configuration |
| time_parameter_name | VARCHAR | Time filter parameter |
| tile_json_url | VARCHAR | Timestamps API URL |
| dataset_id | UUID | FK to geomanager_dataset |

### `geomanager_vectortilelayericon`
Custom icons for vector tile layers.

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| name | VARCHAR | Icon identifier |
| color | VARCHAR | Icon color (hex) |
| file | VARCHAR | Icon file path |
| layer_id | UUID | FK to vectortilelayer |

---

## Entity Relationship Diagram (Simplified)

```
┌─────────────────────┐     ┌──────────────────────┐
│   grids.grid_01dd   │     │ floodproofs.merged_  │
│   ─────────────────│     │ deterministic_geojson│
│   id (PK)          │     │ ───────────────────  │
│   xcol, yrow       │     │ id (PK)              │
│   cell (GEOMETRY)  │◄────│ data_date            │
└────────┬───────────┘     │ geojson_data (JSONB) │
         │                 └──────────┬───────────┘
         │                            │
         ▼                            ▼
┌─────────────────────┐     ┌──────────────────────┐
│ alerts.daily_hmc_   │     │ floodproofs.         │
│ alerts              │     │ discharge_points     │
│ ──────────────────  │     │ (MATERIALIZED VIEW)  │
│ grid_id (FK)        │     │ ────────────────────│
│ alert_date          │     │ station_id           │
│ alert_level         │     │ discharge values     │
└─────────────────────┘     │ alert_level          │
                            └──────────────────────┘
         │
         ▼
┌─────────────────────┐     ┌──────────────────────┐
│ public.multimodal_  │     │ geomanager_          │
│ points              │     │ vectortilelayer      │
│ (MATERIALIZED VIEW) │     │ ───────────────────  │
│ ──────────────────  │     │ id (UUID PK)         │
│ point_id            │     │ title                │
│ daily_max/avg/min   │     │ base_url             │
│ model outputs       │◄────│ render_layers_json   │
│ forecasts_json      │     │ legend               │
└─────────────────────┘     └──────────┬───────────┘
                                       │
                                       ▼
                            ┌──────────────────────┐
                            │ geomanager_          │
                            │ vectortilelayericon  │
                            │ ───────────────────  │
                            │ name                 │
                            │ file (icon path)     │
                            │ layer_id (FK)        │
                            └──────────────────────┘
```

---

## pg_tileserv MVT Functions Summary

| Schema | Function | Purpose |
|--------|----------|---------|
| public | multimodal_points_clustered | Clustered multimodal forecasts |
| public | multimodal_points_clustered_whca | WHCA filtered clusters |
| public | multimodal_points_whca | Individual points (WHCA) |
| floodproofs | discharge_points_clustered | FloodProofs with date filter |
| rivers | osm_waterways_default | River network tiles |
| rivers | osm_waterways_whca | WHCA river tiles |
| impact | admin0_whca, admin1_whca | Admin boundaries |
| impact | popaff*, popage*, popmob* | Impact analysis layers |

---

## Data Flow

```
External Data Sources
        │
        ▼
┌───────────────────┐
│  FloodWatch Jobs  │ (Python ingestion scripts)
│  ─────────────────│
│  • GeoSFM outputs │
│  • FloodProofs    │
│  • Mike Hydro     │
│  • WRF outputs    │
└────────┬──────────┘
         │
         ▼
┌───────────────────┐     ┌─────────────────────┐
│  PostgreSQL DB    │────►│  pg_tileserv        │
│  (PostGIS)        │     │  (MVT Functions)    │
│  ─────────────────│     └──────────┬──────────┘
│  • Raw GeoJSON    │                │
│  • Materialized   │                ▼
│    Views          │     ┌─────────────────────┐
│  • Alert calcs    │     │  Frontend (MapLibre)│
└───────────────────┘     │  ─────────────────  │
                          │  • Clustered points │
                          │  • Alert icons      │
                          │  • Date filtering   │
                          └─────────────────────┘
```

---

*Generated: 2025-12-14*
