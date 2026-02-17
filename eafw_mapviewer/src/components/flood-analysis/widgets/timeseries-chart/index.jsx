/**
 * Timeseries Chart Widget
 * Fixed-lead historical model behavior + latest-run forecast (separate sections)
 */
import React, { useState, useEffect, useMemo } from "react";
import PropTypes from "prop-types";
import {
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
  LineChart,
} from "recharts";
import { isEmpty } from "lodash";

import { DEFAULT_THRESHOLDS } from "@/utils/multimodal-config";
import Loader from "@/components/ui/loader";

import "./styles.scss";

const FLOOD_MODELS = [
  { id: "geosfm", apiKey: "GeoSFM", name: "GeoSFM", color: "#1976d2", description: "Geospatial Stream Flow Model" },
  { id: "floodproof", apiKey: "Floodproof", name: "Floodproof", color: "#388e3c", description: "CIMA Floodproof Model" },
  { id: "mike_hydro_rfe", apiKey: "Mike_Hydro_RFE", name: "MIKE RFE", color: "#f57c00", description: "MIKE Hydro with RFE" },
  { id: "mike_hydro_chirp", apiKey: "Mike_Hydro_CHIRP", name: "MIKE CHIRPS", color: "#7b1fa2", description: "MIKE Hydro with CHIRPS" },
  { id: "mike_hydro_imerg", apiKey: "Mike_Hydro_IMERG", name: "MIKE IMERG", color: "#c62828", description: "MIKE Hydro with IMERG" },
];

const HISTORY_WINDOWS = [
  { value: "30d", label: "30 Days", days: 30 },
  { value: "90d", label: "90 Days", days: 90 },
  { value: "180d", label: "180 Days", days: 180 },
  { value: "365d", label: "1 Year", days: 365 },
];

const LEAD_OPTIONS = [1, 3, 5, 7, 10, 14];
const FORECAST_HORIZON_OPTIONS = [7, 14, 21, 30];

const toNumberOrNull = (value) => {
  if (value === null || value === undefined) return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
};

const formatDateLabel = (dateValue) => {
  if (!dateValue) return "";
  const dateObj = new Date(`${dateValue}T00:00:00`);
  if (Number.isNaN(dateObj.getTime())) return dateValue;
  return dateObj.toLocaleDateString("en-US", { month: "short", day: "numeric" });
};

