import { createContext, useContext, useReducer, useCallback } from 'react';

// Initial state structure
const initialState = {
  // Map layers visibility
  layers: {
    monitoringStations: true,
    geoFSM: false,
    mikeHydro: false,
    hype: false,
    ensemble: false,
    selectedOverlays: new Set(),
    selectedBoundaryLayers: new Set(['admin_level_1']),
  },
  
  // Date selection
  dates: {
    selectedDates: {
      global: null,
      inundation: null,
      impact: null,
    },
    availableDates: [],
    geosfmAvailableDates: [],
    datesLoaded: false,
    geosfmDatesLoaded: false,
  },
  
  // Filters
  filters: {
    selectedCountry: null,
    availableCountries: [],
  },
  
  // Selection state
  selection: {
    selectedStation: null,
    chartType: 'discharge',
    geoFSMDataType: 'riverdepth',
    selectedSeries: 'both',
    selectedYear: new Date().getFullYear(),
  },
  
  // Data
  data: {
    monitoringData: null,
    geoFSMData: null,
    timeSeriesData: [],
    geoFSMTimeSeriesData: [],
    adminBoundariesData: null,
    admin2BoundariesData: null,
    lakesData: null,
    riversData: null,
  },
  
  // UI state
  ui: {
    showChart: false,
    showRightPanel: false,
    showMetadataModal: false,
    currentMetadata: null,
    showFallbackNotification: false,
    fallbackMessage: '',
    activeLegend: null,
    activeOverlays: new Set(),
    isSidebarActive: true,
  },
  
  // Loading states
  loading: {
    isLayersLoading: false,
    isLoadingData: false,
    geoFSMLoading: false,
  },
};

// Action types
export const ACTIONS = {
  // Layer actions
  TOGGLE_LAYER: 'TOGGLE_LAYER',
  SET_OVERLAY_LAYERS: 'SET_OVERLAY_LAYERS',
  SET_BOUNDARY_LAYERS: 'SET_BOUNDARY_LAYERS',
  
  // Date actions
  SET_SELECTED_DATE: 'SET_SELECTED_DATE',
  SET_AVAILABLE_DATES: 'SET_AVAILABLE_DATES',
  SET_GEOSFM_DATES: 'SET_GEOSFM_DATES',
  
  // Filter actions
  SET_SELECTED_COUNTRY: 'SET_SELECTED_COUNTRY',
  SET_AVAILABLE_COUNTRIES: 'SET_AVAILABLE_COUNTRIES',
  
  // Selection actions
  SET_SELECTED_STATION: 'SET_SELECTED_STATION',
  SET_CHART_TYPE: 'SET_CHART_TYPE',
  SET_GEOSFM_DATA_TYPE: 'SET_GEOSFM_DATA_TYPE',
  SET_SELECTED_SERIES: 'SET_SELECTED_SERIES',
  SET_SELECTED_YEAR: 'SET_SELECTED_YEAR',
  
  // Data actions
  SET_MONITORING_DATA: 'SET_MONITORING_DATA',
  SET_GEOSFM_DATA: 'SET_GEOSFM_DATA',
  SET_TIME_SERIES_DATA: 'SET_TIME_SERIES_DATA',
  SET_GEOSFM_TIME_SERIES_DATA: 'SET_GEOSFM_TIME_SERIES_DATA',
  SET_ADMIN_BOUNDARIES: 'SET_ADMIN_BOUNDARIES',
  SET_ADMIN2_BOUNDARIES: 'SET_ADMIN2_BOUNDARIES',
  SET_LAKES_DATA: 'SET_LAKES_DATA',
  SET_RIVERS_DATA: 'SET_RIVERS_DATA',
  
  // UI actions
  TOGGLE_CHART: 'TOGGLE_CHART',
  TOGGLE_RIGHT_PANEL: 'TOGGLE_RIGHT_PANEL',
  TOGGLE_SIDEBAR: 'TOGGLE_SIDEBAR',
  SET_METADATA_MODAL: 'SET_METADATA_MODAL',
  SET_FALLBACK_NOTIFICATION: 'SET_FALLBACK_NOTIFICATION',
  SET_ACTIVE_LEGEND: 'SET_ACTIVE_LEGEND',
  SET_ACTIVE_OVERLAYS: 'SET_ACTIVE_OVERLAYS',
  
  // Loading actions
  SET_LAYERS_LOADING: 'SET_LAYERS_LOADING',
  SET_DATA_LOADING: 'SET_DATA_LOADING',
  SET_GEOSFM_LOADING: 'SET_GEOSFM_LOADING',
};

