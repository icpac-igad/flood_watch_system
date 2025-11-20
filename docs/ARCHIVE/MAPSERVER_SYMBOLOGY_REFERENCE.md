# MapServer Symbology Reference
## Complete styling guide for migrating to TiTiler + TiPg

---

## Vector Layers (PostGIS → TiPg)

### Admin0 - Country Boundaries
```
Geometry: POLYGON
Table: pgstac."Impact_admin0"
Style:
  - Outline Color: RGB(0, 0, 0) - Black
  - Outline Width: 4px
  - Fill Opacity: 0 (transparent)
  - Outline Opacity: 100%
Purpose: Thick black country boundaries
```

### Admin1 - Province Boundaries
```
Geometry: POLYGON
Table: pgstac."Impact_admin1"
Style:
  - Outline Color: RGB(80, 80, 80) - Dark Gray
  - Outline Width: 2px
  - Fill Opacity: 0 (transparent)
  - Outline Opacity: 80%
Purpose: Medium gray province boundaries
```

### Admin2 - District Boundaries
```
Geometry: POLYGON
Table: pgstac."Impact_admin2"
Style:
  - Outline Color: RGB(130, 130, 130) - Light Gray
  - Outline Width: 1px
  - Fill Opacity: 0 (transparent)
  - Outline Opacity: 60%
Purpose: Light gray district boundaries
```

### Water Bodies - Lakes
```
Geometry: POLYGON
Table: pgstac."Impact_waterbodies"
Style:
  - Fill Color: RGB(85, 160, 210) - Blue
  - Outline Color: RGB(85, 160, 210) - Same blue
  - Outline Width: 1px
  - Fill Opacity: 100%
Purpose: Opaque blue lakes (hides rivers below)
```

### Rivers - HydroRIVERS
```
Geometry: LINE
Table: pgstac."Impact_hydrorivers"
Classification Field: ord_clas (Stream Order)

Style by Stream Order:
1. Order 6+ (Largest Rivers):
   - Color: RGB(245, 250, 255) - Almost white
   - Width: 1.2px
   - Opacity: 20%

2. Order 4-5 (Large Tributaries):
   - Color: RGB(220, 235, 245) - Semi-white
   - Width: 0.8px
   - Opacity: 25%

3. Order 1-3 (Small Rivers):
   - Color: RGB(30, 90, 160) - Dark Blue
   - Width: 0.5px
   - Opacity: 35%

Purpose: 3-tier river visualization, larger rivers lighter
```

### Monitoring Stations
```
Geometry: POINT
Table: pgstac."Impact_monitoringstation"
Style:
  - Symbol: Circle
  - Size: 8px
  - Fill Color: RGB(255, 0, 0) - Red
  - Outline Color: RGB(150, 0, 0) - Dark Red
  - Outline Width: 2px
Purpose: Red circle markers for stations
```

---

## Raster Layers (COG → TiTiler)

### Inundation Maps
```
File Location: /app/data/inundation_maps/**/*.tif
Format: Cloud Optimized GeoTIFF (COG)

TiTiler Configuration:
  - Colormap: blues
  - Rescale: 0-1
  - NoData: 0
  - Tile URL: /cog/tiles/{z}/{x}/{y}.png?url={file_url}&rescale=0,1&colormap_name=blues&nodata=0

Purpose: Flood extent visualization in blue shades
```

### Alert Levels
```
File Location: /app/data/merged_alerts/**/*.tif
Format: Cloud Optimized GeoTIFF (COG)

TiTiler Configuration:
  - Colormap: rdylgn_r (Red-Yellow-Green Reversed)
  - Rescale: 1-4
  - NoData: 0
  - Tile URL: /cog/tiles/{z}/{x}/{y}.png?url={file_url}&rescale=1,4&colormap_name=rdylgn_r&nodata=0

Alert Level Colors (rdylgn_r):
  - Level 4 (Emergency): Red
  - Level 3 (Alarm): Orange
  - Level 2 (Warning): Yellow
  - Level 1 (Advisory): Green
  - Level 0 (No Alert): Transparent White

Purpose: Color-coded alert levels
```

