-- Shared vector-tile functions for forecast providers.
--
-- Multimodal, GeoSFM and Mike Hydro all read from the normalized
-- gha.multimodal_forecasts + gha.multimodal_control_points tables.
-- Google Flood reads from gha.google_flood_points_latest.

CREATE OR REPLACE FUNCTION gha.normalize_country_code(raw text)
RETURNS text
LANGUAGE sql
IMMUTABLE
AS $function$
    SELECT CASE UPPER(TRIM(COALESCE(raw, '')))
        WHEN 'BI' THEN 'BI'
        WHEN 'BDI' THEN 'BI'
        WHEN 'DJ' THEN 'DJ'
        WHEN 'DJI' THEN 'DJ'
        WHEN 'ER' THEN 'ER'
        WHEN 'ERI' THEN 'ER'
        WHEN 'ET' THEN 'ET'
        WHEN 'ETH' THEN 'ET'
        WHEN 'KE' THEN 'KE'
        WHEN 'KEN' THEN 'KE'
        WHEN 'RW' THEN 'RW'
        WHEN 'RWA' THEN 'RW'
        WHEN 'SD' THEN 'SD'
        WHEN 'SDN' THEN 'SD'
        WHEN 'SO' THEN 'SO'
        WHEN 'SOM' THEN 'SO'
        WHEN 'SS' THEN 'SS'
        WHEN 'SSD' THEN 'SS'
        WHEN 'TZ' THEN 'TZ'
        WHEN 'TZA' THEN 'TZ'
        WHEN 'UG' THEN 'UG'
        WHEN 'UGA' THEN 'UG'
        ELSE NULL
    END;
$function$;


CREATE OR REPLACE FUNCTION gha.normalize_country_name(raw text)
RETURNS text
LANGUAGE sql
IMMUTABLE
AS $function$
    SELECT CASE gha.normalize_country_code(raw)
        WHEN 'BI' THEN 'BURUNDI'
        WHEN 'DJ' THEN 'DJIBOUTI'
        WHEN 'ER' THEN 'ERITREA'
        WHEN 'ET' THEN 'ETHIOPIA'
        WHEN 'KE' THEN 'KENYA'
        WHEN 'RW' THEN 'RWANDA'
        WHEN 'SD' THEN 'SUDAN'
        WHEN 'SO' THEN 'SOMALIA'
        WHEN 'SS' THEN 'SOUTH SUDAN'
        WHEN 'TZ' THEN 'TANZANIA'
        WHEN 'UG' THEN 'UGANDA'
        ELSE NULL
    END;
$function$;


CREATE OR REPLACE FUNCTION gha.forecast_points_clustered(
    z integer,
    x integer,
    y integer,
    provider text DEFAULT 'multimodal',
    cluster_zoom integer DEFAULT 7,
    date text DEFAULT NULL::text,
    scope text DEFAULT 'all',
    project_countries text DEFAULT NULL::text,
    country_name text DEFAULT NULL::text,
    region_name text DEFAULT NULL::text,
    district_name text DEFAULT NULL::text,
    filter text DEFAULT 'all'
)
RETURNS bytea
LANGUAGE plpgsql
STABLE
PARALLEL SAFE
AS $function$
DECLARE
    tile_bbox_3857 geometry := ST_TileEnvelope(z, x, y);
    tile_bbox_4326 geometry := ST_Transform(tile_bbox_3857, 4326);
    clip_geom geometry := NULL;
    grid_size float := 40.0 / power(2, z);
    provider_key text := lower(trim(coalesce(provider, 'multimodal')));
    scope_key text := lower(trim(coalesce(scope, 'all')));
    filter_key text := lower(trim(coalesce(filter, 'all')));
    query_date date;
    countries_arr text[] := NULL;
    current_value_f text;
    current_value_fc text;
    current_max_f text;
    current_min_f text;
    forecast_object_sql text;
    sql text;
    mvt bytea;
