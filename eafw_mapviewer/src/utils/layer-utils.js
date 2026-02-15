import { ALERT_COLORS, DEFAULT_THRESHOLDS } from './multimodal-config';

// FloodWatch Custom: Params that should be passed to backend for filtering
// These are the ONLY params we want to add to pg_tileserv URLs
const BACKEND_FILTER_PARAMS = ['country_name', 'region_name', 'district_name', 'project_countries', 'scope', 'admin_level', 'risk_level', 'basin_id'];

// Params that control frontend behavior but shouldn't be in URLs
const FRONTEND_ONLY_PARAMS = ['admin_filter', 'whca_filter', 'project_filter', 'basin_filter'];

// Params that are legacy GFW-style and should be ignored
const LEGACY_PARAMS_TO_IGNORE = ['unit_id', 'MASK_UNIT_ID', 'MASK_ADMIN_LEVEL', 'MASK_AREA', 'border_level', 'project_name'];

const isTruthyFlag = (value) =>
  value === true || value === 'true' || value === 1 || value === '1';

const escapeRegExp = (value) => String(value).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
const GOOGLE_FLOOD_GEOJSON_PATH = '/api/v1/google-flood/geojson/';
const MODULAR_GEOJSON_PATHS = [
  '/api/v1/multimodal/geojson/',
  '/api/v1/models/geosfm/geojson/',
  '/api/v1/models/mike-hydro/geojson/',
  '/api/v1/models/floodproof/geojson/',
  '/api/v1/google-flood/geojson/',
];
const GOOGLE_FLOOD_PARAM_KEYS = ['confidence', 'extended_coverage', 'date', 'scope', 'filter'];
const GEOJSON_FILTER_PARAM_KEYS = ['country_name', 'region_name', 'district_name', 'project_countries', 'basin_id', 'date', 'filter'];
const MULTIMODAL_ALERT_LEVEL_EXPR = [
  'downcase',
  ['to-string', ['coalesce', ['get', 'alert_level'], '']],
];
const MULTIMODAL_DAILY_AVG_EXPR = ['to-number', ['coalesce', ['get', 'daily_avg'], 0]];

const buildMultimodalCircleColorExpression = () => ([
  'case',
  ['==', MULTIMODAL_ALERT_LEVEL_EXPR, 'emergency'], ALERT_COLORS.emergency,
  ['==', MULTIMODAL_ALERT_LEVEL_EXPR, 'alarm'], ALERT_COLORS.alarm,
  ['==', MULTIMODAL_ALERT_LEVEL_EXPR, 'warning'], ALERT_COLORS.warning,
  ['==', MULTIMODAL_ALERT_LEVEL_EXPR, 'normal'], ALERT_COLORS.normal,
  ['>=', MULTIMODAL_DAILY_AVG_EXPR, DEFAULT_THRESHOLDS.emergency], ALERT_COLORS.emergency,
  ['>=', MULTIMODAL_DAILY_AVG_EXPR, DEFAULT_THRESHOLDS.alarm], ALERT_COLORS.alarm,
  ['>=', MULTIMODAL_DAILY_AVG_EXPR, DEFAULT_THRESHOLDS.warning], ALERT_COLORS.warning,
  ALERT_COLORS.normal,
]);

const isMultimodalRenderLayer = (renderLayer = {}, tileUrl = '') => {
  const sourceLayer = String(renderLayer['source-layer'] || '');
  const layerId = String(renderLayer.id || '');
  const haystack = `${sourceLayer} ${layerId} ${tileUrl}`.toLowerCase();
  return haystack.includes('multimodal_points') || haystack.includes('multimodal');
};

const normalizeMultimodalPointStyling = (layerConfig, tileUrl = '') => {
  const renderLayers = layerConfig?.render?.layers;
  if (!Array.isArray(renderLayers) || renderLayers.length === 0) return layerConfig;

  let changed = false;
  const nextRenderLayers = renderLayers.map((renderLayer) => {
    if (renderLayer?.type !== 'circle') return renderLayer;
    if (!isMultimodalRenderLayer(renderLayer, tileUrl)) return renderLayer;

    changed = true;
    return {
      ...renderLayer,
      paint: {
        ...(renderLayer.paint || {}),
        'circle-color': buildMultimodalCircleColorExpression(),
      },
    };
  });

  if (!changed) return layerConfig;

  return {
    ...layerConfig,
    render: {
      ...layerConfig.render,
      layers: nextRenderLayers,
    },
  };
};