// Reducer function
function mapViewerReducer(state, action) {
  switch (action.type) {
    // Layer actions
    case ACTIONS.TOGGLE_LAYER:
      return {
        ...state,
        layers: {
          ...state.layers,
          [action.payload.layer]: action.payload.value,
        },
      };
    
    case ACTIONS.SET_OVERLAY_LAYERS:
      return {
        ...state,
        layers: {
          ...state.layers,
          selectedOverlays: action.payload,
        },
      };
    
    case ACTIONS.SET_BOUNDARY_LAYERS:
      return {
        ...state,
        layers: {
          ...state.layers,
          selectedBoundaryLayers: action.payload,
        },
      };
    
    // Date actions
    case ACTIONS.SET_SELECTED_DATE:
      return {
        ...state,
        dates: {
          ...state.dates,
          selectedDates: {
            ...state.dates.selectedDates,
            [action.payload.type]: action.payload.date,
          },
        },
      };
    
    case ACTIONS.SET_AVAILABLE_DATES:
      return {
        ...state,
        dates: {
          ...state.dates,
          availableDates: action.payload,
          datesLoaded: true,
        },
      };
    
    case ACTIONS.SET_GEOSFM_DATES:
      return {
        ...state,
        dates: {
          ...state.dates,
          geosfmAvailableDates: action.payload,
          geosfmDatesLoaded: true,
        },
      };
    
    // Filter actions
    case ACTIONS.SET_SELECTED_COUNTRY:
      return {
        ...state,
        filters: {
          ...state.filters,
          selectedCountry: action.payload,
        },
      };
    
    case ACTIONS.SET_AVAILABLE_COUNTRIES:
      return {
        ...state,
        filters: {
          ...state.filters,
          availableCountries: action.payload,
        },
      };
    
    // Selection actions
    case ACTIONS.SET_SELECTED_STATION:
      return {
        ...state,
        selection: {
          ...state.selection,
          selectedStation: action.payload,
        },
      };
    
    case ACTIONS.SET_CHART_TYPE:
      return {
        ...state,
        selection: {
          ...state.selection,
          chartType: action.payload,
        },
      };
    
    case ACTIONS.SET_GEOSFM_DATA_TYPE:
      return {
        ...state,
        selection: {
          ...state.selection,
          geoFSMDataType: action.payload,
        },
      };
    
    case ACTIONS.SET_SELECTED_SERIES:
      return {
        ...state,
        selection: {
          ...state.selection,
          selectedSeries: action.payload,
        },
      };
    
    case ACTIONS.SET_SELECTED_YEAR:
      return {
        ...state,
        selection: {
          ...state.selection,
          selectedYear: action.payload,
        },
      };
    
    // Data actions
    case ACTIONS.SET_MONITORING_DATA:
      return {
        ...state,
        data: {
          ...state.data,
          monitoringData: action.payload,
        },
      };
    
    case ACTIONS.SET_GEOSFM_DATA:
      return {
        ...state,
        data: {
          ...state.data,
          geoFSMData: action.payload,
        },
      };
    
    case ACTIONS.SET_TIME_SERIES_DATA:
      return {
        ...state,
        data: {
          ...state.data,
          timeSeriesData: action.payload,
        },
      };
    
    case ACTIONS.SET_GEOSFM_TIME_SERIES_DATA:
      return {
        ...state,
        data: {
          ...state.data,
          geoFSMTimeSeriesData: action.payload,
        },
      };
    
    case ACTIONS.SET_ADMIN_BOUNDARIES:
      return {
        ...state,
        data: {
          ...state.data,
          adminBoundariesData: action.payload,
        },
      };
    
    case ACTIONS.SET_ADMIN2_BOUNDARIES:
      return {
        ...state,
        data: {
          ...state.data,
          admin2BoundariesData: action.payload,
        },
      };
    
    case ACTIONS.SET_LAKES_DATA:
      return {
        ...state,
        data: {
          ...state.data,
          lakesData: action.payload,
        },
      };
    
    case ACTIONS.SET_RIVERS_DATA:
      return {
        ...state,
        data: {
          ...state.data,
          riversData: action.payload,
        },
      };
    
    // UI actions
    case ACTIONS.TOGGLE_CHART:
      return {
        ...state,
        ui: {
          ...state.ui,
          showChart: action.payload,
        },
      };
    
    case ACTIONS.TOGGLE_RIGHT_PANEL:
      return {
        ...state,
        ui: {
          ...state.ui,
          showRightPanel: action.payload,
        },
      };
    
    case ACTIONS.TOGGLE_SIDEBAR:
      return {
        ...state,
        ui: {
          ...state.ui,
          isSidebarActive: !state.ui.isSidebarActive,
        },
      };
    
    case ACTIONS.SET_METADATA_MODAL:
      return {
        ...state,
        ui: {
          ...state.ui,
          showMetadataModal: action.payload.show,
          currentMetadata: action.payload.metadata || null,
        },
      };
    
    case ACTIONS.SET_FALLBACK_NOTIFICATION:
      return {
        ...state,
        ui: {
          ...state.ui,
          showFallbackNotification: action.payload.show,
          fallbackMessage: action.payload.message || '',
        },
      };
    
    case ACTIONS.SET_ACTIVE_LEGEND:
      return {
        ...state,
        ui: {
          ...state.ui,
          activeLegend: action.payload,
        },
      };
    
    case ACTIONS.SET_ACTIVE_OVERLAYS:
      return {
        ...state,
        ui: {
          ...state.ui,
          activeOverlays: action.payload,
        },
      };
    
    // Loading actions
    case ACTIONS.SET_LAYERS_LOADING:
      return {
        ...state,
        loading: {
          ...state.loading,
          isLayersLoading: action.payload,
        },
      };
    
    case ACTIONS.SET_DATA_LOADING:
      return {
        ...state,
        loading: {
          ...state.loading,
          isLoadingData: action.payload,
        },
      };
    
    case ACTIONS.SET_GEOSFM_LOADING:
      return {
        ...state,
        loading: {
          ...state.loading,
          geoFSMLoading: action.payload,
        },
      };
    
    default:
      return state;
  }
}

