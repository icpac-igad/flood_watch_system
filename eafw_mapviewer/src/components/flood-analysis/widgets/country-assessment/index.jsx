/**
 * Country Assessment Widget
 * Each GHA country member can filter and add comments
 * When all countries have commented, system generates regional summary
 */
import React, { useState, useEffect, useCallback } from "react";
import PropTypes from "prop-types";
import { isEmpty } from "lodash";

import { CMS_API } from "@/utils/constants";
import Button from "@/components/ui/button";
import Loader from "@/components/ui/loader";

import "./styles.scss";

// GHA Countries
const GHA_COUNTRIES = [
  { code: "BDI", name: "Burundi", flag: "🇧🇮" },
  { code: "DJI", name: "Djibouti", flag: "🇩🇯" },
  { code: "ETH", name: "Ethiopia", flag: "🇪🇹" },
  { code: "KEN", name: "Kenya", flag: "🇰🇪" },
  { code: "RWA", name: "Rwanda", flag: "🇷🇼" },
  { code: "SOM", name: "Somalia", flag: "🇸🇴" },
  { code: "SSD", name: "South Sudan", flag: "🇸🇸" },
  { code: "SDN", name: "Sudan", flag: "🇸🇩" },
  { code: "TZA", name: "Tanzania", flag: "🇹🇿" },
  { code: "UGA", name: "Uganda", flag: "🇺🇬" },
];

// Risk levels
const RISK_LEVELS = [
  { value: "normal", label: "Normal", color: "#b0b0b0" },
  { value: "watch", label: "Watch", color: "#2196F3" },
  { value: "warning", label: "Moderate", color: "#FFC107" },
  { value: "alarm", label: "Severe", color: "#FF9800" },
  { value: "emergency", label: "Extreme", color: "#F44336" },
];

