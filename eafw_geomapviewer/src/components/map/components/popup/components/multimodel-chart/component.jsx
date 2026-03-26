import React, { useEffect, useMemo, useState } from "react";
import PropTypes from "prop-types";
import {
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceArea,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { format, isAfter, parseISO, startOfDay } from "date-fns";

import { CMS_API } from "@/utils/constants";

import "./styles.scss";

const MODEL_COLORS = {
  GeoSFM: "#1f77b4",
  Floodproof: "#ff7f0e",
  Mike_Hydro_RFE: "#2ca02c",
  Mike_Hydro_CHIRP: "#d62728",
  Mike_Hydro_IMERG: "#9467bd",
};

const MODEL_LABELS = {
  GeoSFM: "GeoSFM",
  Floodproof: "FloodProofs",
  Mike_Hydro_RFE: "Mike Hydro (RFE)",
  Mike_Hydro_CHIRP: "Mike Hydro (CHIRP)",
  Mike_Hydro_IMERG: "Mike Hydro (IMERG)",
};

const FORECAST_MODELS = [
  "GeoSFM",
  "Floodproof",
  "Mike_Hydro_RFE",
  "Mike_Hydro_CHIRP",
  "Mike_Hydro_IMERG",
];

const DEFAULT_THRESHOLDS = {
  warning: 300,
  alarm: 500,
  emergency: 750,
};

const toFiniteNumber = (value) => {
  const parsed = parseFloat(value);
  return Number.isFinite(parsed) ? parsed : null;
};

const getDateRange = (forecasts) => {
  if (!forecasts?.length) return "";

  try {
    return `${format(parseISO(forecasts[0].date), "dd MMM yyyy")} - ${format(
      parseISO(forecasts[forecasts.length - 1].date),
      "dd MMM yyyy"
    )}`;
  } catch (error) {
    return "";
  }
};

const detectAvailableModels = (forecasts) => {
  if (!Array.isArray(forecasts) || !forecasts.length) return [];

  return FORECAST_MODELS.filter((model) =>
    forecasts.some((forecast) => toFiniteNumber(forecast?.[model]) !== null)
  );
};

const transformForChart = (forecasts) => {
  const today = startOfDay(new Date());
  const firstDate = forecasts?.[0]?.date || "";
  const lastDate = forecasts?.[forecasts.length - 1]?.date || "";

  let spanMonths = 0;
  try {
    const start = parseISO(firstDate);
    const end = parseISO(lastDate);
    spanMonths =
      (end.getFullYear() - start.getFullYear()) * 12 +
      (end.getMonth() - start.getMonth());
  } catch (error) {
    spanMonths = 0;
  }

  const dateFormat = spanMonths > 3 ? "MMM yyyy" : "dd MMM";

  return forecasts.map((forecast, index) => {
    let displayDate = forecast.date;
    let isForecast = false;

    try {
      const parsedDate = parseISO(forecast.date);
      displayDate = format(parsedDate, dateFormat);
      isForecast = isAfter(startOfDay(parsedDate), today);
    } catch (error) {
      displayDate = forecast.date;
    }

    const entry = {
      index,
      date: forecast.date,
      displayDate,
      isForecast,
      daily_avg: toFiniteNumber(forecast.daily_avg),
      daily_max: toFiniteNumber(forecast.daily_max),
      daily_min: toFiniteNumber(forecast.daily_min),
    };

    FORECAST_MODELS.forEach((model) => {
      const value = toFiniteNumber(forecast?.[model]);
      if (value !== null) {
        entry[model] = value;
      }
    });

    return entry;
  });
};

const findTodayIndex = (chartData) => {
  const today = startOfDay(new Date());

  for (const row of chartData) {
    try {
      const forecastDate = startOfDay(parseISO(row.date));
      if (
        forecastDate.getTime() === today.getTime() ||
        isAfter(forecastDate, today)
      ) {
        return row.index;
      }
    } catch (error) {
      // Ignore malformed dates in popup chart data.
    }
  }

  return null;
};

const ChartTooltip = ({ active, payload }) => {
  if (!active || !payload?.length) {
    return null;
  }

  const dataPoint = payload[0]?.payload || {};
  const modelEntries = FORECAST_MODELS.map((model) => {
    const value = toFiniteNumber(dataPoint?.[model]);
    if (value === null) return null;
    return {
      model,
      label: MODEL_LABELS[model],
      value,
      color: MODEL_COLORS[model],
    };
  }).filter(Boolean);

  return (
    <div className="custom-tooltip">
      <p className="tooltip-date">{dataPoint.displayDate || ""}</p>
      {toFiniteNumber(dataPoint.daily_avg) !== null && (
        <p className="tooltip-summary">
          Daily Avg: {dataPoint.daily_avg.toFixed(2)} m3/s
        </p>
      )}
      <div className="tooltip-models">
        {modelEntries.map((item) => (
          <p key={item.model} style={{ color: item.color }}>
            <span>{item.label}</span>: {item.value.toFixed(2)} m3/s
          </p>
        ))}
      </div>
    </div>
  );
};

ChartTooltip.propTypes = {
  active: PropTypes.bool,
  payload: PropTypes.array,
};

const ModelSelector = ({ availableModels, onToggle, selectedModels }) => (
  <div className="model-selector">
    {FORECAST_MODELS.map((model) => {
      const isAvailable = availableModels.includes(model);
      const isSelected = selectedModels.includes(model);

      return (
        <button
          key={model}
          type="button"
          className={`model-chip ${isAvailable ? "" : "disabled"} ${
            isSelected ? "selected" : ""
          }`}
          onClick={() => isAvailable && onToggle(model)}
          disabled={!isAvailable}
        >
          <span
            className="model-chip-dot"
            style={{ backgroundColor: isAvailable ? MODEL_COLORS[model] : "#999" }}
          />
          <span>{MODEL_LABELS[model]}</span>
        </button>
      );
    })}
  </div>
);

ModelSelector.propTypes = {
  availableModels: PropTypes.array.isRequired,
  onToggle: PropTypes.func.isRequired,
  selectedModels: PropTypes.array.isRequired,
};

const MultiModelChart = ({
  adminName,
  layerName,
  pointId,
  selectedDate,
  thresholds: popupThresholds,
}) => {
  const [responseData, setResponseData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selectedModels, setSelectedModels] = useState(FORECAST_MODELS);
  const [zoomRange, setZoomRange] = useState(null);
  const [refAreaLeft, setRefAreaLeft] = useState(null);
  const [refAreaRight, setRefAreaRight] = useState(null);

  useEffect(() => {
    if (!pointId) {
      setResponseData(null);
      return;
    }

    let cancelled = false;

    const fetchData = async () => {
      setLoading(true);
      setError(null);

      try {
        const params = new URLSearchParams();
        if (selectedDate) {
          params.set("date", selectedDate);
        }

        const suffix = params.toString() ? `?${params.toString()}` : "";
        const response = await fetch(
          `${CMS_API}/flood/forecast-timeseries/${pointId}${suffix}`
        );

        if (!response.ok) {
          throw new Error(`Failed to load forecast timeseries (${response.status})`);
        }

        const payload = await response.json();
        if (!cancelled) {
          setResponseData(payload);
        }
      } catch (fetchError) {
        if (!cancelled) {
          setError(fetchError.message || "Failed to load forecast timeseries");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    fetchData();

    return () => {
      cancelled = true;
    };
  }, [pointId, selectedDate]);

  const forecasts = useMemo(() => responseData?.forecasts || [], [responseData]);

  const {
    actualDate,
    availableModels,
    chartData,
    dateRange,
    selectedDayValue,
    thresholdLines,
    todayIndex,
  } = useMemo(() => {
    const data = transformForChart(forecasts);
    const available = detectAvailableModels(forecasts);
    const mergedThresholds = {
      warning:
        toFiniteNumber(responseData?.thresholds?.warning) ??
        toFiniteNumber(popupThresholds?.warning) ??
        DEFAULT_THRESHOLDS.warning,
      alarm:
        toFiniteNumber(responseData?.thresholds?.alarm) ??
        toFiniteNumber(popupThresholds?.alarm) ??
        DEFAULT_THRESHOLDS.alarm,
      emergency:
        toFiniteNumber(responseData?.thresholds?.emergency) ??
        toFiniteNumber(popupThresholds?.emergency) ??
        DEFAULT_THRESHOLDS.emergency,
    };

    return {
      actualDate: responseData?.data_date || selectedDate || null,
      availableModels: available,
      chartData: data,
      dateRange: getDateRange(forecasts),
      selectedDayValue: data?.[0]?.daily_avg ?? 0,
      thresholdLines: mergedThresholds,
      todayIndex: findTodayIndex(data),
    };
  }, [forecasts, popupThresholds, responseData, selectedDate]);

  useEffect(() => {
    setSelectedModels((prev) => {
      const retained = prev.filter((model) => availableModels.includes(model));
      return retained.length ? retained : availableModels;
    });
  }, [availableModels]);

  useEffect(() => {
    setZoomRange(null);
    setRefAreaLeft(null);
    setRefAreaRight(null);
  }, [chartData]);

  const displayData = useMemo(() => {
    if (!zoomRange) return chartData;
    return chartData.slice(zoomRange.start, zoomRange.end + 1);
  }, [chartData, zoomRange]);

  const indexToLabel = useMemo(() => {
    const labels = {};
    chartData.forEach((row) => {
      labels[row.index] = row.displayDate;
    });
    return labels;
  }, [chartData]);

  const showTodayLine = useMemo(() => {
    if (todayIndex === null) return false;
    if (!zoomRange) return true;
    return todayIndex >= zoomRange.start && todayIndex <= zoomRange.end;
  }, [todayIndex, zoomRange]);

  const toggleModel = (model) => {
    setSelectedModels((prev) =>
      prev.includes(model)
        ? prev.filter((entry) => entry !== model)
        : [...prev, model]
    );
  };

  const chartTitle = `${layerName || "Multi-Model Forecast"}${
    adminName ? ` - ${adminName}` : responseData?.admin_name ? ` - ${responseData.admin_name}` : ""
  }`;

  if (loading) {
    return (
      <div className="c-multimodel-chart-loading">
        <p>Loading forecast data...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="c-multimodel-chart-error">
        <p>{error}</p>
      </div>
    );
  }

  if (!chartData.length) {
    return (
      <div className="c-multimodel-chart-empty">
        <p>No forecast data available.</p>
      </div>
    );
  }

  return (
    <div className="c-multimodel-chart">
      <div className="chart-header">
        <div className="header-title-row">
          <h4>{chartTitle}</h4>
          {zoomRange && (
            <button
              type="button"
              className="reset-zoom-btn"
              onClick={() => setZoomRange(null)}
            >
              Reset zoom
            </button>
          )}
        </div>
        {dateRange && <p className="date-range">{dateRange}</p>}
        <p className="summary-line">
          <strong>
            {actualDate || "Latest"} Daily Avg: {selectedDayValue.toFixed(2)} m3/s
          </strong>
        </p>
      </div>

      {availableModels.length > 0 && (
        <ModelSelector
          availableModels={availableModels}
          selectedModels={selectedModels}
          onToggle={toggleModel}
        />
      )}

      <div className="chart-container">
        <ResponsiveContainer width="100%" height={300}>
          <ComposedChart
            data={displayData}
            margin={{ top: 15, right: 10, left: -10, bottom: 35 }}
            onMouseDown={(event) => {
              if (event?.activeLabel !== undefined) {
                setRefAreaLeft(event.activeLabel);
                setRefAreaRight(event.activeLabel);
              }
            }}
            onMouseMove={(event) => {
              if (refAreaLeft !== null && event?.activeLabel !== undefined) {
                setRefAreaRight(event.activeLabel);
              }
            }}
            onMouseUp={() => {
              if (refAreaLeft === null || refAreaRight === null) return;
              if (refAreaLeft === refAreaRight) {
                setRefAreaLeft(null);
                setRefAreaRight(null);
                return;
              }

              const [start, end] =
                refAreaLeft < refAreaRight
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
              interval="preserveStartEnd"
              tickCount={15}
              minTickGap={30}
              tickFormatter={(value) => indexToLabel[value] || ""}
            />

            <YAxis
              label={{
                value: "Discharge (m3/s)",
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
              tickFormatter={(value) =>
                value >= 1000 ? `${(value / 1000).toFixed(1)}k` : value.toFixed(0)
              }
            />

            <Tooltip content={<ChartTooltip />} />

            {refAreaLeft !== null && refAreaRight !== null && (
              <ReferenceArea
                x1={refAreaLeft}
                x2={refAreaRight}
                strokeOpacity={0.2}
                fill="rgba(25, 118, 210, 0.12)"
              />
            )}

            {showTodayLine && todayIndex !== null && (
              <ReferenceLine
                x={todayIndex}
                stroke="#333"
                strokeDasharray="3 3"
                strokeWidth={1}
                label={{
                  value: "Today",
                  position: "top",
                  fontSize: 9,
                  fill: "#333",
                }}
              />
            )}

            {thresholdLines.warning !== null && (
              <ReferenceLine
                y={thresholdLines.warning}
                ifOverflow="extendDomain"
                stroke="#ffc107"
                strokeDasharray="4 4"
                strokeWidth={1}
                label={{
                  value: "Moderate",
                  position: "right",
                  fontSize: 9,
                  fill: "#b38400",
                }}
              />
            )}
            {thresholdLines.alarm !== null && (
              <ReferenceLine
                y={thresholdLines.alarm}
                ifOverflow="extendDomain"
                stroke="#ff9800"
                strokeDasharray="4 4"
                strokeWidth={1}
                label={{
                  value: "Severe",
                  position: "right",
                  fontSize: 9,
                  fill: "#c66a00",
                }}
              />
            )}
            {thresholdLines.emergency !== null && (
              <ReferenceLine
                y={thresholdLines.emergency}
                ifOverflow="extendDomain"
                stroke="#d32f2f"
                strokeDasharray="4 4"
                strokeWidth={1}
                label={{
                  value: "Extreme",
                  position: "right",
                  fontSize: 9,
                  fill: "#9b1c1c",
                }}
              />
            )}

            {selectedModels.includes("GeoSFM") &&
              availableModels.includes("GeoSFM") && (
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
            {selectedModels.includes("Floodproof") &&
              availableModels.includes("Floodproof") && (
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
            {selectedModels.includes("Mike_Hydro_RFE") &&
              availableModels.includes("Mike_Hydro_RFE") && (
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
            {selectedModels.includes("Mike_Hydro_CHIRP") &&
              availableModels.includes("Mike_Hydro_CHIRP") && (
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
            {selectedModels.includes("Mike_Hydro_IMERG") &&
              availableModels.includes("Mike_Hydro_IMERG") && (
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
  adminName: PropTypes.string,
  layerName: PropTypes.string,
  pointId: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  selectedDate: PropTypes.string,
  thresholds: PropTypes.shape({
    warning: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
    alarm: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
    emergency: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  }),
};

export default MultiModelChart;
