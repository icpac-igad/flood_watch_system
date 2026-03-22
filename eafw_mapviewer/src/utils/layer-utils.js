import { ALERT_COLORS, DEFAULT_THRESHOLDS, ALERT_ICON_NAMES, CLUSTER_ICON_PREFIX } from './multimodal-config';

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
const GOOGLE_FLOOD_GEOJSON_PATH = '/api/v1/google-flood/geojson';
const MODULAR_GEOJSON_PATHS = [
  '/api/v1/multimodal/geojson',
  '/api/v1/models/geosfm/geojson',
  '/api/v1/models/mike-hydro/geojson',
  '/api/v1/models/floodproof/geojson',
  '/api/v1/google-flood/geojson',
];
const GOOGLE_FLOOD_PARAM_KEYS = ['confidence', 'extended_coverage', 'date', 'scope', 'filter'];
const GEOJSON_FILTER_PARAM_KEYS = ['country_name', 'region_name', 'district_name', 'project_countries', 'basin_id', 'date', 'filter'];
const MULTIMODAL_ALERT_LEVEL_EXPR = [
  'downcase',
  [
    'to-string',
    [
      'coalesce',
      ['get', 'alert_level'],
      ['get', 'risk_level'],
      ['get', 'latest_severity'],
      '',
    ],
  ],
];
const MULTIMODAL_ALERT_PRIORITY_EXPR = [
  'to-number',
  ['coalesce', ['get', 'alert_priority'], ['get', 'severity'], 0],
];
const MULTIMODAL_DAILY_AVG_EXPR = ['to-number', ['coalesce', ['get', 'daily_avg'], 0]];
const MULTIMODAL_POINT_COUNT_EXPR = ['to-number', ['coalesce', ['get', 'point_count'], 1]];
const MULTIMODAL_IS_CLUSTER_FEATURE_EXPR = ['>', MULTIMODAL_POINT_COUNT_EXPR, 1];

const MULTIMODAL_IS_EMERGENCY_EXPR = [
  'any',
  ['==', MULTIMODAL_ALERT_LEVEL_EXPR, 'emergency'],
  ['==', MULTIMODAL_ALERT_LEVEL_EXPR, 'extreme'],
  ['==', MULTIMODAL_ALERT_LEVEL_EXPR, 'extreme_flooding'],
  ['==', MULTIMODAL_ALERT_LEVEL_EXPR, 'major_flooding'],
  ['>=', MULTIMODAL_ALERT_PRIORITY_EXPR, 4],
];

const MULTIMODAL_IS_ALARM_EXPR = [
  'any',
  ['==', MULTIMODAL_ALERT_LEVEL_EXPR, 'alarm'],
  ['==', MULTIMODAL_ALERT_LEVEL_EXPR, 'severe'],
  ['==', MULTIMODAL_ALERT_LEVEL_EXPR, 'danger'],
  ['==', MULTIMODAL_ALERT_LEVEL_EXPR, 'moderate_flooding'],
  ['>=', MULTIMODAL_ALERT_PRIORITY_EXPR, 3],
];

const MULTIMODAL_IS_WARNING_EXPR = [
  'any',
  ['==', MULTIMODAL_ALERT_LEVEL_EXPR, 'warning'],
  ['==', MULTIMODAL_ALERT_LEVEL_EXPR, 'moderate'],
  ['==', MULTIMODAL_ALERT_LEVEL_EXPR, 'watch'],
  ['==', MULTIMODAL_ALERT_LEVEL_EXPR, 'minor_flooding'],
  ['==', MULTIMODAL_ALERT_LEVEL_EXPR, 'alert'],
  ['>=', MULTIMODAL_ALERT_PRIORITY_EXPR, 2],
];

const MULTIMODAL_IS_NORMAL_EXPR = [
  'any',
  ['==', MULTIMODAL_ALERT_LEVEL_EXPR, 'normal'],
  ['==', MULTIMODAL_ALERT_LEVEL_EXPR, 'minor'],
  ['==', MULTIMODAL_ALERT_LEVEL_EXPR, 'none'],
  ['>=', MULTIMODAL_ALERT_PRIORITY_EXPR, 1],
];

