/**
 * Alert Summary Widget
 * Displays flood risk exposure statistics - matching drought report design
 */
import React from "react";
import { isEmpty } from "lodash";

import Loader from "@/components/ui/loader";

// Alert level colors matching flood watch color scheme
const ALERT_LEVELS = [
  { key: "emergency", label: "Emergency", color: "#F44336" },
  { key: "alarm", label: "Alarm", color: "#FF9800" },
  { key: "warning", label: "Warning", color: "#FFC107" },
  { key: "normal", label: "Normal", color: "#4CAF50" },
];

const AlertSummaryWidget = ({ params, alertData, loading }) => {
  if (loading) {
    return (
      <div className="c-alert-summary">
        <div className="section-header">
          <h3 className="section-title">Flood Risk Exposure Statistics</h3>
        </div>
        <div className="widget-loader">
          <Loader />
        </div>
      </div>
    );
  }

  // Default values for display
  const byLevel = alertData?.by_level || {};
  const totalPoints = alertData?.total_points || 0;

  // Calculate percentages
  const getPercentage = (count) => {
    if (!totalPoints) return "0.0";
    return ((count / totalPoints) * 100).toFixed(1);
  };

  // Total at-risk points (non-normal)
  const totalAtRisk =
    (byLevel.emergency || 0) + (byLevel.alarm || 0) + (byLevel.warning || 0);

  return (
    <div className="c-alert-summary">
      {/* Section Header */}
      <div className="section-header">
        <h3 className="section-title">Flood Risk Exposure Statistics</h3>
      </div>

      {/* Statistics Table */}
      <div className="c-stats-table">
        <table>
          <thead>
            <tr>
              <th>ALERT LEVEL</th>
              <th>FORECAST POINTS</th>
              <th>% OF TOTAL</th>
            </tr>
          </thead>
          <tbody>
            {ALERT_LEVELS.map((level) => {
              const count = byLevel[level.key] || 0;
              const percentage = getPercentage(count);

              return (
                <tr key={level.key}>
                  <td>
                    <div className="level-indicator">
                      <span
                        className={`level-dot ${level.key}`}
                        style={{ backgroundColor: level.color }}
                      ></span>
                      <span>{level.label}</span>
                    </div>
                  </td>
                  <td>{count.toLocaleString()}</td>
                  <td>{percentage}%</td>
                </tr>
              );
            })}
            <tr className="total-row">
              <td><strong>Total</strong></td>
              <td><strong>{totalPoints.toLocaleString()}</strong></td>
              <td><strong>100%</strong></td>
            </tr>
          </tbody>
        </table>
      </div>

      {/* Summary bar */}
      {totalPoints > 0 && (
        <div className="risk-summary-bar">
          <span className="risk-summary-label">
            <strong>{totalAtRisk.toLocaleString()}</strong> of{" "}
            {totalPoints.toLocaleString()} forecast points at risk (
            {getPercentage(totalAtRisk)}%)
          </span>
        </div>
      )}

      {/* Note about data */}
      <div className="data-note">
        Based on multi-model ensemble forecast for{" "}
        {params?.placename || "selected region"}. Thresholds: Warning &ge; 150,
        Alarm &ge; 300, Emergency &ge; 450 m&sup3;/s.
      </div>
    </div>
  );
};

export default AlertSummaryWidget;
