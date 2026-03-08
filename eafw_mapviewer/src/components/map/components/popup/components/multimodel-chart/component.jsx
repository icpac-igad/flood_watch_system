import React, { useMemo, useState, useEffect, useCallback, useRef } from "react";
import PropTypes from "prop-types";
import {
  ComposedChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  ReferenceArea,
} from "recharts";
import { format, parseISO, isAfter, startOfDay } from "date-fns";
import { saveAs } from "file-saver";

// Import shared configuration - single source of truth
import { getTodayStr } from "@/utils/multimodal-config";

import "./styles.scss";

// =============================================================================
// MODEL CONFIGURATION
// =============================================================================

/** Colors for individual forecast models - distinct colors for each line */
const MODEL_COLORS = {
  GeoSFM: "#1f77b4",        // Blue
  Floodproof: "#ff7f0e",    // Orange
  Mike_Hydro_RFE: "#2ca02c", // Green
  Mike_Hydro_CHIRP: "#d62728", // Red
  Mike_Hydro_IMERG: "#9467bd", // Purple
};

/** Human-readable labels for models */
const MODEL_LABELS = {
  GeoSFM: "GeoSFM",
  Floodproof: "FloodProofs",
  Mike_Hydro_RFE: "Mike Hydro (RFE)",
  Mike_Hydro_CHIRP: "Mike Hydro (CHIRP)",
  Mike_Hydro_IMERG: "Mike Hydro (IMERG)",
};

const isGoogleFloodEndpoint = (endpoint = "") =>
  String(endpoint).toLowerCase().includes("/api/v1/google-flood/geojson");

// Define all selectable models
const FORECAST_MODELS = ["GeoSFM", "Floodproof", "Mike_Hydro_RFE", "Mike_Hydro_CHIRP", "Mike_Hydro_IMERG"];

// =============================================================================
// UTILITY FUNCTIONS
// =============================================================================

/**
 * Finds forecast data for a specific date from the forecasts array
 * Falls back to the last available date if target date not found
 */
const findForecastForDate = (forecasts, targetDate = null) => {
  if (!Array.isArray(forecasts) || forecasts.length === 0) {
    return { forecast: null, usedDate: null };
  }

  const dateStr = targetDate || getTodayStr();

  let forecast = forecasts.find((f) => {
    if (!f.date) return false;
    const forecastDateStr = f.date.split("T")[0];
    return forecastDateStr === dateStr;
  });

  if (forecast) {
    return { forecast, usedDate: dateStr };
  }

  const lastForecast = forecasts[forecasts.length - 1];
  const lastDate = lastForecast?.date?.split("T")[0] || null;

  return { forecast: lastForecast, usedDate: lastDate };
};

/**
 * Extracts primary discharge value from a forecast object.
 * Uses daily_avg first, then falls back to daily_max/daily_min when needed.
 */
