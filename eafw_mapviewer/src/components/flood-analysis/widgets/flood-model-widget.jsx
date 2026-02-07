/**
 * Individual Flood Model Widget
 * Based on mukau-viz-components widgets/cdi.js
 * Displays forecast data for a specific hydrological model
 */
import React from "react";
import { isEmpty } from "lodash";

import Loader from "@/components/ui/loader";

const FloodModelWidget = ({ model, params, data, loading }) => {
  const { id, name, fullName, description, color } = model;

  // Loading state
  if (loading) {
    return (
      <div className="c-flood-widget" style={{ borderLeft: `4px solid ${color}` }}>
        <div className="widget-header">
          <div className="widget-title" style={{ color }}>
            {fullName}
          </div>
        </div>
        <div className="widget-loader">
          <Loader />
        </div>
      </div>
    );
  }

  // No data state
  if (isEmpty(data)) {
    return (
      <div className="c-flood-widget" style={{ borderLeft: `4px solid ${color}` }}>
        <div className="widget-header">
          <div className="widget-title" style={{ color }}>
            {fullName}
          </div>
          <div className="widget-description">{description}</div>
        </div>
        <div className="info-alert">
          No forecast data available for {name} model.
        </div>
      </div>
    );
  }

  return (
    <div className="c-flood-widget" style={{ borderLeft: `4px solid ${color}` }}>
      {/* Header */}
      <div className="widget-header">
        <div className="widget-title" style={{ color }}>
          {fullName}
        </div>
        <div className="widget-description">
          {description}{" "}
          <a
            href={`/documents/${id}-methodology.pdf`}
            target="_blank"
            rel="noreferrer"
          >
            More details
          </a>
        </div>
      </div>

      {/* Content Grid */}
      <div className="widget-content">
        {/* Map Image */}
        {data?.map_url && (
          <div className="map-container">
            <div className="map-header">
              <span className="map-title">
                {data.map_title || `${name} Forecast Map`}
              </span>
              <a
                href={data.map_url}
                download
                className="download-btn"
                title="Download map image"
              >
                ↓ Download
              </a>
            </div>
            <img
              src={data.map_url}
              alt={data.map_title || `${name} forecast map`}
            />
            {data.map_subtitle && (
              <p className="map-subtitle">{data.map_subtitle}</p>
            )}
          </div>
        )}

        {/* Statistics Summary */}
        {data?.statistics && (
          <div className="c-stats-table">
            <h4 style={{ marginBottom: "1rem", color: "#333", fontSize: "1rem" }}>
              Forecast Statistics
            </h4>
            <table>
              <thead>
                <tr>
                  <th>Alert Level</th>
                  <th>Points</th>
                  <th>Population</th>
                  <th>Area (km²)</th>
                </tr>
              </thead>
              <tbody>
                {data.statistics.map((stat, idx) => (
                  <tr key={idx}>
                    <td>
                      <span className={`alert-badge ${stat.level}`}>
                        {stat.level}
                      </span>
                    </td>
                    <td>{stat.points?.toLocaleString() || "-"}</td>
                    <td>{stat.population?.toLocaleString() || "-"}</td>
                    <td>{stat.area?.toLocaleString() || "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Time Series Chart Placeholder */}
        {data?.timeseries && (
          <div className="chart-container" style={{ gridColumn: "1 / -1" }}>
            <h4 style={{ marginBottom: "1rem", color: "#333", fontSize: "1rem" }}>
              {name} Forecast Time Series
            </h4>
            <div className="info-alert">
              Time series chart for {name} model forecast data.
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default FloodModelWidget;
