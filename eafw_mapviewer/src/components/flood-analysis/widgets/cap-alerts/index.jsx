import React, { useState, useEffect } from "react";
import PropTypes from "prop-types";
import { getActiveAlerts } from "@/services/cap";
import Loader from "@/components/ui/loader";

const SEVERITY_COLORS = {
  Extreme: "#d32f2f",
  Severe: "#f57c00",
  Moderate: "#fbc02d",
  Minor: "#4caf50",
};

const CapAlertsWidget = ({ forecastDate, selectedCountry }) => {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    const params = {};
    if (selectedCountry) params.country = selectedCountry;
    if (forecastDate) params.date = forecastDate;

    getActiveAlerts(params)
      .then((data) => setAlerts(data?.features || []))
      .catch(() => setAlerts([]))
      .finally(() => setLoading(false));
  }, [forecastDate, selectedCountry]);

  if (loading) {
    return (
      <div className="cap-alerts-widget" style={{ padding: 16 }}>
        <Loader />
      </div>
    );
  }

  if (!alerts.length) {
    return (
      <div
        className="cap-alerts-widget"
        style={{ padding: "12px 16px", color: "#666", fontSize: 13 }}
      >
        No active CAP alerts
      </div>
    );
  }

  return (
    <div className="cap-alerts-widget" style={{ padding: "8px 0" }}>
      <h4 style={{ margin: "0 0 8px", fontSize: 14, fontWeight: 600 }}>
        Active CAP Alerts ({alerts.length})
      </h4>
      <div style={{ maxHeight: 300, overflowY: "auto" }}>
        {alerts.map((alert) => {
          const props = alert.properties || {};
          const severity = props.severity || "Minor";
          return (
            <div
              key={props.identifier || alert.id}
              style={{
                borderLeft: `4px solid ${SEVERITY_COLORS[severity] || "#999"}`,
                padding: "8px 12px",
                marginBottom: 6,
                backgroundColor: "#fafafa",
                borderRadius: 4,
                fontSize: 13,
              }}
            >
              <div style={{ fontWeight: 600 }}>{props.headline || "CAP Alert"}</div>
              <div style={{ display: "flex", gap: 12, marginTop: 4, color: "#555" }}>
                <span
                  style={{
                    color: SEVERITY_COLORS[severity],
                    fontWeight: 700,
                    fontSize: 12,
                  }}
                >
                  {severity}
                </span>
                {props.expires && (
                  <span style={{ fontSize: 12 }}>
                    Expires: {new Date(props.expires).toLocaleDateString()}
                  </span>
                )}
              </div>
              {props.description && (
                <div style={{ marginTop: 4, fontSize: 12, color: "#666", lineHeight: 1.4 }}>
                  {props.description.length > 150
                    ? `${props.description.slice(0, 150)}...`
                    : props.description}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

CapAlertsWidget.propTypes = {
  forecastDate: PropTypes.string,
  selectedCountry: PropTypes.string,
};

export default CapAlertsWidget;
