/**
 * Ensemble Layer Component
 * Renders ensemble control points as markers on the map
 */

import React, { useState, useEffect } from 'react';
import { GeoJSON } from 'react-leaflet';
import MarkerClusterGroup from 'react-leaflet-cluster';
import L from 'leaflet';
// @ts-ignore
import { filterPointsByCountry, getCountryGeometry } from '../../../utils/map/countryFilter.ts';

interface ForecastRecord {
  date: string;
  Floodproof?: string;
  GeoSFM?: string;
  daily_avg?: string;
  daily_max?: string;
  daily_min?: string;
  Mike_Hydro_RFE?: string;
  Mike_Hydro_CHIRP?: string;
  Mike_Hydro_IMERG?: string;
}

interface EnsembleFeature {
  type: 'Feature';
  properties: {
    ID: number;
    admin_name: string | null;
    x: number;
    y: number;
    Zone: number;
    GRIDCODE: number;
    Node: boolean;
    has_data?: boolean;
    forecasts?: ForecastRecord[];
    forecast_count?: number;
  };
  geometry: {
    type: 'Point';
    coordinates: [number, number];
  };
}

interface EnsembleData {
  type: 'FeatureCollection';
  features: EnsembleFeature[];
}

interface EnsembleLayerProps {
  data: EnsembleData | null;
  selectedCountry: string | null;
  adminBoundariesData: any; // Admin0 boundary data for spatial filtering
  onEnsembleClick?: (feature: EnsembleFeature, markerPosition: { x: number; y: number }) => void;
}

/**
 * Generate table HTML for forecast data with toggle view functionality
 */
function generateForecastTable(forecasts: ForecastRecord[]): string {
  // Include all possible models (GeoSFM will show when data becomes available)
  const allModels = ['Floodproof', 'GeoSFM', 'Mike_Hydro_RFE', 'Mike_Hydro_CHIRP', 'Mike_Hydro_IMERG', 'daily_avg'];
  const excludeModels = ['daily_max', 'daily_min'];

  // Parse data and determine which models have data
  const tableData = forecasts.map(record => {
    const parsed: any = { date: new Date(record.date) };
    allModels.forEach(model => {
      const value = (record as any)[model];
      if (value !== undefined && value !== null && value !== '') {
        const numValue = parseFloat(value);
        if (!isNaN(numValue) && numValue >= 0) {
          parsed[model] = numValue;
        }
      }
    });
    return parsed;
  }).sort((a, b) => a.date.getTime() - b.date.getTime());

  // Find active models (exclude daily_max and daily_min)
  const activeModels = allModels.filter(model =>
    !excludeModels.includes(model) && tableData.some(d => d[model] !== undefined)
  );

  if (activeModels.length === 0 || tableData.length === 0) {
    return '<div style="padding: 20px; text-align: center; color: #666;">No forecast data available</div>';
  }

  const today = new Date();
  today.setHours(0, 0, 0, 0);

  // Build table HTML
  let tableHTML = `
    <div style="max-height: 400px; overflow-y: auto; overflow-x: auto;">
      <table style="width: 100%; border-collapse: collapse; font-size: 11px;">
        <thead style="position: sticky; top: 0; background-color: #6a1b9a; color: white; z-index: 1;">
          <tr>
            <th style="padding: 8px; text-align: left; border: 1px solid #ddd; white-space: nowrap;">Date</th>
            ${activeModels.map(model =>
              `<th style="padding: 8px; text-align: center; border: 1px solid #ddd; white-space: nowrap;">${model.replace(/_/g, ' ')}</th>`
            ).join('')}
          </tr>
        </thead>
        <tbody>
  `;

  tableData.forEach((row, index) => {
    const isFuture = row.date > today;
    const rowBgColor = index % 2 === 0 ? '#ffffff' : '#f5f5f5';
    const rowStyle = isFuture ? 'font-style: italic; color: #555;' : '';

    tableHTML += `<tr style="background-color: ${rowBgColor}; ${rowStyle}">`;

    // Date column
    const dateStr = row.date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
    tableHTML += `<td style="padding: 6px 8px; border: 1px solid #ddd; white-space: nowrap; font-weight: 500;">${dateStr}${isFuture ? ' *' : ''}</td>`;

    // Model value columns
    activeModels.forEach(model => {
      const value = row[model];
      const displayValue = value !== undefined ? value.toFixed(2) : '-';
      const cellStyle = value !== undefined ? 'font-weight: 500;' : 'color: #999;';
      tableHTML += `<td style="padding: 6px 8px; border: 1px solid #ddd; text-align: center; ${cellStyle}">${displayValue}</td>`;
    });

    tableHTML += '</tr>';
  });

  tableHTML += `
        </tbody>
      </table>
    </div>
    <div style="margin-top: 8px; padding: 6px 8px; background-color: #f9fbe7; border-radius: 4px; font-size: 10px; color: #666;">
      <strong>Note:</strong> Values in m³/s. Dates marked with * are future forecasts.
    </div>
  `;

  return tableHTML;
}

