
export const PARAMS_CONFIG = {
  defaultParams: {
    unit_id: '',
    admin_level: '0',
    project_name: 'Admin',
    border_level: '0',
    MASK_AREA: 'Admin',
    MASK_UNIT_ID: '',
    MASK_ADMIN_LEVEL: '0',
    // FloodWatch: Admin boundary names for spatial filtering
    country_name: '',
    region_name: '',
    district_name: '',
    admin_filter: false,
    // FloodWatch: Scope/project filtering
    scope: 'all',
    whca_filter: false,
    project_filter: false,
    project_countries: '',
    basin_filter: false,
    basin_id: '',
    // Google Flood defaults: keep extended coverage off unless user opts in.
    confidence: 'high',
    extended_coverage: false,
  }
};

export const getDefaultParamInteractions = () => ({
  ...PARAMS_CONFIG.defaultParams
});

export const buildUnifiedParams = (boundaryParams = {}) => ({
  unit_id: boundaryParams?.unit_id || '',
  admin_level: boundaryParams?.admin_level || '0',
  project_name: boundaryParams?.project_name || 'Admin',
  border_level: boundaryParams?.border_level || '0',
  MASK_AREA: boundaryParams?.project_name || 'Admin',
  MASK_UNIT_ID: boundaryParams?.unit_id || '',
  MASK_ADMIN_LEVEL: boundaryParams?.admin_level || '0',
  // FloodWatch: Admin boundary names for spatial filtering
  country_name: boundaryParams?.country_name || '',
  region_name: boundaryParams?.region_name || '',
  district_name: boundaryParams?.district_name || '',
  admin_filter: boundaryParams?.admin_filter || false
});

export const buildParamInteractionsFromBoundary = (boundary, adminLevel, borderLevel = '0', projectName = 'Admin', parentBoundaries = {}) => {
  // FloodWatch: Include boundary names for spatial data clipping
  return buildUnifiedParams({
    unit_id: boundary?.code || '',
    admin_level: adminLevel,
    project_name: projectName,
    border_level: borderLevel,
    // Pass boundary names for backend spatial filtering
    country_name: parentBoundaries?.country_name || (adminLevel === '0' ? boundary?.name : ''),
    region_name: parentBoundaries?.region_name || (adminLevel === '1' ? boundary?.name : ''),
    district_name: adminLevel === '2' ? boundary?.name : '',
    admin_filter: !!(boundary?.code)
  });
};

export const extractParamsFromUrl = (url) => {
  if (!url) return null;

  try {
    // Check if URL has query parameters
    const queryIndex = url.indexOf('?');
    if (queryIndex === -1) return null;

    const queryString = url.substring(queryIndex + 1);
    const params = {};

    const searchParams = new URLSearchParams(queryString);
    searchParams.forEach((value, key) => {
      params[key] = value;
    });

    return Object.keys(params).length > 0 ? params : null;
  } catch (e) {
    return null;
  }
};

export const extractParamsFromLayers = (layers) => {
  if (!layers || !layers.length) return null;

  for (const layer of layers) {
    const tiles = layer.layerConfig?.source?.tiles?.[0];
    if (!tiles) continue;

    const extractedParams = extractParamsFromUrl(tiles);

    // Only consider params if they contain at least one boundary-specific param
    if (extractedParams && Object.keys(extractedParams).length > 0) {
      const hasBoundaryParams = extractedParams.unit_id ||
                                extractedParams.MASK_UNIT_ID ||
                                extractedParams.admin_level ||
                                extractedParams.MASK_ADMIN_LEVEL ||
                                extractedParams.project_name ||
                                extractedParams.MASK_AREA ||
                                extractedParams.border_level;

      if (hasBoundaryParams) {
        // Return unified params 
        return buildUnifiedParams({
          unit_id: extractedParams.unit_id || extractedParams.MASK_UNIT_ID || '',
          admin_level: extractedParams.admin_level || extractedParams.MASK_ADMIN_LEVEL || '0',
          project_name: extractedParams.project_name || extractedParams.MASK_AREA || 'Admin',
          border_level: extractedParams.border_level || '0'
        });
      }
    }
  }

  return null;
};
