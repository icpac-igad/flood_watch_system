/**
 * TiTiler / pgSTAC helpers for raster tile rendering.
 *
 * Replaces the MapServer/MapCache WMS pipeline with TiTiler search-based
 * mosaic tiles served via /cog-tiles/.
 *
 * Usage:
 *   import { registerStacSearch, buildTitilerTileUrl, buildCollectionTileUrl } from '@/utils/stac-tiles';
 *
 *   // Search-based (temporal rasters like WRF extreme rainfall):
 *   const searchId = await registerStacSearch('wrf-daily-rainfall', [dateFilter]);
 *   const tileUrl  = buildTitilerTileUrl(searchId, { colormap: ... });
 *
 *   // Collection-based (static rasters like flood extent, population, cropland):
 *   const tileUrl  = buildCollectionTileUrl('flood-extent-return-periods', { colormap_name: 'viridis' });
 */

// ---------------------------------------------------------------------------
// TiTiler base path (proxied by nginx at /cog-tiles/)
// ---------------------------------------------------------------------------
const TITILER_BASE = '/cog-tiles';

// ---------------------------------------------------------------------------
// Extreme rainfall percentile colormaps
// Each entry is [value, R, G, B, A] — a single-interval colormap for the
// flat-color rendering expected by the TiTiler "interval" colormap type.
// ---------------------------------------------------------------------------
export const EXTREME_RAINFALL_TILE_COLORS = {
  f90: [[1, 175, 238, 238, 220]],   // pale cyan — 90th percentile (heavy)
  f95: [[1, 23, 116, 205, 220]],    // medium blue — 95th percentile (very heavy)
  f99: [[1, 6, 0, 139, 220]],       // dark navy — 99th percentile (extremely heavy)
};

// ---------------------------------------------------------------------------
// STAC search registration
// ---------------------------------------------------------------------------

/**
 * Register a pgSTAC search with TiTiler and return its hash ID.
 *
 * @param {string} collection - STAC collection ID (e.g. 'wrf-daily-rainfall')
 * @param {Array}  filters    - CQL2-JSON filter expressions (optional)
 * @returns {Promise<string>} The search hash ID for use in tile URLs
 */
export async function registerStacSearch(collection, filters = []) {
  const body = { collections: [collection] };

  if (filters.length > 0) {
    body['filter-lang'] = 'cql2-json';
    body.filter = filters.length === 1
      ? filters[0]
      : { op: 'and', args: filters };
  }

  const resp = await fetch(`${TITILER_BASE}/searches/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  if (!resp.ok) {
    const text = await resp.text().catch(() => '');
    throw new Error(`STAC search registration failed (${resp.status}): ${text}`);
  }

  const data = await resp.json();
  return data.id;   // hash string used in tile URL path
}

// ---------------------------------------------------------------------------
// Tile URL builders
// ---------------------------------------------------------------------------

/**
 * Build a TiTiler search-based mosaic tile URL template (with {z}/{x}/{y}).
 *
 * @param {string} searchId   - Hash from registerStacSearch()
 * @param {object} [params]   - Extra query params (colormap, assets, rescale, etc.)
 * @returns {string} URL template suitable for a MapLibre raster source
 */
export function buildTitilerTileUrl(searchId, params = {}) {
  const base = `${TITILER_BASE}/searches/${searchId}/tiles/WebMercatorQuad/{z}/{x}/{y}.png`;
  const merged = { assets: 'data', ...params };
  const qs = Object.entries(merged)
    .filter(([, v]) => v !== undefined && v !== null && v !== '')
    .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(typeof v === 'object' ? JSON.stringify(v) : String(v))}`)
    .join('&');
  return qs ? `${base}?${qs}` : base;
}

/**
 * Build a TiTiler collection-based tile URL template (static rasters).
 *
 * For datasets that don't change over time (flood extent, population, cropland,
 * rangeland), we can skip search registration and go straight to the collection
 * tile endpoint.
 *
 * @param {string} collectionId - STAC collection ID (e.g. 'flood-extent-return-periods')
 * @param {object} [params]     - Extra query params (colormap_name, assets, rescale, etc.)
 * @returns {string} URL template suitable for a MapLibre raster source
 */
export function buildCollectionTileUrl(collectionId, params = {}) {
  const base = `${TITILER_BASE}/collections/${collectionId}/tiles/WebMercatorQuad/{z}/{x}/{y}.png`;
  const merged = { assets: 'data', ...params };
  const qs = Object.entries(merged)
    .filter(([, v]) => v !== undefined && v !== null && v !== '')
    .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(typeof v === 'object' ? JSON.stringify(v) : String(v))}`)
    .join('&');
  return qs ? `${base}?${qs}` : base;
}

// ---------------------------------------------------------------------------
// URL detection helpers
// ---------------------------------------------------------------------------

/**
 * Check whether a tile URL points to TiTiler (cog-tiles).
 *
 * @param {string} url - Tile URL to test
 * @returns {boolean}
 */
export const isTitilerTileUrl = (url = '') =>
  url.includes('/cog-tiles/');

// ---------------------------------------------------------------------------
// CQL2 filter helpers (convenience for date filters)
// ---------------------------------------------------------------------------

/**
 * Build a CQL2-JSON datetime equality filter.
 *
 * @param {string} dateStr - ISO date string (YYYY-MM-DD or full ISO 8601)
 * @returns {object} CQL2-JSON filter expression
 */
export function cql2DateFilter(dateStr) {
  return {
    op: 'eq',
    args: [{ property: 'datetime' }, dateStr],
  };
}

/**
 * Build a CQL2-JSON datetime range filter (between two dates).
 *
 * @param {string} startDate - ISO date string
 * @param {string} endDate   - ISO date string
 * @returns {object} CQL2-JSON filter expression
 */
export function cql2DateRangeFilter(startDate, endDate) {
  return {
    op: 'and',
    args: [
      { op: 'gte', args: [{ property: 'datetime' }, startDate] },
      { op: 'lte', args: [{ property: 'datetime' }, endDate] },
    ],
  };
}

/**
 * Build a CQL2-JSON property equality filter.
 *
 * @param {string} property - Property name (e.g. 'percentile')
 * @param {*}      value    - Expected value
 * @returns {object} CQL2-JSON filter expression
 */
export function cql2PropertyFilter(property, value) {
  return {
    op: 'eq',
    args: [{ property }, value],
  };
}