const buildMultimodalCircleColorExpression = () => ([
  'case',
  MULTIMODAL_IS_EMERGENCY_EXPR, ALERT_COLORS.emergency,
  MULTIMODAL_IS_ALARM_EXPR, ALERT_COLORS.alarm,
  MULTIMODAL_IS_WARNING_EXPR, ALERT_COLORS.warning,
  MULTIMODAL_IS_NORMAL_EXPR, ALERT_COLORS.normal,
  ['>=', MULTIMODAL_DAILY_AVG_EXPR, DEFAULT_THRESHOLDS.emergency], ALERT_COLORS.emergency,
  ['>=', MULTIMODAL_DAILY_AVG_EXPR, DEFAULT_THRESHOLDS.alarm], ALERT_COLORS.alarm,
  ['>=', MULTIMODAL_DAILY_AVG_EXPR, DEFAULT_THRESHOLDS.warning], ALERT_COLORS.warning,
  ALERT_COLORS.normal,
]);

const buildMultimodalCircleRadiusExpression = () => ([
  'case',
  ['>', ['to-number', ['coalesce', ['get', 'point_count'], 1]], 50], 18,
  ['>', ['to-number', ['coalesce', ['get', 'point_count'], 1]], 10], 14,
  ['>', ['to-number', ['coalesce', ['get', 'point_count'], 1]], 1], 10,
  8,
]);

const STATIC_MULTIMODAL_TRANSITION = { duration: 0, delay: 0 };

export const isMultimodalRenderLayer = (
  renderLayer = {},
  layerConfig = {},
  tileUrl = '',
  layerMeta = {}
) => {
  const sourceLayer = String(renderLayer['source-layer'] || '');
  const layerId = String(renderLayer.id || '');
  const sourceType = String(layerConfig?.source?.type || '');
  const sourceData = String(
    typeof layerConfig?.source?.data === 'string' ? layerConfig.source.data : ''
  );
  const sourceTiles = Array.isArray(layerConfig?.source?.tiles)
    ? String(layerConfig.source.tiles[0] || '')
    : '';
  const layerName = String(layerMeta?.name || '');
  const datasetName = String(layerMeta?.datasetName || '');
  const datasetId = String(layerMeta?.datasetId || '');

  const haystack =
    `${sourceLayer} ${layerId} ${tileUrl} ${sourceType} ${sourceData} ${sourceTiles} ${layerName} ${datasetName} ${datasetId}`.toLowerCase();

  return (
    haystack.includes('multimodal_points') ||
    haystack.includes('multimodal') ||
    haystack.includes('multi model') ||
    haystack.includes('multi-model') ||
    haystack.includes('geosfm') ||
    haystack.includes('floodproof') ||
    haystack.includes('mike hydro') ||
    haystack.includes('mike-hydro') ||
    haystack.includes('google flood') ||
    haystack.includes('google-flood') ||
    haystack.includes('/api/v1/models/') ||
    haystack.includes('/api/v1/google-flood/geojson/')
  );
};

export const buildMultimodalIconImageExpression = () => ([
  'case',
  MULTIMODAL_IS_EMERGENCY_EXPR, ALERT_ICON_NAMES.emergency,
  MULTIMODAL_IS_ALARM_EXPR, ALERT_ICON_NAMES.alarm,
  MULTIMODAL_IS_WARNING_EXPR, ALERT_ICON_NAMES.warning,
  MULTIMODAL_IS_NORMAL_EXPR, ALERT_ICON_NAMES.normal,
  ['>=', MULTIMODAL_DAILY_AVG_EXPR, DEFAULT_THRESHOLDS.emergency], ALERT_ICON_NAMES.emergency,
  ['>=', MULTIMODAL_DAILY_AVG_EXPR, DEFAULT_THRESHOLDS.alarm], ALERT_ICON_NAMES.alarm,
  ['>=', MULTIMODAL_DAILY_AVG_EXPR, DEFAULT_THRESHOLDS.warning], ALERT_ICON_NAMES.warning,
  ALERT_ICON_NAMES.normal,
]);

export const buildMultimodalClusterIconImageExpression = () => ([
  'case',
  MULTIMODAL_IS_EMERGENCY_EXPR, `${CLUSTER_ICON_PREFIX}emergency`,
  MULTIMODAL_IS_ALARM_EXPR, `${CLUSTER_ICON_PREFIX}alarm`,
  MULTIMODAL_IS_WARNING_EXPR, `${CLUSTER_ICON_PREFIX}warning`,
  MULTIMODAL_IS_NORMAL_EXPR, `${CLUSTER_ICON_PREFIX}normal`,
  ['>=', MULTIMODAL_DAILY_AVG_EXPR, DEFAULT_THRESHOLDS.emergency], `${CLUSTER_ICON_PREFIX}emergency`,
  ['>=', MULTIMODAL_DAILY_AVG_EXPR, DEFAULT_THRESHOLDS.alarm], `${CLUSTER_ICON_PREFIX}alarm`,
  ['>=', MULTIMODAL_DAILY_AVG_EXPR, DEFAULT_THRESHOLDS.warning], `${CLUSTER_ICON_PREFIX}warning`,
  `${CLUSTER_ICON_PREFIX}normal`,
]);

