/**
 * Map Configuration
 * All map-related settings (zoom, bounds, initial position, etc.)
 */

import type { LatLngTuple, LatLngBoundsExpression } from 'leaflet';
import { API_ENDPOINTS } from './endpoints';

export interface MapConfig {
  initialPosition: LatLngTuple;
  initialZoom: number;
  maxBounds: LatLngBoundsExpression;
  minZoom: number;
  maxZoom: number;
  getFeatureInfoFormat: string;
  ghaView: {
    center: LatLngTuple;
    zoom: number;
  };
  mapserverWMSUrl: string;
  mapcacheWMSUrl: string;
  mapcacheTMSUrl: string;
}

/**
 * Core map configuration
 */
export const MAP_CONFIG: MapConfig = {
  // East Africa region - centered to show all admin 0 countries
  initialPosition: [1.5, 37],  // Centered on East Africa
  initialZoom: 5.5,  // Zoom level to fit all admin 0 bounds
  maxBounds: [[-13, 27], [16, 52]], // East Africa/GHA region only
  minZoom: 5,
  maxZoom: 18,
  
  // Map server URLs
  mapserverWMSUrl: API_ENDPOINTS.mapserver.wms,
  mapcacheWMSUrl: API_ENDPOINTS.mapserver.mapcacheWms,
  mapcacheTMSUrl: API_ENDPOINTS.mapserver.mapcacheTms,
  
  // WMS settings
  getFeatureInfoFormat: "application/json",
  
  // Regional view presets - East Africa admin 0 view
  ghaView: {
    center: [1.5, 37],
    zoom: 5.5,
  },
} as const;

/**
 * Monitoring stations styling
 */
export const MONITORING_STATIONS_CONFIG = {
  style: {
    radius: 5,
    fillColor: "#3388ff",
    color: "#fff",
    weight: 1,
    opacity: 1,
    fillOpacity: 0.8,
    selectedFillColor: "#ff4444",
  },
} as const;

/**
 * GeoSFM points styling
 */
export const GEOSFM_CONFIG = {
  style: {
    radius: 5,
    fillColor: "#b87c2c",
    color: "#fff",
    weight: 1,
    opacity: 1,
    fillOpacity: 0.8,
    selectedFillColor: "#ff4444",
  },
} as const;

/**
 * Alert status colors
 */
export const ALERT_COLORS = {
  Normal: "#2ecc71",
  Warning: "#f39c12",
  Alarm: "#e67e22",
  Emergency: "#e74c3c",
} as const;

/**
 * Map layer z-index values
 */
export const LAYER_Z_INDEX = {
  basemap: 0,
  waterBodies: 10,
  rivers: 20,
  admin2: 30,
  admin1: 40,
  admin0: 44,
  inundation: 50,
  stations: 60,
  controls: 1000,
} as const;