const sanitizeTemplateParams = (url) => {
  let sanitized = url;
  // Remove unresolved placeholders like date={{time}} that can break pg_tileserv SQL casts.
  sanitized = sanitized
    .replace(/[&?][^=&]+=\{\{[^}]+\}\}/g, '')
    .replace(/[&?][^=&]+=\{[^}]+\}/g, '');
  // Normalize query separators after removals.
  sanitized = sanitized
    .replace(/\?&/g, '?')
    .replace(/&&/g, '&')
    .replace(/\?$/g, '')
    .replace(/&$/g, '');
  return sanitized;
};

const appendParamsToUrl = (url, params, isFilteredLayer = false) => {
  const [baseUrl, existingQuery = ''] = url.split('?');

  const existingParams = {};
  if (existingQuery) {
    const searchParams = new URLSearchParams(existingQuery);
    searchParams.forEach((value, key) => {
      existingParams[key] = value;
    });
  }

  // Only add backend filter params - ignore legacy and frontend-only params
  if (isFilteredLayer) {
    Object.entries(params).forEach(([key, value]) => {
      // Skip legacy params that shouldn't be in URLs
      if (LEGACY_PARAMS_TO_IGNORE.includes(key)) {
        return;
      }
      // Skip frontend-only params
      if (FRONTEND_ONLY_PARAMS.includes(key)) {
        return;
      }
      // Only add backend filter params with actual values
      if (BACKEND_FILTER_PARAMS.includes(key) && value !== undefined && value !== '' && value !== false) {
        // Keep per-layer admin level from the base URL (admin0/admin1/admin2),
        // do not override it with the globally selected filter level.
        if (key === 'admin_level' && existingParams.admin_level !== undefined) {
          return;
        }
        existingParams[key] = encodeURIComponent(String(value));
      }
    });
  }

  const queryParts = Object.entries(existingParams).map(([key, value]) => `${key}=${value}`);
  const finalQuery = queryParts.join('&');

  const result = finalQuery ? `${baseUrl}?${finalQuery}` : baseUrl;

  return result;
};

const resolveTemplateUrlParams = (url, params = {}) => {
  if (!url || typeof url !== 'string') return url;

  let resolved = url;

  Object.entries(params || {}).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') return;

    const encodedValue = encodeURIComponent(String(value));
    const escapedKey = escapeRegExp(key);

    resolved = resolved
      .replace(new RegExp(`\\{\\{${escapedKey}\\}\\}`, 'g'), encodedValue)
      .replace(new RegExp(`\\{${escapedKey}\\}`, 'g'), encodedValue);
  });

  return sanitizeTemplateParams(resolved);
};

const appendGeojsonParamsToUrl = (url, params = {}) => {
  if (!url || typeof url !== 'string') return url;

  const isModularGeojsonUrl = MODULAR_GEOJSON_PATHS.some((path) => url.includes(path));
  if (!isModularGeojsonUrl) {
    return url;
  }

  const [baseUrl, existingQuery = ''] = url.split('?');
  const searchParams = new URLSearchParams(existingQuery);

  // Apply shared clipping params for all modular GeoJSON model endpoints.
  GEOJSON_FILTER_PARAM_KEYS.forEach((key) => {
    const value = params?.[key];

    if (value === undefined || value === null || value === '') {
      searchParams.delete(key);
      return;
    }

    searchParams.set(key, String(value));
  });

  // Convert frontend WHCA toggle to backend scope for GeoJSON endpoints.
  if (isTruthyFlag(params?.whca_filter)) {
    searchParams.set('scope', 'whca');
  } else if (params?.scope !== undefined && params?.scope !== null && params?.scope !== '') {
    searchParams.set('scope', String(params.scope));
  } else {
    searchParams.delete('scope');
  }

  // Keep Google-specific controls only on Google endpoint.
  if (url.includes(GOOGLE_FLOOD_GEOJSON_PATH)) {
    GOOGLE_FLOOD_PARAM_KEYS.forEach((key) => {
      const value = params?.[key];

      if (value === undefined || value === null || value === '') {
        searchParams.delete(key);
        return;
      }

      searchParams.set(key, String(value));
    });
  } else {
    searchParams.delete('confidence');
    searchParams.delete('extended_coverage');
  }

  const query = searchParams.toString();
  return query ? `${baseUrl}?${query}` : baseUrl;
};