const buildMultimodalSymbolIconImageExpression = () => ([
  'case',
  MULTIMODAL_IS_CLUSTER_FEATURE_EXPR, buildMultimodalClusterIconImageExpression(),
  buildMultimodalIconImageExpression(),
]);

const buildMultimodalSymbolIconSizeExpression = () => ([
  'case',
  ['>', MULTIMODAL_POINT_COUNT_EXPR, 50], 0.62,
  ['>', MULTIMODAL_POINT_COUNT_EXPR, 10], 0.52,
  MULTIMODAL_IS_CLUSTER_FEATURE_EXPR, 0.44,
  0.34,
]);

const buildMultimodalClusterCountTextExpression = () => ([
  'case',
  MULTIMODAL_IS_CLUSTER_FEATURE_EXPR,
  ['to-string', ['coalesce', ['get', 'point_count_abbreviated'], ['get', 'point_count'], '']],
  '',
]);

const buildMultimodalTextSizeExpression = () => ([
  'interpolate',
  ['linear'],
  ['zoom'],
  3, 9,
  8, 11,
  12, 12.5,
]);

const buildMultimodalSortKeyExpression = () => ([
  'case',
  MULTIMODAL_IS_CLUSTER_FEATURE_EXPR,
  ['+', 1000, MULTIMODAL_POINT_COUNT_EXPR],
  MULTIMODAL_ALERT_PRIORITY_EXPR,
]);

const hasPointCountFilterReference = (filter) => {
  if (!filter) return false;
  try {
    return JSON.stringify(filter).includes('point_count');
  } catch {
    return false;
  }
};

const normalizeMultimodalPointStyling = (layerConfig, tileUrl = '', layerMeta = {}) => {
  const renderLayers = layerConfig?.render?.layers;
  if (!Array.isArray(renderLayers) || renderLayers.length === 0) return layerConfig;

  let changed = false;
  const nextRenderLayers = renderLayers.map((renderLayer) => {
    if (!isMultimodalRenderLayer(renderLayer, layerConfig, tileUrl, layerMeta)) return renderLayer;

    if (renderLayer.type === 'symbol') {
      const layerId = String(renderLayer?.id || '').toLowerCase();
      const hasIconDirective =
        Object.prototype.hasOwnProperty.call(renderLayer?.layout || {}, 'icon-image');
      const isExplicitClusterLayer =
        hasPointCountFilterReference(renderLayer?.filter) ||
        layerId.includes('cluster');
      const looksLikePointLayer =
        hasIconDirective ||
        isExplicitClusterLayer ||
        layerId.includes('point');

      if (!looksLikePointLayer) {
        return renderLayer;
      }

      changed = true;

      const countTextExpression = isExplicitClusterLayer
        ? ['to-string', ['coalesce', ['get', 'point_count_abbreviated'], ['get', 'point_count'], '']]
        : buildMultimodalClusterCountTextExpression();
      return {
        ...renderLayer,
        layout: {
          ...(renderLayer.layout || {}),
          'icon-image': buildMultimodalSymbolIconImageExpression(),
          'icon-size': buildMultimodalSymbolIconSizeExpression(),
          'icon-anchor': 'center',
          'icon-pitch-alignment': 'viewport',
          'icon-allow-overlap': false,
          'icon-ignore-placement': false,
          'icon-optional': false,
          'icon-padding': 8,
          'symbol-sort-key': buildMultimodalSortKeyExpression(),
          'text-field': countTextExpression,
          'text-font': ['Noto Sans Bold'],
          'text-size': buildMultimodalTextSizeExpression(),
          'text-anchor': 'center',
          'text-offset': [0, 0],
          'text-allow-overlap': false,
          'text-ignore-placement': false,
          'text-optional': true,
          'text-pitch-alignment': 'viewport',
        },
        paint: {
          ...(renderLayer.paint || {}),
          'icon-opacity': 0.94,
          'text-color': '#ffffff',
          'text-halo-color': 'rgba(6, 18, 37, 0.6)',
          'text-halo-width': 1.3,
          'text-opacity': [
            'case',
            MULTIMODAL_IS_CLUSTER_FEATURE_EXPR, 0.98,
            0,
          ],
        },
      };
    }

    if (renderLayer.type === 'circle') {
      const layerId = String(renderLayer?.id || '').toLowerCase();
      const isExplicitClusterLayer =
        hasPointCountFilterReference(renderLayer?.filter) ||
        layerId.includes('cluster');
      const countTextExpression = isExplicitClusterLayer
        ? ['to-string', ['coalesce', ['get', 'point_count_abbreviated'], ['get', 'point_count'], '']]
        : buildMultimodalClusterCountTextExpression();

      changed = true;

      return {
        ...renderLayer,
        type: 'symbol',
        layout: {
          ...(renderLayer.layout || {}),
          'icon-image': buildMultimodalSymbolIconImageExpression(),
          'icon-size': buildMultimodalSymbolIconSizeExpression(),
          'icon-anchor': 'center',
          'icon-pitch-alignment': 'viewport',
          'icon-allow-overlap': false,
          'icon-ignore-placement': false,
          'icon-optional': false,
          'icon-padding': 8,
          'symbol-sort-key': buildMultimodalSortKeyExpression(),
          'text-field': countTextExpression,
          'text-font': ['Noto Sans Bold'],
          'text-size': buildMultimodalTextSizeExpression(),
          'text-anchor': 'center',
          'text-offset': [0, 0],
          'text-allow-overlap': false,
          'text-ignore-placement': false,
          'text-optional': true,
          'text-pitch-alignment': 'viewport',
        },
        paint: {
          'icon-opacity': 0.94,
          'text-color': '#ffffff',
          'text-halo-color': 'rgba(6, 18, 37, 0.6)',
          'text-halo-width': 1.3,
          'text-opacity': [
            'case',
            MULTIMODAL_IS_CLUSTER_FEATURE_EXPR, 0.98,
            0,
          ],
        },
      };
    }

    return renderLayer;
  });

  if (!changed) return layerConfig;

  return {
    ...layerConfig,
    render: {
      ...layerConfig.render,
      layers: nextRenderLayers,
      parse: false,
    },
  };
};

