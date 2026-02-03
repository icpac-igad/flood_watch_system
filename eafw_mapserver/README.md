# EAFW MapServer

East Africa Flood Watch MapServer - a modular PostGIS-based map service for flood alert data.

## Architecture

- **PostGIS Database**: Uses the shared CMS database to store grid geometries and alert data
- **MapServer**: Renders WMS layers from database queries
- **MapCache**: Tile caching for performance

## Setup

### 1. Initialize Database

Run the initialization script against the CMS database:

```bash
psql -h localhost -p 5431 -U your_user -d your_db -f scripts/init_database.sql
```

Or via docker:

```bash
docker exec -i eafw-pgdb psql -U gis -d geomanager < ../eafw-mapserver/scripts/init_database.sql
```

### 2. Build and Start Services

From `geomanager-web` directory:

```bash
docker-compose build geomanager_mapserver geomanager_mapcache
docker-compose up -d geomanager_mapserver geomanager_mapcache
```

### 3. Ingest Alert Data

```bash
pip install -r scripts/requirements.txt
python scripts/ingest_daily_alerts.py \
    --host localhost \
    --port 5431 \
    --dbname geomanager \
    --user gis \
    /path/to/hmc_alert_daily_*.tif
```

## MapServer Endpoints

- WMS GetCapabilities: `http://localhost:8482/mapserver?SERVICE=WMS&REQUEST=GetCapabilities`
- WMS GetMap: `http://localhost:8482/mapserver?SERVICE=WMS&REQUEST=GetMap&LAYERS=daily_hmc_alert&time=2024-11-28&...`

## Directory Structure

```
eafw-mapserver/
├── database/initdb/        # SQL initialization scripts (standalone mode)
├── mapserver/
│   ├── mapfiles/           # MapServer configuration
│   │   ├── config/         # Database, WMS metadata
│   │   ├── layers/         # Layer definitions
│   │   ├── classifications/# Style classes
│   │   └── shared/         # Common includes
│   ├── Dockerfile          # MapServer container
│   └── nginx.conf          # Nginx config
├── mapcache/
│   ├── Dockerfile          # MapCache container
│   ├── mapcache_config.json # Tile cache config
│   └── generate_mapcache_config.py
└── scripts/
    ├── init_database.sql   # Database setup
    ├── ingest_daily_alerts.py
    └── requirements.txt
```

## Adding New Layers

1. Create SQL function in `scripts/` or as Django migration
2. Create MapServer layer in `mapserver/mapfiles/layers/`
3. Add classification in `mapserver/mapfiles/classifications/`
4. Include layer in `mapserver/mapfiles/mapserver.map`
5. Add mapcache source and tileset in `mapcache/mapcache_config.json`
