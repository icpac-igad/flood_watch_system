/**
 * Monitoring Stations Layer Component
 * Renders monitoring stations as clustered markers with popups
 */

import React, { useState, useEffect } from 'react';
import { GeoJSON } from 'react-leaflet';
import MarkerClusterGroup from 'react-leaflet-cluster';
import L from 'leaflet';
import { getAlertStatus } from '../../../utils/map/alertStatus';
import { getMarkerIcon } from '../../../utils/map/markerIcons';
import { MonitoringData, MonitoringDataFeature, AlertStatus } from '../../../types/map.types';

interface MonitoringStationsLayerProps {
  data: MonitoringData | null;
  selectedDate: string | null;
  selectedCountry: string | null;
  selectedStation: MonitoringDataFeature | null;
  onStationClick: (feature: MonitoringDataFeature) => void;
  onGenerateReport: (feature: MonitoringDataFeature) => void;
}

export const MonitoringStationsLayer: React.FC<MonitoringStationsLayerProps> = ({
  data,
  selectedDate,
  selectedCountry,
  selectedStation,
  onStationClick,
  onGenerateReport
}) => {
  const [renderKey, setRenderKey] = useState(0);
  const [isReady, setIsReady] = useState(true);

  // Force remount when data changes to ensure markers update
  useEffect(() => {
    if (data) {
      // Unmount briefly to clear old markers
      setIsReady(false);

      // Remount with new data after a tiny delay
      setTimeout(() => {
        setRenderKey(prev => prev + 1);
        setIsReady(true);
      }, 10);
    }
  }, [data]); // Only depend on data, NOT renderKey!

  // Filter data by selected country
  const filteredData = React.useMemo(() => {
    if (!data?.features) return null;
    if (!selectedCountry) return data;

    const filteredFeatures = data.features.filter(feature => {
      const country = feature.properties.COUNTRY;
      if (!country) return false;
      return country.toLowerCase() === selectedCountry.toLowerCase();
    });

    return {
      ...data,
      features: filteredFeatures
    };
  }, [data, selectedCountry]);

  if (!filteredData?.features || filteredData.features.length === 0 || !isReady) {
    return null;
  }

  return (
    <MarkerClusterGroup
      key={`cluster-${renderKey}`}
      maxClusterRadius={50}
      disableClusteringAtZoom={15}
      spiderfyOnMaxZoom={false}
      showCoverageOnHover={false}
      spiderLegPolylineOptions={{ weight: 1.5, color: '#222', opacity: 0.5 }}
      spiderfyDistanceMultiplier={1.5}
      iconCreateFunction={(cluster) => {
        const markers = cluster.getAllChildMarkers();
        const alertLevels = markers.map((marker: any) => marker.alertStatus || 'Normal');

        // Count stations by alert level
        const emergencyCount = alertLevels.filter((level: string) => level === 'Emergency').length;
        const alarmCount = alertLevels.filter((level: string) => level === 'Alarm').length;
        const warningCount = alertLevels.filter((level: string) => level === 'Warning').length;

        // Determine highest severity (use balloon marker for clusters)
        let alertStatus: AlertStatus;

        if (emergencyCount > 0) {
          alertStatus = 'Emergency';
        } else if (alarmCount > 0) {
          alertStatus = 'Alarm';
        } else if (warningCount > 0) {
          alertStatus = 'Warning';
        } else {
          alertStatus = 'Normal';
        }

        // Return a larger balloon marker for the cluster (isCluster=true)
        return getMarkerIcon(alertStatus, true, markers.length, false);
      }}
    >
      <GeoJSON
        key={`monitoring-stations-${renderKey}`}
        data={filteredData as any}
        pointToLayer={(feature, latlng) => {
          const isSelected = selectedStation?.properties?.SEC_NAME === feature.properties.SEC_NAME;

          // Calculate current discharge the same way as the legend
          let currentDischarge = null;
          const gfsData = feature.properties["time_series_discharge_simulated-gfs"];
          const iconData = feature.properties["time_series_discharge_simulated-icon"];

          if (gfsData || iconData) {
            let latestGfs = 0;
            let latestIcon = 0;

            if (gfsData) {
              const gfsValues = gfsData.split(",").map((val: string) => Number(val.trim()) || 0);
              latestGfs = gfsValues[gfsValues.length - 1] || 0;
            }

            if (iconData) {
              const iconValues = iconData.split(",").map((val: string) => Number(val.trim()) || 0);
              latestIcon = iconValues[iconValues.length - 1] || 0;
            }

            currentDischarge = Math.max(latestGfs, latestIcon);
          }

          // Use the same alert status calculation as the legend for consistency
          const alertStatus = getAlertStatus(feature, currentDischarge);

          // Use balloon marker icon
          const markerIcon = getMarkerIcon(alertStatus, false, 0, isSelected);

          const marker: any = L.marker(latlng, {
            icon: markerIcon
          });

          // Store alert status for clustering
          marker.alertStatus = alertStatus;

          return marker;
        }}
        onEachFeature={(feature, layer) => {
          layer.on({ click: () => onStationClick(feature) });
          const props = feature.properties;

          // Recalculate discharge and alert status for popup
          const dischargeGFS = feature.properties["time_series_discharge_simulated-gfs"];
          let currentDischarge = 0;

          if (dischargeGFS) {
            const gfsValues = dischargeGFS.split(',').map((v: string) => parseFloat(v)).filter((v: number) => v !== -9998 && !isNaN(v));
            currentDischarge = gfsValues[gfsValues.length - 1] || 0;
          }

          // Calculate alert status based on thresholds
          let alertStatus = 'Normal';
          const alertThreshold = parseFloat(feature.properties.Q_THR1 || 0);
          const alarmThreshold = parseFloat(feature.properties.Q_THR2 || 0);
          const emergencyThreshold = parseFloat(feature.properties.Q_THR3 || 0);

          if (currentDischarge >= emergencyThreshold && emergencyThreshold > 0) {
            alertStatus = 'Emergency';
          } else if (currentDischarge >= alarmThreshold && alarmThreshold > 0) {
            alertStatus = 'Alarm';
          } else if (currentDischarge >= alertThreshold && alertThreshold > 0) {
            alertStatus = 'Warning';
          }

          const discharge = currentDischarge.toFixed(2);
          const popupContent = `
            <div class="station-popup">
              <strong>${props.SEC_NAME || "Station"}</strong><br/>
              <strong>Basin:</strong> ${props.BASIN || "N/A"}<br/>
              <strong>Status:</strong> ${alertStatus}<br/>
              <strong>Discharge:</strong> ${discharge} m³/s<br/>
              <strong>Thresholds:</strong><br/>
              &nbsp;&nbsp;Alert: ${alertThreshold.toFixed(1)} m³/s<br/>
              &nbsp;&nbsp;Alarm: ${alarmThreshold.toFixed(1)} m³/s<br/>
              &nbsp;&nbsp;Emergency: ${emergencyThreshold.toFixed(1)} m³/s<br/>
              <button
                id="generate-report-btn"
                style="margin-top: 10px; padding: 5px 15px; background-color: #1B6840; color: white; border: none; border-radius: 4px; cursor: pointer; font-weight: bold; width: 100%;"
                onmouseover="this.style.backgroundColor='#145432'"
                onmouseout="this.style.backgroundColor='#1B6840'"
              >
                📊 Generate Report
              </button>
            </div>`;

          const popup = L.popup({
            autoPan: true,
            autoPanPadding: [50, 50],
            maxWidth: 300,
            keepInView: true,
            autoPanPaddingTopLeft: [10, 100],
            autoPanPaddingBottomRight: [10, 10],
            offset: [0, -10]
          }).setContent(popupContent);
          layer.bindPopup(popup);

          // Add event listener when popup opens
          layer.on('popupopen', (e) => {
            // Adjust popup position based on marker location
            const map = e.target._map;
            const popupLatLng = e.popup.getLatLng();
            const point = map.latLngToContainerPoint(popupLatLng);
            const mapSize = map.getSize();

            // If marker is in top 30% of screen, open popup below marker
            if (point.y < mapSize.y * 0.3) {
              e.popup.options.offset = [0, 20]; // Offset downward
              e.popup.update();
            }

            // Attach report button handler
            const reportBtn = document.getElementById('generate-report-btn');
            if (reportBtn) {
              reportBtn.onclick = () => onGenerateReport(feature);
            }
          });
        }}
      />
    </MarkerClusterGroup>
  );
};