const extractPrimaryDischarge = (forecast) => {
  if (!forecast) {
    return null;
  }
  const candidates = [forecast.daily_avg, forecast.daily_max, forecast.daily_min];
  for (const value of candidates) {
    const val = parseFloat(value);
    if (!isNaN(val) && val >= 0 && val < 1e10) {
      return val;
    }
  }
  return null;
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
 * Only includes models that actually exist in the forecast data
 */
const detectAvailableModels = (forecasts) => {
  const models = new Set();

  if (!forecasts || forecasts.length === 0) {
    return [];
  }

  // Check each model defined in MODEL_COLORS across ALL forecast entries
  Object.keys(MODEL_COLORS).forEach((modelKey) => {
    const hasModel = forecasts.some((f) => {
      if (!f.hasOwnProperty(modelKey)) return false;
      const val = f[modelKey];
      if (val === undefined || val === null) return false;
      const numVal = parseFloat(val);
      return !isNaN(numVal) && numVal >= 0;
    });

    if (hasModel) {
      models.add(modelKey);
    }
  });

  console.log("[detectAvailableModels] Detected models:", Array.from(models));

  return Array.from(models);
};

/**
 * Transforms forecast data into chart-ready format
 */
const transformForChart = (forecasts) => {
  const today = startOfDay(new Date());
  const firstDate = forecasts[0]?.date || "";
  const lastDate = forecasts[forecasts.length - 1]?.date || "";

  // Determine date format based on data span
  let spanMonths = 0;
  try {
    const start = parseISO(firstDate);
    const end = parseISO(lastDate);
    spanMonths = (end.getFullYear() - start.getFullYear()) * 12 + (end.getMonth() - start.getMonth());
  } catch (e) { /* ignore */ }

  const dateFormat = spanMonths > 3 ? "MMM yyyy" : "dd MMM";

  const data = forecasts.map((f, idx) => {
    let displayDate;
    let isForecast = false;

    try {
      const parsedDate = parseISO(f.date);
      displayDate = format(parsedDate, dateFormat);
      isForecast = isAfter(startOfDay(parsedDate), today);
    } catch (e) {
      displayDate = f.date;
    }

    const entry = {
      date: f.date,
      displayDate,
      isForecast,
      index: idx,
    };

    // Include all model values (even 0) for complete chart display
    Object.keys(MODEL_COLORS).forEach((model) => {
      const rawVal = f[model];
      if (rawVal !== undefined && rawVal !== null) {
        const val = parseFloat(rawVal);
        if (!isNaN(val) && val >= 0 && val < 1e10) {
          entry[model] = val;
        }
      }
    });

    // Include primary discharge series for single-series model feeds (e.g., Google)
    const discharge = extractPrimaryDischarge(f);
    if (discharge !== null) {
      entry.daily_avg = discharge;
    }

    return entry;
  });

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
 * Finds today's index for the reference line
 */
const findTodayIndex = (chartData) => {
  const today = startOfDay(new Date());

  for (const d of chartData) {
    try {
      const forecastDate = startOfDay(parseISO(d.date));
      if (
        forecastDate.getTime() === today.getTime() ||
        isAfter(forecastDate, today)
      ) {
        return d.index;
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
 * Chart tooltip component - shows model values on hover
 */
const ChartTooltip = ({ active, payload, metricLabel = "Daily Avg" }) => {
  if (!active || !payload || !payload.length) {
    return null;
  }

  const dataPoint = payload[0]?.payload || {};

  const modelEntries = [];
  Object.keys(MODEL_COLORS).forEach((model) => {
    const value = dataPoint[model];
    if (value !== undefined && value !== null && !isNaN(value)) {
      modelEntries.push({
        model,
        value: parseFloat(value),
        color: MODEL_COLORS[model],
        label: MODEL_LABELS[model] || model,
      });
    }
  });

  // Sort by value descending
  modelEntries.sort((a, b) => b.value - a.value);

  return (
    <div className="custom-tooltip">
      <p className="tooltip-date">{dataPoint.displayDate || ""}</p>
      {dataPoint.daily_avg !== undefined && (
        <p style={{ color: "#333", fontWeight: "bold", margin: "4px 0" }}>
          {metricLabel}: {dataPoint.daily_avg.toFixed(2)} m³/s
        </p>
      )}
      <div className="tooltip-models">
        {modelEntries.map((item, index) => (
          <p key={index} style={{ color: item.color, margin: "2px 0" }}>
            <span>{item.label}</span>: {item.value.toFixed(4)} m³/s
          </p>
        ))}
      </div>
    </div>
  );
};

ChartTooltip.propTypes = {
  active: PropTypes.bool,
  payload: PropTypes.array,
  metricLabel: PropTypes.string,
};

/**
 * Model Legend/Selector with colored dots
 * Shows available models with clickable dot indicators to toggle visibility
 */
const ModelSelector = ({ availableModels, selectedModels, onToggle }) => {
  return (
    <div className="model-selector" style={{ display: "flex", flexWrap: "wrap", gap: "8px", marginBottom: "8px" }}>
      {FORECAST_MODELS.map((model) => {
        const isAvailable = availableModels.includes(model);
        const isSelected = selectedModels.includes(model);
        return (
          <div
            key={model}
            className={`model-legend-item ${!isAvailable ? "disabled" : ""}`}
            onClick={() => isAvailable && onToggle(model)}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "4px",
              cursor: isAvailable ? "pointer" : "default",
              opacity: isAvailable && isSelected ? 1 : 0.4,
              fontSize: "10px",
            }}
          >
            <span
              style={{
                width: "10px",
                height: "10px",
                borderRadius: "50%",
                backgroundColor: isAvailable ? MODEL_COLORS[model] : "#999",
                display: "inline-block",
                border: isSelected ? "2px solid #333" : "2px solid transparent",
              }}
            />
            <span style={{ color: "#333" }}>
              {MODEL_LABELS[model]}
            </span>
          </div>
        );
      })}
    </div>
  );
};

ModelSelector.propTypes = {
  availableModels: PropTypes.array.isRequired,
  selectedModels: PropTypes.array.isRequired,
  onToggle: PropTypes.func.isRequired,
};

/**
 * Export dropdown component
 */
const ExportDropdown = ({ onExport, isOpen, onToggle }) => {
  const exportOptions = [
    { label: "PNG Image", value: "png", icon: "🖼️" },
    { label: "CSV Data", value: "csv", icon: "📊" },
  ];

  return (
    <div className="export-dropdown-container" style={{ position: "relative" }}>
      <button
        className="export-btn"
        onClick={onToggle}
        title="Export data"
        style={{
          padding: "4px 8px",
          fontSize: "10px",
          cursor: "pointer",
          border: "1px solid #ccc",
          borderRadius: "4px",
          background: "#f5f5f5",
        }}
      >
        ⬇ Export
      </button>
      {isOpen && (
        <div className="export-dropdown" style={{
          position: "absolute",
          top: "100%",
          right: 0,
          background: "#fff",
          border: "1px solid #ccc",
          borderRadius: "4px",
          boxShadow: "0 2px 8px rgba(0,0,0,0.15)",
          zIndex: 100,
        }}>
          {exportOptions.map((opt) => (
            <button
              key={opt.value}
              className="export-option"
              onClick={() => {
                onExport(opt.value);
                onToggle();
              }}
              style={{
                display: "block",
                width: "100%",
                padding: "8px 12px",
                border: "none",
                background: "none",
                cursor: "pointer",
                textAlign: "left",
                fontSize: "11px",
              }}
            >
              <span className="export-icon">{opt.icon}</span> {opt.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
};

ExportDropdown.propTypes = {
  onExport: PropTypes.func.isRequired,
  isOpen: PropTypes.bool.isRequired,
  onToggle: PropTypes.func.isRequired,
};

/**
 * Export chart as PNG image using html2canvas
 */
const exportAsImage = async (chartRef, filename) => {
  if (!chartRef.current) {
    console.error("Chart ref not available");
    return;
  }

  try {
    const html2canvas = (await import("html2canvas")).default;
    const exportBtn = chartRef.current.querySelector(".export-dropdown-container");
    if (exportBtn) {
      exportBtn.style.display = "none";
    }

    const canvas = await html2canvas(chartRef.current, {
      backgroundColor: "#ffffff",
      scale: 2,
      logging: false,
    });

    if (exportBtn) {
      exportBtn.style.display = "";
    }

    canvas.toBlob((blob) => {
      if (blob) {
        saveAs(blob, `${filename}.png`);
      }
    }, "image/png");
  } catch (error) {
    console.error("Error exporting image:", error);
  }
};

/**
 * Export chart data as CSV
 */
const exportAsCSV = (chartData, adminName, availableModels, metricLabel = "Daily Avg") => {
  if (!chartData || !chartData.length) {
    console.error("No chart data to export");
    return;
  }

  const valueHeader = metricLabel.replace(/\s+/g, "_");
  const headers = ["Date", valueHeader, ...availableModels.map(m => MODEL_LABELS[m] || m)];

  const rows = chartData.map((row) => {
    const values = [row.date, row.daily_avg !== undefined ? row.daily_avg.toFixed(4) : ""];
    availableModels.forEach((model) => {
      const val = row[model];
      values.push(val !== undefined && val !== null ? val.toFixed(4) : "");
    });
    return values.join(",");
  });

  const csvContent = [headers.join(","), ...rows].join("\n");
  const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8" });
  const filename = `forecast_${adminName || "data"}_${getTodayStr()}.csv`;
  saveAs(blob, filename);
};

// =============================================================================
// MAIN COMPONENT
// =============================================================================

/**
 * MultiModelChart Component
 * Displays multi-model ensemble forecast data as a line chart
 * Shows individual model lines with toggleable visibility
 */
const MultiModelChart = ({
  forecastsJson,
  layerName,
  adminName,
  pointId,
  dataEndpoint,
  hybasId,
  selectedDate,
  thresholds,
  onDragStart,
}) => {
  const chartRef = useRef(null);

  const [fetchedData, setFetchedData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // State for selected models (all selected by default)
  const [selectedModels, setSelectedModels] = useState(FORECAST_MODELS);

  // State for export dropdown
  const [exportDropdownOpen, setExportDropdownOpen] = useState(false);

  // Zoom selection state
  const [zoomRange, setZoomRange] = useState(null);
  const [refAreaLeft, setRefAreaLeft] = useState(null);
  const [refAreaRight, setRefAreaRight] = useState(null);

  const thresholdLines = useMemo(() => {
    const toValue = (value) => {
      const parsed = parseFloat(value);
      return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
    };

    return {
      warning: toValue(thresholds?.warning ?? thresholds?.threshold_alert),
      alarm: toValue(thresholds?.alarm ?? thresholds?.threshold_alarm),
      emergency: toValue(thresholds?.emergency ?? thresholds?.threshold_emergency),
    };
  }, [thresholds]);

  const isGoogleLayer = useMemo(
    () => isGoogleFloodEndpoint(dataEndpoint),
    [dataEndpoint]
  );
  const summaryMetricLabel = isGoogleLayer ? "Discharge" : "Daily Avg";
  const chartTitle = useMemo(() => {
    const defaultTitle = isGoogleLayer ? "Google Flood Forecast" : "Multi-Model Forecast";
    const baseTitle = layerName || defaultTitle;
    return `${baseTitle}${adminName ? ` - ${adminName}` : ""}`;
  }, [isGoogleLayer, layerName, adminName]);

  const handleDragStart = useCallback((e) => {
    if (typeof onDragStart === "function") {
      onDragStart(e);
    }
  }, [onDragStart]);

  // Toggle model selection
  const toggleModel = useCallback((model) => {
    setSelectedModels((prev) => {
      if (prev.includes(model)) {
        return prev.filter((m) => m !== model);
      } else {
        return [...prev, model];
      }
    });
  }, []);

  // Toggle export dropdown
  const toggleExportDropdown = useCallback(() => {
    setExportDropdownOpen((prev) => !prev);
  }, []);

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
        let url = dataEndpoint || `${API_BASE_URL}/api/v1/multimodal/geojson/`;
        if (!/^https?:\/\//i.test(url) && !url.startsWith("/")) {
          url = `/${url}`;
        }
        if (selectedDate) {
          const separator = url.includes("?") ? "&" : "?";
          url += `${separator}date=${encodeURIComponent(selectedDate)}`;
        }

        console.log(
          `[MultiModelChart] Fetching ${url} for date: ${selectedDate || "latest"}, pointId: ${pointId}, adminName: ${adminName}`
        );
        const response = await fetch(url);
        if (!response.ok) {
          throw new Error("Failed to fetch forecast data");
        }

        const geojson = await response.json();

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
        setError(err.message || "Failed to fetch forecast data");
      } finally {
        setLoading(false);
      }
    };

    fetchForecastData();
  }, [pointId, adminName, selectedDate, dataEndpoint]);

  // Process data using memoization
  const {
    chartData,
    availableModels,
    dateRange,
    todayIndex,
    todayDailyAvg,
    actualDate,
    maxDataValue,
    hasDailyAvgSeries,
  } = useMemo(() => {
    const forecastData = fetchedData || forecastsJson;
    const forecasts = parseForecastData(forecastData);

    if (!forecasts.length) {
      return {
        chartData: [],
        availableModels: [],
        dateRange: "",
        todayIndex: null,
        todayDailyAvg: 0,
        actualDate: null,
        maxDataValue: 0,
        hasDailyAvgSeries: false,
      };
    }

    const models = detectAvailableModels(forecasts);
    const data = transformForChart(forecasts);
    const hasDailyAvg = data.some((entry) => {
      const value = entry.daily_avg;
      return value !== undefined && value !== null && Number.isFinite(value);
    });

    // Calculate max data value for Y-axis scaling
    let maxVal = 0;
    data.forEach(d => {
      Object.keys(MODEL_COLORS).forEach(model => {
        const val = d[model] || 0;
        if (val > maxVal) maxVal = val;
      });
      if (d.daily_avg && d.daily_avg > maxVal) maxVal = d.daily_avg;
    });

    const { forecast: targetForecast, usedDate } = findForecastForDate(forecasts, selectedDate);
    const dailyAvg = targetForecast
      ? extractPrimaryDischarge(targetForecast) ?? 0
      : extractPrimaryDischarge(forecasts[0]) ?? 0;

    console.log(`[MultiModelChart] Data points: ${data.length}, Available models: ${models.join(", ")}, maxVal: ${maxVal.toFixed(2)}`);

    return {
      chartData: data,
      availableModels: models,
      dateRange: getDateRange(forecasts),
      todayIndex: findTodayIndex(data),
      todayDailyAvg: dailyAvg,
      actualDate: usedDate,
      maxDataValue: maxVal,
      hasDailyAvgSeries: hasDailyAvg,
    };
  }, [forecastsJson, fetchedData, selectedDate]);

  const indexToLabel = useMemo(() => {
    const map = {};
    chartData.forEach((d) => {
      map[d.index] = d.displayDate;
    });
    return map;
  }, [chartData]);

  const displayData = useMemo(() => {
    if (!zoomRange) return chartData;
    return chartData.slice(zoomRange.start, zoomRange.end + 1);
  }, [chartData, zoomRange]);

  const showTodayLine = useMemo(() => {
    if (todayIndex === null) return false;
    if (!zoomRange) return true;
    return todayIndex >= zoomRange.start && todayIndex <= zoomRange.end;
  }, [todayIndex, zoomRange]);

  useEffect(() => {
    setZoomRange(null);
    setRefAreaLeft(null);
    setRefAreaRight(null);
  }, [chartData]);

  // Handle export
  const handleExport = useCallback(
    (format) => {
          const displayName = adminName || "forecast";
      const safeFilename = displayName.replace(/[^a-zA-Z0-9_-]/g, "_");

      switch (format) {
        case "png":
          exportAsImage(chartRef, `forecast_${safeFilename}_${getTodayStr()}`);
          break;
        case "csv":
          exportAsCSV(chartData, displayName, availableModels, summaryMetricLabel);
          break;
        default:
          console.warn("Unknown export format:", format);
      }
    },
    [chartData, availableModels, adminName, summaryMetricLabel]
  );

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
    <div className="c-multimodel-chart" ref={chartRef}>
      {/* Drag handle */}
      <div
        className="drag-handle"
        onMouseDown={handleDragStart}
        onTouchStart={handleDragStart}
      >
        <div className="drag-indicator" />
      </div>

        {/* Header */}
        <div className="chart-header">
          <div className="header-title-row" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <h4 style={{ margin: 0 }}>{chartTitle}</h4>
            <div className="header-controls">
              {zoomRange && (
                <button
                  className="reset-zoom-btn"
                  onClick={() => setZoomRange(null)}
                  title="Reset zoom"
                >
                  Reset zoom
                </button>
              )}
              <ExportDropdown
                onExport={handleExport}
                isOpen={exportDropdownOpen}
                onToggle={toggleExportDropdown}
              />
            </div>
          </div>
          {dateRange && <p className="date-range" style={{ margin: "4px 0", fontSize: "11px", color: "#666" }}>{dateRange}</p>}
          <p style={{ fontSize: "11px", color: "#333", margin: "2px 0" }}>
            <strong>{actualDate || "Latest"} {summaryMetricLabel}: {todayDailyAvg.toFixed(2)} m³/s</strong>
            {hybasId && <span style={{ marginLeft: "8px", fontWeight: "normal", color: "#666" }}>| Basin: {hybasId}</span>}
          </p>
        </div>

        {/* Model Selection */}
        {availableModels.length > 0 && (
          <ModelSelector
            availableModels={availableModels}
            selectedModels={selectedModels}
            onToggle={toggleModel}
          />
        )}

        {/* Chart */}
        <div className="chart-container">
          <ResponsiveContainer width="100%" height={300}>
        <ComposedChart
          data={displayData}
          margin={{ top: 15, right: 10, left: -10, bottom: 35 }}
          onMouseDown={(e) => {
            if (e && e.activeLabel !== undefined) {
              setRefAreaLeft(e.activeLabel);
              setRefAreaRight(e.activeLabel);
            }
          }}
          onMouseMove={(e) => {
            if (refAreaLeft !== null && e && e.activeLabel !== undefined) {
              setRefAreaRight(e.activeLabel);
            }
          }}
          onMouseUp={() => {
            if (refAreaLeft === null || refAreaRight === null) return;
            if (refAreaLeft === refAreaRight) {
              setRefAreaLeft(null);
              setRefAreaRight(null);
              return;
            }
            const [start, end] = refAreaLeft < refAreaRight
              ? [refAreaLeft, refAreaRight]
              : [refAreaRight, refAreaLeft];
            setZoomRange({ start, end });
            setRefAreaLeft(null);
            setRefAreaRight(null);
          }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />

          <XAxis
            dataKey="index"
            angle={-45}
            textAnchor="end"
            height={60}
            tick={{ fontSize: 9 }}
            stroke="#666"
            tickMargin={5}
            interval={"preserveStartEnd"}
            tickCount={15}
            minTickGap={30}
            tickFormatter={(value) => indexToLabel[value] || ""}
          />

          <YAxis
            label={{
              value: "Discharge (m³/s)",
              angle: -90,
              position: "insideLeft",
              offset: 15,
              style: { textAnchor: "middle", fontSize: "10px", fill: "#333" },
            }}
            tick={{ fontSize: 9 }}
            stroke="#666"
            width={60}
            domain={[0, (dataMax) => Math.max(dataMax * 1.1, 0.1)]}
            allowDataOverflow={false}
            tickFormatter={(val) =>
              val >= 1000 ? `${(val / 1000).toFixed(1)}k` : val.toFixed(2)
            }
          />

          <Tooltip content={<ChartTooltip metricLabel={summaryMetricLabel} />} />

          {refAreaLeft !== null && refAreaRight !== null && (
            <ReferenceArea
              x1={refAreaLeft}
              x2={refAreaRight}
              strokeOpacity={0.2}
              fill="rgba(25, 118, 210, 0.12)"
            />
          )}

          {/* Today reference line */}
          {showTodayLine && todayIndex !== null && (
            <ReferenceLine
              x={todayIndex}
              stroke="#333"
              strokeDasharray="3 3"
              strokeWidth={1}
              label={{ value: "Today", position: "top", fontSize: 9, fill: "#333" }}
            />
          )}

          {/* Alert thresholds */}
          {thresholdLines.warning !== null && (
            <ReferenceLine
              y={thresholdLines.warning}
              ifOverflow="extendDomain"
              stroke="#ffc107"
              strokeDasharray="4 4"
              strokeWidth={1}
              label={{ value: "Moderate", position: "right", fontSize: 9, fill: "#b38400" }}
            />
          )}
          {thresholdLines.alarm !== null && (
            <ReferenceLine
              y={thresholdLines.alarm}
              ifOverflow="extendDomain"
              stroke="#ff9800"
              strokeDasharray="4 4"
              strokeWidth={1}
              label={{ value: "Severe", position: "right", fontSize: 9, fill: "#c66a00" }}
            />
          )}
          {thresholdLines.emergency !== null && (
            <ReferenceLine
              y={thresholdLines.emergency}
              ifOverflow="extendDomain"
              stroke="#d32f2f"
              strokeDasharray="4 4"
              strokeWidth={1}
              label={{ value: "Extreme", position: "right", fontSize: 9, fill: "#9b1c1c" }}
            />
          )}

          {/* Fallback single-series line for model feeds that expose daily_avg only (e.g., Google) */}
          {availableModels.length === 0 && hasDailyAvgSeries && (
            <Line
              type="monotone"
              dataKey="daily_avg"
              name={summaryMetricLabel}
              stroke="#1f77b4"
              strokeWidth={2.5}
              dot={false}
              connectNulls
              isAnimationActive={false}
            />
          )}

          {/* Individual model lines - only show selected models */}
          {selectedModels.includes("GeoSFM") && availableModels.includes("GeoSFM") && (
            <Line
              type="monotone"
              dataKey="GeoSFM"
              name="GeoSFM"
              stroke={MODEL_COLORS.GeoSFM}
              strokeWidth={2.5}
              dot={false}
              connectNulls
              isAnimationActive={false}
            />
          )}
          {selectedModels.includes("Floodproof") && availableModels.includes("Floodproof") && (
            <Line
              type="monotone"
              dataKey="Floodproof"
              name="FloodProofs"
              stroke={MODEL_COLORS.Floodproof}
              strokeWidth={2.5}
              dot={false}
              connectNulls
              isAnimationActive={false}
            />
          )}
          {selectedModels.includes("Mike_Hydro_RFE") && availableModels.includes("Mike_Hydro_RFE") && (
            <Line
              type="monotone"
              dataKey="Mike_Hydro_RFE"
              name="Mike Hydro (RFE)"
              stroke={MODEL_COLORS.Mike_Hydro_RFE}
              strokeWidth={2.5}
              dot={false}
              connectNulls
              isAnimationActive={false}
            />
          )}
          {selectedModels.includes("Mike_Hydro_CHIRP") && availableModels.includes("Mike_Hydro_CHIRP") && (
            <Line
              type="monotone"
              dataKey="Mike_Hydro_CHIRP"
              name="Mike Hydro (CHIRP)"
              stroke={MODEL_COLORS.Mike_Hydro_CHIRP}
              strokeWidth={2.5}
              dot={false}
              connectNulls
              isAnimationActive={false}
            />
          )}
          {selectedModels.includes("Mike_Hydro_IMERG") && availableModels.includes("Mike_Hydro_IMERG") && (
            <Line
              type="monotone"
              dataKey="Mike_Hydro_IMERG"
              name="Mike Hydro (IMERG)"
              stroke={MODEL_COLORS.Mike_Hydro_IMERG}
              strokeWidth={2.5}
              dot={false}
              connectNulls
              isAnimationActive={false}
            />
          )}
        </ComposedChart>
          </ResponsiveContainer>
        </div>

    </div>
  );
};

MultiModelChart.propTypes = {
  forecastsJson: PropTypes.oneOfType([PropTypes.string, PropTypes.array]),
  layerName: PropTypes.string,
  adminName: PropTypes.string,
  pointId: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  dataEndpoint: PropTypes.string,
  hybasId: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  selectedDate: PropTypes.string,
  thresholds: PropTypes.object,
  onDragStart: PropTypes.func,
};

export default MultiModelChart;