const normalizeSeries = (series = []) => {
  if (!Array.isArray(series)) return [];

  return series
    .map((item) => {
      const point = {
        date: item.date,
        dateLabel: formatDateLabel(item.date),
        ensemble_avg: toNumberOrNull(item.daily_avg),
      };

      FLOOD_MODELS.forEach((model) => {
        point[model.apiKey] = toNumberOrNull(item[model.apiKey]);
      });

      return point;
    })
    .sort((a, b) => new Date(a.date) - new Date(b.date));
};

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload || payload.length === 0) return null;

  const validEntries = payload.filter((entry) => entry.value !== null && entry.value !== undefined);
  if (validEntries.length === 0) return null;

  return (
    <div className="custom-tooltip">
      <div className="tooltip-date">{label}</div>
      {validEntries.map((entry, index) => (
        <div key={index} className="tooltip-item" style={{ color: entry.color }}>
          <span className="tooltip-name">{entry.name}:</span>
          <span className="tooltip-value">{Number(entry.value).toFixed(1)} m³/s</span>
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
  const [historicalData, setHistoricalData] = useState([]);
  const [currentForecastData, setCurrentForecastData] = useState([]);
  const [selectedModels, setSelectedModels] = useState(["geosfm", "floodproof"]);
  const [historyWindow, setHistoryWindow] = useState("90d");
  const [leadTime, setLeadTime] = useState(1);
  const [forecastHorizon, setForecastHorizon] = useState(14);
  const [showThresholds, setShowThresholds] = useState(true);
  const [showTrend, setShowTrend] = useState(true);
  const [thresholds, setThresholds] = useState(DEFAULT_THRESHOLDS);

  const selectedHistoryDays = useMemo(
    () => HISTORY_WINDOWS.find((entry) => entry.value === historyWindow)?.days || 90,
    [historyWindow]
  );

  const selectedModelConfigs = useMemo(
    () => FLOOD_MODELS.filter((model) => selectedModels.includes(model.id)),
    [selectedModels]
  );

  useEffect(() => {
    const fetchModelBehavior = async () => {
      if (!forecastDate) {
        setHistoricalData([]);
        setCurrentForecastData([]);
        return;
      }

      setLoading(true);
      try {
        const queryParams = new URLSearchParams({
          date: forecastDate,
          lead: String(leadTime),
          history_days: String(selectedHistoryDays),
          forecast_horizon_days: String(forecastHorizon),
          ...(selectedCountry && { country: selectedCountry }),
          ...(selectedPoint && { point_id: selectedPoint }),
          ...(params?.scope && params.scope !== "all" && { scope: params.scope }),
        });

        const response = await fetch(`/api/v1/multimodal/model-behavior?${queryParams.toString()}`);

        if (!response.ok) {
          console.error("Failed to fetch model behavior data:", response.status);
          setHistoricalData([]);
          setCurrentForecastData([]);
          return;
        }

        const data = await response.json();
        setHistoricalData(normalizeSeries(data?.historical_behavior || []));
        setCurrentForecastData(normalizeSeries(data?.current_forecast || []));

        if (data?.thresholds) {
          setThresholds({
            warning: toNumberOrNull(data.thresholds.warning) ?? DEFAULT_THRESHOLDS.warning,
            alarm: toNumberOrNull(data.thresholds.alarm) ?? DEFAULT_THRESHOLDS.alarm,
            emergency: toNumberOrNull(data.thresholds.emergency) ?? DEFAULT_THRESHOLDS.emergency,
          });
        } else {
          setThresholds(DEFAULT_THRESHOLDS);
        }
      } catch (error) {
        console.error("Error fetching model behavior timeseries:", error);
        setHistoricalData([]);
        setCurrentForecastData([]);
      } finally {
        setLoading(false);
      }
    };

    fetchModelBehavior();
  }, [
    forecastDate,
    leadTime,
    selectedHistoryDays,
    forecastHorizon,
    selectedCountry,
    selectedPoint,
    params?.scope,
  ]);

  const toggleModel = (modelId) => {
    setSelectedModels((prev) => {
      if (prev.includes(modelId)) {
        if (prev.length === 1) return prev;
        return prev.filter((id) => id !== modelId);
      }
      return [...prev, modelId];
    });
  };

  const trendInfo = useMemo(() => {
    if (currentForecastData.length < 2) return null;

    const first = currentForecastData[0];
    const last = currentForecastData[currentForecastData.length - 1];
    const fallbackModelKey = selectedModelConfigs[0]?.apiKey;

    const firstValue = first?.ensemble_avg ?? (fallbackModelKey ? first?.[fallbackModelKey] : null);
    const lastValue = last?.ensemble_avg ?? (fallbackModelKey ? last?.[fallbackModelKey] : null);

    if (!Number.isFinite(firstValue) || !Number.isFinite(lastValue) || firstValue === 0) return null;

    const change = ((lastValue - firstValue) / firstValue) * 100;

    return {
      direction: change > 5 ? "increasing" : change < -5 ? "decreasing" : "stable",
      change: Math.abs(change).toFixed(1),
    };
  }, [currentForecastData, selectedModelConfigs]);

  const renderChart = (data, emptyMessage) => {
    if (loading) {
      return <div className="chart-loader"><Loader /></div>;
    }

    if (isEmpty(data)) {
      return <div className="no-data">{emptyMessage}</div>;
    }

    return (
      <ResponsiveContainer width="100%" height={320}>
        <LineChart data={data} margin={{ top: 20, right: 30, left: 20, bottom: 20 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#eee" />
          <XAxis dataKey="dateLabel" tick={{ fontSize: 11 }} tickLine={false} />
          <YAxis
            tick={{ fontSize: 11 }}
            tickLine={false}
            label={{ value: "Discharge (m\u00B3/s)", angle: -90, position: "insideLeft", fontSize: 12 }}
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend />

          {showThresholds && (
            <>
              <ReferenceLine y={thresholds.warning} stroke="#FFC107" strokeDasharray="5 5" label="Warning" />
              <ReferenceLine y={thresholds.alarm} stroke="#FF9800" strokeDasharray="5 5" label="Alarm" />
              <ReferenceLine y={thresholds.emergency} stroke="#F44336" strokeDasharray="5 5" label="Emergency" />
            </>
          )}

          {selectedModelConfigs.map((model) => (
            <Line
              key={model.id}
              type="monotone"
              dataKey={model.apiKey}
              name={model.name}
              stroke={model.color}
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 5 }}
              connectNulls={false}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    );
  };

  return (
    <div className="c-timeseries-chart">
      <div className="widget-header">
        <div className="header-left">
          <h3>Forecast Timeseries</h3>
          <p>
            {selectedCountry ? `${selectedCountry} - ` : "Regional "}
            Fixed-lead model behavior and latest-run forecast
          </p>
        </div>

        {trendInfo && showTrend && (
          <div className={`trend-indicator ${trendInfo.direction}`}>
            <span className="trend-text">
              {trendInfo.direction === "stable"
                ? "Stable"
                : `${trendInfo.direction.charAt(0).toUpperCase() + trendInfo.direction.slice(1)} ${trendInfo.change}%`}
            </span>
          </div>
        )}
      </div>

      <div className="chart-controls">
        <div className="control-group">
          <label>Historical Window:</label>
          <div className="range-buttons">
            {HISTORY_WINDOWS.map((range) => (
              <button
                key={range.value}
                className={`range-btn ${historyWindow === range.value ? "active" : ""}`}
                onClick={() => setHistoryWindow(range.value)}
              >
                {range.label}
              </button>
            ))}
          </div>
        </div>

        <div className="control-group">
          <label>Lead:</label>
          <div className="range-buttons">
            {LEAD_OPTIONS.map((leadOption) => (
              <button
                key={leadOption}
                className={`range-btn ${leadTime === leadOption ? "active" : ""}`}
                onClick={() => setLeadTime(leadOption)}
              >
                {leadOption}d
              </button>
            ))}
          </div>
        </div>

        <div className="control-group">
          <label>Forecast Horizon:</label>
          <div className="range-buttons">
            {FORECAST_HORIZON_OPTIONS.map((horizonDays) => (
              <button
                key={horizonDays}
                className={`range-btn ${forecastHorizon === horizonDays ? "active" : ""}`}
                onClick={() => setForecastHorizon(horizonDays)}
              >
                {horizonDays}d
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
        </div>
      </div>

      <div className="chart-sections">
        <section className="chart-section">
          <h4>Historical Model Behaviour (Fixed Lead = {leadTime} day{leadTime > 1 ? "s" : ""})</h4>
          <p className="section-caption">
            Fair model comparison using a standardized lead time over the selected historical window.
          </p>
          <div className="chart-container">
            {renderChart(
              historicalData,
              "No historical fixed-lead data available for this selection"
            )}
          </div>
        </section>

        <section className="chart-section">
          <h4>Current Forecast (Latest Run)</h4>
          <p className="section-caption">
            Next {forecastHorizon} days from run date {forecastDate || "-"}.
          </p>
          <div className="chart-container">
            {renderChart(
              currentForecastData,
              "No latest-run forecast data available for this selection"
            )}
          </div>
        </section>
      </div>

      <div className="chart-legend">
        {showThresholds && (
          <>
            <div className="legend-item threshold warning">Warning: {thresholds.warning} m³/s</div>
            <div className="legend-item threshold alarm">Alarm: {thresholds.alarm} m³/s</div>
            <div className="legend-item threshold emergency">Emergency: {thresholds.emergency} m³/s</div>
          </>
        )}
      </div>
    </div>
  );
};

TimeseriesChartWidget.propTypes = {
  params: PropTypes.object,
  selectedCountry: PropTypes.string,
  selectedPoint: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  forecastDate: PropTypes.string,
};

export default TimeseriesChartWidget;