BEGIN
    IF provider_key NOT IN ('multimodal', 'geosfm', 'mike-hydro', 'floodproof') THEN
        provider_key := 'multimodal';
    END IF;

    IF project_countries IS NOT NULL AND trim(project_countries) <> '' THEN
        countries_arr := regexp_split_to_array(upper(project_countries), '\s*,\s*');
    END IF;

    IF date IS NOT NULL AND trim(date) <> '' THEN
        BEGIN
            query_date := date::date;
        EXCEPTION WHEN OTHERS THEN
            query_date := NULL;
        END;
    END IF;

    IF query_date IS NULL THEN
        SELECT MAX(data_date) INTO query_date
        FROM gha.multimodal_forecasts;
    END IF;

    IF query_date IS NULL THEN
        RETURN ''::bytea;
    END IF;

    IF district_name IS NOT NULL AND trim(district_name) <> '' THEN
        SELECT geom INTO clip_geom
        FROM gha.admin2
        WHERE lower(name_2) = lower(trim(district_name))
          AND (region_name IS NULL OR trim(region_name) = '' OR lower(name_1) = lower(trim(region_name)))
          AND (country_name IS NULL OR trim(country_name) = '' OR lower(country) = lower(trim(country_name)))
        LIMIT 1;
    ELSIF region_name IS NOT NULL AND trim(region_name) <> '' THEN
        SELECT geom INTO clip_geom
        FROM gha.admin1
        WHERE lower(name_1) = lower(trim(region_name))
          AND (country_name IS NULL OR trim(country_name) = '' OR lower(country) = lower(trim(country_name)))
        LIMIT 1;
    ELSIF country_name IS NOT NULL AND trim(country_name) <> '' THEN
        SELECT geom INTO clip_geom
        FROM gha.admin0
        WHERE lower(country) = lower(trim(country_name))
        LIMIT 1;
    END IF;

    IF provider_key = 'multimodal' THEN
        current_value_f := 'f.daily_avg';
        current_value_fc := 'fc.daily_avg';
        current_max_f := 'COALESCE(f.daily_max, f.daily_avg)';
        current_min_f := 'COALESCE(f.daily_min, f.daily_avg)';
        forecast_object_sql := $$json_build_object(
            'date', fc.forecast_date,
            'daily_avg', fc.daily_avg,
            'daily_max', fc.daily_max,
            'daily_min', fc.daily_min,
            'GeoSFM', fc.geosfm,
            'Floodproof', fc.floodproof,
            'Mike_Hydro_RFE', fc.mike_hydro_rfe,
            'Mike_Hydro_CHIRP', fc.mike_hydro_chirp,
            'Mike_Hydro_IMERG', fc.mike_hydro_imerg
        )$$;
    ELSIF provider_key = 'geosfm' THEN
        current_value_f := 'f.geosfm';
        current_value_fc := 'fc.geosfm';
        current_max_f := current_value_f;
        current_min_f := current_value_f;
        forecast_object_sql := $$json_build_object(
            'date', fc.forecast_date,
            'daily_avg', fc.geosfm,
            'GeoSFM', fc.geosfm
        )$$;
    ELSIF provider_key = 'floodproof' THEN
        current_value_f := 'f.floodproof';
        current_value_fc := 'fc.floodproof';
        current_max_f := current_value_f;
        current_min_f := current_value_f;
        forecast_object_sql := $$json_build_object(
            'date', fc.forecast_date,
            'daily_avg', fc.floodproof,
            'Floodproof', fc.floodproof
        )$$;
    ELSE
        current_value_f := $sql$
            CASE
                WHEN f.mike_hydro_rfe IS NULL
                 AND f.mike_hydro_chirp IS NULL
                 AND f.mike_hydro_imerg IS NULL
                THEN NULL
                ELSE GREATEST(
                    COALESCE(f.mike_hydro_rfe, -1e308),
                    COALESCE(f.mike_hydro_chirp, -1e308),
                    COALESCE(f.mike_hydro_imerg, -1e308)
                )
            END
        $sql$;
        current_value_fc := $sql$
            CASE
                WHEN fc.mike_hydro_rfe IS NULL
                 AND fc.mike_hydro_chirp IS NULL
                 AND fc.mike_hydro_imerg IS NULL
                THEN NULL
                ELSE GREATEST(
                    COALESCE(fc.mike_hydro_rfe, -1e308),
                    COALESCE(fc.mike_hydro_chirp, -1e308),
                    COALESCE(fc.mike_hydro_imerg, -1e308)
                )
            END
        $sql$;
        current_max_f := current_value_f;
        current_min_f := current_value_f;
        forecast_object_sql := $$json_build_object(
            'date', fc.forecast_date,
            'daily_avg', CASE
                WHEN fc.mike_hydro_rfe IS NULL
                 AND fc.mike_hydro_chirp IS NULL
                 AND fc.mike_hydro_imerg IS NULL
                THEN NULL
                ELSE GREATEST(
                    COALESCE(fc.mike_hydro_rfe, -1e308),
                    COALESCE(fc.mike_hydro_chirp, -1e308),
                    COALESCE(fc.mike_hydro_imerg, -1e308)
                )
            END,
            'Mike_Hydro_RFE', fc.mike_hydro_rfe,
            'Mike_Hydro_CHIRP', fc.mike_hydro_chirp,
            'Mike_Hydro_IMERG', fc.mike_hydro_imerg
        )$$;
    END IF;

    IF z >= cluster_zoom THEN
        sql := format($sql$
            WITH point_data AS (
                SELECT
                    cp.point_id AS id,
                    cp.point_id,
                    cp.zone,
                    cp.gridcode,
                    cp.admin_name,
                    cp.hybas_id,
                    $1::text AS data_date,
                    f.forecast_date::text AS forecast_date,
                    %1$s AS daily_avg,
                    %2$s AS daily_max,
                    %3$s AS daily_min,
                    f.geosfm,
                    f.floodproof,
                    f.mike_hydro_rfe,
                    f.mike_hydro_chirp,
                    f.mike_hydro_imerg,
                    COALESCE((
                        SELECT json_agg(%4$s ORDER BY fc.forecast_date)
                        FROM gha.multimodal_forecasts fc
                        WHERE fc.point_id = cp.point_id
                          AND fc.data_date = $1
                          AND %5$s IS NOT NULL
                    ), '[]'::json)::text AS forecasts_json,
                    CASE
                        WHEN %1$s >= 750 THEN 'emergency'
                        WHEN %1$s >= 500 THEN 'alarm'
                        WHEN %1$s >= 300 THEN 'warning'
                        ELSE 'normal'
                    END AS alert_level,
                    CASE
                        WHEN %1$s >= 750 THEN 4
                        WHEN %1$s >= 500 THEN 3
                        WHEN %1$s >= 300 THEN 2
                        ELSE 1
                    END AS alert_priority,
                    1 AS point_count,
                    ST_AsMVTGeom(ST_Transform(cp.geom, 3857), $3, 4096, 64, true) AS mvt_geom
                FROM gha.multimodal_control_points cp
                LEFT JOIN LATERAL (
                    SELECT
                        COALESCE(
                            gha.normalize_country_name(cp.country_code),
                            (
                                SELECT UPPER(TRIM(a0.country))
                                FROM gha.admin0 a0
                                WHERE a0.geom && cp.geom
                                  AND ST_Within(cp.geom, a0.geom)
                                LIMIT 1
                            )
                        ) AS country_name,
                        COALESCE(
                            gha.normalize_country_code(cp.country_code),
                            (
                                SELECT gha.normalize_country_code(a0.gid_0)
                                FROM gha.admin0 a0
                                WHERE a0.geom && cp.geom
                                  AND ST_Within(cp.geom, a0.geom)
                                LIMIT 1
                            ),
                            'UN'
                        ) AS country_code
                ) cc ON TRUE
                LEFT JOIN LATERAL (
                    SELECT f.*
                    FROM gha.multimodal_forecasts f
                    WHERE f.point_id = cp.point_id
                      AND f.data_date = $1
                      AND f.forecast_date >= $1
                      AND %6$s IS NOT NULL
                    ORDER BY f.forecast_date ASC
                    LIMIT 1
                ) f ON TRUE
                WHERE cp.geom && $2
                  AND (%7$L <> 'whca' OR COALESCE(cp.whca_selected, FALSE) IS TRUE OR cc.country_code IN ('SD', 'SS', 'UG', 'ET', 'RW'))
                  AND ($4 IS NULL OR cc.country_name = ANY($4) OR cc.country_code = ANY($4))
                  AND ($5 IS NULL OR ST_Within(cp.geom, $5))
                  AND f.point_id IS NOT NULL
            )
            SELECT ST_AsMVT(tile, 'gha.forecast_points_clustered', 4096, 'mvt_geom')
            FROM (
                SELECT *
                FROM point_data
                WHERE (%8$L = 'all'
                    OR (%8$L = 'active' AND daily_avg >= 300)
                    OR (%8$L = 'alarm' AND daily_avg >= 500)
                    OR (%8$L = 'emergency' AND daily_avg >= 750))
            ) tile
            WHERE tile.mvt_geom IS NOT NULL
        $sql$, current_value_f, current_max_f, current_min_f, forecast_object_sql, current_value_fc, current_value_f, scope_key, filter_key);

        EXECUTE sql INTO mvt USING query_date, tile_bbox_4326, tile_bbox_3857, countries_arr, clip_geom;
    ELSE
        sql := format($sql$
            WITH point_rows AS (
                SELECT
                    cp.point_id,
                    cp.x AS px,
                    cp.y AS py,
                    cp.geom,
                    %1$s AS daily_avg,
                    %2$s AS daily_max
                FROM gha.multimodal_control_points cp
                LEFT JOIN LATERAL (
                    SELECT
                        COALESCE(
                            gha.normalize_country_name(cp.country_code),
                            (
                                SELECT UPPER(TRIM(a0.country))
                                FROM gha.admin0 a0
                                WHERE a0.geom && cp.geom
                                  AND ST_Within(cp.geom, a0.geom)
                                LIMIT 1
                            )
                        ) AS country_name,
                        COALESCE(
                            gha.normalize_country_code(cp.country_code),
                            (
                                SELECT gha.normalize_country_code(a0.gid_0)
                                FROM gha.admin0 a0
                                WHERE a0.geom && cp.geom
                                  AND ST_Within(cp.geom, a0.geom)
                                LIMIT 1
                            ),
                            'UN'
                        ) AS country_code
                ) cc ON TRUE
                LEFT JOIN LATERAL (
                    SELECT f.*
                    FROM gha.multimodal_forecasts f
                    WHERE f.point_id = cp.point_id
                      AND f.data_date = $1
                      AND f.forecast_date >= $1
                      AND %3$s IS NOT NULL
                    ORDER BY f.forecast_date ASC
                    LIMIT 1
                ) f ON TRUE
                WHERE cp.geom && $2
                  AND (%4$L <> 'whca' OR COALESCE(cp.whca_selected, FALSE) IS TRUE OR cc.country_code IN ('SD', 'SS', 'UG', 'ET', 'RW'))
                  AND ($4 IS NULL OR cc.country_name = ANY($4) OR cc.country_code = ANY($4))
                  AND ($5 IS NULL OR ST_Within(cp.geom, $5))
                  AND f.point_id IS NOT NULL
            ),
            clustered AS (
                SELECT
                    MIN(point_id) AS id,
                    COUNT(*)::integer AS point_count,
                    MAX(daily_max) AS daily_max,
                    AVG(daily_avg)::numeric(10, 2) AS daily_avg,
                    $1::text AS data_date,
                    CASE
                        WHEN MAX(daily_avg) >= 750 THEN 'emergency'
                        WHEN MAX(daily_avg) >= 500 THEN 'alarm'
                        WHEN MAX(daily_avg) >= 300 THEN 'warning'
                        ELSE 'normal'
                    END AS alert_level,
                    CASE
                        WHEN MAX(daily_avg) >= 750 THEN 4
                        WHEN MAX(daily_avg) >= 500 THEN 3
                        WHEN MAX(daily_avg) >= 300 THEN 2
                        ELSE 1
                    END AS alert_priority,
                    SUM(CASE WHEN daily_avg >= 750 THEN 1 ELSE 0 END)::integer AS emergency_count,
                    SUM(CASE WHEN daily_avg >= 500 AND daily_avg < 750 THEN 1 ELSE 0 END)::integer AS alarm_count,
                    SUM(CASE WHEN daily_avg >= 300 AND daily_avg < 500 THEN 1 ELSE 0 END)::integer AS warning_count,
                    SUM(CASE WHEN daily_avg < 300 OR daily_avg IS NULL THEN 1 ELSE 0 END)::integer AS normal_count,
                    ST_AsMVTGeom(
                        ST_Transform(ST_Centroid(ST_Collect(geom)), 3857),
                        $3,
                        4096,
                        64,
                        true
                    ) AS mvt_geom
                FROM point_rows
                GROUP BY floor(px / $6), floor(py / $6)
            )
            SELECT ST_AsMVT(tile, 'gha.forecast_points_clustered', 4096, 'mvt_geom')
            FROM (
                SELECT *
                FROM clustered
                WHERE (%5$L = 'all'
                    OR (%5$L = 'active' AND daily_avg >= 300)
                    OR (%5$L = 'alarm' AND daily_avg >= 500)
                    OR (%5$L = 'emergency' AND daily_avg >= 750))
            ) tile
            WHERE tile.mvt_geom IS NOT NULL
        $sql$, current_value_f, current_max_f, current_value_f, scope_key, filter_key);

        EXECUTE sql INTO mvt USING query_date, tile_bbox_4326, tile_bbox_3857, countries_arr, clip_geom, grid_size;
    END IF;

    RETURN COALESCE(mvt, ''::bytea);
