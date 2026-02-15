# Geomanager

**Geomanager** is a Wagtail-based geospatial data manager developed by ICPAC. It powers the CMS layer of the FloodWatch system.

## Overview

- **Version**: 0.7.2
- **License**: GPL-3.0
- **Python**: >= 3.11
- **Framework**: Django 4.2 + Wagtail 6.3

## Installation

```bash
pip install geomanager
```

Or install from GitHub:

```bash
pip install git+https://github.com/icpac-igad/flood_watch_system.git#subdirectory=eafw_cms/geomanager
```

## Features

- Raster file/tile layer management (COG support)
- Vector file/tile layer management (PostGIS)
- WMS layer integration and sync
- TileGL layer support
- Built-in tile serving via `large-image`
- Admin interface for layer styling (color ramps, classifications)
- Automated data ingestion via watchers
- Multi-language support (EN, FR, AR, AM, SW, ES)
- Area of Interest (AOI) management
- Administrative boundary management

## Key Dependencies

| Package | Purpose |
|---------|---------|
| Wagtail | CMS framework |
| Django REST Framework | API layer |
| Rasterio / GDAL | Raster data processing |
| Shapely / GeoPandas | Vector geometry |
| xarray / netCDF4 | Multi-dimensional data |
| large-image | Tile generation |
| Matplotlib / CairoSVG | Rendering |

## Management Commands

```bash
# Initialize geomanager (create default categories, settings)
python manage.py initialize_geomanager

# Ingest raster data
python manage.py ingest_geomanager_raster

# Process a directory of layers
python manage.py process_geomanager_layer_directory

# Trigger automated watchers
python manage.py trigger_watchers
```

## Package Structure

```
geomanager/
├── models/          # Django models (raster, vector, WMS, tile layers)
├── views/           # REST API views
├── viewsets/        # DRF ViewSets
├── serializers/     # DRF serializers
├── admin/           # Wagtail admin interface
├── forms/           # Django forms
├── utils/           # Utility modules
├── tasks/           # Background tasks (watchers, periodic)
├── management/      # Django management commands
├── migrations/      # Database migrations (69+)
├── templates/       # HTML templates
├── static/          # CSS/JS assets
├── locale/          # i18n translations
└── templatetags/    # Custom template tags
```
