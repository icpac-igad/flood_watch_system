-- 0.1 Degree Grid Table for EAFW Region
-- Grid covering East Africa flood watch region

DROP TABLE IF EXISTS grids.grid_01dd CASCADE;
CREATE TABLE grids.grid_01dd (
    id SERIAL PRIMARY KEY,
    xcol INTEGER NOT NULL,
    yrow INTEGER NOT NULL,
    cell GEOMETRY(Polygon, 4326) NOT NULL
);

-- Create 0.1 degree grid covering EAFW region
-- Approximate bounds: lon 21-52, lat -12 to 23 (East Africa)
-- That's ~310 cols x 350 rows
INSERT INTO grids.grid_01dd (xcol, yrow, cell)
SELECT xcol, yrow, cell
FROM public.ST_CreateFishnet(
    350,      -- rows (latitude range)
    310,      -- cols (longitude range)
    0.1,      -- cell width (degrees)
    0.1,      -- cell height (degrees)
    21.0,     -- x origin (min longitude)
    -12.0     -- y origin (min latitude)
);

-- Create spatial index
CREATE INDEX idx_grid_01dd_cell ON grids.grid_01dd USING GIST(cell);
CREATE INDEX idx_grid_01dd_xcol_yrow ON grids.grid_01dd(xcol, yrow);

-- Grant permissions
GRANT SELECT ON grids.grid_01dd TO mapuser;
GRANT SELECT ON grids.grid_01dd TO reader;
