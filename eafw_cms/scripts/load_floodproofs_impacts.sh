#!/bin/bash
# Load FloodProofs impact shapefiles into PostGIS
# Usage: ./load_floodproofs_impacts.sh [data_dir] [date]

DATA_DIR="${1:-/home/koros/IGAD-ICPAC/Projects/FloodWatch/code/flood_watch_system/mapserver_data/ibew}"
SPECIFIC_DATE="${2:-}"

# Database connection
DB_HOST="127.0.0.1"
DB_PORT="5431"
DB_NAME="geomanager_web"
DB_USER="geomanager"
DB_PASS="${DB_PASSWORD:?DB_PASSWORD env var required}"

PG_CONN="PG:host=$DB_HOST port=$DB_PORT dbname=$DB_NAME user=$DB_USER password=$DB_PASS"

echo "=== FloodProofs Impact Data Loader ==="
echo "Data directory: $DATA_DIR"

# Find all impact shapefiles
if [ -n "$SPECIFIC_DATE" ]; then
    # Load specific date (format: YYYY-MM-DD or YYYYMMDD)
    DATE_CLEAN=$(echo "$SPECIFIC_DATE" | tr -d '-')
    YEAR=${DATE_CLEAN:0:4}
    MONTH=${DATE_CLEAN:4:2}
    DAY=${DATE_CLEAN:6:2}
    SEARCH_PATH="$DATA_DIR/$YEAR/$MONTH/$DAY"
    echo "Loading data for date: $YEAR-$MONTH-$DAY"
else
    SEARCH_PATH="$DATA_DIR"
    echo "Loading all available data"
fi

# Impact types to load
IMPACT_TYPES=("popafftot" "popaff25" "popaff100" "popage25" "popage100" "popmob25" "popmob100" "healthtot")

loaded_count=0
error_count=0

for impact_type in "${IMPACT_TYPES[@]}"; do
    echo ""
    echo "Processing impact type: $impact_type"

    # Find shapefiles for this impact type
    shapefiles=$(find "$SEARCH_PATH" -name "*FPimpacts-${impact_type}.shp" 2>/dev/null | sort)

    if [ -z "$shapefiles" ]; then
        echo "  No files found for $impact_type"
        continue
    fi

    for shp_file in $shapefiles; do
        # Extract date from filename (e.g., 202505190000_FPimpacts-popafftot.shp -> 2025-05-19)
        filename=$(basename "$shp_file")
        date_str="${filename:0:8}"
        year="${date_str:0:4}"
        month="${date_str:4:2}"
        day="${date_str:6:2}"
        forecast_date="$year-$month-$day"

        layer_name="${filename%.shp}"

        echo "  Loading: $filename -> $forecast_date"

        # Load to temp table
        ogr2ogr -f "PostgreSQL" "$PG_CONN" "$shp_file" \
            -nln "impact.temp_import" \
            -overwrite \
            -lco GEOMETRY_NAME=geom \
            -lco FID=ogc_fid \
            -t_srs EPSG:4326 \
            -nlt PROMOTE_TO_MULTI \
            --config PG_USE_COPY YES \
            -q 2>/dev/null

        if [ $? -ne 0 ]; then
            echo "    ERROR: Failed to load shapefile"
            ((error_count++))
            continue
        fi

        # Insert into main table
        psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -q <<EOF
INSERT INTO impact.floodproofs_impacts (
    forecast_date, impact_type, code_adm, gid_0, name_0, name_1, engtype_1, cod,
    pop_tot, flood_tot, tot_crop, tot_graze, tot_ind, tot_res, tot_serv,
    flood_perc, flood_clas, lack_cc, geom
)
SELECT
    '${forecast_date}'::date,
    '${impact_type}',
    code_adm, gid_0, name_0, name_1, engtype_1, cod,
    pop_tot, flood_tot, tot_crop, tot_graze, tot_ind, tot_res, tot_serv,
    flood_perc, flood_clas, lack_cc, geom
FROM impact.temp_import
ON CONFLICT (forecast_date, impact_type, code_adm) DO UPDATE SET
    pop_tot = EXCLUDED.pop_tot,
    flood_tot = EXCLUDED.flood_tot,
    tot_crop = EXCLUDED.tot_crop,
    tot_graze = EXCLUDED.tot_graze,
    flood_perc = EXCLUDED.flood_perc,
    flood_clas = EXCLUDED.flood_clas,
    geom = EXCLUDED.geom;

DROP TABLE IF EXISTS impact.temp_import;
EOF

        if [ $? -eq 0 ]; then
            ((loaded_count++))
            echo "    OK"
        else
            ((error_count++))
            echo "    ERROR: Failed to insert"
        fi
    done
done

echo ""
echo "=== Load Complete ==="
echo "Files loaded: $loaded_count"
echo "Errors: $error_count"

# Show summary
PGPASSWORD=$DB_PASS psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "
SELECT impact_type, COUNT(*) as records,
       MIN(forecast_date) as min_date, MAX(forecast_date) as max_date
FROM impact.floodproofs_impacts
GROUP BY impact_type
ORDER BY impact_type;
"
