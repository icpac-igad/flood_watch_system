-- ============================================================================
-- Drop-in replacement for gha.forecast_points_clustered that routes all
-- alert-level classification through the gha.classify_alert() helper
-- introduced in 12-percentile-alert-levels.sql.
--
-- What changes vs the 07-* definition:
--   * alert_level  uses gha.classify_alert(cp.point_id, <value>)
--   * alert_priority uses gha.alert_priority(<level>)
--   * cluster aggregates classify each point then MAX the priority
--   * filter predicate uses gha.alert_filter_matches() so legacy values
--     ('active','alarm','emergency') and new ones ('moderate','severe',
--     'extreme') both work.
--
-- Everything else (signature, tile layer name, scope handling, join
-- structure) is identical — tile URLs / frontend contract unchanged.
-- ============================================================================

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
        SELECT MAX(data_date) INTO query_date FROM gha.multimodal_forecasts;
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
        current_value_f  := 'f.daily_avg';
        current_value_fc := 'fc.daily_avg';
        current_max_f    := 'COALESCE(f.daily_max, f.daily_avg)';
        current_min_f    := 'COALESCE(f.daily_min, f.daily_avg)';
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
    ELSE -- mike-hydro: GREATEST across the three mike columns
        current_value_f := $sql$
            CASE
                WHEN f.mike_hydro_rfe IS NULL
                 AND f.mike_hydro_chirp IS NULL
                 AND f.mike_hydro_imerg IS NULL
                THEN NULL
                ELSE GREATEST(
                    COALESCE(f.mike_hydro_rfe,   -1e308),
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
                    COALESCE(fc.mike_hydro_rfe,   -1e308),
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
                    COALESCE(fc.mike_hydro_rfe,   -1e308),
                    COALESCE(fc.mike_hydro_chirp, -1e308),
                    COALESCE(fc.mike_hydro_imerg, -1e308)
                )
            END,
            'Mike_Hydro_RFE',   fc.mike_hydro_rfe,
            'Mike_Hydro_CHIRP', fc.mike_hydro_chirp,
            'Mike_Hydro_IMERG', fc.mike_hydro_imerg
        )$$;
    END IF;

    IF z >= cluster_zoom THEN
        -- Unclustered: per-point record
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
                    gha.classify_alert(cp.point_id, %1$s) AS alert_level,
                    gha.alert_priority(gha.classify_alert(cp.point_id, %1$s)) AS alert_priority,
                    1 AS point_count,
                    ST_AsMVTGeom(ST_Transform(cp.geom, 3857), $3, 4096, 64, true) AS mvt_geom
                FROM gha.multimodal_control_points cp
                LEFT JOIN LATERAL (
                    SELECT
                        COALESCE(
                            gha.normalize_country_name(cp.country_code),
                            (SELECT UPPER(TRIM(a0.country)) FROM gha.admin0 a0
                             WHERE a0.geom && cp.geom AND ST_Within(cp.geom, a0.geom) LIMIT 1)
                        ) AS country_name,
                        COALESCE(
                            gha.normalize_country_code(cp.country_code),
                            (SELECT gha.normalize_country_code(a0.gid_0) FROM gha.admin0 a0
                             WHERE a0.geom && cp.geom AND ST_Within(cp.geom, a0.geom) LIMIT 1),
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
                  AND (%7$L <> 'whca' OR COALESCE(cp.whca_selected, FALSE) IS TRUE OR cc.country_code IN ('SD','SS','UG','ET','RW'))
                  AND ($4 IS NULL OR cc.country_name = ANY($4) OR cc.country_code = ANY($4))
                  AND ($5 IS NULL OR ST_Within(cp.geom, $5))
                  AND f.point_id IS NOT NULL
            )
            SELECT ST_AsMVT(tile, 'gha.forecast_points_clustered', 4096, 'mvt_geom')
            FROM (
                SELECT *
                FROM point_data
                WHERE gha.alert_filter_matches(alert_level, %8$L)
            ) tile
            WHERE tile.mvt_geom IS NOT NULL
        $sql$, current_value_f, current_max_f, current_min_f, forecast_object_sql, current_value_fc, current_value_f, scope_key, filter_key);

        EXECUTE sql INTO mvt USING query_date, tile_bbox_4326, tile_bbox_3857, countries_arr, clip_geom;
    ELSE
        -- Clustered: classify each point first, then aggregate
        sql := format($sql$
            WITH point_rows AS (
                SELECT
                    cp.point_id,
                    cp.x AS px,
                    cp.y AS py,
                    cp.geom,
                    %1$s AS daily_avg,
                    %2$s AS daily_max,
                    gha.classify_alert(cp.point_id, %1$s) AS alert_level,
                    gha.alert_priority(gha.classify_alert(cp.point_id, %1$s)) AS alert_priority
                FROM gha.multimodal_control_points cp
                LEFT JOIN LATERAL (
                    SELECT
                        COALESCE(
                            gha.normalize_country_name(cp.country_code),
                            (SELECT UPPER(TRIM(a0.country)) FROM gha.admin0 a0
                             WHERE a0.geom && cp.geom AND ST_Within(cp.geom, a0.geom) LIMIT 1)
                        ) AS country_name,
                        COALESCE(
                            gha.normalize_country_code(cp.country_code),
                            (SELECT gha.normalize_country_code(a0.gid_0) FROM gha.admin0 a0
                             WHERE a0.geom && cp.geom AND ST_Within(cp.geom, a0.geom) LIMIT 1),
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
                  AND (%4$L <> 'whca' OR COALESCE(cp.whca_selected, FALSE) IS TRUE OR cc.country_code IN ('SD','SS','UG','ET','RW'))
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
                    -- Cluster alert = worst alert across member points
                    MAX(alert_priority) AS alert_priority,
                    CASE MAX(alert_priority)
                        WHEN 4 THEN 'extreme'
                        WHEN 3 THEN 'severe'
                        WHEN 2 THEN 'moderate'
                        ELSE        'normal'
                    END AS alert_level,
                    SUM(CASE WHEN alert_level = 'extreme'  THEN 1 ELSE 0 END)::integer AS extreme_count,
                    SUM(CASE WHEN alert_level = 'severe'   THEN 1 ELSE 0 END)::integer AS severe_count,
                    SUM(CASE WHEN alert_level = 'moderate' THEN 1 ELSE 0 END)::integer AS moderate_count,
                    SUM(CASE WHEN alert_level = 'normal'   THEN 1 ELSE 0 END)::integer AS normal_count,
                    -- Legacy aliases so existing frontend keeps working mid-migration
                    SUM(CASE WHEN alert_level = 'extreme'  THEN 1 ELSE 0 END)::integer AS emergency_count,
                    SUM(CASE WHEN alert_level = 'severe'   THEN 1 ELSE 0 END)::integer AS alarm_count,
                    SUM(CASE WHEN alert_level = 'moderate' THEN 1 ELSE 0 END)::integer AS warning_count,
                    ST_AsMVTGeom(
                        ST_Transform(ST_Centroid(ST_Collect(geom)), 3857),
                        $3, 4096, 64, true
                    ) AS mvt_geom
                FROM point_rows
                GROUP BY floor(px / $6), floor(py / $6)
            )
            SELECT ST_AsMVT(tile, 'gha.forecast_points_clustered', 4096, 'mvt_geom')
            FROM (
                SELECT *
                FROM clustered
                WHERE gha.alert_filter_matches(alert_level, %5$L)
            ) tile
            WHERE tile.mvt_geom IS NOT NULL
        $sql$, current_value_f, current_max_f, current_value_f, scope_key, filter_key);

        EXECUTE sql INTO mvt USING query_date, tile_bbox_4326, tile_bbox_3857, countries_arr, clip_geom, grid_size;
    END IF;

    RETURN COALESCE(mvt, ''::bytea);
END;
$function$;
