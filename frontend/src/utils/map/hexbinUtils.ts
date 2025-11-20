import * as turf from '@turf/turf';

/**
 * Creates hexagonal bins for flood monitoring points
 * @param points - GeoJSON FeatureCollection of flood monitoring points
 * @param cellSize - Size of hexagons in kilometers (default: 50km)
 * @returns GeoJSON FeatureCollection of hexagons with aggregated flood data
 */
export function createHexbins(points: any, cellSize: number = 50) {
  if (!points || !points.features || points.features.length === 0) {
    return null;
  }

  // Get bounding box of all points
  const bbox = turf.bbox(points);
  
  // Create hexagonal grid
  const hexgrid = turf.hexGrid(bbox, cellSize, { units: 'kilometers' });
  
  // Aggregate points into hexagons
  const collected = turf.collect(hexgrid, points, 'properties', 'points');
  
  // Process each hexagon to calculate alert status and metrics
  const processedHexagons = collected.features
    .map((hex: any) => {
      const pointsInHex = hex.properties.points || [];
      
      if (pointsInHex.length === 0) {
        return null; // Skip empty hexagons
      }
      
      // Count alert levels
      let normalCount = 0;
      let warningCount = 0;
      let alarmCount = 0;
      let emergencyCount = 0;
      
      pointsInHex.forEach((point: any) => {
        // Calculate alert status for each point
        const alertThreshold = point.section_discharge_thr_alert || 0;
        const alarmThreshold = point.section_discharge_thr_alarm || 0;
        const emergencyThreshold = point.section_discharge_thr_emergency || 0;
        
        // Get current discharge from time series
        let currentDischarge = 0;
        const gfsData = point["time_series_discharge_simulated-gfs"];
        const iconData = point["time_series_discharge_simulated-icon"];
        
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
        
        // Determine alert level
        if (emergencyThreshold > 0 && currentDischarge >= emergencyThreshold) {
          emergencyCount++;
        } else if (alarmThreshold > 0 && currentDischarge >= alarmThreshold) {
          alarmCount++;
        } else if (alertThreshold > 0 && currentDischarge >= alertThreshold) {
          warningCount++;
        } else {
          normalCount++;
        }
      });
      
      // Determine overall hexagon status (highest severity wins)
      let hexStatus = 'Normal';
      let hexColor = '#4CAF50'; // Green
      let hexOpacity = 0.4;
      
      if (emergencyCount > 0) {
        hexStatus = 'Emergency';
        hexColor = '#D32F2F'; // Dark Red
        hexOpacity = 0.7;
      } else if (alarmCount > 0) {
        hexStatus = 'Alarm';
        hexColor = '#EF5350'; // Red
        hexOpacity = 0.65;
      } else if (warningCount > 0) {
        hexStatus = 'Warning';
        hexColor = '#FFA726'; // Orange
        hexOpacity = 0.6;
      }
      
      return {
        ...hex,
        properties: {
          ...hex.properties,
          totalPoints: pointsInHex.length,
          normalCount,
          warningCount,
          alarmCount,
          emergencyCount,
          status: hexStatus,
          fillColor: hexColor,
          fillOpacity: hexOpacity,
          strokeColor: hexColor,
          strokeOpacity: 0.9
        }
      };
    })
    .filter(Boolean); // Remove null hexagons
  
  return {
    type: 'FeatureCollection',
    features: processedHexagons
  };
}

/**
 * Get style for hexagon based on its properties
 */
export function getHexagonStyle(feature: any) {
  return {
    fillColor: feature.properties.fillColor || '#4CAF50',
    fillOpacity: feature.properties.fillOpacity || 0.4,
    color: feature.properties.strokeColor || '#2E7D32',
    weight: 2,
    opacity: feature.properties.strokeOpacity || 0.9
  };
}