const SAFE_TILE_TEMPLATE_VALUES = new Set([
  '{bbox-epsg-3857}',
  '{{bbox-epsg-3857}}',
  '{bbox-epsg-4326}',
  '{{bbox-epsg-4326}}',
  '{bbox}',
  '{{bbox}}',
  '{z}',
  '{{z}}',
  '{x}',
  '{{x}}',
  '{y}',
  '{{y}}',
  '{-y}',
  '{{-y}}',
  '{tms-y}',
  '{{tms-y}}',
  '{quadkey}',
  '{{quadkey}}',
  '{ratio}',
  '{{ratio}}',
  '{s}',
  '{{s}}',
]);

const decodeUrlComponentSafe = (value = '') => {
  try {
    return decodeURIComponent(value);
  } catch (error) {
    return value;
  }
};

const extractTileservSourceLayer = (url = '') => {
  const match = String(url || '').match(/(?:\/|^)tileserv\/([^/?]+)(?:\/|\?|$)/i);
  if (!match || !match[1]) return null;

  const normalized = decodeUrlComponentSafe(match[1]).trim();
  return normalized || null;
};

const isTemplateToken = (value = '') => /^\{\{?[^}]+\}\}?$/.test(value.trim());

const sanitizeTemplateParams = (url) => {
  if (!url || typeof url !== 'string' || !url.includes('?')) return url;

  const [baseUrl, rawQuery = ''] = url.split('?');
  if (!rawQuery) return url;

  const keptQueryParts = rawQuery
    .split('&')
    .filter(Boolean)
    .filter((part) => {
      const [rawKey, ...valueParts] = part.split('=');
      if (!rawKey) return false;
      if (!valueParts.length) return true;

      const decodedKey = decodeUrlComponentSafe(rawKey).trim().toLowerCase();
      const rawValue = valueParts.join('=');
      const decodedValue = decodeUrlComponentSafe(rawValue).trim();
      const normalizedValue = decodedValue.toLowerCase();

      // Empty time params (time=) trigger 400s from mapcache/WMS for time-dimension layers.
      if ((decodedKey === 'time' || decodedKey === 'dim_time') && decodedValue === '') {
        return false;
      }

      // Remove unresolved placeholders like date={{time}} that can break SQL casts,
      // but preserve map coordinate placeholders needed by maplibre/mapcache.
      if (isTemplateToken(normalizedValue) && !SAFE_TILE_TEMPLATE_VALUES.has(normalizedValue)) {
        return false;
      }

      return true;
    });

  const sanitizedQuery = keptQueryParts.join('&');
  return sanitizedQuery ? `${baseUrl}?${sanitizedQuery}` : baseUrl;
};

