import React, { useCallback, useEffect, useMemo, useState } from "react";
import PropTypes from "prop-types";

import Loader from "@/components/ui/loader";
import { REPORTS_API } from "@/utils/constants";

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

const COMPACT_MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];

const formatCompactDate = (value) => {
  if (!value) return "--";
  try {
    const d = new Date(value);
    if (isNaN(d.getTime())) return "--";
    const day = d.getDate().toString().padStart(2, "0");
    return `${day} ${COMPACT_MONTHS[d.getMonth()]}`;
  } catch {
    return "--";
  }
};

const formatFullDate = (value) => {
  if (!value) return "";
  try {
    const d = new Date(value);
    if (isNaN(d.getTime())) return String(value);
    return d.toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });
  } catch {
    return String(value);
  }
};

const draftStatusInfo = (completionState) => {
  if (completionState === "unapproved") {
    return { label: "Closed", className: "status-closed" };
  }
  return { label: "Open", className: "status-open" };
};

const expertTypeLabel = (expertType) => {
  if (expertType === "hydrologist") return "Hydro";
  if (expertType === "meteorologist") return "Meteo";
  return expertType || "--";
};

const statusLabel = (mode) => (mode === "published" ? "Approved / Published" : "Draft / Unapproved");
const emptyLabel = (mode) => (mode === "published" ? "No published reports" : "No draft reports");

const ReportSidePanel = ({ mode, params }) => {
  const [loading, setLoading] = useState(false);
  const [reports, setReports] = useState([]);
  const [pdfLoadingId, setPdfLoadingId] = useState(null);

  const selectedCountryCode = useMemo(
    () => normalizeCountryCode(params?.admin0_code),
    [params?.admin0_code]
  );
  const scope = (params?.scope || "all").toLowerCase();

  const loadReports = useCallback(async () => {
    const status = mode === "published" ? "published" : "draft";
    const query = new URLSearchParams({ status });

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
      new CustomEvent("flood-report-load-request", {
        detail: { id: reportId },
      })
    );
  };

  const handleDownloadPdf = useCallback(async (report) => {
    const reportId = Number(report?.id);
    if (!Number.isFinite(reportId)) return;

    setPdfLoadingId(reportId);
    try {
      const payload = {
        forecast_date: toIsoDate(report.assessment_date) || new Date().toISOString().split("T")[0],
        placename: report.country_name || "East Africa Region",
        unit_id: null,
        admin_level: null,
        map_image: null,
        chart_image: null,
      };

      const response = await fetch(`${REPORTS_API}/flood-analysis/pdf`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!response.ok) throw new Error(`Server returned ${response.status}`);

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `FloodReport_${(report.report_key || "report").replace(/\s+/g, "_")}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error("PDF download error:", error);
    } finally {
      setPdfLoadingId(null);
    }
  }, []);

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

        {!loading && reports.length > 0 && (
          <div className="table-scroll-wrapper">
            <table className="report-table">
              <thead>
                {mode === "draft" ? (
                  <tr>
                    <th>ID</th>
                    <th>Status</th>
                    <th>Created</th>
                    <th>Modified</th>
                    <th>Task</th>
                    <th>Actions</th>
                  </tr>
                ) : (
                  <tr>
                    <th>ID</th>
                    <th>Status</th>
                    <th>Actions</th>
                  </tr>
                )}
              </thead>
              <tbody>
                {reports.map((report) => {
                  const reportId = Number(report?.id);
                  const canLoad = Number.isFinite(reportId);

                  if (mode === "draft") {
                    const statusInfo = draftStatusInfo(report.completion_state);
                    return (
                      <tr key={report.id || report.report_key}>
                        <td className="col-id" title={report.report_key}>
                          {report.report_key}
                        </td>
                        <td>
                          <span className={`status-badge ${statusInfo.className}`}>
                            {statusInfo.label}
                          </span>
                        </td>
                        <td className="col-date" title={formatFullDate(report.created_at)}>
                          {formatCompactDate(report.created_at)}
                        </td>
                        <td className="col-date" title={formatFullDate(report.updated_at)}>
                          {formatCompactDate(report.updated_at)}
                        </td>
                        <td className="col-task" title={report.expert_type}>
                          {expertTypeLabel(report.expert_type)}
                        </td>
                        <td>
                          <button
                            type="button"
                            className="action-edit-btn"
                            onClick={() => handleLoadReport(report)}
                            disabled={!canLoad}
                            title="Load this report for editing"
                          >
                            Edit
                          </button>
                        </td>
                      </tr>
                    );
                  }

                  // Published mode
                  return (
                    <tr key={report.id || report.report_key}>
                      <td className="col-id" title={report.report_key}>
                        {report.report_key}
                      </td>
                      <td>
                        <span className="status-badge status-published">Published</span>
                      </td>
                      <td>
                        <button
                          type="button"
                          className="action-pdf-btn"
                          onClick={() => handleDownloadPdf(report)}
                          disabled={pdfLoadingId === reportId}
                          title="Download PDF"
                        >
                          {pdfLoadingId === reportId ? "..." : "PDF"}
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

ReportSidePanel.propTypes = {
  mode: PropTypes.oneOf(["draft", "published"]).isRequired,
  params: PropTypes.object,
};

export default ReportSidePanel;
