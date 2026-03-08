/**
 * Risk Assessment Map Widget
 * Allows hydrologists and meteorologists to click on admin2 areas
 * and assign risk levels with comments
 */
import React, { useState, useEffect, useRef, useCallback } from "react";
import PropTypes from "prop-types";
import maplibregl from "maplibre-gl";
import { isEmpty } from "lodash";

import { CMS_API } from "@/utils/constants";
import Loader from "@/components/ui/loader";
import Button from "@/components/ui/button";

import "./styles.scss";

// Risk level configuration
const RISK_LEVELS = [
  { value: "normal", label: "Normal", color: "#b0b0b0", description: "No flood risk expected" },
  { value: "warning", label: "Moderate", color: "#FFC107", description: "Moderate flood risk - monitor situation" },
  { value: "alarm", label: "Severe", color: "#FF9800", description: "High flood risk - prepare for action" },
  { value: "emergency", label: "Extreme", color: "#F44336", description: "Extreme flood risk - immediate action required" },
];

// Default map style (simple basemap)
const DEFAULT_STYLE = {
  version: 8,
  sources: {
    osm: {
      type: "raster",
      tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
      tileSize: 256,
      attribution: "© OpenStreetMap contributors",
    },
  },
  layers: [
    {
      id: "osm-tiles",
      type: "raster",
      source: "osm",
      minzoom: 0,
      maxzoom: 19,
    },
  ],
};

// GHA bounds
const GHA_BOUNDS = [[21, -12], [52, 23]];

