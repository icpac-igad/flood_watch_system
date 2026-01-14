import React, { useMemo, useState, useEffect } from "react";
import PropTypes from "prop-types";
import {
  ComposedChart,
  Line,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";
import { format, parseISO, isAfter, startOfDay } from "date-fns";

// Import shared configuration - single source of truth
import {
  DEFAULT_THRESHOLDS,
  ALERT_COLORS,
  WATER_COLORS,
  calculateAlertLevel,
  getAlertColor,
  getWaterColors,
  getTodayStr,
} from "@/utils/multimodal-config";

import "./styles.scss";

// =============================================================================
// MODEL CONFIGURATION
// =============================================================================

/** Colors for individual forecast models */
const MODEL_COLORS = {
  daily_avg: "#4A90D9",
  GeoSFM: "#1f77b4",
  Floodproof: "#ff7f0e",
  Mike_Hydro_RFE: "#2ca02c",
  Mike_Hydro_CHIRP: "#d62728",
  Mike_Hydro_IMERG: "#9467bd",
};

/** Human-readable labels for models */
const MODEL_LABELS = {
  daily_avg: "Daily Avg",
  GeoSFM: "GeoSFM",
  Floodproof: "FloodProofs",
  Mike_Hydro_RFE: "Mike Hydro (RFE)",
  Mike_Hydro_CHIRP: "Mike Hydro (CHIRP)",
  Mike_Hydro_IMERG: "Mike Hydro (IMERG)",
};

// =============================================================================
// UTILITY FUNCTIONS
// =============================================================================

/**
 * Finds forecast data for a specific date from the forecasts array
 * Falls back to the last available date if target date not found
 * @param {Array} forecasts - Forecast data array
 * @param {string} targetDate - Optional target date (YYYY-MM-DD), defaults to today
 * @returns {object} { forecast, usedDate } - The forecast data and the date actually used
 */
const findForecastForDate = (forecasts, targetDate = null) => {
  if (!Array.isArray(forecasts) || forecasts.length === 0) {
    return { forecast: null, usedDate: null };
  }

  const dateStr = targetDate || getTodayStr();

  // Try to find forecast for target date
  let forecast = forecasts.find((f) => {
    if (!f.date) return false;
    const forecastDateStr = f.date.split("T")[0];
    return forecastDateStr === dateStr;
  });

  // If found, return it with the target date
  if (forecast) {
    return { forecast, usedDate: dateStr };
  }

  // Fallback: use the last available date in the forecasts
  const lastForecast = forecasts[forecasts.length - 1];
  const lastDate = lastForecast?.date?.split("T")[0] || null;

  return { forecast: lastForecast, usedDate: lastDate };
};

/**
 * Extracts daily_avg from a forecast object
 */
const extractDailyAvg = (forecast) => {
  if (!forecast || forecast.daily_avg === undefined) {
    return 0;
  }
  const val = parseFloat(forecast.daily_avg);
  return !isNaN(val) && val >= 0 ? val : 0;
};

/**
 * Parses forecast data from JSON string or returns array directly
 */
const parseForecastData = (forecastData) => {
  if (!forecastData) return [];

  if (typeof forecastData === "string") {
    try {
      return JSON.parse(forecastData);
    } catch (e) {
      console.error("Failed to parse forecasts_json:", e);
      return [];
    }
  }

  return Array.isArray(forecastData) ? forecastData : [];
};

/**
 * Determines which models have valid data in the forecasts
 */
const detectAvailableModels = (forecasts) => {
  const models = new Set();

  forecasts.forEach((f) => {
    Object.keys(f).forEach((key) => {
      if (key === "date" || key === "daily_max" || key === "daily_min") {
        return;
      }
      if (MODEL_COLORS[key]) {
        const val = parseFloat(f[key]);
        if (!isNaN(val) && val > 0 && val < 1e10) {
          models.add(key);
        }
      }
    });
  });

  const hasDailyAvg = forecasts.some(
    (f) => f.daily_avg !== undefined && parseFloat(f.daily_avg) > 0
  );
  if (hasDailyAvg) {
    models.add("daily_avg");
  }

  return Array.from(models);
};

/**
 * Transforms forecast data into chart-ready format
 */
const transformForChart = (forecasts) => {
  const today = startOfDay(new Date());
  const firstDate = forecasts[0]?.date || "";
  const hasHourlyData = firstDate.includes("T") || firstDate.includes(" ");

  const data = forecasts.map((f) => {
    let displayDate;
    let isForecast = false;

    try {
      const parsedDate = parseISO(f.date);
      displayDate = hasHourlyData
        ? format(parsedDate, "dd MMM HH:mm")
        : format(parsedDate, "dd MMM");
      isForecast = isAfter(startOfDay(parsedDate), today);
    } catch (e) {
      displayDate = f.date;
    }

    const entry = {
      date: f.date,
      displayDate,
      isForecast,
    };

    Object.keys(MODEL_COLORS).forEach((model) => {
      if (f[model] !== undefined) {
        const val = parseFloat(f[model]);
        if (!isNaN(val) && val >= 0 && val < 1e10) {
          if (isForecast) {
            entry[`${model}_forecast`] = val;
          } else {
            entry[model] = val;
          }
        }
      }
    });

    return entry;
  });

  // For smooth line transition
  for (let i = 1; i < data.length; i++) {
    if (data[i].isForecast && !data[i - 1].isForecast) {
      Object.keys(MODEL_COLORS).forEach((model) => {
        if (data[i - 1][model] !== undefined) {
          data[i - 1][`${model}_forecast`] = data[i - 1][model];
        }
      });
      break;
    }
  }

  return data;
};

/**
 * Gets the date range string from forecasts
 */
const getDateRange = (forecasts) => {
  if (!forecasts.length) return "";

  const startDate = forecasts[0]?.date;
  const endDate = forecasts[forecasts.length - 1]?.date;

  if (!startDate || !endDate) return "";

  try {
    return `${format(parseISO(startDate), "dd MMM yyyy")} - ${format(parseISO(endDate), "dd MMM yyyy")}`;
  } catch (e) {
    return "";
  }
};

/**
 * Finds today's display date for the reference line
 */
const findTodayDisplayDate = (chartData) => {
  const today = startOfDay(new Date());

  for (const d of chartData) {
    try {
      const forecastDate = startOfDay(parseISO(d.date));
      if (
        forecastDate.getTime() === today.getTime() ||
        isAfter(forecastDate, today)
      ) {
        return d.displayDate;
      }
    } catch (e) {
      // Skip invalid dates
    }
  }

  return null;
};

// =============================================================================
// SUB-COMPONENTS
// =============================================================================

/**
 * Alert badge component - uses shared colors
 */
const AlertBadge = ({ level }) => {
  const color = getAlertColor(level);

  return (
    <span className="alert-badge" style={{ backgroundColor: color }}>
      {level?.toUpperCase() || "NORMAL"}
    </span>
  );
};

AlertBadge.propTypes = {
  level: PropTypes.string,
};

/**
 * Chart tooltip component - uses shared colors
 */
const ChartTooltip = ({ active, payload, label, thresholds }) => {
  if (!active || !payload || !payload.length) {
    return null;
  }

  const dataPoint = payload[0]?.payload || {};

  const modelEntries = [];
  Object.keys(MODEL_COLORS).forEach((model) => {
    const historicalVal = dataPoint[model];
    const forecastVal = dataPoint[`${model}_forecast`];

    const value = historicalVal ?? forecastVal;
    const isForecast = forecastVal !== undefined && historicalVal === undefined;

    if (value !== undefined && value !== null && !isNaN(value)) {
      modelEntries.push({
        model,
        value: parseFloat(value),
        isForecast,
        color: MODEL_COLORS[model],
        label: MODEL_LABELS[model] || model,
      });
    }
  });

  const dailyAvgValue = dataPoint.daily_avg ?? dataPoint.daily_avg_forecast ?? null;

  // Calculate alert level using shared function
  const alertLevel = dailyAvgValue !== null
    ? calculateAlertLevel(dailyAvgValue, thresholds)
    : "normal";
  const alertColor = getAlertColor(alertLevel);

  modelEntries.sort((a, b) => {
    if (a.model === "daily_avg") return -1;
    if (b.model === "daily_avg") return 1;
    return b.value - a.value;
  });

  return (
    <div className="custom-tooltip">
      <p className="tooltip-date">{label}</p>
      <p
        className="tooltip-alert"
        style={{ color: alertColor, fontWeight: "bold" }}
      >
        Alert: {alertLevel.charAt(0).toUpperCase() + alertLevel.slice(1)}
      </p>
      <div className="tooltip-models">
        {modelEntries.map((item, index) => (
          <p key={index} style={{ color: item.color, margin: "2px 0" }}>
            <span
              style={{ fontWeight: item.model === "daily_avg" ? "bold" : "normal" }}
            >
              {item.label}
            </span>
            {item.isForecast ? " (fcst)" : ""}: {item.value.toFixed(4)} m³/s
          </p>
        ))}
      </div>
    </div>
  );
};

ChartTooltip.propTypes = {
  active: PropTypes.bool,
  payload: PropTypes.array,
  label: PropTypes.string,
  thresholds: PropTypes.object,
};

/**
 * Renders model lines for either historical or forecast data
 */
const ModelLines = ({ models, isForecast }) => {
  const suffix = isForecast ? "_forecast" : "";

  return (
    <>
      {models.includes("GeoSFM") && (
        <Line
          type="natural"
          dataKey={`GeoSFM${suffix}`}
          stroke={MODEL_COLORS.GeoSFM}
          strokeWidth={2}
          strokeDasharray="4 4"
          dot={{ r: 2, fill: MODEL_COLORS.GeoSFM }}
          connectNulls
          activeDot={{ r: 5 }}
        />
      )}
      {models.includes("Floodproof") && (
        <Line
          type="natural"
          dataKey={`Floodproof${suffix}`}
          stroke={MODEL_COLORS.Floodproof}
          strokeWidth={2}
          strokeDasharray="4 4"
          dot={{ r: 2, fill: MODEL_COLORS.Floodproof }}
          connectNulls
          activeDot={{ r: 5 }}
        />
      )}
      {models.includes("Mike_Hydro_RFE") && (
        <Line
          type="natural"
          dataKey={`Mike_Hydro_RFE${suffix}`}
          stroke={MODEL_COLORS.Mike_Hydro_RFE}
          strokeWidth={2}
          strokeDasharray="4 4"
          dot={{ r: 2, fill: MODEL_COLORS.Mike_Hydro_RFE }}
          connectNulls
          activeDot={{ r: 5 }}
        />
      )}
      {models.includes("Mike_Hydro_CHIRP") && (
        <Line
          type="natural"
          dataKey={`Mike_Hydro_CHIRP${suffix}`}
          stroke={MODEL_COLORS.Mike_Hydro_CHIRP}
          strokeWidth={2}
          strokeDasharray="4 4"
          dot={{ r: 2, fill: MODEL_COLORS.Mike_Hydro_CHIRP }}
          connectNulls
          activeDot={{ r: 5 }}
        />
      )}
      {models.includes("Mike_Hydro_IMERG") && (
        <Line
          type="natural"
          dataKey={`Mike_Hydro_IMERG${suffix}`}
          stroke={MODEL_COLORS.Mike_Hydro_IMERG}
          strokeWidth={2}
          strokeDasharray="4 4"
          dot={{ r: 2, fill: MODEL_COLORS.Mike_Hydro_IMERG }}
          connectNulls
          activeDot={{ r: 5 }}
        />
      )}
    </>
  );
};

ModelLines.propTypes = {
  models: PropTypes.array.isRequired,
  isForecast: PropTypes.bool,
};

// =============================================================================
// MAIN COMPONENT
// =============================================================================

/**
 * MultiModelChart Component
 * Displays multi-model ensemble forecast data as a line chart
 * Uses shared configuration from multimodal-config.js for consistency
 */
const MultiModelChart = ({
  forecastsJson,
  adminName,
  pointId,
  hybasId,
  selectedDate,
  thresholds: configThresholds,
}) => {
  // Use shared default thresholds
  const thresholds = configThresholds || DEFAULT_THRESHOLDS;
  const [fetchedData, setFetchedData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Fetch fresh data from API when selectedDate changes
  useEffect(() => {
    if (!pointId && !adminName) {
      console.log("[MultiModelChart] No pointId or adminName, using forecastsJson directly");
      return;
    }

    const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "";

    const fetchForecastData = async () => {
      setLoading(true);
      setError(null);

      try {
        let url = `${API_BASE_URL}/api/multimodal/geojson/`;
        if (selectedDate) {
          url += `?date=${selectedDate}`;
        }

        console.log(
          `[MultiModelChart] Fetching for date: ${selectedDate || "latest"}, pointId: ${pointId}, adminName: ${adminName}`
        );
        const response = await fetch(url);
        if (!response.ok) {
          throw new Error("Failed to fetch forecast data");
        }

        const geojson = await response.json();

        // Find feature by point_id first (exact match), then fall back to admin_name
        let feature = null;
        if (pointId) {
          feature = geojson.features?.find(
            (f) => String(f.properties?.point_id) === String(pointId)
          );
        }
        if (!feature && adminName) {
          feature = geojson.features?.find(
            (f) => f.properties?.admin_name === adminName
          );
        }

        if (feature?.properties?.forecasts) {
          console.log(
            `[MultiModelChart] Found fresh data for pointId: ${pointId || "N/A"}, adminName: ${adminName}`
          );
          setFetchedData(feature.properties.forecasts);
        } else {
          console.warn("[MultiModelChart] No feature found, using fallback");
        }
      } catch (err) {
        console.error("Error fetching forecast data:", err);
      } finally {
        setLoading(false);
      }
    };

    fetchForecastData();
  }, [pointId, adminName, selectedDate]);

  // Process data using memoization
  const {
    chartData,
    availableModels,
    dateRange,
    todayDisplayDate,
    alertLevel,
    todayDailyAvg,
    actualDate,
    waterColors,
  } = useMemo(() => {
    const forecastData = fetchedData || forecastsJson;
    const forecasts = parseForecastData(forecastData);

    if (!forecasts.length) {
      return {
        chartData: [],
        availableModels: [],
        dateRange: "",
        todayDisplayDate: null,
        alertLevel: "normal",
        todayDailyAvg: 0,
        actualDate: null,
        waterColors: getWaterColors("normal"),
      };
    }

    const models = detectAvailableModels(forecasts);
    const data = transformForChart(forecasts);

    // Find forecast for selected date (or today if not specified) and extract daily_avg
    // Falls back to last available date if target date not found
    const { forecast: targetForecast, usedDate } = findForecastForDate(forecasts, selectedDate);
    const dailyAvg = targetForecast
      ? extractDailyAvg(targetForecast)
      : extractDailyAvg(forecasts[0]);

    // Use shared function to calculate alert level - ensures consistency with point colors
    const level = calculateAlertLevel(dailyAvg, thresholds);

    console.log(`[MultiModelChart] selectedDate=${selectedDate}, usedDate=${usedDate}, dailyAvg=${dailyAvg}, alertLevel=${level}`);

    return {
      chartData: data,
      availableModels: models,
      dateRange: getDateRange(forecasts),
      todayDisplayDate: findTodayDisplayDate(data),
      alertLevel: level,
      todayDailyAvg: dailyAvg,
      actualDate: usedDate,
      waterColors: getWaterColors(level),
    };
  }, [forecastsJson, fetchedData, thresholds, selectedDate]);

  // Loading state
  if (loading) {
    return (
      <div className="c-multimodel-chart-loading">
        <p>Loading forecast data...</p>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="c-multimodel-chart-error">
        <p>Error: {error}</p>
      </div>
    );
  }

  // Empty state
  if (chartData.length === 0) {
    return (
      <div className="c-multimodel-chart-empty">
        <p>No forecast data available</p>
      </div>
    );
  }

  return (
    <div className="c-multimodel-chart">
      {/* Header */}
      <div className="chart-header">
        <div className="header-title-row">
          <h4>Multi-Model Forecast{adminName ? ` - ${adminName}` : ""}</h4>
          <AlertBadge level={alertLevel} />
        </div>
        {dateRange && <p className="date-range">{dateRange}</p>}
        <p
          className="daily-avg-info"
          style={{ fontSize: "11px", color: "#333", margin: "2px 0" }}
        >
          <strong>{actualDate || "Latest"} Daily Avg: {todayDailyAvg.toFixed(2)} m³/s</strong>
          {hybasId && <span style={{ marginLeft: "8px", fontWeight: "normal", color: "#666" }}>| Basin: {hybasId}</span>}
        </p>
      </div>

      {/* Chart */}
      <ResponsiveContainer width="100%" height={280}>
        <ComposedChart
          data={chartData}
          margin={{ top: 15, right: 10, left: -10, bottom: 35 }}
        >
          <defs>
            <linearGradient id="waterGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={waterColors.stroke} stopOpacity={0.5} />
              <stop offset="100%" stopColor={waterColors.stroke} stopOpacity={0.1} />
            </linearGradient>
            <pattern
              id="forecastPattern"
              patternUnits="userSpaceOnUse"
              width="8"
              height="8"
              patternTransform="rotate(45)"
            >
              <rect width="4" height="8" fill={waterColors.fill} />
              <rect x="4" width="4" height="8" fill="rgba(255, 255, 255, 0.1)" />
            </pattern>
          </defs>

          <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />

          <XAxis
            dataKey="displayDate"
            angle={-45}
            textAnchor="end"
            height={50}
            tick={{ fontSize: 9 }}
            stroke="#666"
            scale="point"
            tickMargin={5}
            interval={2}
          />

          <YAxis
            label={{
              value: "Discharge (m³/s)",
              angle: -90,
              position: "insideLeft",
              offset: -5,
              style: { textAnchor: "middle", fontSize: "10px", fill: "#333" },
            }}
            tick={{ fontSize: 9 }}
            stroke="#666"
            width={50}
            domain={[0, (dataMax) => Math.max(dataMax * 1.1, thresholds.emergency * 1.2)]}
            tickFormatter={(val) =>
              val >= 1000 ? `${(val / 1000).toFixed(1)}k` : val.toFixed(0)
            }
          />

          <Tooltip content={<ChartTooltip thresholds={thresholds} />} />

          {/* Threshold reference lines - uses shared colors */}
          <ReferenceLine
            y={thresholds.warning}
            stroke={ALERT_COLORS.warning}
            strokeWidth={2}
          />
          <ReferenceLine
            y={thresholds.alarm}
            stroke={ALERT_COLORS.alarm}
            strokeWidth={2}
          />
          <ReferenceLine
            y={thresholds.emergency}
            stroke={ALERT_COLORS.emergency}
            strokeWidth={2}
          />

          {/* Today reference line */}
          {todayDisplayDate && (
            <ReferenceLine
              x={todayDisplayDate}
              stroke="#666"
              strokeDasharray="3 3"
              strokeWidth={1}
              label={{ value: "Today", position: "top", fontSize: 9, fill: "#666" }}
            />
          )}

          {/* Historical daily_avg area */}
          {availableModels.includes("daily_avg") && (
            <Area
              type="natural"
              dataKey="daily_avg"
              stroke={waterColors.stroke}
              strokeWidth={2}
              fill="url(#waterGradient)"
              fillOpacity={1}
              dot={false}
              connectNulls
              activeDot={{ r: 5 }}
              baseValue={0}
            />
          )}

          {/* Historical model lines */}
          <ModelLines models={availableModels} isForecast={false} />

          {/* Forecast daily_avg area */}
          {availableModels.includes("daily_avg") && (
            <Area
              type="natural"
              dataKey="daily_avg_forecast"
              stroke={waterColors.stroke}
              strokeWidth={2}
              strokeDasharray="5 5"
              fill="url(#forecastPattern)"
              fillOpacity={1}
              dot={false}
              connectNulls
              activeDot={{ r: 5 }}
              baseValue={0}
            />
          )}

          {/* Forecast model lines */}
          <ModelLines models={availableModels} isForecast={true} />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
};

MultiModelChart.propTypes = {
  forecastsJson: PropTypes.oneOfType([PropTypes.string, PropTypes.array]),
  adminName: PropTypes.string,
  pointId: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  hybasId: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  selectedDate: PropTypes.string,
  thresholds: PropTypes.shape({
    warning: PropTypes.number,
    alarm: PropTypes.number,
    emergency: PropTypes.number,
  }),
};

export default MultiModelChart;
