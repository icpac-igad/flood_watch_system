import React, { useRef } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend as RechartsLegend, ResponsiveContainer, ReferenceLine } from 'recharts';

// Export functions
const exportToCSV = (data, filename, stationName = '') => {
  const headers = Object.keys(data[0]).join(',');
  const csvContent = [
    `# ${stationName} - ${filename}`,
    `# Generated on: ${new Date().toLocaleString()}`,
    headers,
    ...data.map(row => Object.values(row).map(val => 
      val instanceof Date ? val.toISOString().split('T')[0] : val
    ).join(','))
  ].join('\n');
  
  const blob = new Blob([csvContent], { type: 'text/csv' });
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `${filename}.csv`;
  a.click();
  window.URL.revokeObjectURL(url);
};

const exportToPNG = (chartRef, filename, stationName = '') => {
  if (!chartRef.current) return;
  
  const svg = chartRef.current.querySelector('svg');
  if (!svg) return;
  
  const canvas = document.createElement('canvas');
  const ctx = canvas.getContext('2d');
  const svgData = new XMLSerializer().serializeToString(svg);
  const img = new Image();
  
  canvas.width = svg.clientWidth || 800;
  canvas.height = svg.clientHeight || 400;
  
  img.onload = () => {
    ctx.fillStyle = 'white';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(img, 0, 0);
    
    // Add title
    ctx.fillStyle = 'black';
    ctx.font = '16px Arial';
    ctx.fillText(`${stationName} - ${filename}`, 10, 25);
    
    const link = document.createElement('a');
    link.download = `${filename}.png`;
    link.href = canvas.toDataURL();
    link.click();
  };
  
  const svgBlob = new Blob([svgData], { type: 'image/svg+xml;charset=utf-8' });
  const url = URL.createObjectURL(svgBlob);
  img.src = url;
};

