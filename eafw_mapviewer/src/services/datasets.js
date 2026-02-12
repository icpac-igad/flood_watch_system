import request from "@/utils/request";

import { CMS_API } from "@/utils/constants";

const DATASETS_ENDPOINT = `${CMS_API}/datasets/`;
const MAPVIEWER_CONFIG_ENDPOINT = `${CMS_API}/mapviewer-config`;

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
  return datasets.map((dataset) => configById.get(dataset.id) || dataset);
};

export const getApiDatasets = async () => {
  const [datasetsResult, configResult] = await Promise.allSettled([
    request.get(DATASETS_ENDPOINT),
    request.get(MAPVIEWER_CONFIG_ENDPOINT),
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
