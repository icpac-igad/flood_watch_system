import { createAction } from "@/redux/actions";

export const setMapLoading = createAction("setMapLoading");
export const setMapSettings = createAction("setMapSettings");
export const setMapInteractions = createAction("setMapInteractions");
export const setMapInteractionSelected = createAction(
  "setMapInteractionSelected"
);

export const setMapHoverInteraction = createAction("setMapHoverInteraction");
export const clearMapHoverInteraction = createAction(
  "clearMapHoverInteraction"
);

export const clearMapInteractions = createAction("clearMapInteractions");

export const setBasemapFromLegend = createAction("setBasemapFromLegend");

export const setMapBasemap = createAction("setMapBasemap");

export const setFilterInteractions = createAction("setFilterInteractions");
export const clearFilterInteractions = createAction("clearFilterInteractions");

export const setParamInteractions = createAction("setParamInteractions");
export const clearParamInteractions = createAction("clearParamInteractions");
export const setInitialParamInteractions = createAction("setInitialParamInteractions");
export const setInitialBbox = createAction("setInitialBbox");

export const setBoundaryData = createAction("setBoundaryData");
export const clearBoundaryData = createAction("clearBoundaryData");