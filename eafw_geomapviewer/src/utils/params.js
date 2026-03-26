const DEFAULT_PARAMS = {
  unit_id: '',
  admin_level: '0',
  project_name: 'Admin',
  border_level: '0',
  MASK_AREA: 'Admin',
  MASK_UNIT_ID: '',
  MASK_ADMIN_LEVEL: '0',
};

export const getDefaultParamInteractions = () => ({
  ...DEFAULT_PARAMS,
});

const buildUnifiedParams = (boundaryParams = {}) => {
  const unitId = boundaryParams?.unit_id || '';
  const projectName = boundaryParams?.project_name || 'Admin';

  return {
    unit_id: unitId,
    admin_level: boundaryParams?.admin_level || '0',
    project_name: projectName,
    border_level: boundaryParams?.border_level || '0',
    MASK_AREA: projectName,
    MASK_UNIT_ID: unitId,
    MASK_ADMIN_LEVEL: boundaryParams?.admin_level || '0',
  };
};

export const buildParamInteractionsFromBoundary = (boundary, adminLevel, borderLevel = '0', projectName = 'Admin') => {
  return buildUnifiedParams({
    unit_id: boundary?.code || '',
    admin_level: adminLevel,
    project_name: projectName,
    border_level: borderLevel,
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

export const getBorderLevelFromDataset = (dataset) => {
  const layer = dataset?.layers?.[0];
  const tiles = layer?.layerConfig?.source?.tiles?.[0];
  if (!tiles) return null;

  const params = extractParamsFromUrl(tiles);
  if (params?.border_level != null) return Number(params.border_level);

  // If the dataset is a boundary type but has no explicit border_level param in
  // its tile URL, treat it as the country-level (0) boundary. Level 1 and 2
  // boundary datasets always have ?border_level=1/2 baked into their tile URL.
  if (dataset?.isBoundary || layer?.isBoundary) return 0;

  return null;
};

export const extractParamsFromLayers = (layers) => {
  if (!layers || !layers.length) return null;

  for (const layer of layers) {
    const tiles = layer.layerConfig?.source?.tiles?.[0];
    if (!tiles) continue;

    const extractedParams = extractParamsFromUrl(tiles);

    // Only return params if unit_id is set — empty unit_id means no predefined
    // boundary so all filter selectors should remain visible.
    if (extractedParams && Object.keys(extractedParams).length > 0) {
      const unitId = extractedParams.unit_id || extractedParams.MASK_UNIT_ID || '';

      if (unitId) {
        return buildUnifiedParams({
          unit_id: unitId,
          admin_level: extractedParams.admin_level || extractedParams.MASK_ADMIN_LEVEL || '0',
          project_name: extractedParams.project_name || extractedParams.MASK_AREA || 'Admin',
          border_level: extractedParams.border_level || '0',
        });
      }
    }
  }

  return null;
};
