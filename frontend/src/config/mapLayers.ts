/**
 * Map Layers Configuration
 * All layer definitions for WMS, base maps, boundaries, etc.
 */

import { MAP_CONFIG } from './mapConfig';

export interface WMSLayerConfig {
  name: string;
  layer: string;
  legend: string;
  isMapServer: boolean;
  useCache: boolean;
  wmsUrl: string;
  needsDate: boolean;
}

export interface BaseMapConfig {
  name: string;
  url: string;
  attribution: string;
}

/**
 * Create WMS layer configuration
 */
export const createWMSLayer = (
  name: string,
  layerId: string,
  isMapServer = false,
  useCache = true,
  needsDate = false
): WMSLayerConfig => {
  const wmsUrl = (useCache && isMapServer && !needsDate) 
    ? MAP_CONFIG.mapcacheWMSUrl 
    : MAP_CONFIG.mapserverWMSUrl;
  
  let legendUrl: string;
  
  if (isMapServer) {
    legendUrl = `${MAP_CONFIG.mapserverWMSUrl}&SERVICE=WMS&VERSION=1.1.0&REQUEST=GetLegendGraphic&LAYER=${layerId}&FORMAT=image/png&SLD_VERSION=1.1.0&STYLE=default`;
    
    if (needsDate) {
      const currentDate = new Date().toISOString().split('T')[0].replace(/-/g, '');
      legendUrl += `&date=${currentDate}&datetime=${currentDate}0000`;
    }
  } else {
    legendUrl = `${MAP_CONFIG.mapserverWMSUrl}?SERVICE=WMS&VERSION=1.0.0&REQUEST=GetLegendGraphic&LAYER=floodwatch:${layerId}&FORMAT=image/png`;
  }
  
  return {
    name,
    layer: layerId,
    legend: legendUrl,
    isMapServer,
    useCache,
    wmsUrl,
    needsDate,
  };
};

/**
 * Base maps
 */
export const BASE_MAPS: BaseMapConfig[] = [
  {
    name: "ICPAC",
    url: "https://eahazardswatch.icpac.net/tileserver-gl/styles/droughtwatch/{z}/{x}/{y}.png",
    attribution: "© ICPAC_FloodWatch",
  },
  {
    name: "OpenStreetMap",
    url: "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    attribution: "© OpenStreetMap contributors",
  },
  {
    name: "Satellite",
    url: "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    attribution: "© ESRI, Maxar",
  },
  {
    name: "Topographic",
    url: "https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png",
    attribution: "© OpenTopoMap contributors",
  },
];

/**
 * Administrative boundary layers
 */
export const BOUNDARY_LAYERS = [
  createWMSLayer("Admin 0 (Countries)", "admin0", true, true, false),
  createWMSLayer("Admin 1 (Provinces)", "admin1", true, true, false),
  createWMSLayer("Admin 2 (Districts)", "admin2", true, true, false),
  createWMSLayer("Water Bodies", "waterbodies", true, true, false),
  createWMSLayer("Rivers", "rivers", true, true, false),
];

/**
 * Impact layers (disabled - placeholders)
 */
export const IMPACT_LAYERS = [
  { name: "Affected Population", layer: "popafftot_%date%", legend: null, disabled: true },
  { name: "Affected GDP", layer: "gdpimpact_%date%", legend: null, disabled: true },
  { name: "Affected Crops", layer: "cropsimpact_%date%", legend: null, disabled: true },
];

/**
 * IBEW layers (disabled - placeholders)
 */
export const IBEW_LAYERS = [
  { name: "Health Facilities Affected", layer: "healthfac_%date%", legend: null, disabled: true },
  { name: "People Affected (100cm)", layer: "popaff100_%date%", legend: null, disabled: true },
  { name: "People Affected (25cm)", layer: "popaff25_%date%", legend: null, disabled: true },
  { name: "Total People Affected", layer: "popafftot_%date%", legend: null, disabled: true },
  { name: "Vulnerable Age Groups (100cm)", layer: "popage100_%date%", legend: null, disabled: true },
  { name: "Vulnerable Age Groups (25cm)", layer: "popage25_%date%", legend: null, disabled: true },
  { name: "Reduced Mobility (100cm)", layer: "popmob100_%date%", legend: null, disabled: true },
  { name: "Reduced Mobility (25cm)", layer: "popmob25_%date%", legend: null, disabled: true },
];

/**
 * Format layer ID with date
 */
export const formatLayerIdWithDate = (
  baseLayerId: string,
  date: string | null,
  layerType: 'ibew' | 'inundation' | 'impact' | string
): string => {
  if (layerType === 'ibew') {
    return baseLayerId;
  }
  
  if (!date) return baseLayerId;
  
  const formattedDate = date.replace(/-/g, '');
  
  switch(layerType) {
    case 'inundation':
    case 'impact':
      return `${baseLayerId}_${formattedDate}`;
    default:
      return baseLayerId;
  }
};

/**
 * Handle layer loading errors
 */
export const handleLayerError = (layerId: string, error: Error): void => {
  // Error handling - silently ignore hazard layer errors
};