const getBrowserOrigin = () => {
  if (typeof window !== 'undefined' && window.location?.origin) {
    return window.location.origin;
  }
  return '';
};

const absolutizeRuntimeUrl = (url = '') => {
  if (!url || typeof url !== 'string') return url;

  const normalized = url.trim();
  const origin = getBrowserOrigin();
  if (!origin) return normalized;

  if (normalized.startsWith('//') && window.location?.protocol) {
    return `${window.location.protocol}${normalized}`;
  }

  if (normalized.startsWith('/')) {
    return `${origin}${normalized}`;
  }

  if (!/^https?:\/\//i.test(normalized)) {
    return normalized;
  }

  try {
    const parsed = new URL(normalized);
    const loopbackHosts = new Set(['127.0.0.1', 'localhost', '0.0.0.0', '::1']);
    const internalPathPrefixes = [
      '/api/',
      '/pg/',
      '/tileserv/',
      '/mapcache/',
      '/mapserver/',
      '/media/',
      '/static/',
    ];
    const shouldForceSameOrigin =
      parsed.origin !== origin &&
      internalPathPrefixes.some((prefix) => parsed.pathname.startsWith(prefix));

    // For app-internal endpoints returned as absolute URLs (e.g. CMS config),
    // prefer current browser origin to avoid cross-origin/CORS failures.
    if (shouldForceSameOrigin) {
      const afterOrigin = normalized.slice(parsed.origin.length);
      return `${origin}${afterOrigin}`;
    }

    if (loopbackHosts.has(parsed.hostname)) {
      // Reconstruct from the raw string to preserve template tokens like {z}/{x}/{y}
      // (new URL() encodes curly braces in pathname which breaks MapLibre tile templates)
      const afterOrigin = normalized.slice(parsed.origin.length);
      return `${origin}${afterOrigin}`;
    }
  } catch (error) {
    return normalized;
  }

  return normalized;
};