END;
$function$;


CREATE OR REPLACE FUNCTION gha.google_flood_points_clustered(
    z integer,
    x integer,
    y integer,
    cluster_zoom integer DEFAULT 7,
    date text DEFAULT NULL::text,
    scope text DEFAULT 'all',
    project_countries text DEFAULT NULL::text,
    country_name text DEFAULT NULL::text,
    region_name text DEFAULT NULL::text,
    district_name text DEFAULT NULL::text,
    filter text DEFAULT 'all',
    confidence text DEFAULT 'high',
    extended_coverage text DEFAULT 'false'
)
RETURNS bytea
LANGUAGE plpgsql
STABLE
PARALLEL SAFE
AS $function$
DECLARE
    tile_bbox_3857 geometry := ST_TileEnvelope(z, x, y);
    tile_bbox_4326 geometry := ST_Transform(tile_bbox_3857, 4326);
    clip_geom geometry := NULL;
    grid_size float := 40.0 / power(2, z);
    scope_key text := lower(trim(coalesce(scope, 'all')));
    filter_key text := lower(trim(coalesce(filter, 'all')));
    confidence_key text := lower(trim(coalesce(confidence, 'high')));
    query_date date := NULL;
    countries_arr text[] := NULL;
    sql text;
    mvt bytea;
