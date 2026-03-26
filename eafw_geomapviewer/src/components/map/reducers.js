import { POLITICAL_BOUNDARIES_DATASET } from "@/data/datasets";
import { POLITICAL_BOUNDARIES } from "@/data/layers";
import { getDefaultParamInteractions } from "@/utils/params";

import {DEFAULT_CENTER_LAT, DEFAULT_CENTER_LNG, DEFAULT_ZOOM_LEVEL, DEFAULT_MIN_ZOOM} from "@/utils/constants"

import * as actions from "./actions";

export const initialState = {
  loading: false,
  data: {
    interactions: {
      latlng: {},
      interactions: {},
      selected: "",
    },
    hoverInteraction: {
      feature: null,
      latlng: {},
    },
    paramInteractions: getDefaultParamInteractions(),
    initialParamInteractions: null,
    initialBbox: null,
    boundaryData: {},
  },
  settings: {
    center: {
      lat: DEFAULT_CENTER_LAT,
      lng: DEFAULT_CENTER_LNG,
    },
    zoom: DEFAULT_ZOOM_LEVEL,
    bearing: 0,
    pitch: 0,
    minZoom: DEFAULT_MIN_ZOOM,
    maxZoom: 19,
    basemap: {
      value: "",
    },
    labels: true,
    roads: false,
    bbox: [],
    canBound: false,
    drawing: false,
    printing: false,
    comparing: false,
    activeCompareSide: null,
    drawingMode: "draw_polygon",
    mapBounds: [],
    datasets: [
      // admin boundaries
      {
        dataset: POLITICAL_BOUNDARIES_DATASET,
        layers: [POLITICAL_BOUNDARIES],
        opacity: 1,
        visibility: true,
      },
    ],
  },
};

const setMapLoading = (state, { payload }) => ({
  ...state,
  loading: payload,
});

const setMapSettings = (state, { payload }) => ({
  ...state,
  settings: {
    ...state.settings,
    ...payload,
  },
});

const setMapBasemap = (state, { payload }) => ({
  ...state,
  settings: {
    ...state.settings,
    basemap: {
      ...state.settings.basemap,
      ...payload,
    },
  },
});

const setMapInteractions = (state, { payload }) => {
  const interactions = payload?.features?.reduce(
    (obj, { layer, id, geometry, ...data }) => ({
      ...obj,
      [layer?.source || id]: {
        id: layer?.source || id,
        geometry,
        data,
      },
    }),
    {}
  );

  return {
    ...state,
    data: {
      ...state.data,
      interactions: {
        ...state.data.interactions,
        interactions,
        latlng: {
          lat: payload.lngLat[1],
          lng: payload.lngLat[0],
        },
      },
    },
  };
};

const setMapInteractionSelected = (state, { payload }) => ({
  ...state,
  data: {
    ...state.data,
    interactions: {
      ...state.data.interactions,
      selected: payload,
    },
  },
});

const clearMapInteractions = (state) => ({
  ...state,
  data: {
    ...state.data,
    interactions: {
      interactions: {},
      latlng: null,
      selected: "",
    },
  },
});

const setMapHoverInteraction = (state, { payload }) => {
  const hoverFeature = payload && {
    id: payload.feature.id,
    data: payload.feature.properties,
    geometry: payload.feature.geometry,
    source: payload.feature.source,
    layer: payload.feature.layer,
  };

  return {
    ...state,
    data: {
      ...state.data,
      hoverInteraction: {
        feature: hoverFeature,
        latlng: {
          lat: payload.lngLat[1],
          lng: payload.lngLat[0],
        },
      },
    },
  };
};

const clearMapHoverInteraction = (state) => ({
  ...state,
  data: {
    ...state.data,
    hoverInteraction: {
      feature: null,
      latlng: null,
    },
  },
});

const setParamInteractions = (state, { payload }) => ({
  ...state,
  data: {
    ...state.data,
    paramInteractions: {
      ...state.data.paramInteractions,
      ...payload,
    },
  },
});

const clearParamInteractions = (state) => ({
  ...state,
  data: {
    ...state.data,
    // Restore initial CMS params if available, otherwise use defaults
    paramInteractions: state.data.initialParamInteractions || getDefaultParamInteractions(),
  },
});

const setInitialParamInteractions = (state, { payload }) => ({
  ...state,
  data: {
    ...state.data,
    initialParamInteractions: payload,
  },
});

const setBoundaryData = (state, { payload }) => {
  const { key, data } = payload;
  return {
    ...state,
    data: {
      ...state.data,
      boundaryData: {
        ...state.data.boundaryData,
        [key]: data,
      },
    },
  };
};

const clearBoundaryData = (state) => ({
  ...state,
  data: {
    ...state.data,
    boundaryData: {},
  },
});

const setInitialBbox = (state, { payload }) => ({
  ...state,
  data: {
    ...state.data,
    initialBbox: payload,
  },
});

export default {
  [actions.setMapBasemap]: setMapBasemap,
  [actions.setMapLoading]: setMapLoading,
  [actions.setMapSettings]: setMapSettings,
  [actions.setMapInteractions]: setMapInteractions,
  [actions.setMapInteractionSelected]: setMapInteractionSelected,
  [actions.clearMapInteractions]: clearMapInteractions,
  [actions.setMapHoverInteraction]: setMapHoverInteraction,
  [actions.clearMapHoverInteraction]: clearMapHoverInteraction,
  [actions.setParamInteractions]: setParamInteractions,
  [actions.clearParamInteractions]: clearParamInteractions,
  [actions.setInitialParamInteractions]: setInitialParamInteractions,
  [actions.setBoundaryData]: setBoundaryData,
  [actions.clearBoundaryData]: clearBoundaryData,
  [actions.setInitialBbox]: setInitialBbox,
};
