/**
 * Alert Summary Widget
 * Displays flood risk exposure statistics - matching drought report design
 */
import React from "react";

import Loader from "@/components/ui/loader";
import {
  DEFAULT_THRESHOLDS,
  ALERT_COLORS,
  ALERT_LEVEL_ORDER,
  ALERT_LEVEL_LABELS,
} from "@/utils/multimodal-config";

const ALERT_LEVELS = ALERT_LEVEL_ORDER
  .filter((level) => level !== "normal")
  .map((level) => ({
    key: level,
    label: ALERT_LEVEL_LABELS[level],
    color: ALERT_COLORS[level],
  }));

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
              <td><strong>Total at Risk</strong></td>
              <td><strong>{totalAtRisk.toLocaleString()}</strong></td>
              <td><strong>{getPercentage(totalAtRisk)}%</strong></td>
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
        {params?.placename || "selected region"}. Thresholds: Moderate &ge; {DEFAULT_THRESHOLDS.warning},
        Severe &ge; {DEFAULT_THRESHOLDS.alarm}, Extreme &ge; {DEFAULT_THRESHOLDS.emergency} m&sup3;/s.
      </div>
    </div>
  );
};

export default AlertSummaryWidget;
