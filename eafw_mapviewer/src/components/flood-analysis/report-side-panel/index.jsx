import React, { useCallback, useEffect, useMemo, useState } from "react";
import PropTypes from "prop-types";

import Loader from "@/components/ui/loader";

import "./styles.scss";

const WHCA_COUNTRY_CODES = new Set(["SD", "SS", "UG", "ET", "RW"]);

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

const normalizeCountryCode = (value) => {
  const text = (value || "").toString().trim();
  if (!text) return "";

  const byName = COUNTRY_NAME_TO_CODE[text.toLowerCase()];
  if (byName) return byName;

  const upper = text.toUpperCase();
  const alias = COUNTRY_CODE_ALIASES[upper];
  if (alias) return alias;
  if (upper.length === 2 && /^[A-Z]{2}$/.test(upper)) return upper;
  if (upper === "REGION") return "REGION";
  return upper;
};

const toIsoDate = (value) => {
  if (!value) return "";
  const text = value.toString();
  return text.includes("T") ? text.split("T")[0] : text;
};

const statusLabel = (mode) => (mode === "published" ? "Approved / Published" : "Draft / Unapproved");
const emptyLabel = (mode) => (mode === "published" ? "No published reports" : "No draft reports");

const ReportSidePanel = ({ mode, params }) => {
  const [loading, setLoading] = useState(false);
  const [reports, setReports] = useState([]);

  const selectedCountryCode = useMemo(
    () => normalizeCountryCode(params?.admin0_code),
    [params?.admin0_code]
  );
  const scope = (params?.scope || "all").toLowerCase();

  const loadReports = useCallback(async () => {
    const status = mode === "published" ? "published" : "draft";
    const query = new URLSearchParams({ status });
    // Keep side panels useful at page level by listing all available records by status.
    // Date-specific filtering made columns appear empty for most working sessions.

    setLoading(true);
    try {
      const response = await fetch(`/api/v1/assessments/country-assessments/?${query.toString()}`);
      if (!response.ok) {
        setReports([]);
        return;
      }

      const data = await response.json();
      const items = Array.isArray(data?.assessments) ? data.assessments : [];

      const filtered = items.filter((item) => {
        const cc = normalizeCountryCode(item.country_code || item.country_name || item.country);

        if (selectedCountryCode) {
          return cc === selectedCountryCode || cc === "REGION";
        }

        if (scope === "whca") {
          return cc === "REGION" || WHCA_COUNTRY_CODES.has(cc);
        }

        return true;
      });

      filtered.sort((a, b) => {
        const aDate = new Date(a.assessment_date || 0).getTime();
        const bDate = new Date(b.assessment_date || 0).getTime();
        return bDate - aDate;
      });

      setReports(filtered);
    } catch (error) {
      console.error(`Failed to load ${mode} reports:`, error);
      setReports([]);
    } finally {
      setLoading(false);
    }
  }, [mode, scope, selectedCountryCode]);

  useEffect(() => {
    loadReports();
  }, [loadReports]);

  useEffect(() => {
    const handleRefresh = () => loadReports();
    window.addEventListener("flood-report-refresh", handleRefresh);
    return () => window.removeEventListener("flood-report-refresh", handleRefresh);
  }, [loadReports]);

  const handleLoadReport = (report) => {
    const reportId = Number(report?.id);
    if (!Number.isFinite(reportId)) return;

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

    window.dispatchEvent(
      new CustomEvent("flood-report-load-request", {
        detail: { id: reportId },
      })
    );
  };

  return (
    <div className="c-report-side-panel">
      <div className="panel-header">{statusLabel(mode)}</div>
      <div className="panel-body">
        {loading && (
          <div className="list-loader">
            <Loader />
          </div>
        )}

        {!loading && reports.length === 0 && (
          <div className="empty-list">{emptyLabel(mode)}</div>
        )}

        {!loading && reports.map((report) => {
          const reportId = Number(report?.id);
          const canLoad = Number.isFinite(reportId);
          return (
            <button
              type="button"
              key={report.id || report.report_key}
              className={`report-card ${report.completion_state || ""}`}
              onClick={() => handleLoadReport(report)}
              disabled={!canLoad}
            >
              <div className="report-card-top">
                <span className="report-key">{report.report_key}</span>
                <span className={`report-status ${report.status}`}>{report.status}</span>
              </div>

              <div className="report-card-meta">
                <span>{report.country_name || report.country_code}</span>
                <span>{toIsoDate(report.assessment_date)}</span>
              </div>

              <div className="report-card-meta">
                <span>{report.expert_type}</span>
                <span>{report.completion_state || "draft"}</span>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
};

ReportSidePanel.propTypes = {
  mode: PropTypes.oneOf(["draft", "published"]).isRequired,
  params: PropTypes.object,
};

export default ReportSidePanel;
