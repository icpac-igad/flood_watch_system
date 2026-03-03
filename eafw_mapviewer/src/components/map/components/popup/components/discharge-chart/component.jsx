import React, { useMemo } from "react";
import PropTypes from "prop-types";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";
import { format, addHours } from "date-fns";

import "./styles.scss";

/**
 * DischargeChart Component
 * Displays discharge forecast time series data for Floodproofs stations
 * Similar to FloodWatch implementation
 */
const DischargeChart = ({
  gfsData,
  iconData,
  warningThreshold,
  alarmThreshold,
  emergencyThreshold,
  stationName,
}) => {
  const chartData = useMemo(() => {
    if (!gfsData && !iconData) return [];

    // Parse comma-separated values
    const gfsValues = gfsData
      ? gfsData.split(",").map((v) => {
          const num = parseFloat(v.trim());
          return num === -9998 || isNaN(num) ? null : num;
        })
      : [];

    const iconValues = iconData
      ? iconData.split(",").map((v) => {
          const num = parseFloat(v.trim());
          return num === -9998 || isNaN(num) ? null : num;
        })
      : [];

    const maxLength = Math.max(gfsValues.length, iconValues.length);

    // Create time series starting from now
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 12, 0, 0);
    const data = [];

    for (let i = 0; i < maxLength; i++) {
      const timestamp = addHours(now, i * 3); // Assuming 3-hour intervals
      const isHistorical = timestamp < today;

      data.push({
        time: format(timestamp, "dd MMM"),
        fullTime: timestamp,
        timestamp: timestamp.getTime(),
        // Historical data (solid lines)
        gfs: isHistorical ? gfsValues[i] : null,
        icon: isHistorical ? iconValues[i] : null,
        // Forecast data (dashed lines)
        gfsForecast: !isHistorical ? gfsValues[i] : null,
        iconForecast: !isHistorical ? iconValues[i] : null,
      });
    }

    // Add connection point at today - duplicate the last historical point as first forecast point
    const todayIndex = data.findIndex(d => d.fullTime >= today);
    if (todayIndex > 0 && todayIndex < data.length) {
      const lastHistoricalPoint = data[todayIndex - 1];
      if (lastHistoricalPoint && !lastHistoricalPoint.gfsForecast) {
        lastHistoricalPoint.gfsForecast = lastHistoricalPoint.gfs;
        lastHistoricalPoint.iconForecast = lastHistoricalPoint.icon;
      }
    }

    return data;
  }, [gfsData, iconData]);

  // Find today's data point for reference line
  const todayDataPoint = useMemo(() => {
    if (chartData.length === 0) return null;

    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 12, 0, 0);

    // Find the data point closest to today
    let closestPoint = null;
    let closestDiff = Infinity;

    for (let i = 0; i < chartData.length; i++) {
      const dataPoint = chartData[i];
      const diff = Math.abs(dataPoint.fullTime.getTime() - today.getTime());

      if (diff < closestDiff) {
        closestDiff = diff;
        closestPoint = dataPoint;
      }
    }

    return closestPoint;
  }, [chartData]);

  if (chartData.length === 0) {
    return (
      <div className="c-discharge-chart-empty">
        <p>No discharge forecast data available</p>
      </div>
    );
  }

  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      return (
        <div className="custom-tooltip">
          <p className="label">{payload[0].payload.time}</p>
          {payload.map((entry, index) => (
            <p key={index} style={{ color: entry.color }}>
              {entry.name}: {entry.value ? entry.value.toFixed(2) : "N/A"} m³/s
            </p>
          ))}
        </div>
      );
    }
    return null;
  };

  // Get forecast date range for title
  const dateRange = useMemo(() => {
    if (chartData.length === 0) return '';

    const startDate = chartData[0].fullTime;
    const endDate = chartData[chartData.length - 1].fullTime;

    return `${format(startDate, 'dd MMM yyyy')} - ${format(endDate, 'dd MMM yyyy')}`;
  }, [chartData]);

  return (
    <div className="c-discharge-chart">
      <div className="chart-header">
        <h4>Discharge Forecast - {stationName || "Station"}</h4>
        <p style={{ margin: '5px 0 0 0', fontSize: '11px', color: '#666' }}>{dateRange}</p>
      </div>

      <ResponsiveContainer width="100%" height={300}>
        <LineChart
          data={chartData}
          margin={{ top: 10, right: 10, left: 0, bottom: 5 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
          <XAxis
            dataKey="time"
            angle={-45}
            textAnchor="end"
            height={80}
            tick={{ fontSize: 9 }}
            stroke="#666"
            fontWeight={600}
          />
          <YAxis
            label={{
              value: "Discharge (m³/s)",
              angle: -90,
              position: "insideLeft",
              offset: -5,
              style: { textAnchor: 'middle', fontSize: '10px', fill: '#333' },
            }}
            tick={{ fontSize: 9 }}
            stroke="#666"
            fontWeight={600}
            width={40}
          />
          <Tooltip
            content={<CustomTooltip />}
            contentStyle={{
              backgroundColor: 'rgba(255, 255, 255, 0.95)',
              border: '1px solid #ccc',
              borderRadius: '4px',
              boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
              fontSize: '11px'
            }}
          />
          <Legend
            wrapperStyle={{ fontSize: 10, paddingTop: 2 }}
            iconType="line"
          />

          {/* Threshold lines */}
          {warningThreshold > 0 && (
            <ReferenceLine
              y={warningThreshold}
              stroke="#FFA726"
              strokeDasharray="5 5"
              label={{
                value: "Moderate",
                position: "right",
                fill: "#FFA726",
                fontSize: 10,
              }}
            />
          )}
          {alarmThreshold > 0 && (
            <ReferenceLine
              y={alarmThreshold}
              stroke="#FF5722"
              strokeDasharray="5 5"
              label={{
                value: "Severe",
                position: "right",
                fill: "#FF5722",
                fontSize: 10,
              }}
            />
          )}
          {emergencyThreshold > 0 && (
            <ReferenceLine
              y={emergencyThreshold}
              stroke="#B71C1C"
              strokeDasharray="5 5"
              label={{
                value: "Extreme",
                position: "right",
                fill: "#B71C1C",
                fontSize: 10,
              }}
            />
          )}

          {/* Historical data - solid lines */}
          {gfsData && (
            <Line
              type="monotone"
              dataKey="gfs"
              stroke="#1f77b4"
              strokeWidth={2}
              name="GFS"
              dot={false}
              connectNulls
              activeDot={{ r: 6, stroke: '#1f77b4', strokeWidth: 2, fill: 'white' }}
            />
          )}
          {iconData && (
            <Line
              type="monotone"
              dataKey="icon"
              stroke="#ff7f0e"
              strokeWidth={2}
              name="ICON"
              dot={false}
              connectNulls
              activeDot={{ r: 6, stroke: '#ff7f0e', strokeWidth: 2, fill: 'white' }}
            />
          )}

          {/* Forecast data - dashed lines (hidden from legend) */}
          {gfsData && (
            <Line
              type="monotone"
              dataKey="gfsForecast"
              stroke="#1f77b4"
              strokeWidth={2}
              dot={false}
              strokeDasharray="8 4"
              connectNulls
              activeDot={{ r: 6, stroke: '#1f77b4', strokeWidth: 2, fill: 'white' }}
              legendType="none"
            />
          )}
          {iconData && (
            <Line
              type="monotone"
              dataKey="iconForecast"
              stroke="#ff7f0e"
              strokeWidth={2}
              dot={false}
              strokeDasharray="8 4"
              connectNulls
              activeDot={{ r: 6, stroke: '#ff7f0e', strokeWidth: 2, fill: 'white' }}
              legendType="none"
            />
          )}

          {/* Today reference line */}
          {todayDataPoint && (
            <ReferenceLine
              x={todayDataPoint.time}
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

// Helper function to determine current status
const getCurrentStatus = (data, warning, alarm, emergency) => {
  if (!data || data.length === 0) return "Unknown";

  const latestGfs = data[data.length - 1]?.gfs || 0;
  const latestIcon = data[data.length - 1]?.icon || 0;
  const currentDischarge = Math.max(latestGfs, latestIcon);

  if (currentDischarge >= emergency && emergency > 0) {
    return <span className="status-emergency">Extreme</span>;
  } else if (currentDischarge >= alarm && alarm > 0) {
    return <span className="status-alarm">Severe</span>;
  } else if (currentDischarge >= warning && warning > 0) {
    return <span className="status-warning">Moderate</span>;
  }
  return <span className="status-normal">Normal</span>;
};

DischargeChart.propTypes = {
  gfsData: PropTypes.string,
  iconData: PropTypes.string,
  warningThreshold: PropTypes.number,
  alarmThreshold: PropTypes.number,
  emergencyThreshold: PropTypes.number,
  stationName: PropTypes.string,
};

export default DischargeChart;