// Component to render a discharge forecast chart
export const DischargeChart = ({ timeSeriesData, selectedSeries = 'both', stationName = '', height = 400 }) => {
  const chartRef = useRef(null);
  
  if (!timeSeriesData || timeSeriesData.length === 0) {
    return <div className="chart-no-data" style={{ padding: '20px', textAlign: 'center' }}>No data available.</div>;
  }

  const processedData = timeSeriesData.map(item => ({
    time: new Date(item.time),
    gfs: selectedSeries === 'icon' ? null : Number(item.gfs) || 0,
    icon: selectedSeries === 'gfs' ? null : Number(item.icon) || 0
  })).filter(item => 
    (selectedSeries === 'both' && (!isNaN(item.gfs) || !isNaN(item.icon))) ||
    (selectedSeries === 'gfs' && !isNaN(item.gfs)) ||
    (selectedSeries === 'icon' && !isNaN(item.icon))
  );

  // Split data into historical and forecast based on today's date
  const splitDataByToday = React.useMemo(() => {
    const today = new Date();
    const currentDate = new Date(today.getFullYear(), today.getMonth(), today.getDate(), 12, 0, 0);
    
    const historicalData = [];
    const forecastData = [];
    let todayIndex = -1;
    
    processedData.forEach((item, index) => {
      if (item.time <= currentDate) {
        historicalData.push({
          ...item,
          gfsForecast: null,
          iconForecast: null
        });
        todayIndex = index;
      } else {
        forecastData.push({
          ...item,
          gfsForecast: item.gfs,
          iconForecast: item.icon,
          gfs: null,
          icon: null
        });
      }
    });
    
    // Connect forecast data to last historical point
    if (historicalData.length > 0 && forecastData.length > 0) {
      const lastHistorical = historicalData[historicalData.length - 1];
      forecastData.unshift({
        time: lastHistorical.time,
        gfs: null,
        icon: null,
        gfsForecast: lastHistorical.gfs,
        iconForecast: lastHistorical.icon
      });
    }
    
    return { historicalData, forecastData, todayIndex };
  }, [processedData]);

  // Combine all data for chart rendering
  const chartData = React.useMemo(() => {
    const combined = [...processedData];
    const today = new Date();
    const currentDate = new Date(today.getFullYear(), today.getMonth(), today.getDate(), 12, 0, 0);
    
    // Find today's index
    let todayIndex = -1;
    for (let i = 0; i < combined.length; i++) {
      if (combined[i].time.getTime() >= currentDate.getTime()) {
        todayIndex = i;
        break;
      }
    }
    
    // Add forecast data keys to all data points
    combined.forEach((item, index) => {
      if (index >= todayIndex && todayIndex !== -1) {
        // From today onwards, show as forecast (dotted)
        item.gfsForecast = item.gfs;
        item.iconForecast = item.icon;
        item.gfs = null;
        item.icon = null;
      } else {
        // Before today, show as historical (solid) only
        item.gfsForecast = null;
        item.iconForecast = null;
      }
    });

    // Add connection point: duplicate the last historical point as first forecast point
    if (todayIndex > 0 && todayIndex !== -1) {
      const lastHistoricalPoint = combined[todayIndex - 1];
      if (lastHistoricalPoint && !lastHistoricalPoint.gfsForecast) {
        lastHistoricalPoint.gfsForecast = lastHistoricalPoint.gfs;
        lastHistoricalPoint.iconForecast = lastHistoricalPoint.icon;
      }
    }
    
    return combined;
  }, [processedData]);
  

  // Calculate Y-axis domain for better scaling
  const allValues = chartData.flatMap(item => [item.gfs, item.icon, item.gfsForecast, item.iconForecast].filter(v => v != null && !isNaN(v)));
  
  let yDomain;
  // If no valid values, provide default domain
  if (allValues.length === 0) {
    yDomain = [0, 1];
  } else {
    const minValue = Math.min(...allValues);
    const maxValue = Math.max(...allValues);
    const range = maxValue - minValue;
    
    // For very small or zero ranges, ensure proper scaling
    if (range === 0) {
      // All values are the same
      if (maxValue === 0) {
        yDomain = [0, 1];
      } else if (maxValue < 0.01) {
        yDomain = [0, maxValue * 2];
      } else {
        yDomain = [maxValue * 0.8, maxValue * 1.2];
      }
    } else if (range < 0.001) {
      // Extremely small range - use tight bounds
      const padding = range * 2;
      yDomain = [Math.max(0, minValue - padding), maxValue + padding];
    } else if (range < 0.01) {
      // Very small range - use moderate padding
      const padding = range * 1.5;
      yDomain = [Math.max(0, minValue - padding), maxValue + padding];
    } else if (range < 0.1) {
      // Small range - use standard padding
      const padding = range * 0.5;
      yDomain = [Math.max(0, minValue - padding), maxValue + padding];
    } else {
      // Normal range - use minimal padding
      const padding = range * 0.1;
      yDomain = [Math.max(0, minValue - padding), maxValue + padding];
    }
  }

  // Calculate appropriate tick values to avoid duplicates
  const calculateTicks = (domain) => {
    const [min, max] = domain;
    const range = max - min;
    let targetTickCount = 5;
    
    // For very small ranges, reduce tick count to avoid crowding
    if (range < 0.1) targetTickCount = 4;
    if (range < 0.05) targetTickCount = 3;
    
    // Calculate the step size
    let step = range / (targetTickCount - 1);
    
    // Determine the precision needed based on the step size
    let precision = 0;
    if (step < 0.001) precision = 4;
    else if (step < 0.01) precision = 3;
    else if (step < 0.1) precision = 2;
    else if (step < 1) precision = 1;
    
    // Round step to avoid floating point issues
    const factor = Math.pow(10, precision);
    step = Math.ceil(step * factor) / factor;
    
    // Generate ticks starting from a rounded minimum
    const ticks = [];
    const roundedMin = Math.floor(min * factor) / factor;
    
    for (let i = 0; i < targetTickCount; i++) {
      const tickValue = roundedMin + (i * step);
      if (tickValue <= max) {
        // Round to avoid floating point precision issues
        const roundedTick = Math.round(tickValue * factor) / factor;
        ticks.push(roundedTick);
      }
    }
    
    // Remove any duplicates (this handles edge cases)
    const uniqueTicks = [...new Set(ticks.map(t => t.toFixed(precision)))].map(Number);
    
    // Ensure we have at least 2 ticks
    if (uniqueTicks.length < 2) {
      return [min, max];
    }
    
    return uniqueTicks;
  };

  const yTicks = calculateTicks(yDomain);

  // Get current date for reference line - make it dynamic
  const today = new Date();
  const currentDate = new Date(today.getFullYear(), today.getMonth(), today.getDate(), 12, 0, 0);
  
  


  // Find today's data point in the dataset
  const todayDataPoint = React.useMemo(() => {
    if (chartData.length === 0) return null;
    
    // Check data range
    const firstDate = chartData[0].time;
    const lastDate = chartData[chartData.length - 1].time;
    
    
    // Check if today is within the data range
    if (currentDate < firstDate || currentDate > lastDate) {
      return null;
    }
    
    // Find the closest data point to today
    let closestPoint = null;
    let closestDiff = Infinity;
    let closestIndex = -1;
    
    for (let i = 0; i < chartData.length; i++) {
      const dataPoint = chartData[i];
      const diff = Math.abs(dataPoint.time.getTime() - currentDate.getTime());
      
      if (diff < closestDiff) {
        closestDiff = diff;
        closestPoint = dataPoint;
        closestIndex = i;
      }
    }
    
    if (closestPoint) {
      // Calculate position as percentage of data points
      const percentage = (closestIndex / (chartData.length - 1)) * 100;
      
      return {
        dataPoint: closestPoint,
        index: closestIndex,
        positionPercent: percentage
      };
    }
    
    return null;
  }, [chartData, currentDate]);

  return (
    <div className="chart-container" ref={chartRef} style={{ position: 'relative' }}>
      <ResponsiveContainer width="100%" height={height}>
        <LineChart data={chartData} margin={{ top: 5, right: 5, left: 45, bottom: 30 }}>
            <defs>
              <linearGradient id="gfsGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#1f77b4" stopOpacity={0.3}/>
                <stop offset="95%" stopColor="#1f77b4" stopOpacity={0}/>
              </linearGradient>
              <linearGradient id="iconGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#ff7f0e" stopOpacity={0.3}/>
                <stop offset="95%" stopColor="#ff7f0e" stopOpacity={0}/>
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
            <XAxis 
              dataKey="time" 
              angle={-45} 
              textAnchor="end" 
              height={30} 
              tickFormatter={(dt) => {
                const date = new Date(dt);
                return date.toLocaleDateString('en-GB', { day: '2-digit', month: 'short' });
              }} 
              minTickGap={20}
              stroke="#666"
              fontWeight={600}
              fontSize={9}
            />
            <YAxis 
              domain={yDomain}
              ticks={yTicks}
              label={{ 
                value: 'Discharge (m³/s)', 
                angle: -90, 
                position: 'insideLeft', 
                offset: -5, 
                style: { textAnchor: 'middle', fontSize: '10px', fill: '#333' } 
              }}
              stroke="#666"
              fontWeight={600}
              fontSize={9}
              tickFormatter={(value) => {
                const num = Number(value);
                if (isNaN(num)) return '0';
                
                if (num >= 1000) return (num / 1000).toFixed(1) + 'k';
                if (num >= 1) return num.toFixed(1);
                if (num >= 0.1) return num.toFixed(2);
                return num.toFixed(3);
              }}
              width={40}
            />
            <Tooltip 
              labelFormatter={(label) => `Date: ${label.toLocaleDateString('en-GB')}`} 
              formatter={(value, name) => [Number(value).toFixed(3) + ' m³/s', name]}
              contentStyle={{
                backgroundColor: 'rgba(255, 255, 255, 0.95)',
                border: '1px solid #ccc',
                borderRadius: '4px',
                boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
                fontSize: '11px'
              }}
            />
            <RechartsLegend 
              wrapperStyle={{ 
                paddingTop: '2px',
                fontSize: '10px'
              }}
              iconType="line"
              payload={[
                { value: 'GFS', type: 'line', color: '#1f77b4' },
                { value: 'ICON', type: 'line', color: '#ff7f0e' }
              ].filter(item => 
                (selectedSeries === 'both') || 
                (selectedSeries === 'gfs' && item.value === 'GFS') ||
                (selectedSeries === 'icon' && item.value === 'ICON')
              )}
            />
            {/* Historical data - solid lines */}
            {(selectedSeries === 'both' || selectedSeries === 'gfs') && 
              <Line 
                type="monotone" 
                dataKey="gfs" 
                stroke="#1f77b4" 
                name="GFS" 
                dot={false} 
                strokeWidth={2}
                activeDot={{ r: 6, stroke: '#1f77b4', strokeWidth: 2, fill: 'white' }}
              />
            }
            {(selectedSeries === 'both' || selectedSeries === 'icon') && 
              <Line 
                type="monotone" 
                dataKey="icon" 
                stroke="#ff7f0e" 
                name="ICON" 
                dot={false} 
                strokeWidth={2}
                activeDot={{ r: 6, stroke: '#ff7f0e', strokeWidth: 2, fill: 'white' }}
              />
            }
            
            {/* Forecast data - dotted lines (hidden from legend) */}
            {(selectedSeries === 'both' || selectedSeries === 'gfs') && 
              <Line 
                type="monotone" 
                dataKey="gfsForecast" 
                stroke="#1f77b4" 
                dot={false} 
                strokeWidth={2}
                strokeDasharray="8 4"
                activeDot={{ r: 6, stroke: '#1f77b4', strokeWidth: 2, fill: 'white' }}
              />
            }
            {(selectedSeries === 'both' || selectedSeries === 'icon') && 
              <Line 
                type="monotone" 
                dataKey="iconForecast" 
                stroke="#ff7f0e" 
                dot={false} 
                strokeWidth={2}
                strokeDasharray="8 4"
                activeDot={{ r: 6, stroke: '#ff7f0e', strokeWidth: 2, fill: 'white' }}
              />
            }
            {todayDataPoint && (
              <ReferenceLine 
                x={todayDataPoint.dataPoint.time} 
                stroke="#FF4444" 
                strokeWidth={2}
                strokeDasharray="5 5"
                label={{ 
                  value: "Today", 
                  position: "insideTopRight",
                  offset: 5,
                  fill: "#FF4444",
                  fontSize: 10,
                  fontWeight: 600
                }}
              />
            )}
          </LineChart>
        </ResponsiveContainer>
    </div>
  );
};

