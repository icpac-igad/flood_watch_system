-- Fishnet Grid Generator Function
-- Creates regular polygon grids for raster-to-vector conversion
-- Borrowed from mukau-mapserver methodology

CREATE OR REPLACE FUNCTION public.ST_CreateFishnet(
    nrow integer,
    ncol integer,
    xsize numeric(19,9),
    ysize numeric(19,9),
    x0 numeric(19,9) DEFAULT 0,
    y0 numeric(19,9) DEFAULT 0,
    OUT yrow integer,
    OUT xcol integer,
    OUT cell geometry
)
RETURNS SETOF record AS $$
SELECT i + 1 AS row, j + 1 AS col, ST_Translate(cell, j * $3 + $5, i * $4 + $6) AS geom
FROM generate_series(0, $1 - 1) AS i, generate_series(0, $2 - 1) AS j, (
    SELECT ST_PolygonFromText('POLYGON((0 0, 0 '||$4||', '||$3||' '||$4||', '||$3||' 0,0 0))', 4326) AS cell
) AS foo;
$$ LANGUAGE sql IMMUTABLE STRICT;
