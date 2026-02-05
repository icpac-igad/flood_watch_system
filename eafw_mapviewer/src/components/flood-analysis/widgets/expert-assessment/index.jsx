/**
 * Expert Assessment Widget
 * Two sections: one for Hydrologists and one for Meteorologists
 * Each has: 1) Comment section first, 2) Interactive map to set risk levels
 * NOT side-by-side - stacked vertically
 */
import React, { useState, useEffect, useRef, useCallback } from "react";
import PropTypes from "prop-types";
import maplibregl from "maplibre-gl";
import { isEmpty } from "lodash";

import { CMS_API } from "@/utils/constants";
import Loader from "@/components/ui/loader";
import Button from "@/components/ui/button";

import "./styles.scss";

// Risk level configurations
const RISK_LEVELS = [
  { value: "normal", label: "Normal", color: "#4CAF50", description: "Normal conditions" },
  { value: "watch", label: "Watch", color: "#2196F3", description: "Monitoring" },
  { value: "warning", label: "Warning", color: "#FFC107", description: "Elevated risk" },
  { value: "alarm", label: "Alarm", color: "#FF9800", description: "High risk" },
  { value: "emergency", label: "Emergency", color: "#F44336", description: "Severe" },
];

// Expert types configuration
const EXPERT_TYPES = {
  hydrologist: {
    title: "Hydrologist Assessment",
    subtitle: "Flood risk assessment based on river levels and discharge forecasts",
    icon: "💧",
    color: "#1976d2",
  },
  meteorologist: {
    title: "Meteorologist Assessment",
    subtitle: "Weather and rainfall-related flood risk assessment",
    icon: "🌧️",
    color: "#FF9800",
  },
};

// Default map style
const DEFAULT_STYLE = {
  version: 8,
  sources: {
    osm: {
      type: "raster",
      tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
      tileSize: 256,
      attribution: "© OpenStreetMap",
    },
  },
  layers: [
    { id: "osm-tiles", type: "raster", source: "osm", minzoom: 0, maxzoom: 19 },
  ],
};

const GHA_BOUNDS = [[21, -12], [52, 23]];