/**
 * Draw ensemble forecast chart on canvas
 */
function drawEnsembleChart(ctx: CanvasRenderingContext2D, canvas: HTMLCanvasElement, forecasts: ForecastRecord[], firstDate?: string, hoverPos?: { x: number; y: number }) {
  const width = canvas.width;
  const height = canvas.height;
  const padding = { top: 40, right: 120, bottom: 60, left: 60 };
  const chartWidth = width - padding.left - padding.right;
  const chartHeight = height - padding.top - padding.bottom;

  // Clear canvas
  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = '#ffffff';
  ctx.fillRect(0, 0, width, height);

  // Define all possible models and their colors (GeoSFM will show when data becomes available)
  const allModels = ['Floodproof', 'GeoSFM', 'Mike_Hydro_RFE', 'Mike_Hydro_CHIRP', 'Mike_Hydro_IMERG', 'daily_avg', 'daily_max', 'daily_min'];
  const colors: { [key: string]: string } = {
    'Floodproof': '#9C27B0',
    'GeoSFM': '#2196F3',
    'daily_avg': '#4CAF50',
    'daily_max': '#FF9800',
    'daily_min': '#00BCD4',
    'Mike_Hydro_RFE': '#E91E63',
    'Mike_Hydro_CHIRP': '#FF5722',
    'Mike_Hydro_IMERG': '#795548'
  };

  // Parse and sort data - check all possible models (include zero values)
  const chartData = forecasts.map(record => {
    const parsed: any = { date: new Date(record.date) };
    allModels.forEach(model => {
      const value = (record as any)[model];
      if (value !== undefined && value !== null && value !== '') {
        const numValue = parseFloat(value);
        if (!isNaN(numValue) && numValue >= 0) {  // Accept zero and positive values
          parsed[model] = numValue;
        }
      }
    });
    return parsed;
  }).sort((a, b) => a.date.getTime() - b.date.getTime());

  // Find which models have data, excluding daily_max and daily_min
  const excludeModels = ['daily_max', 'daily_min'];
  const activeModels = allModels.filter(model =>
    !excludeModels.includes(model) && chartData.some(d => d[model] !== undefined)
  );

  if (activeModels.length === 0 || chartData.length === 0) {
    ctx.fillStyle = '#666';
    ctx.font = '14px Arial';
    ctx.textAlign = 'center';
    ctx.fillText('No valid forecast data', width / 2, height / 2);
    return;
  }

  // Find min/max values
  let minValue = Infinity;
  let maxValue = -Infinity;
  chartData.forEach(d => {
    activeModels.forEach(model => {
      if (d[model] !== undefined) {
        minValue = Math.min(minValue, d[model]);
        maxValue = Math.max(maxValue, d[model]);
      }
    });
  });

  // Check if we have valid data
  if (maxValue === -Infinity || minValue === Infinity) {
    ctx.fillStyle = '#666';
    ctx.font = '14px Arial';
    ctx.textAlign = 'center';
    ctx.fillText('No valid data values found', width / 2, height / 2);
    return;
  }

  // Add 10% padding to y-axis
  const yPadding = (maxValue - minValue) * 0.1;
  // Extend y-axis below 0 to make zero-value lines visible
  // This ensures models with 0.00 values are visible even when other models have large values
  if (maxValue < 1) {
    // For very small values, extend to -1
    minValue = -1;
    maxValue = Math.max(maxValue + yPadding, 1);
  } else {
    // For larger values, extend minValue by 5% of range below 0 to show zero-value lines
    const rangeExtension = (maxValue - minValue) * 0.05;
    minValue = -rangeExtension;
    maxValue = maxValue + yPadding;
  }

  // Helper functions
  const getX = (index: number) => padding.left + (index / (chartData.length - 1)) * chartWidth;
  const getY = (value: number) => padding.top + chartHeight - ((value - minValue) / (maxValue - minValue)) * chartHeight;

  // Draw grid
  ctx.strokeStyle = '#e0e0e0';
  ctx.lineWidth = 1;
  for (let i = 0; i <= 5; i++) {
    const y = padding.top + (i / 5) * chartHeight;
    ctx.beginPath();
    ctx.moveTo(padding.left, y);
    ctx.lineTo(padding.left + chartWidth, y);
    ctx.stroke();
  }

  // Draw axes
  ctx.strokeStyle = '#666';
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(padding.left, padding.top);
  ctx.lineTo(padding.left, padding.top + chartHeight);
  ctx.lineTo(padding.left + chartWidth, padding.top + chartHeight);
  ctx.stroke();

  // Draw y-axis labels
  ctx.fillStyle = '#666';
  ctx.font = '11px Arial';
  ctx.textAlign = 'right';
  ctx.textBaseline = 'middle';
  for (let i = 0; i <= 5; i++) {
    const value = minValue + (maxValue - minValue) * (1 - i / 5);
    const y = padding.top + (i / 5) * chartHeight;
    ctx.fillText(value.toFixed(1), padding.left - 10, y);
  }

  // Get today's date for determining forecast vs historical
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  // Draw lines for each model (with dotted lines for future forecasts)
  activeModels.forEach(model => {
    const color = colors[model] || '#666';

    // Draw historical data (solid line) and forecast data (dotted line) separately
    let inHistorical = true;
    let historicalPoints: Array<{x: number, y: number, index: number}> = [];
    let forecastPoints: Array<{x: number, y: number, index: number}> = [];

    chartData.forEach((d, index) => {
      if (d[model] !== undefined) {
        const x = getX(index);
        const y = getY(d[model]);
        const isFuture = d.date > today;

        if (isFuture) {
          forecastPoints.push({x, y, index});
        } else {
          historicalPoints.push({x, y, index});
        }
      }
    });

    // Draw historical (solid line)
    if (historicalPoints.length > 0) {
      ctx.strokeStyle = color;
      ctx.lineWidth = 2;
      ctx.setLineDash([]);
      ctx.beginPath();
      historicalPoints.forEach((point, i) => {
        if (i === 0) {
          ctx.moveTo(point.x, point.y);
        } else {
          ctx.lineTo(point.x, point.y);
        }
      });
      ctx.stroke();
    }

    // Draw forecast (dotted line)
    if (forecastPoints.length > 0) {
      ctx.strokeStyle = color;
      ctx.lineWidth = 2;
      ctx.setLineDash([8, 4]);  // Dotted pattern
      ctx.beginPath();

      // Connect from last historical point if exists
      if (historicalPoints.length > 0) {
        const lastHistorical = historicalPoints[historicalPoints.length - 1];
        ctx.moveTo(lastHistorical.x, lastHistorical.y);
        forecastPoints.forEach(point => {
          ctx.lineTo(point.x, point.y);
        });
      } else {
        forecastPoints.forEach((point, i) => {
          if (i === 0) {
            ctx.moveTo(point.x, point.y);
          } else {
            ctx.lineTo(point.x, point.y);
          }
        });
      }
      ctx.stroke();
      ctx.setLineDash([]);  // Reset to solid
    }
  });

  // Draw x-axis labels (dates) - show first, middle, last
  ctx.fillStyle = '#666';
  ctx.font = '10px Arial';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'top';
  const dateIndices = [0, Math.floor(chartData.length / 2), chartData.length - 1];
  dateIndices.forEach(i => {
    if (i < chartData.length) {
      const x = getX(i);
      const dateStr = chartData[i].date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
      ctx.fillText(dateStr, x, padding.top + chartHeight + 10);
    }
  });

  // Draw legend
  ctx.font = '11px Arial';
  ctx.textAlign = 'left';
  ctx.textBaseline = 'middle';
  activeModels.forEach((model, index) => {
    const legendX = padding.left + chartWidth + 15;
    const legendY = padding.top + index * 20;

    // Color box
    ctx.fillStyle = colors[model];
    ctx.fillRect(legendX, legendY - 5, 10, 10);

    // Label
    ctx.fillStyle = '#333';
    const label = model.replace(/_/g, ' ');
    ctx.fillText(label, legendX + 15, legendY);
  });

  // Draw title
  ctx.fillStyle = '#6a1b9a';
  ctx.font = 'bold 13px Arial';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'top';
  const titleText = firstDate ? `Multi-modal Discharge - ${firstDate} (m³/s)` : 'Multi-modal Discharge (m³/s)';
  ctx.fillText(titleText, width / 2, 10);

  // Draw hover tooltip if mouse is over the chart
  if (hoverPos && hoverPos.x >= padding.left && hoverPos.x <= padding.left + chartWidth &&
      hoverPos.y >= padding.top && hoverPos.y <= padding.top + chartHeight) {

    // Find nearest data point
    let nearestIndex = 0;
    let minDist = Infinity;
    chartData.forEach((d, index) => {
      const x = getX(index);
      const dist = Math.abs(x - hoverPos.x);
      if (dist < minDist) {
        minDist = dist;
        nearestIndex = index;
      }
    });

    // Only show tooltip if mouse is reasonably close to a data point
    if (minDist < 30) {
      const dataPoint = chartData[nearestIndex];
      const xPos = getX(nearestIndex);

      // Draw vertical line at hover position
      ctx.strokeStyle = '#666';
      ctx.lineWidth = 1;
      ctx.setLineDash([4, 4]);
      ctx.beginPath();
      ctx.moveTo(xPos, padding.top);
      ctx.lineTo(xPos, padding.top + chartHeight);
      ctx.stroke();
      ctx.setLineDash([]);

      // Draw circles on each line at this point
      activeModels.forEach(model => {
        if (dataPoint[model] !== undefined) {
          const yPos = getY(dataPoint[model]);
          ctx.fillStyle = colors[model];
          ctx.beginPath();
          ctx.arc(xPos, yPos, 4, 0, 2 * Math.PI);
          ctx.fill();
          ctx.strokeStyle = '#fff';
          ctx.lineWidth = 2;
          ctx.stroke();
        }
      });

      // Draw tooltip box
      const tooltipLines = [dataPoint.date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })];
      activeModels.forEach(model => {
        if (dataPoint[model] !== undefined) {
          tooltipLines.push(`${model.replace(/_/g, ' ')}: ${dataPoint[model].toFixed(2)} m³/s`);
        }
      });

      const tooltipPadding = 8;
      const lineHeight = 16;
      const tooltipWidth = 180;
      const tooltipHeight = tooltipLines.length * lineHeight + tooltipPadding * 2;

      // Position tooltip to the right of the point, or left if too close to edge
      let tooltipX = xPos + 15;
      if (tooltipX + tooltipWidth > width - 10) {
        tooltipX = xPos - tooltipWidth - 15;
      }
      let tooltipY = Math.max(padding.top, Math.min(hoverPos.y - tooltipHeight / 2, padding.top + chartHeight - tooltipHeight));

      // Draw tooltip background
      ctx.fillStyle = 'rgba(255, 255, 255, 0.95)';
      ctx.strokeStyle = '#666';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.rect(tooltipX, tooltipY, tooltipWidth, tooltipHeight);
      ctx.fill();
      ctx.stroke();

      // Draw tooltip text
      ctx.fillStyle = '#333';
      ctx.font = 'bold 11px Arial';
      ctx.textAlign = 'left';
      ctx.textBaseline = 'top';
      ctx.fillText(tooltipLines[0], tooltipX + tooltipPadding, tooltipY + tooltipPadding);

      ctx.font = '10px Arial';
      tooltipLines.slice(1).forEach((line, index) => {
        // Color code the model name
        const modelName = line.split(':')[0];
        const modelValue = line.split(':')[1];
        const modelKey = Object.keys(colors).find(key => key.replace(/_/g, ' ') === modelName);

        ctx.fillStyle = modelKey ? colors[modelKey] : '#333';
        ctx.fillText('■', tooltipX + tooltipPadding, tooltipY + tooltipPadding + (index + 1) * lineHeight + 2);

        ctx.fillStyle = '#333';
        ctx.fillText(line, tooltipX + tooltipPadding + 15, tooltipY + tooltipPadding + (index + 1) * lineHeight);
      });
    }
  }
}

