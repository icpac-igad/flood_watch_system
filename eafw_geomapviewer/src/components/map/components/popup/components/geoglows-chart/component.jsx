import React, { useState, useEffect } from "react";
import PropTypes from "prop-types";
import {
  ComposedChart,
  Area,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
} from "recharts";

import "./styles.scss";

const RP_COLORS = {
  rp_2yr: { color: "#F5D140", label: "2-year" },
  rp_10yr: { color: "#FF813D", label: "10-year" },
  rp_25yr: { color: "#FA4343", label: "25-year" },
  rp_50yr: { color: "#BA25F5", label: "50-year" },
};

const formatDate = (dateStr) => {
  const d = new Date(dateStr);
  return `${d.getMonth() + 1}/${d.getDate()}`;
};

const GeoglowsChart = ({ riverId, country, streamOrder }) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!riverId) return;

    setLoading(true);
    setError(null);

    fetch(`/api/flood/geoglows-forecast/${riverId}`)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((d) => {
        if (d.error) {
          setError(d.error);
          return;
        }

        const chartData = d.datetime.map((dt, i) => ({
          date: dt,
          displayDate: formatDate(dt),
          median: d.flow_median[i],
          lower: d.flow_uncertainty_lower[i],
          upper: d.flow_uncertainty_upper[i],
        }));

        setData({
          chartData,
          returnPeriods: d.return_periods || {},
          metadata: d.metadata || {},
        });
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [riverId]);

  if (loading) {
    return (
      <div className="c-geoglows-chart">
        <div className="chart-loading">Loading forecast...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="c-geoglows-chart">
        <div className="chart-error">Error: {error}</div>
      </div>
    );
  }

  if (!data || !data.chartData.length) {
    return (
      <div className="c-geoglows-chart">
        <div className="chart-loading">No forecast data available</div>
      </div>
    );
  }

  const { chartData, returnPeriods } = data;
  const maxFlow = Math.max(
    ...chartData.map((d) => d.upper || d.median),
    ...Object.values(returnPeriods).filter((v) => v > 0)
  );

  return (
    <div className="c-geoglows-chart">
      <div className="chart-header">
        <h4>GEOGloWS River Forecast</h4>
        <div className="subtitle">
          River ID: {riverId}
          {country && ` · ${country}`}
          {streamOrder && ` · Order ${streamOrder}`}
        </div>
      </div>

      <ResponsiveContainer width="100%" height={220}>
        <ComposedChart data={chartData} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
          <XAxis
            dataKey="displayDate"
            tick={{ fontSize: 10 }}
            interval={Math.floor(chartData.length / 6)}
          />
          <YAxis
            tick={{ fontSize: 10 }}
            domain={[0, maxFlow * 1.1]}
            label={{ value: "m³/s", angle: -90, position: "insideLeft", fontSize: 10 }}
          />
          <Tooltip
            labelFormatter={(_, payload) => {
              if (payload?.[0]?.payload?.date) {
                return new Date(payload[0].payload.date).toLocaleString();
              }
              return "";
            }}
            formatter={(value) => [`${value.toFixed(1)} m³/s`]}
          />

          {/* Uncertainty band */}
          <Area
            type="monotone"
            dataKey="upper"
            stroke="none"
            fill="#4BAECC"
            fillOpacity={0.15}
          />
          <Area
            type="monotone"
            dataKey="lower"
            stroke="none"
            fill="#ffffff"
            fillOpacity={1}
          />

          {/* Median flow */}
          <Line
            type="monotone"
            dataKey="median"
            stroke="#4BAECC"
            strokeWidth={2}
            dot={false}
            name="Median Flow"
          />

          {/* Return period thresholds */}
          {Object.entries(RP_COLORS).map(([key, { color, label }]) => {
            const val = returnPeriods[key];
            if (val && val > 0) {
              return (
                <ReferenceLine
                  key={key}
                  y={val}
                  stroke={color}
                  strokeDasharray="5 3"
                  strokeWidth={1.5}
                  label={{
                    value: label,
                    position: "right",
                    fontSize: 9,
                    fill: color,
                  }}
                />
              );
            }
            return null;
          })}
        </ComposedChart>
      </ResponsiveContainer>

      <div className="chart-legend">
        <div className="legend-item">
          <span className="swatch" style={{ background: "#4BAECC" }} />
          Median
        </div>
        <div className="legend-item">
          <span className="swatch" style={{ background: "#4BAECC", opacity: 0.3 }} />
          Uncertainty
        </div>
        {Object.entries(RP_COLORS).map(([key, { color, label }]) =>
          returnPeriods[key] > 0 ? (
            <div key={key} className="legend-item">
              <span className="swatch dashed" style={{ borderColor: color }} />
              {label}
            </div>
          ) : null
        )}
      </div>
    </div>
  );
};

GeoglowsChart.propTypes = {
  riverId: PropTypes.number.isRequired,
  country: PropTypes.string,
  streamOrder: PropTypes.number,
};

export default GeoglowsChart;
