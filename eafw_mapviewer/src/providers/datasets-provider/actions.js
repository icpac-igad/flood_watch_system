import { createAction, createThunkAction } from "@/redux/actions";

import { setMapSettings, setParamInteractions, setInitialParamInteractions, setInitialBbox } from "@/components/map/actions";
import { getApiDatasets } from "@/services/datasets";
import { extractParamsFromLayers } from "@/utils/params";
import { fetchAdminBoundaries } from "@/utils/boundary-utils";

import { getTimeseriesConfig } from "./utils";

export const setDatasetsLoading = createAction("setDatasetsLoading");
export const setDatasets = createAction("setDatasets");
export const updateDatasets = createAction("updateDatasets");
export const removeDataset = createAction("removeDataset");

export const setLayerUpdatingStatus = createAction("setLayerUpdatingStatus");
export const setLayerLoadingStatus = createAction("setLayerLoadingStatus");
export const setGeojsonData = createAction("setGeojsonData");
export const setTimestamps = createAction("setTimestamps");
export const setDatasetParams = createAction("setDatasetParams");

export const fetchDatasets = createThunkAction(
  "fetchDatasets",
  (activeDatasets) => (dispatch, getState) => {
    dispatch(setDatasetsLoading({ loading: true, error: false }));

    const currentActiveDatasets = [...activeDatasets];

    getApiDatasets()
      .then((apiDatasets) => {
        const initialVisibleDatasets = apiDatasets.filter(
          (d) => d.initialVisible
        );
        // Only force Admin Level 0 (country borders) on by default.
        // Level 1 and 2 are available but users toggle them manually.
        const admin0Dataset = apiDatasets.find((d) =>
          /^admin level 0 boundary$/i.test(d?.name || "")
        );
        const defaultVisibleDatasets = [...initialVisibleDatasets];
        if (admin0Dataset && !defaultVisibleDatasets.some((d) => d.id === admin0Dataset.id)) {
          defaultVisibleDatasets.push(admin0Dataset);
        }

        const datasetsWithAnalysis = apiDatasets.reduce(
          (allDatasets, dataset) => {
            const layers = dataset.layers.reduce((dLayers, layer) => {
              if (
                layer.analysisConfig &&
                (layer.analysisConfig.pointTimeseriesAnalysis ||
                  layer.analysisConfig.areaTimeseriesAnalysis)
              ) {
                // mark as has analysis
                layer.hasTimeseriesAnalysis = true;

                if (layer.layerType === "raster_file") {
                  if (layer.analysisConfig.pointTimeseriesAnalysis) {
                    layer.analysisConfig.pointTimeseriesAnalysis.config =
                      getTimeseriesConfig(layer, "point");
                  }

                  if (layer.analysisConfig.areaTimeseriesAnalysis) {
                    layer.analysisConfig.areaTimeseriesAnalysis.config =
                      getTimeseriesConfig(layer, "area");
                  }
                }
              }
              dLayers.push(layer);
              return dLayers;
            }, []);

            dataset.layers = layers;

            allDatasets.push(dataset);

            return allDatasets;
          },
          []
        );

        const { query } = getState().location;

        const hasDatasetsInUrlState =
          query &&
          query.map &&
          query.map.datasets &&
          !!query.map.datasets.length;

        // Extract parameters from initialVisible datasets layers
        let extractedParams = null;
        if (!!initialVisibleDatasets.length) {
          for (const dataset of initialVisibleDatasets) {
            extractedParams = extractParamsFromLayers(dataset.layers);
            if (extractedParams) break;
          }
        }

        // If params found, set them in state and fit map to bounds
        if (extractedParams) {
          // Store as initial params so they can be restored when filters are cleared
          dispatch(setInitialParamInteractions(extractedParams));

          // Get current state to check if filters were restored from URL
          const state = getState();
          const filterInteractions = state.map?.data?.filterInteractions;
          const hasRestoredFilters = filterInteractions?.selectedCountry ||
                                      filterInteractions?.selectedSubBorder ||
                                      filterInteractions?.selectedLowerBorder;

          // Only apply CMS params if there are no restored filters from URL
          if (!hasRestoredFilters) {
            dispatch(setParamInteractions(extractedParams));

            // Fetch boundary data to get bbox for initial fitting
            if (extractedParams.unit_id) {
              fetchAdminBoundaries(null, '', true)
                .then(boundaryJson => {
                  if (boundaryJson && boundaryJson.length > 0) {
                    // Find the matching country by code
                    const matchingCountry = boundaryJson.find(country => country.code === extractedParams.unit_id);

                    if (matchingCountry && matchingCountry.bbox) {
                      const bbox = matchingCountry.bbox;
                      const formattedBbox = [bbox.left, bbox.bottom, bbox.right, bbox.top];

                      // Store initial bbox for restoring when filters are cleared
                      dispatch(setInitialBbox(formattedBbox));

                      dispatch(setMapSettings({
                        canBound: true,
                        bbox: [...formattedBbox]
                      }));
                    }
                  }
                })
                .catch(error => {
                  console.error('Error fetching boundary for initial bounds:', error);
                });
            }
          }
        }

        // set default visible datasets when no datasets in map url state
        if (!hasDatasetsInUrlState && !!defaultVisibleDatasets.length) {
          const newDatasets = [...currentActiveDatasets];
          defaultVisibleDatasets.forEach((dataset) => {
            if (newDatasets.some((d) => d.dataset === dataset.id)) return;
            newDatasets.push({
              dataset: dataset.id,
              layers: dataset.layers.map((l) => l.id),
              opacity: 1,
              visibility: true,
            });
          });

          // set new active Datasets
          dispatch(setMapSettings({ datasets: newDatasets }));
        }

        // Backward compatibility for shared URLs: ensure admin0 boundary is present.
        if (admin0Dataset) {
          const currentMapDatasets = getState().map?.settings?.datasets || [];
          const hasAdmin0 = currentMapDatasets.some(
            (active) => active.dataset === admin0Dataset.id
          );

          if (!hasAdmin0) {
            dispatch(setMapSettings({
              datasets: [
                ...currentMapDatasets,
                {
                  dataset: admin0Dataset.id,
                  layers: admin0Dataset.layers.map((l) => l.id),
                  opacity: 1,
                  visibility: true,
                },
              ],
            }));
          }
        }

        dispatch(updateDatasets(datasetsWithAnalysis));
        dispatch(setDatasetsLoading({ loading: false, error: false }));
      })
      .catch((err) => {
        dispatch(setDatasetsLoading({ loading: false, error: true }));
      });
  }
);
