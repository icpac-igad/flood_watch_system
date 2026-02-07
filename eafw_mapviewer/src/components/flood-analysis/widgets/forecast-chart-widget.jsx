/**
 * Forecast Chart Widget
 * Multi-model ensemble forecast visualization
 * Uses Recharts for interactive charts
 */
import React, { useState, useMemo } from "react";
import { isEmpty } from "lodash";

import Loader from "@/components/ui/loader";

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

// Alert thresholds for reference lines
const THRESHOLDS = {
  warning: 500,
  alarm: 750,
  emergency: 1500,
};

// Custom tooltip for the chart
const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload || !payload.length) return null;

  return (
    <div className="chart-tooltip">
      <p className="tooltip-date">{label}</p>
      <div className="tooltip-models">
        {payload.map((entry, index) => (
          <p key={index} className="tooltip-model">
            <span style={{ color: entry.color }}>{entry.name}:</span>
            <span className="tooltip-value">
              {entry.value?.toFixed(1)} m³/s
            </span>
          </p>
        ))}
      </div>
    </div>
  );
};

const ForecastChartWidget = ({ params, chartData, models, loading }) => {
  const [selectedModels, setSelectedModels] = useState(() =>
    models.map((m) => m.id)
  );

  // Handle model toggle
  const toggleModel = (modelId) => {
    setSelectedModels((prev) => {
      if (prev.includes(modelId)) {
        // Don't remove if it's the last one
        if (prev.length === 1) return prev;
        return prev.filter((id) => id !== modelId);
      }
      return [...prev, modelId];
    });
  };

  // Filter chart data for selected models
  const filteredData = useMemo(() => {
    if (isEmpty(chartData?.data)) return [];
    return chartData.data;
  }, [chartData]);

  if (loading) {
    return (
      <div className="c-flood-widget">
        <div className="widget-header">
          <div className="widget-title">Multi-Model Forecast Comparison</div>
        </div>
        <div className="widget-loader">
          <Loader />
        </div>
      </div>
    );
  }

  if (isEmpty(chartData)) {
    return (
      <div className="c-flood-widget">
        <div className="widget-header">
          <div className="widget-title">Multi-Model Forecast Comparison</div>
          <div className="widget-description">
            Interactive comparison of streamflow forecasts from multiple
            hydrological models. Select models to compare their predictions.
          </div>
        </div>
        <div className="info-alert">
          Forecast comparison chart will be displayed when data is available.
        </div>
      </div>
    );
  }

  return (
    <div className="c-flood-widget" style={{ borderLeft: "4px solid #0c5a27" }}>
      <div className="widget-header">
        <div className="widget-title">Multi-Model Forecast Comparison</div>
        <div className="widget-description">
          Streamflow forecasts from {models.length} hydrological models for{" "}
          {params.placename}. Toggle models to compare predictions.
        </div>
      </div>

      {/* Model Selection Toggle Buttons */}
      <div className="model-tabs">
        {models.map((model) => (
          <button
            key={model.id}
            className={`model-tab ${selectedModels.includes(model.id) ? "active" : ""}`}
            onClick={() => toggleModel(model.id)}
            style={
              selectedModels.includes(model.id)
                ? { backgroundColor: model.color, borderColor: model.color }
                : {}
            }
          >
            {model.name}
          </button>
        ))}
      </div>

      {/* Chart */}
      <div className="chart-container" style={{ height: "400px" }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            data={filteredData}
            margin={{ top: 20, right: 30, left: 20, bottom: 20 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
            <XAxis
              dataKey="date"
              tick={{ fontSize: 11 }}
              tickFormatter={(value) => {
                const date = new Date(value);
                return date.toLocaleDateString("en-GB", {
                  month: "short",
                  day: "numeric",
                });
              }}
            />
            <YAxis
              tick={{ fontSize: 11 }}
              label={{
                value: "Streamflow (m³/s)",
                angle: -90,
                position: "insideLeft",
                style: { fontSize: 11 },
              }}
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend wrapperStyle={{ fontSize: 11, paddingTop: 10 }} />

            {/* Threshold reference lines */}
            <ReferenceLine
              y={THRESHOLDS.warning}
              stroke="#ffc107"
              strokeDasharray="5 5"
              label={{ value: "Warning", fontSize: 10, fill: "#b8860b" }}
            />
            <ReferenceLine
              y={THRESHOLDS.alarm}
              stroke="#ff9800"
              strokeDasharray="5 5"
              label={{ value: "Alarm", fontSize: 10, fill: "#e65100" }}
            />
            <ReferenceLine
              y={THRESHOLDS.emergency}
              stroke="#d32f2f"
              strokeDasharray="5 5"
              label={{ value: "Emergency", fontSize: 10, fill: "#c62828" }}
            />

            {/* Model lines */}
            {models
              .filter((m) => selectedModels.includes(m.id))
              .map((model) => (
                <Line
                  key={model.id}
                  type="monotone"
                  dataKey={model.id}
                  name={model.name}
                  stroke={model.color}
                  strokeWidth={2}
                  dot={{ r: 3 }}
                  activeDot={{ r: 5 }}
                />
              ))}
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Legend note */}
      <div className="chart-note">
        <p>
          Dashed lines indicate alert thresholds. Values above Emergency
          threshold indicate severe flood risk.
        </p>
      </div>
    </div>
  );
};

export default ForecastChartWidget;
