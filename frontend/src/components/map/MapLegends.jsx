import React, { useState, useEffect } from 'react';
import { filterPointsByCountry } from '../../utils/map/countryFilter';

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
        const gfsValues = gfsData.split(',').map(Number).filter(v => !isNaN(v));
        latestGfs = gfsValues.length > 0 ? gfsValues[gfsValues.length - 1] : 0;
      }
      
      if (iconData) {
        const iconValues = iconData.split(',').map(Number).filter(v => !isNaN(v));
        latestIcon = iconValues.length > 0 ? iconValues[iconValues.length - 1] : 0;
      }
      
      currentDischarge = Math.max(latestGfs, latestIcon);
    }
    
    // Get thresholds
    const q_thr1 = parseFloat(station.properties.Q_THR1 || station.properties.q_thr1 || 0);
    const q_thr2 = parseFloat(station.properties.Q_THR2 || station.properties.q_thr2 || 0);
    const q_thr3 = parseFloat(station.properties.Q_THR3 || station.properties.q_thr3 || 0);
    
    // Determine status
    let status = 'Normal';
    if (currentDischarge !== null && currentDischarge !== undefined && !isNaN(currentDischarge)) {
      if (!isNaN(q_thr3) && q_thr3 > 0 && currentDischarge >= q_thr3) status = 'Emergency';
      else if (!isNaN(q_thr2) && q_thr2 > 0 && currentDischarge >= q_thr2) status = 'Alarm';
      else if (!isNaN(q_thr1) && q_thr1 > 0 && currentDischarge >= q_thr1) status = 'Warning';
    } else {
      status = station.properties.status || station.properties.Status || 'Normal';
    }
    
    // Count the status
    const normalizedStatus = status.toLowerCase();
    if (normalizedStatus === 'emergency') stats.emergency++;
    else if (normalizedStatus === 'alarm') stats.alarm++;
    else if (normalizedStatus === 'warning' || normalizedStatus === 'alert') stats.warning++;
    else stats.normal++;
    
    stats.total++;
  });
  
  return stats;
};

// Alert Status Legend Component (FP_EA)
export const AlertStatusLegend = ({ monitoringData, geoFSMData, showGeoFSM }) => {
  if (!monitoringData?.features) return null;
  
  const stats = calculateThresholdStats(monitoringData);
  
  // Count GeoSFM stations if available
  const geoFSMCount = geoFSMData?.features ? 
    new Set(geoFSMData.features.map(f => f.properties.Id)).size : 0;
  
  return (
    <div className="absolute bottom-3 left-3 md:bottom-5 md:left-5 bg-white border border-gray-300 rounded-md md:rounded-lg p-1.5 md:p-3 shadow-md text-[10px] md:text-xs z-[1000] min-w-[120px] md:min-w-[150px]">
      <div className="font-bold mb-1 md:mb-2 text-xs md:text-sm">
        FP_EA
      </div>
      <div className="flex items-center mb-0.5 md:mb-1">
        <img
          src="/map-markers/Normal.svg"
          alt="Normal"
          className="w-3 h-3 md:w-4 md:h-4 mr-1 md:mr-2"
        />
        <span>Normal</span>
        <span className="ml-auto font-bold">
          {stats.normal + (showGeoFSM ? geoFSMCount : 0)}
        </span>
      </div>
      <div className="flex items-center mb-0.5 md:mb-1">
        <img
          src="/map-markers/Warning.svg"
          alt="Alert"
          className="w-3 h-3 md:w-4 md:h-4 mr-1 md:mr-2"
        />
        <span>Alert</span>
        <span className="ml-auto font-bold">{stats.warning}</span>
      </div>
      <div className="flex items-center mb-0.5 md:mb-1">
        <img
          src="/map-markers/Alarm.svg"
          alt="Alarm"
          className="w-3 h-3 md:w-4 md:h-4 mr-1 md:mr-2"
        />
        <span>Alarm</span>
        <span className="ml-auto font-bold">{stats.alarm}</span>
      </div>
      <div className="flex items-center mb-0.5 md:mb-1">
        <img
          src="/map-markers/Emergency.svg"
          alt="Emergency"
          className="w-3 h-3 md:w-4 md:h-4 mr-1 md:mr-2"
        />
        <span>Emergency</span>
        <span className="ml-auto font-bold">{stats.emergency}</span>
      </div>
      {showGeoFSM && geoFSMCount > 0 && (
        <div className="mt-1 md:mt-2 pt-1 md:pt-2 border-t border-gray-200 text-[9px] md:text-[11px] text-gray-600">
          Includes {geoFSMCount} GeoSFM stations
        </div>
      )}
    </div>
  );
};

