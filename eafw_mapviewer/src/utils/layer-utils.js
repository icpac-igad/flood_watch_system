// FloodWatch Custom: Params that should be passed to backend for filtering
// These are the ONLY params we want to add to pg_tileserv URLs
const BACKEND_FILTER_PARAMS = ['country_name', 'region_name', 'district_name', 'whca_countries', 'admin_level', 'risk_level'];

// Params that control frontend behavior but shouldn't be in URLs
const FRONTEND_ONLY_PARAMS = ['admin_filter', 'whca_filter'];

// Params that are legacy GFW-style and should be ignored
const LEGACY_PARAMS_TO_IGNORE = ['unit_id', 'MASK_UNIT_ID', 'MASK_ADMIN_LEVEL', 'MASK_AREA', 'border_level', 'project_name'];

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
        existingParams[key] = encodeURIComponent(String(value));
      }
    });
  }

  const queryParts = Object.entries(existingParams).map(([key, value]) => `${key}=${value}`);
  const finalQuery = queryParts.join('&');

  const result = finalQuery ? `${baseUrl}?${finalQuery}` : baseUrl;

  return result;
};

// =============================================================================
// FloodWatch Custom: WHCA Countries Filter - Tile source swapping
// When WHCA filter is active, swap pg_tileserv tile sources to use filtered versions
// =============================================================================
const WHCA_TILE_REPLACEMENTS = {
  // Multimodal forecast points - use WHCA filtered function (gha schema)
  'gha.multimodal_points': { replacement: 'gha.multimodal_points_whca' },
  'gha.multimodal_points_clustered': { replacement: 'gha.multimodal_points_clustered_whca' },
  'gha.multimodal_points_by_admin': { replacement: 'gha.multimodal_points_clustered_whca' },
  // Admin boundaries - use WHCA filtered functions (gha schema) with admin_level param
  'gha.admin0': { replacement: 'gha.admin_whca', params: 'admin_level=0' },
  'gha.admin1': { replacement: 'gha.admin_whca', params: 'admin_level=1' },
  'gha.admin2': { replacement: 'gha.admin_whca', params: 'admin_level=2' },
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

  return { url: modifiedUrl, sourceLayer: newSourceLayer };
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

  return { url: modifiedUrl, sourceLayer: newSourceLayer };
};

export const processLayers = (layers, paramInteractions, mapSide) => {
  const filteredLayers = mapSide
    ? layers.filter(l => (l.mapSide && l.mapSide === mapSide) || l.isBoundary)
    : layers;

  // FloodWatch Custom: Check if WHCA filter is active
  const isWHCAFilterActive = paramInteractions?.whca_filter === true;

  // FloodWatch Custom: Check if admin filter is active (user selected a country/region/district)
  const isAdminFilterActive = paramInteractions?.admin_filter === true;

  // FloodWatch Custom: Has specific admin selection (country_name set means drilling down)
  const hasAdminSelection = !!(paramInteractions?.country_name);

  // Determine if any filtering is active
  const isFilteringActive = isWHCAFilterActive || isAdminFilterActive;

  return filteredLayers.map(layer => {
    let tiles = layer.layerConfig?.source?.tiles?.[0] || '';
    const newLayer = { ...layer };
    if (!tiles) {
      return newLayer;
    }

    const originalTiles = tiles;
    let tileSourceSwapped = false;
    let newSourceLayer = null;

    // FloodWatch Custom: Apply tile source swapping based on filter state
    if (isWHCAFilterActive) {
      if (hasAdminSelection) {
        // WHCA mode with admin drill-down: use admin-filtered functions
        const result = applyAdminFilter(tiles);
        tiles = result.url;
        newSourceLayer = result.sourceLayer;
        tileSourceSwapped = tiles !== originalTiles;
      } else {
        // WHCA mode without drill-down: use WHCA-filtered functions
        const result = applyWHCAFilter(tiles);
        tiles = result.url;
        newSourceLayer = result.sourceLayer;
        tileSourceSwapped = tiles !== originalTiles;
      }
    } else if (isAdminFilterActive) {
      // Pure admin filter mode (no WHCA): use admin-filtered functions
      const result = applyAdminFilter(tiles);
      tiles = result.url;
      newSourceLayer = result.sourceLayer;
      tileSourceSwapped = tiles !== originalTiles;
    }

    // Only add filter params to layers that had their tile source swapped
    // This ensures only the filtered layers get the country/region params
    if (tileSourceSwapped && isFilteringActive) {
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

    return newLayer;
  });
};