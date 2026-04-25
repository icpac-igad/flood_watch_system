-- Google Flood Forecast tile function.
-- Reads from `gha.google_flood_points_latest` (populated by google_flood_sync)
-- and maps Google's severity enum to the same lowercase vocabulary every
-- other EAFW layer uses, so the unified render style keeps working.

CREATE OR REPLACE FUNCTION gha.google_flood_points_alerts(
    z integer, x integer, y integer,
    scope text DEFAULT '',
    quality text DEFAULT 'verified',
    date text DEFAULT ''
)
RETURNS bytea
LANGUAGE plpgsql
STABLE PARALLEL SAFE
AS $function$
DECLARE
    tile_env  geometry := ST_TileEnvelope(z, x, y);
    tile_bbox geometry := ST_Transform(tile_env, 4326);
    mvt bytea;
    -- WHCA = Sudan, South Sudan, Uganda, Ethiopia, Rwanda.
    use_whca boolean := (scope IS NOT NULL AND lower(trim(scope)) = 'whca');
    -- Default to ALL gauges. Google only `quality_verified`-flags a tiny
    -- subset (~16 of 6100 for GHA), so gating on verified hides every
    -- warning-level point — Google Flood Hub shows all gauges coloured
    -- by severity. `quality=verified` kept for callers who explicitly
    -- want the trimmed subset.
    verified_only boolean := (lower(COALESCE(quality, 'all')) = 'verified');
    query_date date;
BEGIN
    -- Safe date parse: swallow garbage (e.g. literal '{{time}}' placeholder)
    -- and fall back to "latest".
    IF date IS NOT NULL AND date <> '' THEN
        BEGIN
            query_date := date::date;
        EXCEPTION WHEN OTHERS THEN
            query_date := NULL;
        END;
    END IF;
    SELECT ST_AsMVT(tile, 'gha.google_flood_points_alerts', 4096, 'mvt_geom')
    INTO mvt
    FROM (
        SELECT
            gauge_id, point_id, country_code, region_code,
            site_name, river, admin_name,
            daily_avg,
            -- Peak discharge expected over the 8-day forecast horizon.
            -- Google's ABOVE_NORMAL flag is driven by this, not today's
            -- value — a gauge at 13% of threshold today can still be
            -- yellow if the forecast says it will hit 120% in 3 days.
            (
                SELECT MAX(GREATEST(
                    COALESCE((v->>'daily_max')::float, 0),
                    COALESCE((v->>'daily_avg')::float, 0)
                ))
                FROM jsonb_array_elements(forecasts_json) v
            ) AS forecast_peak,
            threshold_alert, threshold_alarm, threshold_emergency,
            latest_severity AS raw_severity,
            latest_forecast_trend AS trend,
            confidence_level,
            confidence_score,
            quality_verified,
            gauge_value_unit,
            latest_issued_time,
            -- Classify off the MAX of (today, forecast peak) vs our
            -- per-gauge thresholds, so the map colour matches what the
            -- chart's forecast line will do when you click in. This
            -- resolves the "today is 13% but dot is yellow" confusion —
            -- yellow means "peak will cross the warning line within the
            -- next 8 days". Google's severity is used as a fallback for
            -- gauges where our thresholds are missing.
            CASE
                WHEN GREATEST(
                        COALESCE(daily_avg, 0),
                        COALESCE((SELECT MAX(GREATEST(
                                    COALESCE((v->>'daily_max')::float, 0),
                                    COALESCE((v->>'daily_avg')::float, 0)))
                                  FROM jsonb_array_elements(forecasts_json) v), 0)
                     ) >= COALESCE(threshold_emergency, 9e18) THEN 'extreme'
                WHEN GREATEST(
                        COALESCE(daily_avg, 0),
                        COALESCE((SELECT MAX(GREATEST(
                                    COALESCE((v->>'daily_max')::float, 0),
                                    COALESCE((v->>'daily_avg')::float, 0)))
                                  FROM jsonb_array_elements(forecasts_json) v), 0)
                     ) >= COALESCE(threshold_alarm, 9e18) THEN 'severe'
                WHEN GREATEST(
                        COALESCE(daily_avg, 0),
                        COALESCE((SELECT MAX(GREATEST(
                                    COALESCE((v->>'daily_max')::float, 0),
                                    COALESCE((v->>'daily_avg')::float, 0)))
                                  FROM jsonb_array_elements(forecasts_json) v), 0)
                     ) >= COALESCE(threshold_alert, 9e18) THEN 'moderate'
                -- Thresholds missing? Trust Google's severity.
                WHEN threshold_alert IS NULL AND latest_severity = 'EXTREME_DANGER' THEN 'extreme'
                WHEN threshold_alert IS NULL AND latest_severity = 'DANGER'         THEN 'severe'
                WHEN threshold_alert IS NULL AND latest_severity IN ('WARNING', 'ABOVE_NORMAL') THEN 'moderate'
                ELSE 'normal'
            END AS alert_level,
            ST_AsMVTGeom(ST_Transform(geom, 3857), tile_env, 4096, 256, false) AS mvt_geom
        FROM gha.google_flood_points_latest
        WHERE geom && tile_bbox
          AND (NOT use_whca OR country_code IN ('SD', 'SS', 'UG', 'ET', 'RW'))
          AND (NOT verified_only OR quality_verified IS TRUE)
          AND (query_date IS NULL OR data_date = query_date)
    ) AS tile
    WHERE tile.mvt_geom IS NOT NULL;

    RETURN COALESCE(mvt, ''::bytea);
END;
$function$;


-- Rewire the Wagtail layer row to use this tile function + the shared style.
UPDATE geomanager_vectortilelayer
SET base_url = 'http://127.0.0.1:9068/pg/tileserv/gha.google_flood_points_alerts/{z}/{x}/{y}.pbf',
    render_layers = '[{
        "type": "circle",
        "paint": {
            "circle-color": ["match", ["get", "alert_level"],
                "extreme",  "#d32f2f",
                "severe",   "#ff9800",
                "moderate", "#ffc107",
                "normal",   "#b0b0b0",
                "#b0b0b0"
            ],
            "circle-radius": 3,
            "circle-opacity": 0.9,
            "circle-stroke-color": "#ffffff",
            "circle-stroke-width": 0.8
        },
        "metadata": {"position": "top"},
        "source-layer": "gha.google_flood_points_alerts"
    }]'::jsonb
WHERE title = 'Google Flood Forecast';