// Create context
const MapViewerContext = createContext();

// Provider component
export function MapViewerProvider({ children }) {
  const [state, dispatch] = useReducer(mapViewerReducer, initialState);
  
  const value = { state, dispatch };
  
  return (
    <MapViewerContext.Provider value={value}>
      {children}
    </MapViewerContext.Provider>
  );
}

// Custom hook to use the context
export function useMapViewer() {
  const context = useContext(MapViewerContext);
  if (!context) {
    throw new Error('useMapViewer must be used within a MapViewerProvider');
  }
  return context;
}

// Export convenience hooks for specific state slices
export function useMapLayers() {
  const { state, dispatch } = useMapViewer();
  
  const toggleLayer = useCallback((layer, value) => {
    dispatch({ type: ACTIONS.TOGGLE_LAYER, payload: { layer, value } });
  }, [dispatch]);
  
  return {
    layers: state.layers,
    toggleLayer,
    setOverlayLayers: (layers) => dispatch({ type: ACTIONS.SET_OVERLAY_LAYERS, payload: layers }),
    setBoundaryLayers: (layers) => dispatch({ type: ACTIONS.SET_BOUNDARY_LAYERS, payload: layers }),
  };
}

export function useMapDates() {
  const { state, dispatch } = useMapViewer();
  
  const setSelectedDate = useCallback((type, date) => {
    dispatch({ type: ACTIONS.SET_SELECTED_DATE, payload: { type, date } });
  }, [dispatch]);
  
  return {
    dates: state.dates,
    setSelectedDate,
    setAvailableDates: (dates) => dispatch({ type: ACTIONS.SET_AVAILABLE_DATES, payload: dates }),
    setGeosfmDates: (dates) => dispatch({ type: ACTIONS.SET_GEOSFM_DATES, payload: dates }),
  };
}

