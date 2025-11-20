/**
 * SINGLE CONFIGURATION FILE
 * All settings for the Early Warning System frontend
 */

// =============================================================================
// API ENDPOINTS
// =============================================================================

const getEnvVar = (key: string, placeholder: string) => {
  const value = import.meta.env[key] || placeholder;
  return value.startsWith('__') ? placeholder : value;
};

export const API = {
  backend: getEnvVar('VITE_API_URL', 'http://localhost:8000/api'),
  fastapi: getEnvVar('VITE_FASTAPI_URL', 'http://localhost:8001'),
  tipg: '/tipg', // TiPg vector tiles (replaces MapServer for admin/rivers/lakes)
  // TODO: Add TiTiler for raster tiles when implemented
  // titiler: '/titiler',
} as const;

// =============================================================================
// MAP CONFIGURATION
// =============================================================================

export const MAP = {
  center: [4.6818, 34.9911] as [number, number], // Greater Horn of Africa
  zoom: 6,
  minZoom: 5,
  maxZoom: 18,
  bounds: [[-13, 20], [25, 52]] as [[number, number], [number, number]], // Include Tanzania
} as const;

// =============================================================================
// ALERT THRESHOLDS (for early warning)
// =============================================================================

export const ALERT_LEVELS = {
  normal: {
    threshold: 2.0,
    color: '#00ff00',
    label: 'Normal',
  },
  watch: {
    threshold: 2.5,
    color: '#ffff00',
    label: 'Watch',
  },
  warning: {
    threshold: 3.0,
    color: '#ffa500',
    label: 'Warning',
  },
  alarm: {
    threshold: 4.0,
    color: '#ff0000',
    label: 'Alarm',
  },
  emergency: {
    threshold: 5.0,
    color: '#8b0000',
    label: 'Emergency',
  },
} as const;

// =============================================================================
// DATA LAYERS
// =============================================================================

export type LayerType = 'stations' | 'rainfall' | 'forecast' | 'geofsm' | 'ensemble' | 'boundary';

export interface LayerConfig {
  id: string;
  name: string;
  type: LayerType;
  enabled: boolean;
  wmsUrl?: string;
  layerName?: string;
  style?: any;
  legend?: string;
  needsDate?: boolean;
}

// Monitoring Stations Layer
export const STATIONS_LAYER: LayerConfig = {
  id: 'monitoring-stations',
  name: 'Monitoring Stations',
  type: 'stations',
  enabled: true,
  style: {
    radius: 5,
    fillColor: '#3388ff',
    color: '#fff',
    weight: 1,
    opacity: 1,
    fillOpacity: 0.8,
  },
};

// GeoSFM Layer (Satellite-based flood detection)
export const GEOFSM_LAYER: LayerConfig = {
  id: 'geofsm',
  name: 'GeoSFM (Satellite)',
  type: 'geofsm',
  enabled: false,
  style: {
    radius: 5,
    fillColor: '#b87c2c',
    color: '#fff',
    weight: 1,
    opacity: 1,
    fillOpacity: 0.8,
  },
};

// MapServer layers commented out - migrated to TiPg (vectors) and TiTiler (rasters - TODO)
//
// // Rainfall Layer (WMS from MapServer) - TODO: Migrate to TiTiler
// export const RAINFALL_LAYER: LayerConfig = {
//   id: 'rainfall',
//   name: 'Rainfall Forecast',
//   type: 'rainfall',
//   enabled: false,
//   wmsUrl: API.titiler,
//   layerName: 'rainfall_%date%',
//   needsDate: true,
// };
//
// // Ensemble Forecast Layer - TODO: Migrate to TiTiler
// export const ENSEMBLE_LAYER: LayerConfig = {
//   id: 'ensemble',
//   name: 'Ensemble Forecast',
//   type: 'ensemble',
//   enabled: false,
//   wmsUrl: API.titiler,
//   layerName: 'ensemble_mean_%date%',
//   needsDate: true,
// };
//
// // Boundary Layer - Now handled by TiPgVectorLayer
// export const BOUNDARY_LAYER: LayerConfig = {
//   id: 'boundaries',
//   name: 'Country Boundaries',
//   type: 'boundary',
//   enabled: true,
//   // Boundaries now served by TiPg vector tiles in MapViewer
// };

