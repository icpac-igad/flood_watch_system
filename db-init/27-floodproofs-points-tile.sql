-- FloodProofs "Deterministic Discharge" map layer tile function.
--
-- The SFTP job ingests one GeoJSON blob per day into
-- `gha.merged_deterministic_geojson.geojson_data` (a jsonb FeatureCollection).
-- The Wagtail layer is configured to pull tiles from
-- `floodproofs.discharge_points_clustered/{z}/{x}/{y}.pbf`, but that
-- function never existed — so the layer rendered empty.
--
-- What this function does on each tile request:
--   1. Pick the latest `merged_deterministic_geojson` row.
--   2. Expand its features to points.
--   3. Compute the peak forecast discharge (max across the next-48h
--      simulated series — GFS first, ICON as fallback).
--   4. Classify severity by comparing peak to Q_THR1/2/3 thresholds.
--   5. Emit MVT with severity + threshold properties so the styling
--      can colour each point and the popup can show numbers.

CREATE SCHEMA IF NOT EXISTS floodproofs;

CREATE OR REPLACE FUNCTION floodproofs.discharge_points_clustered(
    z integer,
    x integer,
    y integer,
    cluster_zoom integer DEFAULT 7
)
RETURNS bytea
LANGUAGE plpgsql
STABLE
AS $function$
DECLARE
    mvt bytea;
    tile_env geometry := ST_TileEnvelope(z, x, y);
    tile_bbox geometry := ST_Transform(tile_env, 4326);
BEGIN
    WITH latest AS (
        SELECT geojson_data, data_date
        FROM gha.merged_deterministic_geojson
        ORDER BY data_date DESC
        LIMIT 1
    ),
    features AS (
        SELECT jsonb_array_elements(l.geojson_data->'features') AS f,
               l.data_date
        FROM latest l
    ),
    points AS (
        SELECT
            ST_SetSRID(
                ST_MakePoint(
                    ((f->'geometry'->'coordinates'->>0))::float,
                    ((f->'geometry'->'coordinates'->>1))::float
                ), 4326
            ) AS geom,
            -- Emit both the new (station_name/river_name) and the legacy
            -- (section_name/basin) field names so popup_config and click
            -- detection keep working without a CMS edit.
            NULLIF(f->'properties'->>'SEC_NAME', '')       AS station_name,
            NULLIF(f->'properties'->>'SEC_NAME', '')       AS section_name,
            NULLIF(f->'properties'->>'SEC_CODE', '')       AS section_id,
            NULLIF(f->'properties'->>'BASIN', '')          AS river_name,
            NULLIF(f->'properties'->>'BASIN', '')          AS basin,
            NULLIF(f->'properties'->>'ADMIN_B_L1', '')     AS admin_l1,
            -- Carry the raw GFS / ICON time series strings so the popup
            -- (and future chart) can use them without a second query.
            NULLIF(f->'properties'->>'time_series_discharge_simulated-gfs', '')  AS time_series_discharge_simulated_gfs,
            NULLIF(f->'properties'->>'time_series_discharge_simulated-icon', '') AS time_series_discharge_simulated_icon,
            NULLIF(f->'properties'->>'time_period', '')     AS time_period,
            (f->'properties'->>'Q_THR1')::float            AS q_thr1,
            (f->'properties'->>'Q_THR2')::float            AS q_thr2,
            (f->'properties'->>'Q_THR3')::float            AS q_thr3,
            -- Peak forecast discharge: try GFS simulation first, fall back
            -- to ICON if GFS is all-zero / missing.
            GREATEST(
                COALESCE((
                    SELECT MAX(NULLIF(v, '')::float)
                    FROM unnest(string_to_array(
                        f->'properties'->>'time_series_discharge_simulated-gfs', ','
                    )) v
                    WHERE v ~ '^-?[0-9]+(\.[0-9]+)?$'
                ), 0),
                COALESCE((
                    SELECT MAX(NULLIF(v, '')::float)
                    FROM unnest(string_to_array(
                        f->'properties'->>'time_series_discharge_simulated-icon', ','
                    )) v
                    WHERE v ~ '^-?[0-9]+(\.[0-9]+)?$'
                ), 0)
            ) AS peak_discharge,
            data_date
        FROM features
    ),
    classified AS (
        SELECT
            geom,
            station_name, section_name, section_id,
            river_name, basin, admin_l1,
            time_series_discharge_simulated_gfs,
            time_series_discharge_simulated_icon,
            time_period,
            q_thr1, q_thr2, q_thr3, peak_discharge, data_date,
            CASE
                WHEN peak_discharge IS NULL OR peak_discharge <= 0 THEN 'normal'
                WHEN q_thr3 IS NOT NULL AND peak_discharge >= q_thr3 THEN 'extreme'
                WHEN q_thr2 IS NOT NULL AND peak_discharge >= q_thr2 THEN 'severe'
                WHEN q_thr1 IS NOT NULL AND peak_discharge >= q_thr1 THEN 'moderate'
                ELSE 'normal'
            END AS alert_level
        FROM points
        WHERE geom && tile_bbox
    )
    SELECT ST_AsMVT(t, 'floodproofs.discharge_points', 4096, 'mvt_geom') INTO mvt
    FROM (
        SELECT
            station_name, section_name, section_id,
            river_name, basin, admin_l1, alert_level,
            peak_discharge AS discharge_gfs,
            time_series_discharge_simulated_gfs,
            time_series_discharge_simulated_icon,
            time_period,
            q_thr1 AS threshold_alert,
            q_thr2 AS threshold_alarm,
            q_thr3 AS threshold_emergency,
            peak_discharge, data_date,
            ST_AsMVTGeom(ST_Transform(geom, 3857), tile_env, 4096, 256, true) AS mvt_geom
        FROM classified
    ) t
    WHERE t.mvt_geom IS NOT NULL;

    RETURN COALESCE(mvt, '');
END;
$function$;
