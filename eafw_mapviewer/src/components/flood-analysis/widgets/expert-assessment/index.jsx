import React, { useState, useEffect, useRef, useCallback, useMemo } from "react";
import PropTypes from "prop-types";
import { connect } from "react-redux";
import maplibregl from "maplibre-gl";

import { ALERT_COLORS } from "@/utils/multimodal-config";
import { getCookie } from "@/services/user";
import Loader from "@/components/ui/loader";
import Button from "@/components/ui/button";

import "./styles.scss";

const RISK_LEVELS = [
  { value: "emergency", label: "Emergency", color: ALERT_COLORS.emergency },
  { value: "alarm", label: "Alarm", color: ALERT_COLORS.alarm },
  { value: "warning", label: "Warning", color: ALERT_COLORS.warning },
  { value: "watch", label: "Watch", color: ALERT_COLORS.watch || "#2196F3" },
  { value: "normal", label: "Normal", color: ALERT_COLORS.normal },
];

const EXPERT_TYPES = {
  hydrologist: {
    title: "Hydrologist",
    subtitle: "River-level and discharge based assessment",
    color: "#1976d2",
  },
  meteorologist: {
    title: "Meteorologist",
    subtitle: "Rainfall and weather based assessment",
    color: "#ef6c00",
  },
};

const COUNTRY_CODE_TO_NAME = {
  BD: "Burundi",
  BI: "Burundi",
  DJ: "Djibouti",
  ER: "Eritrea",
  ET: "Ethiopia",
  KE: "Kenya",
  RW: "Rwanda",
  SO: "Somalia",
  SS: "South Sudan",
  SD: "Sudan",
  TZ: "Tanzania",
  UG: "Uganda",
  REGION: "East Africa Region",
};

const COUNTRY_NAME_TO_CODE = {
  burundi: "BI",
  djibouti: "DJ",
  eritrea: "ER",
  ethiopia: "ET",
  kenya: "KE",
  rwanda: "RW",
  somalia: "SO",
  "south sudan": "SS",
  sudan: "SD",
  tanzania: "TZ",
  uganda: "UG",
  zanzibar: "TZ",
  region: "REGION",
  "east africa region": "REGION",
};

const COUNTRY_CODE_ALIASES = {
  BD: "BI",
  BDI: "BI",
};

const DEFAULT_MAP_STYLE = {
  version: 8,
  sources: {
    osm: {
      type: "raster",
      tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
      tileSize: 256,
      attribution: "© OpenStreetMap",
    },
  },
  layers: [{ id: "osm-tiles", type: "raster", source: "osm", minzoom: 0, maxzoom: 19 }],
};

const GHA_BOUNDS = [[21, -12], [52, 23]];

const normalizeCountryCode = (value) => {
  const text = (value || "").toString().trim();
  if (!text) return "";
  const byName = COUNTRY_NAME_TO_CODE[text.toLowerCase()];
  if (byName) return byName;
  const upper = text.toUpperCase();
  const alias = COUNTRY_CODE_ALIASES[upper];
  if (alias) return alias;
  if (upper.length === 2) return upper;
  if (upper === "REGION") return "REGION";
  return upper;
};

const resolveCountryName = (value) => {
  if (!value) return "";
  const code = normalizeCountryCode(value);
  if (COUNTRY_CODE_TO_NAME[code]) return COUNTRY_CODE_TO_NAME[code];
  return value;
};

const pickAdmin1 = (props = {}) =>
  props.name_1
  || props.admin1
  || props.admin_1
  || props.NAME_1
  || props.ADM1_EN
  || "";

const pickAdmin2 = (props = {}) =>
  props.name_2
  || props.admin2
  || props.admin_2
  || props.NAME_2
  || props.ADM2_EN
  || "";

const pickCountry = (props = {}) =>
  props.country
  || props.country_name
  || props.COUNTRY
  || "";

const districtKey = ({ gid_2, country, admin1, admin2 }) => {
  if (gid_2) return gid_2;
  return `${country || ""}-${admin1 || ""}-${admin2 || ""}`;
};