const isWmsTileUrl = (url = '') => /SERVICE=WMS/i.test(url) || url.includes('/mapserver/');

// =============================================================================
// FloodWatch Custom: WHCA Countries Filter - Tile source swapping
// When WHCA filter is active, swap pg_tileserv tile sources to use filtered versions
// =============================================================================
const WHCA_TILE_REPLACEMENTS = {
  // Multimodal forecast points - use WHCA filtered clustered function (gha schema)
  // Note: there is no non-clustered WHCA variant, so all point layers use the clustered version
  'gha.multimodal_points': { replacement: 'gha.multimodal_points_clustered_whca' },
  'gha.multimodal_points_clustered': { replacement: 'gha.multimodal_points_clustered_whca' },
  'gha.multimodal_points_by_admin': { replacement: 'gha.multimodal_points_clustered_whca' },
  // Admin boundaries - use WHCA filtered functions (gha schema) with admin_level param
  'gha.admin0': { replacement: 'gha.admin_whca', params: 'admin_level=0' },
  'gha.admin1': { replacement: 'gha.admin_whca', params: 'admin_level=1' },
  'gha.admin2': { replacement: 'gha.admin_whca', params: 'admin_level=2' },
  // Current mapviewer boundary baseline is admin_clipped; support WHCA swap from it.
  'gha.admin_clipped': { replacement: 'gha.admin_whca' },
  // If project filter was previously active, also allow swapping from project function.
  'gha.admin_by_project': { replacement: 'gha.admin_whca' },
};

// =============================================================================
// FloodWatch Custom: Admin Filter - Tile source swapping for selected admin
// When admin filter is active, swap to admin-clipped versions that accept params
// =============================================================================
const ADMIN_TILE_REPLACEMENTS = {
  // Multimodal points - use admin-filtered function (accepts country_name, region_name, district_name)
  'gha.multimodal_points': { replacement: 'gha.multimodal_points_by_admin' },
  'gha.multimodal_points_clustered': { replacement: 'gha.multimodal_points_by_admin' },
  'gha.multimodal_points_by_admin': { replacement: 'gha.multimodal_points_by_admin' },
  // Admin boundaries - use clipped functions (gha schema) with admin_level param
  'gha.admin0': { replacement: 'gha.admin_clipped', params: 'admin_level=0' },
  'gha.admin1': { replacement: 'gha.admin_clipped', params: 'admin_level=1' },
  'gha.admin2': { replacement: 'gha.admin_clipped', params: 'admin_level=2' },
  // Also handle WHCA layers when admin filter is applied (swap to clipped version)
  'gha.admin_whca': { replacement: 'gha.admin_clipped' },
  // Climate layers - inundation history supports admin clipping (same function, just needs params)
  'climate.inundation_history_clipped': { replacement: 'climate.inundation_history_clipped' },
};

// =============================================================================
// FloodWatch Custom: Basin/Watershed Filter - Tile source swapping
// When basin filter is active, swap to basin-filtered tile functions
// =============================================================================
const BASIN_TILE_REPLACEMENTS = {
  'gha.multimodal_points': { replacement: 'gha.multimodal_points_by_basin' },
  'gha.multimodal_points_clustered': { replacement: 'gha.multimodal_points_by_basin' },
  'gha.multimodal_points_by_admin': { replacement: 'gha.multimodal_points_by_basin' },
};

// =============================================================================
// FloodWatch Custom: Project Filter - Tile source swapping
// When project filter is active, swap to project-filtered versions that accept
// project_countries param (comma-separated country names), uses ST_Within
// =============================================================================
const PROJECT_TILE_REPLACEMENTS = {
  'gha.multimodal_points': { replacement: 'gha.multimodal_points_by_project' },
  'gha.multimodal_points_clustered': { replacement: 'gha.multimodal_points_by_project' },
  'gha.multimodal_points_by_admin': { replacement: 'gha.multimodal_points_by_project' },
  'gha.admin0': { replacement: 'gha.admin_by_project', params: 'admin_level=0' },
  'gha.admin1': { replacement: 'gha.admin_by_project', params: 'admin_level=1' },
  'gha.admin2': { replacement: 'gha.admin_by_project', params: 'admin_level=2' },
  'gha.admin_clipped': { replacement: 'gha.admin_by_project' },
  'gha.admin_whca': { replacement: 'gha.admin_by_project' },
};