// Component to render GeoSFM charts (river depth or streamflow)
export const GeoSFMChart = ({ timeSeriesData, dataType = 'riverdepth', height = 400 }) => {
  const chartRef = useRef(null);
  
  // Always call all hooks before any conditional returns
  const yAxisLabel = dataType === 'riverdepth' ? 'River Depth (m)' : 'Streamflow (m³/s)';
  const tooltipLabel = dataType === 'riverdepth' ? 'River Depth' : 'Streamflow';
  const displayUnit = dataType === 'riverdepth' ? 'm' : 'm³/s';
  const dataKey = dataType === 'riverdepth' ? 'depth' : 'streamflow';
  
  if (!timeSeriesData || timeSeriesData.length === 0) {
    return <div className="chart-no-data" style={{ padding: '20px', textAlign: 'center' }}>No data available.</div>;
  }
  
  // Split data into historical and forecast based on today's date
  const chartData = React.useMemo(() => {
    const today = new Date();
    const currentDate = new Date(today.getFullYear(), today.getMonth(), today.getDate(), 12, 0, 0);
    
    // Find today's index
    let todayIndex = -1;
    for (let i = 0; i < timeSeriesData.length; i++) {
      const itemTime = new Date(timeSeriesData[i].timestamp);
      if (itemTime.getTime() >= currentDate.getTime()) {
        todayIndex = i;
        break;
      }
    }
    
    // Add forecast data keys to all data points
    const combined = timeSeriesData.map((item, index) => {
      const newItem = { ...item };
      if (index >= todayIndex && todayIndex !== -1) {
        // From today onwards, show as forecast (dotted)
        newItem[`${dataKey}Forecast`] = newItem[dataKey];
        newItem[dataKey] = null;
      } else {
        // Before today, show as historical (solid) only
        newItem[`${dataKey}Forecast`] = null;
      }
      return newItem;
    });

    // Add connection point: duplicate the last historical point as first forecast point
    if (todayIndex > 0 && todayIndex !== -1) {
      const lastHistoricalPoint = combined[todayIndex - 1];
      if (lastHistoricalPoint && !lastHistoricalPoint[`${dataKey}Forecast`]) {
        lastHistoricalPoint[`${dataKey}Forecast`] = lastHistoricalPoint[dataKey];
      }
    }
    
    return combined;
  }, [timeSeriesData, dataKey]);
  
  // Calculate Y-axis domain for better scaling
  const values = chartData.flatMap(item => [item[dataKey], item[`${dataKey}Forecast`]]).filter(v => v != null && !isNaN(v));
  const minValue = Math.min(...values);
  const maxValue = Math.max(...values);
  const padding = (maxValue - minValue) * 0.1;
  const yDomain = [Math.max(0, minValue - padding), maxValue + padding];

  // Find today's data point for reference line
  const today = new Date();
  const currentDate = new Date(today.getFullYear(), today.getMonth(), today.getDate(), 12, 0, 0);
  
  const todayDataPoint = React.useMemo(() => {
    if (chartData.length === 0) return null;
    
    // Find the closest data point to today
    let closestPoint = null;
    let closestDiff = Infinity;
    
    for (let i = 0; i < chartData.length; i++) {
      const dataPoint = chartData[i];
      const itemTime = new Date(dataPoint.timestamp);
      const diff = Math.abs(itemTime.getTime() - currentDate.getTime());
      
      if (diff < closestDiff) {
        closestDiff = diff;
        closestPoint = dataPoint;
      }
    }
    
    return closestPoint;
  }, [chartData, currentDate]);


  return (
    <div className="chart-container" ref={chartRef}>
      <ResponsiveContainer width="100%" height={height}>
          <LineChart data={chartData} margin={{ top: 5, right: 5, left: 45, bottom: 30 }}>
            <defs>
              <linearGradient id="geosfmGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#1f77b4" stopOpacity={0.3}/>
                <stop offset="95%" stopColor="#1f77b4" stopOpacity={0}/>
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
            <XAxis 
              dataKey="timestamp" 
              angle={-45} 
              textAnchor="end" 
              height={30} 
              tickFormatter={(dt) => {
                const date = new Date(dt);
                return date.toLocaleDateString('en-GB', { day: '2-digit', month: 'short' });
              }} 
              minTickGap={20}
              stroke="#666"
              fontWeight={600}
              fontSize={9}
            />
            <YAxis 
              domain={yDomain}
              label={{ 
                value: yAxisLabel, 
                angle: -90, 
                position: 'insideLeft', 
                offset: -5, 
                style: { textAnchor: 'middle', fontSize: '10px', fill: '#333' } 
              }} 
              tickFormatter={(value) => {
                const num = Number(value);
                if (dataType === 'riverdepth') {
                  return num.toFixed(2);
                } else {
                  if (num >= 1000) {
                    return (num / 1000).toFixed(1) + 'k';
                  } else if (num >= 100) {
                    return num.toFixed(0);
                  } else {
                    return num.toFixed(1);
                  }
                }
              }}
              width={40}
              stroke="#666"
              fontWeight={600}
              fontSize={9}
            />
            <Tooltip 
              labelFormatter={(label) => `Date: ${new Date(label).toLocaleDateString('en-GB')}`} 
              formatter={(value) => [`${Number(value).toFixed(2)} ${displayUnit}`, tooltipLabel]}
              contentStyle={{
                backgroundColor: 'rgba(255, 255, 255, 0.95)',
                border: '1px solid #ccc',
                borderRadius: '4px',
                boxShadow: '0 2px 8px rgba(0,0,0,0.15)'
              }}
            />
            <RechartsLegend 
              wrapperStyle={{ paddingTop: '10px' }}
              iconType="line"
            />
            {/* Historical data - solid line */}
            <Line 
              type="monotone" 
              dataKey={dataKey} 
              stroke={dataType === 'riverdepth' ? '#2196F3' : '#FF6B35'} 
              name={tooltipLabel} 
              dot={false} 
              strokeWidth={2}
              activeDot={{ 
                r: 6, 
                stroke: dataType === 'riverdepth' ? '#2196F3' : '#FF6B35', 
                strokeWidth: 2, 
                fill: 'white' 
              }}
            />
            
            {/* Forecast data - dotted line (hidden from legend) */}
            <Line 
              type="monotone" 
              dataKey={`${dataKey}Forecast`} 
              stroke={dataType === 'riverdepth' ? '#2196F3' : '#FF6B35'} 
              dot={false} 
              strokeWidth={2}
              strokeDasharray="8 4"
              activeDot={{ 
                r: 6, 
                stroke: dataType === 'riverdepth' ? '#2196F3' : '#FF6B35', 
                strokeWidth: 2, 
                fill: 'white' 
              }}
              legendType="none"
            />
            
            {/* Today reference line */}
            {todayDataPoint && (
              <ReferenceLine 
                x={todayDataPoint.timestamp} 
                stroke="#FF4444" 
                strokeWidth={2}
                strokeDasharray="5 5"
                label={{ 
                  value: "Today", 
                  position: "insideTopRight",
                  offset: 5,
                  fill: "#FF4444",
                  fontSize: 10,
                  fontWeight: 600
                }}
              />
            )}
          </LineChart>
        </ResponsiveContainer>
    </div>
  );
};