// Single Country Assessment Card
const CountryAssessmentCard = ({
  country,
  assessment,
  expertType,
  forecastDate,
  onSave,
  isExpanded,
  onToggle,
}) => {
  const [riskLevel, setRiskLevel] = useState(assessment?.risk_level || "normal");
  const [comment, setComment] = useState(assessment?.comment || "");
  const [affectedAreas, setAffectedAreas] = useState(assessment?.affected_areas || "");
  const [recommendations, setRecommendations] = useState(assessment?.recommendations || "");
  const [saving, setSaving] = useState(false);

  // Update local state when assessment changes
  useEffect(() => {
    if (assessment) {
      setRiskLevel(assessment.risk_level || "normal");
      setComment(assessment.comment || "");
      setAffectedAreas(assessment.affected_areas || "");
      setRecommendations(assessment.recommendations || "");
    }
  }, [assessment]);

  const handleSave = async () => {
    setSaving(true);
    try {
      await onSave({
        country_code: country.code,
        country_name: country.name,
        expert_type: expertType,
        forecast_date: forecastDate,
        risk_level: riskLevel,
        comment,
        affected_areas: affectedAreas,
        recommendations,
      });
    } finally {
      setSaving(false);
    }
  };

  const hasContent = assessment && (assessment.comment || assessment.risk_level !== "normal");
  const riskConfig = RISK_LEVELS.find((r) => r.value === riskLevel);

  return (
    <div className={`country-card ${isExpanded ? "expanded" : ""} ${hasContent ? "has-content" : ""}`}>
      <div
        className="card-header"
        onClick={onToggle}
        style={{ borderLeftColor: riskConfig?.color || "#ddd" }}
      >
        <div className="country-info">
          <span className="country-flag">{country.flag}</span>
          <span className="country-name">{country.name}</span>
        </div>
        <div className="header-right">
          {hasContent && (
            <span
              className="status-badge"
              style={{ backgroundColor: riskConfig?.color }}
            >
              {riskConfig?.label}
            </span>
          )}
          <span className={`expand-icon ${isExpanded ? "expanded" : ""}`}>▼</span>
        </div>
      </div>

      {isExpanded && (
        <div className="card-content">
          {/* Risk Level Selection */}
          <div className="form-group">
            <label>Overall Risk Level</label>
            <div className="risk-buttons">
              {RISK_LEVELS.map((level) => (
                <button
                  key={level.value}
                  className={`risk-btn ${riskLevel === level.value ? "selected" : ""}`}
                  style={{
                    borderColor: level.color,
                    backgroundColor: riskLevel === level.value ? level.color : "transparent",
                    color: riskLevel === level.value ? "white" : level.color,
                  }}
                  onClick={() => setRiskLevel(level.value)}
                >
                  {level.label}
                </button>
              ))}
            </div>
          </div>

          {/* Affected Areas */}
          <div className="form-group">
            <label>Affected Areas / Regions</label>
            <textarea
              value={affectedAreas}
              onChange={(e) => setAffectedAreas(e.target.value)}
              placeholder="List the most affected areas, rivers, or regions..."
              rows={2}
            />
          </div>

          {/* Situation Assessment */}
          <div className="form-group">
            <label>Situation Assessment</label>
            <textarea
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              placeholder="Describe the current flood situation and forecast outlook..."
              rows={4}
            />
          </div>

          {/* Recommendations */}
          <div className="form-group">
            <label>Recommendations</label>
            <textarea
              value={recommendations}
              onChange={(e) => setRecommendations(e.target.value)}
              placeholder="Provide recommended actions for stakeholders..."
              rows={2}
            />
          </div>

          {/* Last Updated */}
          {assessment?.updated_at && (
            <div className="last-updated">
              Last updated: {new Date(assessment.updated_at).toLocaleString()}
              {assessment.updated_by && ` by ${assessment.updated_by}`}
            </div>
          )}

          {/* Save Button */}
          <div className="card-actions">
            <Button
              theme="theme-button-green"
              onClick={handleSave}
              disabled={saving}
            >
              {saving ? "Saving..." : "Save Assessment"}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
};

// Regional Summary Component
const RegionalSummary = ({ assessments, forecastDate }) => {
  const [generating, setGenerating] = useState(false);
  const [summary, setSummary] = useState(null);

  // Calculate submission status
  const submittedCountries = Object.keys(assessments).filter(
    (code) => assessments[code]?.comment
  );
  const allSubmitted = submittedCountries.length === GHA_COUNTRIES.length;
  const submissionProgress = (submittedCountries.length / GHA_COUNTRIES.length) * 100;

  // Get overall risk level
  const getOverallRisk = () => {
    const levels = Object.values(assessments)
      .map((a) => a?.risk_level)
      .filter(Boolean);

    if (levels.includes("emergency")) return "emergency";
    if (levels.includes("alarm")) return "alarm";
    if (levels.includes("warning")) return "warning";
    if (levels.includes("watch")) return "watch";
    return "normal";
  };

  // Generate regional summary
  const handleGenerateSummary = async () => {
    setGenerating(true);
    try {
      const response = await fetch(`${CMS_API}/regional-summary/generate/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          forecast_date: forecastDate,
          assessments: assessments,
        }),
      });

      if (response.ok) {
        const data = await response.json();
        setSummary(data.summary);
      } else {
        // Generate local summary
        setSummary(generateLocalSummary(assessments));
      }
    } catch (error) {
      console.error("Error generating summary:", error);
      setSummary(generateLocalSummary(assessments));
    } finally {
      setGenerating(false);
    }
  };

  // Generate summary locally
  const generateLocalSummary = (assessments) => {
    const riskCounts = { emergency: 0, alarm: 0, warning: 0, watch: 0, normal: 0 };
    const affectedAreasList = [];
    const recommendationsList = [];

    Object.values(assessments).forEach((a) => {
      if (a?.risk_level) riskCounts[a.risk_level]++;
      if (a?.affected_areas) affectedAreasList.push(a.affected_areas);
      if (a?.recommendations) recommendationsList.push(a.recommendations);
    });

    return {
      overall_risk: getOverallRisk(),
      risk_counts: riskCounts,
      affected_areas: affectedAreasList.join("\n\n"),
      combined_recommendations: recommendationsList.join("\n\n"),
      generated_at: new Date().toISOString(),
    };
  };

  const overallRisk = getOverallRisk();
  const riskConfig = RISK_LEVELS.find((r) => r.value === overallRisk);

  return (
    <div className="regional-summary">
      <div className="summary-header">
        <h4>Regional Summary</h4>
        <div
          className="overall-risk-badge"
          style={{ backgroundColor: riskConfig?.color }}
        >
          {riskConfig?.label}
        </div>
      </div>

      {/* Progress Indicator */}
      <div className="submission-progress">
        <div className="progress-bar">
          <div
            className="progress-fill"
            style={{ width: `${submissionProgress}%` }}
          />
        </div>
        <div className="progress-text">
          {submittedCountries.length} of {GHA_COUNTRIES.length} countries submitted
        </div>
      </div>

      {/* Country Submission Status */}
      <div className="submission-status">
        {GHA_COUNTRIES.map((country) => {
          const hasSubmitted = assessments[country.code]?.comment;
          return (
            <div
              key={country.code}
              className={`status-item ${hasSubmitted ? "submitted" : "pending"}`}
              title={country.name}
            >
              {country.flag}
              {hasSubmitted ? "✓" : "○"}
            </div>
          );
        })}
      </div>

      {/* Generate Summary Button */}
      <div className="summary-actions">
        <Button
          theme={allSubmitted ? "theme-button-green" : "theme-button-light"}
          onClick={handleGenerateSummary}
          disabled={generating || submittedCountries.length < 3}
        >
          {generating ? "Generating..." : "Generate Regional Summary"}
        </Button>
        {submittedCountries.length < 3 && (
          <p className="hint">At least 3 countries must submit to generate summary</p>
        )}
      </div>

      {/* Generated Summary */}
      {summary && (
        <div className="generated-summary">
          <h5>Generated Summary Report</h5>
          <div className="summary-content">
            <div className="summary-section">
              <strong>Overall Risk Assessment:</strong>
              <span className="risk-badge" style={{ backgroundColor: riskConfig?.color }}>
                {riskConfig?.label}
              </span>
            </div>

            {summary.affected_areas && (
              <div className="summary-section">
                <strong>Affected Areas:</strong>
                <p>{summary.affected_areas}</p>
              </div>
            )}

            {summary.combined_recommendations && (
              <div className="summary-section">
                <strong>Recommendations:</strong>
                <p>{summary.combined_recommendations}</p>
              </div>
            )}

            <div className="summary-footer">
              Generated: {new Date(summary.generated_at).toLocaleString()}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

// Main Component
const CountryAssessmentWidget = ({
  params,
  forecastDate,
  expertType = "hydrologist",
}) => {
  const [assessments, setAssessments] = useState({});
  const [loading, setLoading] = useState(true);
  const [expandedCountry, setExpandedCountry] = useState(null);
  const [activeExpertType, setActiveExpertType] = useState(expertType);

  // Load existing assessments
  useEffect(() => {
    const loadAssessments = async () => {
      setLoading(true);
      try {
        const response = await fetch(
          `${CMS_API}/country-assessments/?date=${forecastDate || ""}&expert_type=${activeExpertType}`
        );
        if (response.ok) {
          const data = await response.json();
          const assessmentMap = {};
          (data.assessments || []).forEach((a) => {
            assessmentMap[a.country_code] = a;
          });
          setAssessments(assessmentMap);
        }
      } catch (error) {
        console.error("Error loading assessments:", error);
      } finally {
        setLoading(false);
      }
    };

    loadAssessments();
  }, [forecastDate, activeExpertType]);

  // Save assessment
  const handleSaveAssessment = useCallback(async (assessmentData) => {
    try {
      const response = await fetch(`${CMS_API}/country-assessments/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(assessmentData),
      });

      if (response.ok) {
        const data = await response.json();
        setAssessments((prev) => ({
          ...prev,
          [assessmentData.country_code]: {
            ...assessmentData,
            id: data.id,
            updated_at: new Date().toISOString(),
          },
        }));
      }
    } catch (error) {
      console.error("Error saving assessment:", error);
      // Still update local state
      setAssessments((prev) => ({
        ...prev,
        [assessmentData.country_code]: {
          ...assessmentData,
          updated_at: new Date().toISOString(),
        },
      }));
    }
  }, []);

  return (
    <div className="c-country-assessment">
      <div className="widget-header">
        <div className="header-content">
          <h3>Country Flood Assessments</h3>
          <p>Each country member can add their assessment. Regional summary is generated when countries submit.</p>
        </div>

        {/* Expert Type Tabs */}
        <div className="expert-tabs">
          <button
            className={`tab-btn ${activeExpertType === "hydrologist" ? "active" : ""}`}
            onClick={() => setActiveExpertType("hydrologist")}
          >
            💧 Hydrologist
          </button>
          <button
            className={`tab-btn ${activeExpertType === "meteorologist" ? "active" : ""}`}
            onClick={() => setActiveExpertType("meteorologist")}
          >
            🌧️ Meteorologist
          </button>
        </div>
      </div>

      {loading ? (
        <div className="loading-container"><Loader /></div>
      ) : (
        <div className="assessment-layout">
          {/* Country Cards */}
          <div className="countries-list">
            {GHA_COUNTRIES.map((country) => (
              <CountryAssessmentCard
                key={country.code}
                country={country}
                assessment={assessments[country.code]}
                expertType={activeExpertType}
                forecastDate={forecastDate}
                onSave={handleSaveAssessment}
                isExpanded={expandedCountry === country.code}
                onToggle={() =>
                  setExpandedCountry(
                    expandedCountry === country.code ? null : country.code
                  )
                }
              />
            ))}
          </div>

          {/* Regional Summary */}
          <RegionalSummary
            assessments={assessments}
            forecastDate={forecastDate}
          />
        </div>
      )}
    </div>
  );
};

CountryAssessmentWidget.propTypes = {
  params: PropTypes.object,
  forecastDate: PropTypes.string,
  expertType: PropTypes.string,
};

export default CountryAssessmentWidget;
