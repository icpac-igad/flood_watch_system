import { useEffect, useMemo, useState } from "react";

import FullscreenLayout from "@/wrappers/fullscreen";
import { CMS_API } from "@/utils/constants";

import "./reports.scss";

const FILTERS = [
  { key: "all", label: "All Reports" },
  { key: "bulletin", label: "Flood Bulletins" },
  { key: "sitrep", label: "Situation Reports" },
];

const TYPE_LABELS = {
  bulletin: "Flood Bulletin",
  sitrep: "Situation Report",
};

const formatDate = (value) => {
  if (!value) {
    return "Date TBD";
  }

  try {
    return new Date(value).toLocaleDateString("en-GB", {
      year: "numeric",
      month: "long",
      day: "numeric",
    });
  } catch (err) {
    return value;
  }
};

const ReportCard = ({ report }) => {
  const {
    title,
    summary,
    report_type,
    report_date,
    badge,
    url,
  } = report;

  const badgeLabel = TYPE_LABELS[report_type] || "Report";

  return (
    <article className="report-card">
      <div className="report-card__header">
        <span className={`report-card__type badge-${report_type}`}>
          {badgeLabel}
        </span>
        <p className="report-card__date">
          {formatDate(report_date)}
        </p>
      </div>

      <h3 className="report-card__title">{title}</h3>

      {badge && (
        <span className="report-card__badge">{badge}</span>
      )}

      <p className="report-card__summary">
        {summary || "Summary will be available when the report is published."}
      </p>

      <div className="report-card__footer">
        <a
          href={url || "#"}
          target="_blank"
          rel="noreferrer"
          className="report-card__link"
        >
          View Report →
        </a>
      </div>
    </article>
  );
};

const ReportsPage = () => {
  const [reports, setReports] = useState([]);
  const [introduction, setIntroduction] = useState("");
  const [filter, setFilter] = useState("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let ignore = false;

    const fetchReports = async () => {
      setLoading(true);
      try {
        const response = await fetch(`${CMS_API}/reports/`);
        if (!response.ok) {
          throw new Error(await response.text());
        }

        const data = await response.json();
        if (ignore) {
          return;
        }

        setIntroduction(data.introduction || "");
        setReports(data.reports || []);
        setError(null);
      } catch (err) {
        if (!ignore) {
          setError(
            err?.message || "Unable to load reports. Try again later."
          );
        }
      } finally {
        if (!ignore) {
          setLoading(false);
        }
      }
    };

    fetchReports();

    return () => {
      ignore = true;
    };
  }, []);

  const filteredReports = useMemo(() => {
    if (filter === "all") {
      return reports;
    }
    return reports.filter((report) => report.report_type === filter);
  }, [filter, reports]);

  return (
    <FullscreenLayout
      title="Reports"
      description="Latest flood bulletins and situation reports"
    >
      <div className="reports-page">
        <section className="reports-header">
          <div className="reports-header__content">
            <p className="reports-header__eyebrow">East Africa Flood Watch</p>
            <h1 className="reports-header__title">Reports</h1>
            <p className="reports-header__intro">
              {introduction ||
                "Browse the latest bulletins and situation reports produced by ICPAC."}
            </p>
          </div>
          <div className="reports-header__actions">
            {FILTERS.map((item) => (
              <button
                key={item.key}
                type="button"
                className={`reports-filter ${
                  filter === item.key ? "is-active" : ""
                }`}
                onClick={() => setFilter(item.key)}
              >
                {item.label}
              </button>
            ))}
          </div>
        </section>

        <section className="reports-grid">
          {loading && <p className="reports-state">Loading reports…</p>}
          {!loading && error && (
            <p className="reports-state reports-state--error">{error}</p>
          )}
          {!loading && !error && filteredReports.length === 0 && (
            <p className="reports-state">No reports available at the moment.</p>
          )}
          {!loading &&
            !error &&
            filteredReports.map((report) => (
              <ReportCard key={report.id} report={report} />
            ))}
        </section>
      </div>
    </FullscreenLayout>
  );
};

export default ReportsPage;