export const EnsembleLayer: React.FC<EnsembleLayerProps> = ({ data, selectedCountry, adminBoundariesData, onEnsembleClick }) => {
  const [renderKey, setRenderKey] = useState(0);
  const [isReady, setIsReady] = useState(true);

  // Force remount when data or country selection changes
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
  }, [data, selectedCountry]);

  // Filter data by selected country using spatial filtering
  const filteredData = React.useMemo(() => {
    if (!data?.features) {
      return null;
    }

    // No country selected or "All Countries" selected: show all points
    if (!selectedCountry || selectedCountry === '') {
      return data;
    }

    // Admin boundaries required for spatial filtering
    if (!adminBoundariesData) {
      return data;
    }

    // Special case: "WHCA Countries" selected - filter to points in any of the 5 WHCA countries
    if (selectedCountry === 'WHCA') {
      const whcaCountries = ['Uganda', 'Rwanda', 'South Sudan', 'Ethiopia', 'Sudan'];
      let combinedFeatures: EnsembleFeature[] = [];

      whcaCountries.forEach(country => {
        const result = filterPointsByCountry(data, adminBoundariesData, country);
        if (result?.features) {
          combinedFeatures = [...combinedFeatures, ...result.features as EnsembleFeature[]];
        }
      });

      // Remove duplicates (in case a point is on a border)
      const uniqueFeatures = Array.from(
        new Map(combinedFeatures.map(f => [f.properties.ID, f])).values()
      );

      return {
        ...data,
        features: uniqueFeatures
      };
    }

    // Single country selected: spatially filter points within that country's boundaries
    const result = filterPointsByCountry(data, adminBoundariesData, selectedCountry);
    if (result) {
      return result;
    }

    return data;
  }, [data, selectedCountry, adminBoundariesData]);

  if (!filteredData?.features || filteredData.features.length === 0 || !isReady) {
    return null;
  }

  // Create ensemble marker icon - grey balloon/pin style with purple outline
  const createEnsembleIcon = () => {
    const width = 24;
    const height = 30;
    const bgColor = '#9E9E9E';  // Grey
    const strokeColor = '#9C27B0';  // Purple

    return L.divIcon({
      className: 'ensemble-marker',
      html: `
        <svg width="${width}" height="${height}" viewBox="0 0 24 36" xmlns="http://www.w3.org/2000/svg" style="filter: drop-shadow(0 2px 4px rgba(0,0,0,0.3));">
          <path d="M12 0C7.6 0 4 3.6 4 8c0 5.4 8 20 8 20s8-14.6 8-20c0-4.4-3.6-8-8-8z"
                fill="${bgColor}"
                stroke="${strokeColor}"
                stroke-width="1.5"/>
        </svg>
      `,
      iconSize: [width, height],
      iconAnchor: [width/2, height],
      popupAnchor: [0, -height + 5]
    });
  };

  // Create cluster icon for ensemble points - grey balloon style with purple outline, no numbers
  const createClusterIcon = (cluster: any) => {
    const width = 32;
    const height = 42;
    const bgColor = '#9E9E9E';  // Grey
    const strokeColor = '#9C27B0';  // Purple

    return L.divIcon({
      className: 'ensemble-cluster',
      html: `
        <svg width="${width}" height="${height}" viewBox="0 0 24 36" xmlns="http://www.w3.org/2000/svg" style="filter: drop-shadow(0 2px 4px rgba(0,0,0,0.3));">
          <path d="M12 0C7.6 0 4 3.6 4 8c0 5.4 8 20 8 20s8-14.6 8-20c0-4.4-3.6-8-8-8z"
                fill="${bgColor}"
                stroke="${strokeColor}"
                stroke-width="2"/>
        </svg>
      `,
      iconSize: [width, height],
      iconAnchor: [width/2, height],
      popupAnchor: [0, -height + 5]
    });
  };

  return (
    <MarkerClusterGroup
      key={`ensemble-cluster-${renderKey}`}
      maxClusterRadius={50}
      disableClusteringAtZoom={15}
      spiderfyOnMaxZoom={false}
      showCoverageOnHover={false}
      spiderLegPolylineOptions={{ weight: 1.5, color: '#9C27B0', opacity: 0.5 }}
      spiderfyDistanceMultiplier={1.5}
      iconCreateFunction={createClusterIcon}
    >
      <GeoJSON
        key={`ensemble-points-${renderKey}`}
        data={filteredData}
        pointToLayer={(feature, latlng) => {
          const marker: any = L.marker(latlng, {
            icon: createEnsembleIcon()
          });
          return marker;
        }}
        onEachFeature={(feature, layer) => {
          const props = feature.properties;

          const hasForecastData = props.has_data && props.forecasts && props.forecasts.length > 0;

          // Get available models list as comma-separated string
          const getAvailableModels = () => {
            if (!hasForecastData) return '';

            // Only show actual model names (not derived statistics like daily_avg/min/max)
            const allModels = ['Floodproof', 'GeoSFM', 'Mike_Hydro_RFE', 'Mike_Hydro_CHIRP', 'Mike_Hydro_IMERG'];
            const availableModels = allModels.filter(model => {
              return props.forecasts.some((record: any) => {
                const value = record[model];
                if (value !== undefined && value !== null && value !== '') {
                  const numValue = parseFloat(value);
                  // Include model if it has a valid numeric value >= 0 (including zeros)
                  return !isNaN(numValue) && numValue >= 0;
                }
                return false;
              });
            });

            return availableModels.map(m => m.replace(/_/g, ' ')).join(', ');
          };

          // Get first forecast date
          const getForecastDate = () => {
            if (!hasForecastData || !props.forecasts || props.forecasts.length === 0) return '';
            const firstDate = props.forecasts[0]?.date;
            if (firstDate) {
              return ` - ${firstDate}`;
            }
            return '';
          };

          // Create popup content with view toggle and chart/table
          const popupContent = `
            <div class="ensemble-popup" style="min-width: ${hasForecastData ? '520px' : '220px'}; max-width: 95vw; max-height: 90vh; overflow-y: auto;">
              <div style="background-color: #f3e5f5; padding: 12px; border-radius: 6px; margin-bottom: 12px;">
                <h3 style="margin: 0 0 8px 0; color: #6a1b9a; font-size: 16px;">${props.admin_name || 'N/A'} Zone${props.Zone}_${props.GRIDCODE}</h3>
                ${hasForecastData ? `
                  <div style="font-size: 11px; color: #666; margin-bottom: 4px;">
                    <strong>Available Models:</strong> ${getAvailableModels()}
                  </div>
                  <div style="font-size: 11px; color: #666;">
                    <strong>Forecast Records:</strong> ${props.forecasts.length} records
                  </div>
                ` : ''}
              </div>
              ${hasForecastData ? `
                <div style="display: flex; gap: 8px; margin-bottom: 12px; justify-content: center; flex-wrap: wrap;">
                  <button
                    id="toggle-chart-${props.ID}"
                    onclick="
                      document.getElementById('chart-view-${props.ID}').style.display = 'block';
                      document.getElementById('table-view-${props.ID}').style.display = 'none';
                      this.style.backgroundColor = '#034930';
                      this.style.color = 'white';
                      document.getElementById('toggle-table-${props.ID}').style.backgroundColor = '#e0e0e0';
                      document.getElementById('toggle-table-${props.ID}').style.color = '#333';
                    "
                    style="
                      padding: 8px 16px;
                      border: none;
                      border-radius: 4px;
                      background-color: #034930;
                      color: white;
                      cursor: pointer;
                      font-size: 12px;
                      font-weight: 600;
                      transition: all 0.2s;
                    "
                  >
                    Chart View
                  </button>
                  <button
                    id="toggle-table-${props.ID}"
                    onclick="
                      document.getElementById('chart-view-${props.ID}').style.display = 'none';
                      document.getElementById('table-view-${props.ID}').style.display = 'block';
                      this.style.backgroundColor = '#034930';
                      this.style.color = 'white';
                      document.getElementById('toggle-chart-${props.ID}').style.backgroundColor = '#e0e0e0';
                      document.getElementById('toggle-chart-${props.ID}').style.color = '#333';
                    "
                    style="
                      padding: 8px 16px;
                      border: none;
                      border-radius: 4px;
                      background-color: #e0e0e0;
                      color: #333;
                      cursor: pointer;
                      font-size: 12px;
                      font-weight: 600;
                      transition: all 0.2s;
                    "
                  >
                    Table View
                  </button>
                </div>

                <div id="chart-view-${props.ID}" style="background-color: white; padding: 10px; border: 1px solid #ddd; border-radius: 6px;">
                  <canvas id="ensemble-chart-${props.ID}" width="480" height="300" style="width: 100%; max-width: 480px;"></canvas>
                </div>

                <div id="table-view-${props.ID}" style="display: none; background-color: white; padding: 10px; border: 1px solid #ddd; border-radius: 6px;">
                  ${generateForecastTable(props.forecasts)}
                </div>
              ` : `
                <div style="padding: 12px; background-color: #fff3e0; border-radius: 4px; font-size: 12px; color: #e65100; text-align: center;">
                  <strong>Note:</strong> No forecast data available for this point.
                </div>
              `}
            </div>
          `;

          const popup = L.popup({
            autoPan: true,
            autoPanPadding: [50, 50],
            maxWidth: hasForecastData ? 550 : 320,
            minWidth: hasForecastData ? 520 : 220,
            keepInView: true,
            className: 'ensemble-popup-no-tip'
          }).setContent(popupContent);

          layer.bindPopup(popup);

          // Handle popup open - draw chart on canvas and attach event listeners
          if (hasForecastData) {
            layer.on('popupopen', () => {
              // Small delay to ensure canvas is in DOM
              setTimeout(() => {
                const canvas = document.getElementById(`ensemble-chart-${props.ID}`) as HTMLCanvasElement;
                if (!canvas) {
                  return;
                }

                const ctx = canvas.getContext('2d');
                if (!ctx) {
                  return;
                }

                // Get first forecast date
                const firstDate = props.forecasts && props.forecasts.length > 0 ? props.forecasts[0]?.date : undefined;

                // Draw chart using canvas API
                drawEnsembleChart(ctx, canvas, props.forecasts, firstDate);

                // Add hover functionality
                let lastHoverIndex = -1;
                canvas.addEventListener('mousemove', (e) => {
                  const rect = canvas.getBoundingClientRect();
                  const x = e.clientX - rect.left;
                  const y = e.clientY - rect.top;

                  // Redraw chart with hover tooltip
                  drawEnsembleChart(ctx, canvas, props.forecasts, firstDate, { x, y });
                });

                canvas.addEventListener('mouseleave', () => {
                  // Redraw without hover
                  drawEnsembleChart(ctx, canvas, props.forecasts, firstDate);
                });

                // Set cursor style
                canvas.style.cursor = 'crosshair';
              }, 100);
            });
          }
        }}
      />
    </MarkerClusterGroup>
  );
};