const applyBasinFilter = (tileUrl) => {
  let modifiedUrl = tileUrl;
  let newSourceLayer = null;

  Object.entries(BASIN_TILE_REPLACEMENTS).forEach(([original, config]) => {
    const replacement = typeof config === 'object' ? config.replacement : config;

    if (!modifiedUrl.includes(original)) return;

    newSourceLayer = replacement;

    const escapedOriginal = original.replace('.', '\\.');
    const pattern1 = new RegExp(`(tileserv/)${escapedOriginal}(/|\\?)`, 'g');
    modifiedUrl = modifiedUrl.replace(pattern1, `$1${replacement}$2`);
    const pattern2 = new RegExp(`(tileserv/)${escapedOriginal}(\\{)`, 'g');
    modifiedUrl = modifiedUrl.replace(pattern2, `$1${replacement}/$2`);
  });

  return { url: sanitizeTemplateParams(modifiedUrl), sourceLayer: newSourceLayer };
};

const applyProjectFilter = (tileUrl) => {
  let modifiedUrl = tileUrl;
  let newSourceLayer = null;

  Object.entries(PROJECT_TILE_REPLACEMENTS).forEach(([original, config]) => {
    const replacement = typeof config === 'object' ? config.replacement : config;
    const params = typeof config === 'object' ? config.params : null;

    const escapedOriginal = original.replace('.', '\\.');
    if (!modifiedUrl.includes(original)) return;

    newSourceLayer = replacement;

    const pattern1 = new RegExp(`(tileserv/)${escapedOriginal}(/|\\?)`, 'g');
    modifiedUrl = modifiedUrl.replace(pattern1, `$1${replacement}$2`);
    const pattern2 = new RegExp(`(tileserv/)${escapedOriginal}(\\{)`, 'g');
    modifiedUrl = modifiedUrl.replace(pattern2, `$1${replacement}/$2`);

    if (params && modifiedUrl.includes(replacement)) {
      if (modifiedUrl.includes('?')) {
        modifiedUrl = modifiedUrl + '&' + params;
      } else if (modifiedUrl.includes('.pbf')) {
        modifiedUrl = modifiedUrl.replace('.pbf', '.pbf?' + params);
      }
    }
  });

  return { url: sanitizeTemplateParams(modifiedUrl), sourceLayer: newSourceLayer };
};

const applyAdminFilter = (tileUrl) => {
  let modifiedUrl = tileUrl;
  let newSourceLayer = null; // Track the new source layer name for MVT

  Object.entries(ADMIN_TILE_REPLACEMENTS).forEach(([original, config]) => {
    const replacement = typeof config === 'object' ? config.replacement : config;
    const params = typeof config === 'object' ? config.params : null;

    const escapedOriginal = original.replace('.', '\\.');

    // Check if URL contains this source
    if (!modifiedUrl.includes(original)) return;

    // Track the new source layer name (this is what the MVT tile will contain)
    newSourceLayer = replacement;

    // Pattern 1: tileserv/schema.table/ (followed by slash or query)
    const pattern1 = new RegExp(`(tileserv/)${escapedOriginal}(/|\\?)`, 'g');
    modifiedUrl = modifiedUrl.replace(pattern1, `$1${replacement}$2`);

    // Pattern 2: tileserv/schema.table (at end of path segment before {z})
    const pattern2 = new RegExp(`(tileserv/)${escapedOriginal}(\\{)`, 'g');
    modifiedUrl = modifiedUrl.replace(pattern2, `$1${replacement}/$2`);

    // Add query params if specified (e.g., admin_level=0)
    if (params && modifiedUrl.includes(replacement)) {
      if (modifiedUrl.includes('?')) {
        modifiedUrl = modifiedUrl + '&' + params;
      } else if (modifiedUrl.includes('.pbf')) {
        modifiedUrl = modifiedUrl.replace('.pbf', '.pbf?' + params);
      }
    }
  });

  return { url: sanitizeTemplateParams(modifiedUrl), sourceLayer: newSourceLayer };
};

