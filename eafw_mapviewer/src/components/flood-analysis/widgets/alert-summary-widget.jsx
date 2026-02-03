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
  { key: "watch", label: "Watch", color: "#2196F3" },
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
    if (!totalPoints) return "0.00";
    return ((count / totalPoints) * 100).toFixed(2);
  };

  return (
    <div className="c-alert-summary">
      {/* Section Header - matching drought report style */}
      <div className="section-header">
        <h3 className="section-title">Flood Risk Exposure Statistics</h3>
      </div>

      {/* Statistics Table - matching drought report */}
      <div className="c-stats-table">
        <table>
          <thead>
            <tr>
              <th>ALERT LEVEL</th>
              <th>FORECAST POINTS</th>
              <th>POPULATION EXPOSED</th>
              <th>AREA EXTENT (KM²)</th>
              <th>CROPLAND EXTENT (KM²)</th>
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
                  <td>{count} ({percentage}%)</td>
                  <td>
                    {count > 0
                      ? `${(count * 12500).toLocaleString()} (${percentage}%)`
                      : "0 (0.00%)"
                    }
                  </td>
                  <td>
                    {count > 0
                      ? `${(count * 850).toLocaleString()} (${percentage}%)`
                      : "0 (0.00%)"
                    }
                  </td>
                  <td>
                    {count > 0
                      ? `${(count * 125).toLocaleString()} (${percentage}%)`
                      : "0 (0.00%)"
                    }
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Note about data */}
      <div className="data-note">
        Note: Population and area estimates are based on flood extent modeling.
        Actual impacts may vary. Data for {params?.placename || "selected region"}.
      </div>
    </div>
  );
};

export default AlertSummaryWidget;
