import React, { useState, useCallback, useEffect, useRef } from "react";
import {
  MapContainer,
  TileLayer,
  WMSTileLayer,
  useMapEvents,
  useMap,
  LayersControl,
  GeoJSON,
  Popup,
} from "react-leaflet";
import MarkerClusterGroup from 'react-leaflet-markercluster';
import { ListGroup, Nav, Tab, Modal, Button } from "react-bootstrap";
import "leaflet/dist/leaflet.css";
import "leaflet.markercluster/dist/MarkerCluster.css";
import "leaflet.markercluster/dist/MarkerCluster.Default.css";
import "bootstrap/dist/css/bootstrap.min.css";
import L from "leaflet";
import { DischargeChart, GeoSFMChart } from "../utils/chartUtils.jsx";
import IBEWPopupHandler from "../utils/IBEWPopupHandler.jsx";

// Fix Leaflet default icon issue
import icon from 'leaflet/dist/images/marker-icon.png';
import iconShadow from 'leaflet/dist/images/marker-shadow.png';
import iconRetina from 'leaflet/dist/images/marker-icon-2x.png';

delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: iconRetina,
  iconUrl: icon,
  shadowUrl: iconShadow,
});

// Add CSS styles for blinking animation
const style = document.createElement('style');
style.innerHTML = `
  @keyframes blink-warning {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
  }
  
  @keyframes blink-alarm {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.3; }
  }
  
  @keyframes blink-emergency {
    0%, 100% { opacity: 1; }
    25% { opacity: 0.2; }
    50% { opacity: 1; }
    75% { opacity: 0.2; }
  }
  
  .marker-warning, .cluster-warning {
    animation: blink-warning 2s infinite;
  }
  
  .marker-alarm, .cluster-alarm {
    animation: blink-alarm 1.5s infinite;
  }
  
  .marker-emergency, .cluster-emergency {
    animation: blink-emergency 1s infinite;
  }
`;
document.head.appendChild(style);

// Configuration for the map's initial state and WMS server
const MAP_CONFIG = {
  initialPosition: [4.6818, 34.9911], // Central East Africa
  initialZoom: 5,
  // Much more flexible bounds for East Africa region
  // Allows extensive panning while still having some limits
  maxBounds: [[-35, -20], [35, 75]], // Very expanded bounds for easy navigation
  minZoom: 2,
  maxZoom: 18,
  mapserverWMSUrl: `http://197.254.1.10:8093/cgi-bin/mapserv?map=/etc/mapserver/master.map`,
  mapcacheWMSUrl: `http://197.254.1.10:8095/mapcache/wms`,
  mapcacheTMSUrl: `http://197.254.1.10:8095/mapcache/tms/1.0.0`,
  getFeatureInfoFormat: "application/json",
};

// Define the GeoJSON path based on environment
const GEOJSON_PATH = process.env.NODE_ENV === "production"
  ? "/timeseries_data/merged_data.geojson"
  : "/merged_data.geojson";

