/**
 * Timeseries Chart Widget
 * Shows historical and forecast trends for selected region
 * Allows model selection and comparison
 */
import React, { useState, useEffect, useMemo } from "react";
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
  Area,
  ComposedChart,
} from "recharts";
import { isEmpty } from "lodash";

import { CMS_API } from "@/utils/constants";
import { DEFAULT_THRESHOLDS } from "@/utils/multimodal-config";
import Loader from "@/components/ui/loader";

import "./styles.scss";

// Available flood models
const FLOOD_MODELS = [
  { id: "geosfm", name: "GeoSFM", color: "#1976d2", description: "Geospatial Stream Flow Model" },
  { id: "floodproof", name: "Floodproof", color: "#388e3c", description: "CIMA Floodproof Model" },
  { id: "mike_hydro_rfe", name: "MIKE RFE", color: "#f57c00", description: "MIKE Hydro with RFE" },
  { id: "mike_hydro_chirp", name: "MIKE CHIRPS", color: "#7b1fa2", description: "MIKE Hydro with CHIRPS" },
  { id: "mike_hydro_imerg", name: "MIKE IMERG", color: "#c62828", description: "MIKE Hydro with IMERG" },
];

// Alert thresholds - use shared config (warning: 150, alarm: 300, emergency: 450 m³/s)
const THRESHOLDS = DEFAULT_THRESHOLDS;

// Custom tooltip
const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload || payload.length === 0) return null;

  return (
    <div className="custom-tooltip">
      <div className="tooltip-date">{label}</div>
      {payload.map((entry, index) => (
        <div key={index} className="tooltip-item" style={{ color: entry.color }}>
          <span className="tooltip-name">{entry.name}:</span>
          <span className="tooltip-value">{entry.value?.toFixed(1)} m³/s</span>
        </div>
      ))}
    </div>
  );
};