export function useMapFilters() {
  const { state, dispatch } = useMapViewer();
  
  return {
    filters: state.filters,
    setSelectedCountry: (country) => dispatch({ type: ACTIONS.SET_SELECTED_COUNTRY, payload: country }),
    setAvailableCountries: (countries) => dispatch({ type: ACTIONS.SET_AVAILABLE_COUNTRIES, payload: countries }),
  };
}

export function useMapSelection() {
  const { state, dispatch } = useMapViewer();
  
  return {
    selection: state.selection,
    setSelectedStation: (station) => dispatch({ type: ACTIONS.SET_SELECTED_STATION, payload: station }),
    setChartType: (type) => dispatch({ type: ACTIONS.SET_CHART_TYPE, payload: type }),
    setGeoFSMDataType: (type) => dispatch({ type: ACTIONS.SET_GEOSFM_DATA_TYPE, payload: type }),
    setSelectedSeries: (series) => dispatch({ type: ACTIONS.SET_SELECTED_SERIES, payload: series }),
    setSelectedYear: (year) => dispatch({ type: ACTIONS.SET_SELECTED_YEAR, payload: year }),
  };
}

export function useMapData() {
  const { state, dispatch } = useMapViewer();
  
  return {
    data: state.data,
    setMonitoringData: (data) => dispatch({ type: ACTIONS.SET_MONITORING_DATA, payload: data }),
    setGeoFSMData: (data) => dispatch({ type: ACTIONS.SET_GEOSFM_DATA, payload: data }),
    setTimeSeriesData: (data) => dispatch({ type: ACTIONS.SET_TIME_SERIES_DATA, payload: data }),
    setGeoFSMTimeSeriesData: (data) => dispatch({ type: ACTIONS.SET_GEOSFM_TIME_SERIES_DATA, payload: data }),
    setAdminBoundaries: (data) => dispatch({ type: ACTIONS.SET_ADMIN_BOUNDARIES, payload: data }),
    setAdmin2Boundaries: (data) => dispatch({ type: ACTIONS.SET_ADMIN2_BOUNDARIES, payload: data }),
    setLakesData: (data) => dispatch({ type: ACTIONS.SET_LAKES_DATA, payload: data }),
    setRiversData: (data) => dispatch({ type: ACTIONS.SET_RIVERS_DATA, payload: data }),
  };
}

export function useMapUI() {
  const { state, dispatch } = useMapViewer();
  
  return {
    ui: state.ui,
    toggleChart: (show) => dispatch({ type: ACTIONS.TOGGLE_CHART, payload: show }),
    toggleRightPanel: (show) => dispatch({ type: ACTIONS.TOGGLE_RIGHT_PANEL, payload: show }),
    toggleSidebar: () => dispatch({ type: ACTIONS.TOGGLE_SIDEBAR }),
    setMetadataModal: (show, metadata = null) => dispatch({ type: ACTIONS.SET_METADATA_MODAL, payload: { show, metadata } }),
    setFallbackNotification: (show, message = '') => dispatch({ type: ACTIONS.SET_FALLBACK_NOTIFICATION, payload: { show, message } }),
    setActiveLegend: (legend) => dispatch({ type: ACTIONS.SET_ACTIVE_LEGEND, payload: legend }),
    setActiveOverlays: (overlays) => dispatch({ type: ACTIONS.SET_ACTIVE_OVERLAYS, payload: overlays }),
  };
}

export function useMapLoading() {
  const { state, dispatch } = useMapViewer();
  
  return {
    loading: state.loading,
    setLayersLoading: (loading) => dispatch({ type: ACTIONS.SET_LAYERS_LOADING, payload: loading }),
    setDataLoading: (loading) => dispatch({ type: ACTIONS.SET_DATA_LOADING, payload: loading }),
    setGeoSFMLoading: (loading) => dispatch({ type: ACTIONS.SET_GEOSFM_LOADING, payload: loading }),
  };
}
