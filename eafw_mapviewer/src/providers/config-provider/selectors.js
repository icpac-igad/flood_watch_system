import { getBasemap } from "@/components/map/selectors";
import { createStructuredSelector } from "reselect";

export const getApiBaseMaps = (state) => state.config && state.config.basemaps;

export const getMultimodalClusterConfig = (state) =>
  state.config && state.config.multimodalClusterConfig;

export const getConfigProps = createStructuredSelector({
  basemaps: getApiBaseMaps,
  basemap: getBasemap,
});