const RiskAssessmentMap = ({
  params,
  forecastDate,
  onAssessmentsChange,
  readOnly = false,
}) => {
  const mapContainer = useRef(null);
  const map = useRef(null);
  const [loading, setLoading] = useState(true);
  const [selectedArea, setSelectedArea] = useState(null);
  const [assessments, setAssessments] = useState({});
  const [showPanel, setShowPanel] = useState(false);
  const [comment, setComment] = useState("");
  const [selectedRisk, setSelectedRisk] = useState("normal");
  const [saving, setSaving] = useState(false);
  const [countries, setCountries] = useState([]);
  const [selectedCountry, setSelectedCountry] = useState("");

  // Fetch countries for filter
  useEffect(() => {
    const fetchCountries = async () => {
      try {
        const response = await fetch(`/api/admin-boundaries/`);
        if (response.ok) {
          const data = await response.json();
          setCountries(Array.isArray(data) ? data : []);
        }
      } catch (error) {
        console.error("Failed to fetch countries:", error);
      }
    };
    fetchCountries();
  }, []);

  // Initialize map
  useEffect(() => {
    if (map.current) return;

    map.current = new maplibregl.Map({
      container: mapContainer.current,
      style: DEFAULT_STYLE,
      bounds: GHA_BOUNDS,
      fitBoundsOptions: { padding: 20 },
    });

    map.current.addControl(new maplibregl.NavigationControl(), "top-right");

    map.current.on("load", () => {
      // Add admin2 boundaries source (from pg_tileserv)
      map.current.addSource("admin2", {
        type: "vector",
        tiles: [`${CMS_API}/pg/tileserv/gha.admin2/{z}/{x}/{y}.pbf`],
        minzoom: 0,
        maxzoom: 14,
      });

      // Add fill layer for admin2 (colored by risk)
      map.current.addLayer({
        id: "admin2-fill",
        type: "fill",
        source: "admin2",
        "source-layer": "gha.admin2",
        paint: {
          "fill-color": [
            "case",
            ["has", ["get", "name_2"], ["literal", {}]],
            ["get", ["get", "name_2"], ["literal", {}]],
            "rgba(100, 100, 100, 0.1)",
          ],
          "fill-opacity": 0.6,
        },
      });

      // Add outline layer
      map.current.addLayer({
        id: "admin2-outline",
        type: "line",
        source: "admin2",
        "source-layer": "gha.admin2",
        paint: {
          "line-color": "#333",
          "line-width": 1,
        },
      });

      // Add hover highlight layer
      map.current.addLayer({
        id: "admin2-hover",
        type: "fill",
        source: "admin2",
        "source-layer": "gha.admin2",
        paint: {
          "fill-color": "#627BC1",
          "fill-opacity": 0.3,
        },
        filter: ["==", "name_2", ""],
      });

      setLoading(false);
    });

    const hoverPopup = new maplibregl.Popup({
      closeButton: false,
      closeOnClick: false,
      offset: 10,
    });

    // Click handler
    map.current.on("click", "admin2-fill", (e) => {
      if (readOnly) return;

      const feature = e.features[0];
      if (feature) {
        const props = feature.properties;
        setSelectedArea({
          name_2: props.name_2,
          name_1: props.name_1,
          country: props.country,
          gid_2: props.gid_2,
        });

        // Load existing assessment if any
        const key = `${props.country}-${props.name_1}-${props.name_2}`;
        const existing = assessments[key];
        if (existing) {
          setSelectedRisk(existing.risk_level);
          setComment(existing.comment || "");
        } else {
          setSelectedRisk("normal");
          setComment("");
        }

        setShowPanel(true);
      }
    });

    // Hover effect
    map.current.on("mousemove", "admin2-fill", (e) => {
      if (e.features.length > 0) {
        const props = e.features[0].properties || {};
        const districtName = props.name_2 || "District";
        const admin1Name = props.name_1 || "N/A";
        const countryName = props.country || "";

        map.current.getCanvas().style.cursor = "pointer";
        map.current.setFilter("admin2-hover", [
          "==",
          "name_2",
          districtName,
        ]);

        hoverPopup
          .setLngLat(e.lngLat)
          .setHTML(
            `<div style="font-size:12px;line-height:1.35">`
            + `<strong>${districtName}</strong><br/>`
            + `<span style="color:#334155">Admin 1: ${admin1Name}</span><br/>`
            + `<span style="color:#666">${countryName}</span>`
            + `</div>`
          )
          .addTo(map.current);
      }
    });

    map.current.on("mouseleave", "admin2-fill", () => {
      map.current.getCanvas().style.cursor = "";
      map.current.setFilter("admin2-hover", ["==", "name_2", ""]);
      hoverPopup.remove();
    });

    return () => {
      if (map.current) {
        map.current.remove();
        map.current = null;
      }
    };
  }, [readOnly]);

  // Update map colors when assessments change
  useEffect(() => {
    if (!map.current || !map.current.isStyleLoaded()) return;

    // Build color expression from assessments
    const colorExpression = ["match", ["get", "name_2"]];

    Object.entries(assessments).forEach(([key, assessment]) => {
      const name_2 = key.split("-").pop();
      const riskConfig = RISK_LEVELS.find((r) => r.value === assessment.risk_level);
      if (riskConfig) {
        colorExpression.push(name_2, riskConfig.color);
      }
    });

    // Default color
    colorExpression.push("rgba(100, 100, 100, 0.1)");

    map.current.setPaintProperty("admin2-fill", "fill-color", colorExpression);
  }, [assessments]);

  // Filter map by country
  useEffect(() => {
    if (!map.current || !map.current.isStyleLoaded()) return;

    if (selectedCountry) {
      map.current.setFilter("admin2-fill", ["==", "country", selectedCountry]);
      map.current.setFilter("admin2-outline", ["==", "country", selectedCountry]);
    } else {
      map.current.setFilter("admin2-fill", null);
      map.current.setFilter("admin2-outline", null);
    }
  }, [selectedCountry]);

  // Load existing assessments
  useEffect(() => {
    const loadAssessments = async () => {
      if (!forecastDate) return;

      try {
        const response = await fetch(
          `${CMS_API}/risk-assessments/?date=${forecastDate}`
        );
        if (response.ok) {
          const data = await response.json();
          const assessmentMap = {};
          (data.assessments || []).forEach((a) => {
            const key = `${a.country}-${a.admin1}-${a.admin2}`;
            assessmentMap[key] = {
              risk_level: a.risk_level,
              comment: a.comment,
              updated_by: a.updated_by,
              updated_at: a.updated_at,
            };
          });
          setAssessments(assessmentMap);
        }
      } catch (error) {
        console.error("Failed to load assessments:", error);
      }
    };

    loadAssessments();
  }, [forecastDate]);

  // Save assessment
  const handleSaveAssessment = useCallback(async () => {
    if (!selectedArea) return;

    setSaving(true);
    try {
      const key = `${selectedArea.country}-${selectedArea.name_1}-${selectedArea.name_2}`;

      // Update local state
      const newAssessments = {
        ...assessments,
        [key]: {
          risk_level: selectedRisk,
          comment: comment,
          updated_at: new Date().toISOString(),
        },
      };
      setAssessments(newAssessments);

      // Save to backend
      const response = await fetch(`${CMS_API}/risk-assessments/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          forecast_date: forecastDate || new Date().toISOString().split("T")[0],
          country: selectedArea.country,
          admin1: selectedArea.name_1,
          admin2: selectedArea.name_2,
          gid_2: selectedArea.gid_2,
          risk_level: selectedRisk,
          comment: comment,
        }),
      });

      if (!response.ok) {
        console.error("Failed to save assessment to server");
      }

      // Notify parent
      if (onAssessmentsChange) {
        onAssessmentsChange(newAssessments);
      }

      setShowPanel(false);
      setSelectedArea(null);
    } catch (error) {
      console.error("Error saving assessment:", error);
    } finally {
      setSaving(false);
    }
  }, [selectedArea, selectedRisk, comment, assessments, forecastDate, onAssessmentsChange]);

  // Cancel editing
  const handleCancel = () => {
    setShowPanel(false);
    setSelectedArea(null);
    setComment("");
    setSelectedRisk("normal");
  };

  // Get assessment summary
  const getAssessmentSummary = () => {
    const summary = { normal: 0, warning: 0, alarm: 0, emergency: 0 };
    Object.values(assessments).forEach((a) => {
      if (summary[a.risk_level] !== undefined) {
        summary[a.risk_level]++;
      }
    });
    return summary;
  };

  const summary = getAssessmentSummary();

  return (
    <div className="c-risk-assessment-map">
      <div className="widget-header">
        <h3 className="widget-title">Expert Risk Assessment</h3>
        <p className="widget-subtitle">
          Click on admin2 areas to assign flood risk levels
        </p>
      </div>

      {/* Country Filter */}
      <div className="country-filter">
        <label>Filter by Country:</label>
        <select
          value={selectedCountry}
          onChange={(e) => setSelectedCountry(e.target.value)}
        >
          <option value="">All Countries</option>
          {countries.map((c) => (
            <option key={c.code} value={c.code}>
              {c.name}
            </option>
          ))}
        </select>
      </div>

      {/* Assessment Summary */}
      <div className="assessment-summary">
        {RISK_LEVELS.map((level) => (
          <div key={level.value} className="summary-item">
            <span
              className="summary-color"
              style={{ backgroundColor: level.color }}
            />
            <span className="summary-label">{level.label}:</span>
            <span className="summary-count">{summary[level.value]}</span>
          </div>
        ))}
      </div>

      {/* Map Container */}
      <div className="map-wrapper">
        {loading && (
          <div className="map-loader">
            <Loader />
          </div>
        )}
        <div ref={mapContainer} className="map-container" />

        {/* Legend */}
        <div className="map-legend">
          <div className="legend-title">Risk Levels</div>
          {RISK_LEVELS.map((level) => (
            <div key={level.value} className="legend-item">
              <span
                className="legend-color"
                style={{ backgroundColor: level.color }}
              />
              <span className="legend-label">{level.label}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Edit Panel */}
      {showPanel && selectedArea && (
        <div className="edit-panel">
          <div className="panel-header">
            <h4>Set Risk Level</h4>
            <button className="close-btn" onClick={handleCancel}>
              ×
            </button>
          </div>

          <div className="panel-content">
            <div className="area-info">
              <div className="area-name">{selectedArea.name_2}</div>
              <div className="area-parents">
                {selectedArea.name_1}, {selectedArea.country}
              </div>
            </div>

            <div className="risk-selector">
              <label>Risk Level:</label>
              <div className="risk-options">
                {RISK_LEVELS.map((level) => (
                  <label
                    key={level.value}
                    className={`risk-option ${selectedRisk === level.value ? "selected" : ""}`}
                    style={{
                      borderColor: level.color,
                      backgroundColor:
                        selectedRisk === level.value ? level.color : "transparent",
                    }}
                  >
                    <input
                      type="radio"
                      name="risk-level"
                      value={level.value}
                      checked={selectedRisk === level.value}
                      onChange={(e) => setSelectedRisk(e.target.value)}
                    />
                    <span className="risk-label">{level.label}</span>
                  </label>
                ))}
              </div>
            </div>

            <div className="comment-section">
              <label>Comment / Justification:</label>
              <textarea
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                placeholder="Add notes about this assessment..."
                rows={3}
              />
            </div>

            <div className="panel-actions">
              <Button theme="theme-button-light" onClick={handleCancel}>
                Cancel
              </Button>
              <Button
                theme="theme-button-green"
                onClick={handleSaveAssessment}
                disabled={saving}
              >
                {saving ? "Saving..." : "Save Assessment"}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

RiskAssessmentMap.propTypes = {
  params: PropTypes.object,
  forecastDate: PropTypes.string,
  onAssessmentsChange: PropTypes.func,
  readOnly: PropTypes.bool,
};

export default RiskAssessmentMap;
