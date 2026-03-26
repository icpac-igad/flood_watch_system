import { createAction, createThunkAction } from "@/redux/actions";

import { setMapSettings, setParamInteractions, setInitialParamInteractions } from "@/components/map/actions";
import { getApiDatasets } from "@/services/datasets";
import { extractParamsFromLayers } from "@/utils/params";
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

        // Mark boundary datasets so they get higher z-index and stay on top.
        // Config stores categories as "sections" with { category: title, id }.
        const { sections } = getState().config || {};
        const boundaryCategoryIds = (sections || [])
          .filter((s) => /boundary/i.test(s.category || ''))
          .map((s) => s.id);
        datasetsWithAnalysis.forEach((d) => {
          if (boundaryCategoryIds.includes(d.category)) {
            d.isBoundary = true;
            (d.layers || []).forEach((l) => { l.isBoundary = true; });
          }
        });

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

        // If params found, apply them and fit map to the initial boundary bbox
        if (extractedParams) {
          dispatch(setInitialParamInteractions(extractedParams));
          dispatch(setParamInteractions(extractedParams));
        }

        // set default visible datasets when no datasets in map url state
        if (!hasDatasetsInUrlState && !!initialVisibleDatasets.length) {
          const newDatasets = [...currentActiveDatasets].concat(
            initialVisibleDatasets.reduce((all, dataset) => {
              const config = {
                dataset: dataset.id,
                layers: dataset.layers.map((l) => l.id),
                opacity: 1,
                visibility: true,
              };
              all.push(config);
              return all;
            }, [])
          );

          // set new active Datasets
          dispatch(setMapSettings({ datasets: newDatasets }));
        }

        dispatch(updateDatasets(datasetsWithAnalysis));
        dispatch(setDatasetsLoading({ loading: false, error: false }));
      })
      .catch((err) => {
        dispatch(setDatasetsLoading({ loading: false, error: true }));
      });
  }
);