const TimeseriesChartWidget = ({
  params,
  selectedCountry,
  selectedPoint,
  forecastDate,
}) => {
  const [loading, setLoading] = useState(false);
  const [chartData, setChartData] = useState([]);
  const [selectedModels, setSelectedModels] = useState(["geosfm", "floodproof"]);
  const [timeRange, setTimeRange] = useState("7d"); // 7d, 14d, 30d, historical
  const [showThresholds, setShowThresholds] = useState(true);
  const [showTrend, setShowTrend] = useState(true);

  // Fetch timeseries data - NO DEMO DATA, API only
  useEffect(() => {
    const fetchTimeseriesData = async () => {
      if (!forecastDate) {
        setChartData([]);
        return;
      }

      setLoading(true);
      try {
        const queryParams = new URLSearchParams({
          date: forecastDate,
          range: timeRange,
          ...(selectedCountry && { country: selectedCountry }),
          ...(selectedPoint && { point_id: selectedPoint }),
        });

        // Try multimodal geojson endpoint for forecast data
        const response = await fetch(`${CMS_API}/multimodal/geojson/?${queryParams}`);

        if (response.ok) {
          const data = await response.json();
          // Transform GeoJSON features to timeseries format
          const transformedData = transformGeoJSONToTimeseries(data);
          setChartData(transformedData);
        } else {
          console.error("Failed to fetch timeseries data:", response.status);
          setChartData([]);
        }
      } catch (error) {
        console.error("Error fetching timeseries:", error);
        setChartData([]);
      } finally {
        setLoading(false);
      }
    };

    fetchTimeseriesData();
  }, [forecastDate, timeRange, selectedCountry, selectedPoint]);

  // Transform GeoJSON response to timeseries format
  const transformGeoJSONToTimeseries = (geojson) => {
    if (!geojson?.features?.length) return [];

    // Get forecasts from first feature (all features have same dates)
    const firstFeature = geojson.features.find(f => f.properties?.forecasts?.length > 0);
    if (!firstFeature?.properties?.forecasts) return [];

    // Aggregate all points to get regional averages
    const dateMap = {};

    geojson.features.forEach(feature => {
      const forecasts = feature.properties?.forecasts || [];
      forecasts.forEach(forecast => {
        const date = forecast.date;
        if (!dateMap[date]) {
          dateMap[date] = {
            date,
            dateLabel: new Date(date).toLocaleDateString("en-US", { month: "short", day: "numeric" }),
            isForecast: new Date(date) >= new Date(forecastDate),
            geosfm_sum: 0, geosfm_count: 0,
            floodproof_sum: 0, floodproof_count: 0,
            mike_hydro_rfe_sum: 0, mike_hydro_rfe_count: 0,
            mike_hydro_chirp_sum: 0, mike_hydro_chirp_count: 0,
            mike_hydro_imerg_sum: 0, mike_hydro_imerg_count: 0,
            daily_avg_sum: 0, daily_avg_count: 0,
          };
        }

        if (forecast.GeoSFM != null) { dateMap[date].geosfm_sum += forecast.GeoSFM; dateMap[date].geosfm_count++; }
        if (forecast.Floodproof != null) { dateMap[date].floodproof_sum += forecast.Floodproof; dateMap[date].floodproof_count++; }
        if (forecast.Mike_Hydro_RFE != null) { dateMap[date].mike_hydro_rfe_sum += forecast.Mike_Hydro_RFE; dateMap[date].mike_hydro_rfe_count++; }
        if (forecast.Mike_Hydro_CHIRP != null) { dateMap[date].mike_hydro_chirp_sum += forecast.Mike_Hydro_CHIRP; dateMap[date].mike_hydro_chirp_count++; }
        if (forecast.Mike_Hydro_IMERG != null) { dateMap[date].mike_hydro_imerg_sum += forecast.Mike_Hydro_IMERG; dateMap[date].mike_hydro_imerg_count++; }
        if (forecast.daily_avg != null) { dateMap[date].daily_avg_sum += forecast.daily_avg; dateMap[date].daily_avg_count++; }
      });
    });

    // Convert to averages
    return Object.values(dateMap)
      .map(d => ({
        date: d.date,
        dateLabel: d.dateLabel,
        isForecast: d.isForecast,
        geosfm: d.geosfm_count > 0 ? d.geosfm_sum / d.geosfm_count : null,
        floodproof: d.floodproof_count > 0 ? d.floodproof_sum / d.floodproof_count : null,
        mike_hydro_rfe: d.mike_hydro_rfe_count > 0 ? d.mike_hydro_rfe_sum / d.mike_hydro_rfe_count : null,
        mike_hydro_chirp: d.mike_hydro_chirp_count > 0 ? d.mike_hydro_chirp_sum / d.mike_hydro_chirp_count : null,
        mike_hydro_imerg: d.mike_hydro_imerg_count > 0 ? d.mike_hydro_imerg_sum / d.mike_hydro_imerg_count : null,
        ensemble_avg: d.daily_avg_count > 0 ? d.daily_avg_sum / d.daily_avg_count : null,
      }))
      .sort((a, b) => new Date(a.date) - new Date(b.date));
  };

  // Toggle model selection
  const toggleModel = (modelId) => {
    setSelectedModels((prev) => {
      if (prev.includes(modelId)) {
        return prev.filter((id) => id !== modelId);
      }
      return [...prev, modelId];
    });
  };

  // Calculate trend
  const trendInfo = useMemo(() => {
    if (chartData.length < 2) return null;

    const forecastData = chartData.filter((d) => d.isForecast);
    if (forecastData.length < 2) return null;

    const firstValue = forecastData[0]?.ensemble_avg || forecastData[0]?.geosfm || 0;
    const lastValue = forecastData[forecastData.length - 1]?.ensemble_avg ||
                      forecastData[forecastData.length - 1]?.geosfm || 0;
    const change = ((lastValue - firstValue) / firstValue) * 100;

    return {
      direction: change > 5 ? "increasing" : change < -5 ? "decreasing" : "stable",
      change: Math.abs(change).toFixed(1),
    };
  }, [chartData]);

  return (
    <div className="c-timeseries-chart">
      <div className="widget-header">
        <div className="header-left">
          <h3>Forecast Timeseries</h3>
          <p>
            {selectedCountry ? `${selectedCountry} - ` : "Regional "}
            Multi-model discharge forecast
          </p>
        </div>

        {trendInfo && showTrend && (
          <div className={`trend-indicator ${trendInfo.direction}`}>
            <span className="trend-icon">
              {trendInfo.direction === "increasing" ? "📈" :
               trendInfo.direction === "decreasing" ? "📉" : "➡️"}
            </span>
            <span className="trend-text">
              {trendInfo.direction === "stable" ? "Stable" :
               `${trendInfo.direction} ${trendInfo.change}%`}
            </span>
          </div>
        )}
      </div>

      {/* Controls */}
      <div className="chart-controls">
        <div className="time-range-selector">
          <label>Time Range:</label>
          <div className="range-buttons">
            {[
              { value: "7d", label: "7 Days" },
              { value: "14d", label: "14 Days" },
              { value: "30d", label: "30 Days" },
              { value: "historical", label: "Historical" },
            ].map((range) => (
              <button
                key={range.value}
                className={`range-btn ${timeRange === range.value ? "active" : ""}`}
                onClick={() => setTimeRange(range.value)}
              >
                {range.label}
              </button>
            ))}
          </div>
        </div>

        <div className="chart-options">
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={showThresholds}
              onChange={(e) => setShowThresholds(e.target.checked)}
            />
            Show Thresholds
          </label>
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={showTrend}
              onChange={(e) => setShowTrend(e.target.checked)}
            />
            Show Trend
          </label>
        </div>
      </div>

      {/* Model Selection */}
      <div className="model-selector">
        <label>Models:</label>
        <div className="model-chips">
          {FLOOD_MODELS.map((model) => (
            <button
              key={model.id}
              className={`model-chip ${selectedModels.includes(model.id) ? "active" : ""}`}
              style={{
                borderColor: model.color,
                backgroundColor: selectedModels.includes(model.id) ? model.color : "transparent",
                color: selectedModels.includes(model.id) ? "white" : model.color,
              }}
              onClick={() => toggleModel(model.id)}
              title={model.description}
            >
              {model.name}
            </button>
          ))}
          <button
            className={`model-chip ensemble ${selectedModels.length === FLOOD_MODELS.length ? "active" : ""}`}
            onClick={() => {
              if (selectedModels.length === FLOOD_MODELS.length) {
                setSelectedModels(["geosfm"]);
              } else {
                setSelectedModels(FLOOD_MODELS.map((m) => m.id));
              }
            }}
          >
            {selectedModels.length === FLOOD_MODELS.length ? "Single" : "All Models"}
          </button>
        </div>
      </div>

      {/* Chart */}
      <div className="chart-container">
        {loading ? (
          <div className="chart-loader"><Loader /></div>
        ) : isEmpty(chartData) ? (
          <div className="no-data">No timeseries data available</div>
        ) : (
          <ResponsiveContainer width="100%" height={350}>
            <ComposedChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#eee" />
              <XAxis
                dataKey="dateLabel"
                tick={{ fontSize: 11 }}
                tickLine={false}
              />
              <YAxis
                tick={{ fontSize: 11 }}
                tickLine={false}
                label={{ value: "Discharge (m³/s)", angle: -90, position: "insideLeft", fontSize: 12 }}
              />
              <Tooltip content={<CustomTooltip />} />
              <Legend />

              {/* Threshold lines */}
              {showThresholds && (
                <>
                  <ReferenceLine y={THRESHOLDS.warning} stroke="#FFC107" strokeDasharray="5 5" label="Warning" />
                  <ReferenceLine y={THRESHOLDS.alarm} stroke="#FF9800" strokeDasharray="5 5" label="Alarm" />
                  <ReferenceLine y={THRESHOLDS.emergency} stroke="#F44336" strokeDasharray="5 5" label="Emergency" />
                </>
              )}

              {/* Today reference line */}
              <ReferenceLine
                x={chartData.find((d) => d.isForecast)?.dateLabel}
                stroke="#666"
                strokeDasharray="3 3"
                label={{ value: "Today", position: "top", fontSize: 10 }}
              />

              {/* Model lines */}
              {selectedModels.map((modelId) => {
                const model = FLOOD_MODELS.find((m) => m.id === modelId);
                if (!model) return null;

                return (
                  <Line
                    key={modelId}
                    type="monotone"
                    dataKey={modelId}
                    name={model.name}
                    stroke={model.color}
                    strokeWidth={2}
                    dot={false}
                    activeDot={{ r: 5 }}
                  />
                );
              })}

              {/* Ensemble range area (if showing all models) */}
              {selectedModels.length >= 3 && (
                <Area
                  type="monotone"
                  dataKey="ensemble_max"
                  stackId="ensemble"
                  stroke="none"
                  fill="#e0e0e0"
                  fillOpacity={0.3}
                />
              )}
            </ComposedChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Legend / Info */}
      <div className="chart-legend">
        <div className="legend-item">
          <span className="legend-line historical"></span>
          Historical data
        </div>
        <div className="legend-item">
          <span className="legend-line forecast"></span>
          Forecast data
        </div>
        {showThresholds && (
          <>
            <div className="legend-item threshold warning">Warning: {THRESHOLDS.warning} m³/s</div>
            <div className="legend-item threshold alarm">Alarm: {THRESHOLDS.alarm} m³/s</div>
            <div className="legend-item threshold emergency">Emergency: {THRESHOLDS.emergency} m³/s</div>
          </>
        )}
      </div>
    </div>
  );
};

TimeseriesChartWidget.propTypes = {
  params: PropTypes.object,
  selectedCountry: PropTypes.string,
  selectedPoint: PropTypes.string,
  forecastDate: PropTypes.string,
};

export default TimeseriesChartWidget;
