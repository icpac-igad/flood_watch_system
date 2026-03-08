import request from "@/utils/request";

import { FASTAPI_API } from "@/utils/constants";

const DATASETS_ENDPOINT = `${FASTAPI_API}/datasets/mapviewer/`;
const MAPVIEWER_CONFIG_ENDPOINT = `${FASTAPI_API}/mapviewer-config`;

const isVectorTileservLayer = (layer = {}) => {
  const source = layer?.layerConfig?.source || {};
  const sourceType = String(source.type || layer?.layerConfig?.type || "").toLowerCase();
  const tileUrls = Array.isArray(source.tiles) ? source.tiles : [];
  return (
    sourceType === "vector" &&
    tileUrls.some((tileUrl) => /\/(?:pg\/)?tileserv\//i.test(String(tileUrl || "")))
  );
};

const mergeDatasetWithConfig = (dataset, configDataset) => {
  if (!configDataset) return dataset;

  const mergedDataset = { ...configDataset };
  const datasetLayers = Array.isArray(dataset?.layers) ? dataset.layers : [];
  const configLayers = Array.isArray(configDataset?.layers) ? configDataset.layers : [];

  if (!datasetLayers.length || !configLayers.length) {
    return mergedDataset;
  }

  const datasetLayersById = new Map(
    datasetLayers
      .filter((layer) => layer?.id)
      .map((layer) => [layer.id, layer])
  );

  mergedDataset.layers = configLayers.map((configLayer) => {
    const layerId = String(configLayer?.id || "");
    const datasetLayer = datasetLayersById.get(layerId);
    if (!datasetLayer) return configLayer;

    const shouldPreferDatasetVector =
      isVectorTileservLayer(datasetLayer) && !isVectorTileservLayer(configLayer);

    if (!shouldPreferDatasetVector) return configLayer;

    return {
      ...configLayer,
      layerType: datasetLayer.layerType || configLayer.layerType,
      layerConfig: datasetLayer.layerConfig,
      params: datasetLayer.params || configLayer.params,
      provider: datasetLayer.provider || configLayer.provider,
    };
  });

  return mergedDataset;
};

const mergeDatasetsWithConfig = (datasets = [], configDatasets = []) => {
  if (!Array.isArray(datasets) || !datasets.length) return [];
  if (!Array.isArray(configDatasets) || !configDatasets.length) return datasets;

  const configById = new Map(
    configDatasets
      .filter((dataset) => dataset && dataset.id)
      .map((dataset) => [dataset.id, dataset])
  );

  // Keep the same dataset set/order from /datasets, while borrowing richer
  // layer configs (params/selector config/interaction overrides) from
  // /mapviewer-config when available.
  return datasets.map((dataset) =>
    mergeDatasetWithConfig(dataset, configById.get(dataset.id))
  );
};

export const getApiDatasets = async () => {
  const cacheBust = Date.now();
  const [datasetsResult, configResult] = await Promise.allSettled([
    request.get(DATASETS_ENDPOINT, {
      params: { _ts: cacheBust },
      headers: { "Cache-Control": "no-cache" },
    }),
    request.get(MAPVIEWER_CONFIG_ENDPOINT, {
      params: { _ts: cacheBust },
      headers: { "Cache-Control": "no-cache" },
    }),
  ]);

  if (datasetsResult.status !== "fulfilled") {
    throw datasetsResult.reason;
  }

  const datasets = datasetsResult.value?.data || [];
  const configDatasets =
    configResult.status === "fulfilled"
      ? configResult.value?.data?.datasets || []
      : [];

  return mergeDatasetsWithConfig(datasets, configDatasets);
};