BEGIN
    IF project_countries IS NOT NULL AND trim(project_countries) <> '' THEN
        countries_arr := regexp_split_to_array(upper(project_countries), '\s*,\s*');
    END IF;

    IF date IS NOT NULL AND trim(date) <> '' THEN
        BEGIN
            query_date := date::date;
        EXCEPTION WHEN OTHERS THEN
            query_date := NULL;
        END;
    END IF;

    IF lower(trim(coalesce(extended_coverage, 'false'))) IN ('1', 'true', 'yes', 'on') THEN
        confidence_key := 'all';
    ELSIF confidence_key NOT IN ('all', 'high', 'low') THEN
        confidence_key := 'high';
    END IF;

    IF district_name IS NOT NULL AND trim(district_name) <> '' THEN
        SELECT geom INTO clip_geom
        FROM gha.admin2
        WHERE lower(name_2) = lower(trim(district_name))
          AND (region_name IS NULL OR trim(region_name) = '' OR lower(name_1) = lower(trim(region_name)))
          AND (country_name IS NULL OR trim(country_name) = '' OR lower(country) = lower(trim(country_name)))
        LIMIT 1;
    ELSIF region_name IS NOT NULL AND trim(region_name) <> '' THEN
        SELECT geom INTO clip_geom
        FROM gha.admin1
        WHERE lower(name_1) = lower(trim(region_name))
          AND (country_name IS NULL OR trim(country_name) = '' OR lower(country) = lower(trim(country_name)))
        LIMIT 1;
    ELSIF country_name IS NOT NULL AND trim(country_name) <> '' THEN
        SELECT geom INTO clip_geom
        FROM gha.admin0
        WHERE lower(country) = lower(trim(country_name))
        LIMIT 1;
    END IF;

    IF z >= cluster_zoom THEN
        sql := format($sql$
            WITH point_data AS (
                SELECT
                    COALESCE(NULLIF(g.point_id, ''), g.gauge_id) AS id,
                    g.gauge_id,
                    COALESCE(NULLIF(g.point_id, ''), g.gauge_id) AS point_id,
                    COALESCE(NULLIF(g.admin_name, ''), NULLIF(g.site_name, ''), g.gauge_id) AS admin_name,
                    g.hybas_id,
                    COALESCE(NULLIF(g.country_code, ''), NULLIF(g.region_code, ''), cc.country_code) AS country_code,
                    COALESCE(NULLIF(g.region_code, ''), cc.country_code) AS region_code,
                    g.data_date::text AS data_date,
                    COALESCE(g.latest_issued_time::text, g.data_date::text) AS forecast_date,
                    COALESCE(g.daily_avg, g.daily_max) AS daily_avg,
                    g.daily_max,
                    g.daily_min,
                    g.threshold_alert,
                    g.threshold_alarm,
                    g.threshold_emergency,
                    g.latest_severity AS google_flood_severity,
                    g.latest_forecast_trend AS forecast_trend,
                    g.confidence_level,
                    g.confidence_score,
                    g.quality_verified,
                    g.model_quality_verified,
                    g.status_quality_verified,
                    COALESCE(g.forecasts_json, '[]'::jsonb)::text AS forecasts_json,
                    CASE
                        WHEN UPPER(COALESCE(g.latest_severity, '')) IN ('EXTREME', 'EXTREME_FLOODING', 'MAJOR_FLOODING') THEN 'emergency'
                        WHEN UPPER(COALESCE(g.latest_severity, '')) IN ('SEVERE', 'DANGER', 'MODERATE_FLOODING') THEN 'alarm'
                        WHEN UPPER(COALESCE(g.latest_severity, '')) IN ('WARNING', 'WATCH', 'MINOR_FLOODING', 'ALERT') THEN 'warning'
                        WHEN g.daily_max IS NOT NULL AND g.threshold_emergency IS NOT NULL AND g.daily_max >= g.threshold_emergency THEN 'emergency'
                        WHEN g.daily_max IS NOT NULL AND g.threshold_alarm IS NOT NULL AND g.daily_max >= g.threshold_alarm THEN 'alarm'
                        WHEN g.daily_max IS NOT NULL AND g.threshold_alert IS NOT NULL AND g.daily_max >= g.threshold_alert THEN 'warning'
                        WHEN COALESCE(g.daily_avg, g.daily_max) IS NOT NULL
                             AND g.threshold_emergency IS NOT NULL
                             AND COALESCE(g.daily_avg, g.daily_max) >= g.threshold_emergency THEN 'emergency'
                        WHEN COALESCE(g.daily_avg, g.daily_max) IS NOT NULL
                             AND g.threshold_alarm IS NOT NULL
                             AND COALESCE(g.daily_avg, g.daily_max) >= g.threshold_alarm THEN 'alarm'
                        WHEN COALESCE(g.daily_avg, g.daily_max) IS NOT NULL
                             AND g.threshold_alert IS NOT NULL
                             AND COALESCE(g.daily_avg, g.daily_max) >= g.threshold_alert THEN 'warning'
                        ELSE 'normal'
                    END AS alert_level,
                    CASE
                        WHEN UPPER(COALESCE(g.latest_severity, '')) IN ('EXTREME', 'EXTREME_FLOODING', 'MAJOR_FLOODING') THEN 4
                        WHEN UPPER(COALESCE(g.latest_severity, '')) IN ('SEVERE', 'DANGER', 'MODERATE_FLOODING') THEN 3
                        WHEN UPPER(COALESCE(g.latest_severity, '')) IN ('WARNING', 'WATCH', 'MINOR_FLOODING', 'ALERT') THEN 2
                        WHEN g.daily_max IS NOT NULL AND g.threshold_emergency IS NOT NULL AND g.daily_max >= g.threshold_emergency THEN 4
                        WHEN g.daily_max IS NOT NULL AND g.threshold_alarm IS NOT NULL AND g.daily_max >= g.threshold_alarm THEN 3
                        WHEN g.daily_max IS NOT NULL AND g.threshold_alert IS NOT NULL AND g.daily_max >= g.threshold_alert THEN 2
                        WHEN COALESCE(g.daily_avg, g.daily_max) IS NOT NULL
                             AND g.threshold_emergency IS NOT NULL
                             AND COALESCE(g.daily_avg, g.daily_max) >= g.threshold_emergency THEN 4
                        WHEN COALESCE(g.daily_avg, g.daily_max) IS NOT NULL
                             AND g.threshold_alarm IS NOT NULL
                             AND COALESCE(g.daily_avg, g.daily_max) >= g.threshold_alarm THEN 3
                        WHEN COALESCE(g.daily_avg, g.daily_max) IS NOT NULL
                             AND g.threshold_alert IS NOT NULL
                             AND COALESCE(g.daily_avg, g.daily_max) >= g.threshold_alert THEN 2
                        ELSE 1
                    END AS alert_priority,
                    CASE
                        WHEN UPPER(COALESCE(g.confidence_level, '')) = 'LOW' THEN TRUE
                        ELSE FALSE
                    END AS extended_coverage,
                    1 AS point_count,
                    ST_AsMVTGeom(ST_Transform(g.geom, 3857), $2, 4096, 64, true) AS mvt_geom
                FROM gha.google_flood_points_latest g
                LEFT JOIN LATERAL (
                    SELECT
                        COALESCE(
                            gha.normalize_country_name(g.country_code),
                            gha.normalize_country_name(g.region_code),
                            (
                                SELECT UPPER(TRIM(a0.country))
                                FROM gha.admin0 a0
                                WHERE a0.geom && g.geom
                                  AND ST_Within(g.geom, a0.geom)
                                LIMIT 1
                            )
                        ) AS country_name,
                        COALESCE(
                            gha.normalize_country_code(g.country_code),
                            gha.normalize_country_code(g.region_code),
                            (
                                SELECT gha.normalize_country_code(a0.gid_0)
                                FROM gha.admin0 a0
                                WHERE a0.geom && g.geom
                                  AND ST_Within(g.geom, a0.geom)
                                LIMIT 1
                            ),
                            'UN'
                        ) AS country_code
                ) cc ON TRUE
                WHERE g.geom && $1
                  AND g.geom IS NOT NULL
                  AND ($3 IS NULL OR g.data_date = $3)
                  AND (%1$L <> 'whca' OR cc.country_code IN ('SD', 'SS', 'UG', 'ET', 'RW'))
                  AND ($4 IS NULL OR cc.country_name = ANY($4) OR cc.country_code = ANY($4))
                  AND ($5 IS NULL OR ST_Within(g.geom, $5))
                  AND (%2$L = 'all'
                    OR (%2$L = 'high' AND UPPER(COALESCE(g.confidence_level, '')) = 'HIGH')
                    OR (%2$L = 'low' AND UPPER(COALESCE(g.confidence_level, '')) = 'LOW'))
            )
            SELECT ST_AsMVT(tile, 'gha.google_flood_points_clustered', 4096, 'mvt_geom')
            FROM (
                SELECT *
                FROM point_data
                WHERE (%3$L = 'all'
                    OR (%3$L = 'active' AND alert_level <> 'normal')
                    OR (%3$L = 'alarm' AND alert_level IN ('alarm', 'emergency'))
                    OR (%3$L = 'emergency' AND alert_level = 'emergency'))
            ) tile
            WHERE tile.mvt_geom IS NOT NULL
        $sql$, scope_key, confidence_key, filter_key);

        EXECUTE sql INTO mvt USING tile_bbox_4326, tile_bbox_3857, query_date, countries_arr, clip_geom;
    ELSE
        sql := format($sql$
            WITH point_rows AS (
                SELECT
                    COALESCE(NULLIF(g.point_id, ''), g.gauge_id) AS id,
                    g.geom,
                    ST_X(g.geom) AS px,
                    ST_Y(g.geom) AS py,
                    COALESCE(g.daily_avg, g.daily_max) AS daily_avg,
                    g.daily_max,
                    CASE
                        WHEN UPPER(COALESCE(g.latest_severity, '')) IN ('EXTREME', 'EXTREME_FLOODING', 'MAJOR_FLOODING') THEN 'emergency'
                        WHEN UPPER(COALESCE(g.latest_severity, '')) IN ('SEVERE', 'DANGER', 'MODERATE_FLOODING') THEN 'alarm'
                        WHEN UPPER(COALESCE(g.latest_severity, '')) IN ('WARNING', 'WATCH', 'MINOR_FLOODING', 'ALERT') THEN 'warning'
                        WHEN g.daily_max IS NOT NULL AND g.threshold_emergency IS NOT NULL AND g.daily_max >= g.threshold_emergency THEN 'emergency'
                        WHEN g.daily_max IS NOT NULL AND g.threshold_alarm IS NOT NULL AND g.daily_max >= g.threshold_alarm THEN 'alarm'
                        WHEN g.daily_max IS NOT NULL AND g.threshold_alert IS NOT NULL AND g.daily_max >= g.threshold_alert THEN 'warning'
                        WHEN COALESCE(g.daily_avg, g.daily_max) IS NOT NULL
                             AND g.threshold_emergency IS NOT NULL
                             AND COALESCE(g.daily_avg, g.daily_max) >= g.threshold_emergency THEN 'emergency'
                        WHEN COALESCE(g.daily_avg, g.daily_max) IS NOT NULL
                             AND g.threshold_alarm IS NOT NULL
                             AND COALESCE(g.daily_avg, g.daily_max) >= g.threshold_alarm THEN 'alarm'
                        WHEN COALESCE(g.daily_avg, g.daily_max) IS NOT NULL
                             AND g.threshold_alert IS NOT NULL
                             AND COALESCE(g.daily_avg, g.daily_max) >= g.threshold_alert THEN 'warning'
                        ELSE 'normal'
                    END AS alert_level
                FROM gha.google_flood_points_latest g
                LEFT JOIN LATERAL (
                    SELECT
                        COALESCE(
                            gha.normalize_country_name(g.country_code),
                            gha.normalize_country_name(g.region_code),
                            (
                                SELECT UPPER(TRIM(a0.country))
                                FROM gha.admin0 a0
                                WHERE a0.geom && g.geom
                                  AND ST_Within(g.geom, a0.geom)
                                LIMIT 1
                            )
                        ) AS country_name,
                        COALESCE(
                            gha.normalize_country_code(g.country_code),
                            gha.normalize_country_code(g.region_code),
                            (
                                SELECT gha.normalize_country_code(a0.gid_0)
                                FROM gha.admin0 a0
                                WHERE a0.geom && g.geom
                                  AND ST_Within(g.geom, a0.geom)
                                LIMIT 1
                            ),
                            'UN'
                        ) AS country_code
                ) cc ON TRUE
                WHERE g.geom && $1
                  AND g.geom IS NOT NULL
                  AND ($2 IS NULL OR g.data_date = $2)
                  AND (%1$L <> 'whca' OR cc.country_code IN ('SD', 'SS', 'UG', 'ET', 'RW'))
                  AND ($3 IS NULL OR cc.country_name = ANY($3) OR cc.country_code = ANY($3))
                  AND ($4 IS NULL OR ST_Within(g.geom, $4))
                  AND (%2$L = 'all'
                    OR (%2$L = 'high' AND UPPER(COALESCE(g.confidence_level, '')) = 'HIGH')
                    OR (%2$L = 'low' AND UPPER(COALESCE(g.confidence_level, '')) = 'LOW'))
            ),
            clustered AS (
                SELECT
                    MIN(id) AS id,
                    COUNT(*)::integer AS point_count,
                    MAX(daily_max) AS daily_max,
                    AVG(daily_avg)::numeric(10, 2) AS daily_avg,
                    CASE
                        WHEN SUM(CASE WHEN alert_level = 'emergency' THEN 1 ELSE 0 END) > 0 THEN 'emergency'
                        WHEN SUM(CASE WHEN alert_level = 'alarm' THEN 1 ELSE 0 END) > 0 THEN 'alarm'
                        WHEN SUM(CASE WHEN alert_level = 'warning' THEN 1 ELSE 0 END) > 0 THEN 'warning'
                        ELSE 'normal'
                    END AS alert_level,
                    SUM(CASE WHEN alert_level = 'emergency' THEN 1 ELSE 0 END)::integer AS emergency_count,
                    SUM(CASE WHEN alert_level = 'alarm' THEN 1 ELSE 0 END)::integer AS alarm_count,
                    SUM(CASE WHEN alert_level = 'warning' THEN 1 ELSE 0 END)::integer AS warning_count,
                    SUM(CASE WHEN alert_level = 'normal' THEN 1 ELSE 0 END)::integer AS normal_count,
                    ST_AsMVTGeom(
                        ST_Transform(ST_Centroid(ST_Collect(geom)), 3857),
                        $5,
                        4096,
                        64,
                        true
                    ) AS mvt_geom
                FROM point_rows
                GROUP BY floor(px / $6), floor(py / $6)
            )
            SELECT ST_AsMVT(tile, 'gha.google_flood_points_clustered', 4096, 'mvt_geom')
            FROM (
                SELECT *
                FROM clustered
                WHERE (%3$L = 'all'
                    OR (%3$L = 'active' AND alert_level <> 'normal')
                    OR (%3$L = 'alarm' AND alert_level IN ('alarm', 'emergency'))
                    OR (%3$L = 'emergency' AND alert_level = 'emergency'))
            ) tile
            WHERE tile.mvt_geom IS NOT NULL
        $sql$, scope_key, confidence_key, filter_key);

        EXECUTE sql INTO mvt USING tile_bbox_4326, query_date, countries_arr, clip_geom, tile_bbox_3857, grid_size;
    END IF;

    RETURN COALESCE(mvt, ''::bytea);
END;
$function$;


GRANT EXECUTE ON FUNCTION gha.normalize_country_code(text) TO PUBLIC;
GRANT EXECUTE ON FUNCTION gha.normalize_country_name(text) TO PUBLIC;
GRANT EXECUTE ON FUNCTION gha.forecast_points_clustered(integer, integer, integer, text, integer, text, text, text, text, text, text, text) TO PUBLIC;
GRANT EXECUTE ON FUNCTION gha.google_flood_points_clustered(integer, integer, integer, integer, text, text, text, text, text, text, text, text, text) TO PUBLIC;
