import { POLITICAL_BOUNDARIES_DATASET } from "@/data/datasets";
import { POLITICAL_BOUNDARIES } from "@/data/layers";
import { getDefaultParamInteractions } from "@/utils/params";

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
    filterInteractions: {
      selectedCountry: null,
      selectedSubBorder: null,
      selectedLowerBorder: null,
    },
    paramInteractions: getDefaultParamInteractions(),
    initialParamInteractions: null, // Store CMS predefined params
    initialBbox: null, // Store initial CMS boundary bbox
    boundaryData: {},
    cmsScopes: [], // CMS-defined project scopes (fetched from /api/v1/cms/scopes)
    defaultScope: 'all', // CMS default scope key
  },
  settings: {
    center: {
      lat: 5.73,
      lng: 36.84,
    },
    zoom: 4,
    bearing: 0,
    pitch: 0,
    minZoom: 2,
    maxZoom: 19,
    basemap: {
      value: "",
    },
    labels: true,
    roads: false,
    bbox: [],
    canBound: true,
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
        // Preserve layer config for custom layers (like multimodal cluster)
        // This allows getInteractions to use embedded interactionConfig
        ...(layer?.interactionConfig ? { layer } : {}),
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

const setFilterInteractions = (state, { payload }) => ({
  ...state,
  data: {
    ...state.data,
    filterInteractions: {
      ...state.data.filterInteractions,
      ...payload,
    },
  },
});

const clearFilterInteractions = (state) => ({
  ...state,
  data: {
    ...state.data,
    filterInteractions: {
      selectedCountry: null,
      selectedSubBorder: null,
      selectedLowerBorder: null,
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

const setInitialBbox = (state, { payload }) => ({
  ...state,
  data: {
    ...state.data,
    initialBbox: payload,
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

const setCmsScopes = (state, { payload }) => ({
  ...state,
  data: {
    ...state.data,
    cmsScopes: payload.scopes || [],
    defaultScope: payload.default_scope || 'all',
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
  [actions.setFilterInteractions]: setFilterInteractions,
  [actions.clearFilterInteractions]: clearFilterInteractions,
  [actions.setParamInteractions]: setParamInteractions,
  [actions.clearParamInteractions]: clearParamInteractions,
  [actions.setInitialParamInteractions]: setInitialParamInteractions,
  [actions.setInitialBbox]: setInitialBbox,
  [actions.setBoundaryData]: setBoundaryData,
  [actions.clearBoundaryData]: clearBoundaryData,
  [actions.setCmsScopes]: setCmsScopes,
};