// Single Expert Section Component
const ExpertSection = ({
  expertType,
  config,
  forecastDate,
  selectedCountry,
  requireComment = false,
  onCommentError,
}) => {
  const mapContainer = useRef(null);
  const map = useRef(null);
  const [loading, setLoading] = useState(true);
  const [assessments, setAssessments] = useState({});
  const [overallComment, setOverallComment] = useState("");
  const [overallRisk, setOverallRisk] = useState("normal");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  // For popup editing
  const [selectedArea, setSelectedArea] = useState(null);
  const [showEditPanel, setShowEditPanel] = useState(false);
  const [editRisk, setEditRisk] = useState("normal");
  const [editComment, setEditComment] = useState("");

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
      // Add admin2 boundaries source
      map.current.addSource("admin2", {
        type: "vector",
        tiles: [`${window.location.origin}/pg/tileserv/gha.admin2/{z}/{x}/{y}.pbf`],
        minzoom: 0,
        maxzoom: 14,
      });

      // Fill layer - will be colored based on assessments
      map.current.addLayer({
        id: "admin2-fill",
        type: "fill",
        source: "admin2",
        "source-layer": "gha.admin2",
        paint: {
          "fill-color": "rgba(200, 200, 200, 0.3)",
          "fill-opacity": 0.7,
        },
      });

      // Outline layer
      map.current.addLayer({
        id: "admin2-outline",
        type: "line",
        source: "admin2",
        "source-layer": "gha.admin2",
        paint: { "line-color": "#666", "line-width": 0.5 },
      });

      // Hover layer
      map.current.addLayer({
        id: "admin2-hover",
        type: "fill",
        source: "admin2",
        "source-layer": "gha.admin2",
        paint: { "fill-color": "#627BC1", "fill-opacity": 0.5 },
        filter: ["==", "name_2", ""],
      });

      setLoading(false);
    });

    // Click handler for setting risk level
    map.current.on("click", "admin2-fill", (e) => {
      const feature = e.features[0];
      if (feature) {
        const props = feature.properties;
        setSelectedArea({
          name_2: props.name_2,
          name_1: props.name_1,
          country: props.country,
          gid_2: props.gid_2,
        });

        const key = `${props.country}-${props.name_1}-${props.name_2}`;
        const existing = assessments[key];
        if (existing) {
          setEditRisk(existing.risk_level);
          setEditComment(existing.comment || "");
        } else {
          setEditRisk("normal");
          setEditComment("");
        }
        setShowEditPanel(true);
      }
    });

    // Hover effects
    map.current.on("mousemove", "admin2-fill", (e) => {
      if (e.features.length > 0) {
        map.current.getCanvas().style.cursor = "pointer";
        map.current.setFilter("admin2-hover", ["==", "name_2", e.features[0].properties.name_2]);
      }
    });

    map.current.on("mouseleave", "admin2-fill", () => {
      map.current.getCanvas().style.cursor = "";
      map.current.setFilter("admin2-hover", ["==", "name_2", ""]);
    });

    return () => {
      if (map.current) {
        map.current.remove();
        map.current = null;
      }
    };
  }, []);

  // Update map colors when assessments change
  useEffect(() => {
    if (!map.current || !map.current.isStyleLoaded()) return;

    const colorExpression = ["match", ["get", "name_2"]];
    Object.entries(assessments).forEach(([key, assessment]) => {
      const name_2 = key.split("-").pop();
      const riskConfig = RISK_LEVELS.find((r) => r.value === assessment.risk_level);
      if (riskConfig) {
        colorExpression.push(name_2, riskConfig.color);
      }
    });
    colorExpression.push("rgba(200, 200, 200, 0.3)");

    try {
      map.current.setPaintProperty("admin2-fill", "fill-color", colorExpression);
    } catch (e) {
      // Layer may not be ready
    }
  }, [assessments]);

  // Filter by selected country
  useEffect(() => {
    if (!map.current || !map.current.isStyleLoaded()) return;

    const filter = selectedCountry ? ["==", "country", selectedCountry] : null;
    try {
      map.current.setFilter("admin2-fill", filter);
      map.current.setFilter("admin2-outline", filter);
    } catch (e) {
      // Layer may not be ready
    }
  }, [selectedCountry]);

  // Load existing assessments
  useEffect(() => {
    const loadAssessments = async () => {
      if (!forecastDate) return;

      try {
        const response = await fetch(
          `${CMS_API}/risk-assessments/?date=${forecastDate}&expert_type=${expertType}`
        );
        if (response.ok) {
          const data = await response.json();
          const assessmentMap = {};
          (data.assessments || []).forEach((a) => {
            const key = `${a.country}-${a.admin1}-${a.admin2}`;
            assessmentMap[key] = {
              risk_level: a.risk_level,
              comment: a.comment,
            };
          });
          setAssessments(assessmentMap);
        }
      } catch (error) {
        console.error("Failed to load assessments:", error);
      }
    };
    loadAssessments();
  }, [forecastDate, expertType]);

  // Save area risk level
  const handleSaveAreaRisk = useCallback(async () => {
    if (!selectedArea) return;
    setSaving(true);

    try {
      const key = `${selectedArea.country}-${selectedArea.name_1}-${selectedArea.name_2}`;
      const newAssessments = {
        ...assessments,
        [key]: {
          risk_level: editRisk,
          comment: editComment,
        },
      };
      setAssessments(newAssessments);

      // Save to backend
      await fetch(`${CMS_API}/risk-assessments/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          expert_type: expertType,
          forecast_date: forecastDate || new Date().toISOString().split("T")[0],
          country: selectedArea.country,
          admin1: selectedArea.name_1,
          admin2: selectedArea.name_2,
          gid_2: selectedArea.gid_2,
          risk_level: editRisk,
          comment: editComment,
        }),
      });

      setShowEditPanel(false);
      setSelectedArea(null);
    } catch (error) {
      console.error("Error saving:", error);
    } finally {
      setSaving(false);
    }
  }, [selectedArea, editRisk, editComment, assessments, forecastDate, expertType]);

  // Save overall assessment
  const handleSaveOverall = useCallback(async () => {
    // Validate comment if required
    if (requireComment && !overallComment.trim()) {
      if (onCommentError) onCommentError(true);
      return;
    }
    if (onCommentError) onCommentError(false);

    setSaving(true);
    try {
      await fetch(`${CMS_API}/country-assessments/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          expert_type: expertType,
          forecast_date: forecastDate || new Date().toISOString().split("T")[0],
          country_code: selectedCountry || "REGION",
          country_name: selectedCountry || "East Africa Region",
          risk_level: overallRisk,
          comment: overallComment,
        }),
      });
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (error) {
      console.error("Error saving overall assessment:", error);
    } finally {
      setSaving(false);
    }
  }, [overallComment, overallRisk, forecastDate, expertType, selectedCountry, requireComment, onCommentError]);

  const handleCancelEdit = () => {
    setShowEditPanel(false);
    setSelectedArea(null);
    setEditComment("");
    setEditRisk("normal");
  };

  // Summary counts
  const getSummary = () => {
    const summary = {};
    RISK_LEVELS.forEach((l) => { summary[l.value] = 0; });
    Object.values(assessments).forEach((a) => {
      if (summary[a.risk_level] !== undefined) summary[a.risk_level]++;
    });
    return summary;
  };

  const summary = getSummary();

  return (
    <div className="expert-section" style={{ borderTopColor: config.color }}>
      <div className="section-header">
        <div className="header-left">
          <span className="section-icon">{config.icon}</span>
          <div>
            <h4>{config.title}</h4>
            <p>{config.subtitle}</p>
          </div>
        </div>
      </div>

      {/* Overall Comment Section - FIRST */}
      <div className="overall-assessment">
        <h5>Overall Assessment Comment</h5>
        <p className="hint">Provide your overall assessment for the region or selected country</p>

        <div className="overall-risk-selector">
          <label>Overall Risk Level:</label>
          <div className="risk-buttons">
            {RISK_LEVELS.map((level) => (
              <button
                key={level.value}
                className={`risk-btn ${overallRisk === level.value ? "selected" : ""}`}
                style={{
                  borderColor: level.color,
                  backgroundColor: overallRisk === level.value ? level.color : "transparent",
                  color: overallRisk === level.value ? "white" : level.color,
                }}
                onClick={() => setOverallRisk(level.value)}
              >
                {level.label}
              </button>
            ))}
          </div>
        </div>

        <textarea
          value={overallComment}
          onChange={(e) => {
            setOverallComment(e.target.value);
            if (onCommentError && e.target.value.trim()) onCommentError(false);
          }}
          placeholder={`Enter your ${expertType} assessment, observations, and recommendations...${requireComment ? " (Required)" : ""}`}
          rows={4}
          className={requireComment && !overallComment.trim() ? "required-field" : ""}
          required={requireComment}
        />

        <div className="save-row">
          <Button
            theme="theme-button-green"
            onClick={handleSaveOverall}
            disabled={saving}
          >
            {saving ? "Saving..." : saved ? "✓ Saved" : "Save Assessment"}
          </Button>
          {saved && <span className="saved-indicator">Assessment saved successfully!</span>}
        </div>
      </div>

      {/* Risk Map - SECOND */}
      <div className="risk-map-section">
        <h5>District Risk Levels</h5>
        <p className="hint">Click on districts to set specific risk levels (optional)</p>

        {/* Summary */}
        <div className="assessment-summary">
          {RISK_LEVELS.map((level) => (
            <div key={level.value} className="summary-item">
              <span className="summary-color" style={{ backgroundColor: level.color }} />
              <span className="summary-label">{level.label}:</span>
              <span className="summary-count">{summary[level.value]}</span>
            </div>
          ))}
        </div>

        {/* Map */}
        <div className="map-wrapper">
          {loading && <div className="map-loader"><Loader /></div>}
          <div ref={mapContainer} className="map-container" />

          {/* Legend */}
          <div className="map-legend">
            <div className="legend-title">Risk Levels</div>
            {RISK_LEVELS.map((level) => (
              <div key={level.value} className="legend-item">
                <span className="legend-color" style={{ backgroundColor: level.color }} />
                <span className="legend-label">{level.label}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Edit Panel for individual district */}
      {showEditPanel && selectedArea && (
        <div className="edit-panel-overlay" onClick={handleCancelEdit}>
          <div className="edit-panel" onClick={(e) => e.stopPropagation()}>
            <div className="panel-header">
              <h4>Set District Risk Level</h4>
              <button className="close-btn" onClick={handleCancelEdit}>×</button>
            </div>

            <div className="panel-content">
              <div className="area-info">
                <div className="area-name">{selectedArea.name_2}</div>
                <div className="area-parents">{selectedArea.name_1}, {selectedArea.country}</div>
              </div>

              <div className="risk-selector">
                <label>Risk Level:</label>
                <div className="risk-options">
                  {RISK_LEVELS.map((level) => (
                    <label
                      key={level.value}
                      className={`risk-option ${editRisk === level.value ? "selected" : ""}`}
                      style={{
                        borderColor: level.color,
                        backgroundColor: editRisk === level.value ? level.color : "transparent",
                      }}
                    >
                      <input
                        type="radio"
                        name={`risk-${expertType}`}
                        value={level.value}
                        checked={editRisk === level.value}
                        onChange={(e) => setEditRisk(e.target.value)}
                      />
                      <span className="risk-label">{level.label}</span>
                    </label>
                  ))}
                </div>
              </div>

              <div className="comment-section">
                <label>Comment (optional):</label>
                <textarea
                  value={editComment}
                  onChange={(e) => setEditComment(e.target.value)}
                  placeholder="Add notes about this district..."
                  rows={3}
                />
              </div>

              <div className="panel-actions">
                <Button theme="theme-button-light" onClick={handleCancelEdit}>Cancel</Button>
                <Button theme="theme-button-green" onClick={handleSaveAreaRisk} disabled={saving}>
                  {saving ? "Saving..." : "Save"}
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

// Main component - single expert assessment with type selector
const ExpertAssessmentWidget = ({
  params,
  forecastDate,
  selectedCountry,
}) => {
  const [expertType, setExpertType] = useState("hydrologist");
  const [commentError, setCommentError] = useState(false);

  const handleExpertTypeChange = (type) => {
    setExpertType(type);
    setCommentError(false);
  };

  return (
    <div className="c-expert-assessment">
      <div className="widget-header">
        <h3 className="widget-title">Expert Risk Assessment</h3>
        <p className="widget-subtitle">
          Provide your expert assessment. Comment is required.
        </p>
      </div>

      {/* Expert Type Selector */}
      <div className="expert-type-selector">
        <label className="selector-label">I am a:</label>
        <div className="type-buttons">
          {Object.entries(EXPERT_TYPES).map(([type, config]) => (
            <button
              key={type}
              className={`type-btn ${expertType === type ? "selected" : ""}`}
              style={{
                borderColor: config.color,
                backgroundColor: expertType === type ? config.color : "transparent",
                color: expertType === type ? "white" : config.color,
              }}
              onClick={() => handleExpertTypeChange(type)}
            >
              <span className="type-icon">{config.icon}</span>
              <span className="type-label">
                {type === "hydrologist" ? "Hydrologist" : "Meteorologist"}
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* Single Expert Section based on selected type */}
      <ExpertSection
        expertType={expertType}
        config={EXPERT_TYPES[expertType]}
        forecastDate={forecastDate}
        selectedCountry={selectedCountry}
        requireComment={true}
        onCommentError={setCommentError}
      />

      {commentError && (
        <div className="comment-error-message">
          Please provide an assessment comment before saving.
        </div>
      )}
    </div>
  );
};

ExpertAssessmentWidget.propTypes = {
  params: PropTypes.object,
  forecastDate: PropTypes.string,
  selectedCountry: PropTypes.string,
};

export default ExpertAssessmentWidget;