### Flood Hazard Maps
```
File Location: /app/mapserver_data/hazards/**/*.tif
Format: Cloud Optimized GeoTIFF (COG)

Classification:
  - No Flood: Transparent White
  - Low Risk: Yellow (RGB 255, 255, 0)
  - Medium Risk: Orange (RGB 255, 165, 0)
  - High Risk: Dark Orange (RGB 255, 100, 0)
  - Very High Risk: Red (RGB 255, 0, 0)

Purpose: Risk-based flood hazard mapping
```

### IBEW Impact Layers
```
File Location: shapefiles/ibew_shapefiles/{date}_FPimpacts-{layer_name}
Format: Shapefile (Polygon)

Classification Field: flood_tot

Style:
  1. No Impact (flood_tot = 0):
     - Fill: RGB(240, 240, 240) - Light Gray
     - Outline: RGB(200, 200, 200) - Gray
     - Width: 0.5px
  
  2. Impact (flood_tot > 0):
     - Fill: RGB(255, 0, 0) - Red
     - Outline: RGB(150, 150, 150) - Gray
     - Width: 0.5px
     - Opacity: 70%

Purpose: Impact assessment polygons showing affected areas
```

---

## Frontend Alert Status Markers

### Station Status Icons
```
Location: /public/map-markers/

Icons:
  1. Normal.svg → Green circle
  2. Warning.svg → Yellow/Orange triangle
  3. Alarm.svg → Orange/Red diamond
  4. Emergency.svg → Red square

Purpose: Visual indicators for monitoring station status
```

---

## Migration Notes

### TiPg Vector Tile Configuration
```json
{
  "admin0": {
    "stroke": "#000000",
    "stroke-width": 4,
    "stroke-opacity": 1.0,
    "fill-opacity": 0
  },
  "admin1": {
    "stroke": "#505050",
    "stroke-width": 2,
    "stroke-opacity": 0.8,
    "fill-opacity": 0
  },
  "admin2": {
    "stroke": "#828282",
    "stroke-width": 1,
    "stroke-opacity": 0.6,
    "fill-opacity": 0
  },
  "waterbodies": {
    "fill": "#55A0D2",
    "stroke": "#55A0D2",
    "stroke-width": 1,
    "fill-opacity": 1.0
  },
  "rivers": {
    "classification": "ord_clas",
    "styles": {
      "6+": {"stroke": "#F5FAFF", "stroke-width": 1.2, "stroke-opacity": 0.2},
      "4-5": {"stroke": "#DCEBF5", "stroke-width": 0.8, "stroke-opacity": 0.25},
      "1-3": {"stroke": "#1E5AA0", "stroke-width": 0.5, "stroke-opacity": 0.35}
    }
  },
  "monitoring_stations": {
    "marker-color": "#FF0000",
    "marker-size": 8,
    "marker-stroke": "#960000",
    "marker-stroke-width": 2
  }
}
```

### TiTiler Colormap Definitions
```python
# Import custom colormaps
from rio_tiler.colormap import cmap

# Blues colormap (0-1 range, lighter to darker blue)
BLUES_COLORMAP = cmap.get("blues")

# Alert Level colormap (1-4 range, green→yellow→orange→red)
ALERT_COLORMAP = cmap.get("rdylgn_r")

# Custom Hazard colormap
HAZARD_COLORMAP = {
    0: (255, 255, 255, 0),      # Transparent
    1: (255, 255, 0, 180),      # Yellow - Low Risk
    2: (255, 165, 0, 200),      # Orange - Medium Risk
    3: (255, 100, 0, 220),      # Dark Orange - High Risk
    4: (255, 0, 0, 255)         # Red - Very High Risk
}
```

---

## Database Connection
```
Host: postgis (Docker) / localhost:5432 (Local)
Database: floodwatch
User: postgres
Password: floodwatch_pass
Schema: pgstac
Tables:
  - Impact_admin0
  - Impact_admin1
  - Impact_admin2
  - Impact_waterbodies
  - Impact_hydrorivers
  - Impact_monitoringstation
```

---

**Generated:** 2025-11-05  
**Purpose:** Reference guide for maintaining identical visualization when migrating from MapServer to TiTiler+TiPg  
**Status:** Complete symbology documentation ready for eoAPI implementation