const applyWHCAFilter = (tileUrl) => {
  let modifiedUrl = tileUrl;
  let newSourceLayer = null; // Track the new source layer name for MVT

  Object.entries(WHCA_TILE_REPLACEMENTS).forEach(([original, config]) => {
    const replacement = typeof config === 'object' ? config.replacement : config;
    const params = typeof config === 'object' ? config.params : null;

    // Match the table/function name in pg_tileserv URL patterns
    // Patterns: /pg/tileserv/schema.table/ or /tileserv/schema.table/
    const escapedOriginal = original.replace('.', '\\.');

    // Check if URL contains this source
    if (!modifiedUrl.includes(original)) return;

    // Track the new source layer name (this is what the MVT tile will contain)
    newSourceLayer = replacement;

    // Pattern 1: tileserv/schema.table/ (followed by slash or query)
    const pattern1 = new RegExp(`(tileserv/)${escapedOriginal}(/|\\?)`, 'g');
    modifiedUrl = modifiedUrl.replace(pattern1, `$1${replacement}$2`);

    // Pattern 2: tileserv/schema.table (at end of path segment before {z})
    const pattern2 = new RegExp(`(tileserv/)${escapedOriginal}(\\{)`, 'g');
    modifiedUrl = modifiedUrl.replace(pattern2, `$1${replacement}/$2`);

    // Add query params if specified
    if (params && modifiedUrl.includes(replacement)) {
      if (modifiedUrl.includes('?')) {
        modifiedUrl = modifiedUrl + '&' + params;
      } else if (modifiedUrl.includes('.pbf')) {
        modifiedUrl = modifiedUrl.replace('.pbf', '.pbf?' + params);
      }
    }
  });

  return { url: sanitizeTemplateParams(modifiedUrl), sourceLayer: newSourceLayer };
};

