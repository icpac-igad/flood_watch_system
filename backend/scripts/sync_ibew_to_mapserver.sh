#!/bin/bash

# Sync IBEW v2 shapefiles from data/merged to MapServer directory
# This script copies the latest IBEW v2 data for MapServer to serve

echo "======================================"
echo "🗂️  IBEW v2 Shapefile Sync"
echo "======================================"

# Source and destination directories
SOURCE_DIR="/home/koros/IGAD-ICPAC/Projects/FloodWatch/code/flood_watch_system/data/merged/2025"
DEST_DIR="/home/koros/IGAD-ICPAC/Projects/FloodWatch/code/flood_watch_system/data/shapefiles/ibew_shapefiles"

# Create destination directory if it doesn't exist
mkdir -p "$DEST_DIR"

# Find the latest date directory
LATEST_DATE=$(ls -d $SOURCE_DIR/*/*/*/ 2>/dev/null | sort -r | head -1)

if [ -z "$LATEST_DATE" ]; then
    echo "❌ No data found in $SOURCE_DIR"
    exit 1
fi

echo "📅 Latest data found: $(basename $(dirname $(dirname $LATEST_DATE)))/$(basename $(dirname $LATEST_DATE))/$(basename $LATEST_DATE)"
echo "📁 Source: $LATEST_DATE"
echo "📂 Destination: $DEST_DIR"
echo ""

# Required IBEW v2 layers (as per ibew_layers.map)
declare -a LAYERS=(
    "healthtot"
    "popaff100"
    "popaff25"
    "popafftot"
    "popage100"
    "popage25"
    "popmob100"
    "popmob25"
)

# Counter for tracking
COPIED=0
SKIPPED=0

# Copy each layer
for LAYER in "${LAYERS[@]}"; do
    echo "Processing layer: $LAYER"

    # Find shapefile for this layer
    SHAPEFILE=$(find "$LATEST_DATE" -name "*FPimpacts-${LAYER}.shp" 2>/dev/null | head -1)

    if [ -z "$SHAPEFILE" ]; then
        echo "  ⚠️  Not found: FPimpacts-$LAYER"
        continue
    fi

    # Get base name without extension
    BASE_NAME=$(basename "$SHAPEFILE" .shp)
    BASE_PATH="${SHAPEFILE%.shp}"

    # Copy all related files (.shp, .shx, .dbf, .prj, etc.)
    for FILE in ${BASE_PATH}.*; do
        if [ -f "$FILE" ]; then
            EXT="${FILE##*.}"
            DEST_FILE="$DEST_DIR/${LAYER}.${EXT}"

            # Copy file
            cp -f "$FILE" "$DEST_FILE"

            if [ $? -eq 0 ]; then
                echo "  ✅ Copied: ${LAYER}.${EXT}"
                ((COPIED++))
            else
                echo "  ❌ Failed: ${LAYER}.${EXT}"
            fi
        fi
    done
done

echo ""
echo "======================================"
echo "📊 SYNC SUMMARY"
echo "======================================"
echo "✅ Files copied: $COPIED"
echo ""
echo "🌐 TEST URLS:"
echo "======================================"
echo "WMS GetCapabilities:"
echo "http://localhost:8080/cgi-bin/mapserv?map=/etc/mapserver/ibew_layers.map&SERVICE=WMS&REQUEST=GetCapabilities"
echo ""
echo "Sample GetMap (Total People Affected):"
echo "http://localhost:8080/cgi-bin/mapserv?map=/etc/mapserver/ibew_layers.map&SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&LAYERS=popafftot&BBOX=30,-15,55,25&WIDTH=800&HEIGHT=600&FORMAT=image/png&SRS=EPSG:4326&TRANSPARENT=TRUE"
echo ""
echo "✨ Sync complete!"