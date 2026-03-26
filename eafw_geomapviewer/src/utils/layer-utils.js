const appendParamsToUrl = (url, params) => {
  const [baseUrl, existingQuery = ''] = url.split('?');

  const existingParams = {};
  if (existingQuery) {
    const searchParams = new URLSearchParams(existingQuery);
    searchParams.forEach((value, key) => {
      existingParams[key] = value;
    });
  }

  // Merge with new params.
  // - border_level: preserve the URL's value if > 0 
  Object.entries(params).forEach(([key, value]) => {
    const preserve = key === 'border_level' && existingParams.hasOwnProperty(key) && Number(existingParams[key]) > 0;
    if (!preserve && value !== undefined && (value !== '' || key.startsWith('MASK_'))) {
      existingParams[key] = `{${key}}`;
    }
  });

  const queryParts = Object.entries(existingParams).map(([key, value]) => `${key}=${value}`);
  const finalQuery = queryParts.join('&');

  return finalQuery ? `${baseUrl}?${finalQuery}` : baseUrl;
};

export const processLayers = (layers, paramInteractions, mapSide) => {
  const filteredLayers = mapSide
    ? layers.filter(l => (l.mapSide && l.mapSide === mapSide) || l.isBoundary)
    : layers;

  // Admin filters use unit_id, while project filters use scope/project_countries.
  const hasParamInteractions =
    !!paramInteractions?.unit_id ||
    !!paramInteractions?.MASK_UNIT_ID ||
    paramInteractions?.scope === 'whca' ||
    (
      !!paramInteractions?.project_countries &&
      paramInteractions.project_countries !== '__none__'
    );

  return filteredLayers.map(layer => {
    const tiles = layer.layerConfig?.source?.tiles?.[0] || '';
    const newLayer = { ...layer };
    if (!tiles) {
      return newLayer;
    }

    const layerParams = layer.params || {};
    let combinedParams = { ...layerParams };

    if (layer.isBoundary) {
      // Boundary layers: append scope directly (not as template placeholder)
      if (hasParamInteractions && paramInteractions?.scope) {
        const sep = tiles.indexOf('?') === -1 ? '?' : '&';
        const scopedTiles = tiles + sep + 'scope=' + paramInteractions.scope;
        newLayer.layerConfig = {
          ...newLayer.layerConfig,
          source: {
            ...newLayer.layerConfig.source,
            tiles: [scopedTiles]
          }
        };
      }
      return newLayer;
    }

    if (hasParamInteractions && paramInteractions) {
      combinedParams = { ...layerParams, ...paramInteractions };
    }

    // Apply combined params to URL if there are any
    if (Object.keys(combinedParams).length > 0) {
      const updatedTiles = appendParamsToUrl(tiles, combinedParams);

      newLayer.params = combinedParams;
      newLayer.layerConfig = {
        ...newLayer.layerConfig,
        source: {
          ...newLayer.layerConfig.source,
          tiles: [updatedTiles]
        }
      };
    }

    return newLayer;
  });
};