export const processLayers = (layers, paramInteractions, mapSide) => {
  const filteredLayers = mapSide
    ? layers.filter(l => (l.mapSide && l.mapSide === mapSide) || l.isBoundary)
    : layers;

  // FloodWatch Custom: Check filter states
  const isProjectFilterActive =
    isTruthyFlag(paramInteractions?.project_filter) || !!paramInteractions?.project_countries;
  const isWHCAFilterActive = isTruthyFlag(paramInteractions?.whca_filter);
  const isAdminFilterActive = isTruthyFlag(paramInteractions?.admin_filter);
  const isBasinFilterActive = isTruthyFlag(paramInteractions?.basin_filter);

  // Determine if any filtering is active
  const isFilteringActive = isProjectFilterActive || isWHCAFilterActive || isAdminFilterActive || isBasinFilterActive;

  return filteredLayers.map(layer => {
    let tiles = layer.layerConfig?.source?.tiles?.[0] || '';
    const newLayer = { ...layer };

    // Resolve URL templates for GeoJSON string sources
    const sourceData = newLayer.layerConfig?.source?.data;
    if (typeof sourceData === 'string') {
      // Merge layer params with global interactions so project/admin/WHCA
      // clipping applies to modular GeoJSON model endpoints too.
      const params = {
        ...(newLayer.params || {}),
        ...(paramInteractions || {}),
      };
      const resolvedSourceData = appendGeojsonParamsToUrl(
        resolveTemplateUrlParams(sourceData, params),
        params
      );

      if (resolvedSourceData !== sourceData) {
        newLayer.layerConfig = {
          ...newLayer.layerConfig,
          source: {
            ...newLayer.layerConfig.source,
            data: resolvedSourceData,
          },
        };
      }
    }

    if (!tiles) {
      if (newLayer.layerConfig) {
        newLayer.layerConfig = normalizeMultimodalPointStyling(newLayer.layerConfig);
      }
      return newLayer;
    }

    const originalTiles = tiles;
    let tileSourceSwapped = false;
    let newSourceLayer = null;

    // FloodWatch Custom: Apply tile source swapping based on filter state
    // Priority: Basin > Project > WHCA > Admin
    if (isBasinFilterActive) {
      const result = applyBasinFilter(tiles);
      tiles = result.url;
      newSourceLayer = result.sourceLayer;
      tileSourceSwapped = tiles !== originalTiles;
    } else if (isProjectFilterActive) {
      // Project filter: swap to project-filtered functions (accepts project_countries param)
      const result = applyProjectFilter(tiles);
      tiles = result.url;
      newSourceLayer = result.sourceLayer;
      tileSourceSwapped = tiles !== originalTiles;
    } else if (isWHCAFilterActive) {
      // Always use WHCA filter — the WHCA pg_tileserv functions accept
      // country_name, region_name, district_name for admin drill-down
      const result = applyWHCAFilter(tiles);
      tiles = result.url;
      newSourceLayer = result.sourceLayer;
      tileSourceSwapped = tiles !== originalTiles;
    } else if (isAdminFilterActive) {
      const result = applyAdminFilter(tiles);
      tiles = result.url;
      newSourceLayer = result.sourceLayer;
      tileSourceSwapped = tiles !== originalTiles;
    }

    // If the source was already a filtered function (e.g. gha.admin_clipped),
    // we still need to append admin params even when no swap happened.
    const isAlreadyFilteredLayer =
      (isProjectFilterActive && (
        tiles.includes('tileserv/gha.multimodal_points_by_project') ||
        tiles.includes('tileserv/gha.admin_by_project')
      )) ||
      (isWHCAFilterActive && (
        tiles.includes('tileserv/gha.multimodal_points_clustered_whca') ||
        tiles.includes('tileserv/gha.admin_whca') ||
        tiles.includes('tileserv/gha.admin_clipped')
      )) ||
      (isAdminFilterActive && (
        tiles.includes('tileserv/gha.admin_clipped') ||
        tiles.includes('tileserv/gha.multimodal_points_by_admin') ||
        tiles.includes('tileserv/climate.inundation_history_clipped')
      )) ||
      (isBasinFilterActive && tiles.includes('tileserv/gha.multimodal_points_by_basin'));

    // Add filter params when swapped OR when already on a filtered function source.
    if ((tileSourceSwapped || isAlreadyFilteredLayer) && isFilteringActive) {
      const updatedTiles = appendParamsToUrl(tiles, paramInteractions, true);

      // Update the layer config with new tiles URL
      newLayer.layerConfig = {
        ...newLayer.layerConfig,
        source: {
          ...newLayer.layerConfig.source,
          tiles: [updatedTiles]
        }
      };

      // CRITICAL: Update source-layer in render.layers to match MVT layer name
      // MVT tiles contain an embedded layer name that MUST match the style's source-layer
      if (newSourceLayer && newLayer.layerConfig.render?.layers) {
        newLayer.layerConfig = {
          ...newLayer.layerConfig,
          render: {
            ...newLayer.layerConfig.render,
            layers: newLayer.layerConfig.render.layers.map(renderLayer => ({
              ...renderLayer,
              'source-layer': newSourceLayer
            }))
          }
        };
      }
    }

    // Ensure MapServer WMS raster requests receive clipping scope params as well.
    const resolvedTiles = newLayer.layerConfig?.source?.tiles?.[0] || tiles || originalTiles;
    if (isWmsTileUrl(resolvedTiles) && isFilteringActive) {
      const wmsParams = {
        country_name: paramInteractions?.country_name || '',
        region_name: paramInteractions?.region_name || '',
        district_name: paramInteractions?.district_name || '',
        project_countries: paramInteractions?.project_countries || '',
      };

      if (isWHCAFilterActive) {
        wmsParams.scope = 'whca';
      } else if (isProjectFilterActive) {
        wmsParams.scope = 'project';
      } else {
        wmsParams.scope = 'all';
      }

      newLayer.layerConfig = {
        ...newLayer.layerConfig,
        source: {
          ...newLayer.layerConfig.source,
          tiles: [appendParamsToUrl(resolvedTiles, wmsParams, true)],
        },
      };
    }

    if (newLayer.layerConfig) {
      const finalTiles = newLayer.layerConfig?.source?.tiles?.[0] || tiles || originalTiles;
      newLayer.layerConfig = normalizeMultimodalPointStyling(newLayer.layerConfig, finalTiles);
    }

    return newLayer;
  });
};