// All available layers
export const LAYERS: LayerConfig[] = [
  STATIONS_LAYER,
  GEOFSM_LAYER,
  // RAINFALL_LAYER,  // TODO: Re-enable when TiTiler is implemented
  // ENSEMBLE_LAYER,  // TODO: Re-enable when TiTiler is implemented
  // BOUNDARY_LAYER,  // Now using TiPgVectorLayer directly in MapViewer
];

// =============================================================================
// BASE MAPS
// =============================================================================

export const BASE_MAPS = [
  {
    id: 'osm',
    name: 'OpenStreetMap',
    url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
  },
  {
    id: 'satellite',
    name: 'Satellite',
    url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    attribution: '&copy; Esri',
  },
] as const;

// =============================================================================
// COUNTRIES (for filtering)
// =============================================================================

export const COUNTRIES = [
  { code: 'KE', name: 'Kenya', bounds: [[-4.68, 33.91], [5.03, 41.91]] },
  { code: 'UG', name: 'Uganda', bounds: [[-1.48, 29.57], [4.22, 35.04]] },
  { code: 'TZ', name: 'Tanzania', bounds: [[-11.76, 29.33], [-0.99, 40.48]] },
  { code: 'ET', name: 'Ethiopia', bounds: [[3.40, 32.99], [14.89, 47.99]] },
  { code: 'SO', name: 'Somalia', bounds: [[-1.67, 40.99], [11.98, 51.41]] },
  { code: 'SS', name: 'South Sudan', bounds: [[3.49, 24.14], [12.22, 35.95]] },
] as const;

// =============================================================================
// UI SETTINGS
// =============================================================================

export const UI = {
  animationSpeed: 300, // ms
  markerClusterRadius: 80, // pixels
  popupMaxWidth: 400, // pixels
  chartHeight: 300, // pixels
} as const;

// =============================================================================
// DATA REFRESH INTERVALS
// =============================================================================

export const REFRESH_INTERVALS = {
  stations: 5 * 60 * 1000, // 5 minutes
  forecast: 15 * 60 * 1000, // 15 minutes
  geofsm: 60 * 60 * 1000, // 1 hour
} as const;

// =============================================================================
// HELPER FUNCTIONS
// =============================================================================

/**
 * Get WMS URL for a layer with date replacement
 */
export const getLayerUrl = (layer: LayerConfig, date?: string): string => {
  if (!layer.wmsUrl || !layer.layerName) return '';

  const layerName = layer.needsDate && date
    ? layer.layerName.replace('%date%', date.replace(/-/g, ''))
    : layer.layerName;

  return `${layer.wmsUrl}?SERVICE=WMS&VERSION=1.1.0&REQUEST=GetMap&LAYERS=${layerName}`;
};

/**
 * Get alert level based on water level value
 */
export const getAlertLevel = (value: number) => {
  if (value >= ALERT_LEVELS.emergency.threshold) return ALERT_LEVELS.emergency;
  if (value >= ALERT_LEVELS.alarm.threshold) return ALERT_LEVELS.alarm;
  if (value >= ALERT_LEVELS.warning.threshold) return ALERT_LEVELS.warning;
  if (value >= ALERT_LEVELS.watch.threshold) return ALERT_LEVELS.watch;
  return ALERT_LEVELS.normal;
};

/**
 * Format date for API calls (YYYYMMDD)
 */
export const formatDateForAPI = (date: Date): string => {
  return date.toISOString().split('T')[0].replace(/-/g, '');
};

/**
 * Get color for a value based on alert thresholds
 */
export const getColorForValue = (value: number): string => {
  return getAlertLevel(value).color;
};
