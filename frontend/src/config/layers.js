// Configuration for map server based on environment
// Use placeholders that will be replaced at runtime by docker-entrypoint.sh
const getMapServerConfig = () => {
  const mapserverUrl = import.meta.env.VITE_MAPSERVER_URL || "__VITE_MAPSERVER_URL__";
  const mapcacheWmsUrl = import.meta.env.VITE_MAPCACHE_WMS_URL || "__VITE_MAPCACHE_WMS_URL__";
  const mapcacheTmsUrl = import.meta.env.VITE_MAPCACHE_TMS_URL || "__VITE_MAPCACHE_TMS_URL__";

  // Check if placeholders are still present (not replaced) - if so, return localhost URLs
  const finalMapserverUrl = mapserverUrl.startsWith('__') ? 'http://localhost:8095/' : mapserverUrl;
  const finalMapcacheWmsUrl = mapcacheWmsUrl.startsWith('__') ? 'http://localhost:8096/' : mapcacheWmsUrl;
  const finalMapcacheTmsUrl = mapcacheTmsUrl.startsWith('__') ? 'http://localhost:8096/tms/1.0.0' : mapcacheTmsUrl;

  return {
    mapserverWMSUrl: finalMapserverUrl,
    mapcacheWMSUrl: finalMapcacheWmsUrl,
    mapcacheTMSUrl: finalMapcacheTmsUrl,
  };
};

// Map configuration
export const MAP_CONFIG = {
  initialPosition: [4.6818, 34.9911], // Central Greater Horn of Africa
  initialZoom: 6,
  maxBounds: [[-13, 20], [25, 52]], // Expanded to include Tanzania (south to -13°)
  minZoom: 5,
  maxZoom: 18,
  ...getMapServerConfig(),
  getFeatureInfoFormat: "application/json",
  ghaView: {
    center: [4.6818, 34.9911],
    zoom: 6
  }
};

// API configuration - uses placeholder for runtime replacement
export const API_BASE_URL = "__VITE_API_URL__";
export const FASTAPI_BASE_URL = "__VITE_FASTAPI_URL__";

// Monitoring stations configuration
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
};

// GeoSFM configuration
export const GEOFSM_CONFIG = {
  style: {
    radius: 5,
    fillColor: "#b87c2c",
    color: "#fff",
    weight: 1,
    opacity: 1,
    fillOpacity: 0.8,
    selectedFillColor: "#ff4444",
  },
};

// Utility function to create WMS layer objects with date support
export const createWMSLayer = (name, layerId, isMapServer = false, useCache = true, needsDate = false) => {
  const wmsUrl = (useCache && isMapServer && !needsDate) ? MAP_CONFIG.mapcacheWMSUrl : MAP_CONFIG.mapserverWMSUrl;
  
  let legendUrl;
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
    needsDate
  };
};

// Impact Layers - Placeholder layers (same as original, disabled)
export const IMPACT_LAYERS = [
  { name: "Affected Population", layer: "popafftot_%date%", legend: null, disabled: true },
  { name: "Affected GDP", layer: "gdpimpact_%date%", legend: null, disabled: true },
  { name: "Affected Crops", layer: "cropsimpact_%date%", legend: null, disabled: true },
];

// IBEW Layers - Placeholder layers (same as original, disabled)
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

// Boundary Layers - All static layers served via MapServer WMS
export const BOUNDARY_LAYERS = [
  createWMSLayer("Admin 0 (Countries)", "admin0", true, true, false),
  createWMSLayer("Admin 1 (Provinces)", "admin1", true, true, false),
  createWMSLayer("Admin 2 (Districts)", "admin2", true, true, false),
  createWMSLayer("Water Bodies", "waterbodies", true, true, false),
  createWMSLayer("Rivers", "rivers", true, true, false),
];

// Base Maps
export const BASE_MAPS = [
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

// Helper function to format layer ID with date
export const formatLayerIdWithDate = (baseLayerId, date, layerType) => {
  if (layerType === 'ibew') {
    return baseLayerId; // Return as-is for runtime substitution
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

// Helper function to handle layer loading errors
export const handleLayerError = (layerId, error) => {
  // Error handling - silently ignore hazard layer errors
};

// Helper function to get alert status
export const getAlertStatus = (station, currentDischarge = null) => {
  if (!station) return 'Normal';
  const props = station.properties || station;
  if (!props) return 'Normal';
  
  const q_thr1 = parseFloat(props.Q_THR1 || props.q_thr1 || 0);
  const q_thr2 = parseFloat(props.Q_THR2 || props.q_thr2 || 0);
  const q_thr3 = parseFloat(props.Q_THR3 || props.q_thr3 || 0);
  
  if (currentDischarge !== null && currentDischarge !== undefined && !isNaN(currentDischarge)) {
    if (!isNaN(q_thr3) && q_thr3 > 0 && currentDischarge >= q_thr3) return 'Emergency';
    if (!isNaN(q_thr2) && q_thr2 > 0 && currentDischarge >= q_thr2) return 'Alarm';
    if (!isNaN(q_thr1) && q_thr1 > 0 && currentDischarge >= q_thr1) return 'Warning';
    return 'Normal';
  }
  
  return props.status || props.Status || 'Normal';
};