// Configuration for monitoring stations
const MONITORING_STATIONS_CONFIG = {
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

// Configuration for GeoSFM points
const GEOFSM_CONFIG = {
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

// Metadata for layers - COMMENTED OUT FOR NOW
const LAYER_METADATA = {
  // Metadata will be added here later
};

// Helper function to handle layer loading errors
const handleLayerError = (layerId, error) => {
  console.error(`Error loading layer ${layerId}:`, error);
  // Add more detailed error logging for hazard layers
  if (layerId.includes('flood_hazard')) {
    console.error('Flood hazard layer error details:', {
      layerId: layerId,
      errorMessage: error?.message || 'Unknown error',
      errorType: error?.type || 'Unknown type'
    });
  }
};

// Helper function to handle overlapping points by adding small offset
const handleOverlappingPoints = (features) => {
  const locationMap = new Map();
  
  features.forEach((feature) => {
    if (feature.geometry?.coordinates) {
      const [lng, lat] = feature.geometry.coordinates;
      const key = `${lat.toFixed(6)},${lng.toFixed(6)}`;
      
      if (!locationMap.has(key)) {
        locationMap.set(key, []);
      }
      locationMap.get(key).push(feature);
    }
  });
  
  // Apply small offset to overlapping points
  locationMap.forEach((overlappingFeatures) => {
    if (overlappingFeatures.length > 1) {
      const angleStep = (2 * Math.PI) / overlappingFeatures.length;
      const offsetDistance = 0.0001; // Small offset in degrees
      
      overlappingFeatures.forEach((feature, index) => {
        const angle = index * angleStep;
        const [originalLng, originalLat] = feature.geometry.coordinates;
        
        // Apply circular offset
        feature.geometry.coordinates[0] = originalLng + offsetDistance * Math.cos(angle);
        feature.geometry.coordinates[1] = originalLat + offsetDistance * Math.sin(angle);
      });
    }
  });
  
  return features;
};


// Helper function to determine alert status based on thresholds
const getAlertStatus = (station, currentDischarge = null) => {
  const props = station.properties;
  const q_thr1 = parseFloat(props.Q_THR1 || props.q_thr1); // Alert threshold
  const q_thr2 = parseFloat(props.Q_THR2 || props.q_thr2); // Alarm threshold  
  const q_thr3 = parseFloat(props.Q_THR3 || props.q_thr3); // Emergency threshold
  
  // If we have current discharge data, use it for real-time status
  if (currentDischarge !== null && currentDischarge !== undefined && !isNaN(currentDischarge)) {
    if (!isNaN(q_thr3) && currentDischarge >= q_thr3) return 'Emergency';
    if (!isNaN(q_thr2) && currentDischarge >= q_thr2) return 'Alarm';
    if (!isNaN(q_thr1) && currentDischarge >= q_thr1) return 'Warning';
    return 'Normal';
  }
  
  // Otherwise use status from properties or default to Normal
  return props.status || props.Status || 'Normal';
};

// Helper function to calculate overall threshold statistics
const calculateThresholdStats = (monitoringData, timeSeriesData) => {
  if (!monitoringData?.features) return { normal: 0, warning: 0, alarm: 0, emergency: 0, total: 0 };
  
  const stats = { normal: 0, warning: 0, alarm: 0, emergency: 0, total: 0 };
  
  monitoringData.features.forEach(station => {
    // Get current discharge from this station's own time series data
    let currentDischarge = null;
    
    const gfsData = station.properties["time_series_discharge_simulated-gfs"];
    const iconData = station.properties["time_series_discharge_simulated-icon"];
    
    if (gfsData || iconData) {
      let latestGfs = 0;
      let latestIcon = 0;
      
      if (gfsData) {
        const gfsValues = gfsData.split(",").map(val => Number(val.trim()) || 0);
        latestGfs = gfsValues[gfsValues.length - 1] || 0;
      }
      
      if (iconData) {
        const iconValues = iconData.split(",").map(val => Number(val.trim()) || 0);
        latestIcon = iconValues[iconValues.length - 1] || 0;
      }
      
      currentDischarge = Math.max(latestGfs, latestIcon);
    }
    
    const status = getAlertStatus(station, currentDischarge);
    stats[status.toLowerCase()]++;
    stats.total++;
  });
  
  return stats;
};


// Helper function to create marker icon based on alert status
const createMarkerIcon = (alertStatus, isSelected = false, isCluster = false, clusterCount = 0) => {
  if (isCluster) {
    // For clusters, use the same marker icon but scale size based on alert-specific count
    const iconMap = {
      'Normal': '/assets/map-markers/Normal.svg',
      'Warning': '/assets/map-markers/Warning.svg', 
      'Alarm': '/assets/map-markers/Alarm.svg',
      'Emergency': '/assets/map-markers/Emergency.svg'
    };
    
    const iconUrl = iconMap[alertStatus] || iconMap['Normal'];
    
    // Use same fixed size for all clusters - only label and color differ
    const size = 28; // Fixed size for all clusters
    
    // Only show count label for Warning (yellow) clusters
    const showLabel = alertStatus === 'Warning';
    
    // Add blinking class for non-normal statuses
    const blinkClass = alertStatus !== 'Normal' ? `cluster-${alertStatus.toLowerCase()}` : '';
    
    return L.divIcon({
      html: `
        <div style="position: relative; width: ${size}px; height: ${size}px;">
          <img src="${iconUrl}" style="width: 100%; height: 100%;" />
          ${showLabel ? `<div style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); background-color: rgba(255,255,255,0.9); color: #333; border-radius: 50%; width: 14px; height: 14px; display: flex; align-items: center; justify-content: center; font-size: 9px; font-weight: bold; border: 1px solid rgba(0,0,0,0.3); box-shadow: 0 1px 2px rgba(0,0,0,0.3);">${clusterCount}</div>` : ''}
        </div>
      `,
      className: `cluster-marker ${blinkClass}`,
      iconSize: [size, size],
      iconAnchor: [size/2, size]
    });
  } else {
    // Regular individual markers
    const iconMap = {
      'Normal': '/assets/map-markers/Normal.svg',
      'Warning': '/assets/map-markers/Warning.svg', 
      'Alarm': '/assets/map-markers/Alarm.svg',
      'Emergency': '/assets/map-markers/Emergency.svg'
    };
    
    const iconUrl = iconMap[alertStatus] || iconMap['Normal'];
    const iconSize = isSelected ? [20, 20] : [16, 16];
    
    // Add blinking class for non-normal statuses
    const blinkClass = alertStatus !== 'Normal' ? `marker-${alertStatus.toLowerCase()}` : '';
    const className = [isSelected ? 'selected-marker' : '', blinkClass].filter(Boolean).join(' ');
    
    return L.icon({
      iconUrl: iconUrl,
      iconSize: iconSize,
      iconAnchor: [iconSize[0]/2, iconSize[1]],
      popupAnchor: [0, -iconSize[1]],
      className: className
    });
  }
};

// Utility function to create WMS layer objects with date support
const createWMSLayer = (name, layerId, isMapServer = false, useCache = true, needsDate = false) => {
  const wmsUrl = (useCache && isMapServer) ? MAP_CONFIG.mapcacheWMSUrl : MAP_CONFIG.mapserverWMSUrl;
  
  // Build proper legend URL
  let legendUrl;
  if (isMapServer) {
    // For MapServer layers, ensure proper URL construction
    legendUrl = `${MAP_CONFIG.mapserverWMSUrl}&SERVICE=WMS&VERSION=1.1.0&REQUEST=GetLegendGraphic&LAYER=${layerId}&FORMAT=image/png&SLD_VERSION=1.1.0&STYLE=default`;
    
    // Add date parameters for date-based layers
    if (needsDate) {
      const currentDate = new Date().toISOString().split('T')[0].replace(/-/g, '');
      legendUrl += `&date=${currentDate}&datetime=${currentDate}0000`;
    }
  } else {
    // For non-MapServer layers (if you have any)
    legendUrl = `${MAP_CONFIG.geoserverWMSUrl}?SERVICE=WMS&VERSION=1.0.0&REQUEST=GetLegendGraphic&LAYER=floodwatch:${layerId}&FORMAT=image/png`;
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

// Function to format layer ID with date - UPDATED for runtime substitution
const formatLayerIdWithDate = (baseLayerId, date, layerType) => {
  // For IBEW layers, DON'T modify the layer ID - use it as-is
  // The runtime substitution happens server-side via URL parameters
  if (layerType === 'ibew') {
    return baseLayerId; // Return "popafftot_%date%" as-is
  }
  
  if (!date) return baseLayerId;
  
  const formattedDate = date.replace(/-/g, '');
  
  switch(layerType) {
    case 'inundation':
      return `${baseLayerId}_${formattedDate}`;
    case 'impact':
      return `${baseLayerId}_${formattedDate}`; // FIXED: Added date support for impact layers
    default:
      return baseLayerId;
  }
};

// Impact layers - UPDATED: now with date support
const IMPACT_LAYERS = [
  createWMSLayer("Affected Population", "impact_population", true, true, true), // Changed to true
  createWMSLayer("Affected GDP", "impact_gdp", true, true, true), // Changed to true
  createWMSLayer("Affected Crops", "impact_crops", true, true, true), // Changed to true
  createWMSLayer("Affected Roads", "impact_roads", true, true, true), // Changed to true
  createWMSLayer("Displaced Population", "impact_displaced", true, true, true), // Changed to true
  createWMSLayer("Affected Livestock", "impact_livestock", true, true, true), // Changed to true
  createWMSLayer("Affected Grazing Land", "impact_grazing", true, true, true), // Changed to true
];

// IBEW Layers - UPDATED to use the exact layer names from GetCapabilities
const IBEW_LAYERS = [
  createWMSLayer("Health Facilities Affected", "healthtot_%date%", true, false, true),
  createWMSLayer("People Affected (100cm)", "popaff100_%date%", true, false, true),
  createWMSLayer("People Affected (25cm)", "popaff25_%date%", true, false, true),
  createWMSLayer("Total People Affected", "popafftot_%date%", true, false, true),
  createWMSLayer("Vulnerable Age Groups (100cm)", "popage100_%date%", true, false, true),
  createWMSLayer("Vulnerable Age Groups (25cm)", "popage25_%date%", true, false, true),
  createWMSLayer("Reduced Mobility (100cm)", "popmob100_%date%", true, false, true),
  createWMSLayer("Reduced Mobility (25cm)", "popmob25_%date%", true, false, true),
];

// Boundary layers (no date needed)
const BOUNDARY_LAYERS = [
  createWMSLayer("Admin 1", "admin_level_1", true, true, false),
  createWMSLayer("Admin 2", "admin_level_2", true, true, false),
  createWMSLayer("Lakes", "lakes", true, true, false),
  createWMSLayer("Rivers", "rivers", true, true, false),
  createWMSLayer("Basins", "basins", true, true, false),
];

const BASE_MAPS = [
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

// Info icon component
const InfoIcon = ({ layerName, onClick }) => (
  <span 
    className="info-icon" 
    onClick={(e) => {
      e.stopPropagation();
      onClick(layerName);
    }}
    style={{
      cursor: 'pointer',
      marginLeft: '8px',
      fontSize: '14px',
      color: '#007bff',
      fontWeight: 'bold',
      display: 'inline-flex',
      alignItems: 'center',
      justifyContent: 'center',
      width: '20px',
      height: '20px',
      borderRadius: '50%',
      border: '1px solid #007bff',
      lineHeight: '1'
    }}
  >
    i
  </span>
);

// Component to display metadata modal
const MetadataModal = ({ show, handleClose, metadata }) => {
  if (!metadata) return null;
  
  return (
    <Modal show={show} onHide={handleClose} size="lg" centered>
      <Modal.Header closeButton className="bg-light">
        <Modal.Title style={{ color: "#1B6840" }}>{metadata.title}</Modal.Title>
      </Modal.Header>
      <Modal.Body>
        <p>{metadata.description}</p>
        <ul className="mb-3">
          {metadata.details.map((detail, index) => (
            <li key={index}>{detail}</li>
          ))}
        </ul>
        <p><strong>Source:</strong> {metadata.source}</p>
      </Modal.Body>
      <Modal.Footer>
        <Button variant="secondary" onClick={handleClose}>
          Close
        </Button>
      </Modal.Footer>
    </Modal>
  );
};

// Helper function to format date compactly
const formatCompactDate = (dateString) => {
  if (!dateString) return '';
  const date = new Date(dateString);
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  return `${date.getDate()} ${months[date.getMonth()]}`;
};

// Component to render a layer selector with checkboxes and calendar
const LayerSelector = ({ title, layers, selectedLayers, onLayerSelect, onInfoClick, selectedDate, onDateChange, showCalendar = true }) => {
  const [isCalendarOpen, setIsCalendarOpen] = useState(false);
  const [showFullDate, setShowFullDate] = useState(false);
  const [windowWidth, setWindowWidth] = useState(window.innerWidth);

  useEffect(() => {
    const handleResize = () => setWindowWidth(window.innerWidth);
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const isMobile = windowWidth < 768;
  const isTablet = windowWidth >= 768 && windowWidth < 1024;
  
  return (
    <div className="layers-section">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
        <h6 style={{ margin: 0 }}>{title}</h6>
        {showCalendar && (
          <div style={{ position: 'relative' }}>
            <button
              onClick={() => {
                setIsCalendarOpen(!isCalendarOpen);
                if (isMobile) {
                  setShowFullDate(!showFullDate);
                }
              }}
              onMouseEnter={() => !isMobile && setShowFullDate(true)}
              onMouseLeave={() => !isMobile && !isCalendarOpen && setShowFullDate(false)}
              style={{
                padding: isMobile ? '4px 6px' : '6px 10px',
                fontSize: isMobile ? '11px' : isTablet ? '12px' : '13px',
                backgroundColor: '#007bff',
                border: '2px solid #007bff',
                borderRadius: '6px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '3px',
                color: 'white',
                fontWeight: '500',
                transition: 'all 0.2s ease',
                minWidth: showFullDate ? (isMobile ? '100px' : '120px') : (isMobile ? '65px' : '80px'),
                justifyContent: 'center',
                position: 'relative',
                whiteSpace: 'nowrap'
              }}
              title={selectedDate || new Date().toISOString().split('T')[0]}
            >
              <span style={{ fontSize: isMobile ? '10px' : '12px' }}>📅</span>
              <span>{showFullDate 
                ? (selectedDate || new Date().toISOString().split('T')[0])
                : formatCompactDate(selectedDate || new Date().toISOString().split('T')[0])}
              </span>
            </button>
            {isCalendarOpen && (
              <div style={{
                position: 'absolute',
                top: '100%',
                right: 0,
                marginTop: '4px',
                backgroundColor: 'white',
                border: '1px solid #ddd',
                borderRadius: '4px',
                boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
                zIndex: 1000,
                padding: '8px'
              }}>
                <input
                  type="date"
                  value={selectedDate || new Date().toISOString().split('T')[0]}
                  onChange={(e) => {
                    onDateChange(e.target.value);
                    setIsCalendarOpen(false);
                  }}
                  max={new Date().toISOString().split('T')[0]}
                  style={{
                    padding: '8px 12px',
                    border: '2px solid #007bff',
                    borderRadius: '6px',
                    fontSize: '14px',
                    fontWeight: '500',
                    backgroundColor: '#f8f9fa',
                    color: '#495057',
                    outline: 'none',
                    cursor: 'pointer',
                    transition: 'all 0.2s ease',
                    width: '100%'
                  }}
                  onFocus={(e) => {
                    e.target.style.borderColor = '#0056b3';
                    e.target.style.backgroundColor = '#ffffff';
                    e.target.style.boxShadow = '0 0 0 0.2rem rgba(0, 123, 255, 0.25)';
                  }}
                  onBlur={(e) => {
                    e.target.style.borderColor = '#007bff';
                    e.target.style.backgroundColor = '#f8f9fa';
                    e.target.style.boxShadow = 'none';
                  }}
                />
              </div>
            )}
          </div>
        )}
      </div>
      <ListGroup className="layer-selector">
        {layers.map((layer) => (
          <ListGroup.Item key={layer.name}>
            <div className="layer-content">
              <div className="toggle-switch-small">
                <input
                  type="checkbox"
                  id={`layer-${layer.name}`}
                  checked={selectedLayers.has(layer.layer)}
                  onChange={() => onLayerSelect(layer)}
                />
                <label
                  htmlFor={`layer-${layer.name}`}
                  className="toggle-slider-small"
                ></label>
              </div>
              <label htmlFor={`layer-${layer.name}`} className="layer-label">
                {layer.name}
              </label>
            </div>
            <InfoIcon layerName={layer.name} onClick={onInfoClick} />
          </ListGroup.Item>
        ))}
      </ListGroup>
    </div>
  );
};

// FIXED MapLegend component - removes "Legend not available" text
const MapLegend = ({ legendUrl, title }) => {
  const [imageError, setImageError] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  
  // Reset states when legendUrl changes
  useEffect(() => {
    setImageError(false);
    setIsLoading(true);
  }, [legendUrl]);
  
  const needsCustomLegend = () =>
    title === "Hazard Map" ||
    title === "Inundation Map" ||
    legendUrl?.includes("Alerts") ||
    title === "GeoSFM" ||
    title === "Alerts Map" ||
    legendUrl?.includes("geofsm_layer");
    
  const legendData = needsCustomLegend()
    ? title === "GeoSFM" || legendUrl?.includes("geofsm_layer")
      ? {
          title: "GeoSFM",
          items: [
            { color: "#2c7fb8", label: "Low Risk" },
            { color: "#7fcdbb", label: "Medium Risk" },
            { color: "#edf8b1", label: "High Risk" },
          ],
        }
      : {
          title: "Hazard Map",
          items: [
            { color: "#FF0000", label: "High Hazard" },
            { color: "#FFFF00", label: "Medium hazard" },
            { color: "#45cbf7", label: "Low Hazard" },
          ],
        }
    : null;

  if (needsCustomLegend()) {
    return (
      <div className="map-legend">
        <h5>{legendData.title}</h5>
        {legendData.items.map((item, index) => (
          <div
            key={index}
            style={{ display: "flex", alignItems: "center", marginBottom: "8px" }}
          >
            <div
              style={{
                width: "24px",
                height: "24px",
                backgroundColor: item.color,
                marginRight: "8px",
                border: "1px solid #ccc",
              }}
            />
            <span style={{ fontSize: "12px" }}>{item.label}</span>
          </div>
        ))}
      </div>
    );
  }
  
  // FIXED: Only show legend if we have a valid URL and no error
  if (!legendUrl || imageError) {
    return null; // Return null instead of showing "Legend not available"
  }

  return (
    <div className="map-legend">
      <h5>{title}</h5>
      {isLoading && (
        <div style={{ padding: "10px", textAlign: "center", fontSize: "12px", color: "#666" }}>
          Loading legend...
        </div>
      )}
      <img
        src={legendUrl}
        alt={`Legend for ${title}`}
        onLoad={() => setIsLoading(false)}
        onError={(e) => {
          console.error(`Failed to load legend for ${title}:`, legendUrl);
          setImageError(true);
          setIsLoading(false);
        }}
        style={{ 
          display: isLoading ? 'none' : 'block',
          maxWidth: '100%',
          height: 'auto'
        }}
      />
    </div>
  );
};

// Component for the sidebar with tabs
const TabSidebar = ({
  hazardLayers,
  impactLayers,
  ibewLayers,
  boundaryLayers,
  selectedLayers,
  selectedBoundaryLayers,
  onLayerSelect,
  onBoundaryLayerSelect,
  showMonitoringStations,
  setShowMonitoringStations,
  showGeoFSM,
  setShowGeoFSM,
  geoFSMLoading,
  selectedStation,
  showMikeHydro,
  setShowMikeHydro,
  onInfoClick,
  selectedDate,
  onDateChange,
}) => {
  const [stationDate, setStationDate] = useState(new Date().toISOString().split('T')[0]);
  const [isLayersExpanded, setIsLayersExpanded] = useState(false); // Default collapsed
  
  return (
    <div className="sidebar" style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      {/* Station Information Section - Always Visible */}
      <div style={{ 
        padding: '15px', 
        borderBottom: '2px solid #e9ecef', 
        backgroundColor: '#f8f9fa',
        flexShrink: 0,
        maxHeight: '40%',
        overflowY: 'auto'
      }}>
        <h5 style={{ margin: '0 0 10px 0', color: '#1B6840', fontWeight: '600', fontSize: '16px' }}>Station Information</h5>
        <ListGroup style={{ fontSize: '14px' }}>
              <ListGroup.Item>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <div className="layer-content">
                    <div className="toggle-switch-small">
                      <input
                        type="checkbox"
                        id="monitoring-stations-toggle"
                        checked={showMonitoringStations}
                        onChange={() => setShowMonitoringStations((prev) => !prev)}
                      />
                      <label
                        htmlFor="monitoring-stations-toggle"
                        className="toggle-slider-small"
                      ></label>
                    </div>
                    <label htmlFor="monitoring-stations-toggle">
                      FloodProofs East Africa
                    </label>
                  </div>
                  <InfoIcon layerName="FloodProofs East Africa" onClick={onInfoClick} />
                </div>
              </ListGroup.Item>
              <ListGroup.Item>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <div className="layer-content">
                      <div className="toggle-switch-small">
                        <input
                          type="checkbox"
                          id="geofsm-toggle"
                          checked={showGeoFSM}
                          onChange={() => setShowGeoFSM((prev) => !prev)}
                        />
                        <label
                          htmlFor="geofsm-toggle"
                          className="toggle-slider-small"
                        ></label>
                      </div>
                      <label htmlFor="geofsm-toggle">
                        GeoSFM {geoFSMLoading && <span style={{fontSize: '12px', color: '#666'}}> (Loading...)</span>}
                      </label>
                    </div>
                    <InfoIcon layerName="GeoSFM" onClick={onInfoClick} />
                  </div>
                </div>
              </ListGroup.Item>
              <ListGroup.Item>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <div className="layer-content">
                    <div className="toggle-switch-small">
                      <input
                        type="checkbox"
                        id="mike-hydro-toggle"
                        checked={showMikeHydro}
                        onChange={() => setShowMikeHydro(!showMikeHydro)}
                      />
                      <label
                        htmlFor="mike-hydro-toggle"
                        className="toggle-slider-small"
                      ></label>
                    </div>
                    <label htmlFor="mike-hydro-toggle">
                      Mike Hydro
                    </label>
                  </div>
                  <InfoIcon layerName="Mike Hydro" onClick={onInfoClick} />
                </div>
              </ListGroup.Item>
        </ListGroup>
        {selectedStation && (
              <div className="station-characteristics">
                <h5>{selectedStation.properties?.SEC_NAME}</h5>
                <div className="characteristics-grid">
                  <div className="characteristic-item">
                    <span className="characteristic-label">Basin:</span>
                    <span className="characteristic-value">
                      {selectedStation.properties?.BASIN}
                    </span>
                  </div>
                  <div className="characteristic-item">
                    <span className="characteristic-label">Area:</span>
                    <span className="characteristic-value">
                      {selectedStation.properties?.AREA} km²
                    </span>
                  </div>
                  <div className="characteristic-item">
                    <span className="characteristic-label">Location:</span>
                    <span className="characteristic-value">
                      {selectedStation.properties?.latitude?.toFixed(4)}°N,{" "}
                      {selectedStation.properties?.longitude?.toFixed(4)}°E
                    </span>
                  </div>
                  <div className="characteristic-item">
                    <span className="characteristic-label">Alert Threshold:</span>
                    <span className="characteristic-value alert-threshold">
                      {selectedStation.properties?.Q_THR1 ? parseFloat(selectedStation.properties.Q_THR1).toFixed(2) : 'N/A'} m³/s
                    </span>
                  </div>
                  <div className="characteristic-item">
                    <span className="characteristic-label">Alarm Threshold:</span>
                    <span className="characteristic-value alarm-threshold">
                      {selectedStation.properties?.Q_THR2 ? parseFloat(selectedStation.properties.Q_THR2).toFixed(2) : 'N/A'} m³/s
                    </span>
                  </div>
                  <div className="characteristic-item">
                    <span className="characteristic-label">
                      Emergency Threshold:
                    </span>
                    <span className="characteristic-value emergency-threshold">
                      {selectedStation.properties?.Q_THR3 ? parseFloat(selectedStation.properties.Q_THR3).toFixed(2) : 'N/A'} m³/s
                    </span>
                  </div>
                </div>
              </div>
            )}
      </div>
      
      {/* Collapsible Impact Layers Section */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <div 
          className="sidebar-tabs"
          onClick={() => setIsLayersExpanded(!isLayersExpanded)}
          style={{ 
            cursor: 'pointer', 
            padding: '15px',
            backgroundColor: isLayersExpanded ? '#1B6840' : '#f8f9fa',
            borderBottom: '1px solid #e9ecef',
            display: 'flex',
            justifyContent: 'flex-start', // Align to left like Station Information
            alignItems: 'center',
            userSelect: 'none',
            transition: 'all 0.3s ease'
          }}
        >
          <span style={{ 
            color: isLayersExpanded ? 'white' : '#1B6840', 
            fontWeight: '600',
            fontSize: '16px', // Match Station Information font size
            marginLeft: '0' // Ensure no extra margin
          }}>
            Impact Layers
          </span>
        </div>
        {isLayersExpanded && (
          <div style={{ flex: 1, overflowY: 'auto', padding: '15px' }}>
            <LayerSelector
              title="Inundation Map"
              layers={hazardLayers}
              selectedLayers={selectedLayers}
              onLayerSelect={onLayerSelect}
              onInfoClick={onInfoClick}
              selectedDate={selectedDate}
              onDateChange={onDateChange}
            />
            <LayerSelector
              title="Impact Layers"
              layers={impactLayers}
              selectedLayers={selectedLayers}
              onLayerSelect={onLayerSelect}
              onInfoClick={onInfoClick}
              selectedDate={selectedDate}
              onDateChange={onDateChange}
              showCalendar={true}
            />
            <LayerSelector
              title="IBEW Layers"
              layers={ibewLayers}
              selectedLayers={selectedLayers}
              onLayerSelect={onLayerSelect}
              onInfoClick={onInfoClick}
              selectedDate={selectedDate}
              onDateChange={onDateChange}
            />
          </div>
        )}
      </div>
    </div>
  );
};

// UPDATED StableWMSLayer component to handle runtime substitution properly
const StableWMSLayer = React.memo(({ url, layers, transparent = true, format = "image/png", version = "1.1.0", zIndex = 100, layerConfig, selectedDate, layerType }) => {
  const [key, setKey] = useState(0);
  
  // For IBEW layers, don't modify the layer ID but add date parameters to URL
  const finalLayerId = React.useMemo(() => {
    if (layerType === 'ibew') {
      return layers; // Use layer name as-is: "popafftot_%date%"
    }
    const formattedId = layerConfig?.needsDate && selectedDate ? 
      formatLayerIdWithDate(layers, selectedDate, layerType) : layers;
    
    // Debug logging for inundation/hazard layers
    if (layers.includes('flood_hazard') || layers === 'flood_hazard') {
      console.log('Inundation layer debug:', {
        originalLayer: layers,
        layerType: layerType,
        selectedDate: selectedDate,
        finalLayerId: formattedId,
        needsDate: layerConfig?.needsDate
      });
    }
    
    return formattedId;
  }, [layers, layerConfig, selectedDate, layerType]);
  
  // Build URL with runtime substitution parameters for IBEW layers
  const finalUrl = React.useMemo(() => {
    if (layerType === 'ibew' && selectedDate) {
      const formattedDate = selectedDate.replace(/-/g, '');
      const urlParams = new URLSearchParams();
      urlParams.set('date', formattedDate);
      urlParams.set('datetime', `${formattedDate}0000`);
      
      const separator = url.includes('?') ? '&' : '?';
      return `${url}${separator}${urlParams.toString()}`;
    }
    return url;
  }, [url, layerType, selectedDate]);
  
  useEffect(() => {
    setKey(prev => prev + 1);
  }, [finalLayerId, selectedDate]);
  
  
  // Debug logging for hazard layers
  if (finalLayerId.includes('flood_hazard')) {
    console.log('Rendering flood hazard WMS layer:', {
      url: finalUrl,
      layerId: finalLayerId,
      format: format,
      transparent: transparent
    });
  }
  
  return (
    <WMSTileLayer
      key={`wms-${finalLayerId}-${selectedDate}-${key}`}
      url={finalUrl}
      layers={finalLayerId}
      format={format}
      transparent={transparent}
      version={version}
      updateWhenIdle={true}
      updateWhenZooming={false}
      updateInterval={200}
      keepBuffer={2}
      zIndex={zIndex}
      eventHandlers={{
        error: (error) => handleLayerError(finalLayerId, error),
        load: () => {}
      }}
    />
  );
});

// Main MapViewer component
const MapViewer = () => {
  const [selectedLayers, setSelectedLayers] = useState(new Set());
  const [selectedBoundaryLayers, setSelectedBoundaryLayers] = useState(new Set([
    'rivers',
    'admin_level_1'
  ]));
  const [activeLegend, setActiveLegend] = useState(null);
  const [mapKey, setMapKey] = useState(0);
  const [showMonitoringStations, setShowMonitoringStations] = useState(false);
  const [showGeoFSM, setShowGeoFSM] = useState(false);
  const [showMikeHydro, setShowMikeHydro] = useState(false);
  const [monitoringData, setMonitoringData] = useState(null);
  const [geoFSMData, setGeoFSMData] = useState(null);
  const [selectedStation, setSelectedStation] = useState(null);
  const [timeSeriesData, setTimeSeriesData] = useState([]);
  const [geoFSMTimeSeriesData, setGeoFSMTimeSeriesData] = useState([]);
  const [geoFSMLoading, setGeoFSMLoading] = useState(false);
  const [showChart, setShowChart] = useState(false);
  
  // Debug showChart changes
  useEffect(() => {
  }, [showChart]);
  const [chartType, setChartType] = useState("discharge");
  const [geoFSMDataType, setGeoFSMDataType] = useState("streamflow");
  const [selectedSeries, setSelectedSeries] = useState("both");
  const [availableDataTypes, setAvailableDataTypes] = useState([]);
  const [panelHeight, setPanelHeight] = useState(320);
  const [panelWidth, setPanelWidth] = useState(600);
  const [isResizing, setIsResizing] = useState(false);
  const [resizeDirection, setResizeDirection] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
  const [panelPosition, setPanelPosition] = useState({ x: 0, y: 0 });
  
  // State for mobile responsiveness
  const [isMobile, setIsMobile] = useState(window.innerWidth < 768);
  const [sidebarOpen, setSidebarOpen] = useState(!window.innerWidth < 768);
  
  // Handle window resize for responsiveness
  useEffect(() => {
    const handleResize = () => {
      const mobile = window.innerWidth < 768;
      setIsMobile(mobile);
      // Auto-close sidebar on mobile
      if (mobile && sidebarOpen) {
        setSidebarOpen(false);
      }
    };
    
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [sidebarOpen]);
  
  // State for metadata modal
  const [showMetadataModal, setShowMetadataModal] = useState(false);
  const [currentMetadata, setCurrentMetadata] = useState(null);
  
  // State for unified date selection for all layers
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split('T')[0]);

  // Handler for date changes - now applies to all layers
  const handleDateChange = (date) => {
    setSelectedDate(date);
    
    // Force map refresh when date changes
    setMapKey(prev => prev + 1);
  };

  // Handler for info icon clicks
  const handleInfoClick = (layerName) => {
    // For now, show a simple placeholder since metadata is empty
    const metadata = LAYER_METADATA[layerName] || {
      title: layerName,
      description: `Information about ${layerName}`,
      details: ["Details will be added soon"],
      source: "East Africa Flood Watch"
    };
    
    metadata.title = layerName;
    setCurrentMetadata(metadata);
    setShowMetadataModal(true);
  };

  // Handler for closing metadata modal
  const handleCloseMetadata = () => {
    setShowMetadataModal(false);
  };

  // Function to fetch GeoJSON data
  const fetchMonitoringData = useCallback(() => {
    
    fetch(GEOJSON_PATH)
      .then((response) => {
        if (!response.ok) {
          console.error(`HTTP error! status: ${response.status}`);
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
      })
      .then((data) => {
        
        data.features.forEach((feature) => {
          if (feature.geometry?.coordinates) {
            feature.properties.latitude = feature.geometry.coordinates[1];
            feature.properties.longitude = feature.geometry.coordinates[0];
          }
        });
        
        setMonitoringData(data);
      })
      .catch((error) => {
        console.error("Error loading monitoring data:", error);
        setMonitoringData(null);
      });
  }, []);

  useEffect(() => {
    if (showMonitoringStations) {
      fetchMonitoringData();
      const interval = setInterval(fetchMonitoringData, 60000);
      return () => clearInterval(interval);
    } else {
      setMonitoringData(null);
      setTimeSeriesData([]);
      setSelectedStation(null);
    }
  }, [showMonitoringStations, fetchMonitoringData]);

  useEffect(() => {
    if (showGeoFSM) {
      setGeoFSMLoading(true);
      fetch("hydro_data_with_locations.geojson")
        .then((response) => response.json())
        .then((data) => {
          
          // Since we're using the pre-filtered file, skip complex date filtering
          // The file is already filtered to relevant dates
          const allFeatures = data.features;
          
          // Debug: Check for station ID 249 specifically
          const station249Features = allFeatures.filter(f => f.properties.Id === 249);
          
          // Check if coordinates are the same
          if (station249Features.length > 1) {
            const coords = station249Features.map(f => f.geometry?.coordinates);
          }
          
          // Deduplicate features by station ID - keep only one feature per station for map display
          const stationMap = new Map();
          allFeatures.forEach((feature, index) => {
            const stationId = feature.properties.Id;
            if (stationId && !stationMap.has(stationId)) {
              // Add coordinates as properties for easier access
              if (feature.geometry?.coordinates) {
                feature.properties.latitude = feature.geometry.coordinates[1];
                feature.properties.longitude = feature.geometry.coordinates[0];
              }
              stationMap.set(stationId, feature);
            }
          });
          
          // Create filtered data with unique stations only for map display
          const filteredData = {
            ...data,
            features: Array.from(stationMap.values())
          };
          
          
          // Store the deduplicated data for map display
          setGeoFSMData(filteredData);
          
          // Store the full dataset globally for time series processing
          window.geoFSMFullData = {
            ...data,
            features: allFeatures
          };
          
          const validTypes = ["riverdepth", "streamflow"];
          const dataTypes = [
            ...new Set(
              filteredData.features
                .map((f) => f.properties.data_type)
                .filter((type) => type && validTypes.includes(type)),
            ),
          ].sort((a, b) => a === "streamflow" ? -1 : b === "streamflow" ? 1 : 0);
          setAvailableDataTypes(
            dataTypes.length > 0 ? dataTypes : ["streamflow", "riverdepth"],
          );
          setGeoFSMDataType(dataTypes.includes("streamflow") ? "streamflow" : (dataTypes[0] || "streamflow"));

          // Skip expensive time series processing during initial load
          // This will be done only when a station is selected
          setGeoFSMTimeSeriesData([]);
          setGeoFSMLoading(false);
        })
        .catch((error) => {
          console.error("Error loading GeoSFM data:", error);
          setGeoFSMData(null);
          setGeoFSMTimeSeriesData([]);
          setAvailableDataTypes([]);
          setGeoFSMLoading(false);
        });
    } else {
      setGeoFSMData(null);
      setGeoFSMTimeSeriesData([]);
      setAvailableDataTypes([]);
      setGeoFSMLoading(false);
      // Only clear selected station if it was a GeoFSM station
      if (selectedStation && selectedStation.properties.Id) {
        setSelectedStation(null);
        setChartType("discharge"); // Reset to default discharge chart type
        setGeoFSMDataType("streamflow"); // Reset to default GeoSFM data type
      }
    }
  }, [showGeoFSM]);



  // Handle panel resizing
  const handleResizeStart = (direction, e) => {
    setIsResizing(true);
    setResizeDirection(direction);
    e.preventDefault();
    e.stopPropagation();
  };

  const handleMouseMove = useCallback((e) => {
    if (!isResizing || !resizeDirection) return;
    
    const rect = document.querySelector('.bottom-panel').getBoundingClientRect();
    const minWidth = 400;
    const maxWidth = window.innerWidth - 100;
    const minHeight = 200;
    const maxHeight = window.innerHeight - 150;
    
    let newWidth = panelWidth;
    let newHeight = panelHeight;
    let newX = panelPosition.x;
    let newY = panelPosition.y;
    
    switch(resizeDirection) {
      case 'top':
        newHeight = rect.bottom - e.clientY;
        newY = e.clientY - 80;
        break;
      case 'bottom':
        newHeight = e.clientY - rect.top;
        break;
      case 'left':
        newWidth = rect.right - e.clientX;
        newX = e.clientX - 350;
        break;
      case 'right':
        newWidth = e.clientX - rect.left;
        break;
      case 'top-left':
        newHeight = rect.bottom - e.clientY;
        newWidth = rect.right - e.clientX;
        newY = e.clientY - 80;
        newX = e.clientX - 350;
        break;
      case 'top-right':
        newHeight = rect.bottom - e.clientY;
        newWidth = e.clientX - rect.left;
        newY = e.clientY - 80;
        break;
      case 'bottom-left':
        newHeight = e.clientY - rect.top;
        newWidth = rect.right - e.clientX;
        newX = e.clientX - 350;
        break;
      case 'bottom-right':
        newHeight = e.clientY - rect.top;
        newWidth = e.clientX - rect.left;
        break;
    }
    
    if (newWidth >= minWidth && newWidth <= maxWidth) {
      setPanelWidth(newWidth);
      if (['left', 'top-left', 'bottom-left'].includes(resizeDirection)) {
        setPanelPosition(prev => ({ ...prev, x: newX }));
      }
    }
    
    if (newHeight >= minHeight && newHeight <= maxHeight) {
      setPanelHeight(newHeight);
      if (['top', 'top-left', 'top-right'].includes(resizeDirection)) {
        setPanelPosition(prev => ({ ...prev, y: newY }));
      }
    }
  }, [isResizing, resizeDirection, panelWidth, panelHeight, panelPosition]);

  const handleMouseUp = useCallback(() => {
    setIsResizing(false);
    setResizeDirection(null);
  }, []);

  // Handle panel dragging
  const handleDragStart = (e) => {
    setIsDragging(true);
    const rect = e.currentTarget.closest('.bottom-panel').getBoundingClientRect();
    setDragOffset({
      x: e.clientX - rect.left,
      y: e.clientY - rect.top
    });
    e.preventDefault();
  };

  const handleDragMove = useCallback((e) => {
    if (!isDragging) return;
    
    const windowWidth = window.innerWidth;
    const windowHeight = window.innerHeight;
    const sidebarWidth = 350;
    
    const newX = Math.max(sidebarWidth, Math.min(windowWidth - 400, e.clientX - dragOffset.x));
    const newY = Math.max(80, Math.min(windowHeight - panelHeight - 30, e.clientY - dragOffset.y));
    
    setPanelPosition({ x: newX - sidebarWidth, y: newY });
  }, [isDragging, dragOffset, panelHeight]);

  const handleDragEnd = useCallback(() => {
    setIsDragging(false);
  }, []);

  useEffect(() => {
    if (isResizing) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
      
      const cursorMap = {
        'top': 'ns-resize',
        'bottom': 'ns-resize',
        'left': 'ew-resize', 
        'right': 'ew-resize',
        'top-left': 'nw-resize',
        'top-right': 'ne-resize',
        'bottom-left': 'sw-resize',
        'bottom-right': 'se-resize'
      };
      
      document.body.style.cursor = cursorMap[resizeDirection] || 'default';
      document.body.style.userSelect = 'none';
    }

    if (isDragging) {
      document.addEventListener('mousemove', handleDragMove);
      document.addEventListener('mouseup', handleDragEnd);
      document.body.style.cursor = 'move';
      document.body.style.userSelect = 'none';
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      document.removeEventListener('mousemove', handleDragMove);
      document.removeEventListener('mouseup', handleDragEnd);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };
  }, [isResizing, resizeDirection, isDragging, handleMouseMove, handleMouseUp, handleDragMove, handleDragEnd]);

  // Enhanced layer selection with proper date handling
  const handleLayerSelection = useCallback(
    (layer) => {
      setSelectedLayers((prev) => {
        const newSelectedLayers = new Set(prev);
        const isImpactLayer = IMPACT_LAYERS.some((l) => l.layer === layer.layer);
        const isIBEWLayer = IBEW_LAYERS.some((l) => l.layer === layer.layer);
        
        if (newSelectedLayers.has(layer.layer)) {
          newSelectedLayers.delete(layer.layer);
          if (activeLegend === layer.legend) setActiveLegend(null);
        } else {
          if (isImpactLayer) {
            IMPACT_LAYERS.forEach((l) => newSelectedLayers.delete(l.layer));
          }
          if (isIBEWLayer) {
            IBEW_LAYERS.forEach((l) => newSelectedLayers.delete(l.layer));
          }
          
          newSelectedLayers.add(layer.layer);
          setActiveLegend(layer.legend);
        }
        return newSelectedLayers;
      });
      
      setShowChart(false);
      setSelectedStation(null);
      setTimeSeriesData([]);
      setGeoFSMTimeSeriesData([]);
    },
    [activeLegend],
  );

  
  const handleBoundaryLayerSelection = useCallback(
    (layer) => {
      if (layer.layer === 'admin_level_1') {
        return;
      }
      
      setSelectedBoundaryLayers((prev) => {
        const newSelected = new Set(prev);
        if (newSelected.has(layer.layer)) {
          newSelected.delete(layer.layer);
          if (activeLegend === layer.legend) setActiveLegend(null);
        } else {
          newSelected.add(layer.layer);
          setActiveLegend(layer.legend);
        }
        return newSelected;
      });
    },
    [activeLegend],
  );

  const handleStationClick = useCallback(
    (feature) => {
      setSelectedStation(feature);
      setShowChart(true);
      
      if (!feature?.properties) {
        return;
      }

      const dataType = feature.properties.data_type || "discharge";
      
      // For GeoSFM data, set chartType to indicate we're in GeoSFM mode
      if (dataType === "riverdepth" || dataType === "streamflow") {
        setChartType("riverdepth"); // Use riverdepth as the general GeoSFM indicator
        // If this is a GeoSFM station, prioritize streamflow if available
        const stationId = feature.properties.Id;
        const stationFeatures = (window.geoFSMFullData || geoFSMData)?.features?.filter(f => f.properties.Id === stationId) || [];
        const hasStreamflow = stationFeatures.some(f => f.properties.data_type === "streamflow");
        setGeoFSMDataType(hasStreamflow ? "streamflow" : dataType);
      } else {
        setChartType(dataType);
        setGeoFSMDataType(dataType === "discharge" ? "streamflow" : dataType);
      }

      try {
        if (dataType === "riverdepth" || dataType === "streamflow") {
          
          // Use the full dataset for time series processing, not the deduplicated display data
          const fullGeoFSMData = window.geoFSMFullData || geoFSMData;
          
          const stationFeatures = fullGeoFSMData?.features?.filter((f) => f.properties.Id === feature.properties.Id) || [];
          
          const timeSeries =
            stationFeatures
              .reduce((acc, f) => {
                const timestamp = new Date(f.properties.timestamp);
                if (isNaN(timestamp.getTime())) return acc;
                const existing = acc.find(
                  (item) => item.timestamp.getTime() === timestamp.getTime(),
                );
                if (existing) {
                  if (f.properties.data_type === "riverdepth")
                    existing.depth = Number(f.properties.value) || 0;
                  else if (f.properties.data_type === "streamflow")
                    existing.streamflow = Number(f.properties.value) || 0;
                } else {
                  acc.push({
                    timestamp,
                    depth:
                      f.properties.data_type === "riverdepth"
                        ? Number(f.properties.value) || 0
                        : 0,
                    streamflow:
                      f.properties.data_type === "streamflow"
                        ? Number(f.properties.value) || 0
                        : 0,
                  });
                }
                return acc;
              }, [])
              .sort((a, b) => a.timestamp - b.timestamp) || [];
          
          
          setGeoFSMTimeSeriesData(timeSeries);
          setTimeSeriesData([]);
          
          // Set available data types based on the selected station's data
          const stationDataTypes = [
            ...new Set(
              fullGeoFSMData?.features
                ?.filter((f) => f.properties.Id === feature.properties.Id)
                .map((f) => f.properties.data_type)
                .filter((type) => type && ["riverdepth", "streamflow"].includes(type))
            )
          ].sort((a, b) => a === "streamflow" ? -1 : b === "streamflow" ? 1 : 0);
          setAvailableDataTypes(stationDataTypes.length > 0 ? stationDataTypes : ["streamflow", "riverdepth"]);
          
          // Ensure streamflow is selected if available
          if (stationDataTypes.includes("streamflow")) {
            setGeoFSMDataType("streamflow");
          }
        } else {
          
          const timePeriod =
            feature.properties.time_period?.split(",")?.map((t) => t.trim()) ||
            [];
          const gfsValues =
            feature.properties["time_series_discharge_simulated-gfs"]
              ?.split(",")
              .map((val) => Number(val.trim()) || 0) || [];
          const iconValues =
            feature.properties["time_series_discharge_simulated-icon"]
              ?.split(",")
              .map((val) => Number(val.trim()) || 0) || [];
              

          const rawData = timePeriod
            .map((time, index) => ({
              time: new Date(time),
              gfs: gfsValues[index],
              icon: iconValues[index],
            }))
            .filter(
              (item) =>
                !isNaN(item.time.getTime()) &&
                !isNaN(item.gfs) &&
                !isNaN(item.icon),
            );
            

          // Aggregate data by day (daily averages)
          const dailyData = rawData.reduce((acc, item) => {
            const dateKey = item.time.toISOString().split('T')[0]; // Get YYYY-MM-DD format
            
            if (!acc[dateKey]) {
              acc[dateKey] = {
                date: new Date(dateKey),
                gfsValues: [],
                iconValues: []
              };
            }
            
            acc[dateKey].gfsValues.push(item.gfs);
            acc[dateKey].iconValues.push(item.icon);
            
            return acc;
          }, {});

          // Calculate daily averages
          const aggregatedData = Object.values(dailyData).map(day => ({
            time: day.date,
            gfs: day.gfsValues.reduce((sum, val) => sum + val, 0) / day.gfsValues.length,
            icon: day.iconValues.reduce((sum, val) => sum + val, 0) / day.iconValues.length
          })).sort((a, b) => a.time - b.time);

          setTimeSeriesData(aggregatedData);
          setGeoFSMTimeSeriesData([]);
        }
      } catch (error) {
        console.error("Error in handleStationClick:", error);
        setTimeSeriesData([]);
        setGeoFSMTimeSeriesData([]);
      }
    },
    [geoFSMData],
  );

  
  // Update hazard layers
  const hazardLayersWithDate = React.useMemo(() => [
    createWMSLayer("Inundation Map", `flood_hazard`, true, false, true),
    createWMSLayer("Alerts Map", "Alerts", true, false, false),
  ], []);

  // Get the appropriate date for a layer type
  const getDateForLayerType = (layerConfig) => {
    if (!layerConfig.needsDate) return null;
    
    // Return the unified date for all layers
    return selectedDate;
  };

  return (
    <div className="map-viewer">
      {/* Development Notice Banner - Centered Below Navbar Items */}
      <div style={{
        position: 'fixed',
        top: '82px', // Small gap after navbar ends
        left: isMobile ? '50%' : '50%', // Center horizontally
        transform: 'translateX(-50%)',
        width: isMobile ? '300px' : '500px', // Responsive width
        height: '28px',
        backgroundColor: 'rgba(255, 193, 7, 0.95)', // Yellow background
        borderRadius: '8px', // Rounded all corners
        overflow: 'hidden',
        zIndex: 1000, // Above map but below other controls
        display: 'flex',
        alignItems: 'center',
        pointerEvents: 'none', // Don't interfere with map interaction
        boxShadow: '0 2px 6px rgba(0,0,0,0.2)',
        border: '2px solid #ffc107'
      }}>
        <div style={{
          display: 'flex',
          animation: 'scrollTextContinuous 45s linear infinite', // Slower continuous animation
          whiteSpace: 'nowrap',
          paddingLeft: '100%'
        }}>
          <span style={{
            color: '#333', // Black text on yellow background
            fontSize: '16px', // Increased font size
            fontWeight: 'bold', // Bold text
            letterSpacing: '0.5px',
            display: 'inline-block',
            minWidth: '1200px' // Ensure text width is exactly double the container width
          }}>
            ⚠️ NOTICE: This system is under development. Most features are still in testing phases and may not function as expected. ⚠️ &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
            ⚠️ NOTICE: This system is under development. Most features are still in testing phases and may not function as expected. ⚠️
          </span>
        </div>
      </div>
      
      {/* Add CSS animation */}
      <style>
        {`
          @keyframes scrollTextContinuous {
            0% {
              transform: translateX(0%);
            }
            100% {
              transform: translateX(-100%);
            }
          }
        `}
      </style>
      
      {/* Mobile toggle button */}
      {isMobile && (
        <button
          onClick={() => setSidebarOpen(!sidebarOpen)}
          style={{
            position: 'fixed',
            bottom: sidebarOpen ? '40vh' : '10px',
            left: '10px',
            zIndex: 1002,
            backgroundColor: '#1B6840',
            color: 'white',
            border: 'none',
            borderRadius: '50%',
            width: '50px',
            height: '50px',
            fontSize: '24px',
            cursor: 'pointer',
            boxShadow: '0 2px 10px rgba(0,0,0,0.3)',
            transition: 'all 0.3s ease',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}
        >
          {sidebarOpen ? '✕' : '☰'}
        </button>
      )}
      
      <div className={`sidebar ${isMobile && !sidebarOpen ? 'sidebar-hidden' : ''}`}>
        <TabSidebar
          hazardLayers={hazardLayersWithDate}
          impactLayers={IMPACT_LAYERS}
          ibewLayers={IBEW_LAYERS}
          boundaryLayers={BOUNDARY_LAYERS}
          selectedLayers={selectedLayers}
          selectedBoundaryLayers={selectedBoundaryLayers}
          onLayerSelect={handleLayerSelection}
          onBoundaryLayerSelect={handleBoundaryLayerSelection}
          showMonitoringStations={showMonitoringStations}
          setShowMonitoringStations={setShowMonitoringStations}
          showGeoFSM={showGeoFSM}
          setShowGeoFSM={setShowGeoFSM}
          geoFSMLoading={geoFSMLoading}
          selectedStation={selectedStation}
          showMikeHydro={showMikeHydro}
          setShowMikeHydro={setShowMikeHydro}
          onInfoClick={handleInfoClick}
          selectedDate={selectedDate}
          onDateChange={handleDateChange}
        />
      </div>
      <div className="main-content">
        <div className="map-container" style={{
          bottom: (showChart && !panelPosition.x && !panelPosition.y) ? `${panelHeight + 30}px` : '30px'
        }}>
          <MapContainer
            center={MAP_CONFIG.initialPosition}
            zoom={MAP_CONFIG.initialZoom}
            minZoom={MAP_CONFIG.minZoom}
            maxZoom={MAP_CONFIG.maxZoom}
            maxBounds={MAP_CONFIG.maxBounds}
            maxBoundsViscosity={0.1}
            scrollWheelZoom={{
              speed: 0.5,  // Slower zoom speed (default is 1)
              sensitivity: 0.5  // Less sensitive to scroll
            }}
            wheelDebounceTime={100}  // Add debounce for smoother scrolling
            wheelPxPerZoomLevel={120}  // More scroll needed per zoom level
            zoomSnap={0.25}  // Allow fractional zoom levels for smoother transitions
            zoomDelta={0.5}  // Smaller zoom increments (default is 1)
            zoomAnimation={true}  // Enable zoom animation
            zoomAnimationThreshold={4}  // Always animate zoom
            style={{ height: "100%", width: "100%" }}
            key={mapKey}
          >
            <TileLayer
              url={BASE_MAPS[0].url}
              attribution={BASE_MAPS[0].attribution}
            />
            
            {/* Render WMS layers with proper date handling */}
            {Array.from(selectedLayers).map((layerId) => {
              const layerConfig = [
                ...hazardLayersWithDate, 
                ...IMPACT_LAYERS, 
                ...IBEW_LAYERS
              ].find(l => l.layer === layerId);
              
              if (!layerConfig) {
                console.warn(`Layer configuration not found for: ${layerId}`);
                return null;
              }
              
              const layerDate = getDateForLayerType(layerConfig);
              const layerType = IMPACT_LAYERS.some(l => l.layer === layerId) ? 'impact' :
                              IBEW_LAYERS.some(l => l.layer === layerId) ? 'ibew' :
                              layerId.includes('flood_hazard') ? 'inundation' : null;
              
              return (
                <StableWMSLayer
                  key={`layer-${layerId}-${layerDate || 'no-date'}`}
                  url={layerConfig.useCache ? MAP_CONFIG.mapcacheWMSUrl : MAP_CONFIG.mapserverWMSUrl}
                  layers={layerId}
                  transparent={true}
                  format="image/png"
                  version="1.1.0"
                  zIndex={100}
                  layerConfig={layerConfig}
                  selectedDate={layerDate}
                  layerType={layerType}
                />
              );
            })}

            {/* Boundary layers with MapCache */}
            {['lakes', 'rivers', 'basins'].map(layerId => 
              selectedBoundaryLayers.has(layerId) && (
                <StableWMSLayer
                  key={`boundary-${layerId}`}
                  url={MAP_CONFIG.mapcacheWMSUrl}
                  layers={layerId}
                  transparent={true}
                  format="image/png"
                  version="1.1.0"
                  zIndex={layerId === 'rivers' ? 50 : 200}
                  layerConfig={{ needsDate: false }}
                />
              )
            )}
            
            {/* Admin layers with highest z-index to ensure they're always on top */}
            {['admin_level_1', 'admin_level_2'].map((adminLayer, index) => 
              selectedBoundaryLayers.has(adminLayer) && (
                <StableWMSLayer
                  key={`boundary-${adminLayer}-top`}
                  url={MAP_CONFIG.mapcacheWMSUrl}
                  layers={adminLayer}
                  transparent={true}
                  format="image/png"
                  version="1.1.0"
                  zIndex={400 + index}
                  layerConfig={{ needsDate: false }}
                />
              )
            )}
            
            <LayersControl position="topright">
              {BASE_MAPS.map((basemap) => (
                <LayersControl.BaseLayer
                  key={basemap.name}
                  name={basemap.name}
                  checked={basemap.name === "ICPAC"}
                >
                  <TileLayer
                    url={basemap.url}
                    attribution={basemap.attribution}
                  />
                </LayersControl.BaseLayer>
              ))}
              
              {/* Boundary layers in layer control */}
              {BOUNDARY_LAYERS.map((layer) => (
                <LayersControl.Overlay
                  key={layer.layer}
                  name={layer.name}
                  checked={selectedBoundaryLayers.has(layer.layer)}
                >
                  <WMSTileLayer
                    url={MAP_CONFIG.mapserverWMSUrl}
                    layers={layer.layer}
                    format="image/png"
                    transparent={true}
                    version="1.1.0"
                    eventHandlers={{
                      add: () => setSelectedBoundaryLayers(prev => new Set([...prev, layer.layer])),
                      remove: () => {
                        if (layer.layer !== 'admin_level_1' && layer.layer !== 'rivers') {
                          setSelectedBoundaryLayers(prev => {
                            const newLayers = new Set(prev);
                            newLayers.delete(layer.layer);
                            return newLayers;
                          });
                        }
                      }
                    }}
                  />
                </LayersControl.Overlay>
              ))}
            </LayersControl>
            
            {showMonitoringStations && monitoringData?.features && (
              <MarkerClusterGroup
                maxClusterRadius={50}
                disableClusteringAtZoom={15}
                spiderfyOnMaxZoom={true}
                showCoverageOnHover={false}
                spiderLegPolylineOptions={{ weight: 1.5, color: '#222', opacity: 0.5 }}
                spiderfyDistanceMultiplier={1.5}
                iconCreateFunction={(cluster) => {
                  const markers = cluster.getAllChildMarkers();
                  const alertLevels = markers.map(marker => marker.alertStatus || 'Normal');
                  
                  // Count stations by alert level
                  const emergencyCount = alertLevels.filter(level => level === 'Emergency').length;
                  const alarmCount = alertLevels.filter(level => level === 'Alarm').length;
                  const warningCount = alertLevels.filter(level => level === 'Warning').length;
                  
                  // Determine highest severity and show count for that level
                  let alertStatus;
                  let displayCount;
                  
                  if (emergencyCount > 0) {
                    alertStatus = 'Emergency';
                    displayCount = emergencyCount;
                  } else if (alarmCount > 0) {
                    alertStatus = 'Alarm';
                    displayCount = alarmCount;
                  } else if (warningCount > 0) {
                    alertStatus = 'Warning';
                    displayCount = warningCount;
                  } else {
                    alertStatus = 'Normal';
                    displayCount = cluster.getChildCount(); // Show total count for normal clusters
                  }
                  
                  // Create cluster icon with threshold-based count
                  const clusterIcon = createMarkerIcon(alertStatus, false, true, displayCount);
                  return clusterIcon;
                }}
              >
                <GeoJSON
                key={`monitoring-stations-${selectedStation?.properties?.SEC_NAME || "none"}`}
                data={{
                  ...monitoringData,
                  features: handleOverlappingPoints([...monitoringData.features])
                }}
                pointToLayer={(feature, latlng) => {
                  const isSelected =
                    selectedStation?.properties?.SEC_NAME ===
                    feature.properties.SEC_NAME;
                  
                  // Get current discharge from this station's own time series data
                  let currentDischarge = null;
                  
                  // Get the latest discharge value from this station's time series
                  const gfsData = feature.properties["time_series_discharge_simulated-gfs"];
                  const iconData = feature.properties["time_series_discharge_simulated-icon"];
                  
                  if (gfsData || iconData) {
                    let latestGfs = 0;
                    let latestIcon = 0;
                    
                    if (gfsData) {
                      const gfsValues = gfsData.split(",").map(val => Number(val.trim()) || 0);
                      latestGfs = gfsValues[gfsValues.length - 1] || 0;
                    }
                    
                    if (iconData) {
                      const iconValues = iconData.split(",").map(val => Number(val.trim()) || 0);
                      latestIcon = iconValues[iconValues.length - 1] || 0;
                    }
                    
                    currentDischarge = Math.max(latestGfs, latestIcon);
                  }
                  
                  // Determine alert status based on thresholds
                  const alertStatus = getAlertStatus(feature, currentDischarge);
                  
                  // Create marker with appropriate icon
                  const marker = L.marker(latlng, {
                    icon: createMarkerIcon(alertStatus, isSelected)
                  });
                  
                  // Add alert status as a property for easy access
                  marker.alertStatus = alertStatus;
                  marker.currentDischarge = currentDischarge;
                  
                  return marker;
                }}
                onEachFeature={(feature, layer) => {
                  layer.on({ click: () => handleStationClick(feature) });
                  const props = feature.properties;
                  layer.bindPopup(
                    `<div class="station-popup">
                      <strong>${props.SEC_NAME || "Station"}</strong><br/>
                      <strong>Basin:</strong> ${props.BASIN || "N/A"}<br/>
                      <strong>Current Status:</strong> <span style="color: ${
                        layer.alertStatus === 'Emergency' ? '#9c27b0' :
                        layer.alertStatus === 'Alarm' ? '#f44336' :
                        layer.alertStatus === 'Warning' ? '#ffeb3b' : '#4caf50'
                      }; font-weight: bold;">${layer.alertStatus}</span><br/>
                      ${layer.currentDischarge ? `<strong>Current Discharge:</strong> ${layer.currentDischarge.toFixed(1)} m³/s<br/>` : ''}
                      <strong>Thresholds:</strong><br/>
                      &nbsp;&nbsp;Alert: ${(props.Q_THR1 || props.q_thr1) ? parseFloat(props.Q_THR1 || props.q_thr1).toFixed(2) : 'N/A'} m³/s<br/>
                      &nbsp;&nbsp;Alarm: ${(props.Q_THR2 || props.q_thr2) ? parseFloat(props.Q_THR2 || props.q_thr2).toFixed(2) : 'N/A'} m³/s<br/>
                      &nbsp;&nbsp;Emergency: ${(props.Q_THR3 || props.q_thr3) ? parseFloat(props.Q_THR3 || props.q_thr3).toFixed(2) : 'N/A'} m³/s
                    </div>`,
                  );
                }}
              />
              </MarkerClusterGroup>
            )}
            {showGeoFSM && geoFSMData?.features && (() => {
              // Deduplicate GeoSFM features by both station ID and location
              const uniqueStations = new Map();
              const uniqueLocations = new Map();
              
              geoFSMData.features.forEach(feature => {
                const stationId = feature.properties.Id;
                const coords = feature.geometry?.coordinates;
                
                if (coords) {
                  // Create a location key based on coordinates (rounded to avoid floating point issues)
                  const locationKey = `${coords[1].toFixed(6)}_${coords[0].toFixed(6)}`;
                  
                  // Only add if we haven't seen this station ID or location before
                  if (!uniqueStations.has(stationId) && !uniqueLocations.has(locationKey)) {
                    uniqueStations.set(stationId, feature);
                    uniqueLocations.set(locationKey, feature);
                  }
                }
              });
              
              const deduplicatedFeatures = Array.from(uniqueStations.values());
              
              return (
              <>
                <MarkerClusterGroup
                maxClusterRadius={30}
                disableClusteringAtZoom={13}
                spiderfyOnMaxZoom={false}
                showCoverageOnHover={false}
                zoomToBoundsOnClick={true}
                removeOutsideVisibleBounds={false}
                iconCreateFunction={(cluster) => {
                  const markers = cluster.getAllChildMarkers();
                  const alertLevels = markers.map(marker => marker.alertStatus || 'Normal');
                  
                  // Count stations by alert level
                  const emergencyCount = alertLevels.filter(level => level === 'Emergency').length;
                  const alarmCount = alertLevels.filter(level => level === 'Alarm').length;
                  const warningCount = alertLevels.filter(level => level === 'Warning').length;
                  
                  // Determine highest severity and show count for that level
                  let alertStatus;
                  let displayCount;
                  
                  if (emergencyCount > 0) {
                    alertStatus = 'Emergency';
                    displayCount = emergencyCount;
                  } else if (alarmCount > 0) {
                    alertStatus = 'Alarm';
                    displayCount = alarmCount;
                  } else if (warningCount > 0) {
                    alertStatus = 'Warning';
                    displayCount = warningCount;
                  } else {
                    alertStatus = 'Normal';
                    displayCount = cluster.getChildCount(); // Show total count for normal clusters
                  }
                  
                  // Create cluster icon with threshold-based count
                  const clusterIcon = createMarkerIcon(alertStatus, false, true, displayCount);
                  return clusterIcon;
                }}
              >
                <GeoJSON
                key={`geofsm-points-${deduplicatedFeatures.length}`}
                data={{
                  ...geoFSMData,
                  features: deduplicatedFeatures
                }}
                pointToLayer={(feature, latlng) => {
                  const isSelected =
                    selectedStation?.properties?.Id === feature.properties.Id;
                  
                  // For now, use Normal status for all GeoSFM stations
                  // In future, this could be enhanced with threshold-based status
                  const alertStatus = 'Normal';
                  
                  // Create marker with appropriate icon using same system as FloodProofs
                  const marker = L.marker(latlng, {
                    icon: createMarkerIcon(alertStatus, isSelected)
                  });
                  
                  return marker;
                }}
                onEachFeature={(feature, layer) => {
                  const props = feature.properties;
                  layer.bindPopup(
                    `<div class="geofsm-popup"><strong>${props.Name || "GeoFSM Point"}</strong><br/>Description: ${props.Descriptio || "N/A"}<br/>Gridcode: ${props.Gridcode || "N/A"}<br/>Latitude: ${props.Y?.toFixed(4) || "N/A"}°N<br/>Longitude: ${props.X?.toFixed(4) || "N/A"}°E<br/>ID: ${props.Id || "N/A"}</div>`,
                  );
                  layer.on({ click: () => handleStationClick(feature) });
                }}
              />
              </MarkerClusterGroup>
              </>
              );
            })()}
            
            {/* IBEW Popup Handler - replaces old FeatureInfoHandler */}
            <IBEWPopupHandler
              selectedLayers={selectedLayers}
              selectedDate={selectedDate}
              mapConfig={MAP_CONFIG}
            />
            
          </MapContainer>
          
          {/* Alert Status Legend */}
          {monitoringData?.features && (
            <div className="alert-status-legend" style={{
              position: 'absolute',
              bottom: '20px',
              left: '20px',
              backgroundColor: 'white',
              border: '1px solid #ccc',
              borderRadius: '8px',
              padding: '12px',
              boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
              fontSize: '12px',
              zIndex: 1000,
              minWidth: '150px'
            }}>
              <div style={{ fontWeight: 'bold', marginBottom: '8px', fontSize: '13px' }}>
                FP_EA
              </div>
              {(() => {
                const stats = calculateThresholdStats(monitoringData);
                
                // Count GeoSFM stations if available
                const geoFSMCount = geoFSMData?.features ? 
                  new Set(geoFSMData.features.map(f => f.properties.Id)).size : 0;
                
                return (
                  <>
                    <div style={{ display: 'flex', alignItems: 'center', marginBottom: '4px' }}>
                      <img 
                        src="/assets/map-markers/Normal.svg" 
                        alt="Normal" 
                        style={{ width: '16px', height: '16px', marginRight: '8px' }}
                      />
                      <span>Normal</span>
                      <span style={{ marginLeft: 'auto', fontWeight: 'bold' }}>
                        {stats.normal + (showGeoFSM ? geoFSMCount : 0)}
                      </span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', marginBottom: '4px' }}>
                      <img 
                        src="/assets/map-markers/Warning.svg" 
                        alt="Alert" 
                        style={{ width: '16px', height: '16px', marginRight: '8px' }}
                      />
                      <span>Alert</span>
                      <span style={{ marginLeft: 'auto', fontWeight: 'bold' }}>{stats.warning}</span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', marginBottom: '4px' }}>
                      <img 
                        src="/assets/map-markers/Alarm.svg" 
                        alt="Alarm" 
                        style={{ width: '16px', height: '16px', marginRight: '8px' }}
                      />
                      <span>Alarm</span>
                      <span style={{ marginLeft: 'auto', fontWeight: 'bold' }}>{stats.alarm}</span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', marginBottom: '4px' }}>
                      <img 
                        src="/assets/map-markers/Emergency.svg" 
                        alt="Emergency" 
                        style={{ width: '16px', height: '16px', marginRight: '8px' }}
                      />
                      <span>Emergency</span>
                      <span style={{ marginLeft: 'auto', fontWeight: 'bold' }}>{stats.emergency}</span>
                    </div>
                    {showGeoFSM && geoFSMCount > 0 && (
                      <div style={{ 
                        marginTop: '8px', 
                        paddingTop: '8px', 
                        borderTop: '1px solid #eee',
                        fontSize: '11px',
                        color: '#666'
                      }}>
                        Includes {geoFSMCount} GeoSFM stations
                      </div>
                    )}
                  </>
                );
              })()}
            </div>
          )}
          
          {/* Temporarily disabled legend until repaired */}
          {/* {activeLegend && (
            <div className="map-legend" style={{ 
              position: 'absolute', 
              bottom: '20px', 
              right: '20px', 
              backgroundColor: 'white', 
              padding: '15px', 
              borderRadius: '8px',
              boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
              zIndex: 1000,
              maxWidth: '300px'
            }}>
              <MapLegend
                legendUrl={activeLegend}
                title={
                  [...hazardLayersWithDate, ...IMPACT_LAYERS, ...IBEW_LAYERS, ...BOUNDARY_LAYERS].find(
                    (layer) => layer.legend === activeLegend,
                  )?.name || "Legend"
                }
              />
            </div>
          )} */}
        </div>
        {showChart && (
          <div className="bottom-panel" style={{
            position: 'fixed',
            bottom: panelPosition.y ? 'auto' : '30px',
            top: panelPosition.y ? `${panelPosition.y}px` : 'auto',
            left: `${350 + panelPosition.x}px`,
            right: (panelPosition.x || panelPosition.y) ? 'auto' : '0px',
            width: (panelPosition.x || panelPosition.y) ? `${panelWidth}px` : 'auto',
            height: `${panelHeight}px`,
            backgroundColor: 'white',
            border: '1px solid #ddd',
            borderBottom: 'none',
            borderTop: '2px solid #1B6840',
            boxShadow: '0 -4px 12px rgba(0, 0, 0, 0.15)',
            zIndex: 1100,
            display: 'block',
            borderRadius: (panelPosition.x || panelPosition.y) ? '8px' : '0'
          }}>
            {/* Resize Handles - only show when panel is dragged/floating */}
            {(panelPosition.x || panelPosition.y) && (
              <>
                {/* Top */}
                <div
                  onMouseDown={(e) => handleResizeStart('top', e)}
                  style={{
                    position: 'absolute',
                    top: '-4px',
                    left: '8px',
                    right: '8px',
                    height: '8px',
                    cursor: 'ns-resize',
                    backgroundColor: 'transparent',
                    zIndex: 902
                  }}
                />
                {/* Bottom */}
                <div
                  onMouseDown={(e) => handleResizeStart('bottom', e)}
                  style={{
                    position: 'absolute',
                    bottom: '-4px',
                    left: '8px',
                    right: '8px',
                    height: '8px',
                    cursor: 'ns-resize',
                    backgroundColor: 'transparent',
                    zIndex: 902
                  }}
                />
                {/* Left */}
                <div
                  onMouseDown={(e) => handleResizeStart('left', e)}
                  style={{
                    position: 'absolute',
                    left: '-4px',
                    top: '8px',
                    bottom: '8px',
                    width: '8px',
                    cursor: 'ew-resize',
                    backgroundColor: 'transparent',
                    zIndex: 902
                  }}
                />
                {/* Right */}
                <div
                  onMouseDown={(e) => handleResizeStart('right', e)}
                  style={{
                    position: 'absolute',
                    right: '-4px',
                    top: '8px',
                    bottom: '8px',
                    width: '8px',
                    cursor: 'ew-resize',
                    backgroundColor: 'transparent',
                    zIndex: 902
                  }}
                />
                {/* Top-Left Corner */}
                <div
                  onMouseDown={(e) => handleResizeStart('top-left', e)}
                  style={{
                    position: 'absolute',
                    top: '-4px',
                    left: '-4px',
                    width: '12px',
                    height: '12px',
                    cursor: 'nw-resize',
                    backgroundColor: 'transparent',
                    zIndex: 903
                  }}
                />
                {/* Top-Right Corner */}
                <div
                  onMouseDown={(e) => handleResizeStart('top-right', e)}
                  style={{
                    position: 'absolute',
                    top: '-4px',
                    right: '-4px',
                    width: '12px',
                    height: '12px',
                    cursor: 'ne-resize',
                    backgroundColor: 'transparent',
                    zIndex: 903
                  }}
                />
                {/* Bottom-Left Corner */}
                <div
                  onMouseDown={(e) => handleResizeStart('bottom-left', e)}
                  style={{
                    position: 'absolute',
                    bottom: '-4px',
                    left: '-4px',
                    width: '12px',
                    height: '12px',
                    cursor: 'sw-resize',
                    backgroundColor: 'transparent',
                    zIndex: 903
                  }}
                />
                {/* Bottom-Right Corner */}
                <div
                  onMouseDown={(e) => handleResizeStart('bottom-right', e)}
                  style={{
                    position: 'absolute',
                    bottom: '-4px',
                    right: '-4px',
                    width: '12px',
                    height: '12px',
                    cursor: 'se-resize',
                    backgroundColor: 'transparent',
                    zIndex: 903
                  }}
                />
              </>
            )}
            
            {/* Original resize handle for docked position */}
            {!panelPosition.x && !panelPosition.y && (
              <div
                onMouseDown={(e) => handleResizeStart('top', e)}
                style={{
                  position: 'absolute',
                  top: '-5px',
                  left: '0',
                  right: '0',
                  height: '10px',
                  cursor: 'ns-resize',
                  backgroundColor: 'transparent',
                  zIndex: 901,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center'
                }}
              >
                <div style={{
                  width: '80px',
                  height: '4px',
                  backgroundColor: '#ccc',
                  borderRadius: '2px',
                  transition: 'background-color 0.2s'
                }} 
                onMouseEnter={(e) => e.target.style.backgroundColor = '#999'}
                onMouseLeave={(e) => e.target.style.backgroundColor = '#ccc'}
                />
              </div>
            )}
            <div 
              className="chart-header" 
              onMouseDown={handleDragStart}
              style={{
                cursor: 'move',
                userSelect: 'none',
                background: 'linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%)',
                borderBottom: '1px solid #ddd'
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <div style={{ 
                  display: 'flex', 
                  flexDirection: 'column', 
                  gap: '2px',
                  opacity: 0.6 
                }}>
                  <div style={{ width: '4px', height: '4px', backgroundColor: '#666', borderRadius: '50%' }}></div>
                  <div style={{ width: '4px', height: '4px', backgroundColor: '#666', borderRadius: '50%' }}></div>
                  <div style={{ width: '4px', height: '4px', backgroundColor: '#666', borderRadius: '50%' }}></div>
                </div>
                <h5 style={{ margin: 0 }}>
                  {selectedStation?.properties?.SEC_NAME ||
                    (chartType === "riverdepth" || chartType === "streamflow"
                      ? `${selectedStation?.properties?.Name || selectedStation?.properties?.Descriptio || 'GeoSFM Station'} - ${geoFSMDataType === 'riverdepth' ? 'River Depth' : 'Streamflow'}`
                      : "Discharge Forecast")}
                </h5>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                {/* Chart Type Filter for GeoSFM */}
                {(chartType === "riverdepth" || chartType === "streamflow") && (
                  <div 
                    className="chart-controls" 
                    style={{ zIndex: 1000, position: 'relative' }}
                    onMouseDown={(e) => e.stopPropagation()}
                    onClick={(e) => e.stopPropagation()}
                  >
                    <select
                      value={geoFSMDataType}
                      onChange={(e) => {
                        setGeoFSMDataType(e.target.value);
                      }}
                      onMouseDown={(e) => {
                        e.stopPropagation();
                      }}
                      onClick={(e) => {
                        e.stopPropagation();
                      }}
                      onMouseEnter={(e) => {
                        e.target.style.backgroundColor = "#FFCC80";
                        e.target.style.borderColor = "#E65100";
                      }}
                      onMouseLeave={(e) => {
                        e.target.style.backgroundColor = "#FFF3E0";
                        e.target.style.borderColor = "#FF9800";
                      }}
                      style={{ 
                        marginRight: "10px", 
                        padding: "4px 8px",
                        border: "1px solid #FF9800",
                        borderRadius: "3px",
                        backgroundColor: "#FFF3E0",
                        color: "#E65100",
                        fontWeight: "500",
                        minWidth: "120px",
                        fontSize: "11px",
                        cursor: "pointer",
                        zIndex: 1001,
                        position: "relative",
                        pointerEvents: "auto",
                        boxShadow: "0 1px 2px rgba(0,0,0,0.1)",
                        transition: "all 0.2s ease"
                      }}
                    >
                      <option value="riverdepth">River Depth</option>
                      <option value="streamflow">Streamflow</option>
                    </select>
                  </div>
                )}
                
                {/* Series Filter for FloodProofs */}
                {chartType === "discharge" && (
                  <div 
                    className="chart-controls" 
                    style={{ zIndex: 1000, position: 'relative' }}
                    onMouseDown={(e) => e.stopPropagation()}
                    onClick={(e) => e.stopPropagation()}
                  >
                    <select
                      value={selectedSeries}
                      onChange={(e) => setSelectedSeries(e.target.value)}
                      onMouseDown={(e) => {
                        e.stopPropagation();
                      }}
                      onClick={(e) => {
                        e.stopPropagation();
                      }}
                      onMouseEnter={(e) => {
                        e.target.style.backgroundColor = "#FFCC80";
                        e.target.style.borderColor = "#E65100";
                      }}
                      onMouseLeave={(e) => {
                        e.target.style.backgroundColor = "#FFF3E0";
                        e.target.style.borderColor = "#FF9800";
                      }}
                      style={{ 
                        marginRight: "10px", 
                        padding: "4px 8px",
                        border: "1px solid #FF9800",
                        borderRadius: "3px",
                        backgroundColor: "#FFF3E0",
                        color: "#E65100",
                        fontWeight: "500",
                        minWidth: "120px",
                        fontSize: "11px",
                        cursor: "pointer",
                        zIndex: 1001,
                        position: "relative",
                        pointerEvents: "auto",
                        boxShadow: "0 1px 2px rgba(0,0,0,0.1)",
                        transition: "all 0.2s ease"
                      }}
                    >
                      <option value="both">Both GFS & ICON</option>
                      <option value="gfs">GFS Only</option>
                      <option value="icon">ICON Only</option>
                    </select>
                  </div>
                )}
                
                {/* Export buttons */}
                <button
                  onClick={() => {
                    if (chartType === "riverdepth" || chartType === "streamflow") {
                      const stationName = selectedStation?.properties?.Name || selectedStation?.properties?.Descriptio || 'GeoSFM Station';
                      const csvData = geoFSMTimeSeriesData.map(item => ({
                        Date: new Date(item.timestamp).toISOString().split('T')[0],
                        [`${chartType === 'riverdepth' ? 'River Depth' : 'Streamflow'} (${chartType === 'riverdepth' ? 'm' : 'm³/s'})`]: item[chartType === 'riverdepth' ? 'depth' : 'streamflow'] || ''
                      }));
                      const headers = Object.keys(csvData[0]).join(',');
                      const csvContent = [
                        `# ${stationName} - ${chartType}`,
                        `# Generated on: ${new Date().toLocaleString()}`,
                        headers,
                        ...csvData.map(row => Object.values(row).join(','))
                      ].join('\n');
                      const blob = new Blob([csvContent], { type: 'text/csv' });
                      const url = window.URL.createObjectURL(blob);
                      const a = document.createElement('a');
                      a.href = url;
                      a.download = `${stationName}_${chartType}.csv`;
                      a.click();
                      window.URL.revokeObjectURL(url);
                    } else {
                      const stationName = selectedStation?.properties?.SEC_NAME || 'FloodProofs Station';
                      const csvData = timeSeriesData.map(item => ({
                        Date: item.time.toISOString().split('T')[0],
                        'GFS Forecast (m³/s)': item.gfs || '',
                        'ICON Forecast (m³/s)': item.icon || ''
                      }));
                      const headers = Object.keys(csvData[0]).join(',');
                      const csvContent = [
                        `# ${stationName} - discharge_forecast`,
                        `# Generated on: ${new Date().toLocaleString()}`,
                        headers,
                        ...csvData.map(row => Object.values(row).join(','))
                      ].join('\n');
                      const blob = new Blob([csvContent], { type: 'text/csv' });
                      const url = window.URL.createObjectURL(blob);
                      const a = document.createElement('a');
                      a.href = url;
                      a.download = `${stationName}_discharge_forecast.csv`;
                      a.click();
                      window.URL.revokeObjectURL(url);
                    }
                  }}
                  style={{
                    padding: '4px 8px',
                    backgroundColor: '#28a745',
                    color: 'white',
                    border: 'none',
                    borderRadius: '3px',
                    fontSize: '10px',
                    cursor: 'pointer',
                    boxShadow: '0 1px 2px rgba(0,0,0,0.1)'
                  }}
                >
                  📊 CSV
                </button>
                
                <button
                  onClick={() => {
                    // FloodProofs: Create professional 3-chart layout
                    if (chartType === "discharge" && timeSeriesData && timeSeriesData.length > 0) {
                      const canvas = document.createElement('canvas');
                      const ctx = canvas.getContext('2d');
                      
                      canvas.width = 1200;
                      canvas.height = 900;
                      
                      // Fill background
                      ctx.fillStyle = 'white';
                      ctx.fillRect(0, 0, canvas.width, canvas.height);
                      
                      const stationName = selectedStation?.properties?.SEC_NAME || 'FloodProofs Station';
                      
                      // Header section
                      ctx.fillStyle = '#f8f9fa';
                      ctx.fillRect(0, 0, canvas.width, 80);
                      ctx.strokeStyle = '#dee2e6';
                      ctx.lineWidth = 1;
                      ctx.strokeRect(0, 0, canvas.width, canvas.height);
                      ctx.strokeRect(0, 0, canvas.width, 80);
                      
                      // Title
                      ctx.fillStyle = '#1B6840';
                      ctx.font = 'bold 20px Arial';
                      ctx.fillText(`${stationName} - Discharge Forecast Analysis`, 20, 25);
                      
                      // Station details
                      ctx.fillStyle = '#333';
                      ctx.font = '12px Arial';
                      const basin = selectedStation?.properties?.BASIN || 'N/A';
                      const area = selectedStation?.properties?.AREA || 'N/A';
                      const lat = selectedStation?.properties?.latitude?.toFixed(4) || 'N/A';
                      const lng = selectedStation?.properties?.longitude?.toFixed(4) || 'N/A';
                      
                      ctx.fillText(`Basin: ${basin} | Area: ${area} km² | Location: ${lat}°N, ${lng}°E`, 20, 45);
                      
                      // Thresholds
                      const alertThreshold = selectedStation?.properties?.Q_THR1 || 'N/A';
                      const alarmThreshold = selectedStation?.properties?.Q_THR2 || 'N/A';
                      const emergencyThreshold = selectedStation?.properties?.Q_THR3 || 'N/A';
                      
                      ctx.fillStyle = '#ff9800';
                      ctx.fillText(`Alert: ${alertThreshold} m³/s`, 20, 62);
                      ctx.fillStyle = '#f44336';
                      ctx.fillText(`| Alarm: ${alarmThreshold} m³/s`, 150, 62);
                      ctx.fillStyle = '#d32f2f';
                      ctx.fillText(`| Emergency: ${emergencyThreshold} m³/s`, 300, 62);
                      
                      // Branding
                      ctx.fillStyle = '#1B6840';
                      ctx.font = 'bold 14px Arial';
                      ctx.fillText('East Africa Flood Watch | IGAD-ICPAC', canvas.width - 320, 25);
                      ctx.fillStyle = '#666';
                      ctx.font = '10px Arial';
                      ctx.fillText(`Generated: ${new Date().toLocaleString()}`, canvas.width - 200, 45);
                      
                      // Chart dimensions
                      const chartWidth = 540;
                      const chartHeight = 240;
                      const margin = { top: 40, right: 40, bottom: 60, left: 80 };
                      
                      // Helper function to draw professional chart
                      const drawProfessionalChart = (x, y, data, title, isLine = true, modelKey = null) => {
                        // Chart background
                        ctx.fillStyle = 'white';
                        ctx.fillRect(x, y, chartWidth, chartHeight);
                        ctx.strokeStyle = '#e0e0e0';
                        ctx.lineWidth = 1;
                        ctx.strokeRect(x, y, chartWidth, chartHeight);
                        
                        // Plot area
                        const plotX = x + margin.left;
                        const plotY = y + margin.top;
                        const plotWidth = chartWidth - margin.left - margin.right;
                        const plotHeight = chartHeight - margin.top - margin.bottom;
                        
                        // Title
                        ctx.fillStyle = '#333';
                        ctx.font = 'bold 14px Arial';
                        ctx.textAlign = 'center';
                        ctx.fillText(title, x + chartWidth / 2, y + 20);
                        ctx.textAlign = 'left';
                        
                        if (isLine) {
                          // Line chart for individual models
                          const maxValue = Math.max(...data.map(d => d[modelKey]));
                          const yScale = plotHeight / (maxValue * 1.1);
                          const xScale = plotWidth / (data.length - 1);
                          
                          // Grid lines
                          ctx.strokeStyle = '#f0f0f0';
                          ctx.lineWidth = 1;
                          for (let i = 0; i <= 5; i++) {
                            const gridY = plotY + plotHeight - (i * plotHeight / 5);
                            ctx.beginPath();
                            ctx.moveTo(plotX, gridY);
                            ctx.lineTo(plotX + plotWidth, gridY);
                            ctx.stroke();
                          }
                          
                          // Y-axis
                          ctx.strokeStyle = '#333';
                          ctx.lineWidth = 2;
                          ctx.beginPath();
                          ctx.moveTo(plotX, plotY);
                          ctx.lineTo(plotX, plotY + plotHeight);
                          ctx.stroke();
                          
                          // X-axis
                          ctx.beginPath();
                          ctx.moveTo(plotX, plotY + plotHeight);
                          ctx.lineTo(plotX + plotWidth, plotY + plotHeight);
                          ctx.stroke();
                          
                          // Y-axis labels
                          ctx.fillStyle = '#666';
                          ctx.font = '10px Arial';
                          ctx.textAlign = 'right';
                          for (let i = 0; i <= 5; i++) {
                            const value = (maxValue * i) / 5;
                            const labelY = plotY + plotHeight - (i * plotHeight / 5);
                            ctx.fillText(value.toFixed(1), plotX - 10, labelY + 3);
                          }
                          
                          // Y-axis title
                          ctx.save();
                          ctx.translate(plotX - 50, plotY + plotHeight / 2);
                          ctx.rotate(-Math.PI / 2);
                          ctx.font = 'bold 12px Arial';
                          ctx.textAlign = 'center';
                          ctx.fillText('Discharge (m³/s)', 0, 0);
                          ctx.restore();
                          
                          // X-axis labels (dates)
                          ctx.textAlign = 'center';
                          ctx.font = '9px Arial';
                          data.forEach((point, i) => {
                            if (i % Math.ceil(data.length / 6) === 0) {
                              const labelX = plotX + (i * xScale);
                              ctx.save();
                              ctx.translate(labelX, plotY + plotHeight + 15);
                              ctx.rotate(-Math.PI / 6);
                              ctx.fillText(point.time.toLocaleDateString('en-GB'), 0, 0);
                              ctx.restore();
                            }
                          });
                          
                          // Draw line
                          const color = modelKey === 'gfs' ? '#1f77b4' : '#ff7f0e';
                          ctx.strokeStyle = color;
                          ctx.lineWidth = 3;
                          ctx.beginPath();
                          
                          data.forEach((point, i) => {
                            const pointX = plotX + (i * xScale);
                            const pointY = plotY + plotHeight - (point[modelKey] * yScale);
                            
                            if (i === 0) ctx.moveTo(pointX, pointY);
                            else ctx.lineTo(pointX, pointY);
                          });
                          ctx.stroke();
                          
                          // Draw points
                          ctx.fillStyle = color;
                          data.forEach((point, i) => {
                            const pointX = plotX + (i * xScale);
                            const pointY = plotY + plotHeight - (point[modelKey] * yScale);
                            ctx.beginPath();
                            ctx.arc(pointX, pointY, 3, 0, 2 * Math.PI);
                            ctx.fill();
                          });
                        } else {
                          // Bar chart for comparison
                          const recentData = data.slice(-7);
                          const maxValue = Math.max(...recentData.flatMap(d => [d.gfs, d.icon]));
                          const yScale = plotHeight / (maxValue * 1.1);
                          const barGroupWidth = plotWidth / recentData.length;
                          const barWidth = barGroupWidth * 0.35;
                          
                          // Grid lines
                          ctx.strokeStyle = '#f0f0f0';
                          ctx.lineWidth = 1;
                          for (let i = 0; i <= 5; i++) {
                            const gridY = plotY + plotHeight - (i * plotHeight / 5);
                            ctx.beginPath();
                            ctx.moveTo(plotX, gridY);
                            ctx.lineTo(plotX + plotWidth, gridY);
                            ctx.stroke();
                          }
                          
                          // Axes
                          ctx.strokeStyle = '#333';
                          ctx.lineWidth = 2;
                          ctx.beginPath();
                          ctx.moveTo(plotX, plotY);
                          ctx.lineTo(plotX, plotY + plotHeight);
                          ctx.moveTo(plotX, plotY + plotHeight);
                          ctx.lineTo(plotX + plotWidth, plotY + plotHeight);
                          ctx.stroke();
                          
                          // Y-axis labels
                          ctx.fillStyle = '#666';
                          ctx.font = '10px Arial';
                          ctx.textAlign = 'right';
                          for (let i = 0; i <= 5; i++) {
                            const value = (maxValue * i) / 5;
                            const labelY = plotY + plotHeight - (i * plotHeight / 5);
                            ctx.fillText(value.toFixed(1), plotX - 10, labelY + 3);
                          }
                          
                          // Y-axis title
                          ctx.save();
                          ctx.translate(plotX - 50, plotY + plotHeight / 2);
                          ctx.rotate(-Math.PI / 2);
                          ctx.font = 'bold 12px Arial';
                          ctx.textAlign = 'center';
                          ctx.fillText('Discharge (m³/s)', 0, 0);
                          ctx.restore();
                          
                          // Draw bars
                          recentData.forEach((dataPoint, i) => {
                            const groupX = plotX + (i * barGroupWidth) + barGroupWidth * 0.1;
                            
                            // GFS bar
                            const gfsHeight = dataPoint.gfs * yScale;
                            ctx.fillStyle = '#1f77b4';
                            ctx.fillRect(groupX, plotY + plotHeight - gfsHeight, barWidth, gfsHeight);
                            
                            // ICON bar
                            const iconHeight = dataPoint.icon * yScale;
                            ctx.fillStyle = '#ff7f0e';
                            ctx.fillRect(groupX + barWidth + 2, plotY + plotHeight - iconHeight, barWidth, iconHeight);
                            
                            // Date label
                            ctx.fillStyle = '#666';
                            ctx.font = '9px Arial';
                            ctx.textAlign = 'center';
                            ctx.save();
                            ctx.translate(groupX + barWidth, plotY + plotHeight + 15);
                            ctx.rotate(-Math.PI / 6);
                            ctx.fillText(dataPoint.time.toLocaleDateString('en-GB'), 0, 0);
                            ctx.restore();
                          });
                        }
                        ctx.textAlign = 'left';
                      };
                      
                      // Draw charts
                      drawProfessionalChart((canvas.width - chartWidth) / 2, 100, timeSeriesData, 'Model Comparison (Last 7 Days)', false);
                      drawProfessionalChart(30, 380, timeSeriesData, 'GFS Model Forecast', true, 'gfs');
                      drawProfessionalChart(630, 380, timeSeriesData, 'ICON Model Forecast', true, 'icon');
                      
                      // Legend
                      const legendY = 650;
                      ctx.fillStyle = '#1f77b4';
                      ctx.fillRect(canvas.width / 2 - 80, legendY, 15, 15);
                      ctx.fillStyle = '#333';
                      ctx.font = '12px Arial';
                      ctx.fillText('GFS Model', canvas.width / 2 - 60, legendY + 12);
                      
                      ctx.fillStyle = '#ff7f0e';
                      ctx.fillRect(canvas.width / 2 + 10, legendY, 15, 15);
                      ctx.fillText('ICON Model', canvas.width / 2 + 30, legendY + 12);
                      
                      const link = document.createElement('a');
                      link.download = `${stationName}_forecast_analysis.png`;
                      link.href = canvas.toDataURL();
                      link.click();
                      return;
                    }
                    
                    // GeoSFM: Professional vertical stacked layout (depth and streamflow)
                    if ((chartType === "riverdepth" || chartType === "streamflow") && geoFSMTimeSeriesData && geoFSMTimeSeriesData.length > 0) {
                      const canvas = document.createElement('canvas');
                      const ctx = canvas.getContext('2d');
                      
                      canvas.width = 1000;
                      canvas.height = 900;
                      
                      // Fill background
                      ctx.fillStyle = 'white';
                      ctx.fillRect(0, 0, canvas.width, canvas.height);
                      
                      const stationName = selectedStation?.properties?.Name || selectedStation?.properties?.Descriptio || 'GeoSFM Station';
                      
                      // Header section with centered branding
                      ctx.fillStyle = '#1B6840';
                      ctx.font = 'bold 24px Arial';
                      ctx.textAlign = 'center';
                      ctx.fillText('IGAD-ICPAC East Africa Flood Watch', canvas.width / 2, 30);
                      
                      // Station title
                      ctx.font = 'bold 18px Arial';
                      ctx.fillText(`${stationName} - GeoSFM Monitoring Data`, canvas.width / 2, 60);
                      
                      // Generation date
                      ctx.fillStyle = '#666';
                      ctx.font = '12px Arial';
                      ctx.fillText(`Generated: ${new Date().toLocaleDateString('en-GB', {day: 'numeric', month: 'long', year: 'numeric'})}`, canvas.width / 2, 80);
                      
                      ctx.textAlign = 'left';
                      
                      // Chart dimensions
                      const chartWidth = 900;
                      const chartHeight = 320;
                      const margin = { top: 60, right: 120, bottom: 80, left: 80 };
                      
                      // Helper function to draw professional GeoSFM chart with legend
                      const drawProfessionalGeoSFMChart = (x, y, dataKey, color, title, unit) => {
                        // Plot area
                        const plotX = x + margin.left;
                        const plotY = y + margin.top;
                        const plotWidth = chartWidth - margin.left - margin.right;
                        const plotHeight = chartHeight - margin.top - margin.bottom;
                        
                        // Title
                        ctx.fillStyle = '#333';
                        ctx.font = 'bold 16px Arial';
                        ctx.textAlign = 'center';
                        ctx.fillText(`${title} (${unit})`, x + chartWidth / 2, y + 25);
                        ctx.textAlign = 'left';
                        
                        // Get data values
                        const values = geoFSMTimeSeriesData.map(d => d[dataKey] || 0);
                        const maxValue = Math.max(...values);
                        const yScale = plotHeight / (maxValue * 1.1);
                        const xScale = plotWidth / (geoFSMTimeSeriesData.length - 1);
                        
                        // Grid lines
                        ctx.strokeStyle = '#f0f0f0';
                        ctx.lineWidth = 1;
                        for (let i = 0; i <= 6; i++) {
                          const gridY = plotY + plotHeight - (i * plotHeight / 6);
                          ctx.beginPath();
                          ctx.moveTo(plotX, gridY);
                          ctx.lineTo(plotX + plotWidth, gridY);
                          ctx.stroke();
                        }
                        
                        // Y-axis
                        ctx.strokeStyle = '#333';
                        ctx.lineWidth = 2;
                        ctx.beginPath();
                        ctx.moveTo(plotX, plotY);
                        ctx.lineTo(plotX, plotY + plotHeight);
                        ctx.stroke();
                        
                        // X-axis
                        ctx.beginPath();
                        ctx.moveTo(plotX, plotY + plotHeight);
                        ctx.lineTo(plotX + plotWidth, plotY + plotHeight);
                        ctx.stroke();
                        
                        // Y-axis labels
                        ctx.fillStyle = '#666';
                        ctx.font = '11px Arial';
                        ctx.textAlign = 'right';
                        for (let i = 0; i <= 6; i++) {
                          const value = (maxValue * i) / 6;
                          const labelY = plotY + plotHeight - (i * plotHeight / 6);
                          ctx.fillText(value.toFixed(1), plotX - 10, labelY + 4);
                        }
                        
                        // Y-axis title
                        ctx.save();
                        ctx.translate(plotX - 50, plotY + plotHeight / 2);
                        ctx.rotate(-Math.PI / 2);
                        ctx.font = 'bold 12px Arial';
                        ctx.textAlign = 'center';
                        ctx.fillText(`${title} (${unit})`, 0, 0);
                        ctx.restore();
                        
                        // X-axis labels (dates)
                        ctx.textAlign = 'center';
                        ctx.font = '10px Arial';
                        ctx.fillStyle = '#666';
                        geoFSMTimeSeriesData.forEach((point, i) => {
                          if (i % Math.ceil(geoFSMTimeSeriesData.length / 10) === 0) {
                            const labelX = plotX + (i * xScale);
                            const date = new Date(point.timestamp);
                            const dateStr = date.toLocaleDateString('en-GB', { day: '2-digit', month: 'short' });
                            ctx.fillText(dateStr, labelX, plotY + plotHeight + 15);
                          }
                        });
                        
                        // X-axis title
                        ctx.font = 'bold 12px Arial';
                        ctx.textAlign = 'center';
                        ctx.fillStyle = '#333';
                        ctx.fillText('Date', plotX + plotWidth / 2, plotY + plotHeight + 40);
                        
                        // Draw line
                        ctx.strokeStyle = color;
                        ctx.lineWidth = 3;
                        ctx.beginPath();
                        
                        geoFSMTimeSeriesData.forEach((point, i) => {
                          const pointX = plotX + (i * xScale);
                          const pointY = plotY + plotHeight - ((point[dataKey] || 0) * yScale);
                          
                          if (i === 0) ctx.moveTo(pointX, pointY);
                          else ctx.lineTo(pointX, pointY);
                        });
                        ctx.stroke();
                        
                        // Draw points
                        ctx.fillStyle = color;
                        geoFSMTimeSeriesData.forEach((point, i) => {
                          const pointX = plotX + (i * xScale);
                          const pointY = plotY + plotHeight - ((point[dataKey] || 0) * yScale);
                          ctx.beginPath();
                          ctx.arc(pointX, pointY, 3, 0, 2 * Math.PI);
                          ctx.fill();
                        });
                        
                        // Legend box
                        const legendX = plotX + plotWidth - 150;
                        const legendY = plotY + 20;
                        ctx.fillStyle = 'rgba(255, 255, 255, 0.9)';
                        ctx.fillRect(legendX, legendY, 130, 30);
                        ctx.strokeStyle = '#ddd';
                        ctx.lineWidth = 1;
                        ctx.strokeRect(legendX, legendY, 130, 30);
                        
                        // Legend line
                        ctx.strokeStyle = color;
                        ctx.lineWidth = 3;
                        ctx.beginPath();
                        ctx.moveTo(legendX + 10, legendY + 15);
                        ctx.lineTo(legendX + 30, legendY + 15);
                        ctx.stroke();
                        
                        // Legend text
                        ctx.fillStyle = '#333';
                        ctx.font = '12px Arial';
                        ctx.textAlign = 'left';
                        ctx.fillText(title, legendX + 35, legendY + 19);
                        
                        ctx.textAlign = 'left';
                      };
                      
                      // Draw charts vertically stacked
                      drawProfessionalGeoSFMChart(50, 120, 'depth', '#2196F3', 'River Depth', 'm');
                      drawProfessionalGeoSFMChart(50, 480, 'streamflow', '#FF6B35', 'Streamflow', 'm³/s');
                      
                      const link = document.createElement('a');
                      link.download = `${stationName}_geosfm_analysis.png`;
                      link.href = canvas.toDataURL();
                      link.click();
                      return;
                    }
                  }}
                  style={{
                    padding: '4px 8px',
                    backgroundColor: '#007bff',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    fontSize: '11px',
                    cursor: 'pointer'
                  }}
                >
                  📸 PNG
                </button>
                
                <button
                  className="close-button"
                  onClick={() => {
                    setShowChart(false);
                    setSelectedStation(null);
                    setTimeSeriesData([]);
                    setGeoFSMTimeSeriesData([]);
                  }}
                >
                  ×
                </button>
              </div>
            </div>
            <div className="chart-container" style={{ 
              height: `${Math.max(panelHeight - 45, 155)}px`, 
              width: '100%', 
              padding: '0 20px 10px 20px',
              overflow: 'hidden'
            }}>
              {chartType === "riverdepth" || chartType === "streamflow" ? (
                <GeoSFMChart
                  timeSeriesData={geoFSMTimeSeriesData}
                  dataType={geoFSMDataType}
                  stationName={selectedStation?.properties?.Name || selectedStation?.properties?.Descriptio || 'GeoSFM Station'}
                  height={Math.max(panelHeight - 65, 135)}
                />
              ) : (
                timeSeriesData && timeSeriesData.length > 0 ? (
                  <DischargeChart
                    timeSeriesData={timeSeriesData}
                    selectedSeries={selectedSeries}
                    stationName={selectedStation?.properties?.SEC_NAME || 'FloodProofs Station'}
                    height={Math.max(panelHeight - 65, 135)}
                  />
                ) : (
                  <div style={{ padding: '20px', textAlign: 'center' }}>
                    <p>Loading chart data... ({timeSeriesData?.length || 0} data points)</p>
                  </div>
                )
              )}
            </div>
          </div>
        )}
      </div>
      {/* Metadata Modal */}
      <MetadataModal
        show={showMetadataModal}
        handleClose={handleCloseMetadata}
        metadata={currentMetadata}
      />
    </div>
  );
};

export default MapViewer;