const appendParamsToUrl = (url, params, isFilteredLayer = false) => {
  // Preserve MapLibre template tokens like {bbox-epsg-3857}, {z}, {x}, {y}
  // by extracting them before URLSearchParams encoding (which would percent-encode curlies).
  const TEMPLATE_PLACEHOLDER_RE = /\{[a-zA-Z0-9_-]+\}/g;
  const placeholderMap = {};
  let placeholderIdx = 0;
  const safeUrl = url.replace(TEMPLATE_PLACEHOLDER_RE, (match) => {
    const key = `__TPL${placeholderIdx++}__`;
    placeholderMap[key] = match;
    return key;
  });

  const [baseUrl, existingQuery = ''] = safeUrl.split('?');
  const searchParams = existingQuery ? new URLSearchParams(existingQuery) : new URLSearchParams();

  if (isFilteredLayer) {
    Object.entries(params).forEach(([key, value]) => {
      if (LEGACY_PARAMS_TO_IGNORE.includes(key)) return;
      if (FRONTEND_ONLY_PARAMS.includes(key)) return;
      if (BACKEND_FILTER_PARAMS.includes(key) && value !== undefined && value !== '' && value !== false) {
        searchParams.set(key, String(value));
      }
    });
  }

  const finalQuery = searchParams.toString();
  let result = finalQuery ? `${baseUrl}?${finalQuery}` : baseUrl;

  // Restore MapLibre template tokens
  Object.entries(placeholderMap).forEach(([placeholder, original]) => {
    result = result.replace(placeholder, original);
  });

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

  // GeoJSON endpoints currently accept scope=all|whca only.
  // For non-WHCA project scopes, pass project_countries without scope
  // to avoid 400 "Invalid scope" responses.
  const normalizedScope = String(params?.scope || '').toLowerCase();
  if (isTruthyFlag(params?.whca_filter) || normalizedScope === 'whca') {
    searchParams.set('scope', 'whca');
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

const isWmsTileUrl = (url = '') => /SERVICE=WMS/i.test(url) || url.includes('/mapserver/') || url.includes('/mapcache/');

const isRasterTileUrl = (url = '') => isWmsTileUrl(url);

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
  // WRF rainfall layers - same function, clipping params appended by pg_tileserv
  'wrf.get_total_rainfall_tiles': { replacement: 'wrf.get_total_rainfall_tiles' },
  'wrf.get_extreme_rainfall_tiles': { replacement: 'wrf.get_extreme_rainfall_tiles' },
  'wrf.get_daily_rainfall_tiles': { replacement: 'wrf.get_daily_rainfall_tiles' },
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
  // WRF rainfall layers - same function, clipping params appended by pg_tileserv
  'wrf.get_total_rainfall_tiles': { replacement: 'wrf.get_total_rainfall_tiles' },
  'wrf.get_extreme_rainfall_tiles': { replacement: 'wrf.get_extreme_rainfall_tiles' },
  'wrf.get_daily_rainfall_tiles': { replacement: 'wrf.get_daily_rainfall_tiles' },
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
  // WRF rainfall layers - same function, clipping params appended by pg_tileserv
  'wrf.get_total_rainfall_tiles': { replacement: 'wrf.get_total_rainfall_tiles' },
  'wrf.get_extreme_rainfall_tiles': { replacement: 'wrf.get_extreme_rainfall_tiles' },
  'wrf.get_daily_rainfall_tiles': { replacement: 'wrf.get_daily_rainfall_tiles' },
};

// =============================================================================
// FloodWatch Custom: Legacy tile source remapping
// Keep old CMS layer configs working when source tables/functions were renamed.
// =============================================================================
const LEGACY_TILE_REPLACEMENTS = {
  'boundary.ea_watersheds_level_03_v1': { replacement: 'gha.nile_basin_mask' },
  'boundary.get_pre_defined_boundary': { replacement: 'cms.capeditor_predefinedalertarea' },
  'cms.capeditor_predefinedalertarea': { replacement: 'cms.capeditor_predefinedalertarea' },
  'rivers.osm_waterways_default': { replacement: 'gha.hydro_rivers' },
  'rivers.osm_waterways': { replacement: 'gha.hydro_rivers' },
};

const applyLegacyTileReplacement = (tileUrl) => {
  let modifiedUrl = tileUrl;
  let newSourceLayer = null;

  Object.entries(LEGACY_TILE_REPLACEMENTS).forEach(([original, config]) => {
    const replacement = typeof config === 'object' ? config.replacement : config;
    const escapedOriginal = original.replace('.', '\\.');

    if (!modifiedUrl.includes(original)) return;

    newSourceLayer = replacement;

    const pattern1 = new RegExp(`(tileserv/)${escapedOriginal}(/|\\?)`, 'g');
    modifiedUrl = modifiedUrl.replace(pattern1, `$1${replacement}$2`);
    const pattern2 = new RegExp(`(tileserv/)${escapedOriginal}(\\{)`, 'g');
    modifiedUrl = modifiedUrl.replace(pattern2, `$1${replacement}/$2`);
  });

  return { url: sanitizeTemplateParams(modifiedUrl), sourceLayer: newSourceLayer };
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

const applyAdminBoundaryZoomBand = (layerConfig, tileUrl = '') => {
  if (!layerConfig?.render?.layers || !Array.isArray(layerConfig.render.layers)) {
    return layerConfig;
  }

  const lowerUrl = String(tileUrl || '').toLowerCase();
  if (
    !lowerUrl.includes('tileserv/gha.admin_clipped') &&
    !lowerUrl.includes('tileserv/gha.admin_whca') &&
    !lowerUrl.includes('tileserv/gha.admin_by_project')
  ) {
    return layerConfig;
  }

  const levelMatch = lowerUrl.match(/[?&]admin_level=([^&]+)/);
  const adminLevel = levelMatch?.[1];
  if (!['0', '1', '2'].includes(adminLevel)) {
    return layerConfig;
  }

  const bands = {
    '0': { minzoom: 0 },
    '1': { minzoom: 5.5, maxzoom: 8 },
    '2': { minzoom: 8 },
  };
  const band = bands[adminLevel];

  return {
    ...layerConfig,
    render: {
      ...layerConfig.render,
      layers: layerConfig.render.layers.map((renderLayer) => ({
        ...renderLayer,
        ...band,
      })),
    },
  };
};

export const processLayers = (layers, paramInteractions, mapSide) => {
  const filteredLayers = mapSide
    ? layers.filter(l => (l.mapSide && l.mapSide === mapSide) || l.isBoundary)
    : layers;

  const scopeValue = String(paramInteractions?.scope || '').toLowerCase();
  const hasProjectScope = scopeValue === 'project';
  const hasWhcaScope = scopeValue === 'whca';

  // FloodWatch Custom: Check filter states
  const isProjectFilterActive =
    isTruthyFlag(paramInteractions?.project_filter) || !!paramInteractions?.project_countries || hasProjectScope;
  const isWHCAFilterActive = isTruthyFlag(paramInteractions?.whca_filter) || hasWhcaScope;
  const isAdminFilterActive = isTruthyFlag(paramInteractions?.admin_filter);
  const isBasinFilterActive = isTruthyFlag(paramInteractions?.basin_filter);

  // Determine if any filtering is active
  const isFilteringActive = isProjectFilterActive || isWHCAFilterActive || isAdminFilterActive || isBasinFilterActive;
  const resolvedScope = hasWhcaScope
    ? 'whca'
    : hasProjectScope
      ? 'project'
      : isWHCAFilterActive
        ? 'whca'
        : isProjectFilterActive
          ? 'project'
          : 'all';
  const backendFilterParams = {
    ...(paramInteractions || {}),
    scope: resolvedScope,
  };

  return filteredLayers.map(layer => {
    let tiles = layer.layerConfig?.source?.tiles?.[0] || '';
    const newLayer = { ...layer };
    if (tiles) {
      const absoluteTiles = absolutizeRuntimeUrl(tiles);
      if (absoluteTiles !== tiles && newLayer.layerConfig?.source) {
        tiles = absoluteTiles;
        newLayer.layerConfig = {
          ...newLayer.layerConfig,
          source: {
            ...newLayer.layerConfig.source,
            tiles: [absoluteTiles],
          },
        };
      }

      // Resolve URL templates for raster tile sources too (e.g. {time} in TiTiler item ids).
      const templateParams = {
        ...(newLayer.params || {}),
        ...(paramInteractions || {}),
      };
      const resolvedTiles = resolveTemplateUrlParams(tiles, templateParams);
      if (resolvedTiles !== tiles && newLayer.layerConfig?.source) {
        tiles = resolvedTiles;
        newLayer.layerConfig = {
          ...newLayer.layerConfig,
          source: {
            ...newLayer.layerConfig.source,
            tiles: [resolvedTiles],
          },
        };
      }

      const sanitizedTiles = sanitizeTemplateParams(tiles);
      if (sanitizedTiles !== tiles) {
        tiles = sanitizedTiles;
        if (newLayer.layerConfig?.source) {
          newLayer.layerConfig = {
            ...newLayer.layerConfig,
            source: {
              ...newLayer.layerConfig.source,
              tiles: [sanitizedTiles],
            },
          };
        }
      }

      // NOTE: TiTiler style defaults (colormaps, rescale, resampling) are applied
      // once at the very end of processLayers, AFTER all URL manipulations
      // (filter swaps, param appending, template resolution) are complete.
      // This prevents intermediate URL reconstruction from corrupting encoded
      // colormap JSON values.
    }

    // Resolve URL templates for GeoJSON string sources
    const sourceData = newLayer.layerConfig?.source?.data;
    if (typeof sourceData === 'string') {
      const absoluteSourceData = absolutizeRuntimeUrl(sourceData);

      // Merge global interactions as base, then layer params override
      // so layer-specific controls (e.g. Google Flood toggle) take precedence.
      const params = {
        ...(paramInteractions || {}),
        ...(newLayer.params || {}),
      };
      const resolvedSourceData = appendGeojsonParamsToUrl(
        resolveTemplateUrlParams(absoluteSourceData, params),
        params
      );

      const isModularGeojson = MODULAR_GEOJSON_PATHS.some((path) => absoluteSourceData.includes(path));

      newLayer.layerConfig = {
        ...newLayer.layerConfig,
        source: {
          ...newLayer.layerConfig.source,
          ...(resolvedSourceData !== sourceData && { data: resolvedSourceData }),
          // Enable MapBox GL client-side clustering for modular GeoJSON model layers.
          // Aggregate daily_avg (max) so cluster icon expressions can derive alert level.
          ...(isModularGeojson && {
            cluster: true,
            clusterRadius: 50,
            clusterMaxZoom: 12,
            clusterProperties: {
              daily_avg: ['max', ['get', 'daily_avg']],
            },
          }),
        },
      };
    }

    if (!tiles) {
      if (newLayer.layerConfig) {
        newLayer.layerConfig = normalizeMultimodalPointStyling(
          newLayer.layerConfig,
          '',
          {
            name: newLayer.name,
            datasetName: newLayer.datasetTitle || newLayer.datasetName || '',
            datasetId: newLayer.dataset || '',
          }
        );
      }
      return newLayer;
    }

    const legacyResult = applyLegacyTileReplacement(tiles);
    if (legacyResult.url !== tiles) {
      tiles = legacyResult.url;

      if (newLayer.layerConfig?.source) {
        newLayer.layerConfig = {
          ...newLayer.layerConfig,
          source: {
            ...newLayer.layerConfig.source,
            tiles: [tiles],
          },
        };
      }

      if (legacyResult.sourceLayer && newLayer.layerConfig?.render?.layers) {
        newLayer.layerConfig = {
          ...newLayer.layerConfig,
          render: {
            ...newLayer.layerConfig.render,
            layers: newLayer.layerConfig.render.layers.map(renderLayer => ({
              ...renderLayer,
              'source-layer': legacyResult.sourceLayer,
            })),
          },
        };
      }
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
    // WRF rainfall functions accept country_name/project_countries directly
    const isWrfRainfallLayer =
      tiles.includes('tileserv/wrf.get_total_rainfall_tiles') ||
      tiles.includes('tileserv/wrf.get_extreme_rainfall_tiles') ||
      tiles.includes('tileserv/wrf.get_daily_rainfall_tiles');

    const isAlreadyFilteredLayer =
      (isProjectFilterActive && (
        tiles.includes('tileserv/gha.multimodal_points_by_project') ||
        tiles.includes('tileserv/gha.admin_by_project') ||
        isWrfRainfallLayer
      )) ||
      (isWHCAFilterActive && (
        tiles.includes('tileserv/gha.multimodal_points_clustered_whca') ||
        tiles.includes('tileserv/gha.admin_whca') ||
        tiles.includes('tileserv/gha.admin_clipped') ||
        isWrfRainfallLayer
      )) ||
      (isAdminFilterActive && (
        tiles.includes('tileserv/gha.admin_clipped') ||
        tiles.includes('tileserv/gha.multimodal_points_by_admin') ||
        tiles.includes('tileserv/climate.inundation_history_clipped') ||
        isWrfRainfallLayer
      )) ||
      (isBasinFilterActive && tiles.includes('tileserv/gha.multimodal_points_by_basin'));

    // Add filter params when swapped OR when already on a filtered function source.
    if ((tileSourceSwapped || isAlreadyFilteredLayer) && isFilteringActive) {
      const updatedTiles = appendParamsToUrl(tiles, backendFilterParams, true);

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

    // Ensure raster tile requests (WMS or TiTiler) receive clipping scope params.
    const resolvedTiles = newLayer.layerConfig?.source?.tiles?.[0] || tiles || originalTiles;
    if (isRasterTileUrl(resolvedTiles) && isFilteringActive) {
      const rasterParams = {
        country_name: paramInteractions?.country_name || '',
        region_name: paramInteractions?.region_name || '',
        district_name: paramInteractions?.district_name || '',
        project_countries: paramInteractions?.project_countries || '',
        scope: resolvedScope,
      };

      const updatedRasterTiles = appendParamsToUrl(resolvedTiles, rasterParams, true);

      newLayer.layerConfig = {
        ...newLayer.layerConfig,
        source: {
          ...newLayer.layerConfig.source,
          tiles: [updatedRasterTiles],
        },
      };
    }

    if (newLayer.layerConfig) {
      const finalTiles = newLayer.layerConfig?.source?.tiles?.[0] || tiles || originalTiles;

      // Keep vector source-layer aligned with the active pg_tileserv source.
      // Shared URL states can preserve old source-layer values while the tile URL
      // already points to a filtered function/table, which makes layers disappear.
      if (
        newLayer.layerConfig?.source?.type === 'vector' &&
        Array.isArray(newLayer.layerConfig?.render?.layers)
      ) {
        const inferredSourceLayer = extractTileservSourceLayer(finalTiles);
        if (inferredSourceLayer) {
          newLayer.layerConfig = {
            ...newLayer.layerConfig,
            render: {
              ...newLayer.layerConfig.render,
              layers: newLayer.layerConfig.render.layers.map((renderLayer) => ({
                ...renderLayer,
                'source-layer': inferredSourceLayer,
              })),
            },
          };
        }
      }

      newLayer.layerConfig = applyAdminBoundaryZoomBand(newLayer.layerConfig, finalTiles);
      newLayer.layerConfig = normalizeMultimodalPointStyling(
        newLayer.layerConfig,
        finalTiles,
        {
          name: newLayer.name,
          datasetName: newLayer.datasetTitle || newLayer.datasetName || '',
          datasetId: newLayer.dataset || '',
        }
      );

    }

    return newLayer;
  });
};