// Multi-modal Legend Component
export const MultimodalLegend = ({ ensembleData, selectedCountry, adminBoundariesData }) => {
  // Calculate the filtered count (same logic as in EnsembleLayer)
  let displayCount = 0;

  if (ensembleData?.features) {
    if (!selectedCountry || selectedCountry === '') {
      // No filter - show all
      displayCount = ensembleData.features.length;
    } else if (selectedCountry === 'WHCA' && adminBoundariesData) {
      // WHCA Countries filter
      const whcaCountries = ['Uganda', 'Rwanda', 'South Sudan', 'Ethiopia', 'Sudan'];
      let combinedFeatures = [];

      whcaCountries.forEach(country => {
        const result = filterPointsByCountry(ensembleData, adminBoundariesData, country);
        if (result?.features) {
          combinedFeatures = [...combinedFeatures, ...result.features];
        }
      });

      // Remove duplicates
      const uniqueFeatures = Array.from(
        new Map(combinedFeatures.map(f => [f.properties.ID, f])).values()
      );
      displayCount = uniqueFeatures.length;
    } else if (adminBoundariesData) {
      // Single country filter
      const result = filterPointsByCountry(ensembleData, adminBoundariesData, selectedCountry);
      displayCount = result?.features?.length || 0;
    } else {
      // No admin data - show all
      displayCount = ensembleData.features.length;
    }
  }

  if (displayCount === 0) return null;

  return (
    <div className="absolute bottom-3 right-3 md:bottom-5 md:right-5 bg-white border border-gray-300 rounded-md md:rounded-lg p-1.5 md:p-3 shadow-md text-[10px] md:text-xs z-[1000] min-w-[120px] md:min-w-[150px]">
      <div className="font-bold mb-1 md:mb-2 text-xs md:text-sm">
        Multi-modal
      </div>
      <div className="flex items-center mb-0.5 md:mb-1">
        <svg
          width="16"
          height="20"
          viewBox="0 0 24 36"
          xmlns="http://www.w3.org/2000/svg"
          className="mr-1 md:mr-2"
          style={{ filter: 'drop-shadow(0 1px 2px rgba(0,0,0,0.3))' }}
        >
          <path
            d="M12 0C7.6 0 4 3.6 4 8c0 5.4 8 20 8 20s8-14.6 8-20c0-4.4-3.6-8-8-8z"
            fill="#9E9E9E"
            stroke="#9C27B0"
            strokeWidth="1.5"
          />
        </svg>
        <span>Stations</span>
        <span className="ml-auto font-bold">{displayCount}</span>
      </div>
    </div>
  );
};

// Map Legend Component
export const MapLegend = ({ legendUrl, title }) => {
  const [imageError, setImageError] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  
  // Reset states when legendUrl changes
  useEffect(() => {
    setImageError(false);
    setIsLoading(true);
  }, [legendUrl]);
  
  const needsCustomLegend = () =>
    title === "Hazard Map" ||
    title === "fp_inundation map" ||
    legendUrl?.includes("Alerts") ||
    title === "GeoSFM" ||
    title === "fp_hazards" ||
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
      <div className="bg-white border border-gray-300 rounded-md md:rounded-lg p-1.5 md:p-3 shadow-md">
        <h5 className="font-bold mb-1 md:mb-2 text-xs md:text-sm">{legendData.title}</h5>
        {legendData.items.map((item, index) => (
          <div
            key={index}
            className="flex items-center mb-1 md:mb-2"
          >
            <div
              className="w-4 h-4 md:w-6 md:h-6 mr-1 md:mr-2 border border-gray-300"
              style={{ backgroundColor: item.color }}
            />
            <span className="text-[10px] md:text-xs">{item.label}</span>
          </div>
        ))}
      </div>
    );
  }
  
  // Only show legend if we have a valid URL and no error
  if (!legendUrl || imageError) {
    return null;
  }

  return (
    <div className="bg-white border border-gray-300 rounded-md md:rounded-lg p-1.5 md:p-3 shadow-md">
      <h5 className="font-bold mb-1 md:mb-2 text-xs md:text-sm">{title}</h5>
      {isLoading && (
        <div className="p-1.5 md:p-2.5 text-center text-[10px] md:text-xs text-gray-600">
          Loading legend...
        </div>
      )}
      <img
        src={legendUrl}
        alt={`Legend for ${title}`}
        onLoad={() => setIsLoading(false)}
        onError={(e) => {
          setImageError(true);
          setIsLoading(false);
        }}
        className={`${isLoading ? 'hidden' : 'block'} max-w-full h-auto`}
      />
    </div>
  );
};