const requestHeaders = () => {
  const headers = { "Content-Type": "application/json" };
  const csrf = getCookie("csrftoken");
  if (csrf) headers["X-CSRFToken"] = csrf;
  return headers;
};

const getRiskColor = (riskLevel) => {
  const config = RISK_LEVELS.find((r) => r.value === riskLevel);
  return config ? config.color : "rgba(200, 200, 200, 0.3)";
};

const ExpertAssessmentWidget = ({
  forecastDate,
  selectedCountry,
  userData,
}) => {
  const mapContainerRef = useRef(null);
  const mapRef = useRef(null);
  const districtEditsRef = useRef({});
  const mergedRiskByKeyRef = useRef({});

  const [expertType, setExpertType] = useState("hydrologist");

  const [overallRisk, setOverallRisk] = useState("normal");
  const [overallComment, setOverallComment] = useState("");
  const [affectedAreas, setAffectedAreas] = useState("");
  const [recommendations, setRecommendations] = useState("");

  const [saveLoading, setSaveLoading] = useState(false);
  const [statusMessage, setStatusMessage] = useState("");
  const [activeReportId, setActiveReportId] = useState(null);

  const [majorityByKey, setMajorityByKey] = useState({});
  const [districtEdits, setDistrictEdits] = useState({});

  const [mapLoading, setMapLoading] = useState(true);
  const [selectedArea, setSelectedArea] = useState(null);
  const [showEditPanel, setShowEditPanel] = useState(false);
  const [editRisk, setEditRisk] = useState("normal");
  const [editComment, setEditComment] = useState("");

  const selectedCountryCode = useMemo(() => normalizeCountryCode(selectedCountry), [selectedCountry]);
  const selectedCountryName = useMemo(() => resolveCountryName(selectedCountry), [selectedCountry]);
  const hasCountryFocus = !!(selectedCountryCode && selectedCountryCode !== "REGION");
  const reportScope = hasCountryFocus ? "member_state" : "general";
  const reportCountryCode = hasCountryFocus ? selectedCountryCode : "REGION";
  const reportCountryName = hasCountryFocus
    ? (selectedCountryName || selectedCountryCode)
    : "East Africa Region";

  const mapCountryFilter = useMemo(
    () => (hasCountryFocus ? selectedCountryName : ""),
    [hasCountryFocus, selectedCountryName]
  );

  const mergedRiskByKey = useMemo(() => {
    const merged = { ...majorityByKey };
    Object.values(districtEdits).forEach((item) => {
      const key = districtKey(item);
      merged[key] = item.risk_level;
    });
    return merged;
  }, [majorityByKey, districtEdits]);

  const districtSummary = useMemo(() => {
    const summary = {};
    RISK_LEVELS.forEach((level) => {
      summary[level.value] = 0;
    });
    Object.values(districtEdits).forEach((item) => {
      if (summary[item.risk_level] !== undefined) {
        summary[item.risk_level] += 1;
      }
    });
    return summary;
  }, [districtEdits]);

  useEffect(() => {
    districtEditsRef.current = districtEdits;
  }, [districtEdits]);

  useEffect(() => {
    mergedRiskByKeyRef.current = mergedRiskByKey;
  }, [mergedRiskByKey]);

  const clearEditor = useCallback(() => {
    setActiveReportId(null);
    setOverallRisk("normal");
    setOverallComment("");
    setAffectedAreas("");
    setRecommendations("");
    setDistrictEdits({});
    setStatusMessage("");
    window.dispatchEvent(
      new CustomEvent("flood-report-active-selection", {
        detail: null,
      })
    );
  }, []);

  const loadMajority = useCallback(async () => {
    if (!forecastDate) return;

    try {
      const query = new URLSearchParams({ date: forecastDate, admin_level: "2" });
      if (selectedCountryName) {
        query.set("country", selectedCountryName);
      }
      const response = await fetch(`/api/v1/risk/risk-majority?${query.toString()}`);
      if (!response.ok) return;

      const data = await response.json();
      const map = {};
      (data.risk_by_admin || []).forEach((item) => {
        const key = item.key || districtKey(item);
        map[key] = item.risk_level;
      });
      setMajorityByKey(map);
    } catch (error) {
      console.error("Failed to load majority risk:", error);
      setMajorityByKey({});
    }
  }, [forecastDate, selectedCountryName]);

  const loadSingleReport = useCallback(async (assessmentId) => {
    try {
      const response = await fetch(`/api/v1/assessments/country-assessments/?id=${assessmentId}&include_districts=true`);
      if (!response.ok) return;
      const data = await response.json();
      const report = (data.assessments || [])[0];
      if (!report) return;

      setActiveReportId(report.id);
      setOverallRisk(report.risk_level || "normal");
      setOverallComment(report.assessment_comment || "");
      setAffectedAreas(report.affected_areas || "");
      setRecommendations(report.recommendations || "");

      const mappedDistricts = {};
      (report.district_assessments || []).forEach((item) => {
        const key = districtKey(item);
        mappedDistricts[key] = {
          country: item.country,
          admin1: item.admin1,
          admin2: item.admin2,
          gid_2: item.gid_2 || null,
          risk_level: item.risk_level || "normal",
          comment: item.comment || "",
        };
      });
      setDistrictEdits(mappedDistricts);

      setStatusMessage(`Loaded ${report.report_key}`);
      window.dispatchEvent(
        new CustomEvent("flood-report-active-selection", {
          detail: {
            id: report.id,
            status: report.status,
            report_key: report.report_key,
            expert_type: report.expert_type,
            country_code: report.country_code,
            country_name: report.country_name,
            assessment_date: report.assessment_date,
            completion_state: report.completion_state,
          },
        })
      );
    } catch (error) {
      console.error("Failed to load report details:", error);
    }
  }, []);

  const saveReport = useCallback(async (mode = "draft") => {
    const saveMode = mode === "submitted" ? "submitted" : "draft";

    if (!forecastDate) {
      setStatusMessage("Select a forecast date before saving.");
      return;
    }

    if (!overallComment.trim()) {
      setStatusMessage("Overall assessment comment is required before saving.");
      return;
    }

    const districtPayload = Object.values(districtEdits).map((item) => ({
      country: item.country,
      country_name: item.country,
      country_code: normalizeCountryCode(item.country),
      admin1: item.admin1,
      admin2: item.admin2,
      gid_2: item.gid_2,
      risk_level: item.risk_level,
      comment: item.comment || "",
    }));

    const creatorFromProfile = (userData && (userData.full_name || userData.email || userData.username))
      || `${expertType}-open-entry`;

    const payload = {
      expert_type: expertType,
      forecast_date: forecastDate,
      report_group: reportScope,
      country_code: reportCountryCode,
      country_name: reportCountryName,
      risk_level: overallRisk,
      comment: overallComment,
      affected_areas: affectedAreas,
      recommendations,
      created_by: creatorFromProfile,
      save_mode: saveMode,
      is_published: false,
      logged_in: true,
      district_assessments: districtPayload,
      replace_district_assessments: true,
    };

    setSaveLoading(true);
    setStatusMessage(
      saveMode === "submitted"
        ? "Submitting draft report for admin review..."
        : "Saving draft report as unapproved..."
    );

    try {
      const response = await fetch(`/api/v1/assessments/country-assessments/`, {
        method: "POST",
        headers: requestHeaders(),
        credentials: "include",
        body: JSON.stringify(payload),
      });

      const body = await response.json();
      if (!response.ok) {
        setStatusMessage(body.error || "Failed to save report.");
        return;
      }

      if (body.id) {
        setActiveReportId(body.id);
      }

      if (saveMode === "submitted") {
        setStatusMessage(
          `Draft submitted for review with ${body.district_saved_count || 0} district edits.`
        );
      } else {
        setStatusMessage(
          `Draft saved as unapproved with ${body.district_saved_count || 0} district edits.`
        );
      }

      window.dispatchEvent(new CustomEvent("flood-report-refresh"));
      if (body.id) {
        await loadSingleReport(body.id);
      }
    } catch (error) {
      console.error("Failed to save report:", error);
      setStatusMessage("Failed to save report.");
    } finally {
      setSaveLoading(false);
    }
  }, [
    forecastDate,
    reportScope,
    reportCountryCode,
    reportCountryName,
    overallComment,
    districtEdits,
    userData,
    expertType,
    overallRisk,
    affectedAreas,
    recommendations,
    loadSingleReport,
  ]);

  useEffect(() => {
    if (!forecastDate) return;
    loadMajority();
  }, [forecastDate, expertType, selectedCountryCode, loadMajority]);

  useEffect(() => {
    const handleLoadRequest = (event) => {
      const reportId = Number(event?.detail?.id);
      if (!Number.isFinite(reportId)) return;
      loadSingleReport(reportId);
    };

    window.addEventListener("flood-report-load-request", handleLoadRequest);
    return () => window.removeEventListener("flood-report-load-request", handleLoadRequest);
  }, [loadSingleReport]);

  useEffect(() => {
    if (!mapRef.current) {
      mapRef.current = new maplibregl.Map({
        container: mapContainerRef.current,
        style: DEFAULT_MAP_STYLE,
        bounds: GHA_BOUNDS,
        fitBoundsOptions: { padding: 20 },
      });

      mapRef.current.addControl(new maplibregl.NavigationControl(), "top-right");

      mapRef.current.on("load", () => {
        mapRef.current.addSource("admin2", {
          type: "vector",
          tiles: [`${window.location.origin}/pg/tileserv/gha.admin2/{z}/{x}/{y}.pbf`],
          minzoom: 0,
          maxzoom: 14,
        });

        mapRef.current.addLayer({
          id: "admin2-fill",
          type: "fill",
          source: "admin2",
          "source-layer": "gha.admin2",
          paint: {
            "fill-color": "rgba(220, 220, 220, 0.35)",
            "fill-opacity": 0.72,
          },
        });

        mapRef.current.addLayer({
          id: "admin2-outline",
          type: "line",
          source: "admin2",
          "source-layer": "gha.admin2",
          paint: {
            "line-color": "#5f6368",
            "line-width": 0.6,
          },
        });

        mapRef.current.addLayer({
          id: "admin2-hover",
          type: "line",
          source: "admin2",
          "source-layer": "gha.admin2",
          paint: {
            "line-color": "#1f4e79",
            "line-width": 1.6,
          },
          filter: ["==", "gid_2", ""],
        });

        setMapLoading(false);
      });

      const hoverPopup = new maplibregl.Popup({
        closeButton: false,
        closeOnClick: false,
        offset: 10,
      });

      mapRef.current.on("click", "admin2-fill", (event) => {
        const feature = event.features && event.features[0];
        if (!feature) return;
        const props = feature.properties || {};
        const item = {
          country: pickCountry(props),
          admin1: pickAdmin1(props),
          admin2: pickAdmin2(props),
          gid_2: props.gid_2,
        };
        const key = districtKey(item);
        const existing = districtEditsRef.current[key];

        setSelectedArea(item);
        setEditRisk(existing ? existing.risk_level : (mergedRiskByKeyRef.current[key] || "normal"));
        setEditComment(existing ? (existing.comment || "") : "");
        setShowEditPanel(true);
      });

      mapRef.current.on("mousemove", "admin2-fill", (event) => {
        const feature = event.features && event.features[0];
        if (!feature) return;

        const props = feature.properties || {};
        const admin1Name = pickAdmin1(props);
        const admin2Name = pickAdmin2(props);
        const countryName = pickCountry(props);
        const key = districtKey({
          country: countryName,
          admin1: admin1Name,
          admin2: admin2Name,
          gid_2: props.gid_2,
        });
        const mergedRisk = mergedRiskByKeyRef.current[key] || "normal";

        mapRef.current.getCanvas().style.cursor = "pointer";
        mapRef.current.setFilter("admin2-hover", ["==", "gid_2", props.gid_2 || ""]);

        hoverPopup
          .setLngLat(event.lngLat)
          .setHTML(
            `<div style="font-size:12px;line-height:1.35">`
            + `<strong>${admin2Name || "District"}</strong><br/>`
            + `<span style="color:#334155">Admin 1: ${admin1Name || "N/A"}</span><br/>`
            + `<span style="color:#666">${countryName || ""}</span><br/>`
            + `<span style="color:${getRiskColor(mergedRisk)};font-weight:700">${mergedRisk.toUpperCase()}</span>`
            + `</div>`
          )
          .addTo(mapRef.current);
      });

      mapRef.current.on("mouseleave", "admin2-fill", () => {
        mapRef.current.getCanvas().style.cursor = "";
        mapRef.current.setFilter("admin2-hover", ["==", "gid_2", ""]);
        hoverPopup.remove();
      });
    }

    return () => {
      if (mapRef.current) {
        mapRef.current.remove();
        mapRef.current = null;
      }
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!mapRef.current || !mapRef.current.isStyleLoaded()) return;

    const expression = [
      "match",
      [
        "coalesce",
        ["get", "gid_2"],
        ["concat", ["get", "country"], "-", ["get", "name_1"], "-", ["get", "name_2"]],
      ],
    ];

    Object.entries(mergedRiskByKey).forEach(([key, risk]) => {
      expression.push(key, getRiskColor(risk));
    });
    expression.push("rgba(220, 220, 220, 0.35)");

    try {
      mapRef.current.setPaintProperty("admin2-fill", "fill-color", expression);
    } catch (error) {
      // layer not yet ready
    }
  }, [mergedRiskByKey]);

  useEffect(() => {
    if (!mapRef.current || !mapRef.current.isStyleLoaded()) return;

    const filter = mapCountryFilter ? ["==", "country", mapCountryFilter] : null;
    try {
      mapRef.current.setFilter("admin2-fill", filter);
      mapRef.current.setFilter("admin2-outline", filter);
    } catch (error) {
      // layer not yet ready
    }
  }, [mapCountryFilter]);

  const applyDistrictEdit = useCallback(() => {
    if (!selectedArea) return;
    const key = districtKey(selectedArea);
    setDistrictEdits((prev) => ({
      ...prev,
      [key]: {
        country: selectedArea.country,
        admin1: selectedArea.admin1,
        admin2: selectedArea.admin2,
        gid_2: selectedArea.gid_2 || null,
        risk_level: editRisk,
        comment: editComment,
      },
    }));

    setShowEditPanel(false);
    setSelectedArea(null);
    setEditComment("");
    setEditRisk("normal");
  }, [selectedArea, editRisk, editComment]);

  const cancelDistrictEdit = useCallback(() => {
    setShowEditPanel(false);
    setSelectedArea(null);
    setEditComment("");
    setEditRisk("normal");
  }, []);

  return (
    <div className="c-expert-assessment">
      <div className="widget-header">
        <h3 className="widget-title">Flood Assessment Workspace</h3>
        <p className="widget-subtitle">
          Hydrologists and meteorologists update flood narratives and district edits here. Every update is saved as draft and published after admin review.
        </p>
      </div>

      <div className="assessment-controls">
        <div className="expert-switch">
          {Object.entries(EXPERT_TYPES).map(([value, config]) => (
            <button
              key={value}
              type="button"
              className={`expert-btn ${expertType === value ? "active" : ""}`}
              style={{ borderColor: config.color }}
              onClick={() => {
                setExpertType(value);
                clearEditor();
              }}
            >
              <span>{config.title}</span>
              <small>{config.subtitle}</small>
            </button>
          ))}
        </div>
      </div>

      <div className="interactive-column">
        <div className="editor-header">
          <div>
            <h4>Current Expert Report</h4>
            <p>
              Scope: {reportCountryName}
            </p>
          </div>
          <div className="header-meta">
            <span className="workflow-pill">Draft → Admin Review → Published</span>
            {activeReportId && <span className="active-id">Report ID: {activeReportId}</span>}
          </div>
        </div>

        <div className="overall-editor">
          <div className="form-group">
            <label>Overall Risk Level</label>
            <div className="risk-buttons">
              {RISK_LEVELS.map((level) => (
                <button
                  key={level.value}
                  type="button"
                  className={`risk-btn ${overallRisk === level.value ? "selected" : ""}`}
                  style={{
                    borderColor: level.color,
                    backgroundColor: overallRisk === level.value ? level.color : "transparent",
                  }}
                  onClick={() => setOverallRisk(level.value)}
                >
                  {level.label}
                </button>
              ))}
            </div>
          </div>

          <div className="form-group">
            <label>Overall Assessment Comment</label>
            <textarea
              value={overallComment}
              onChange={(event) => setOverallComment(event.target.value)}
              placeholder="Detailed expert analysis and situation narrative"
              rows={4}
            />
          </div>

          <div className="form-group-row">
            <div className="form-group">
              <label>Affected Areas</label>
              <textarea
                value={affectedAreas}
                onChange={(event) => setAffectedAreas(event.target.value)}
                placeholder="Districts/areas of concern"
                rows={3}
              />
            </div>
            <div className="form-group">
              <label>Recommendations</label>
              <textarea
                value={recommendations}
                onChange={(event) => setRecommendations(event.target.value)}
                placeholder="Actions and advisories"
                rows={3}
              />
            </div>
          </div>
        </div>

        <div className="district-summary">
          {RISK_LEVELS.map((level) => (
            <div key={level.value} className="summary-item">
              <span className="dot" style={{ backgroundColor: level.color }} />
              <span>{level.label}</span>
              <strong>{districtSummary[level.value] || 0}</strong>
            </div>
          ))}
        </div>

        <div className="map-wrapper">
          {mapLoading && (
            <div className="map-loader"><Loader /></div>
          )}
          <div ref={mapContainerRef} className="map-container" />
          <div className="map-note">
            Baseline map shading comes from forecast majority risk by admin unit. District edits override baseline and are saved with the draft for admin review.
          </div>
        </div>

        <div className="editor-actions">
          <Button
            theme="theme-button-light"
            onClick={() => saveReport("draft")}
            disabled={saveLoading}
          >
            {saveLoading ? "Saving..." : "Save Draft (Unapproved)"}
          </Button>
          <Button
            theme="theme-button-green"
            onClick={() => saveReport("submitted")}
            disabled={saveLoading}
          >
            {saveLoading ? "Saving..." : "Submit for Review"}
          </Button>
        </div>

        <div className="approval-note">
          Save Draft keeps the report as unapproved. Submit for Review sends it to the draft review queue; admin approval publishes it to the right panel.
        </div>

        {statusMessage && <div className="status-message">{statusMessage}</div>}
      </div>

      {showEditPanel && selectedArea && (
        <div className="edit-panel-overlay" onClick={cancelDistrictEdit}>
          <div className="edit-panel" onClick={(event) => event.stopPropagation()}>
            <div className="edit-panel-header">
              <h4>District Risk Edit</h4>
              <button type="button" className="close-btn" onClick={cancelDistrictEdit}>x</button>
            </div>
            <div className="edit-panel-body">
              <div className="area-title">{selectedArea.admin2}</div>
              <div className="area-subtitle">{selectedArea.admin1}, {selectedArea.country}</div>

              <div className="risk-options">
                {RISK_LEVELS.map((level) => (
                  <button
                    key={level.value}
                    type="button"
                    className={`risk-option ${editRisk === level.value ? "active" : ""}`}
                    style={{
                      borderColor: level.color,
                      backgroundColor: editRisk === level.value ? level.color : "transparent",
                    }}
                    onClick={() => setEditRisk(level.value)}
                  >
                    {level.label}
                  </button>
                ))}
              </div>

              <div className="form-group">
                <label>District Comment</label>
                <textarea
                  value={editComment}
                  onChange={(event) => setEditComment(event.target.value)}
                  rows={3}
                  placeholder="Optional district-level note"
                />
              </div>

              <div className="edit-panel-actions">
                <Button theme="theme-button-light" onClick={cancelDistrictEdit}>Cancel</Button>
                <Button theme="theme-button-green" onClick={applyDistrictEdit}>Apply</Button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

ExpertAssessmentWidget.propTypes = {
  forecastDate: PropTypes.string,
  selectedCountry: PropTypes.string,
  userData: PropTypes.object,
};

const mapStateToProps = (state) => ({
  userData: state?.auth?.data || {},
});

export default connect(mapStateToProps)(ExpertAssessmentWidget);
