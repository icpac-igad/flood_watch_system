# MapServer Configuration for Flood Watch System

## Overview
This directory contains MapServer mapfiles for the East Africa Flood Watch System.

## Files

### admin.map
- Basic administrative boundaries layer
- Used for vector boundary overlays

### ibew_legends.map
- **NEW**: Dedicated legend service for IBEW (Impact-Based Early Warning) layers
- Provides clean legend graphics without date placeholders
- Contains styled classes for all IBEW layer types

## IBEW Legend Layers

The `ibew_legends.map` file contains dedicated legend definitions for:

1. **healthtot** - Health Centers Affected
2. **popaff100** - People Affected (100cm flood depth)
3. **popaff25** - People Affected (25cm flood depth)
4. **popafftot** - Total People Affected
5. **popage100** - Vulnerable Age Groups (100cm flood depth)
6. **popage25** - Vulnerable Age Groups (25cm flood depth)
7. **popmob100** - Reduced Mobility (100cm flood depth)
8. **popmob25** - Reduced Mobility (25cm flood depth)

## Usage

### Frontend Integration
The frontend automatically uses the dedicated legend service for IBEW layers:
```javascript
// IBEW legend URL example:
http://197.254.1.10:8093/cgi-bin/mapserv?map=/etc/mapserver/mapfiles/ibew_legends.map&SERVICE=WMS&VERSION=1.1.0&REQUEST=GetLegendGraphic&LAYER=popaff25&FORMAT=image/png
```

### Deployment
- Mapfiles are automatically copied to `/var/www/html/mapfiles/` during container startup
- The entrypoint script ensures proper permissions and ownership
- Apache serves the mapfiles via CGI

## Color Schemes

### People Affected Layers (Blue-Green Scale)
- No Impact: Transparent
- Low: Light Yellow (#FFFFE6)
- Medium: Light Green (#A1DAB4)
- High: Teal (#41B6C4)
- Very High: Dark Blue (#225EA8)

### Vulnerable Age Groups (Red-Orange Scale)
- No Impact: Transparent
- Low: Light Pink (#FEE5D9)
- Medium: Orange (#FC9272)
- High: Red-Orange (#FB6A4A)
- Very High: Dark Red (#CB181D)

### Reduced Mobility (Orange-Brown Scale)
- No Impact: Transparent
- Low: Light Orange (#FFF7EC)
- Medium: Orange (#FEC44F)
- High: Dark Orange (#D95F0E)
- Very High: Brown (#993404)

## Troubleshooting

1. **Legend not displaying**: Check if the mapfile path is correct in the frontend
2. **Permission errors**: Ensure www-data has read access to mapfiles
3. **Style issues**: Verify CLASS definitions and color values in the mapfile

## Future Enhancements

- Add more sophisticated styling based on actual data ranges
- Implement dynamic legend generation based on real data statistics
- Add support for custom date-based legends if needed