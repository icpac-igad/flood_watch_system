/**
 * GeoSFM Layer Component
 * Renders GeoSFM forecast data as hexagons on the map
 */

import React, { useState, useEffect } from 'react';
import { GeoJSON } from 'react-leaflet';
import L from 'leaflet';

interface GeoSFMFeature {
  type: 'Feature';
  properties: any;
  geometry: any;
}

interface GeoSFMData {
  type: 'FeatureCollection';
  features: GeoSFMFeature[];
}

interface GeoSFMLayerProps {
  data: GeoSFMData | null;
  selectedDate: string | null;
}

export const GeoSFMLayer: React.FC<GeoSFMLayerProps> = ({
  data,
  selectedDate
}) => {
  const [renderKey, setRenderKey] = useState(0);
  const [isReady, setIsReady] = useState(true);

  // Force remount when data changes
  useEffect(() => {
    if (data) {
      // Unmount briefly to clear old features
      setIsReady(false);

      // Remount with new data
      setTimeout(() => {
        setRenderKey(prev => prev + 1);
        setIsReady(true);
      }, 10);
    }
  }, [data, renderKey]);

  if (!data?.features || data.features.length === 0 || !isReady) {
    return null;
  }

  return (
    <GeoJSON
      key={`geosfm-${renderKey}`}
      data={data}
      style={(feature) => {
        // Style hexagons based on flood probability or other properties
        const value = feature?.properties?.value || 0;

        // Color scale based on value
        let fillColor = '#3388ff';
        let fillOpacity = 0.4;

        if (value > 0.7) {
          fillColor = '#d73027';
          fillOpacity = 0.7;
        } else if (value > 0.5) {
          fillColor = '#fc8d59';
          fillOpacity = 0.6;
        } else if (value > 0.3) {
          fillColor = '#fee08b';
          fillOpacity = 0.5;
        } else if (value > 0.1) {
          fillColor = '#d9ef8b';
          fillOpacity = 0.4;
        }

        return {
          fillColor,
          fillOpacity,
          color: '#ffffff',
          weight: 1,
          opacity: 0.8
        };
      }}
      onEachFeature={(feature, layer) => {
        // Add popup with feature properties
        const props = feature.properties;
        const popupContent = `
          <div class="geosfm-popup">
            <strong>GeoSFM Forecast</strong><br/>
            ${Object.keys(props).map(key =>
              `<strong>${key}:</strong> ${props[key]}<br/>`
            ).join('')}
          </div>`;

        layer.bindPopup(popupContent, {
          autoPan: true,
          autoPanPadding: [50, 50],
          maxWidth: 300,
          keepInView: true
        });
      }}
    />
  );
};
